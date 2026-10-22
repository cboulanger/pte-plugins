"""
Building the TEI header from the values of the Document Description Form.

The mapping follows the "TEI path" column of the form. Elements are created
without namespace, like the PDF-TEI-Editor's own tei_utils, and get the TEI
namespace from the TEI root element when serialized.

Conventions of the form become attributes:
- [inferred] values get ana="#inferred", values ending in "?" get cert="low";
- dates get @when or @notBefore/@notAfter;
- "Surname, Forename" becomes persName/surname+forename, authority ids @ref.
"""

import re
from dataclasses import dataclass

from lxml import etree

from .values import (
    ParsedDate,
    ParsedName,
    ParsedValue,
    parse_date,
    parse_image_files,
    parse_languages,
    parse_name,
    parse_name_and_date,
    parse_names,
    parse_value,
    split_list,
)

XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

DOC_TYPES: dict[str, str] = {
    "letter": "letter",
    "postcard": "postcard",
    "telegram": "telegram",
    "conference program": "program",
    "program": "program",
    "programme": "program",
    "manuscript of paper or talk": "manuscript",
    "manuscript": "manuscript",
    "printed paper or offprint": "offprint",
    "offprint": "offprint",
    "notes": "notes",
    "other": "other",
}

DOC_TYPE_LABELS: dict[str, str] = {
    "letter": "Letter",
    "postcard": "Postcard",
    "telegram": "Telegram",
    "program": "Conference program or other printed matter",
    "manuscript": "Manuscript of a paper or talk",
    "offprint": "Printed paper or offprint",
    "notes": "Notes",
    "other": "Other",
}

CORRESPONDENCE_TYPES = {"letter", "postcard", "telegram"}
PRINTED_TYPES = {"program", "offprint"}
PAPER_TYPES = {"manuscript", "notes"}

DATE_EVIDENCE: dict[str, str] = {
    "on the document": "internal",
    "postmark": "postmark",
    "inferred from content": "conjecture",
}

OBJECT_FORMS: dict[str, str] = {
    "original": "original",
    "carbon copy": "carbon-copy",
    "photocopy": "photocopy",
    "draft": "draft",
    "transcript by someone else": "transcript",
    "transcript": "transcript",
}

AVAILABILITY: dict[str, str] = {"yes": "free", "no": "restricted", "unclear": "unknown"}


@dataclass
class DocumentType:
    """The document type from the form, as a doctype category id plus free text for "other"."""

    category: str
    text: str


def parse_doc_type(raw: str | None) -> DocumentType:
    """Map the form's document type to a doctype category ("other" for unknown values)."""
    text = parse_value(raw).text
    key = text.lower()
    if key in DOC_TYPES:
        return DocumentType(DOC_TYPES[key], text)
    if key.startswith("other"):
        return DocumentType("other", re.sub(r"^other\s*[:(]?\s*|\)$", "", text, flags=re.IGNORECASE).strip())
    return DocumentType("other", text)


def _sub(parent: etree._Element, tag: str, text: str | None = None, **attrs: str) -> etree._Element:
    """Append a child element with optional text and attributes (attributes with empty values are skipped)."""
    elem = etree.SubElement(parent, tag, {k: v for k, v in attrs.items() if v})
    if text:
        elem.text = text
    return elem


def _mark(elem: etree._Element, value: ParsedValue | ParsedDate | ParsedName) -> etree._Element:
    """Record the inferred/uncertain markers of a form value on an element."""
    if value.inferred:
        elem.set("ana", "#inferred")
    if value.uncertain:
        elem.set("cert", "low")
    return elem


def _text_elem(parent: etree._Element, tag: str, raw: str | None, **attrs: str) -> etree._Element | None:
    """Append an element holding a form value, or nothing if the value is empty."""
    value = parse_value(raw)
    if not value:
        return None
    return _mark(_sub(parent, tag, value.text, **attrs), value)


def _date_elem(parent: etree._Element, tag: str, raw: str | None, **attrs: str) -> etree._Element | None:
    """Append a date element with normalized dating attributes."""
    date = parse_date(raw)
    if date is None:
        return None
    return _mark(_sub(parent, tag, date.text, **date.attrs, **attrs), date)


