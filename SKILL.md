---
name: gtm-preview-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rule. Use for plan-ordered analytics and media-tag QA that must cover every applicable interaction and material variant, complete safe gated flows, reconcile every business dataLayer push by action window, compare exact raw and resolved GTM, tag, runtime, and browser-send evidence, detect missing, duplicate, mistimed, or wrong-context occurrences, and deliver one evidence-backed verdict per event plus a validated XLSX. Excludes tracking-plan design, container audit or configuration, implementation fixes, publishing, server-side GTM, and legal consent decisions.
---

# GTM Preview Recette

## North star

> Execute an expert, tracking-plan-led GTM recette on the actual test website, covering every planned event in its original order. Use supplied URLs, screenshots, and journeys when available; otherwise identify and execute the relevant website interactions. For every event, use GTM Preview to compare the tracking-plan expectation with the exact live dataLayer.push payload, its variables, values and types, the resolved GTM variables, the expected tag firing or non-firing behaviour, and every required runtime tag parameter and value. Complete ordinary and authentication-gated journeys with safe synthetic data whenever possible, requesting analyst intervention only at protected, consequential, or genuinely ambiguous boundaries. Return an immediate, evidence-backed verdict and precise reason for each event, omit nothing silently, and finish with a complete plan-ordered status summary and validated detailed workbook.

Apply this north star to every concerned client-side analytics, advertising,
Floodlight, pixel, vendor-template, and Custom HTML tag. A browser request
proves an attempted client send, not vendor ingestion, attribution, or
reporting.

## Keep one acceptance workflow

Use one workflow whose checks are derived from each confirmed tracking-plan
requirement. Do not choose a reduced workflow label. Record the acceptance
scope and the applicable evidence layers explicitly. A requirement that has no
applicable tag, destination, consent, or other downstream expectation may omit
that layer, but a declared expectation may never be silently dropped.

Treat the tracking plan or explicit analyst-defined acceptance rule as the
specification. Stop if neither exists. Do not:

- design or repair the tracking plan;
- audit, clean, configure, version, submit, or publish GTM;
- modify the website or implement a fix;
- make legal or privacy-policy decisions;
- test server-side GTM, server clients or transformations, or browser/server
  deduplication;
- claim vendor receipt from browser-only evidence.

Record the most specific evidenced reason for a failure or non-firing tag.
Do not infer an unproved root cause.

Complete ordinary forms, sign-up, lead, account, authentication, and
non-production conversion gates with safe synthetic data unless the analyst
excluded them. Pause only for credentials, MFA, CAPTCHA, external
email/SMS verification, real payment, irreversible or consequential actions,
or genuinely ambiguous choices. Never request, copy, log, or automate
credentials.

Do not invent arbitrary negative journeys. Detect unwanted behaviour by
classifying every observed business push during the planned positive journeys.
Reproduce an anomaly when useful, and run an explicit non-firing scenario only
when the acceptance specification requires it.

## Load references progressively

Do not preload the complete reference library. Always read only:

- [interaction protocol](references/02-execution/interaction-protocol.md); and
- [core execution contract](references/03-judgement/execution-contract.md).

Then load each stage reference immediately before that stage:

- **Normalize and design cases:** [inputs and outputs](references/01-orientation/inputs-outputs.md)
  and [journey and coverage](references/02-execution/journey-inference-and-coverage.md).
  Read [schema v2](references/03-judgement/schema-v2.md) before manually
  constructing or repairing normalized requirements or event patches; use the
  deterministic initializer and validators instead of reading code.
- **Connect and execute:** [Tag Assistant operations](references/02-execution/tag-assistant-operations.md),
  [browser readiness](references/02-execution/browser-session-and-readiness.md),
  and the [interaction and capture playbook](references/02-execution/interaction-and-capture-playbook.md).
- **Compare and judge:** [evidence model](references/03-judgement/evidence-model.md)
  and [comparison contract](references/03-judgement/comparison-contract.md).
  Load [matching rules](references/03-judgement/matching-rules.md) when a
  requirement uses anything beyond literal equality, presence, absence, or
  exact type.
