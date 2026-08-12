# GTM Preview Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-preview-recette?sort=semver)](https://github.com/haiqigeng/gtm-preview-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Current release

[v2.2.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v2.2.0) is
the current supported release. Download the validated package:
[gtm-preview-recette-v2.2.0.zip](https://github.com/haiqigeng/gtm-preview-recette/releases/download/v2.2.0/gtm-preview-recette-v2.2.0.zip).

v2.2.0 hardens live operations without changing the fixed 19-layer and
8-sublayer acceptance contract. Interrupted browser, Preview, network-capture,
or surface actions are now retained and settled honestly as uncertain/BLOCKED;
orphan checks can be explicitly voided; same-origin SPA page transitions and
multi-container cases have deterministic evidence rules; and phase-specific
readiness no longer relies on one undifferentiated gate.

The release also adds transactional layer batches, complete computed outcome
coverage, formula-safe CSV sidecars, path-alias rejection, journaled crash
recovery for results/session and final workbook/session pairs, shared strict
value semantics, smaller event-validation slices, and CI that extracts and
tests the actual packaged skill before release. Redundant and contradictory
legacy documentation was removed; schema v2 is now migration-only.

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
canonical or per-tag verdicts, missing tag scope/inventory, inconsistent
trigger/consent/client-check claims,
incomplete privacy scans, provenance-free evidence, and unreconciled
baseline comparisons. Final certification additionally cross-checks the
normalized result against the session's interaction cases, attempts, layer
results, classified push counts, and direct evidence linkage. Literal vendor
keys such as `ep.value` are supported through quoted request paths.

There is one operational recette workflow, not a separate dataLayer-only mode.
The tracking plan supplies expected values and optional journey hints; it never
selects evidence layers. Tag scope is a separate declared policy:
`analytics_only` by default, exact plan-declared media destinations when
present, all relevant client-side tags only on explicit request, or a fixed tag
set. The central comparison remains:

```text
tracking plan -> raw push/API Call -> resolved Data Layer
-> concerned-tag inventory and scope -> each in-scope tag's GTM variables
-> configuration -> firing/non-firing/count -> runtime tag values/types
-> decoded browser send -> per-layer/per-tag verdict -> event verdict
```

Every link keeps its own status. A correct dataLayer payload therefore cannot
hide a wrong configured source, firing decision, runtime value or type, or
browser request.

Before an absent event can fail, the real website interaction must have
independently completed and the acceptance-relevant stream must have settled.
A failed click is retained, its event window is reconciled, and one transient
retry uses a new linked action ID. A journal-only push missing from Tag
Assistant triggers a controlled connection/page-node/window check and cannot
substitute for required Preview evidence.

Every run begins with a concise responsibility-labelled preflight, waits for
`READY`, and then pauses only at protected checkpoints.

Coverage is exhaustive where the website exposes a safe finite set: repeated
header/menu/footer controls, cards, CTAs, placements, and low-cardinality
values are parameterized and all executed. Large combinatorial spaces use
documented boundary and risk-based pairwise coverage. The workflow does not
invent arbitrary negative journeys; it detects duplicate, premature, delayed,
wrong-order, and wrong-context events while reconciling the planned positive
journey, then reproduces an anomaly only when useful.

An encountered ordinary form, sign-up, login preparation, lead, or account
gate remains part of the journey. Ordinary fields, privacy acknowledgements,
tested-conversion opt-ins, and submissions use safe synthetic data without
repeated prompts. An inoperable checkbox is a `UI_CONTROL_BLOCKER` only after
all safe control/retry methods, not a consent or authorization boundary.
Synthetic credentials may be used ephemerally in the same controlled run and
reused for login, but are never stored or shown in chat. Protected credentials
or sign-in, MFA, CAPTCHA, verification links/codes, real payment, external
approval, and irreversible actions stay under analyst control. CMP simulation
keeps its separate one-time approval.

## Inputs And Outputs

Inputs may be an XLSX, CSV, sheet export, document, screenshot, mock-up, or
analyst explanation. The skill recognizes the client's structure and maps it to
an internal test matrix without forcing a new template. XLSX hyperlinks,
comments, merged/hidden structure, and embedded images are retained during
inspection so supplied journey guidance is not lost.

The required output is a concise XLSX validation matrix backed by 21 validated
worksheets, including the Defect Register, interaction cases, Layer Verdicts,
and the observed business-push stream.
Each row shows the tracking-plan value, raw/resolved client signal, GTM/tag
configuration, runtime and outbound values, component verdicts, exact
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

Close the plan-ordered event through the guided validation/feedback gate, then
build the final workbook only after every event is closed:

```powershell
python -B scripts/recette_operator.py close-event `
  normalized-results.json session.json event-001-patch.json `
  --event-group-id EVG-001
python -B scripts/recette_operator.py finish-run `
  normalized-results.json session.json gtm-recette-results.xlsx
```

New guided runs declare `run.action_boundary_contract_version: 1`. Runtime
snapshots must come from the supported Playwright/browser-connector probes and
use fresh, phase-bound, distinct action/network evidence. Older schema-v3
results without this marker remain readable, but the operator never invents
their missing checks or cursors.

Reopen late-discovered coverage without losing history:

```powershell
python -B scripts/recette_operator.py reopen-event `
  normalized-results.json session.json --event-group-id EVG-001 `
  --reason "Late material footer interaction discovered"
```

The workbook and sidecars identify `Output contract: 2` (the CSV repeats it on
every row) so exact-header consumers can distinguish the outcome/anomaly/
runtime-cursor interface from the earlier output contract.

Inspect a plan, decode safe browser-request captures, and validate results
event by event:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
python -B scripts/decode_browser_requests.py requests.json decoded-requests.json
python -B scripts/incremental_recette.py status normalized-results.json `
  --session-ledger session.json
python -B scripts/incremental_recette.py validate-event normalized-results.json `
  --event-group-id EVG-001 `
  --session-ledger session.json
python -B scripts/preview_session_ledger.py import-pushes session.json pushes.json
python -B scripts/preview_session_ledger.py import-layers session.json layers.json `
  --action-id ACT-001
python -B scripts/preview_session_ledger.py scaffold-tag-results session.json `
  --action-id ACT-001 --output tag-results.json
python -B scripts/recette_operator.py status normalized-results.json session.json
```

Migrate legacy v2 discovery without inheriting proof, and verify a packaged
release or local installation against its SHA-256 manifest:

```powershell
python -B scripts/migrate_schema_v2_to_v3.py old-results.json normalized-results.json `
  --legacy-session old-session.json --case-manifest retest-cases.json
python -B scripts/verify_release_artifact.py dist/gtm-preview-recette-v2.2.0.zip
```

Evaluate declared client-side rules, scan for redacted sensitive-data findings,
or compare a supplied previous run:

```powershell
python -B scripts/validate_business_rules.py normalized-results.json
python -B scripts/scan_sensitive_data.py normalized-results.json
python -B scripts/diff_recette_runs.py previous-results.json normalized-results.json
python -B scripts/build_retest_manifest.py normalized-results.json session.json retest.json
```

Register optional upstream context without granting it verdict authority, or
emit concise report sidecars:

```powershell
python -B scripts/register_supporting_artifact.py normalized-results.json audit-facts.json `
  --artifact-id ART-AUDIT-001 `
  --artifact-type gtm_container_audit_facts `
  --source-skill gtm-container-audit-cleanup `
  --source-run-id AUDIT-001 `
  --source-version 1.0.0
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict --session-ledger session.json `
  --defects-csv defects.csv --defects-md defects.md `
  --stakeholder-summary summary.md
```

Run regression tests:

```powershell
python -m unittest discover -s tests -v
```

Run the browser-helper regression:

```powershell
python -m pip install -e ".[browser-test]"
python -m playwright install chromium
python -B tests/run_browser_helpers.py
```

The full agent workflow starts in `SKILL.md`. It loads the compact interaction
and execution contracts first, then loads detailed references only at the stage
that uses them. The reference map is:

- `references/01-orientation/`: concise input/output and cross-skill boundaries.
- `references/02-execution/`: interaction, browser readiness, multi-vendor
  destinations/containers, Tag Assistant operations, interaction capture,
  incremental evidence, runtime contexts, consent, and test data.
- `references/03-judgement/`: comparison, evidence, matching, conditional and
  business/privacy rules, regression, schema, verdict, and workbook contracts.
- `scripts/`: deterministic schema, plan inspection, browser helpers, request
  decoding, incremental validation, business-rule, privacy, regression, and
  XLSX tooling.
- `tests/`: regression coverage for strict evidence and report output.

Do not store client exports, screenshots, container IDs, domains, emails,
credentials, or generated reports in a release bundle.
