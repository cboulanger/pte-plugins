"""
Archival edition extractor.

Input: a PDF made of a filled-in Document Description Form followed by the
photographs of an archival document. Output: a TEI document whose header is
populated from the form and whose text is a diplomatic transcription of the
photographs, made page by page by a multimodal model.
"""

import datetime
import logging
from pathlib import Path
from typing import Any, Optional

import pymupdf
from lxml import etree

from fastapi_app.lib.extraction import BaseExtractor
from fastapi_app.lib.llm import LLMProvider
from fastapi_app.lib.secrets import require_user_secret
from fastapi_app.plugins.anthropic_llm.llm_provider import AnthropicLLMProvider
from fastapi_app.lib.utils.annotation_rules_utils import AnnotationRuleRef
from fastapi_app.lib.utils.config_utils import get_config
from fastapi_app.lib.utils.debug_utils import log_extraction_response
from fastapi_app.lib.utils.doi_utils import encode_for_xml_id
from fastapi_app.lib.utils.tei_utils import (
    create_encoding_desc_with_extractor,
    create_revision_desc_with_status,
    create_schema_processing_instruction,
    create_tei_document,
    get_file_id_from_options,
    serialize_tei_with_formatted_header,
)

from .config import (
    ANNOTATION_GUIDES,
    EXTRACTOR_ID,
    FORM_OPTIONS,
    GUIDELINES_MARKDOWN_URL,
    MAX_SCANNED_FORM_PAGES,
    NAVIGATION_XPATH,
    SECRET_SERVICE_ID,
    SECRET_SERVICE_LABEL,
    REPOSITORY_URL,
    SCHEMA_URL,
    VARIANT_ID,
    get_authority,
    get_model,
)
from .form_parser import build_form_prompt, count_text_form_pages, parse_form_response, parse_form_tables
from .header_builder import build_class_decl, build_facsimile, build_scaffold_header, main_language
from .transcriber import plain_text, render_page_image, transcribe_page

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "0.1.0"
LOCAL_SCHEMA = Path(__file__).parent / "static" / "schema" / "tei-archival.rng"

CONTEXT_FIELDS: list[tuple[str, str]] = [
    ("doc_type", "Document type"),
    ("title", "Title"),
    ("supplied_title", "Descriptive title"),
    ("authors", "Author(s)"),
    ("date", "Date"),
    ("place", "Place"),
    ("languages", "Languages"),
    ("writing", "Writing"),
    ("senders", "Sender"),
    ("addressees", "Addressee"),
    ("names", "Names mentioned"),
    ("later_additions", "Later additions"),
]


def build_context(fields: dict[str, str]) -> str:
    """Summary of the description form given to the model as context for transcription."""
    lines = [f"- {label}: {fields[key]}" for key, label in CONTEXT_FIELDS if fields.get(key)]
    return "\n".join(lines) if lines else "- (no description available)"