- **Validate and close:** [incremental evidence workflow](references/02-execution/incremental-evidence-workflow.md)
  before the first event patch, and
  [workbook architecture](references/03-judgement/workbook-architecture.md)
  only before final report generation.

Read the following only when relevant:

- [consent and synthetic data](references/02-execution/consent-and-synthetic-data.md)
  for a CMP, consent expectation, or gated journey;
- [client-side destinations and containers](references/02-execution/client-side-destinations-and-containers.md)
  for analytics/media sends, multiple web containers or destinations, or
  Custom HTML;
- [client-side runtime contexts](references/02-execution/client-side-runtime-contexts.md)
  for SPA, auto-event, responsive, iframe, cross-domain, cookie/linker,
  platform-adapter, Custom JavaScript, or browser-limit checks;
- [conditional business and privacy rules](references/03-judgement/conditional-business-and-privacy-rules.md)
  for conditional branches, cross-field rules, ecommerce completeness, or
  sensitive-data checks; and
- [regression comparison](references/03-judgement/regression-comparison.md)
  when a prior recette or acceptance-relevant read-only container comparison is
  supplied.

Use [the gold mini-recette](references/gold-mini-recette.md) only when
calibration is needed for independent layer verdicts, wrong-context detection,
or output structure.

## Execute the recette

### 0. Confirm responsibilities and readiness

Show the responsibility-labelled preflight from the interaction protocol in no
more than five bullets and wait for `READY` or an equivalent confirmation
before opening client files or executing the website.

The acceptance specification and test origin are essential. URLs, screenshots,
selectors, journeys, GTM identifiers, and consent scenarios are supporting
inputs; infer them safely when possible.

### 1. Normalize the tracking plan in source order

Accept XLSX, CSV, document, screenshot, mock-up, or analyst explanation without
forcing a template. Preserve file, sheet, row, cell, section, screenshot, and
original event order.

When the plan is tabular, inspect structure, hyperlinks, comments, hidden
content, merged ranges, and embedded images:

```powershell
python scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

Create:

1. one stable source-bound requirement per expected event field, variable,
   concerned tag, tag configuration field, firing condition, runtime
   parameter, destination request, consent condition, trigger/sequence
   contract, or declared client-side rule; and
2. one ordered event group for analyst feedback and final reporting.

For each requirement preserve the expected value, type, matching rule,
occurrence rule, page/state/action condition, source mechanism, GTM variable,
tag owner and configuration, firing or non-firing expectation, runtime
parameter, destination/vendor ID, and applicable browser request path.
Represent separate destinations as separate requirements. Ask only when an
ambiguity could materially change a verdict.

For every concerned tag, declare `tag_delivery` before execution:

- `browser_request` for analytics or media tags that send from the browser;
  require exact tag configuration, firing/count, runtime value/type,
  destination/event identity, request count, endpoint, and decoded parameters;
- `local_only` only for a genuinely local tag; do not invent a network layer.

Initialize the coverage ledger with the evidence layers derived from these
requirements:

```powershell
python scripts/init_coverage_ledger.py interpreted-requirements.json normalized-results.json `
  --run-id RUN-001 `
  --title "GTM recette" `
  --site-url https://example.test/ `
  --environment Preprod `
  --environment-class preprod `
  --container-id GTM-XXXX `
  --workspace Recette `
  --tracking-plan-source tracking-plan.xlsx `
  --acceptance-scope "Confirmed tracking-plan requirements"
```

### 2. Build complete but proportionate coverage

For every event group, enumerate every applicable interaction, placement,
branch, and material finite value. Use supplied routes and images first.
Otherwise explore the actual site and use the DOM census as discovery support:

```javascript
await page.addScriptTag({ path: "scripts/dom_interaction_census.js" })
await page.evaluate(() => window.__gtmRecetteCensus())
```

The census identifies candidates; execute real user-facing interactions through
the browser. Do not call one header item, menu item, card, CTA, footer link, or
product count representative of the family.

- Exhaust safe, practical finite sets. Counts 1 through 9 require nine isolated
  cases when the count can change payload or firing.
