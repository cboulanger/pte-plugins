"""
Unit tests for the admin API of the inference endpoints plugin.

@testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/routes.py
@testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/keys.py
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_app.lib.core.dependencies import require_authenticated_user
from fastapi_app.lib.llm import LLMProviderError, LLMProviderRegistry
from fastapi_app.lib.secrets import SecretStore
from pte_plugin_inference_endpoints import plugin as plugin_module
from pte_plugin_inference_endpoints import routes as routes_module
from pte_plugin_inference_endpoints.keys import SHARED_KEY_OWNER
from pte_plugin_inference_endpoints.routes import router
from pte_plugin_inference_endpoints.store import EndpointStore
from pte_plugin_inference_endpoints.url_policy import EndpointURLError

ADMIN = {"username": "admin", "roles": ["admin"]}
USER = {"username": "jane", "roles": ["user"]}

OLLAMA = {"name": "Ollama (local)", "base_url": "http://localhost:11434/v1/", "models": ["llama3.2", " ", "llama3.2"], "free": True}


class TestRoutes(unittest.TestCase):
    def setUp(self):
        LLMProviderRegistry.reset_instance()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        db_dir = Path(self.temp_dir.name)
        self.store = EndpointStore(db_dir)
        self.secrets = SecretStore(db_dir)
        for target, value in (
            (routes_module, self.store), (plugin_module, self.store),
        ):
            patcher = patch.object(target, "get_store", return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch("pte_plugin_inference_endpoints.keys.get_secret_store", return_value=self.secrets)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(routes_module, "check_url")
        self.check_url = patcher.start()
        self.addCleanup(patcher.stop)

        self.user = ADMIN
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[require_authenticated_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        plugin_module.unregister_all()
        LLMProviderRegistry.reset_instance()

    def _add(self, **changes: object) -> dict[str, object]:
        response = self.client.post("/api/plugins/inference-endpoints/endpoints", json={**OLLAMA, **changes})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_add_list_and_delete(self):
        added = self._add()
        self.assertEqual(added["id"], "ollama-local")
        self.assertEqual(added["base_url"], "http://localhost:11434/v1")
        self.assertEqual(added["models"], ["llama3.2"])
        self.assertEqual(added["created_by"], "admin")
        self.assertIsNotNone(LLMProviderRegistry.get_instance().get_provider("endpoint-ollama-local"))

        listed = self.client.get("/api/plugins/inference-endpoints/endpoints").json()
        self.assertEqual([e["id"] for e in listed], ["ollama-local"])

        response = self.client.delete("/api/plugins/inference-endpoints/endpoints/ollama-local")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.store.load(), [])
        with self.assertRaises(KeyError):
            LLMProviderRegistry.get_instance().get_provider("endpoint-ollama-local")
        self.assertEqual(self.client.delete("/api/plugins/inference-endpoints/endpoints/ollama-local").status_code, 404)

    def test_shared_key_is_stored_encrypted_and_never_returned(self):
        added = self._add(key_mode="shared", api_key="sk-secret")
        self.assertTrue(added["has_key"])
        self.assertNotIn("sk-secret", self.client.get("/api/plugins/inference-endpoints/endpoints").text)
        self.assertNotIn("sk-secret", self.store.path.read_text())
        self.assertEqual(self.secrets.get(SHARED_KEY_OWNER, "inference-endpoint-ollama-local"), "sk-secret")

        self.client.delete("/api/plugins/inference-endpoints/endpoints/ollama-local")
        self.assertIsNone(self.secrets.get(SHARED_KEY_OWNER, "inference-endpoint-ollama-local"))

    def test_shared_key_mode_needs_a_key(self):
        response = self.client.post("/api/plugins/inference-endpoints/endpoints", json={**OLLAMA, "key_mode": "shared"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.store.load(), [])

    def test_forbidden_url_is_rejected(self):
        self.check_url.side_effect = EndpointURLError("Host 'metadata' resolves to a link-local address")
        response = self.client.post("/api/plugins/inference-endpoints/endpoints", json={**OLLAMA, "base_url": "http://metadata/v1"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("link-local", response.json()["detail"])

    def test_non_admins_are_rejected(self):
        self.user = USER
        self.assertEqual(self.client.get("/api/plugins/inference-endpoints/endpoints").status_code, 403)
        self.assertEqual(self.client.post("/api/plugins/inference-endpoints/endpoints", json=OLLAMA).status_code, 403)
        self.assertEqual(self.client.post("/api/plugins/inference-endpoints/test", json=OLLAMA).status_code, 403)

    def test_test_new_endpoint_uses_entered_key(self):
        with patch.object(routes_module.EndpointLLMProvider, "fetch_models", autospec=True) as fetch:
            fetch.side_effect = lambda provider: ["llama3.2", "qwen"] if provider._api_key == "k" else []
            result = self.client.post("/api/plugins/inference-endpoints/test", json={**OLLAMA, "key_mode": "shared", "api_key": "k"}).json()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["models"], ["llama3.2", "qwen"])

    def test_test_reports_missing_model_and_errors(self):
        with patch.object(routes_module.EndpointLLMProvider, "fetch_models", return_value=["qwen"]):
            result = self.client.post("/api/plugins/inference-endpoints/test", json=OLLAMA).json()
        self.assertFalse(result["ok"])
        self.assertIn("llama3.2", result["message"])

        with patch.object(routes_module.EndpointLLMProvider, "fetch_models", side_effect=LLMProviderError("Could not reach Ollama")):
            result = self.client.post("/api/plugins/inference-endpoints/test", json=OLLAMA).json()
        self.assertEqual(result, {"ok": False, "models": [], "message": "Could not reach Ollama"})

    def test_test_stored_endpoint_with_user_keys_needs_own_key(self):
        self._add(key_mode="user")
        with patch("pte_plugin_inference_endpoints.routes.require_user_secret", side_effect=routes_module.MissingSecretError("x")):
            result = self.client.post("/api/plugins/inference-endpoints/endpoints/ollama-local/test").json()
        self.assertFalse(result["ok"])
        self.assertIn("API Keys", result["message"])


if __name__ == "__main__":
    unittest.main()
