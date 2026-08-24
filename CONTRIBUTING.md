# Contributing

The source version is **v6.0.0**. Use synthetic fixtures only. Never commit
client plans, domains, container or destination IDs, browser traces,
screenshots, reports, credentials, tokens, form data, or run artifacts.

## Design rules

- Preserve one staged compiler, one canonical occurrence model and one
  deterministic verdict authority. Do not add alternate ledgers/results or a
  public provenance/verdict setter.
- Compile typed occurrence, value/state, relationship, order, transport and
  negative claims without imposing a fixed layer matrix.
- Keep scenarios just in time. Do not recreate whole-plan cases, domain rows,
  tag inventories or reports before the first useful action.
- Preserve exact API Call/conditional call-time source and continuous request deltas,
  strict JSON types/states, declared-only wire coercion, document/action/Preview identity,
  evidence-source non-substitution and independent business outcome.
- Keep the Tag Assistant API Call, Data Layer state, Variables, tag inventory,
  effective tag mapping/runtime and browser request as separate authorities. Compare
  every destination-applicable planned field on every applicable surface.
- Preserve six diagnostic domains plus confidence and coverage gates. Detailed
  operational rows must remain applicable and per-target, not fixed stages.
- Semantic annotations may only add evidence-backed `FAIL` or `REVIEW`; the
  deterministic renderer owns all statuses.
- Keep behavior signatures as lean coverage evidence, not a large ontology.
- Optimize measured browser/navigation/Preview work, not by skipping proof.
- Keep Playwright MCP headed Edge as the default runtime, `next`/`complete` as the normal
  loop, one real interaction per action, and existing-window attachment as an explicit
  fallback. Do not add coordinate or guessed-tool recovery.
- Keep server-side certification outside this skill.

Every verdict or workflow change needs a focused synthetic regression that
fails without the change. Changes to `datalayer_recorder.js` or
`dom_interaction_census.js` also require the real-browser helper suite.

## Validation

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache scripts tests
python -m ruff format --check scripts tests
python -m unittest discover -s tests -v
python -B tests/run_browser_helpers.py
python -B scripts/check_release.py
# Release validation also needs a sanitized successful live pilot:
python -B scripts/check_release.py --tag v6.0.0 --live-pilot C:\path\to\live-pilot.json
```

## Versioning

Use semantic tags and archive names. Store `6.0.0` in `pyproject.toml`, tag it
as `v6.0.0`, and package it as `gtm-client-recette-v6.0.0.zip`. Increment major
for incompatible architecture/contracts, minor for compatible capability, and
patch for compatible corrections.
