# 09 · AI Implementation

## Live mode (`ANTHROPIC_API_KEY` set)

`app/agents/extractor.py → llm_extract()` sends the PDF (as a `document` block) or image (as an `image` block) to Claude via the official Anthropic Python SDK:

- model: `ANTHROPIC_MODEL` (default `claude-opus-5-5`), effort `medium`
- **structured output**: `output_config.format = json_schema` with `{document_type, type_confidence, fields[{name,value,confidence,note}]}`
- server-side refusal fallback enabled (`fallbacks="default"`); `refusal` stop reasons and API errors become an understandable extraction error
- prompt instructs: return `null` for absent/unreadable values, never guess; confidence per field

Fields below `LOW_CONFIDENCE_THRESHOLD` (default 0.75) are marked `uncertain`.

> Live mode was implemented against the SDK documentation but **not executed** in our test environment (no API key). DEMO MODE is what our tests cover.

## DEMO MODE (no key)

- **PDFs with a text layer**: `pypdf` extracts text; a keyword classifier picks the document type; label/pattern rules extract fields; dates and amounts are normalised.
- **Confidence is a heuristic**, documented in code: 0.96 when the label is found and the value matches the expected format, 0.68 when the format doesn't match, 0.41 when characters are unreadable (`?`), 0 when missing.
- **Images**: no OCR/vision without a model, so **no fields are produced** and the workflow is routed to manual triage. Nothing is faked.
- Complaint category and urgency are derived from keyword signals and explained in the field note.

## Measured accuracy (labelled samples)

`/api/analytics/reports → extraction_accuracy` runs the DEMO parser over the six labelled sample PDFs in `samples/ground_truth.json` and reports field-level accuracy. An unreadable value counts as correct only if the extractor left it empty. This is a small, illustrative test set, not a benchmark.

## Deterministic validation

The Validator and Planner never call an LLM. All decisions about validity, duplicates and approval are code + database queries, so model output can't approve itself.
