"""
Write examples/sample-letter.tei.xml: the extractor's output for the sample PDF,
with the canned transcription of the test suite's fake model instead of a real one.

Usage (from the repository root, PTE_ROOT pointing to a PDF-TEI-Editor checkout):
    uv run --project "$PTE_ROOT" python scripts/make_example_tei.py
"""

import asyncio
import re
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
PTE_ROOT = Path(os.environ.get("PTE_ROOT", REPO_ROOT.parent / "pdf-tei-editor")).resolve()
sys.path[:0] = [str(PTE_ROOT), str(REPO_ROOT / "plugins")]

from fastapi_app.lib.llm import LLMProviderRegistry  # noqa: E402

from archival_edition import extractor  # noqa: E402
from archival_edition.tests.test_extractor import FakeProvider  # noqa: E402

PDF = REPO_ROOT / "plugins" / "archival_edition" / "tests" / "fixtures" / "sample-letter.pdf"
OUTPUT = REPO_ROOT / "examples" / "sample-letter.tei.xml"


def main() -> int:
    provider = FakeProvider()
    provider.label = "Example provider"
    LLMProviderRegistry.get_instance().register(provider)
    config = MagicMock()
    config.get.return_value = ["Extraction"]
    with patch.object(extractor, "check_model_access", lambda *args: None), \
            patch.object(extractor, "get_authority", lambda: "Example project"), \
            patch.object(extractor, "log_extraction_response", lambda *args, **kwargs: None), \
            patch.object(extractor, "get_config", lambda: config):
        xml = asyncio.run(extractor.ArchivalEditionExtractor().extract(
            pdf_path=str(PDF),
            options={"provider_id": provider.id, "model_id": "example-model", "stable_id": "sample-letter"},
        ))
    # Fixed timestamp so that the example only changes when the output does
    xml = re.sub(r'when="\d{4}-\d{2}-\d{2}T[^"]+"', 'when="2026-10-20T00:00:00Z"', xml)
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(xml + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
