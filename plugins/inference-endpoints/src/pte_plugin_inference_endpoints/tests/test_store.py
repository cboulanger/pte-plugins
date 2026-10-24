"""
Unit tests for the endpoint storage.

@testCovers plugins/inference-endpoints/src/pte_plugin_inference_endpoints/store.py
"""

import json
import tempfile
import unittest
from pathlib import Path

from pte_plugin_inference_endpoints.store import Endpoint, EndpointStore, slugify


class TestEndpointStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.store = EndpointStore(Path(self.temp_dir.name))

    def test_empty_without_file(self):
        self.assertEqual(self.store.load(), [])
        self.assertIsNone(self.store.mtime())

    def test_add_load_remove(self):
        added = self.store.add(Endpoint(id="ollama", name="Ollama", base_url="http://localhost:11434/v1", models=("llama3.2",), free=True))
        self.assertEqual(self.store.load(), [added])
        self.assertEqual(added.provider_id, "endpoint-ollama")
        self.assertEqual(added.secret_service, "inference-endpoint-ollama")

        self.assertEqual(self.store.remove("ollama"), added)
        self.assertEqual(self.store.load(), [])
        self.assertIsNone(self.store.remove("ollama"))

    def test_add_makes_ids_unique(self):
        first = self.store.add(Endpoint(id="ollama", name="Ollama", base_url="http://a/v1"))
        second = self.store.add(Endpoint(id="ollama", name="Ollama", base_url="http://b/v1"))
        third = self.store.add(Endpoint(id="ollama", name="Ollama", base_url="http://c/v1"))
        self.assertEqual([first.id, second.id, third.id], ["ollama", "ollama-2", "ollama-3"])

    def test_invalid_key_mode_and_unknown_keys_are_tolerated(self):
        self.store.path.write_text(json.dumps({"endpoints": [
            {"id": "x", "name": "X", "base_url": "http://x/v1", "key_mode": "bogus", "future_field": 1},
            {"name": "missing id and url"},
        ]}))
        endpoints = self.store.load()
        self.assertEqual(len(endpoints), 1)
        self.assertEqual(endpoints[0].key_mode, "none")

    def test_corrupt_file_reads_as_empty(self):
        self.store.path.write_text("{not json")
        self.assertEqual(self.store.load(), [])


class TestSlugify(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Ollama (local)"), "ollama-local")
        self.assertEqual(slugify("!!!"), "endpoint")


if __name__ == "__main__":
    unittest.main()
