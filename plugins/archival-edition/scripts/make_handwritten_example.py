"""
Build the example and test fixture plugins/archival_edition/tests/fixtures/schlote-letter-1906.pdf.

A real handwritten letter: Ernst Schlote to Maria Lüdeke, Lifang (Tsingtao),
10 June 1906, German in Kurrent script with Chinese numerals on pages 3 and 4.
The scans were published on Wikimedia Commons under CC0 1.0 by Bernd Schwabe
(Wikipedia Hannover); see SOURCES below and fixtures/README.md.

Fills the Document Description Form with the description of the letter,
converts it to PDF with LibreOffice and appends the three scans (page 1,
pages 2-3 as a double page, page 4) as image-only pages. Requires
python-docx, PyMuPDF, Pillow, LibreOffice (soffice) and access to
upload.wikimedia.org (or the scans in a local directory).

Usage: uv run python scripts/make_handwritten_example.py [--images DIR]

--images DIR reads the scans from DIR (named as on Commons) instead of
downloading them, e.g. when Wikimedia rate-limits the requests.
"""

import argparse

import hashlib
import io
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pymupdf
from PIL import Image

from make_sample_pdf import FIXTURES, fill_form

OUTPUT = FIXTURES / "schlote-letter-1906.pdf"

FILE_PREFIX = "1906-06-10 Ernst Schlote handschriftlicher Brief aus Tsingtao (Lifang) an Frl. Maria Lüdeke in Linden bei Hannover, Marktplatz 12, Brief Seite "
# Commons file name suffix, page label in the form
SOURCES = [("1.jpg", "1r"), ("2 und 3.jpg", "1v-2r"), ("4.jpg", "2v")]

# Width of the downloaded images (one of the thumbnail sizes Wikimedia serves)
WIDTH = 1920
USER_AGENT = "pte-edition-plugin-fixture/1.0 (https://github.com/cboulanger/pte-edition-plugin; fixture build script)"

# Description taken from the Commons file pages and from the scans themselves
VALUES = {
    "Document ID": "EXAMPLE-1906-001",
    "Document type": "letter",
    "Descriptive title": "Letter from Ernst Schlote to Maria Lüdeke, Lifang (Tsingtao), 10 June 1906",
    "Author(s)": "Schlote, Ernst",
    "Country": "Germany",
    "City": "Hannover",
    "Holding institution": "private collection",
    "Estate or collection": "Scans: Wikimedia Commons, Category:Ernst Schlote",
    "Date": "1906-06-10",
    "Source of the date": "on the document",
    "Place": "Lifang (Tsingtao)",
    "Extent": "1 folded sheet, 4 pages written",
    "Material and format": "squared paper",
    "Original or copy": "original",
    "Writing": "handwritten",
    "Damage": "folds, slight staining",
    "Later additions": "Chinese numerals written in ink on pages 3 and 4",
    "Language(s)": "de; zh",
    "Summary": "Schlote thanks his fiancée for her letters, writes about growing potatoes in China, the German-style town of Tsingtao and the Chinese numerals he is learning to write.",
    "Keywords": "Kiautschou; Tsingtao; everyday life; Chinese script",
    "Names mentioned": "Lüdeke, Maria",
    "May it be published?": "yes",
    "Rights holder": "public domain (CC0 1.0 for the scans)",
    "Image files": "; ".join(f"Seite_{name.removesuffix('.jpg').replace(' ', '_')} = {label}" for name, label in SOURCES),
    "Photographed by": "Schwabe, Bernd, 2026",
    "Other remarks": "Envelope (not included) postmarked Tsingtau 1906-09-19, arrival stamp Linden 1906-10-30.",
    "Sender(s)": "Schlote, Ernst",
    "Place of sending": "Lifang (Tsingtao)",
    "Date of sending": "1906-06-10",
    "Addressee(s)": "Lüdeke, Maria",
    "Place of receipt": "Linden bei Hannover",
    "Date of receipt": "1906-10-30",
}


def image_url(suffix: str) -> str:
    """URL of the WIDTH px thumbnail of a Commons file."""
    name = (FILE_PREFIX + suffix).replace(" ", "_")
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()
    quoted = urllib.parse.quote(name)
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{digest[0]}/{digest[:2]}/{quoted}/{WIDTH}px-{quoted}"


def download(url: str) -> bytes:
    """Fetch url, waiting and retrying when Wikimedia rate-limits the request."""
    for attempt in range(1, 7):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 6:
                raise
            time.sleep(10 * attempt)
    raise AssertionError("unreachable")


def photo_page(pdf: pymupdf.Document, data: bytes) -> None:
    """Append the scan as an image-only page, recompressed to keep the fixture small."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=80, optimize=True)
    # 1 px = 0.3 pt, an A4-like page for the single pages
    page = pdf.new_page(width=image.width * 0.3, height=image.height * 0.3)
    page.insert_image(page.rect, stream=buffer.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", type=Path, help="directory with the scans, named as on Commons")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        filled = Path(tmp) / "form.docx"
        fill_form(filled, VALUES)
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(filled)],
            check=True, capture_output=True,
        )
        pdf = pymupdf.open(Path(tmp) / "form.pdf")
        for suffix, _ in SOURCES:
            data = (args.images / (FILE_PREFIX + suffix)).read_bytes() if args.images else download(image_url(suffix))
            photo_page(pdf, data)
        pdf.set_metadata({"title": VALUES["Descriptive title"], "subject": "Example for the archival edition plugin; scans CC0 1.0, Wikimedia Commons"})
        pdf.save(OUTPUT, garbage=4, deflate=True)
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
