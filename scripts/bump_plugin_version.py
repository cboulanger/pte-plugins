"""
Write a new version into a plugin's pte-plugin.json (the single source of its package version).

Usage:
    python scripts/bump_plugin_version.py <plugin-path> <version>

Example:
    python scripts/bump_plugin_version.py plugins/grobid 1.2.0
"""

import json
import sys
import tomllib
from pathlib import Path


def manifest_path(plugin_dir: Path) -> Path:
    """The pte-plugin.json of the plugin package in ``plugin_dir``."""
    project = tomllib.loads((plugin_dir / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    (module,) = project["entry-points"]["pte.plugins"].values()
    return plugin_dir / "src" / module / "pte-plugin.json"


def bump_version(plugin_dir: Path, version: str) -> None:
    """Set ``version`` in the plugin's manifest, keeping its other fields and formatting."""
    path = manifest_path(plugin_dir)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["version"] = version
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    bump_version(Path(sys.argv[1]), sys.argv[2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
