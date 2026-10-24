import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bump_plugin_version", REPO_ROOT / "scripts" / "bump_plugin_version.py")
assert spec is not None and spec.loader is not None
bump_plugin_version = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bump_plugin_version)


class TestBumpPluginVersion(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plugin_dir = Path(self.tmp.name) / "plugins" / "demo"
        module_dir = self.plugin_dir / "src" / "pte_plugin_demo"
        module_dir.mkdir(parents=True)
        (self.plugin_dir / "pyproject.toml").write_text(
            '[project]\nname = "pte-plugin-demo"\n'
            '[project.entry-points."pte.plugins"]\ndemo = "pte_plugin_demo"\n',
            encoding="utf-8",
        )
        (module_dir / "pte-plugin.json").write_text(
            json.dumps({"version": "1.0.0", "readme": "https://example.com", "engines": {"pte": ">=0.76.0"}}, indent=2) + "\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_bump_version_updates_version_field(self):
        bump_plugin_version.bump_version(self.plugin_dir, "1.1.0")
        manifest = json.loads((self.plugin_dir / "src" / "pte_plugin_demo" / "pte-plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "1.1.0")

    def test_bump_version_preserves_other_fields_and_formatting(self):
        bump_plugin_version.bump_version(self.plugin_dir, "1.1.0")
        text = (self.plugin_dir / "src" / "pte_plugin_demo" / "pte-plugin.json").read_text(encoding="utf-8")
        manifest = json.loads(text)
        self.assertEqual(manifest["readme"], "https://example.com")
        self.assertEqual(manifest["engines"], {"pte": ">=0.76.0"})
        self.assertTrue(text.endswith("}\n"))
        expected = {"version": "1.1.0", "readme": "https://example.com", "engines": {"pte": ">=0.76.0"}}
        self.assertEqual(text, json.dumps(expected, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()
