"""
Unit tests for the provider registration of the inference endpoints plugin.

@testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/plugin.py
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi_app.lib.llm import LLMProviderRegistry
from fastapi_app.lib.secrets import SecretServiceRegistry
from pte_plugin_inference_endpoints import plugin as plugin_module
from pte_plugin_inference_endpoints.plugin import InferenceEndpointsPlugin, sync_providers
from pte_plugin_inference_endpoints.store import Endpoint, EndpointStore


class TestProviderRegistration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        LLMProviderRegistry.reset_instance()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = EndpointStore(Path(self.temp_dir.name))
        patcher = patch.object(plugin_module, "get_store", return_value=self.store)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        plugin_module.unregister_all()
        LLMProviderRegistry.reset_instance()

    def _provider_ids(self) -> set[str]:
        return {p.id for p in LLMProviderRegistry.get_instance().list_providers()}

    async def test_initialize_registers_stored_endpoints_and_cleanup_unregisters(self):
        self.store.add(Endpoint(id="ollama", name="Ollama", base_url="http://localhost:11434/v1"))
        plugin = InferenceEndpointsPlugin()
        await plugin.initialize(None)
        self.assertEqual(self._provider_ids(), {"endpoint-ollama"})
        self.assertEqual(LLMProviderRegistry.get_instance().get_provider("endpoint-ollama").label, "Ollama")

        await plugin.cleanup()
        self.assertEqual(self._provider_ids(), set())

    def test_sync_adds_and_removes_providers(self):
        self.store.add(Endpoint(id="a", name="A", base_url="http://a/v1"))
        sync_providers(self.store)
        self.assertEqual(self._provider_ids(), {"endpoint-a"})

        self.store.add(Endpoint(id="b", name="B", base_url="http://b/v1", key_mode="user"))
        self.store.remove("a")
        sync_providers(self.store)
        self.assertEqual(self._provider_ids(), {"endpoint-b"})
        self.assertIsNotNone(SecretServiceRegistry.get("inference-endpoint-b"))

    def test_providers_of_other_plugins_are_kept(self):
        other = plugin_module.EndpointLLMProvider(Endpoint(id="x", name="X", base_url="http://x/v1"))
        other.id = "kisski"
        LLMProviderRegistry.get_instance().register(other)
        sync_providers(self.store)
        self.assertEqual(self._provider_ids(), {"kisski"})

    async def test_watch_picks_up_changes_of_other_workers(self):
        plugin = InferenceEndpointsPlugin()
        with patch.object(plugin_module, "WATCH_INTERVAL_SECONDS", 0.01):
            await plugin.initialize(None)
            self.store.add(Endpoint(id="late", name="Late", base_url="http://late/v1"))
            for _ in range(200):
                if "endpoint-late" in self._provider_ids():
                    break
                await asyncio.sleep(0.01)
            self.assertIn("endpoint-late", self._provider_ids())
            await plugin.cleanup()
        self.assertEqual(self._provider_ids(), set())


if __name__ == "__main__":
    unittest.main()
