"""
Assemble the GitHub Pages site of this repository, https://mpilhlt.github.io/pte-plugins/:

- index.html: overview of all plugins, from pte-plugins.json and each plugin's pte-plugin.json,
  with links to the plugin's README, source, documentation and releases
- pte-plugins.json: a copy of the index
- <plugin>/: the plugin's docs/ directory, for plugins that have one (e.g. the archival-edition
  schema and guidelines, whose URLs are recorded in TEI documents and must not change)

Usage:
    python scripts/build_site.py [OUTPUT_DIR]   # default: _site
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = REPO_ROOT / "pte-plugins.json"
# Manifest fields shown in the overview anyway
SHOWN_MANIFEST_FIELDS = {"version", "readme", "engines"}

STYLE = """
:root { --fg: #1f2328; --muted: #59636e; --bg: #ffffff; --card: #f6f8fa; --border: #d1d9e0; --link: #0969da; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #f0f6fc; --muted: #9198a1; --bg: #0d1117; --card: #151b23; --border: #3d444d; --link: #4493f8; }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 64rem; margin: 0 auto; padding: 2rem 1rem 4rem; }
a { color: var(--link); }
h1 { margin: 0 0 .5rem; font-size: 2rem; }
h2 { margin: 2.5rem 0 1rem; font-size: 1.4rem; }
h3 { margin: 0; font-size: 1.15rem; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .875em; }
.muted { color: var(--muted); }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; vertical-align: top; padding: .4rem .6rem; border-bottom: 1px solid var(--border); }
th { font-weight: 600; }
td:first-child { white-space: nowrap; }
.plugin { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin: 0 0 1rem; scroll-margin-top: 1rem; }
.plugin header { display: flex; flex-wrap: wrap; align-items: baseline; gap: .25rem 1rem; }
.plugin p { margin: .5rem 0; }
.links { display: flex; flex-wrap: wrap; gap: .25rem 1rem; margin: .5rem 0; }
dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: .25rem 1rem; margin: .75rem 0 0; }
dt { color: var(--muted); }
dd { margin: 0; overflow-wrap: anywhere; }
@media (max-width: 36rem) {
  dl { grid-template-columns: minmax(0, 1fr); gap: 0; }
  dd { margin-bottom: .5rem; }
}
pre { margin: 0; padding: .5rem .75rem; overflow-x: auto; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; }
footer { margin-top: 3rem; font-size: .875rem; }
"""


def load_plugins() -> tuple[str, list[dict[str, object]]]:
    """Repository URL and index entries, each with its manifest under "manifest"."""
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    plugins = index["plugins"]
    for plugin in plugins:
        manifest_file = REPO_ROOT / plugin["path"] / "src" / plugin["module"] / "pte-plugin.json"
        plugin["manifest"] = json.loads(manifest_file.read_text(encoding="utf-8"))
    return index["repository"], plugins


def docs_dir(plugin: dict[str, object]) -> Path:
    """The plugin's docs/ directory, published at <site>/<plugin directory name>/."""
    return REPO_ROOT / str(plugin["path"]) / "docs"


def code_list(items: list[str]) -> str:
    """Comma-separated list of code items, or a dash."""
    return ", ".join(f"<code>{escape(item)}</code>" for item in items) or '<span class="muted">none</span>'


