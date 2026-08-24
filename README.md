# GTM Client Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-client-recette?sort=semver)](https://github.com/haiqigeng/gtm-client-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository version: **v6.0.1**.

GTM Client Recette is a personal expert skill for client-side GTM Preview acceptance
testing. It follows an existing tracking plan or explicit rules, operates in a headed
Playwright MCP-managed Microsoft Edge session, and asks whether the page, business state, source stream,
GTM decision, runtime payload and browser delivery form one truthful causal chain.

The goal is not the shortest possible run. It is the highest number of trustworthy
findings per expensive browser interaction.

## Why the redesign

Versions 3.1–5.2 accumulated browser handshakes and agent-controlled staging that could
still delay the first inspection for many minutes. Version 6 keeps the v5 quality engine
but replaces its control path:

- the unit of work is a typed measurement claim in a material scenario;
- one staged compiler and one canonical occurrence/evidence model;
- fully expanded Tag Assistant API Call as the normal exact-message source, with a
  document-start recorder only when stronger invocation-time evidence is needed;
- capability-checked Playwright MCP launches one headed persistent Edge profile by default
  without coupling the workflow to one package version;
- `next` freezes one action before Preview creates the first measured page load;
- `complete` commits browser deltas and the bounded Preview pass together;
- observable document transitions preserve evidence and block confidence after agent
  mistakes; operation counters are optional telemetry;
- one real interaction can satisfy several causally co-occurring claims;
- each interaction receives one bounded Preview pass with selective deep reads;
- finite and dependent live values are discovered just in time;
- high-cardinality populations are sampled by behavior signature;
- deterministic business/anomaly judgement prevents coherent false passes;
- one canonical correlation/judgement pass and immediate compact per-layer feedback,
  with full claim detail retained in canonical outputs;
- reports are rendered once at final reconciliation.

No future-event scenario scaffold, fixed layer matrix, alternate result authority,
browser-extension dependency, browser replacement loop or generic slow mode is part of
the default design. Existing-window attachment remains an explicit fallback.

## Inspection model

Applicable proof is grouped into six diagnostic domains:

1. reality;
2. source signal;
3. GTM decision;
4. destination delivery;
5. surrounding behavior;
6. data safety.

Evidence confidence and scenario completeness are closure gates. These are not serial
browser stages. A source-only/state-only update does not receive invented delivery
requirements. When a state-only core block explicitly feeds `page_view`, or for an
ordinary GA4 event, each destination-applicable planned field is checked independently
against the exact API Call/proven call-time source, Tag Assistant Data Layer state,
Variables, effective tag mapping, tag runtime and the decoded browser request from the
same action.

Operational detail remains visible per target: DataLayer/API Call, accumulated GTM Data
Layer state, GTM Preview event and Variables, fired/not-fired inventory, named tag
configuration/effective mapping/firing/runtime, browser request/destination, business
anchor, anomaly, safety and gate. The Data Layer tab never substitutes for an API Call.

## Minimal CLI

```powershell
python -B scripts/recette.py init --plan tracking-plan.xlsx --run-dir C:\path\to\run --approved
python -B scripts/recette.py next --run-dir C:\path\to\run --event EV-view_item --scenario ordinary --input first-runtime-check.json
# Perform exactly the returned action card once in the managed Edge window.
python -B scripts/recette.py complete --run-dir C:\path\to\run --action A-RETURNED-BY-NEXT --input action-and-preview.json --markdown
python -B scripts/recette.py status --run-dir C:\path\to\run
python -B scripts/recette.py finish --run-dir C:\path\to\run
```

The public surface is `init`, `next`, `complete`, `status`, `handoff`, `finish`, `report`,
and `reopen`. Use `--help` for exact arguments. There is no arbitrary
append, provenance override, layer setter or verdict setter.

The first `next` carries only the verified Playwright capability profile and optional
health telemetry before the target load. `complete` requires the returned action ID, so
a retry cannot drift to another event. Later starts reuse the same runtime. Repeating an
already committed event/scenario requires a structured evidence-defect or user-request
basis; new material language, shipping, payment, product-signature, or other scenarios do
not.

## Startup sequence

