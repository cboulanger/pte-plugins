# Machine refs point at condensed LLM guidelines

## Problem

The LLM Reviewer (annotation-review) sends the "machine" ref of each editorialDecl rule category with every chunk of a document. For `references` documents that is the full "Citation model" section of fossil's `docs/guidelines.md` (~11,900 tokens) plus "Data correction" (~650), about 80% of every request. Small models take long to process this.

## Measurements (estimated at 3.5 characters per token)

| Section | Full | Condensed |
| --- | --- | --- |
| Data correction | ~645 | ~150 |
| Document segmentation model | ~4,160 | ~600 |
| Reference segmentation model | ~2,830 | ~380 |
| Citation model | ~11,860 | ~2,900 |

Whole citation-model reviews of `tests/pdf-match/sources/` documents: gruber (12 chunks) ~181,000 → ~67,500 input tokens, zjs (4 chunks) ~59,300 → ~21,400, slr (1 chunk) ~14,200 → ~4,700.

## Change

- fossil: `docs/guidelines-llm.md` condenses the four sections under the same headings. `scripts/check-llm-digest.py` (run in CI) fails when a section changed on one side only; fossil's `CLAUDE.md` requires mirroring every change in both files.
- grobid plugin: `AnnotationGuide.machine_url` (optional). If set, the machine ref is derived from it (heading anchor → line range, or a line range as is) instead of from `url`; if that fails (e.g. the file does not exist yet at the pinned commit), the ref derived from `url` is used as before. The four fossil guides set it to the same anchor in `guidelines-llm.md`.
- Existing documents keep their old machine refs until "Refresh document rules" is run on them.

## Not done

- No A/B evaluation with a real model yet (no LLM endpoint in the cloud session). Proposed: inject errors into gold `references` documents and compare recall, false findings, tokens and time between full and condensed rules, with a repeat run of the full rules as the noise baseline.
- Prompt caching (Anthropic `cache_control`) and larger chunks are possible follow-ups.
- Ollama truncates prompts longer than `num_ctx` silently; check this when small models run on Ollama.
