# GTM Client Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-client-recette?sort=semver)](https://github.com/haiqigeng/gtm-client-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository version: **v5.0.0**.

GTM Client Recette is a personal expert skill for client-side GTM Preview acceptance
testing. It follows an existing tracking plan or explicit rules, operates in the user's
already-open Chromium session, and asks whether the page, business state, source stream,
GTM decision, runtime payload and browser delivery form one truthful causal chain.

The goal is not the shortest possible run. It is the highest number of trustworthy
findings per expensive browser interaction.

## Why the redesign

Versions 3.1–4.0 accumulated setup stages, ledgers and per-layer ceremony that could
delay the first inspection for many minutes. Version 5 is a zero-based architecture:

- the unit of work is a typed measurement claim in a material scenario;
- one staged compiler and one canonical occurrence/evidence model;
- continuous call-time dataLayer and browser-network deltas;
- one vertical browser action can satisfy several applicable claims;
- Preview is synchronized in safe micro-batches, with selective deep reads;
- finite and dependent live values are discovered just in time;
- high-cardinality populations are sampled by behavior signature;
- deterministic business/anomaly judgement prevents coherent false passes;
- immediate non-certifying action pulses and detailed canonical per-event feedback;
- reports are rendered once at final reconciliation.

No future-event scenario scaffold, fixed layer matrix, alternate result authority,
browser replacement program or generic slow mode is part of the design.

## Inspection model

Applicable proof is grouped into six diagnostic domains:

1. reality;
2. source signal;
3. GTM decision;
4. destination delivery;
5. surrounding behavior;
6. data safety.

Evidence confidence and scenario completeness are closure gates. These are not eight
mandatory browser stages. A state-only dataLayer update may need source, reality and
behavior proof but no invented GA4 request; an ordinary GA4 event can automatically
check one parameter across source, resolved GTM state, tag runtime and decoded request
from the same captured action.

Operational detail remains visible per target: DataLayer API, GTM Preview event and
variable, named tag configuration/firing/runtime, browser request/destination, business
anchor, anomaly, safety and gate. This keeps feedback actionable without restoring a
fixed nine- or nineteen-layer workflow.

## Minimal CLI

```powershell
python -B scripts/recette.py init --plan tracking-plan.xlsx --run-dir C:\path\to\run --approved --origin https://example.test --expected-container GTM-XXXX
python -B scripts/recette.py begin --run-dir C:\path\to\run --event EV-view_item --scenario ordinary --input before.json
# Perform the real browser interaction in the existing approved session.
python -B scripts/recette.py commit --run-dir C:\path\to\run --input after-and-deltas.json
python -B scripts/recette.py sync-preview --run-dir C:\path\to\run --input preview-batch.json --markdown
python -B scripts/recette.py status --run-dir C:\path\to\run
python -B scripts/recette.py finish --run-dir C:\path\to\run
```

The full public surface is `init`, `begin`, `commit`, `sync-preview`, `status`, `handoff`,
`finish`, `report`, and `reopen`. Use `--help` for exact arguments. There is no arbitrary
append, provenance override, layer setter or verdict setter.

## Tracking-plan intake

JSON, YAML, CSV/TSV, XLSX and the supported GA4 tracking-plan handoff compile through one
predicate vocabulary shared with runtime judgement. Tabular intake preserves source
coordinates, allowed values, JSON types, tag/destination scope and contiguous
merged/fill-down event rows. It reports rows seen, compiled, inherited and intentionally
ignored. An orphan or ambiguous requirement fails immediately; an unsupported rule is
localized to its event so a malformed later event cannot block the first valid event.

## Scenario behavior

The plan is not assumed to list every possible value. The skill:

- exhausts manageable finite material values such as languages or payment methods;
- tests reachable dependent values such as shipping methods under the states where they
  are offered;
- samples products/content by distinct behavior signature instead of brute force;
- compares dynamic identity to the selected scenario's visible state;
- records plan-omitted live values as gaps and expands when they may alter behavior;
- watches the complete source stream around and between planned interactions.

Therefore `en` and `fr` can both pass in their own route scenarios, while a fixed enum or
the selected product/cart identity remains strict.

## Outputs

Each completed event receives a scenario/domain summary followed by operational rows
with status, simple expected/observed detail, exact `Check next` target and stable
evidence references. The final output includes a plan-ordered conclusion, JSON, Markdown,
validated XLSX, defect/retest views and telemetry.

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
python -B scripts/check_release.py --tag v5.0.0
```

The controlled harness covers the generalized stress catalogue through executable
contracts and representative metamorphic mutations; it does not claim 978 independent
browser executions. Existing-browser speed and Tag Assistant extraction remain an
explicit deployment acceptance item because the local control bridge was unavailable
during release validation; no synthetic test is presented as that live pilot.

See the [design conformance](docs/v5-design-conformance.md),
[regression and downgrade audit](docs/v5-regression-downgrade-audit.md), and
[technical review](docs/v5-technical-review.md).
