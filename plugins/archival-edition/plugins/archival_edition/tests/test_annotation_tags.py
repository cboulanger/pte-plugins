"""Scope of the annotation tags for the editor's visual mode, generated from the plugin schema by the editor."""

import unittest

from archival_edition.config import VARIANT_ID
from archival_edition.extractor import ArchivalEditionExtractor


class AnnotationTagsTest(unittest.TestCase):
    def setUp(self) -> None:
        info = ArchivalEditionExtractor.get_info()
        self.tags = {t["tag"]: t for t in info["annotationTags"][VARIANT_ID]}

    def test_inline_transcription_elements_are_tags(self) -> None:
        for name in ("unclear", "gap", "del", "add", "persName", "placeName", "date", "choice", "supplied"):
            self.assertIn(name, self.tags)

    def test_letter_structure_elements_are_tags(self) -> None:
        for name in ("opener", "dateline", "salute", "p", "ab", "list", "item", "closer", "signed", "postscript"):
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
        self.assertIn("reason", [a["name"] for a in unclear["attributes"]])
        self.assertTrue(unclear["description"])


if __name__ == "__main__":
    unittest.main()
