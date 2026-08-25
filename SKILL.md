---
name: gtm-client-recette
description: Execute a personal client-side GTM acceptance recette from one XLSX tracking plan in one headed Playwright MCP browser, with fixed five-layer evidence, material-scenario coverage, continuous anomaly detection, immediate event feedback, and one final XLSX.
---

# GTM Client Recette

## North star

Maximize trustworthy findings per browser interaction. A coherent tracking chain is still
wrong when it contradicts the real page, selected control, performed action, or visible
outcome. Test every planned event and every materially different scenario, preserve every
intervening business API Call, and explain each verdict before continuing.

## Fixed personal contract

- Input is exactly one `.xlsx` tracking plan.
- Browser is exactly one headed standalone Playwright MCP context opened by the agent.
- Output is immediate per-event feedback plus one final
  `gtm-client-recette-results.xlsx`.
- There are no alternate formats, browsers, modes, scopes, flags, retries, fallbacks,
  repair paths, or backup workflows.
- Ordinary navigation, synthetic values, interactions, and form submissions are in scope.
  The user handles credentials, MFA, CAPTCHA, verification, real payment, and ordinary
  consent in the same Playwright window when needed.

Do not design the tracking plan, change or publish GTM, modify the website, certify
server-side/vendor receipt, bypass protected controls, or make legal consent conclusions.

## Fixed five-layer proof

Every event always reports these rows in this order:

1. **Page/action reality** — reachable non-404 page, intended state, selected values,
   performed interaction, and visible outcome.
2. **Data Layer API Call** — the exact fully expanded Tag Assistant API Call, occurrence,
   planned fields, JSON types, values, and every intervening business call.
3. **GTM Tags** — concerned tag inventory, mapping, firing count, configuration, and
   event-time runtime values from Tag Assistant Names/Values.
4. **Browser request** — attributable client request, destination, planned values,
   response/failure, duplicates, and retries.
5. **Surrounding behavior** — missing, duplicate, premature, delayed, interjected, stale,
   contaminating, or business-implausible behavior.

The acceptance baseline is the tracking-plan rule plus the actual interaction context.
Compare every planned field independently at API Call, GTM mapping/runtime, and browser
request. Cross-layer equality is only supporting evidence: a chain can be coherently
wrong. If the UI proves quantity `1` while API Call, tag, and request all contain `2`,
those three layers fail.

Do not inspect the accumulated Data Layer tab, GTM Variables tab, consent panels, or a
direct dataLayer recorder. If a mandatory surface is unavailable, report its dependent
checks `BLOCKED`; never substitute weaker evidence.

## Fixed workflow

Resolve `<skill-root>` as this file's directory.

1. Ask only for the XLSX, known protected prerequisites, and whether the user is ready to
   prepare GTM Preview.
2. After `ready`, open one headed Playwright MCP window at `about:blank` immediately.
   Start local XLSX compilation while the user prepares Tag Assistant, the target site,
   login, and ordinary consent.
3. Run:

   ```text
   python -B "<skill-root>/scripts/recette.py" start "<plan.xlsx>" "<new-run-dir>"
   ```

   The run directory must be absent or empty. Any invalid or ambiguous workbook stops
   before measurement with exact sheet/row errors.
4. Once Preview and the target are ready, execute
   `scripts/playwright_collector.js` once through Playwright MCP. Reuse that observer for
   the complete run. It returns `current_cursor` and `current_document_cursor`. If it
   cannot bootstrap, stop; do not choose another browser.
5. Run `recette.py next "<run-dir>" <preview-cursor>`. For the first Core action, pass
   `current_document_cursor` so the prepared document is inspected without reloading. For
   another first action, pass `current_cursor`. Thereafter pass the exact cursor returned
   by the preceding `complete`. The command returns the only open action card. Choose the
   material scenario from plan values, visible controls, live routes, and prior evidence.
6. Use exactly one Playwright code execution for the scenario. In that execution: locate
   the existing target and Tag Assistant pages; attach an action-bounded request listener;
   capture the before reality anchor; perform exactly one interaction; wait only for its
   explicit visible outcome and relevant activity; capture after reality; invoke
   `globalThis.__gtmRecetteCollect` once in Tag Assistant; detach the listener; and return
   one minimal bundle. Never split these into exploratory panel calls. For Core, observe
   the attributable current prepared document; do not create a setup or cleanup reload.
   The bundle must contain matching `action_id`/`event_id`, the observer contract and
   cursor, `scenario {id, signature, values}`, `coverage {complete, rationale, remaining,
   unreachable}`, `reality {complete, attributable, page, outcome, expected, findings}`,
   the collector's `source`/`gtm`/`behavior`, and `network {complete, attributable,
   requests, findings}`. Normalize request parameters to plan paths only from the captured
   request; never guess missing values.
7. Save the returned canonical bundle as
   `<run-dir>/evidence-<action-id>.json` and run:

   ```text
   python -B "<skill-root>/scripts/recette.py" complete "<run-dir>" "<run-dir>/evidence-<action-id>.json"
   ```

   Show its five-layer feedback immediately. Do not begin another action first.
8. Repeat `next -> one Playwright observation -> complete` until every material branch is
   final, then run `recette.py finish "<run-dir>"` once.

## Scenario and anomaly rules

Scenario selection runs for every event. Exhaust manageable finite and reachable values
such as language, shipping, payment, login, and cart state. For products/content or any
high-cardinality population, test one representative per materially different behavior
signature plus boundaries and exceptions; never enumerate equivalent members. A live
plan-omitted value becomes a visible plan gap and another scenario when it may change
occurrence, payload, tag, request, outcome, or verdict.

The observer cursor is continuous. Inspect every business API Call since the previous
cursor, including calls between interactions and causal technical rows such as Trigger
Groups. Never hide a second interaction or discard an unexpected event.

## Feedback, blocking, and stopping

Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, `NOT_APPLICABLE`, and `PENDING`. Every non-pass
layer states the exact reason, affected fields/checks, expected versus observed, and the
target a human should inspect next.

A real tracking `FAIL` never stops execution. One blocked event also does not stop the
run. Increment the consecutive-zero-evidence counter only when all five layers are
`BLOCKED` and no attributable evidence exists. Reset it whenever a later event has any
usable attributable evidence. After two consecutive zero-evidence events, emit the
second feedback and stop without reload, retry, browser switch, repair, or final XLSX.

Fail immediately before or during execution when the fixed contract itself is broken:
invalid XLSX, unavailable Playwright MCP, unusable Preview/target preparation, corrupted
run state, mismatched action identity, or lost observer contract. Never reopen or salvage
an invalid run; start a new run after correcting the environment.
