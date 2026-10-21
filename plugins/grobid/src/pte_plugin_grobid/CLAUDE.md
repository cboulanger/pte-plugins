# GROBID Plugin — Code Assistant Notes

## Tests

Plugin tests live in `plugins/grobid/src/pte_plugin_grobid/tests/`. JavaScript unit tests run with `npm test` in the repository root (see the root README).

Python unit tests run with pytest in the editor's environment:

```bash
uv run --project "$PTE_ROOT" python -m pytest plugins/grobid/src/pte_plugin_grobid/tests/test_annotation_config.py -v
```

**All new tests for this plugin go in `plugins/grobid/src/pte_plugin_grobid/tests/`**, not in `tests/unit/`.
