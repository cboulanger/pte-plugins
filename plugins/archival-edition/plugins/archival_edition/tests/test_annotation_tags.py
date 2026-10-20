"""Annotation tags for the editor's visual mode, generated from the plugin schema."""

import unittest
from pathlib import Path

from archival_edition.annotation_tags import PALETTE, generate_annotation_tags
from archival_edition.config import VARIANT_ID
from archival_edition.extractor import ArchivalEditionExtractor

SCHEMA = Path(__file__).parent.parent / "static" / "schema" / "tei-archival.rng"


class AnnotationTagsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tags = {t["tag"]: t for t in generate_annotation_tags(SCHEMA)}

    def test_inline_transcription_elements_are_tags(self) -> None:
        for name in ("unclear", "gap", "del", "add", "persName", "placeName", "date", "choice", "supplied"):
            self.assertIn(name, self.tags)

    def test_alternatives_in_choice_and_subst_are_tags(self) -> None:
        for name in ("abbr", "expan", "sic", "corr", "orig", "reg"):
            self.assertIn(name, self.tags)

    def test_milestones_are_not_tags(self) -> None:
        for name in ("lb", "pb", "cb", "milestone"):
            self.assertNotIn(name, self.tags)
            self.assertNotIn(name, self.tags["p"]["childTags"])

    def test_tag_data(self) -> None:
        unclear = self.tags["unclear"]
        self.assertEqual(unclear["label"], "unclear")
        self.assertIn(unclear["color"], PALETTE)
        self.assertIn("reason", [a["name"] for a in unclear["attributes"]])
        self.assertTrue(unclear["description"])

    def test_missing_schema_gives_no_tags(self) -> None:
        self.assertEqual(generate_annotation_tags(SCHEMA.with_name("missing.rng")), [])

    def test_extractor_info_declares_tags_for_the_variant(self) -> None:
        info = ArchivalEditionExtractor.get_info()
        self.assertEqual([t["tag"] for t in info["annotationTags"][VARIANT_ID]], sorted(self.tags))


if __name__ == "__main__":
    unittest.main()
