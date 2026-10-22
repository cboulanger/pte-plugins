"""
Checks the GitHub Pages site built by scripts/build_site.py: every plugin of the index is listed
with a link to its README, and the plugins' docs/ directories are published at their URLs.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX = json.loads((REPO_ROOT / "pte-plugins.json").read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("build_site", REPO_ROOT / "scripts" / "build_site.py")
assert spec is not None and spec.loader is not None
build_site = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_site)


class TestSite(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "_site"
        build_site.build_site(self.out)
        self.html = (self.out / "index.html").read_text(encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lists_every_plugin_with_readme_link(self):
        for plugin in INDEX["plugins"]:
            with self.subTest(plugin=plugin["id"]):
                self.assertIn(f'id="{plugin["id"]}"', self.html)
                self.assertIn(f'href="{INDEX["repository"]}/tree/main/{plugin["path"]}#readme"', self.html)

    def test_publishes_index_and_docs(self):
        self.assertEqual(json.loads((self.out / "pte-plugins.json").read_text(encoding="utf-8")), INDEX)
        # URLs recorded in TEI documents
        self.assertTrue((self.out / "archival-edition" / "schema" / "tei-archival.rng").is_file())
        self.assertTrue((self.out / "archival-edition" / "guidelines.md").is_file())


if __name__ == "__main__":
    unittest.main()