def _name_elem(parent: etree._Element, name: ParsedName, role: str = "") -> etree._Element:
    """Append a persName (with surname/forename) or orgName."""
    refs = " ".join(name.refs)
    if not name.is_person:
        return _mark(_sub(parent, "orgName", name.text, ref=refs, role=role), name)
    pers = _sub(parent, "persName", ref=refs, role=role)
    if name.forename:
        # No separator text between the parts: the editor strips whitespace in the header
        _sub(pers, "surname", name.surname)
        _sub(pers, "forename", name.forename)
    else:
        pers.text = name.text
    return _mark(pers, name)


def _place_elem(parent: etree._Element, raw: str | None) -> etree._Element | None:
    """Append a placeName."""
    return _text_elem(parent, "placeName", raw)


def _resp_stmt(parent: etree._Element, resp: str, raw: str | None) -> None:
    """Append a respStmt from a "Name, date" form value (e.g. "Photographed by")."""
    name_text, date = parse_name_and_date(raw)
    name = parse_name(name_text, person=True) if name_text else None
    if name is None:
        return
    stmt = _sub(parent, "respStmt")
    _sub(stmt, "resp", resp, when=date)
    _name_elem(stmt, name)


def _phrase_names(parent: etree._Element, raw: str | None) -> None:
    """Fill an element with a semicolon-separated list of names (persName/orgName)."""
    for name in parse_names(raw):
        _name_elem(parent, name)


def build_file_desc(fields: dict[str, str], file_xml_id: str, doc_type: DocumentType, authority: str) -> etree._Element:
    """
    Build fileDesc: titleStmt, publicationStmt, notesStmt and sourceDesc (msDesc,
    plus biblStruct for printed matter).
    """
    file_desc = etree.Element("fileDesc")
    file_desc.set(XML_ID, file_xml_id)

    # titleStmt
    title_stmt = _sub(file_desc, "titleStmt")
    if not _text_elem(title_stmt, "title", fields.get("title"), level="a"):
        supplied = fields.get("supplied_title") or fields.get("doc_id") or "Untitled document"
        _text_elem(title_stmt, "title", supplied, level="a", type="supplied")
    author_names = parse_names(fields.get("authors"), person=True)
    for name in author_names:
        if name.text.lower() == "unknown":
            _sub(title_stmt, "author", "Unknown")
        else:
            _name_elem(_sub(title_stmt, "author"), name)
    for name in parse_names(fields.get("corporate_author"), person=False):
        _name_elem(_sub(title_stmt, "author"), name)
    _resp_stmt(title_stmt, "photography", fields.get("photographed_by"))
    _resp_stmt(title_stmt, "metadata", fields.get("form_filled_by"))

    # publicationStmt
    pub_stmt = _sub(file_desc, "publicationStmt")
    _sub(pub_stmt, "authority", authority)
    _text_elem(pub_stmt, "idno", fields.get("doc_id"), type="document-id")
    status = AVAILABILITY.get(parse_value(fields.get("publishable")).text.lower(), "")
    if status or fields.get("restriction") or fields.get("rights_holder"):
        availability = _sub(pub_stmt, "availability", status=status)
        _text_elem(availability, "p", fields.get("restriction"))
        _text_elem(availability, "licence", fields.get("rights_holder"))

    # notesStmt
    notes_stmt = etree.Element("notesStmt")
    if fields.get("names"):
        _phrase_names(_sub(notes_stmt, "note", type="entities"), fields.get("names"))
    for related in split_list(fields.get("related")):
        item = _sub(notes_stmt, "relatedItem")
        _text_elem(item, "bibl", related)
    if doc_type.category in PRINTED_TYPES:
        _text_elem(notes_stmt, "note", fields.get("creator_role"), type="participation")
    _text_elem(notes_stmt, "note", fields.get("remarks"))
    if doc_type.category == "other" and doc_type.text and doc_type.text.lower() != "other":
        _sub(notes_stmt, "note", doc_type.text, type="doctype")
    if len(notes_stmt):
        file_desc.append(notes_stmt)

    # sourceDesc
    source_desc = _sub(file_desc, "sourceDesc")
    source_desc.append(build_ms_desc(fields, doc_type, author_names))
    if doc_type.category in PRINTED_TYPES and any(
        fields.get(k) for k in ("event", "event_dates", "event_place", "organisers", "publisher")
    ):
        source_desc.append(build_bibl_struct(fields))
    return file_desc


