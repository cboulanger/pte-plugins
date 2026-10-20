"""
End-to-end tests of the extractor with a fake multimodal model, and of loading
the plugin from FASTAPI_PLUGIN_PATHS.
"""

import asyncio
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from fastapi_app.lib.llm import LLMImage, LLMModel, LLMProvider, LLMProviderRegistry

from archival_edition import extractor as extractor_module
from archival_edition.extractor import ArchivalEditionExtractor
from archival_edition.transcriber import parse_fragment, plain_text

FIXTURES = Path(__file__).parent / "fixtures"
PLUGIN_DIR = Path(__file__).parent.parent
SCHEMA = PLUGIN_DIR / "static" / "schema" / "tei-archival.rng"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}

PAGE_1 = """<opener><dateline>Budapest, 1962. márc. 12.</dateline><lb/><salute>Kedves Jane!</salute></opener>
<p><lb/>Köszönöm a <unclear cert="low">különlenyomatot</unclear>,<lb/>nagy örömmel olvastam. Remélem</p>"""
PAGE_2_BROKEN = "<p part=\"F\"><lb/>Bécsben találkozunk<lb/>a konferencián.</p><closer><salute>Szívélyes üdvözlettel</salute><signed>Teszt Elek</closer>"
PAGE_2_REPAIRED = "<p part=\"F\"><lb/>Bécsben találkozunk<lb/>a konferencián.</p><closer><salute>Szívélyes üdvözlettel</salute><signed>Teszt Elek</signed></closer>"


class FakeProvider(LLMProvider):
    """Returns canned transcriptions; page 2 is malformed and gets repaired."""

    def __init__(self) -> None:
        self.id = "fake"
        self.label = "Fake"
        self.image_calls: list[tuple[str, int]] = []
        self.text_calls = 0

    def list_models(self) -> list[LLMModel]:
        return [{"id": "m", "label": "M", "capabilities": frozenset({"chat"}), "status": None, "free": True}]

    async def chat_completion(self, model_id: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        self.text_calls += 1
        return PAGE_2_REPAIRED

    def supports_image_input(self, model_id: str) -> bool:
        return True

    async def chat_completion_with_images(self, model_id: str, system_prompt: str, user_prompt: str, images: list[LLMImage], temperature: float = 0.2) -> str:
        self.image_calls.append((user_prompt, len(images)))
        assert images[0]["media_type"] == "image/jpeg" and images[0]["data"][:2] == b"\xff\xd8"
        return PAGE_1 if len(self.image_calls) == 1 else PAGE_2_BROKEN


class TestTranscriberHelpers(unittest.TestCase):

    def test_parse_fragment_strips_fences_and_namespaces(self):
        elements = parse_fragment('```xml\n<p xmlns="http://www.tei-c.org/ns/1.0">a<lb/>b</p>\n```')
        self.assertEqual([e.tag for e in elements], ["p"])
        self.assertEqual(plain_text(elements), "a\nb")

    def test_parse_fragment_rejects_loose_text(self):
        with self.assertRaises(etree.XMLSyntaxError):
            parse_fragment("Here is the transcription: <p>a</p>")


@patch.object(extractor_module, "check_model_access", lambda provider, model_id, user: None)
@patch.object(extractor_module, "get_authority", lambda: "Test project")
@patch.object(extractor_module, "log_extraction_response", lambda *args, **kwargs: None)
class TestExtractor(unittest.TestCase):

    def setUp(self):
        self.provider = FakeProvider()
        LLMProviderRegistry.get_instance().register(self.provider)
        self.config = patch.object(extractor_module, "get_config")
        self.config.start().return_value.get.return_value = ["Extraction"]

    def tearDown(self):
        self.config.stop()
        LLMProviderRegistry.get_instance().unregister("fake")

    def extract(self, **options: str) -> etree._Element:
        xml = asyncio.run(ArchivalEditionExtractor().extract(
            pdf_path=str(FIXTURES / "sample-letter.pdf"),
            options={"provider_id": "fake", "model_id": "m", "stable_id": "abc123", **options},
        ))
        self.assertTrue(xml.startswith("<?xml-model href=\"https://cboulanger.github.io/pte-edition-plugin/schema/tei-archival.rng\""))
        return etree.fromstring(xml.encode("utf-8"))

    def assert_valid(self, tei: etree._Element) -> None:
        schema = etree.RelaxNG(etree.parse(str(SCHEMA)))
        self.assertTrue(schema.validate(tei), schema.error_log)

    def test_full_extraction(self):
        tei = self.extract()
        self.assert_valid(tei)
        self.assertEqual(len(self.provider.image_calls), 2)
        self.assertEqual(self.provider.text_calls, 1)
        # the second page gets the end of the first one as context
        self.assertIn("nagy örömmel olvastam", self.provider.image_calls[1][0])
        self.assertIn("Teszt, Elek", self.provider.image_calls[0][0])
        self.assertEqual(tei.xpath("//tei:text/@xml:lang", namespaces=NS), ["hu"])
        self.assertEqual(tei.xpath("//tei:body/tei:div/@type", namespaces=NS), ["letter"])
        self.assertEqual(tei.xpath("//tei:pb/@facs", namespaces=NS), ["#surface-1", "#surface-2"])
        self.assertEqual(tei.xpath("//tei:pb/@n", namespaces=NS), ["1r", "1v"])
        self.assertEqual(tei.xpath("//tei:closer/tei:signed/text()", namespaces=NS), ["Teszt Elek"])
        self.assertEqual(tei.xpath("//tei:application[@type='extractor']/@ident", namespaces=NS), ["archival-edition"])
        self.assertEqual(tei.xpath("//tei:label[@type='variant-id']/text()", namespaces=NS), ["archival-edition"])
        self.assertEqual(tei.xpath("//tei:respStmt[tei:resp='automatic transcription']/tei:orgName/text()", namespaces=NS), ["Fake / m"])
        self.assertTrue(tei.xpath("//tei:interpretation//tei:ref[contains(@target, 'guidelines.md')]", namespaces=NS))

    def test_header_only(self):
        tei = self.extract(transcribe="no")
        self.assert_valid(tei)
        self.assertEqual(self.provider.image_calls, [])
        self.assertEqual(len(tei.xpath("//tei:pb", namespaces=NS)), 2)


class TestPluginLoading(unittest.TestCase):
    """The plugin loads from FASTAPI_PLUGIN_PATHS as an external, multi-module plugin."""

    def test_discovered_as_external_plugin(self):
        from fastapi_app.config import get_settings
        from fastapi_app.lib.plugins.plugin_registry import PluginRegistry

        registry = PluginRegistry()
        with patch.dict(os.environ, {"FASTAPI_PLUGIN_PATHS": str(PLUGIN_DIR.parent)}):
            registry.discover_plugins([PLUGIN_DIR.parent], builtin_dir=get_settings().plugins_code_dir)
        record = registry.get_record("archival-edition")
        assert record is not None
        self.assertEqual(record.load_status, "ok", record.error)
        self.assertTrue(record.external)
        self.assertEqual(type(record.plugin).__module__, "pte_external_plugins.archival_edition.plugin")


if __name__ == "__main__":
    unittest.main()
