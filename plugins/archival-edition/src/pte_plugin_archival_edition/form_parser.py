"""
Reading the Document Description Form from the first pages of a PDF.

The form is normally exported from Word, so its pages have a text layer and the
values can be read from the form's tables directly. The photographs that
follow are image-only pages. When the form itself was printed and scanned (no
text layer), the extractor falls back to asking the model to read it, see
build_form_prompt() and parse_form_response().
"""

import json
import logging
import re

import pymupdf

from .fields import FIELD_IDS, FIELDS_BY_LABEL, FORM_FIELDS, normalize_label

logger = logging.getLogger(__name__)

FORM_TITLE = "document description form"
MIN_TEXT_CHARS = 50


def has_text_layer(page: pymupdf.Page) -> bool:
    """Whether a page has a usable text layer (as opposed to a photo or scan)."""
    return len(page.get_text().strip()) >= MIN_TEXT_CHARS


def count_text_form_pages(doc: pymupdf.Document) -> int:
    """
    Number of leading form pages with a text layer.

    The form starts on the first page with its title and ends before the first
    page without a text layer. Returns 0 if the first page is not a form page
    with a text layer (e.g. a scanned form).
    """
    if doc.page_count == 0 or not has_text_layer(doc[0]):
        return 0
    if FORM_TITLE not in normalize_label(doc[0].get_text()):
        return 0
    count = 0
    for page in doc:
        if not has_text_layer(page):
            break
        count += 1
    return count


def _cell_text(page: pymupdf.Page, bbox: tuple[float, float, float, float] | None) -> str:
    """
    Text of one table cell. Read with get_text() rather than Table.extract(),
    which garbles ligatures ("tt", "ff", "ti") as written by LibreOffice/Word.
    """
    if bbox is None:
        return ""
    text = page.get_text("text", clip=pymupdf.Rect(bbox), flags=0)
    # a line wrapped after a hyphen ("German-|style", "1v-|2r") continues the word
    text = re.sub(r"(?<=\w-)\s*\n\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_form_tables(doc: pymupdf.Document, page_count: int) -> dict[str, str]:
    """
    Read the "Your entry" column of the form's tables.

    Rows are matched to fields by the text of their first cell; rows that do not
    name a known field (headers, wrapped continuation rows) are ignored. A row
    split across a page break continues in a row with an empty first cell, whose
    entry is appended to the previous field.

    Args:
        doc: The PDF
        page_count: Number of leading form pages

    Returns:
        Field id -> entry text, for all fields with a non-empty entry
    """
    values: dict[str, str] = {}
    last_field: str | None = None
    for page in doc.pages(0, page_count):
        for table in page.find_tables().tables:
            for row in table.rows:
                cells = [_cell_text(page, bbox) for bbox in row.cells]
                if len(cells) < 3:
                    continue
                field = FIELDS_BY_LABEL.get(normalize_label(cells[0]))
                entry = cells[2]
                if field is not None:
                    last_field = field.id
                    if entry:
                        values[field.id] = entry
                elif not cells[0] and entry and last_field is not None:
                    values[last_field] = f"{values.get(last_field, '')} {entry}".strip()
                else:
                    last_field = None
    return values


def build_form_prompt() -> str:
    """Prompt asking the model to read a scanned form into JSON."""
    field_lines = "\n".join(f'- "{f.id}": {f.label}' for f in FORM_FIELDS)
    return (
        "The images show the first pages of a PDF. It starts with a filled-in 'Document Description Form' "
        "(a table with the columns Field, What to enter, Your entry, TEI path), followed by photographs of an archival document.\n\n"
        "1. Count how many of the images belong to the form (form_pages).\n"
        "2. Copy the text of the 'Your entry' column for each field exactly as written, including square brackets and question marks. "
        "Leave out fields whose entry is empty.\n\n"
        "Answer with one JSON object and nothing else, of the form "
        '{"form_pages": 2, "fields": {"doc_id": "...", ...}}. Use these keys for the fields:\n'
        f"{field_lines}"
    )


def parse_form_response(response: str) -> tuple[int, dict[str, str]]:
    """
    Parse the model's JSON answer to build_form_prompt().

    Returns:
        (number of form pages, field id -> entry text); unknown keys are dropped

    Raises:
        ValueError: If the response contains no JSON object
    """
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        raise ValueError("The model did not return the form as JSON")
    data = json.loads(match.group(0))
    form_pages = int(data.get("form_pages", 0))
    raw_fields = data.get("fields", {})
    fields = {
        key: re.sub(r"\s+", " ", str(value)).strip()
        for key, value in raw_fields.items()
        if key in FIELD_IDS and value is not None and str(value).strip()
    }
    return form_pages, fields
