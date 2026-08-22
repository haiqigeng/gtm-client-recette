# GTM Client Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-client-recette?sort=semver)](https://github.com/haiqigeng/gtm-client-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Current release

[v3.1.0](https://github.com/haiqigeng/gtm-client-recette/releases/tag/v3.1.0)
is the current supported release. Download the validated package:
[gtm-client-recette-v3.1.0.zip](https://github.com/haiqigeng/gtm-client-recette/releases/download/v3.1.0/gtm-client-recette-v3.1.0.zip).

This is a personal expert skill for client-side GTM Preview acceptance testing.
It tests an existing tracking plan on the real site and behaves like an analyst
during recette: it validates tags, but also notices dead pages, wrong business
state, odd events between interactions, wrong containers, broken journeys, and
coherent-looking tracking that is semantically false.

## What v3.1 adds

- Explainable scenario classes and sampling instead of either one arbitrary
  example or every product/page.
- Complete accounting for the dataLayer stream before, during, and between
  planned interactions.
- Separate technical-delivery and overall semantic verdicts.
- Page-health and before/after journey-state evidence.
- Positive business anchors, so two matching empty systems do not prove a
  populated cart or another positive state.
- Binding to the already-approved browser, tab, Preview session, and actually
  loaded GTM container.
- Same-session protected handoffs for CAPTCHA/authentication.
- Natural or explicitly simulated acquisition/referrer scenarios.
- Exact current-run identity across normalized results, session ledgers,
  recorder snapshots, and imported sidecars, with stale-run rejection.
- Complete evidence-catalog hashing, capture-time request redaction, safer
  configurable regexes, and transactional path/import guards.
- One simple layer-by-layer result per event and a plan-ordered conclusion.

## Default inspection

All 19 canonical rows remain visible for auditability, but only applicable
layers are substantive. A normal planned dataLayer event with a browser-sending
tag requires ten default layers: action boundary, raw push, resolved Data Layer,
tag inventory, variables, configuration, firing/count, runtime parameters,
browser request, and sensitive-data scan. Consent, trigger, sequence, business,
regression, container, and conditional layers activate only when applicable.

## Coverage policy

The skill tests every finite material branch and samples only within large
groups that share one behavior signature. A sampled class includes an ordinary
and contrasting member, plus applicable boundaries and exceptions. Any failure,
ambiguity, unseen material value, or new runtime branch reopens coverage review.
Every case stores explicit material-dimension values, and every class closes all
four adaptive trigger reviews even when no trigger was observed.

## Output

Each event receives immediate case and layer statuses, a plain reason,
technical versus semantic components, evidence IDs, and a retest instruction
when needed. The final conclusion lists every event in tracking-plan order.

Operator-v2 workbooks contain the 21 legacy detailed sheets plus eight expert
sheets for coverage decisions, scenario classes, semantic checks, journey
state, stream segments, protected handoffs, gated flows, and final conclusion.
Legacy operator-v1 output remains contract 2 with its exact columns;
operator-v2 output is explicitly contract 3.

## Boundaries

The skill does not design tracking plans, mutate or publish GTM, fix websites,
certify server-side GTM or vendor ingestion, or make legal consent decisions.
It can exercise acquisition/SEO-related tracking scenarios, but it does not
test indexing or ranking.

## Development validation

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache .
python -m ruff format --check .
python -m unittest discover -s tests -v
python -B tests/run_browser_helpers.py
python -B scripts/check_release.py --tag v3.1.0
python -B scripts/build_skill_package.py --output dist/gtm-client-recette-v3.1.0.zip
python -B scripts/verify_release_artifact.py dist/gtm-client-recette-v3.1.0.zip
```

The release archive intentionally contains only runtime skill files. Tests,
repository governance files, caches, previous-run output, and packaging tools
remain outside the installed skill.
