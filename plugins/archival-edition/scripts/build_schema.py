"""
Flatten the composable RNG schema in schema/ into a single file.

For each top-level schema in schema/ (not shared/):
  1. Replace each <include href="..."/> with the definitions of the included grammar.
  2. Abort if a <define name="..."> occurs more than once.
  3. Check that lxml can compile the result as RELAX NG.
  4. Write it to docs/schema/ and to the plugin's static/schema/ directory.

Usage: uv run python scripts/build_schema.py [--check]
  --check  only verify that the generated files are up to date
"""

import sys
from collections import Counter
from pathlib import Path

from lxml import etree

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_SRC = REPO_ROOT / "schema"
OUTPUT_DIRS = [
    REPO_ROOT / "docs" / "schema",
    REPO_ROOT / "plugins" / "archival_edition" / "static" / "schema",
]

RNG_NS = "http://relaxng.org/ns/structure/1.0"
HEADER = (
    "AUTO-GENERATED - do not edit directly.\n"
    "     Source:      schema/{name}\n"
    "     Regenerate:  uv run python scripts/build_schema.py "
)


def flatten(path: Path) -> etree._ElementTree:
    """Return the schema at path with all includes inlined."""
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=False)
    tree = etree.parse(str(path), parser)
    root = tree.getroot()
    for include in root.findall(f"{{{RNG_NS}}}include"):
        included = flatten(path.parent / include.get("href", "")).getroot()
        position = root.index(include)
        root.remove(include)
        for offset, child in enumerate(c for c in included if not isinstance(c, etree._Comment)):
            root.insert(position + offset, child)
    return tree


def build(path: Path) -> bytes:
    """Flatten, check and serialize one top-level schema."""
    tree = flatten(path)
    root = tree.getroot()
    names = Counter(d.get("name") for d in root.iter(f"{{{RNG_NS}}}define"))
    duplicates = sorted(n for n, count in names.items() if count > 1)
    if duplicates:
        raise SystemExit(f"{path.name}: duplicate defines: {', '.join(duplicates)}")
    etree.RelaxNG(tree)
    body = etree.tostring(root, encoding="unicode", pretty_print=True)
    header = HEADER.format(name=path.name)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!-- {header}-->\n{body}'.encode("utf-8")


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale: list[Path] = []
    for path in sorted(SCHEMA_SRC.glob("*.rng")):
        content = build(path)
        for out_dir in OUTPUT_DIRS:
            target = out_dir / path.name
            if check:
                if not target.exists() or target.read_bytes() != content:
                    stale.append(target)
                continue
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            print(f"Wrote {target.relative_to(REPO_ROOT)}")
    if stale:
        print("Generated schemas are out of date, run scripts/build_schema.py:", file=sys.stderr)
        for target in stale:
            print(f"  {target.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
