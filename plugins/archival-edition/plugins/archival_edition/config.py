"""Configuration of the archival edition plugin."""

from fastapi_app.lib.utils.config_utils import get_config

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

ANNOTATION_GUIDES = [
    {"variant_ids": [VARIANT_ID], "category": "primary", "type": "markdown", "url": GUIDELINES_MARKDOWN_URL},
    {"variant_ids": [VARIANT_ID], "category": "primary", "type": "html", "url": GUIDELINES_HTML_URL},
]


def get_authority() -> str:
    """The responsible body recorded in publicationStmt/authority."""
    return str(get_config().get(AUTHORITY_CONFIG_KEY, default=DEFAULT_AUTHORITY) or DEFAULT_AUTHORITY)
