# GTM Preview Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-preview-recette?sort=semver)](https://github.com/haiqigeng/gtm-preview-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Current release

[v1.1.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.1.0) is
the current supported release. Download the validated package:
[gtm-preview-recette-v1.1.0.zip](https://github.com/haiqigeng/gtm-preview-recette/releases/download/v1.1.0/gtm-preview-recette-v1.1.0.zip).

v1.1.0 is the schema-v2 client-side hardening release. It requires explicit
web-container inventory, action-value metadata, applicability-derived evidence
layers, and stricter provenance; legacy normalized rows must be upgraded before
certification. It also adds embedded tracking-plan asset extraction,
visible-interaction census, document-start dataLayer journalling, robust
request decoding, practical Tag Assistant recovery guidance, and atomic
per-event validation.

An expert-only workflow for testing an existing client-side Google Tag Manager
implementation against a tracking plan. It coordinates Playwright, GTM Preview,
Tag Assistant, analytics and media tags, browser destination requests, multiple
web containers, consent scenarios, cross-field and privacy checks, browser
contexts, prior-run comparison, and a detailed XLSX result workbook.

## Who It Serves

- Web analysts, analytics consultants, GTM specialists, and agencies.
- Expert QA teams that already understand dataLayer, GTM variables, triggers,
  tags, consent, and Tag Assistant.
- Codex and other Markdown-capable agents that can operate a Playwright browser.

It is intentionally not a beginner marketing-team guide.

## How It Works

The workflow is organized into three layers:

1. **Orientation**: establish scope, interpret the client's bespoke tracking plan,
   define journeys, and confirm expectations.
2. **Execution**: open the dedicated browser, connect GTM Preview, reproduce
   journeys, test every applicable interaction and material finite value,
   reconcile every business push in the ordered action-window stream, complete
   ordinary synthetic-data gates, and capture evidence.
3. **Judgement**: compare raw or native client signals, resolved Data Layer
   state, variables, tag values/firing, destination requests, trigger and
   sequence logic, consent, business rules, redacted sensitive-data results,
   context checks, and optional regressions against the confirmed specification.

Strict validation reconciles destination IDs, vendor event names, and tested
parameters with their raw browser-request paths. It also rejects omitted
applicable verdicts, inconsistent trigger/consent/client-check claims,
incomplete privacy scans, provenance-free evidence, and unreconciled
baseline comparisons. Literal vendor keys such as `ep.value` are supported
through quoted request paths.

There is one operational recette workflow, not separate dataLayer-only,
analytics-only, or media-only run types. Each confirmed tracking-plan
requirement determines its applicable evidence layers. The central comparison
remains:

```text
tracking plan -> raw push/API Call -> resolved Data Layer -> GTM variable
-> concerned tag configuration -> firing/non-firing -> runtime tag value
-> decoded browser send -> verdict
```

Every link keeps its own status. A correct dataLayer payload therefore cannot
hide a wrong configured source, firing decision, runtime value or type, or
browser request.

Every run begins with a concise responsibility-labelled preflight, waits for
`READY`, and then pauses only at protected checkpoints.

Coverage is exhaustive where the website exposes a safe finite set: repeated
header/menu/footer controls, cards, CTAs, placements, and low-cardinality
values are parameterized and all executed. Large combinatorial spaces use
documented boundary and risk-based pairwise coverage. The workflow does not
invent arbitrary negative journeys; it detects duplicate, premature, delayed,
wrong-order, and wrong-context events while reconciling the planned positive
journey, then reproduces an anomaly only when useful.

An encountered ordinary form, sign-up, login, lead, or account gate remains
part of the journey. Confirmed non-production lead, registration, and
conversion submissions use synthetic data by default. Credentials, MFA,
CAPTCHA, verification links/codes, real payment, and irreversible actions stay
under analyst control.

## Inputs And Outputs

Inputs may be an XLSX, CSV, sheet export, document, screenshot, mock-up, or
analyst explanation. The skill recognizes the client's structure and maps it to
an internal test matrix without forcing a new template. XLSX hyperlinks,
comments, merged/hidden structure, and embedded images are retained during
inspection so supplied journey guidance is not lost.

The required output is a concise XLSX validation matrix backed by 17 validated
worksheets. Each row shows the tracking-plan value, raw/resolved client signal,
GTM/tag configuration, runtime and outbound values, component verdicts, exact
mismatch, and evidence.

## Boundaries

The workflow tests behaviour only. It does not create a tracking plan, audit or
clean a GTM container, debug or fix implementation, change the website, publish
GTM, or make legal/privacy decisions. Server-side GTM clients,
transformations, requests, and browser/server deduplication are not included.
Unallowlisted sensitive content is reported only through redacted scanner
findings and is refused by workbook generation until the source is quarantined
or replaced with safe synthetic/redacted evidence.

## Run

Install the small deterministic dependency set:

```powershell
python -m pip install -e ".[dev]"
```

Build a workbook from normalized evidence:

```powershell
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Inspect a plan, decode safe browser-request captures, and validate results
event by event:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
python -B scripts/decode_browser_requests.py requests.json decoded-requests.json
python -B scripts/incremental_recette.py status normalized-results.json
python -B scripts/incremental_recette.py validate-event normalized-results.json --event-group-id EVG-001
```

Evaluate declared client-side rules, scan for redacted sensitive-data findings,
or compare a supplied previous run:

```powershell
python -B scripts/validate_business_rules.py normalized-results.json
python -B scripts/scan_sensitive_data.py normalized-results.json
python -B scripts/diff_recette_runs.py previous-results.json normalized-results.json
```

Run regression tests:

```powershell
python -m unittest discover -s tests -v
```

The full agent workflow starts in `SKILL.md`. The reference map is:

- `references/01-orientation/`: purpose, users, inputs, outputs, acceptance, and non-goals.
- `references/02-execution/`: interaction, browser readiness, multi-vendor
  destinations/containers, Tag Assistant operations, interaction capture,
  incremental evidence, runtime contexts, consent, test data, and QA commands.
- `references/03-judgement/`: comparison, evidence, matching, conditional and
  business/privacy rules, regression, verdict, workbook, and completion rules.
- `scripts/`: deterministic schema, plan inspection, browser helpers, request
  decoding, incremental validation, business-rule, privacy, regression, and
  XLSX tooling.
- `tests/`: regression coverage for strict evidence and report output.

Do not store client exports, screenshots, container IDs, domains, emails,
credentials, or generated reports in a release bundle.
