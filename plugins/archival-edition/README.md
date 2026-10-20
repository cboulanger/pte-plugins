# pte-edition-plugin

An external plugin for the [PDF-TEI-Editor](https://github.com/mpilhlt/pdf-tei-editor) for editing archival documents (letters, postcards, telegrams, conference programs, manuscripts of papers and talks, notes), and an example of how to extend the editor without changing its source code.

It contains:

- **an extractor** (`archival-edition`) for PDFs made of a filled-in [Document Description Form](plugins/archival_edition/tests/fixtures/document-description-form.docx) followed by photographs of the document. The form is read into the TEI header. The photographs are transcribed page by page by Claude with the user's own API key, diplomatically, in all languages the model supports;
- **a schema**, [tei-archival.rng](docs/schema/tei-archival.rng): a lightweight RELAX NG schema written from scratch (no ODD), derived from the schemas of [fossil](https://github.com/mpilhlt/fossil) and extended for archival material (`msDesc`, `correspDesc`, `facsimile`, diplomatic transcription);
- **annotation guidelines**, [docs/guidelines.md](docs/guidelines.md), which also document how each form field maps to TEI.

The schema and guidelines are published at <https://cboulanger.github.io/pte-edition-plugin/>.

## Installation

The plugin needs a PDF-TEI-Editor version with support for multi-module external plugins, image input for LLM providers and per-user API keys (mpilhlt/pdf-tei-editor#566).

1. Clone this repository next to the editor:

   ```bash
   git clone https://github.com/cboulanger/pte-edition-plugin.git /opt/pte-edition-plugin
   ```

2. Point the editor to the `plugins/` directory (the plugin has a `pte-plugin.json` marker, so the editor finds it). The variable can list several directories, separated by `:` (`;` on Windows):

   ```bash
   # .env of the editor
   FASTAPI_PLUGIN_PATHS=/opt/pte-edition-plugin/plugins
   ```

   For Docker, mount the directory into the container:

   ```bash
   docker run ... \
     -v /opt/pte-edition-plugin/plugins:/opt/pte-plugins:ro \
     -e FASTAPI_PLUGIN_PATHS=/opt/pte-plugins \
     cboulanger/pdf-tei-editor:latest
   ```

3. Each user supplies their own Anthropic API key, so the cost of the transcription is billed to the user and not to the maintainer of the editor. When a user starts an extraction without a stored key, the editor asks for it and stores it encrypted (it can also be managed under the user menu > API Keys). Administrators and scripts can store keys with `uv run python bin/user-secrets.py set anthropic --user <name>` in the editor's directory. The model is chosen in the extraction dialog; `ARCHIVAL_EDITION_MODEL` (or the config key `plugin.archival-edition.model`) sets the default.
4. Optional: set `ARCHIVAL_EDITION_AUTHORITY` (or the config key `plugin.archival-edition.authority`) to the project responsible for the edition; it goes into `publicationStmt/authority`.

After a restart, "Archival Edition" appears as an external plugin in the Plugin Manager, and "Archival edition (description form + transcription)" is offered in the extraction dialog.

The plugin uses only Python packages the editor already installs (lxml, PyMuPDF).

## Usage

1. Fill in the Document Description Form for a document and export it to PDF from Word.
2. Append the photographs of the document, one per page and in reading order.
3. Upload the PDF to the editor and run the "Archival edition" extractor. Options:
   - **Transcribe pages**: `no` builds only the header and the page structure, without calling the model;
   - **Form pages**: number of form pages at the start of the PDF; leave empty to detect them (the form pages are the ones with a text layer).
4. Review the result following the [review checklist](docs/guidelines.md#review-checklist).

If the form was printed and scanned instead of exported, it has no text layer. The extractor then asks the model to read it.

## How it works

```text
PDF ──► form pages (text layer) ──► form_parser.py ──► field values ──► header_builder.py ──► teiHeader
   └──► photo pages ──► transcriber.py (one model request per page, JPEG ≤ 2000 px,
                         with the form data and the end of the previous page as context)
                         ──► <pb/> + TEI blocks per page ──► text/body/div
```

| File | Purpose |
| --- | --- |
| [plugin.py](plugins/archival_edition/plugin.py) | Registers the extractor and the document rules provider (schema URL, guidelines) |
| [extractor.py](plugins/archival_edition/extractor.py) | Assembles the TEI document |
| [fields.py](plugins/archival_edition/fields.py), [values.py](plugins/archival_edition/values.py) | Form fields and their conventions (`[inferred]`, `?`, dates, names) |
| [form_parser.py](plugins/archival_edition/form_parser.py) | Reads the form's tables from the text layer, or asks the model for scanned forms |
| [header_builder.py](plugins/archival_edition/header_builder.py) | Maps form fields to the TEI header |
| [transcriber.py](plugins/archival_edition/transcriber.py), [prompts/](plugins/archival_edition/prompts) | Page-by-page transcription with one repair round for malformed XML |
| [schema/](schema) | Composable RNG source of the schema |

[examples/sample-letter.tei.xml](examples/sample-letter.tei.xml) shows the output for the test PDF (with a canned transcription instead of a real model).

## Extending the PDF-TEI-Editor

This repository is an example of a plugin that lives outside the editor's source tree. How external plugins work (discovery, the `pte-plugin.json` marker, packages, routes, static files, dependencies) is described in the editor's [backend plugin guide](https://github.com/mpilhlt/pdf-tei-editor/blob/devel/docs/code-assistant/backend-plugins.md#external-plugins).

## Development

Tests run in the Python environment of a PDF-TEI-Editor checkout (default `../pdf-tei-editor`, or set `PTE_ROOT`):

```bash
uv run --project ../pdf-tei-editor python -m pytest
```

After editing anything in `schema/`, regenerate the flattened schema (written to `docs/schema/` and the plugin's `static/schema/`):

```bash
uv run --project ../pdf-tei-editor python scripts/build_schema.py
```

Regenerate the test PDF (needs LibreOffice and python-docx) and the example output:

```bash
uv run --project ../pdf-tei-editor --with python-docx python scripts/make_sample_pdf.py
uv run --project ../pdf-tei-editor python scripts/make_example_tei.py
```

The schema and guidelines are served by GitHub Pages from the `docs/` directory of the `main` branch.