def build_ms_desc(fields: dict[str, str], doc_type: DocumentType, authors: list[ParsedName]) -> etree._Element:
    """Build msDesc: identifier, contents, physical description, origin, related publications."""
    ms_desc = etree.Element("msDesc")

    identifier = _sub(ms_desc, "msIdentifier")
    _text_elem(identifier, "country", fields.get("country"))
    _text_elem(identifier, "settlement", fields.get("city"))
    _text_elem(identifier, "repository", fields.get("repository"))
    _text_elem(identifier, "collection", fields.get("collection"))
    _text_elem(identifier, "idno", fields.get("shelfmark"), type="shelfmark")

    contents = etree.Element("msContents")
    item = _sub(contents, "msItem")
    for name in authors:
        if name.text.lower() != "unknown":
            _name_elem(_sub(item, "author"), name)
    if doc_type.category in PAPER_TYPES:
        _text_elem(item, "note", fields.get("stage"), type="stage")
    if len(item):
        ms_desc.append(contents)

    phys = etree.Element("physDesc")
    object_desc = _sub(phys, "objectDesc", form=OBJECT_FORMS.get(parse_value(fields.get("form")).text.lower(), ""))
    support_desc = _sub(object_desc, "supportDesc")
    _text_elem(support_desc, "support", fields.get("material"))
    _text_elem(support_desc, "extent", fields.get("extent"))
    _text_elem(support_desc, "foliation", fields.get("not_photographed"))
    _text_elem(support_desc, "condition", fields.get("damage"))
    if not len(support_desc):
        object_desc.remove(support_desc)
    if not len(object_desc) and not object_desc.get("form"):
        phys.remove(object_desc)

    writing = parse_value(fields.get("writing")).text.lower()
    if writing in ("handwritten", "mixed"):
        hand_desc = _sub(phys, "handDesc")
        _sub(hand_desc, "handNote", "Main hand of the document.", scope="major", script="handwritten", **{XML_ID: "hand-main"})
        if fields.get("later_additions"):
            _text_elem(hand_desc, "handNote", fields.get("later_additions"), scope="minor", **{XML_ID: "hand-later"})
    if writing in ("typewritten", "printed", "mixed"):
        type_desc = _sub(phys, "typeDesc")
        kind = "typewritten" if writing != "printed" else "printed"
        _sub(type_desc, "typeNote", f"The document is {kind}." if writing != "mixed" else "Typewritten or printed parts.")
    _text_elem(phys, "additions", fields.get("letterhead"), type="letterhead")
    _text_elem(phys, "additions", fields.get("later_additions"), type="later")
    _text_elem(phys, "accMat", fields.get("enclosures"))
    if len(phys):
        ms_desc.append(phys)

    if fields.get("date") or fields.get("place"):
        history = _sub(ms_desc, "history")
        origin = _sub(history, "origin")
        evidence = DATE_EVIDENCE.get(parse_value(fields.get("date_evidence")).text.lower(), "")
        if fields.get("date_evidence") and not evidence:
            evidence = "other"
        _date_elem(origin, "origDate", fields.get("date"), evidence=evidence)
        place = _text_elem(origin, "origPlace", fields.get("place"))
        if place is not None and place.text and place.text.lower() == "unknown":
            place.set("cert", "unknown")

    bibls: list[etree._Element] = []
    if doc_type.category in PAPER_TYPES and fields.get("published_as"):
        bibl = etree.Element("bibl", type="published")
        bibl.text = parse_value(fields.get("published_as")).text
        if fields.get("differs"):
            _sub(bibl, "note", f"Differences from the manuscript: {parse_value(fields['differs']).text}", type="differences")
        bibls.append(bibl)
    if bibls:
        list_bibl = _sub(_sub(ms_desc, "additional"), "listBibl")
        for bibl in bibls:
            list_bibl.append(bibl)
    return ms_desc


def build_bibl_struct(fields: dict[str, str]) -> etree._Element:
    """Build the biblStruct of printed matter (part C of the form)."""
    bibl_struct = etree.Element("biblStruct", type="printed")
    monogr = _sub(bibl_struct, "monogr")
    _text_elem(monogr, "title", fields.get("title") or fields.get("supplied_title"), level="m")
    for name in parse_names(fields.get("organisers")):
        stmt = _sub(monogr, "respStmt")
        _sub(stmt, "resp", "organiser")
        _name_elem(stmt, name)
    if fields.get("event") or fields.get("event_dates") or fields.get("event_place"):
        meeting = _sub(monogr, "meeting")
        meeting.text = parse_value(fields.get("event")).text or None
        _date_elem(meeting, "date", fields.get("event_dates"))
        _place_elem(meeting, fields.get("event_place"))
    imprint = _sub(monogr, "imprint")
    _text_elem(imprint, "publisher", fields.get("publisher"))
    return bibl_struct