def render_plugin(plugin: dict[str, object], repository: str) -> str:
    """The section of one plugin."""
    manifest: dict[str, object] = plugin["manifest"]  # type: ignore[assignment]
    plugin_id = str(plugin["id"])
    path = str(plugin["path"])
    source = f"{repository}/tree/main/{path}"
    readme = str(manifest.get("readme") or f"{source}#readme")
    releases = f"{repository}/releases?q={plugin_id}-v&expanded=true"
    links = [f'<a href="{escape(readme)}">README</a>', f'<a href="{escape(source)}">Source</a>']
    if docs_dir(plugin).is_dir():
        links.append(f'<a href="{escape(Path(path).name)}/">Documentation</a>')
    links.append(f'<a href="{escape(releases)}">Releases</a>')

    engines: dict[str, str] = plugin.get("engines") or {}  # type: ignore[assignment]
    requires = [f'<a href="#{escape(r)}"><code>{escape(r)}</code></a>' for r in plugin["requires"]]  # type: ignore[union-attr]
    install = f'uv pip install "{plugin["package"]} @ git+{repository}#subdirectory={path}"'
    rows = [
        ("Package", f"<code>{escape(str(plugin['package']))}</code>"),
        ("Module", f"<code>{escape(str(plugin['module']))}</code>"),
        ("Editor versions", f"<code>{escape(engines.get('pte', '*'))}</code>"),
        ("Plugin API", f"<code>{escape(engines.get('pte-plugin-api', '*'))}</code>"),
        ("Requires plugins", ", ".join(requires) or '<span class="muted">none</span>'),
        ("Python dependencies", code_list(plugin["dependencies"])),  # type: ignore[arg-type]
    ]
    for key, value in manifest.items():
        if key not in SHOWN_MANIFEST_FIELDS:
            rows.append((key, f"<code>{escape(json.dumps(value, ensure_ascii=False))}</code>"))
    rows.append(("Install", f"<pre><code>{escape(install)}</code></pre>"))
    details = "\n".join(f"      <dt>{escape(k)}</dt><dd>{v}</dd>" for k, v in rows)
    return f"""  <section class="plugin" id="{escape(plugin_id)}">
    <header>
      <h3><a href="#{escape(plugin_id)}">{escape(plugin_id)}</a></h3>
      <span class="muted">version {escape(str(plugin["version"]))}</span>
    </header>
    <p>{escape(str(plugin["description"]))}</p>
    <div class="links">{" ".join(links)}</div>
    <dl>
{details}
    </dl>
  </section>"""


def render_index(repository: str, plugins: list[dict[str, object]], generated: str) -> str:
    """The contents of index.html."""
    summary = "\n".join(
        f'      <tr><td><a href="#{escape(str(p["id"]))}">{escape(str(p["id"]))}</a></td>'
        f'<td>{escape(str(p["version"]))}</td><td>{escape(str(p["description"]))}</td></tr>'
        for p in plugins
    )
    sections = "\n".join(render_plugin(p, repository) for p in plugins)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PDF-TEI-Editor plugins</title>
  <style>{STYLE}</style>
</head>
<body>
<main>
  <h1>PDF-TEI-Editor plugins</h1>
  <p>Plugins for the <a href="https://github.com/mpilhlt/pdf-tei-editor">PDF-TEI-Editor</a> from the <a href="{escape(repository)}">pte-plugins</a> repository. Administrators can install released plugins in the editor's plugin manager, or install a plugin into the editor's Python environment with the command shown for it. The same information is available as <a href="pte-plugins.json">pte-plugins.json</a>.</p>

  <h2>Overview</h2>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Plugin</th><th>Version</th><th>Description</th></tr></thead>
      <tbody>
{summary}
      </tbody>
    </table>
  </div>

  <h2>Plugins</h2>
{sections}

  <footer class="muted">Generated {escape(generated)} from <a href="{escape(repository)}/blob/main/pte-plugins.json">pte-plugins.json</a>.</footer>
</main>
</body>
</html>
"""


def build_site(out_dir: Path) -> None:
    """Write the site into out_dir, which is emptied first."""
    repository, plugins = load_plugins()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for plugin in plugins:
        if docs_dir(plugin).is_dir():
            shutil.copytree(docs_dir(plugin), out_dir / Path(str(plugin["path"])).name)
    shutil.copyfile(INDEX_FILE, out_dir / "pte-plugins.json")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (out_dir / "index.html").write_text(render_index(repository, plugins, generated), encoding="utf-8")


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "_site"
    build_site(out_dir.resolve())
    print(f"Wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