- Reset state between cases when prior actions can affect results.
- For large spaces, document semantic partitions, boundaries, and risk-based
  combinations.
- Create explicit cases for planned conditional, responsive, error-only,
  personalised, or experiment branches. Do not call an unacquired branch
  `PASS`.
- Explore relevant alternative routes before declaring an event unavailable.

Register each discovered case in the session ledger before acting. Give it the
event group, element, placement, material variant, discovery source, and
derived applicable layers. Do not collapse multiple placements or values into
one representative case.

### 3. Establish the controlled browser and Preview session

Use either an analyst-approved attached browser session or a dedicated
Playwright-capable profile. Follow the Tag Assistant operations reference for
extension attachment, existing authenticated profiles, connection recovery,
history clearing, and analyst handback.

Before verdict work, confirm:

- intended account, web container, workspace, Preview environment, and target
  origin;
- correct Tag Assistant tab and `Connected` status;
- each concerned tag's owning client-side container;
- the natural initial consent state; and
- stable identities for the website, GTM, Tag Assistant, and any applicable
  vendor-helper surfaces.

Initialize one resumable session ledger, register the controlled surfaces, and
reuse it for the whole run:

```powershell
python scripts/preview_session_ledger.py init session.json `
  --profile-path <controlled-profile> `
  --approved-origin https://example.test
```

Keep separate cursors and evidence when multiple containers must be tested
sequentially. Never merge their event histories.

Install the supplemental recorder at document start before navigation, then
start context-level request capture:

```javascript
await context.addInitScript({ path: "scripts/datalayer_recorder.js" })
```

The recorder helps preserve early, multi-argument, mutated-object, and
state-clearing pushes. It is never a substitute for exact Tag Assistant
`API Call` evidence when Preview-dependent layers apply. Capture requests at
browser-context level so unload, redirect, popup, iframe, service-worker, and
batched sends are not lost. Decode retained safe request records with:

```powershell
python scripts/decode_browser_requests.py requests.json decoded-requests.json
```

Recorder capture must never change the website's own `push` return value or
error. Check `window.__gtmRecetteJournal.checkIntegrity("dataLayer")` after a
reassignment or wrapper change. Treat `pushReplacedUnverified` as a capture
limitation rather than wrapping an unknown delegate twice. For a confirmed
custom array, call `window.__gtmRecetteJournal.watch("<layerName>")`.

Do not retain credentials, authorization headers, cookies, or raw sensitive
values.

If the journal records a candidate push that Tag Assistant does not show,
freeze the affected verdict and follow the discrepancy protocol in the Tag
Assistant operations reference. Recheck the correct page node, container,
origin, connection and full action-index window, then repeat once only when
safe. Supplemental capture may expose the gap; it cannot pass a required
Preview link.

### 4. Establish consent without silently changing it

Capture the natural/default event-level consent state. For an ordinary journey
with no consent acceptance requirement, make the normal CMP choice needed to
continue and mark consent-specific checks `NOT_TESTED`.

Test refusal, partial choice, change of choice, or Advanced Consent Mode v2 only
when required by the tracking plan. A banner click is not proof of event-level
consent state.

Never inject consent values as routine setup. If a defective or missing CMP
blocks the recette, show the blocker and ask the analyst before applying any
temporary browser-session override. State the exact values, method, scope,
limitations, and reversal, and keep natural-CMP evidence separate from the
override. A production exception requires explicit production-specific
authorization and restoration confirmation. An override can exercise
downstream tags but can never pass the native CMP implementation.

### 5. Run every event group in original order

For each case:

1. confirm the page, connection, consent state, and an observed quiet baseline;
2. mark the action boundary and previous Preview event index;
3. perform one exact real interaction or value variant;
4. verify the interaction itself completed through a safe non-tracking signal
   such as URL, visible state, control value, navigation, or success message;
5. record case and attempt identity, element, placement, URL/state, safe input,
   value type, completion signal, and timezone-qualified timestamp;
6. wait for the expected event or bounded timeout, then for the relevant
   business stream to settle under the adaptive quiet-window rule;
