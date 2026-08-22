# Contributing

Use synthetic fixtures only. Never commit client tracking plans, domains,
container IDs, screenshots, reports, credentials, emails, or browser traces.

## Versioning

Use semantic `v` versioning, never calendar-date versioning:

- Store `MAJOR.MINOR.PATCH` in `pyproject.toml`; the current release is
  `3.1.0`.
- Prefix Git tags and release archives with `v`, for example `v3.0.0` and
  `gtm-client-recette-v3.1.0.zip`.
- Increment PATCH for compatible fixes, MINOR for compatible functionality,
  and MAJOR for incompatible changes.

Before opening a pull request, run:

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache .
python -m ruff format --check .
python -m unittest discover -s tests -v
python -B scripts/check_release.py --tag v3.1.0
```

Changes to verdict logic require a regression fixture that fails before the
change and passes after it. Keep the skill limited to recette execution; do not
add GTM audit, implementation, debugging, or publishing behaviour.

Keep one acceptance workflow. Derive applicable evidence layers from confirmed
requirements and preserve independent verdicts for raw API Call, resolved Data
Layer, GTM variable, tag configuration, firing, runtime parameter, and browser
request. Do not reintroduce named full/scoped run types or allow one layer to
substitute for another.

Changes to interaction coverage, event-stream reconciliation, or gated-journey
behaviour also require an anonymized regression in
`tests/test_v310_optimizations.py`. Keep coverage proportional:
exhaust practical finite sets, document risk-based large-space coverage, and
do not add speculative negative crawling.

Changes to final certification must test the normalized result together with a
schema-v3 session ledger. Cover case closure, retained retries, explicit
business-push counts/classifications, per-case applicable layers, direct
evidence linkage, and workbook case/push sheets. Do not weaken strict
certification to preserve an incomplete legacy run.

Changes to action execution or absence judgement must keep interaction outcome
independent from tracking, retain failed attempts and retry lineage, and test
adaptive settlement. A supplemental recorder observation may expose a Preview
gap but cannot pass a required Tag Assistant layer.

Changes to the dataLayer recorder or DOM census require a synthetic browser
check with `python -B tests/run_browser_helpers.py`; install the optional
`browser-test` dependencies and Chromium first. Changes to plan inspection,
request decoding, or incremental event handling require focused unit tests.

Preserve schema-v3 normalization where possible. If stricter certification
requires new fields, update the fixtures and document the legacy-row upgrade in
the README and changelog. Add strict negative tests for every new
component-level PASS rule. Server-side GTM remains a separate scope and must
not be introduced here.
