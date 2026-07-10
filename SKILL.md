---
name: gtm-preview-recette
description: Execute an interactive, expert GTM Preview and Tag Assistant recette against an existing tracking plan. First present the complete step-by-step workflow, label Analyst/Codex/Shared responsibilities, and wait for explicit READY before taking any execution action. Then run browser-driven journeys, exact dataLayer.push payload checks, resolved Data Layer and GTM variable checks, tag fired/not-fired verification, tag parameter comparison, consent-behaviour checks, evidence capture, and a detailed XLSX result workbook. Accept client-specific tracking-plan formats through AI recognition plus analyst explanation. Do not use for GTM audits, tracking-plan creation, implementation changes, debugging, publishing, or beginner GTM guidance.
---

# GTM Preview Recette

## Purpose

Run evidence-backed acceptance testing for an existing GTM implementation. Work at expert web-analyst level and treat the tracking plan as the specification. Consider the task achieved only when a detailed XLSX report has been produced and validated.

## Preserve the boundary

- Test implementation behaviour against the supplied specification.
- Do not create, redesign, or repair a tracking plan.
- Do not perform a general GTM audit or container-cleanup review.
- Do not modify GTM, submit or publish a version, change the website, or fix defects.
- Do not diagnose beyond recording an observed non-firing reason. Mark any interpretation as inferred.
- Do not turn the workflow into beginner GTM training.
- Test consent behaviour against supplied expectations; do not make legal or privacy-policy decisions.

Stop and request the missing specification when no tracking plan or analyst-defined expectation is available. A website and event names alone are not sufficient acceptance criteria.

## Load the relevant references

- Read [references/01-orientation/inputs-outputs.md](references/01-orientation/inputs-outputs.md) while establishing scope and deliverables.
- Read [references/02-execution/interaction-protocol.md](references/02-execution/interaction-protocol.md) before every run.
- Read [references/02-execution/browser-session-and-readiness.md](references/02-execution/browser-session-and-readiness.md) before opening GTM or executing a journey.
- Read [references/02-execution/consent-and-synthetic-data.md](references/02-execution/consent-and-synthetic-data.md) before handling consent or forms.
- Read [references/03-judgement/matching-rules.md](references/03-judgement/matching-rules.md) while interpreting the tracking plan.
- Read [references/03-judgement/evidence-model.md](references/03-judgement/evidence-model.md) while capturing event evidence.
- Read [references/03-judgement/comparison-contract.md](references/03-judgement/comparison-contract.md) before assigning verdicts.
- Read [references/03-judgement/workbook-architecture.md](references/03-judgement/workbook-architecture.md) before generating the workbook.

## Execute the workflow

### 0. Show the workflow and wait for READY

Before opening a browser, reading client files, inspecting a website, or
generating any output, display the friendly bullet-list run plan from
[references/02-execution/interaction-protocol.md](references/02-execution/interaction-protocol.md).
Use only the plain responsibility labels `Analyst`, `Codex`, and `Shared`; do
not use internal terms such as `OWNER`, `execution contract`, or `judgement` in
the preflight message. Explain that the analyst must complete protected
authentication in the dedicated Playwright session opened after `READY`, rather
than a separate browser. List required inputs and checkpoints, then ask whether
the analyst is ready to start.

Do not take execution actions until the analyst replies with `READY` or an
equivalent explicit confirmation. If the analyst corrects the plan, update it
and wait for confirmation again. After `READY`, announce the current step,
owner, status, and next action before each step. Pause at every user-owned or
shared checkpoint; never silently skip ahead.

### 1. Establish the test contract

Collect the tracking plan, website/environment URL, GTM account and container identifiers when known, workspace, preview environment when relevant, consent scenarios, credentials boundary, and any provided journeys or mock-ups.

