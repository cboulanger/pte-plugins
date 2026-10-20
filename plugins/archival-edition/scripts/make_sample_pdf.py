"""
Build the test fixture plugins/archival_edition/tests/fixtures/sample-letter.pdf.

Fills the Document Description Form (DOCX) with fictional values for a letter,
converts it to PDF with LibreOffice and appends two generated "photo" pages
(image-only pages without a text layer), mimicking how archive material is
prepared. Requires python-docx, PyMuPDF and LibreOffice (soffice).

Usage: uv run python scripts/make_sample_pdf.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import docx
import pymupdf

FIXTURES = Path(__file__).resolve().parent.parent / "plugins" / "archival_edition" / "tests" / "fixtures"
FORM = FIXTURES / "document-description-form.docx"
OUTPUT = FIXTURES / "sample-letter.pdf"

# Fictional values; field labels as printed in the form's "Field" column
VALUES = {
    "Document ID": "TEST-0001",
    "Document type": "letter",
    "Descriptive title": "Letter from Teszt Elek to Jane Example, 12 March 1962",
    "Author(s)": "Teszt, Elek",
    "Country": "Hungary",
    "City": "Budapest",
    "Holding institution": "Example Archive",
    "Estate or collection": "Nachlass Example",
    "Shelfmark": "Box 3, Folder 12, No. 4",
    "Date": "1962-03-12",
    "Source of the date": "on the document",
    "Place": "Budapest",
    "Extent": "1 leaf, 2 pages written",
    "Material and format": "letter paper",
    "Original or copy": "original",
    "Writing": "handwritten",
    "Damage": "small tear at the upper margin",
    "Language(s)": "hu; en",
    "Summary": "Thanks the addressee for an offprint and proposes a meeting at the conference in Vienna.",
    "Keywords": "comparative law; conference; offprint",
    "Names mentioned": "Example, Jane; University of Vienna",
    "Related documents": "reply to no. TEST-0000",
    "May it be published?": "unclear",
    "Reason for any restriction": "author still in copyright",
    "Image files": "IMG_0001 = 1r; IMG_0002 = 1v",
    "Photographed by": "Tester, Tom, 2026-10-01",
    "Form filled in by": "Tester, Tom, 2026-10-02",
    "Sender(s)": "Teszt, Elek",
    "Place of sending": "Budapest",
    "Date of sending": "[1962-03-12?]",
    "Addressee(s)": "Example, Jane",
    "Place of receipt": "Vienna",
}


def fill_form(target: Path) -> None:
    """Write the filled form to target."""
    document = docx.Document(str(FORM))
    for table in document.tables:
        for row in table.rows[1:]:
            label = row.cells[0].text.strip()
            if label in VALUES:
                row.cells[2].text = VALUES[label]
    document.save(str(target))


def photo_page(pdf: pymupdf.Document, lines: list[str]) -> None:
    """Append an image-only page showing the given lines of 'handwriting'."""
    scratch = pymupdf.open()
    page = scratch.new_page(width=420, height=595)
    page.draw_rect(page.rect, color=None, fill=(0.93, 0.9, 0.82))
    y = 80
    for line in lines:
        page.insert_text((50, y), line, fontsize=15, fontname="tiro", color=(0.15, 0.15, 0.35))
        y += 30
    pixmap = page.get_pixmap(dpi=110)
    target = pdf.new_page(width=420, height=595)
    target.insert_image(target.rect, pixmap=pixmap)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        filled = Path(tmp) / "form.docx"
        fill_form(filled)
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(filled)],
            check=True, capture_output=True,
        )
        pdf = pymupdf.open(Path(tmp) / "form.pdf")
        photo_page(pdf, ["Budapest, 1962. márc. 12.", "", "Kedves Jane!", "", "Köszönöm a különlenyomatot,", "nagy örömmel olvastam."])
        photo_page(pdf, ["Remélem, Bécsben találkozunk", "a konferencián.", "", "Szívélyes üdvözlettel", "Teszt Elek"])
        pdf.save(OUTPUT, garbage=4, deflate=True)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
