# GTM Client Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-client-recette?sort=semver)](https://github.com/haiqigeng/gtm-client-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository version: **v7.0.0**.

GTM Client Recette is a personal expert skill for client-side GTM Preview acceptance
testing. It follows an existing tracking plan, uses a headed Playwright MCP-managed
Microsoft Edge session, and asks whether one real interaction forms a truthful causal
chain from page reality through the exact Data Layer API Call, concerned GTM tag, and
browser request—while noticing weird behavior around it.

Its north star is trustworthy findings per expensive browser interaction, not maximum
machinery and not the smallest possible checklist.

## Why v7

Versions 3.1–6.x accumulated setup handshakes, default panels, evidence requirements, and
agent normalization steps that could consume many minutes before or during one event.
v7 keeps the claim, scenario, anomaly, business-reality, privacy, and deterministic
verdict engine while replacing the expensive default path:

- prepare one managed browser while the plan compiles;
- freeze one setup cursor;
- run one planned interaction;
- execute one paste-ready five-second collector;
- judge once and emit explained per-event feedback immediately;
- expand scenarios only when material evidence requires it.

Missing evidence now yields targeted `BLOCKED` feedback instead of refusing completion,
reloading, or hanging. Browser health counters, accumulated Data Layer state, GTM
Variables, and consent detail are no longer default prerequisites.

## Default inspection layers

Every event always reports these five rows:

1. **Page/action reality** — valid page, intended route/state, successful action/outcome,
   and visible business truth.
2. **Data Layer API Call** — exact fully expanded Tag Assistant API Call, planned fields,
   types/values/count, and unplanned business pushes.
3. **GTM Tags** — concerned inventory, effective configuration/mapping, firing count,
   and runtime values, including causal Trigger Group firing.
4. **Browser request** — applicable logical hit, destination, planned parameters,
   transport outcome, duplicates, and retries.
5. **Surrounding behavior** — missing, duplicate, premature, delayed, interjected, stale,
   or contaminating behavior around and between interactions.

The tracking plan is the baseline. Every applicable planned field is compared at API
Call, effective tag mapping, tag runtime, and request. A tag exposing only one of twelve
planned fields fails the other eleven when tag detail is complete. Dynamic values may
change between selected scenarios but must agree across these surfaces inside one action.

The accumulated Tag Assistant **Data Layer** tab and **Variables** tab are conditional
diagnostics only. They activate from explicit state/resolved requirements or a precise
ambiguity; neither substitutes for the API Call or tag runtime. Direct call-time
recording, consent, acquisition, forms, media, and protected-gate diagnostics are also
conditional. Evidence confidence, scenario coverage, and data safety appear when
non-pass.

## Fast operating sequence

1. Intake asks once for the plan/rules, unresolved tag category, protected prerequisites,
   and readiness.
2. After `ready`, open one blank headed managed Edge window. The user prepares login,
   GTM Preview, the site, and ordinary consent while `init` normalizes the plan.
3. Derive URL/environment/container/destination from the plan and prepared runtime; do
   not ask redundant permission for synthetic interactions or ordinary forms.
4. Freeze one Preview cursor and run `next` for the current material scenario.
5. Perform exactly the returned action once. Core gets at most one measured navigation,
   never a cleanup reload.
6. Run the returned `playwright_completion.code` once, add a native action-bounded
   Playwright network delta when available, and pass the bundle to `complete`.
7. Show the returned five-layer feedback before the next action.
8. Finish after all material branches are tested, equivalent, or honestly blocked.

The user accepts ordinary consent because vendor-specific CMP automation is slow and
brittle. The agent pauses only for credentials, MFA, CAPTCHA, verification links/codes,
real payment, or another protected gate.

## Minimal CLI

```powershell
python -B scripts/recette.py init --plan tracking-plan.xlsx --run-dir C:\path\to\run --approved
python -B scripts/recette.py next --run-dir C:\path\to\run --event EV-view_item --scenario ordinary --input first-runtime-check.json
# Perform the action and run the returned paste-ready Playwright callback once.
python -B scripts/recette.py complete --run-dir C:\path\to\run --action A-RETURNED-BY-NEXT --input completion.json
python -B scripts/recette.py status --run-dir C:\path\to\run
python -B scripts/recette.py finish --run-dir C:\path\to\run
```

The public surface is `init`, `next`, `complete`, `status`, `handoff`, `finish`, `report`,
and `reopen`. There is no public layer/verdict/provenance setter.

## Tracking-plan intake

JSON, YAML, CSV/TSV, XLSX, and supported GA4 handoffs compile through one predicate
vocabulary. Workbook intake supports flat and event-metadata-plus-variable-sheet layouts,
classifies every sheet, continues recognized variable tables across visual blanks,
excludes classified JavaScript examples, preserves exact machine identifier case, and
reconciles index events with detail sheets.

An orphan/ambiguous row stops intake. A malformed or index-only later event is localized
so the first executable event can start. Broad “all planned” wording resolves through
plan identities or a concise category such as GA4, never as a literal runtime tag or
destination.

## Scenario coverage

The plan may omit live values. The skill:

- tests every manageable finite material value, such as languages/payment methods;
- tests reachable dependent values, such as shipping methods per applicable state;
- samples one representative per distinct high-cardinality behavior signature instead
  of every product/content item;
- compares selected dynamic identities to visible business state and across all layers;
- expands when a plan-omitted value, boundary, exception, failure, or new signature is
  materially different;
- keeps every intervening business API Call for chronological anomaly detection.

## Per-event and final output

`complete` always persists and emits one event feedback block, even when capture is
partial. Each block gives all five layer statuses, passed/total checks, concise reasons,
affected fields, observed/expected values when available, exact `Check next`, and evidence
IDs. The GTM layer separates inventory, mapping, firing, and runtime counts.

The final conclusion lists every event with all five layer statuses and why. Canonical
JSON and a validated XLSX retain every detailed scenario/claim, defect, limitation,
evidence reference, and telemetry row. Statuses are `PASS`, `FAIL`, `BLOCKED`, `REVIEW`,
`NOT_APPLICABLE`, and `PENDING`; reports map pass/fail to OK/KO.

## Boundaries

The skill does not design tracking plans, configure/fix/publish GTM, mutate the website,
certify server-side processing/vendor receipt, bypass protected gates, or make legal
consent conclusions.

## Development validation

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

The suite covers compiler reconciliation, source authority, field completeness,
cross-layer dynamic-value coherence, page/business reality, anomalies, identity,
protocol decoding, partial-evidence feedback, five-layer output, action budgets, and a
real browser-DOM collector fixture. An optional sanitized live pilot can be validated
with `--live-pilot` after release; it is not fabricated from a fixture.

See [v7 design conformance](docs/v7-design-conformance.md),
[v7 regression and downgrade audit](docs/v7-regression-downgrade-audit.md), and
[v7 technical review](docs/v7-technical-review.md).
