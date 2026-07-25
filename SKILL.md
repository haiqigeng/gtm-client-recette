---
name: gtm-preview-recette
description: Execute an expert, operational GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit scoped acceptance rule. Use for full-site or journey-level web analytics QA that must preserve tracking-plan order, infer missing website journeys, complete authorised synthetic-data flows, compare exact raw dataLayer.push payloads and types with resolved Data Layer and GTM variables, verify concerned-tag firing and runtime parameters, provide one evidence-backed verdict per event, and deliver a strictly validated XLSX. Do not use for tracking-plan design, general GTM audits, implementation fixes, publishing, legal consent decisions, or observation without acceptance criteria.
---

# GTM Preview Recette

## North star

> Execute an expert, tracking-plan-led GTM recette on the actual test website, covering every planned event in its original order. Use supplied URLs, screenshots, and journeys when available; otherwise identify and execute the relevant website interactions. For every event, use GTM Preview to compare the tracking-plan expectation with the exact live dataLayer.push payload, its variables, values and types, the resolved GTM variables, the expected tag firing or non-firing behaviour, and every required runtime tag parameter and value. Complete ordinary and authentication-gated journeys with safe synthetic data whenever possible, requesting analyst intervention only at protected, consequential, or genuinely ambiguous boundaries. Return an immediate, evidence-backed verdict and precise reason for each event, omit nothing silently, and finish with a complete plan-ordered status summary and validated detailed workbook.

Treat operational journey completion and evidence reconciliation as inseparable:
the journey creates the evidence, and the evidence makes the verdict trustworthy.

## Preserve the boundary

- Treat the supplied tracking plan or explicit analyst-defined acceptance rule as
  the specification.
- Default to `FULL_TRACKING_PLAN_RECETTE`. Use
  `SCOPED_ACCEPTANCE_RECETTE` only for an explicitly bounded rule and list the
  included evidence layers.
- Stop when neither a tracking plan nor an analyst-defined acceptance rule
  exists. A website and event names alone are not acceptance criteria.
- Do not design or repair the tracking plan, audit or clean the container,
  modify GTM or website code, implement fixes, submit, create a version, or
  publish.
- Record the most specific observed non-firing reason, but do not claim an
  unproved root cause or recommend a fix unless separately requested.
- Keep Google sign-in, MFA, CAPTCHA, external email/SMS verification, real
  payment, irreversible actions, and unresolved consequential choices under
  analyst control. Never request, copy, log, store, or automate credentials.
- Test supplied consent expectations without making legal or privacy-policy
  judgements.

## Load the required references

- Read [references/01-orientation/inputs-outputs.md](references/01-orientation/inputs-outputs.md)
  while establishing scope.
- Read [references/02-execution/interaction-protocol.md](references/02-execution/interaction-protocol.md)
  before every run.
- Read [references/03-judgement/schema-v2.md](references/03-judgement/schema-v2.md)
  before normalizing the plan or evidence.
- Read [references/02-execution/browser-session-and-readiness.md](references/02-execution/browser-session-and-readiness.md)
  before opening GTM or executing a journey.
- Read [references/02-execution/journey-inference-and-coverage.md](references/02-execution/journey-inference-and-coverage.md)
  before inferring an undocumented route.
- Read [references/02-execution/consent-and-synthetic-data.md](references/02-execution/consent-and-synthetic-data.md)
  before handling consent, forms, or a gated journey.
- Read [references/03-judgement/matching-rules.md](references/03-judgement/matching-rules.md),
  [references/03-judgement/evidence-model.md](references/03-judgement/evidence-model.md),
  and [references/03-judgement/comparison-contract.md](references/03-judgement/comparison-contract.md)
  before assigning verdicts.
- Read [references/03-judgement/workbook-architecture.md](references/03-judgement/workbook-architecture.md)
  before generating the report.

## Execute the workflow

### 0. Show preflight and wait for READY

Before opening a browser, reading client files, inspecting the website, or
generating output, display the five-or-fewer bullet preflight from
[references/02-execution/interaction-protocol.md](references/02-execution/interaction-protocol.md).
Use only the labels `Analyst`, `Codex`, and `Shared`.

