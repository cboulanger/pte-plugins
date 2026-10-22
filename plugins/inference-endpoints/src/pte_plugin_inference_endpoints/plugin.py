"""
Inference endpoints plugin.

Lets administrators add and remove any number of OpenAI-compatible inference
endpoints (e.g. Ollama, vLLM, LM Studio, OpenRouter). Each endpoint is registered as
a provider in the core LLM provider registry (fastapi_app/lib/llm/), so its models
are selectable wherever the registry is used, like those of the anthropic-llm and
google-llm plugins.

The endpoints are stored in ``data/db/inference-endpoints.json`` (see store.py); every
worker process watches the file and re-registers the providers when it changes.
"""

import asyncio
import logging
from contextlib import suppress
from typing import Any, Callable

from fastapi_app.plugin_api import LLMProviderRegistry, Plugin, PluginContext, get_settings

from .keys import register_user_key_service, unregister_user_key_service
from .llm_provider import EndpointLLMProvider
from .store import EndpointStore

logger = logging.getLogger(__name__)

PLUGIN_ID = "inference-endpoints"
WATCH_INTERVAL_SECONDS = 5.0

# Provider ids this process has registered, and the file modification time they reflect
_registered: set[str] = set()
_synced_mtime: float | None = None


def get_store() -> EndpointStore:
    """The endpoint store of the configured data directory."""
    return EndpointStore(get_settings().db_dir)


def sync_providers(store: EndpointStore) -> None:
    """Register a provider for every stored endpoint and unregister those of removed ones."""
    global _synced_mtime
    _synced_mtime = store.mtime()
    endpoints = store.load()
    registry = LLMProviderRegistry.get_instance()
    current = {endpoint.provider_id for endpoint in endpoints}
    for provider_id in _registered - current:
        registry.unregister(provider_id)
        unregister_user_key_service(provider_id.removeprefix("endpoint-"))
    _registered.intersection_update(current)
    for endpoint in endpoints:
        if endpoint.key_mode == "user":
            register_user_key_service(endpoint)
        registry.register(EndpointLLMProvider(endpoint))
        _registered.add(endpoint.provider_id)
    logger.debug(f"Inference endpoints registered: {sorted(current)}")


def unregister_all() -> None:
    """Unregister the providers this process has registered."""
    global _synced_mtime
    registry = LLMProviderRegistry.get_instance()
    for provider_id in _registered:
        registry.unregister(provider_id)
        unregister_user_key_service(provider_id.removeprefix("endpoint-"))
    _registered.clear()
    _synced_mtime = None


class InferenceEndpointsPlugin(Plugin):
    """Plugin that registers configurable OpenAI-compatible endpoints as LLM providers."""

    def __init__(self) -> None:
        self._watch_task: asyncio.Task[None] | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        """Return plugin metadata."""
        return {
            "id": PLUGIN_ID,
            "name": "Inference Endpoints",
            "description": "Registers OpenAI-compatible inference endpoints (e.g. Ollama) as LLM providers",
            "category": "inference",
            "version": "1.0.0",
            "required_roles": ["admin"],
            "endpoints": [
                {
                    "name": "manage",
                    "label": "Inference endpoints",
                    "description": "Add and remove OpenAI-compatible inference endpoints",
                    "state_params": [],
                }
            ],
        }

    def get_endpoints(self) -> dict[str, Callable]:
        """Return available endpoints."""
        return {"manage": self.manage}

    async def manage(self, context: PluginContext, params: dict[str, Any]) -> dict[str, str]:
        """Open the endpoint management page."""
        return {"outputUrl": f"/api/plugins/{PLUGIN_ID}/manage"}

    async def initialize(self, context: PluginContext) -> None:
        """Register the stored endpoints and watch the endpoints file for changes by other workers."""
        sync_providers(get_store())
        self._watch_task = asyncio.create_task(self._watch())

    async def _watch(self) -> None:
        store = get_store()
        while True:
            await asyncio.sleep(WATCH_INTERVAL_SECONDS)
            try:
                if store.mtime() != _synced_mtime:
                    sync_providers(store)
            except Exception as e:  # keep watching after an unexpected error
                logger.error(f"Could not update the inference endpoints: {e}")

    async def cleanup(self) -> None:
        """Stop watching and unregister the providers."""
        if self._watch_task is not None:
            self._watch_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._watch_task
            self._watch_task = None
        unregister_all()
