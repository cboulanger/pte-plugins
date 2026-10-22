"""
Unit tests for plugins/grobid/src/pte_plugin_grobid/plugin.py endpoint metadata.

Run manually:
    uv run --project "$PTE_ROOT" python -m pytest plugins/grobid/src/pte_plugin_grobid/tests/test_plugin_endpoints.py -v

@testCovers plugins/grobid/src/pte_plugin_grobid/plugin.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))


class PluginEndpointMetadataTestCase(unittest.TestCase):
    def test_reload_feature_file_endpoint_is_grouped_under_grobid_category(self):
        from pte_plugin_grobid.plugin import GrobidPlugin

        plugin = GrobidPlugin.__new__(GrobidPlugin)  # skip __init__ (config bootstrap)
        endpoints = {e["name"]: e for e in plugin.metadata["endpoints"]}
        self.assertEqual(endpoints["reload_feature_file"]["category"], "grobid")
        self.assertEqual(endpoints["reload_feature_file"]["label"], "Reload Feature File")


if __name__ == "__main__":
    unittest.main()
