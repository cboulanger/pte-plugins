"""
Tests for the reading view static/archival-edition-to-html.xsl, run with libxslt (the XSLT 1.0
processor of Chromium-based browsers).
"""

import unittest
from pathlib import Path

from lxml import etree, html

PLUGIN_DIR = Path(__file__).parent.parent
XSLT = etree.XSLT(etree.parse(str(PLUGIN_DIR / "static" / "archival-edition-to-html.xsl")))
EXAMPLE = PLUGIN_DIR.parent.parent / "examples" / "sample-letter.tei.xml"


def render(tei: str) -> html.HtmlElement:
    """Transform a TEI document and parse the result."""
    return html.fromstring(str(XSLT(etree.fromstring(tei.encode()))))


def tei(body: str) -> str:
    """A minimal TEI document with the given body content."""
    return (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><titleStmt><title>T</title></titleStmt>'
        f"</fileDesc></teiHeader><text><body>{body}</body></text></TEI>"
    )


def pages(doc: html.HtmlElement) -> list[str]:
    """Normalized text of each page box, without its label."""
    result = []
    for page in doc.xpath('//section[@class="ae-page"]'):
        for label in page.xpath('div[@class="ae-page-label"]'):
            page.remove(label)
        # line and block boundaries separate words
        for element in page.iter("br", "div", "p"):
            element.tail = " " + (element.tail or "")
        result.append(" ".join(page.text_content().split()))
    return result


class TestHtmlView(unittest.TestCase):

    def test_sample_letter(self):
        doc = render(EXAMPLE.read_text(encoding="utf-8"))
        labels = doc.xpath('//div[@class="ae-page-label"]/text()')
        self.assertEqual(labels, ["Page 1r", "Page 1v"])
        self.assertIn("Example Archive", doc.xpath('string(//div[@class="ae-summary"])'))
        first, second = pages(doc)
        self.assertTrue(first.startswith("Budapest, 1962. márc. 12."))
        self.assertTrue(first.endswith("Remélem"))
        self.assertEqual(second, "Bécsben találkozunk a konferencián. Szívélyes üdvözlettel Teszt Elek")

    def test_page_break_inside_paragraph(self):
        doc = render(tei('<p><pb n="1"/><lb/>one <hi>two<pb n="2"/><lb/>three</hi> four</p>'))
        self.assertEqual(pages(doc), ["one two", "three four"])
        # the paragraph is continued in the second box, without a leading line break
        second = doc.xpath('//section[@class="ae-page"]')[1]
        self.assertEqual(len(second.xpath(".//p")), 1)
        self.assertEqual(second.xpath(".//p/node()[1]/self::br"), [])

    def test_content_before_first_pb(self):
        doc = render(tei('<p>before</p><pb n="2"/><p>after</p>'))
        self.assertEqual(pages(doc), ["before", "after"])

    def test_without_pb(self):
        doc = render(tei("<p>all</p>"))
        self.assertEqual(pages(doc), ["all"])

    def test_editorial_markup(self):
        doc = render(tei(
            '<pb/><p><lb/>a <choice><sic>teh</sic><corr>the</corr></choice> <gap reason="illegible"/>'
            " <supplied>b</supplied> <del>c</del><add>d</add><lb/>e</p>"
        ))
        self.assertEqual(pages(doc), ["a the […] [b] cd e"])
        self.assertEqual(doc.xpath('//span[@class="ae-alt"]/@title'), ["teh"])
        self.assertEqual(len(doc.xpath("//p/br")), 1)


if __name__ == "__main__":
    unittest.main()
