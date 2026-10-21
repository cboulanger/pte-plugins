"""
Archival edition plugin for the PDF-TEI-Editor.

Loaded from outside the editor's source tree via FASTAPI_PLUGIN_PATHS. Registers
the archival edition extractor and the document rules provider that points
documents to the schema and annotation guidelines in this repository.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi_app.lib.core.url_cache import UrlCache
from fastapi_app.lib.doc_rules.rules_providers import register_document_rules_provider, unregister_document_rules_provider
from fastapi_app.lib.extraction import ExtractorRegistry
from fastapi_app.lib.plugins.frontend_extension_registry import FrontendExtensionRegistry
from fastapi_app.lib.plugins.plugin_base import Plugin, PluginContext
from fastapi_app.lib.plugins.plugin_tools import get_plugin_config
from fastapi_app.lib.secrets import register_secret_service
from fastapi_app.lib.utils.annotation_rules_utils import AnnotationRuleRef

from .config import (
    AUTHORITY_CONFIG_KEY,
    AUTHORITY_ENV_VAR,
    DEFAULT_AUTHORITY,
    DEFAULT_MODEL,
    EXTRACTOR_ID,
    GUIDELINES_MARKDOWN_URL,
    MODEL_CONFIG_KEY,
    MODEL_ENV_VAR,
    PLUGIN_ID,
    SECRET_SERVICE_DESCRIPTION,
    SECRET_SERVICE_HELP_URL,
    SECRET_SERVICE_ID,
    SECRET_SERVICE_LABEL,
    SCHEMA_URL,
    VARIANT_ID,
)
from .extractor import LOCAL_SCHEMA, PLUGIN_VERSION, ArchivalEditionExtractor

try:
    # Editor versions without it download the schema from SCHEMA_URL (GitHub Pages)
    from fastapi_app.lib.core.schema_validator import register_bundled_schema, unregister_bundled_schema
except ImportError:
    register_bundled_schema = None
    unregister_bundled_schema = None

logger = logging.getLogger(__name__)


class ArchivalEditionRulesProvider:
    """Schema URL and guideline references for "Refresh document rules"."""

    def build_editorial_decl_entries(self, variant_id: str, cache: UrlCache) -> list[AnnotationRuleRef]:
        if variant_id != VARIANT_ID:
            return []
        return [{
            "category": "primary",
            "n": "Archival edition annotation guidelines",
            "refs": [{"target": GUIDELINES_MARKDOWN_URL, "content_type": "markdown", "subtype": "human"}],
        }]

    def get_schema_url(self, variant_id: str) -> Optional[str]:
        return SCHEMA_URL if variant_id == VARIANT_ID else None


class ArchivalEditionPlugin(Plugin):
    """Header from the Document Description Form and transcription of photographed archival documents."""

    def __init__(self) -> None:
        get_plugin_config(
            AUTHORITY_CONFIG_KEY,
            AUTHORITY_ENV_VAR,
            default=DEFAULT_AUTHORITY,
            description="Responsible body recorded in publicationStmt/authority of archival edition documents",
        )
        get_plugin_config(
            MODEL_CONFIG_KEY,
            MODEL_ENV_VAR,
            default=DEFAULT_MODEL,
            description="Default Claude model for transcription when none is chosen in the extraction dialog",
        )

    @property
    def metadata(self) -> dict[str, Any]:
        """Return plugin metadata."""
        return {
            "id": PLUGIN_ID,
            "name": "Archival Edition",
            "description": "Extractor for photographed archival documents with a description form, schema and annotation guidelines",
            "category": "extractor",
            "version": PLUGIN_VERSION,
            "required_roles": ["user"],
            "endpoints": [],
        }

    def get_endpoints(self) -> dict[str, Callable]:
        """The extractor is used through /api/v1/extract; no menu endpoints."""
        return {}

    async def initialize(self, context: PluginContext) -> None:
        """Register the extractor and the document rules provider."""
        register_secret_service(SECRET_SERVICE_ID, SECRET_SERVICE_LABEL, SECRET_SERVICE_DESCRIPTION, SECRET_SERVICE_HELP_URL)
        ExtractorRegistry.get_instance().register(ArchivalEditionExtractor)
        register_document_rules_provider(EXTRACTOR_ID, PLUGIN_ID, ArchivalEditionRulesProvider())
        if register_bundled_schema is not None:
            # validate against the schema of the installed plugin, without depending on GitHub Pages
            register_bundled_schema(SCHEMA_URL, LOCAL_SCHEMA)
        pb_sync = Path(__file__).parent / "extensions" / "pb-sync.js"
        FrontendExtensionRegistry.get_instance().register_extension(pb_sync, PLUGIN_ID)
        html_view = Path(__file__).parent / "extensions" / "tei-html-view.js"
        FrontendExtensionRegistry.get_instance().register_extension(html_view, PLUGIN_ID)
        logger.info("Archival edition plugin initialized")

    async def cleanup(self) -> None:
        """Unregister the extractor and the document rules provider."""
        ExtractorRegistry.get_instance().unregister(EXTRACTOR_ID)
        unregister_document_rules_provider(EXTRACTOR_ID)
        if unregister_bundled_schema is not None:
            unregister_bundled_schema(SCHEMA_URL)
