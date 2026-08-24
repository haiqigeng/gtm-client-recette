# Contributing

The source version is **v7.0.0**. Use synthetic fixtures only. Never commit client plans,
domains, container/destination IDs, browser traces, screenshots, reports, credentials,
tokens, form data, or run artifacts.

## Design rules

- Preserve one compiler, one causal occurrence model, and one deterministic verdict
  authority. Do not add alternate ledgers, result models, or public verdict setters.
- Optimize for trustworthy findings per real browser interaction. Do not reintroduce
  whole-plan precomputation, mandatory preflight bundles, cleanup reloads, browser
  replacement, or manual panel-to-JSON handshakes.
- Keep the default user-facing layers fixed at reality, exact API Call, GTM Tags, browser
  request, and surrounding behavior. Every event must report all five with status and
  explained non-pass detail.
- Keep accumulated Data Layer state, GTM Variables, recorder, consent, acquisition, form,
  media, and protected checks conditional. Explicit diagnostic requirements must remain
  supported.
- Compare every applicable plan field at API Call, effective tag mapping, tag runtime,
  and request. Preserve strict types/states and scenario-local dynamic-value coherence.
- Preserve every post-cursor business API Call and causal technical follow-up needed for
  duplicate, missing, delayed, and interjected-event analysis.
- Never let a coherent technical chain override dead-page, failed-action, stale-product,
  empty-populated-cart, form, or purchase reality.
- Keep scenarios just in time. Exhaust finite/dependent material values and sample
  high-cardinality members by proven behavior signature.
- Keep Playwright MCP headed Edge as default. One setup cursor, one action, one bounded
  collector pass, and immediate partial-safe feedback are the normal path.
- Missing evidence must block dependent checks and still produce feedback; it must not
  throw before reporting or authorize a repeat.
- Semantic annotations may only add evidence-backed `FAIL` or `REVIEW`.
- Keep client/server certification boundaries explicit.

Every verdict/workflow change requires a focused synthetic regression that fails without
the change. Collector, recorder, or DOM-helper changes also require the real-browser
helper suite.

## Validation

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache scripts tests
python -m ruff format --check scripts tests
python -m unittest discover -s tests -v
python -B tests/run_browser_helpers.py
python -B scripts/check_release.py --tag v7.0.0
python -B scripts/build_skill_package.py --output dist/gtm-client-recette-v7.0.0.zip
python -B scripts/verify_release_artifact.py dist/gtm-client-recette-v7.0.0.zip
```

An optional sanitized live pilot may be checked with `--live-pilot`. Never claim a local
fixture is a live client pilot.

## Versioning

Store `7.0.0` in `pyproject.toml`, tag it `v7.0.0`, and package it as
`gtm-client-recette-v7.0.0.zip`. Increment major for an incompatible inspection/output or
workflow contract, minor for compatible capability, and patch for compatible fixes.