7. record first and settled final event indexes, chosen quiet window, timeout,
   settlement result, and reason;
8. inspect and classify every business `dataLayer` push in the action window,
   not just pushes with the expected event name;
9. capture applicable resolved state, variables, concerned-tag evidence,
   trigger/exception/sequence evidence, requests, consent, and direct errors;
10. assign independent component verdicts; and
11. validate and deliver the event verdict after all its cases, then continue
    automatically.

Use the ledger commands to enforce this sequence:

1. `register-case` before the first attempt;
2. `begin-action` with the case ID and prior Preview cursor;
3. `record-push` once for every observed business push, including companion
   and anomalous pushes; preserve the connection epoch when a reconnect resets
   Preview event indexes;
4. `settle-action` with the independently counted business-push total;
5. `record-layer` for every layer declared applicable to the completed case.

Final validation rejects a pending case, an unclassified or omitted push, an
open action, a missing applicable layer, or a normalized action boundary that
does not exactly match the retained attempt.

Never use the expected tracking event as proof that the website interaction
completed. If an overlay, stale locator, animation, validation error, or other
transient UI condition prevents the action, retain and reconcile that failed
attempt, restore a quiet baseline, and retry once with a new action ID. More
retries require an evidenced transient reason. If no valid action can be
completed, use `BLOCKED`, not an implementation `FAIL`. If tracking fires
during the failed attempt, keep it as possible premature or wrong-context
evidence.

Choose the quiet window from the observed baseline rather than from a fixed
sleep. Restart it after every acceptance-relevant business or state push;
unrelated technical noise alone need not keep the relevant window open. Extend
the bounded timeout only for evidenced application latency. If the relevant
stream never settles, do not pass or fail absence, count, or deduplication from
that incomplete window; block the affected occurrence evidence and state the
limitation.

Keep a gapless cursor from the first controlled load through the final action.
Classify each push against its trigger condition, page/state, causal action,
expected count, and order. This is how the recette detects duplicates,
premature, delayed, wrong-order, and wrong-context events, including planned
event names firing where they do not belong.

Within one Preview stream, identify a push by connection epoch plus event
index. Increment the epoch after a recorded disconnect/reconnect so a reused
index is not mistaken for a duplicate; never use an epoch change to hide an
unclassified window.

Treat an encountered form or authentication gate as part of the journey. Use
unique synthetic data and submit ordinary forms, registrations, and explicitly
authorized lead/conversion steps. Synthetic credentials may be created and
used ephemerally inside the controlled browser run; never put them in chat,
the ledger, evidence, or workbook. Reuse a safely created synthetic account for
its login case. A run-wide authorization remains valid for its stated safe
scope, origin, and environment, so do not ask again for each equivalent case.
It never covers protected credentials, MFA, CAPTCHA, verification, real
payment, or irreversible action. At such a checkpoint, prepare the journey,
ask the analyst to complete only that step, and resume. Never silently skip the
remainder.

### 6. Reconcile the independent evidence chain

For every applicable occurrence, compare in this order:

```text
tracking-plan requirement
-> occurrence, action window, count, context, and chronology
-> exact live Tag Assistant API Call / raw dataLayer.push
-> resolved Data Layer at that exact event
-> resolved GTM variable
-> concerned tag configuration
-> expected firing or non-firing status and fire count
-> runtime tag parameter value and type
-> expected client-side destination and decoded browser request value
-> applicable trigger, exception, sequence, consent, and client-side rules
-> requirement and event verdict
```

This chain is non-substitutive:

- Tag Assistant `API Call` is the authoritative raw push. Its `Data Layer`
  panel is resolved state and may include inherited values.
- Compare absent, JavaScript `undefined`, explicit `null`, empty string, empty
  array/object, value, and type exactly.
- A correct raw payload does not pass a wrong resolved variable, wrong
  configured tag value, wrong firing decision, wrong runtime value/type, or
  wrong outbound request.