class ArchivalEditionExtractor(BaseExtractor):
    """Header from the description form, transcription of the photographs by a multimodal model."""

    @classmethod
    def get_info(cls) -> dict[str, Any]:
        """Return information about the archival edition extractor."""
        return {
            "id": EXTRACTOR_ID,
            "name": "Archival edition (description form + transcription)",
            "description": "Reads the Document Description Form at the start of the PDF into the TEI header and transcribes the photographed pages with the selected model",
            "input": ["pdf"],
            "output": ["tei-document"],
            "uses_inference_model": False,
            "variants": [VARIANT_ID],
            "options": FORM_OPTIONS,
            "navigation_xpath": NAVIGATION_XPATH,
            "annotationGuides": ANNOTATION_GUIDES,
        }

    @classmethod
    def is_available(cls) -> bool:
        """Always available: each user supplies the Anthropic key, which is requested when it is missing."""
        return True

    @staticmethod
    def _resolve_model(options: dict[str, Any]) -> tuple[LLMProvider, str]:
        """
        The provider and model to use: Claude with the key of the user who runs the extraction.

        The key comes from the editor's per-user secret store, so the cost is billed to that user.

        Raises:
            MissingSecretError: If the user has not stored an Anthropic key yet; the editor then asks for it
        """
        api_key = require_user_secret(options.get("username"), SECRET_SERVICE_ID)
        provider = AnthropicLLMProvider(id="archival-edition-anthropic", label=SECRET_SERVICE_LABEL, api_key=api_key)
        return provider, get_model(options)

    async def _read_form(self, doc: pymupdf.Document, options: dict[str, Any]) -> tuple[int, dict[str, str]]:
        """
        Read the description form: from the text layer if there is one, else with the model.

        Returns:
            (number of form pages, field id -> entry)
        """
        requested = str(options.get("form_pages") or "").strip()
        form_pages = int(requested) if requested.isdigit() else count_text_form_pages(doc)
        if form_pages > 0 and count_text_form_pages(doc) > 0:
            return form_pages, parse_form_tables(doc, form_pages)

        logger.info("Description form has no text layer, reading it with the model")
        provider, model_id = self._resolve_model(options)
        page_count = min(doc.page_count, max(form_pages, MAX_SCANNED_FORM_PAGES))
        images = [render_page_image(doc[i]) for i in range(page_count)]
        response = await provider.chat_completion_with_images(
            model_id, "You read filled-in forms exactly.", build_form_prompt(), images, temperature=0.0
        )
        detected_pages, fields = parse_form_response(response)
        return (form_pages or detected_pages), fields

    async def extract(self, pdf_path: Optional[str] = None, xml_content: Optional[str] = None,
                      options: Optional[dict[str, Any]] = None) -> str:
        """
        Build the TEI document for one archival document.

        Args:
            pdf_path: Path to the PDF (description form + photographs)
            xml_content: Not used
            options: Extraction options (variant_id, transcribe, form_pages, provider_id, model_id, username, ...)

        Returns:
            Complete TEI document as XML string
        """
        if not pdf_path:
            raise ValueError("A PDF is required for the archival edition extractor")
        options = options or {}
        with pymupdf.open(pdf_path) as doc:
            return await self._extract(doc, pdf_path, options)

    async def _extract(self, doc: pymupdf.Document, pdf_path: str, options: dict[str, Any]) -> str:
        """Build the TEI document from the opened PDF, see extract()."""
        transcribe = str(options.get("transcribe") or "yes").lower() != "no"
        variant_id = options.get("variant_id") or VARIANT_ID
        form_pages, fields = await self._read_form(doc, options)
        photo_pages = list(range(form_pages, doc.page_count))
        logger.info("Archival edition: %d form page(s), %d photographed page(s), %d form fields", form_pages, len(photo_pages), len(fields))

        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        file_id = get_file_id_from_options(options, pdf_path)

        tei_doc = create_tei_document()
        tei_header, doc_type = build_scaffold_header(fields, encode_for_xml_id(file_id), get_authority())
        tei_doc.append(tei_header)

        provider: LLMProvider | None = None
        model_id = ""
        if transcribe and photo_pages:
            provider, model_id = self._resolve_model(options)
            title_stmt = tei_header.find("fileDesc/titleStmt")
            assert title_stmt is not None
            resp_stmt = etree.SubElement(title_stmt, "respStmt")
            etree.SubElement(resp_stmt, "resp").text = "automatic transcription"
            etree.SubElement(resp_stmt, "orgName").text = f"{provider.label} / {model_id}"

        editorial_decl: list[AnnotationRuleRef] = [{
            "category": "primary",
            "n": "Archival edition annotation guidelines",
            "refs": [{"target": GUIDELINES_MARKDOWN_URL, "content_type": "markdown", "subtype": "human"}],
        }]
        labels = [("form-pages", str(form_pages))]
        if provider is not None:
            labels += [("provider", provider.label), ("model", model_id)]
        encoding_desc = create_encoding_desc_with_extractor(
            timestamp=timestamp,
            extractor_name="Archival edition",
            extractor_ident=EXTRACTOR_ID,
            extractor_version=PLUGIN_VERSION,
            variant_id=variant_id,
            additional_labels=labels,
            refs=[REPOSITORY_URL, SCHEMA_URL],
            editorial_decl_entries=editorial_decl,
        )
        encoding_desc.append(build_class_decl())
        tei_header.insert(1, encoding_desc)

        facsimile, surfaces = build_facsimile(fields, len(photo_pages))
        if surfaces:
            tei_doc.append(facsimile)

        text = etree.SubElement(tei_doc, "text")
        language = main_language(fields)
        if language:
            text.set("{http://www.w3.org/XML/1998/namespace}lang", language)
        div = etree.SubElement(etree.SubElement(text, "body"), "div", type=doc_type.category)

        failed_pages: list[str] = []
        previous_text = ""
        context = build_context(fields)
        for index, page_number in enumerate(photo_pages):
            surface_id, label = surfaces[index]
            etree.SubElement(div, "pb", n=label, facs=f"#{surface_id}")
            if provider is None:
                continue
            page = await transcribe_page(
                provider, model_id, render_page_image(doc[page_number]), label,
                index + 1, len(photo_pages), context, previous_text,
            )
            log_extraction_response(EXTRACTOR_ID, pdf_path, page.raw, f".page-{index + 1}.xml")
            if page.failed:
                failed_pages.append(label)
            for element in page.elements:
                div.append(element)
            previous_text = plain_text(page.elements)
        if not len(div):
            etree.SubElement(div, "ab", type="blank")

        description = "Header from the description form"
        if provider is not None:
            description += f"; transcription by {provider.label} / {model_id}"
        if failed_pages:
            description += f"; markup of page(s) {', '.join(failed_pages)} could not be parsed and was removed"
        extraction_label = get_config().get("annotation.lifecycle.change-descriptions", default=["Extraction"])[0]
        tei_header.append(create_revision_desc_with_status(timestamp, "extraction", description, label=extraction_label))

        result = serialize_tei_with_formatted_header(tei_doc, [create_schema_processing_instruction(SCHEMA_URL)])
        self._log_validation(result)
        return result

    @staticmethod
    def _log_validation(xml: str) -> None:
        """Validate the result against the bundled schema and log problems (the editor shows them too)."""
        try:
            schema = etree.RelaxNG(etree.parse(str(LOCAL_SCHEMA)))
            document = etree.fromstring(xml.encode("utf-8"))
            if not schema.validate(document):
                for error in list(schema.error_log)[:20]:
                    logger.warning("Archival edition output: line %d: %s", error.line, error.message)
        except (etree.XMLSyntaxError, etree.RelaxNGParseError) as e:
            logger.warning("Could not validate archival edition output: %s", e)