The essential inputs are the acceptance specification and target environment.
Journeys, URLs, screenshots, selectors, GTM identifiers, and consent scenarios
are supporting inputs when available or applicable; their absence is not a
blocker when they can be inferred safely.

Wait for `READY` or an equivalent explicit confirmation before any execution
action. Authentication in another browser does not authenticate the dedicated
Playwright session.

### 1. Normalize the acceptance contract

Recognize the original XLSX, CSV, document, screenshot, mock-up, or analyst
explanation without forcing a template. Preserve file, sheet, row, cell,
section, screenshot, and source order when available.

Create schema-v2 stable requirement IDs and two ordered inventories before
browser execution:

1. one source-bound row per required event field, variable, tag firing
   condition, tag parameter, or applicable consent condition;
2. one event group per planned event for analyst feedback and final reporting.

Extract the journey clue, expected event, field path, value, type, matching
rule, occurrence rule, GTM variable, concerned tag, configuration field,
runtime parameter, firing expectation, and applicable consent expectation.
Ask only when ambiguity could materially change a verdict.

Use:

```powershell
python scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

when a workbook or CSV needs structural inspection.

### 2. Build the coverage and journey ledger

For every event group, record supplied or inferred journey, candidate pages,
selectors or visible labels, intended action, expected event, inference source,
confidence, attempted routes, and current status.

Use this authority order:

1. supplied journey or test scenario;
2. screenshot, mock-up, or implementation specification;
3. analyst instruction;
4. URLs, selectors, labels, or actions in the tracking plan;
5. relevant website exploration inferred from event semantics and visible
   elements.

Translate production example paths to the confirmed test origin. Mark inferred
steps. Explore relevant alternative routes before declaring an event or element
unavailable. Ask before ambiguous consequential actions, real lead submission,
account changes, payment, or irreversible effects.

### 3. Establish the controlled Preview session

Open a dedicated Playwright-capable browser session. Register and rediscover
these surfaces by role, URL, origin, and title before every action:

1. GTM workspace;
2. Tag Assistant;
3. debugged website.

Require the analyst to authenticate manually inside that session. Record the
account, web container, workspace, Preview environment, target origin, initial
consent state, and `Connected` status. Do not start verdicts until the intended
container, workspace, domain, and Preview connection are confirmed.

Apply the readiness, action-boundary, quiet-window, cross-domain, SPA
deduplication, reconnect, and checkpoint rules in
[references/02-execution/browser-session-and-readiness.md](references/02-execution/browser-session-and-readiness.md).

### 4. Establish applicable consent state

Capture the natural/default event-level consent state before interaction. For a
normal functional journey without a consent requirement, use the normal CMP
choice needed to execute the journey and mark consent checks `NOT_TESTED`.
Execute refused, partial, change-of-choice, or Advanced Consent Mode scenarios
only when required by the acceptance contract.

Never inject or simulate consent as routine setup. If a missing or defective CMP
on a non-production test environment prevents otherwise valid testing:

1. show the observed blocker;
2. explain the exact temporary browser-session override, values, scope, and what
   it will not validate;
3. request explicit analyst approval;
4. proceed only after approval;
5. preserve natural-CMP and `session_override` evidence as separate scenarios.

Without approval, keep affected checks blocked and continue unaffected coverage.
Never use an override to pass the natural CMP implementation.

### 5. Execute continuously in plan order

For each event group:

1. verify the intended page, Preview connection, applicable consent state, and
   quiet event stream;
2. record the last Preview event before the action;
3. execute the exact supplied or inferred website interaction;
4. record URL, element, action, value, timestamp, and inference status;
5. wait for expected events or a bounded timeout and then a quiet window;
6. record first and settled final event indexes;
7. inspect every concerned Preview event and capture the full comparison chain;
8. assign component and event verdicts;
9. emit one concise event verdict with the exact mismatch or blocker;
10. continue automatically to the next planned event.

Do not require repeated `continue` or `generate report` commands.

For authorised ordinary registration, lead, checkout-preparation, and account
flows, infer form formats and use unique synthetic data. Accept only required
terms and declarations. Leave optional marketing, profiling, partner-sharing,
and communication choices unchecked unless they are the tested conversion.

At a protected checkpoint, pause and ask the analyst to complete the step in the
dedicated browser, then resume. Assign `BLOCKED` only when the analyst cannot or
does not complete it, no safe test method exists, or an evidenced external
blocker such as HTTP 403 prevents execution. Never automate real payment.

### 6. Capture the full evidence chain

For every occurred event retain separately:

```text
tracking-plan requirement
-> event occurrence and chronology
-> exact Tag Assistant API Call / raw dataLayer.push
-> resolved Data Layer at that event
-> resolved GTM variable
-> concerned tag configuration
-> tag firing status and fire count
-> runtime tag parameter value and type
-> applicable event-level consent state
```

The Tag Assistant `API Call` is authoritative for the raw push. The `Data
Layer` panel is resolved state and may contain inherited values. Browser
interception is supplemental and must never be relabelled as Tag Assistant
evidence.

Inspect only concerned tags: expected to fire, expected to remain blocked,
unexpected but relevant, or needed to explain a wanted tag’s non-firing. Never
create an event-by-every-container-tag matrix.

### 7. Compare and explain

Use the strict comparison and dependency rules in the judgement references.
Preserve absent, JavaScript `undefined`, explicit `null`, empty string, empty
array/object, and each actual value type.

For a wanted tag that does not fire, capture trigger evaluation, blockers or
exceptions, relevant variable values, event-level consent, and direct Preview
or console messages. Use the most specific evidenced reason and its source. If
the reason is not established, write:

`Reason not established from available Preview evidence`

Do not stop at event-name presence, page success, or tag firing; validate every
applicable requirement independently.

### 8. Close coverage and give the final ordered summary

Compare executed results with both inventories. Attempt relevant alternative
routes for every pending event before final classification. Never use
`NOT_TESTED` for an attempted journey blocked by an external condition.

After coverage is complete, output a concise list of every planned event in
original order with `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED`.
Component failures must remain visible beneath any event roll-up.

### 9. Build and validate the workbook

Normalize results as schema version 2 and generate:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Use the bundled script’s absolute path when outside the skill directory. Reload
the workbook and verify required sheets, row counts, filters, hyperlinks,
structured values, wrapped notes, and status formatting. Do not declare
completion when strict validation fails.

## Use the status model

- `PASS`: the confirmed expectation is satisfied with exact evidence.
- `FAIL`: implementation contradicts a confirmed expectation.
- `BLOCKED`: execution was attempted but a documented external, protected, or
  upstream blocker prevented the check.
- `REVIEW`: evidence exists but plan semantics or interpretation require analyst
  confirmation.
- `NOT_TESTED`: deliberately outside confirmed scope; never a substitute for a
  failed attempt or blocker.

The overall requirement and event status is the worst applicable component
status. A successful journey cannot hide a failed event field, variable, firing
condition, parameter, or applicable consent requirement.

## Enforce completion

Declare a full recette complete only when:

- every source-bound requirement and event group from the confirmed inventory is
  present once;
- every planned event has been attempted in original order or has an explicit
  confirmed out-of-scope status;
- every action has readiness, action-boundary, and settled-stream evidence;
- every occurred event has exact raw API-call and separate resolved Data Layer
  evidence;
- every applicable variable, concerned tag, firing condition, tag parameter,
  and consent condition has its own verdict;
- every wanted non-fired tag has an evidenced reason or the explicit
  reason-not-established statement;
- every protected checkpoint was offered to the analyst before final
  `BLOCKED`;
- every result references known evidence;
- relevant unexpected events and tags are listed;
- the final plan-ordered event summary has been delivered; and
- the detailed XLSX passes strict semantic validation and reload checks.

If any gate is unmet, state that the recette is incomplete and name the exact
missing or blocked evidence.