- A fired tag does not prove correct configuration or runtime parameters.
- A correct runtime value does not prove the correct configured source.
- A browser-sending tag requires first-party browser-network evidence tied to
  the same action and container. GA4 “send ecommerce data” and Custom
  JavaScript inputs still require their exact resolved runtime values plus the
  decoded outbound request.
- A correct event name at a time when its trigger condition is false is
  `FAIL`.
- A duplicate beyond the allowed count, wrong action window, or wrong order is
  `FAIL`.
- An unplanned relevant business push is classified and retained. Use `FAIL`
  when it contradicts a confirmed expectation; use `REVIEW` only when the
  tracking-plan meaning itself is genuinely ambiguous.

When no push is expected, replace only the raw-push link with exact
`source_signal` evidence for the native GTM event, DOM/auto-event, enhanced
measurement, direct vendor call, or Custom HTML execution. Keep every
applicable downstream comparison.

Evaluate a declared business rule on the accepted source surface: the raw API
Call payload for `data_layer_push`, otherwise the captured `source_signal`
payload/value, with resolved Data Layer only as an evidenced fallback. Retain
the evaluation source and never allow malformed path syntax to pass.

Inspect only concerned tags: expected to fire, expected not to fire,
unexpected but relevant, or needed to explain non-firing. For a wanted tag that
does not fire, capture trigger evaluation, blockers/exceptions, relevant
variables, event-level consent, and direct Preview errors. If the cause is not
evidenced, write:

`Reason not established from available Preview evidence`

### 7. Validate and report each event incrementally

Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED`.

- `PASS`: the confirmed expectation is satisfied with exact evidence.
- `FAIL`: a completed, settled action or directly observed passive occurrence
  contradicts a confirmed expectation.
- `BLOCKED`: a documented external, protected, or upstream blocker prevented an
  attempted execution or made an applicable evidence layer unavailable.
- `REVIEW`: direct evidence exists, but a precise semantic question requires
  analyst judgement. Missing execution or evidence is not `REVIEW`.
- `NOT_TESTED`: deliberately outside the confirmed acceptance scope.

Use `PENDING` only inside the working ledger. It is never a final verdict.

The requirement and event status is the worst applicable component status.
Never allow a successful journey or upstream component to hide a downstream
failure.

Before announcing an event result, validate its complete atomic patch and then
apply it:

```powershell
python scripts/incremental_recette.py apply-event normalized-results.json event-001-patch.json `
  --session-ledger session.json
python scripts/incremental_recette.py validate-event normalized-results.json `
  --event-group-id EVG-001 `
  --session-ledger session.json
```

`apply-event` is transactional: if normalized or session reconciliation fails,
the working result must remain unchanged.

Give one immediate evidence-backed verdict and precise reason per event. Group
homogeneous successful cases compactly, but name every distinct failed,
blocked, or review variant and placement. Include cases executed/applicable,
raw push, resolved state, GTM variable, tag configuration/firing/runtime,
browser request, aggregate reason, and the exact website retest interaction for
non-PASS results. Do not wait until the final workbook to reveal failures.

### 8. Close coverage and build the workbook

Before completion, confirm that:

- every source-bound requirement and event group is present once in original
  order;
- every applicable case was attempted or has an explicit limitation;
- every observed business push is classified;
- raw, resolved, variable, configuration, firing, runtime, destination, and
  conditional layers each have their own evidence and verdict when applicable;
- all ordinary gates were completed and protected checkpoints were offered to
  the analyst;
- unexpected events and tags remain visible; and
- no sensitive raw content is stored in the normalized data or report.

Run the final deterministic checks and workbook build:

```powershell
python scripts/incremental_recette.py final-validate normalized-results.json `
  --session-ledger session.json
python scripts/validate_business_rules.py normalized-results.json
python scripts/scan_sensitive_data.py normalized-results.json
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict `
  --session-ledger session.json
```

Reload the workbook and verify sheets, row counts, filters, hyperlinks,
structured values, wrapped notes, and status formatting. If strict validation
fails, the recette is incomplete.

Finish with every planned event in original order and its aggregate status.
Keep each component failure and affected case visible beneath the event
roll-up. State exact missing or blocked evidence instead of implying
completion.