def build_class_decl() -> etree._Element:
    """Build the classDecl with the doctype taxonomy referenced by catRef."""
    class_decl = etree.Element("classDecl")
    taxonomy = _sub(class_decl, "taxonomy", **{XML_ID: "doctype"})
    for category, label in DOC_TYPE_LABELS.items():
        cat = _sub(taxonomy, "category", **{XML_ID: f"doctype-{category}"})
        _sub(cat, "catDesc", label)
    return class_decl


def build_profile_desc(fields: dict[str, str], doc_type: DocumentType) -> etree._Element:
    """Build profileDesc: abstract, creation, langUsage, textClass and correspDesc."""
    profile = etree.Element("profileDesc")
    summary = parse_value(fields.get("summary"))
    if summary:
        _mark(_sub(_sub(profile, "abstract"), "p", summary.text), summary)
    if doc_type.category in PAPER_TYPES:
        _text_elem(profile, "creation", fields.get("occasion"))

    languages = [(code, label) for code, label in parse_languages(fields.get("languages")) if code]
    if languages:
        lang_usage = _sub(profile, "langUsage")
        for code, label in languages:
            _sub(lang_usage, "language", label if label.lower() != code else None, ident=code)

    text_class = _sub(profile, "textClass")
    _sub(text_class, "catRef", target=f"#doctype-{doc_type.category}", scheme="#doctype")
    terms = split_list(fields.get("keywords"))
    if terms:
        keywords = _sub(text_class, "keywords")
        for term in terms:
            _sub(keywords, "term", term)

    if doc_type.category in CORRESPONDENCE_TYPES:
        corresp = build_corresp_desc(fields)
        if len(corresp):
            profile.append(corresp)
    return profile


def build_corresp_desc(fields: dict[str, str]) -> etree._Element:
    """Build correspDesc from part B of the form."""
    corresp = etree.Element("correspDesc")
    sent = etree.Element("correspAction", type="sent")
    for name in parse_names(fields.get("senders")):
        _name_elem(sent, name)
    for name in parse_names(fields.get("scribe"), person=True):
        _name_elem(sent, name, role="scribe")
    _place_elem(sent, fields.get("sent_place"))
    _date_elem(sent, "date", fields.get("sent_date"))
    if len(sent):
        corresp.append(sent)

    received = etree.Element("correspAction", type="received")
    for name in parse_names(fields.get("addressees")):
        _name_elem(received, name)
    _place_elem(received, fields.get("received_place"))
    _date_elem(received, "date", fields.get("received_date"))
    if len(received):
        corresp.append(received)

    context = etree.Element("correspContext")
    _text_elem(context, "ref", fields.get("replies_to"), type="replyTo")
    _text_elem(context, "ref", fields.get("replied_by"), type="repliedBy")
    if len(context):
        corresp.append(context)
    return corresp


def build_facsimile(fields: dict[str, str], page_count: int) -> tuple[etree._Element, list[tuple[str, str]]]:
    """
    Build facsimile with one surface per photographed page.

    Page labels and file names come from the "Image files" field
    ("IMG_0231 = 1r; ..."); pages beyond the listed files are numbered.

    Returns:
        (facsimile element, list of (surface xml:id, page label) per page)
    """
    images = parse_image_files(fields.get("image_files"))
    facsimile = etree.Element("facsimile")
    surfaces: list[tuple[str, str]] = []
    for i in range(page_count):
        file_name, label = images[i] if i < len(images) else ("", "")
        label = label or str(i + 1)
        surface_id = f"surface-{i + 1}"
        surface = _sub(facsimile, "surface", n=label, **{XML_ID: surface_id})
        if file_name:
            _sub(surface, "graphic", url=file_name)
        surfaces.append((surface_id, label))
    return facsimile, surfaces


def build_scaffold_header(fields: dict[str, str], file_xml_id: str, authority: str) -> tuple[etree._Element, DocumentType]:
    """
    Build teiHeader with fileDesc and profileDesc (encodingDesc and revisionDesc
    are added by the extractor, which knows the application context).
    """
    doc_type = parse_doc_type(fields.get("doc_type"))
    header = etree.Element("teiHeader")
    header.append(build_file_desc(fields, file_xml_id, doc_type, authority))
    header.append(build_profile_desc(fields, doc_type))
    return header, doc_type


def main_language(fields: dict[str, str]) -> str:
    """ISO code of the first language listed in the form, or "" if none."""
    for code, _ in parse_languages(fields.get("languages")):
        if code:
            return code
    return ""
