"""Configuration of the archival edition plugin."""

import json
from pathlib import Path
from typing import Any

from fastapi_app.lib.utils.config_utils import get_config

MANIFEST_FILE = Path(__file__).parent / "pte-plugin.json"


def read_manifest_version() -> str:
    """The plugin version, declared once in pte-plugin.json (which also holds the compatible editor versions)."""
    try:
        return str(json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return "0.0.0"


EXTRACTOR_ID = "archival-edition"
VARIANT_ID = "archival-edition"
PLUGIN_ID = "archival-edition"

REPOSITORY_URL = "https://github.com/cboulanger/pte-edition-plugin"
PAGES_URL = "https://cboulanger.github.io/pte-edition-plugin"
SCHEMA_URL = f"{PAGES_URL}/schema/tei-archival.rng"
GUIDELINES_MARKDOWN_URL = f"{PAGES_URL}/guidelines.md"
GUIDELINES_HTML_URL = f"{REPOSITORY_URL}/blob/main/docs/guidelines.md"

# publicationStmt/authority of generated documents (the project responsible for the edition)
AUTHORITY_CONFIG_KEY = "plugin.archival-edition.authority"
AUTHORITY_ENV_VAR = "ARCHIVAL_EDITION_AUTHORITY"
DEFAULT_AUTHORITY = "Unpublished archival edition"

# The model is billed to the user, so it runs with the user's own Anthropic key, stored in the
# editor's encrypted per-user secret store under this service id
SECRET_SERVICE_ID = "anthropic"
SECRET_SERVICE_LABEL = "Anthropic Claude"
SECRET_SERVICE_DESCRIPTION = "The archival edition extractor sends page images to Claude with your own API key, so the cost is billed to you."
SECRET_SERVICE_HELP_URL = "https://console.anthropic.com/settings/keys"

MODEL_CONFIG_KEY = "plugin.archival-edition.model"
MODEL_ENV_VAR = "ARCHIVAL_EDITION_MODEL"
DEFAULT_MODEL = "claude-opus-5-5"
MODELS = [DEFAULT_MODEL, "claude-sonnet-5-5"]

# Pages read by the model when the form has no text layer (scanned form)
MAX_SCANNED_FORM_PAGES = 6

FORM_OPTIONS = {
    "variant_id": {
        "type": "string",
        "label": "Variant identifier",
        "description": "Variant of the archival edition schema",
        "required": False,
        "options": [VARIANT_ID],
    },
    "model": {
        "type": "string",
        "label": "Claude model",
        "description": "Model used for transcription, billed to your own API key; leave empty for the default",
        "required": False,
        "options": MODELS,
    },
    "transcribe": {
        "type": "string",
        "label": "Transcribe pages",
        "description": "\"no\" builds the header and facsimile only, without calling the model for the photographs",
        "required": False,
        "options": ["yes", "no"],
    },
    "form_pages": {
        "type": "string",
        "label": "Form pages",
        "description": "Number of description form pages at the start of the PDF; leave empty to detect them",
        "required": False,
    },
}

NAVIGATION_XPATH = {
    VARIANT_ID: [
        {"value": "//tei:pb", "label": "&lt;pb&gt;"},
        {"value": "//tei:persName", "label": "&lt;persName&gt;"},
        {"value": "//tei:unclear", "label": "&lt;unclear&gt;"},
        {"value": "//tei:gap", "label": "&lt;gap&gt;"},
    ]
}

# Chips of the XML editor's visual mode: the elements allowed in a <div> (opener, dateline, salute, p, ab, list,
# closer, signed, postscript, ...), the inline transcription elements inside them, the items of lists and the
# alternatives grouped in <choice>/<subst> (abbr/expan, sic/corr, orig/reg), without the empty milestones.
# ANNOTATION_TAG_EXPAND is processed in order, so a parent comes before the elements found inside it.
ANNOTATION_TAG_ROOT = "div"
ANNOTATION_TAG_EXCLUDE = {"lb", "pb", "cb", "milestone"}
ANNOTATION_TAG_EXPAND = ["p", "opener", "closer", "list", "choice", "subst"]

ANNOTATION_GUIDES = [
    {"variant_ids": [VARIANT_ID], "category": "primary", "type": "markdown", "url": GUIDELINES_MARKDOWN_URL},
    {"variant_ids": [VARIANT_ID], "category": "primary", "type": "html", "url": GUIDELINES_HTML_URL},
]


def get_authority() -> str:
    """The responsible body recorded in publicationStmt/authority."""
    return str(get_config().get(AUTHORITY_CONFIG_KEY, default=DEFAULT_AUTHORITY) or DEFAULT_AUTHORITY)


def get_model(options: dict[str, Any]) -> str:
    """The model chosen in the extraction options, else the configured default."""
    chosen = str(options.get("model") or "").strip()
    return chosen or str(get_config().get(MODEL_CONFIG_KEY, default=DEFAULT_MODEL) or DEFAULT_MODEL)
