# 03 · Proposed Solution

ActionLoop splits the job into specialised, inspectable steps:

1. **Extractor Agent** — classifies the document and extracts fields with a confidence score each. Missing or unreadable values are returned as empty with a note; nothing is invented.
2. **Validator Agent** — runs deterministic rules (required, regex, range, date, age, date order, duplicate, confidence) stored in the `validation_rules` table and editable in Settings.
3. **Action Planner** — produces an ordered plan (department, priority, impact, reasoning) and decides whether a human must approve. Payments, admissions, duplicates, unreadable required values, unclassified documents and urgent complaints always need approval.
4. **Human approval** — reviewers approve, reject or request correction; they can correct field values, which triggers re-validation and re-planning before execution.
5. **Execution** — approved actions are executed in **simulation mode** (clearly labelled; no external systems are called in this prototype).
6. **Audit** — every transition appends a hash-chained event. Approval decisions and workflow outcomes are anchored on MST Blockchain.

### Why blockchain is meaningful here

A hash chain alone proves internal consistency, but whoever controls the database could rewrite the entire chain. Anchoring decision hashes in a public MST contract fixes a point in time that the operator cannot rewrite: anyone holding an exported audit record can recompute its hash and check it against the contract on MSTScan, without trusting ActionLoop's servers.
