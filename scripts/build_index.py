"""
Write pte-plugins.json, the index of the plugins in this repository, from the plugin packages.

For each plugins/<name>/ the index lists the plugin id (the ``pte.plugins`` entry point name),
the distribution and module name, the version (from pte-plugin.json), the description, the
plugins it requires (its pte-plugin-* dependencies) and its other Python dependencies. The
editor's plugin manager reads the index to list the plugins for installation; a plugin whose
dependencies are not installed in the editor's environment cannot be installed at runtime.

Usage:
    python scripts/build_index.py           # write pte-plugins.json
    python scripts/build_index.py --check   # exit 1 if pte-plugins.json is outdated
"""

import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = REPO_ROOT / "pte-plugins.json"
REPOSITORY = "https://github.com/mpilhlt/pte-plugins"
ENTRY_POINT_GROUP = "pte.plugins"


def read_plugin(plugin_dir: Path) -> dict[str, object]:
    """Index entry of one plugin package directory."""
    project = tomllib.loads((plugin_dir / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    (plugin_id, module), = project["entry-points"][ENTRY_POINT_GROUP].items()
    manifest = json.loads((plugin_dir / "src" / module / "pte-plugin.json").read_text(encoding="utf-8"))
    dependencies = list(project.get("dependencies", []))
    requires = [re.split(r"[\s<>=!~\[;]", dep, maxsplit=1)[0] for dep in dependencies]
    return {
        "id": plugin_id,
        "package": project["name"],
        "module": module,
        "path": plugin_dir.relative_to(REPO_ROOT).as_posix(),
        "version": manifest["version"],
        "description": project.get("description", ""),
        "requires": [dep for dep in requires if dep.startswith("pte-plugin-")],
        "dependencies": [dep for dep, name in zip(dependencies, requires) if not name.startswith("pte-plugin-")],
        "engines": manifest.get("engines", {}),
    }


def build_index() -> str:
    """The contents of pte-plugins.json."""
    plugins = [read_plugin(d) for d in sorted((REPO_ROOT / "plugins").iterdir()) if (d / "pyproject.toml").is_file()]
    packages = {p["package"]: p["id"] for p in plugins}
    for plugin in plugins:
        plugin["requires"] = [packages[dep] for dep in plugin["requires"]]  # type: ignore[union-attr]
    return json.dumps({"repository": REPOSITORY, "plugins": plugins}, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    content = build_index()
    if "--check" in sys.argv:
        if not INDEX_FILE.is_file() or INDEX_FILE.read_text(encoding="utf-8") != content:
            print("pte-plugins.json is outdated, run: python scripts/build_index.py", file=sys.stderr)
            return 1
        return 0
    INDEX_FILE.write_text(content, encoding="utf-8")
    print(f"Wrote {INDEX_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
