"""
Fields of the Document Description Form.

Each field is identified by a stable id and found in the form by its label
(the text of the "Field" column). Labels are matched after normalization, so
line breaks, extra whitespace, typographic apostrophes and letter case in the
PDF text layer do not matter.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FormField:
    """One row of the Document Description Form."""

    id: str
    label: str
    part: str  # "A" (all documents), "B" (letters), "C" (printed matter), "D" (papers)


FORM_FIELDS: tuple[FormField, ...] = (
    # A1. Identification
    FormField("doc_id", "Document ID", "A"),
    FormField("doc_type", "Document type", "A"),
    FormField("title", "Title of document", "A"),
    FormField("supplied_title", "Descriptive title", "A"),
    FormField("authors", "Author(s)", "A"),
    FormField("corporate_author", "Corporate author", "A"),
    # A2. Where the original is kept
    FormField("country", "Country", "A"),
    FormField("city", "City", "A"),
    FormField("repository", "Holding institution", "A"),
    FormField("collection", "Estate or collection", "A"),
    FormField("shelfmark", "Shelfmark", "A"),
    # A3. Date and place of creation
    FormField("date", "Date", "A"),
    FormField("date_evidence", "Source of the date", "A"),
    FormField("place", "Place", "A"),
    # A4. Physical description
    FormField("extent", "Extent", "A"),
    FormField("material", "Material and format", "A"),
    FormField("form", "Original or copy", "A"),
    FormField("writing", "Writing", "A"),
    FormField("letterhead", "Letterhead, stamps, seals", "A"),
    FormField("later_additions", "Later additions", "A"),
    FormField("damage", "Damage", "A"),
    FormField("enclosures", "Enclosures", "A"),
    # A5. Content
    FormField("languages", "Language(s)", "A"),
    FormField("summary", "Summary", "A"),
    FormField("keywords", "Keywords", "A"),
    FormField("names", "Names mentioned", "A"),
    FormField("related", "Related documents", "A"),
    # A6. Rights and sensitivity
    FormField("publishable", "May it be published?", "A"),
    FormField("restriction", "Reason for any restriction", "A"),
    FormField("rights_holder", "Rights holder", "A"),
    # A7. Images and responsibility
    FormField("image_files", "Image files", "A"),
    FormField("not_photographed", "Pages not photographed", "A"),
    FormField("photographed_by", "Photographed by", "A"),
    FormField("form_filled_by", "Form filled in by", "A"),
    FormField("remarks", "Other remarks", "A"),
    # B. Letters, postcards and telegrams
    FormField("senders", "Sender(s)", "B"),
    FormField("sent_place", "Place of sending", "B"),
    FormField("sent_date", "Date of sending", "B"),
    FormField("addressees", "Addressee(s)", "B"),
    FormField("received_place", "Place of receipt", "B"),
    FormField("received_date", "Date of receipt", "B"),
    FormField("replies_to", "Answers which letter?", "B"),
    FormField("replied_by", "Answered by which letter?", "B"),
    FormField("scribe", "Written on behalf of someone?", "B"),
    # C. Conference programs and other printed matter
    FormField("event", "Name of the event", "C"),
    FormField("event_dates", "Date(s) of the event", "C"),
    FormField("event_place", "Place of the event", "C"),
    FormField("organisers", "Organiser(s)", "C"),
    FormField("publisher", "Publisher or printer", "C"),
    FormField("creator_role", "Role of the estate's creator", "C"),
    # D. Papers, talks and manuscripts
    FormField("stage", "Stage of the text", "D"),
    FormField("occasion", "Occasion", "D"),
    FormField("published_as", "Later published?", "D"),
    FormField("differs", "Differs from the published version?", "D"),
)

FIELD_IDS: tuple[str, ...] = tuple(f.id for f in FORM_FIELDS)


def normalize_label(label: str) -> str:
    """Normalize a field label for matching: lower case, single spaces, straight apostrophes."""
    label = label.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", label).strip().lower()


FIELDS_BY_LABEL: dict[str, FormField] = {normalize_label(f.label): f for f in FORM_FIELDS}