Accept XLSX, CSV, exported sheets, documents, screenshots, or an analyst explanation. Recognize the client's structure and build an internal test matrix; never require the client to rewrite the source into a fixed template. Preserve source sheet, row, cell, or section references. Show the interpreted event, variable, tag, value, and consent mapping to the analyst for confirmation when ambiguity could alter a verdict.

### 2. Define executable journeys

Use this order of authority:

1. Supplied journey or test scenario.
2. Mock-up or implementation specification.
3. Analyst instructions.
4. URLs, selectors, labels, or actions identified in the tracking plan.
5. Website exploration inferred from event names and visible elements.

Mark inferred steps. Ask for confirmation when multiple plausible actions can produce the same event, or before consequential actions such as payment, account changes, form submission to a real lead system, or irreversible state changes.

### 3. Start a controlled GTM Preview session

Use Playwright MCP or the available Playwright-capable browser surface. Open a dedicated browser session and preserve the multi-tab relationship among GTM, Tag Assistant, and the debugged website.

Require the analyst to complete Google sign-in, MFA, CAPTCHA, or other protected authentication manually. Never request, store, or automate credentials.

Record each preparation step as execution evidence:

1. Open GTM.
2. Select the required account, web container, and workspace.
3. Click Preview.
4. Enter the website URL to test.
5. Confirm that Tag Assistant reports `Connected`.
6. Confirm that the debugged website opens with the intended preview context.

Do not begin journey verdicts until the connection, container, workspace, target URL, and consent starting state have been recorded.

Register the GTM workspace, Tag Assistant, and website surfaces by role, URL,
and title. Rediscover a surface before every action; never rely on a stale tab
index. Apply the readiness and quiet-window rules in
[references/02-execution/browser-session-and-readiness.md](references/02-execution/browser-session-and-readiness.md).

### 4. Establish consent scenarios

Capture the initial/default consent state before interacting with the consent
interface. Manage the banner and consent preferences automatically according to
the confirmed test scenario:

- For a normal functional journey with no consent scenario, accept the site's
  standard cookie choice so the journey can run. Record the initial state and
  selected action as setup evidence; mark consent checks `NOT_TESTED`.
- For a requested refusal, partial-choice, or change-of-choice scenario, apply
  that state automatically, execute the journey in each requested state, and
  record the before/after tag behaviour.
- When consent gating or Google Advanced Consent Mode is in scope, verify the
  required tag firing, blocking, and consent-state behaviour under each
  requested state. Include the applicable consent signals and tag-level
  evidence in the report.

Pause only when no available choice can reach the journey or the choice would
cause an irreversible account, payment, or subscription action. Do not make a
legal or privacy-policy judgement from the observed behaviour.

### 5. Execute each journey

Drive stable, repeatable interactions with Playwright. Record URL, action, element, outcome, timestamp/order, and evidence ID for every step. Pause for analyst action when the journey reaches MFA, CAPTCHA, payment, email confirmation, ambiguous navigation, or another protected/manual checkpoint.

For an authorised test journey, complete ordinary registration, lead, and
pre-submission forms automatically with generated synthetic test data when no
test data is supplied. Infer each field's expected format from its label,
validation, and surrounding context. Never use a real person's identity,
contact details, payment data, or credentials. Use reserved example domains for
synthetic email addresses and do not expose generated passwords in the report.
Proceed through account creation or form submission only when it does not need
external email/SMS validation or a payment. Stop and record `BLOCKED` at an
email/SMS code, magic link, CAPTCHA, payment, or similarly protected step. Do
not accept optional marketing, communication, profiling, or newsletter opt-ins
unless they are the explicitly tested conversion. For authorised synthetic test
registrations, accept required terms, privacy notices, and declarations needed
to submit the form, and decline or leave unchecked every optional preference.
Record each required acceptance and optional refusal as execution evidence.

Monitor Tag Assistant while navigating. Identify expected events, missing expected events, duplicate events, and relevant unexpected events. Do not treat an event name alone as proof of a successful test.

