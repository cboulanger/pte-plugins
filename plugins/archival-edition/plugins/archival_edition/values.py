"""
Parsing of the conventions used when filling in the Document Description Form.

- Inferred information is put in [square brackets]; a question mark marks it as uncertain.
- Dates are YYYY-MM-DD, YYYY-MM or YYYY; ranges are written as start/end.
- Persons are written "Surname, Forename", optionally followed by a GND, VIAF or Wikidata id.
- Lists (persons, keywords, languages) are separated by semicolons.
"""

import re
from dataclasses import dataclass, field

DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
WIKIDATA_RE = re.compile(r"\b(Q\d+)\b")
GND_RE = re.compile(r"\bGND[:\s]*([0-9X-]{6,})", re.IGNORECASE)
VIAF_RE = re.compile(r"\bVIAF[:\s]*(\d+)", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")

LANGUAGE_CODES: dict[str, str] = {
    "hungarian": "hu", "magyar": "hu", "ungarisch": "hu",
    "english": "en", "englisch": "en", "angol": "en",
    "german": "de", "deutsch": "de", "német": "de",
    "french": "fr", "französisch": "fr", "francia": "fr",
    "russian": "ru", "russisch": "ru", "orosz": "ru",
    "italian": "it", "italienisch": "it", "olasz": "it",
    "latin": "la", "latein": "la", "latin nyelv": "la",
    "polish": "pl", "czech": "cs", "slovak": "sk", "romanian": "ro", "serbian": "sr", "croatian": "hr",
}


@dataclass
class ParsedValue:
    """A form value with the [inferred] and ? markers removed."""

    text: str
    inferred: bool = False
    uncertain: bool = False

    def __bool__(self) -> bool:
        return bool(self.text)


@dataclass
class ParsedDate:
    """A date or date range with its TEI attributes."""

    text: str
    attrs: dict[str, str] = field(default_factory=dict)
    inferred: bool = False
    uncertain: bool = False


@dataclass
class ParsedName:
    """A person or organisation name with authority file references."""

    text: str
    surname: str = ""
    forename: str = ""
    is_person: bool = True
    refs: list[str] = field(default_factory=list)
    inferred: bool = False
    uncertain: bool = False


def parse_value(raw: str | None) -> ParsedValue:
    """
    Strip the inferred/uncertain markers from a form value.

    "[1962-03?]" -> ParsedValue("1962-03", inferred=True, uncertain=True)
    """
    text = re.sub(r"\s+", " ", raw or "").strip()
    inferred = text.startswith("[") and text.endswith("]")
    if inferred:
        text = text[1:-1].strip()
    uncertain = text.endswith("?")
    if uncertain:
        text = text[:-1].strip()
    return ParsedValue(text=text, inferred=inferred, uncertain=uncertain)


def split_list(raw: str | None) -> list[str]:
    """Split a semicolon-separated list into its non-empty items."""
    return [item.strip() for item in (raw or "").split(";") if item.strip()]


def parse_date(raw: str | None) -> ParsedDate | None:
    """
    Parse a date or date range into TEI dating attributes.

    "1962-03-12" -> when; "1962-03/1962-05" -> notBefore/notAfter. Values that do
    not follow the form's date format keep their text without attributes.
    """
    value = parse_value(raw)
    if not value:
        return None
    attrs: dict[str, str] = {}
    parts = [p.strip() for p in value.text.split("/")]
    if len(parts) == 1 and DATE_RE.match(parts[0]):
        attrs["when"] = parts[0]
    elif len(parts) == 2 and all(DATE_RE.match(p) for p in parts):
        attrs["notBefore"], attrs["notAfter"] = parts
    return ParsedDate(text=value.text, attrs=attrs, inferred=value.inferred, uncertain=value.uncertain)


def _authority_refs(text: str) -> tuple[str, list[str]]:
    """Remove authority ids from a name and return them as URIs."""
    refs: list[str] = []
    for match in URL_RE.findall(text):
        refs.append(match.rstrip(").,"))
    text = URL_RE.sub("", text)
    for match in GND_RE.findall(text):
        refs.append(f"https://d-nb.info/gnd/{match}")
    text = GND_RE.sub("", text)
    for match in VIAF_RE.findall(text):
        refs.append(f"https://viaf.org/viaf/{match}")
    text = VIAF_RE.sub("", text)
    for match in WIKIDATA_RE.findall(text):
        refs.append(f"http://www.wikidata.org/entity/{match}")
    text = WIKIDATA_RE.sub("", text)
    text = re.sub(r"\(\s*[,;]?\s*\)", "", text)
    return re.sub(r"\s+", " ", text).strip(" ,;()"), refs


def parse_name(raw: str, person: bool | None = None) -> ParsedName | None:
    """
    Parse one name. "Surname, Forename" is a person; a name without a comma is an
    organisation unless `person` says otherwise.
    """
    value = parse_value(raw)
    if not value:
        return None
    text, refs = _authority_refs(value.text)
    is_person = person if person is not None else ("," in text or text.lower() == "unknown")
    surname, _, forename = text.partition(",") if is_person else (text, "", "")
    return ParsedName(
        text=text,
        surname=surname.strip(),
        forename=forename.strip(),
        is_person=is_person,
        refs=refs,
        inferred=value.inferred,
        uncertain=value.uncertain,
    )


def parse_names(raw: str | None, person: bool | None = None) -> list[ParsedName]:
    """Parse a semicolon-separated list of names."""
    return [n for n in (parse_name(item, person) for item in split_list(raw)) if n is not None]


def parse_languages(raw: str | None) -> list[tuple[str, str]]:
    """
    Parse the languages field into (ISO 639 code, label) pairs.

    Accepts codes ("hu; en") and names in English, German or Hungarian
    ("Hungarian, English"); unknown names are kept as label with an empty code.
    """
    result: list[tuple[str, str]] = []
    for item in re.split(r"[;,/]| and | und | és ", raw or ""):
        label = item.strip()
        if not label:
            continue
        lower = label.lower()
        if re.fullmatch(r"[a-z]{2,3}", lower):
            code = lower
        else:
            code = LANGUAGE_CODES.get(lower, "")
        result.append((code, label))
    return result


def parse_image_files(raw: str | None) -> list[tuple[str, str]]:
    """
    Parse "IMG_0231 = 1r; IMG_0232 = 1v" into (file name, page label) pairs.
    Items without "=" get an empty page label.
    """
    result: list[tuple[str, str]] = []
    for item in re.split(r"[;\n]", raw or ""):
        if not item.strip():
            continue
        name, _, label = item.partition("=")
        result.append((name.strip(), label.strip()))
    return result


def parse_name_and_date(raw: str | None) -> tuple[str, str]:
    """Split "Surname, Forename, 2026-10-02" into the name and a trailing ISO date, if any."""
    text = (raw or "").strip()
    match = re.search(r"[,;\s]+(\d{4}(-\d{2}(-\d{2})?)?)\s*$", text)
    if match:
        return text[: match.start()].strip(), match.group(1)
    return text, ""
