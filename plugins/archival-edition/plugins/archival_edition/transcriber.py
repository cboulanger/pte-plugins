"""
Page-by-page transcription of the photographed pages with a multimodal model.

Each page is rendered to a JPEG and sent on its own, together with what the
description form says about the document and the end of the previous page's
transcription, so that the model can continue paragraphs across page breaks.
The answer is a sequence of TEI block elements, which is parsed and, if it is
not well-formed, sent back once for repair.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from lxml import etree

from fastapi_app.lib.llm import LLMImage, LLMProvider

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompts"
MAX_IMAGE_EDGE_PX = 2000
JPEG_QUALITY = 85
PREVIOUS_TAIL_CHARS = 600

REPAIR_SYSTEM_PROMPT = (
    "You fix malformed TEI XML fragments. Return the corrected fragment only: the same text and markup, "
    "with tags properly nested and closed and special characters escaped. No explanations, no code fences."
)


@dataclass
class PageTranscription:
    """The transcription of one page as TEI block elements (without namespace)."""

    elements: list[etree._Element]
    raw: str
    repaired: bool = False
    failed: bool = False


def load_prompt(name: str) -> str:
    """Read a prompt template from the prompts/ directory."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def render_page_image(page: pymupdf.Page) -> LLMImage:
    """
    Render a PDF page to a JPEG whose longer edge is at most MAX_IMAGE_EDGE_PX.

    Archive photos are often 12+ megapixels, more than vision models use and
    larger than their per-image size limits.
    """
    longest_edge_pt = max(page.rect.width, page.rect.height)
    zoom = min(MAX_IMAGE_EDGE_PX / longest_edge_pt, 4.0)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
    return {"data": pixmap.tobytes("jpeg", jpg_quality=JPEG_QUALITY), "media_type": "image/jpeg"}


def _strip_fences(text: str) -> str:
    """Remove code fences, XML declarations and namespace declarations from a model answer."""
    text = re.sub(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$", "", text.strip())
    text = re.sub(r"<\?xml[^>]*\?>", "", text)
    return re.sub(r'\s+xmlns(:\w+)?="[^"]*"', "", text).strip()


def parse_fragment(text: str) -> list[etree._Element]:
    """
    Parse a sequence of TEI elements without namespace.

    Raises:
        etree.XMLSyntaxError: If the fragment is not well-formed
    """
    wrapper = etree.fromstring(f'<wrapper xmlns:xml="http://www.w3.org/XML/1998/namespace">{_strip_fences(text)}</wrapper>')
    if wrapper.text and wrapper.text.strip():
        raise etree.XMLSyntaxError(f"Text outside of elements: {wrapper.text.strip()[:60]}", None, 0, 0)  # type: ignore[call-arg]
    return list(wrapper)


def plain_text(elements: list[etree._Element]) -> str:
    """The text content of transcribed elements, with line breaks for lb."""
    parts: list[str] = []
    for elem in elements:
        for node in elem.iter():
            if node.tag == "lb":
                parts.append("\n")
            if node.text:
                parts.append(node.text)
            if node is not elem and node.tail:
                parts.append(node.tail)
        parts.append("\n")
    return re.sub(r"[ \t]+", " ", "".join(parts)).strip()


def fallback_elements(raw: str) -> list[etree._Element]:
    """Wrap an answer that could not be parsed as escaped text with a note for the annotator."""
    ab = etree.Element("ab", type="unparsed")
    ab.text = re.sub(r"<[^>]+>", "", raw).strip()
    note = etree.Element("note", type="transcription-error")
    note.text = "The model's transcription of this page was not well-formed XML; the markup was removed."
    return [note, ab]


async def transcribe_page(
    provider: LLMProvider,
    model_id: str,
    image: LLMImage,
    page_label: str,
    page_number: int,
    page_count: int,
    context: str,
    previous_text: str,
) -> PageTranscription:
    """
    Transcribe one page.

    Args:
        provider: LLM provider with image input
        model_id: Model to use
        image: The rendered page
        page_label: Page label from the form (1r, 1v, ...)
        page_number: 1-based page number among the photographed pages
        page_count: Number of photographed pages
        context: Summary of the description form for the model
        previous_text: Plain text of the previous page's transcription, if any

    Returns:
        The parsed transcription; failed=True if it could not be parsed even after repair
    """
    previous = ""
    if previous_text:
        tail = previous_text[-PREVIOUS_TAIL_CHARS:]
        previous = f"The previous page ended with:\n---\n{tail}\n---"
    user_prompt = load_prompt("transcription-user.md").format(
        page_label=page_label,
        page_number=page_number,
        page_count=page_count,
        context=context,
        previous=previous,
    )
    raw = await provider.chat_completion_with_images(
        model_id, load_prompt("transcription-system.md"), user_prompt, [image], temperature=0.0
    )
    try:
        return PageTranscription(elements=parse_fragment(raw), raw=raw)
    except etree.XMLSyntaxError as error:
        parse_error = str(error)
        logger.warning("Transcription of page %s is not well-formed (%s), asking for a repair", page_label, parse_error)

    repaired = await provider.chat_completion(
        model_id, REPAIR_SYSTEM_PROMPT, f"Parser error: {parse_error}\n\nFragment:\n{raw}", temperature=0.0
    )
    try:
        return PageTranscription(elements=parse_fragment(repaired), raw=repaired, repaired=True)
    except etree.XMLSyntaxError:
        logger.warning("Repair of page %s failed, keeping the text without markup", page_label)
        return PageTranscription(elements=fallback_elements(raw), raw=raw, failed=True)