Before each consequential action, require the target page, Preview connection,
and requested consent state to be stable. After each action, wait for the event
stream to settle before selecting and judging events. Do not use a fixed sleep
as proof of readiness.

### 6. Inspect every tested event

For each event selected in the Tag Assistant left timeline, capture:

- Event order/identifier and event name.
- The `API call` section with the exact live `dataLayer.push(...)` payload.
- The `Data Layer` panel state at that event.
- Relevant values from the `Variables` panel.
- `Tags fired`, including fire count, status, runtime values, and tag parameters.
- `Tags not fired`, including tags expected to fire and tags expected to remain blocked.
- Consent state and relevant console evidence.
- Screenshot or equivalent machine-readable evidence references.

Treat the API-call object as the authoritative raw payload for that push. Treat the Data Layer panel as the resolved data model at that moment, which may contain values inherited from earlier pushes. Never merge these two evidence types.

### 7. Apply comparison rules

- Require strict equality from tracking plan to dataLayer and tag value when the expected value is fixed.
- Require dataLayer-to-runtime-tag equality unless the tracking plan defines a transformation.
- Validate documented transformations explicitly and show input, rule, and output.
- For dynamic or non-exhaustive plan values, apply the confirmed rule such as presence, type, format, regex, allowed values, identifier stability, or value change.
- Preserve type distinctions; do not silently equate strings, numbers, booleans, arrays, nulls, and absent values.
- Mark expected-but-absent events or tags as failures unless the execution itself was blocked.
- Record relevant unexpected events and tags separately; do not silently ignore them.

### 8. Record wanted-tag non-firing reasons

For every tag expected to fire but observed in `Tags not fired` or as failed:

1. Open its Tag Assistant details.
2. Capture the firing trigger evaluation, blocking trigger or exception, relevant variable values, consent state, and any direct failure message.
3. Record the most specific evidenced reason available.
4. Label the reason source as `preview`, `console`, `consent`, or `inferred`.
5. When evidence does not establish a reason, write `Reason not established from available Preview evidence`; never invent one.

Report the observed reason without recommending or implementing a fix unless the user separately requests debugging.

### 9. Produce the XLSX report

Normalize the evidence according to [references/03-judgement/workbook-architecture.md](references/03-judgement/workbook-architecture.md). Generate the workbook with:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Use an absolute path to the bundled script when executing outside the skill directory. Open or reload the generated workbook to verify that sheets, filters, values, hyperlinks, wrapped notes, and status formatting are intact.

## Use the status model

- `PASS`: observed result satisfies the confirmed expectation and has evidence.
- `FAIL`: observed result contradicts the expectation, including a missing expected event/tag.
- `BLOCKED`: the check could not execute because of a documented external or manual blocker.
- `REVIEW`: evidence exists but the expectation or interpretation requires analyst confirmation.
- `NOT_TESTED`: explicitly out of the executed scope; include the reason and evidence of scope/execution context.

Do not use a passing journey status to hide failed event, variable, tag, parameter, or consent rows.

## Enforce the completion gate

Declare the recette complete only when all of the following are true:

- The tracking-plan interpretation and journey scope are confirmed or clearly marked as analyst-provided.
- Every planned event is `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED`.
- Every tested event contains separate API-call and resolved Data Layer evidence.
- Every required variable, tag, tag parameter, and consent expectation has a row-level verdict.
- Every expected-but-not-fired tag has an evidenced reason or the explicit reason-not-established statement.
- Every result row references evidence and detailed notes where needed.
- Unexpected relevant events/tags are listed.
- A detailed XLSX workbook exists and passes strict report validation.
- The validation matrix contains one source-bound row per required
  event/field/tag comparison and shows tracking-plan, dataLayer, tag
  configuration, and resolved runtime values side by side.
- Every action boundary records readiness before the action and a settled event
  stream afterward.

If any gate is unmet, report the work as incomplete and state the exact missing evidence or blocked checks.
