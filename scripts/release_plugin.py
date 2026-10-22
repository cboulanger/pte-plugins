"""
Resolve the plugin of a release tag and check that the tag matches the plugin's version.

Release tags have the form ``<plugin-id>-v<version>``; the version must be the ``version``
in the plugin's pte-plugin.json (the single source of the package version).

Usage:
    python scripts/release_plugin.py <tag>

Prints ``id=...``, ``version=...`` and ``path=...`` lines (for ``$GITHUB_OUTPUT``) and exits
with 1 if the tag does not name a plugin of the index or does not match its version.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAG_PATTERN = re.compile(r"^(?P<id>[a-z0-9][a-z0-9_-]*)-v(?P<version>\d+\.\d+\.\d+(?:[-+.][0-9A-Za-z.-]+)?)$")


def resolve(tag: str) -> dict[str, str]:
    """
    The plugin id, version and directory of a release tag.

    Raises:
        ValueError: If the tag is malformed, names no plugin or does not match the plugin's version
    """
    match = TAG_PATTERN.match(tag)
    if not match:
        raise ValueError(f"Release tag must be <plugin-id>-v<version>, not {tag}")
    plugin_id, version = match.group("id"), match.group("version")
    index = json.loads((REPO_ROOT / "pte-plugins.json").read_text(encoding="utf-8"))
    entry = next((p for p in index["plugins"] if p["id"] == plugin_id), None)
    if entry is None:
        raise ValueError(f"pte-plugins.json lists no plugin {plugin_id}")
    manifest = json.loads((REPO_ROOT / entry["path"] / "src" / entry["module"] / "pte-plugin.json").read_text(encoding="utf-8"))
    if manifest.get("version") != version:
        raise ValueError(f"Tag {tag} does not match the version {manifest.get('version')} in the manifest of {plugin_id}")
    return {"id": plugin_id, "version": version, "path": entry["path"]}


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        result = resolve(sys.argv[1])
    except ValueError as e:
        print(f"::error::{e}", file=sys.stderr)
        return 1
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