Intake asks for the plan/rules, unresolved tag category, protected prerequisites, and a
single readiness confirmation. It does not require the user to restate URL, environment,
container, destination, synthetic-data permission, or ordinary submission permission
when the plan and prepared browser can resolve them.

After `ready`, open one blank headed managed Edge window immediately. The user prepares
authentication, GTM Preview, and the site there while `init` normalizes the plan. A site
load used to establish login/consent is setup only. If consent is already persistent,
keep final Connect/target navigation until `next`; otherwise accept the CMP during setup,
then authorize exactly one measured Core reload. The skill never adds two cleanup reloads.

## Tracking-plan intake

JSON, YAML, CSV/TSV, XLSX and the supported GA4 tracking-plan handoff compile through one
predicate vocabulary shared with runtime judgement. XLSX intake supports ordinary flat
tables and common sheets with an event-metadata block followed by a variable table;
JavaScript examples are excluded. Recognized sectioned tables continue across visual blank
rows; exact machine identifier case is preserved. Intake classifies every workbook sheet,
reconciles index events with detailed requirement sheets, and reports what was compiled
or ignored. An orphan/ambiguous requirement fails immediately; an index-only or
unsupported later event is localized so the first valid event can start.

Broad “all planned” scope is resolved only through plan identities. Concise aliases such
as `GA4 tags only` and a destination value of `GA4` normalize to the GA4 category rather
than becoming literal runtime IDs. With no exact destination, one concrete causal GA4
destination may be runtime-discovered and reported; exact declared IDs remain strict.
Unresolvable prose still stops before browser work.

## Scenario behavior

The plan is not assumed to list every possible value. The skill:

- exhausts manageable finite material values such as languages or payment methods;
- tests reachable dependent values such as shipping methods under the states where they
  are offered;
- samples one representative per distinct product/content behavior signature instead of
  requiring an arbitrary contrast or brute force;
- compares dynamic identity to the selected scenario's visible state;
- records plan-omitted live values as gaps and expands when they may alter behavior;
- watches the complete source stream around and between planned interactions.

Therefore `en` and `fr` can both pass in their own route scenarios, while a fixed enum or
the selected product/cart identity remains strict.

## Outputs

Each completed action immediately returns a scenario/domain summary followed by one
compact status row for every applicable operational layer, with simple non-pass
expected/observed detail, exact `Check next` target and stable evidence references. Full
claim rows remain in JSON/XLSX. Coverage may still be pending; it affects closure without
blocking capture or first feedback. Every differing value and every `FAIL`, `BLOCKED` or
`REVIEW` remains visible. The final output includes a plan-ordered conclusion, JSON,
Markdown, validated XLSX, defect/retest views and telemetry.
If a later continuous delta exposes an event between two interactions, the same
completion pass visibly revises the affected prior event without another page load.

Canonical statuses are `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, `NOT_APPLICABLE` and
`PENDING`; user-facing reports map pass/fail to OK/KO. The renderer—not the conversational
agent—owns statuses. Semantic reasoning may only add evidence-backed failure or review.

## Boundaries

The skill does not design tracking plans, configure/fix/publish GTM, mutate the website,
certify server-side processing or vendor receipt, bypass protected gates, or make legal
consent decisions.

## Development validation

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache scripts tests
python -m ruff format --check scripts tests
python -m unittest discover -s tests -v
python -B tests/run_browser_helpers.py
python -B scripts/check_release.py
# A release tag additionally requires a sanitized successful live-pilot JSON:
python -B scripts/check_release.py --tag v6.0.1 --live-pilot C:\path\to\live-pilot.json
```

The controlled harness covers generalized compiler, evidence-authority, cross-layer,
scenario, anomaly, identity, protocol, output and startup contracts. Controlled timings
are diagnostic only. A release requires a clean installed-skill run through the
capability-verified Playwright MCP runtime: Core plus one ordinary event, one Preview pass, all mandatory
layers, no guessed/coordinate methods, ad-hoc evidence files or unauthorized reloads,
first action within 120 seconds and first detailed feedback within 300 seconds. No local
fixture is presented as that pilot.

See the [design conformance](docs/v6-design-conformance.md),
[regression and downgrade audit](docs/v6-regression-downgrade-audit.md), and
[technical review](docs/v6-technical-review.md).
