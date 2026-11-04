# Revision 2: reproduction and declarations

## Setup and official command

Clone `https://github.com/sranswal/signalpost-company-intel.git`, check out the exact commit in the submission email, and run:

```bash
uv sync --locked
uv run --locked python scripts/run_competition_batch.py --organisations evaluator-companies.jsonl --bulk brreg-enheter.csv --profiles-output out/run/profiles.jsonl --output out/run/envelopes.jsonl --report out/run/report.json --run-id evaluator-run
```

Python 3.12+ is required. The official input and frozen registry snapshot come from Builderr. The runner infers batch size, preserving input order and returning exactly one terminal envelope per input. In addition to JSONL results, it automatically outputs a self-contained interactive viewer at `out/run/index.html`.

## Smoke and refresh

The checked-in sample contains 100 companies excluded from prior manifests. Selection is deterministic and stratified: 70 registry websites, 30 without.

Run the live sample:

```bash
uv run --locked python scripts/run_competition_batch.py --organisations submission/v2/smoke-companies.jsonl --bulk brreg-enheter.csv --profiles-output out/smoke/profiles.jsonl --output out/smoke/envelopes.jsonl --report out/smoke/report.json --run-id local-smoke --previous-profiles submission/v2/previous-profiles.jsonl
```

The snapshot replay and unit tests are the deterministic checks:

```bash
uv run --locked python -m pytest -q
uv run --locked python scripts/run_refresh_replay.py --manifest tests/fixtures/refresh-snapshots.json --output out/replay.json
```

The source-only `first_run.py` uses saved public responses and makes no network calls.

## Models, APIs and cost

- Production inference: deterministic extraction and rules. No LLM, weights or model API key required.
- Official sources: public BRREG entity, roles, group, subunit and accounts APIs; frozen registry CSV supplied by the evaluator.
- Website access & discovery: zero-cost search across Norwegian public directories and web search without external paid API keys. Candidate homepages are kept only when exact legal name or organisation number appears on the fetched page.
- Careers & News: secondary traversal of verified company domains looking for recruitment (`/karriere`, `/jobb`, `/careers`) and updates (`/nyheter`, `/aktuelt`, `/pressemeldinger`).
- Executive brief: synthesized, grounded written summary per company in Norwegian enterprise context.
- Interactive showcase: self-contained visual dashboard (`index.html`) generated automatically in the batch output directory.
- Private, reserved, multicast and credential-bearing URL targets are blocked. Robots checks and byte/timeout limits are enforced.
- Third-party API cost: $0 per 100-company run and $0 per official run at any batch size. Compute, bandwidth and hosting are separate and environment-dependent.
- External caches: the evaluator's frozen registry CSV, optional explicit previous snapshots and explicit `--resume` checkpoints only.
- Rights and dependency licences: [SOURCE_RIGHTS.md](SOURCE_RIGHTS.md). Exact dependency versions are in `uv.lock`.

## Evidence and known limits

`claims` is the publication boundary. Candidate websites, rejected social handles and group financial statements remain labelled source data, not claims about the legal entity. Freshness is a reporting-year check against the live registry, not proof that an API has exposed every amendment. A stale response is flagged, never presented as a verified current filing.

The matching rules are intentionally conservative. Legitimate brand names and social aliases can be missed. Only specific original-publication fields on news paths are accepted.

An operational smoke pass is not a measured real-world precision or recall score. Only Builderr's official run establishes competition qualification.
