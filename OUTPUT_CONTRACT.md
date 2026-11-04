# Signalpost revision-2 output

One JSON object per evaluator-supplied organisation number, in input order. `schema_version` is `signalpost-v2`.

- `organisation_number`, `legal_identity`: exact registry identity.
- `summary`: concise, synthesized executive summary covering legal identity, location, leadership, employee count, financial performance, and verified online footprint.
- `state`: `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous` or `failed`.
- `modules`: per-module state, final timestamp and retry count when supplied.
- `claims`: published field/value pairs, availability and `evidence_ids`.
  - Official identity, roles, locations, and group relationships.
  - Multi-year legal-entity financial accounts, comparison, and freshness status.
  - `company_summary`: grounded written brief with registry provenance.
  - `official_website`: verified company homepage (kept only if the page explicitly names the company or its organisation number).
  - `careers_page`: verified active careers, job openings, or recruitment section.
  - `news_page` / `company_news`: verified news, press releases, or dated article updates.
  - `social_account`: verified outbound social accounts with exact handle matching.
- `evidence`: source records with stable IDs, URLs, timestamps, source classes, hashes and source snapshots. Rejected website snapshots are labelled `raw_source_candidate`.
- `profile`: internal normalized profile, including rejected candidates and separately scoped group statements. It is not the list of published facts.
- `changes`: material differences against an explicitly supplied prior profile.
- `refresh`: prior snapshot hash and same-snapshot comparison result. Prior source evidence is preserved under `profile.previous_evidence`.
- `errors`: module and worker failures, retained even when other fields succeed.
- `operations`: company runtime, counted request attempts, bytes where measured, and third-party API charges.
- `started_at`, `completed_at`, `run_id`: run metadata.

A company can have an overall `available` result while individual fields are blocked or ambiguous. A worker crash always sets its result to `failed`. Failure rows count as terminal results, never silent drops. A malformed input batch is rejected before research.

Internal evidence statuses retain the extractor vocabulary (`not_found`, `source_error`, etc.); `state` and claim `availability` use the six public contract values. Candidate source URLs and raw registry website fields do not constitute published website ownership.

`report.json` records batch runtime, request counts, bytes, request and company latency summaries, emitted results, worker failures, refresh changes and contract checks.

An interactive, self-contained visual report (`index.html`) is automatically generated in the batch output directory beside `envelopes.jsonl` to allow immediate browser review of all company summaries, financials, careers, news, and source evidence.
