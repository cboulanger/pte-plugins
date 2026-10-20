"""
Annotation tags for the visual (annotation) mode of the XML editor.

The editor shows its visual mode for a variant only when an extractor declares annotation tags for that
variant (`annotationTags` in the extractor info). The tags are generated from the plugin's own schema: the
elements allowed in the transcription of a paragraph, plus the alternatives grouped in `choice` and `subst`
(`abbr`/`expan`, `sic`/`corr`, `orig`/`reg`), without the empty layout milestones, which are not wrapped
around text.
"""

import copy
import hashlib
from pathlib import Path
from typing import TypedDict

from fastapi_app.lib.utils.relaxng_to_codemirror import RelaxNGParser, TagAttribute, TagVariant

# Element whose content model holds the inline transcription markup
ROOT_TAG = "p"
# Empty milestone elements: positions, not spans of text
EXCLUDE = {"lb", "pb", "cb", "milestone"}
# Elements whose children get their own badge too
GROUPING_TAGS = ("choice", "subst")

# The palette of the editor's GROBID annotation chips, light enough for the dark badge label
PALETTE: list[str] = [
    "#89dceb", "#f38ba8", "#89b4fa", "#cba6f7", "#94e2d5", "#f9e2af",
    "#a6e3a1", "#f5c2e7", "#74c7ec", "#a6adc8", "#f2cdcd", "#eba0ac",
    "#b4befe", "#bac2de", "#fab387", "#f5e0dc", "#d18455",
]


class AnnotationTag(TypedDict):
    """One entry of the extractor info's `annotationTags` list."""
    tag: str
    label: str
    color: str
    description: str | None
    attributes: list[TagAttribute]
    variants: list[TagVariant]
    bareAllowed: bool
    childTags: list[str]


_cache: dict[Path, tuple[float, list[AnnotationTag]]] = {}


def _color_for_tag(tag_name: str, taken: set[str]) -> str:
    """Stable color per tag name (sha256, not the per-process `hash()`), the next free one on a collision."""
    index = int(hashlib.sha256(tag_name.encode("utf-8")).hexdigest(), 16) % len(PALETTE)
    for offset in range(len(PALETTE)):
        color = PALETTE[(index + offset) % len(PALETTE)]
        if color not in taken:
            return color
    return PALETTE[index]


def generate_annotation_tags(schema_path: Path) -> list[AnnotationTag]:
    """The annotation tags derived from the schema at `schema_path`; empty if the file does not exist."""
    if not schema_path.is_file():
        return []
    mtime = schema_path.stat().st_mtime
    cached = _cache.get(schema_path)
    if cached is not None and cached[0] == mtime:
        return copy.deepcopy(cached[1])

    parser = RelaxNGParser(include_global_attrs=False, sort_alphabetically=True)
    parser.parse_file(str(schema_path))
    definitions = parser.extract_tag_definitions(ROOT_TAG, EXCLUDE)
    for group in GROUPING_TAGS:
        children = definitions[group]["children"] if group in definitions else []
        for child in children:
            if child in definitions or child in EXCLUDE:
                continue
            child_definition = parser.extract_tag_definitions(child, EXCLUDE).get(child)
            if child_definition is not None:
                definitions[child] = child_definition

    tags: list[AnnotationTag] = []
    taken: set[str] = set()
    for name in sorted(definitions):
        data = definitions[name]
        color = _color_for_tag(name, taken)
        taken.add(color)
        tags.append({
            "tag": name,
            "label": name,
            "color": color,
            "description": data["description"],
            "attributes": data["attributes"],
            "variants": data["variants"],
            "bareAllowed": data["bareAllowed"],
            "childTags": [c for c in data["children"] if c not in EXCLUDE],
        })
    _cache[schema_path] = (mtime, tags)
    return copy.deepcopy(tags)
