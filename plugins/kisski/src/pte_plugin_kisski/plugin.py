"""
KISSKI extractor plugin.

Registers the KisskiExtractor with the extraction registry.
Provides PDF and text extraction endpoints using KISSKI Academic Cloud API.
"""

import logging
from typing import Any, Callable

from fastapi_app.plugin_api import (
    ExtractorRegistry,
    get_config,
    get_plugin_config,
    get_service_registry,
    LLMProviderRegistry,
    Plugin,
    PluginContext,
)
from fastapi_app.lib.secrets import register_secret_service

from .extractor import KisskiExtractor
from .llm_provider import KisskiLLMProvider
from .service import KisskiService

logger = logging.getLogger(__name__)

SECRET_SERVICE_ID = "kisski"


class KisskiPlugin(Plugin):
    """Plugin that provides KISSKI API-based text and PDF processing."""

    def __init__(self) -> None:
        get_plugin_config("plugin.kisski.api.key", "KISSKI_API_KEY", default=None, description="API key for the KISSKI Academic Cloud service", masked=True)
        get_plugin_config("plugin.kisski.api.url", "KISSKI_API_URL", default="https://chat-ai.academiccloud.de/v1", description="Base URL for the KISSKI Academic Cloud API")

    @property
    def metadata(self) -> dict[str, Any]:
        """Return plugin metadata."""
        pdf_support = KisskiExtractor.check_pdf_support()
        description = "Text and PDF processing using KISSKI Academic Cloud API"
        if not pdf_support:
            description += " (PDF support unavailable - install pdf2image and poppler)"

        return {
            "id": "kisski",
            "name": "KISSKI Extractor",
            "description": description,
            "category": "extractor",
            "version": "2.0.0",
            "required_roles": ["user"],
            "endpoints": [],
            "pdf_support": pdf_support,
        }

    def get_endpoints(self) -> dict[str, Callable]:
        """Return available endpoints."""
        return {}

    async def initialize(self, context: PluginContext) -> None:
        """Register the KISSKI extractor and service."""
        import os

        # Check and log PDF support status
        pdf_support = KisskiExtractor.check_pdf_support()
        if not pdf_support:
            logger.warning(
                "KISSKI plugin: PDF support not available. "
                "Install pdf2image and poppler for PDF extraction."
            )

        # Register extractor (existing functionality)
        registry = ExtractorRegistry.get_instance()
        registry.register(KisskiExtractor)

        # Register service (new functionality)
        # Skip in test mode to allow test plugin's dummy service to take precedence
        app_mode = os.environ.get("FASTAPI_APPLICATION_MODE", "development")
        if app_mode == "testing":
            logger.info("KISSKI service not registered in testing mode")
        elif KisskiService.is_available():
            service_registry = get_service_registry()
            service_registry.register_service(KisskiService())
            logger.info("KISSKI service registered for structured-data-extraction")
        else:
            logger.warning("KISSKI service not available - missing API key")

        # Register LLM provider connector (new functionality)
        # Skip in test mode, mirroring the service-registration guard above, so a
        # live-network-capable provider never silently registers during test runs.
        api_key = get_config().get("plugin.kisski.api.key")
        base_url = get_config().get("plugin.kisski.api.url")
        if app_mode == "testing":
            logger.info("KISSKI LLM provider not registered in testing mode")
        else:
            register_secret_service(
                SECRET_SERVICE_ID,
                "KISSKI Academic Cloud",
                "Used for KISSKI models in the inference model picker.",
                "https://saia.gwdg.de/dashboard",
            )
            LLMProviderRegistry.get_instance().register(
                KisskiLLMProvider(
                    id="kisski",
                    label="KISSKI Academic Cloud",
                    base_url=base_url,
                    api_key=api_key,
                    secret_service=SECRET_SERVICE_ID,
                )
            )
            logger.info("KISSKI LLM provider registered (%s)", "shared key" if api_key else "per-user keys")

        logger.info(
            f"KISSKI extractor plugin initialized (PDF support: {pdf_support})"
        )

    async def cleanup(self) -> None:
        """Unregister the KISSKI extractor and service."""
        # Unregister extractor (existing functionality)
        registry = ExtractorRegistry.get_instance()
        registry.unregister("kisski-neural-chat")
        
        # Unregister service (new functionality)
        service_registry = get_service_registry()
        service_registry.unregister_service("kisski-extractor")

        # Unregister LLM provider (new functionality)
        LLMProviderRegistry.get_instance().unregister("kisski")

        logger.info("KISSKI extractor plugin cleaned up")
