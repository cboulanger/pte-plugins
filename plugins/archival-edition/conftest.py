"""
pytest setup: tests run in the Python environment of a PDF-TEI-Editor checkout.

Set PTE_ROOT to the checkout (default: ../pdf-tei-editor) and run
    uv run --project "$PTE_ROOT" python -m pytest
from this directory.
"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PTE_ROOT = Path(os.environ.get("PTE_ROOT", REPO_ROOT.parent / "pdf-tei-editor")).resolve()

for path in (PTE_ROOT, REPO_ROOT / "plugins"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
