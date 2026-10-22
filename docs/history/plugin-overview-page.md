# Plugin overview page on GitHub Pages

Requested by Christian on 2026-10-22: a CI action that generates an overview page for the pte-plugins GitHub Pages site, listing all plugins with their info and a link to their README, rebuilt on every commit to `main`.

## Starting point

- Pages is enabled with source "GitHub Actions". `.github/workflows/pages.yml` deployed only `plugins/archival-edition/docs` to `/archival-edition/`, and ran only when `plugins/*/docs/**` changed. The schema and guidelines URLs under `/archival-edition/` are recorded in TEI documents and loaded by the editor, so they must stay stable.
- `pte-plugins.json` (built by `scripts/build_index.py`, checked in CI) holds id, package, module, path, version, description, required plugins, Python dependencies and engines. Each `pte-plugin.json` additionally holds the `readme` URL.

## Implementation

- `scripts/build_site.py [OUTPUT_DIR]` (stdlib only) writes the site into `_site`:
  - `index.html`: summary table, then one section per plugin (anchor `#<id>`) with version, description, links (README from the manifest's `readme` field, source, documentation if the plugin has `docs/`, releases filtered by `<id>-v`), package, module, engine ranges, required plugins (linked), Python dependencies, any further manifest fields, and the `uv pip install` command. Self-contained HTML/CSS, light and dark scheme, no horizontal scroll at phone width.
  - `pte-plugins.json`: copy of the index.
  - `<plugin directory>/`: the `docs/` directory of every plugin that has one (generalizes the former hardcoded archival-edition copy; the archival-edition URLs are unchanged).
- `pages.yml` extends the existing workflow rather than adding a second one, because a Pages deployment replaces the whole site: two workflows would overwrite each other. It now runs on every push to `main` (no path filter), checks the index with `build_index.py --check`, and assembles the site with `build_site.py`.
- `tests/test_site.py` builds the site into a temporary directory and checks that every plugin is listed with its README link and that the archival-edition files are published at their URLs.
- README: section on the overview page.

## Notes

- The page is generated from `main`, so it shows the version in the manifests, which can be ahead of the latest release tag.
- `npm run build` does not apply: this repository has no build step.
