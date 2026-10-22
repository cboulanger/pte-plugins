"""
Storage of the configured inference endpoints.

The endpoints are kept in ``<db_dir>/inference-endpoints.json``, which every server
worker reads, so that an endpoint added in one worker reaches the others (see
``InferenceEndpointsPlugin._watch``). API keys are not part of the file: a shared key
is stored encrypted in the core secret store (see ``keys.py``), per-user keys are
stored by each user.
"""

import json
import logging
import os
import re
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

FILE_NAME = "inference-endpoints.json"

KeyMode = Literal["none", "shared", "user"]
KEY_MODES: tuple[KeyMode, ...] = ("none", "shared", "user")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """A lowercase id made of letters, digits and hyphens."""
    return _SLUG_RE.sub("-", name.lower()).strip("-")[:40] or "endpoint"


@dataclass(frozen=True)
class Endpoint:
    """An OpenAI-compatible inference endpoint.

    Attributes:
        id: Stable id derived from the name; the LLM provider id is ``endpoint-<id>``
        name: Label shown in the model picker
        base_url: URL the OpenAI paths are appended to, e.g. ``http://localhost:11434/v1``
        key_mode: "none" (no key), "shared" (one key for everyone, set by the admin)
            or "user" (each user stores their own key)
        models: Model ids to offer; empty lists the models from ``GET {base_url}/models``
        vision: Whether the models accept images
        free: Whether non-admin users may use the models (see the core's model access rules)
        timeout: Seconds to wait for a completion
    """

    id: str
    name: str
    base_url: str
    key_mode: KeyMode = "none"
    models: tuple[str, ...] = ()
    vision: bool = False
    free: bool = False
    timeout: int = 600
    created_by: str = ""

    @property
    def provider_id(self) -> str:
        """Id of the LLM provider registered for this endpoint."""
        return f"endpoint-{self.id}"

    @property
    def secret_service(self) -> str:
        """Id of the secret service holding the endpoint's key."""
        return f"inference-endpoint-{self.id}"

    def to_json(self) -> dict[str, object]:
        """JSON representation for the endpoints file."""
        data = asdict(self)
        data["models"] = list(self.models)
        return data

    @classmethod
    def from_json(cls, data: dict[str, object]) -> "Endpoint":
        """Create from the file's representation; unknown keys are ignored."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        models = known.get("models") or []
        known["models"] = tuple(str(m) for m in models) if isinstance(models, list) else ()
        if known.get("key_mode") not in KEY_MODES:
            known["key_mode"] = "none"
        return cls(**known)  # type: ignore[arg-type]


class EndpointStore:
    """Reads and writes the endpoints file."""

    def __init__(self, db_dir: Path):
        self.path = Path(db_dir) / FILE_NAME

    def mtime(self) -> float | None:
        """Modification time of the file, or None if it does not exist."""
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def load(self) -> list[Endpoint]:
        """The configured endpoints; invalid entries are skipped."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError) as e:
            logger.error(f"Cannot read {self.path}: {e}")
            return []
        endpoints: list[Endpoint] = []
        for entry in data.get("endpoints", []):
            try:
                endpoints.append(Endpoint.from_json(entry))
            except (TypeError, ValueError) as e:
                logger.error(f"Ignoring invalid entry in {self.path}: {entry!r} ({e})")
        return endpoints

    def save(self, endpoints: list[Endpoint]) -> None:
        """Replace the file atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps({"endpoints": [e.to_json() for e in endpoints]}, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".inference-endpoints-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def add(self, endpoint: Endpoint) -> Endpoint:
        """Add an endpoint; its id is made unique among the existing ones."""
        endpoints = self.load()
        taken = {e.id for e in endpoints}
        unique_id, n = endpoint.id, 2
        while unique_id in taken:
            unique_id, n = f"{endpoint.id}-{n}", n + 1
        endpoint = replace(endpoint, id=unique_id)
        self.save([*endpoints, endpoint])
        return endpoint

    def remove(self, endpoint_id: str) -> Endpoint | None:
        """Remove an endpoint; returns it, or None if there was none with that id."""
        endpoints = self.load()
        removed = next((e for e in endpoints if e.id == endpoint_id), None)
        if removed is not None:
            self.save([e for e in endpoints if e.id != endpoint_id])
        return removed

    def get(self, endpoint_id: str) -> Endpoint | None:
        """The endpoint with that id, or None."""
        return next((e for e in self.load() if e.id == endpoint_id), None)
