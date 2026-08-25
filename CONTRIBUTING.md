# Contributing

The source version is **v8.0.0**. This repository serves one personal fixed workflow.
Use synthetic fixtures only; never commit client plans, domains, IDs, browser traces,
screenshots, reports, credentials, form data, or run artifacts.

## Design rules

- Keep XLSX as the only user input and the validated XLSX as the only final artifact.
- Keep standalone headed Playwright MCP as the only browser surface.
- Keep the runtime command set exactly `start`, `next`, `complete`, and `finish`.
- Keep the five layers fixed and ordered: reality, exact API Call, GTM Tags, browser
  request, and surrounding behavior.
- Check every planned field independently at API Call, tag mapping/runtime, and request;
  visible reality remains an independent baseline.
- Preserve continuous business-event chronology and immediate feedback before the next
  action.
- Exhaust reachable finite material values and sample high-cardinality members only by
  materially different behavior signature.
- Keep the two-consecutive-all-blocked/no-evidence stop rule.
- Fail fast on invalid XLSX, wrong observer contract, corrupted state, or mismatched
  action. Never add salvage, repair, retry, reopen, fallback, mode, or feature flags.
- Do not reintroduce the accumulated Data Layer tab, GTM Variables, recorder, consent
  engine, alternate browser, or run-specific normalization.
- Add a focused synthetic regression for every behavior change. Browser-helper changes
  require the Playwright fixture.

## Verification

```powershell
python -m pip install -e ".[dev,browser-test]"
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m unittest discover -s tests -v
python -B tests/run_browser_collector.py
python -m vulture scripts tests --min-confidence 80
python -B scripts/check_release.py --tag v8.0.0
python -B scripts/build_skill_package.py --output dist/gtm-client-recette-v8.0.0.zip
python -B scripts/verify_release_artifact.py dist/gtm-client-recette-v8.0.0.zip
```

## Versioning

Store `8.0.0` in `pyproject.toml`, tag it `v8.0.0`, and package it as
`gtm-client-recette-v8.0.0.zip`. Use a major release for an incompatible fixed-contract
change, minor for a compatible improvement, and patch for a compatible correction.
