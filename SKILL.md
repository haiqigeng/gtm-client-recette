---
name: gtm-client-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rules. Use for plan-ordered analytics and media-tag QA in a Playwright MCP-managed headed Microsoft Edge session, with material-scenario coverage, continuous dataLayer anomaly detection, GTM and browser-delivery reconciliation, business-reality checks, immediate per-event/per-layer feedback, and a validated XLSX. Excludes tracking-plan design, GTM mutation or publication, server-side certification, implementation fixes, and legal consent decisions.
---

# GTM Client Recette

## North star

Maximize trustworthy findings per expensive browser interaction. Behave like an expert
analyst doing recette: decide whether each measurement claim describes the real interaction,
not merely whether an event exists or a tag fired.

A technically coherent chain is still `FAIL` when the page is dead, the wrong target is
bound, the action fails, a populated cart sends no products, a form event precedes a
failed submission, or an uncaused event appears between planned interactions.

## Authority and boundaries

Require an existing tracking plan or explicit acceptance rules. Invocation authorizes
ordinary reversible navigation, synthetic test data, visible interactions, and ordinary
form submissions in scope; do not ask for separate permission. Pause only for
credentials, MFA, CAPTCHA, verification links/codes, external approval, real payment, or
another protected/consequential gate.

Do not design or weaken the plan, change/publish GTM, fix the site, certify server-side
processing/vendor receipt, bypass protected gates, or issue legal consent conclusions.
Separate client defects, plan gaps, setup/binding errors, evidence limits, protected
gates, and agent execution errors.

## Default inspection contract

For every event, always report these five layers in this order:

1. **Page/action reality** — reachable non-404 page, intended route/state, successful
   interaction/outcome, and visible business anchors.
2. **Data Layer API Call** — the exact fully expanded Tag Assistant API Call on the
   selected occurrence, including occurrence count, planned fields, JSON types, values,
   and every unplanned business push in the action window.
3. **GTM Tags** — concerned fired/non-fired inventory, effective configuration/mapping,
   firing count, and runtime values. A tag may fire on a causally following Trigger
   Group; stop before the next unrelated business event.
4. **Browser request** — applicable logical hit, event/destination, planned parameters,
   request outcome, and duplicate/retry behavior. Use `NOT_APPLICABLE` when the plan
   creates no browser-delivery obligation.
5. **Surrounding behavior** — missing, duplicate, premature, delayed, interjected,
   stale, contaminating, or otherwise implausible behavior around and between actions.

The tracking plan is the baseline. For every destination-applicable planned field,
compare the selected scenario's value independently at API Call, effective tag mapping,
tag runtime, and browser request. The same dynamic value may differ across product,
language, shipping, or payment scenarios, but it must agree across surfaces inside one
scenario. A tag proving 1 of 12 planned fields fails the 11 absent mappings/runtime
values when detail is complete. Generic ecommerce forwarding counts only when effective
configuration or runtime proves it.

The normal source authority is the fully expanded Tag Assistant **API Call**. A proven
call-time dataLayer recorder is conditional stronger evidence only when the API Call is
unavailable/incomplete or exact pre-GTM invocation behavior matters. A state-only dataLayer
update remains valid source without an invented event.

The accumulated Tag Assistant **Data Layer** tab and **Variables** tab are not mandatory
defaults. Open them only for an explicit `state_path`/`resolved_path`, ambiguity, stale
state investigation, or mapping diagnosis. Consent, acquisition, forms, media,
protected-gate, and direct-recorder checks are likewise conditional. Evidence confidence,
scenario coverage, and data safety are automatic gates shown when non-pass.

Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, `NOT_APPLICABLE`, and `PENDING`. Missing or
partial evidence blocks only its dependent checks; it never triggers a cleanup reload or
prevents per-event feedback.

## Operating workflow

Resolve `<skill-root>` as this file's directory. The normal CLI loop is
`init -> next -> complete -> finish`; use
`python -B "<skill-root>/scripts/recette.py" --help` for exact syntax.

### 1. Intake once and prepare the browser early

Ask once for the plan/rules, unresolved client tag category if the plan cannot resolve
it, known protected prerequisites, and whether the user is ready. State that after
`ready` you will open one blank headed managed Edge window for them to prepare GTM/Tag
Assistant, the target site, authentication, and ordinary consent.

Do not ask for URL, environment, container, destination, synthetic-data permission, or
ordinary submission permission when the plan/prepared runtime can resolve them. After
`ready`, read [browser and Preview](references/browser-and-preview.md), open `about:blank`
immediately, and start `init` while the user prepares the window.

The user handles login and accepts the ordinary consent banner. If consent is not ready,
ask the user to accept it before measurement; do not build vendor-specific CMP automation.
Leave consent denied/untouched only for an explicit consent scenario. Setup loads are not
Core evidence.

### 2. Compile once, locally and losslessly

Compile JSON, YAML, CSV/TSV, supported XLSX, or a supported handoff directly. Classify
every workbook sheet, ignore classified code/examples, continue recognized variable
tables across visual blanks, preserve exact machine identifiers/case, reconcile event
indexes to detail sheets, and expose compiled/ignored rows. Orphan or ambiguous rows stop
intake; malformed later events stay localized and must not delay the first executable
event.

Do not prebuild all scenarios, reports, browser ledgers, or future-event evidence. Broad
“all planned” scope resolves through actual plan identities or one concise category,
never as a literal runtime tag/destination.

### 3. Freeze setup once

Inspect the prepared managed tabs once. Derive origin, Preview session, natural active
container, workspace, and observed destinations. Record one capability profile and one
`setup_boundary` containing the current Preview epoch/index, ordinary/explicit consent
context, and optional binding.

A wrong provider/channel/profile stops before interaction. An unavailable surface blocks
only dependent checks; do not probe alternate browsers or private methods. For Core,
perform exactly one action-card-authorized measured navigation after the setup cursor.
Never add a second “clean” reload.

### 4. Choose one material scenario just in time

Read [scenario coverage](references/scenario-coverage.md) only when choosing the current
event branch. Combine plan values with visible controls, live values, routes, and platform
semantics. Exhaust manageable finite and reachable dependent values. For products/content
or another high-cardinality population, test one representative per materially distinct
behavior signature plus applicable boundaries/exceptions; do not brute-force equivalent
members.

Call `next` for the earliest safe high-information event/scenario. It freezes one
`OBSERVE_CURRENT`, `NAVIGATE_ONCE`, or `INTERACT_ONCE` action, document policy, Preview
cursor, planned fields, and known dimensions. Perform exactly that interaction once.

Read [protected journeys](references/protected-journeys.md) only when consent variation,
acquisition, forms, authentication, CAPTCHA, payment, or another protected journey is
actually involved.

### 5. Capture once and emit feedback immediately

Read [verdict and output](references/verdict-and-output.md) before the first `complete`.
Use the paste-ready `playwright_completion.code` returned by `next` once after the action;
it needs no import, local-file access, or handwritten panel normalization. It returns the
current page/binding, a canonical bounded Preview delta, and a privacy-safe resource-
timing network fallback. Prefer the native Playwright/MCP action-bounded request delta
when available and pass it as `network`; never persist cookies, authorization headers,
or unrelated full-browser traffic.

The collector reads every post-cursor event name, every business API Call needed for
chronology, complete concerned tag inventory, and deep detail only for concerned tags.
It has one five-second pass and one semantic selector fallback. If any component remains
partial, submit the partial bundle: `complete` must return explained `BLOCKED` rows, not
reload, replace the browser, or wait indefinitely.

`complete` commits and judges once. It always emits per tested event and persists that feedback
before the next action. Show all five default layers, each status and
passed/total subchecks. For every non-pass layer show the exact reason, affected fields,
observed versus expected when available, `Check next`, and evidence IDs. The GTM row must
separate inventory, mapping, firing, and runtime counts. Keep detailed claim rows in
canonical JSON/XLSX.

One action may produce multiple Preview rows and causally co-occurring planned events,
but never hide a second user interaction. Inspect every intervening source/API message.
An unexpected `add_to_cart` between `view_item_list` and `view_item`, a duplicate from
one click, or a later anomaly that changes an earlier verdict must be surfaced and may
revise prior feedback.

### 6. Expand only from material evidence

Update only the affected event's scenario tree after each action. A plan-omitted live
value becomes a visible plan gap and another scenario only when it changes or may change
behavior. Repeat an event/scenario only with a structured retest basis: an evidence-defect
record or explicit user-request record. Distinct material scenarios are not repeats.

### 7. Finish once

Finish only when every event has an honest final confidence/coverage decision and no open
action or protected handoff remains. Deliver plan-ordered conclusion Markdown, canonical
JSON, validated XLSX, defects, limitations, and exact retest targets. The deterministic renderer owns every
status; analyst reasoning may only add an evidence-backed `FAIL` or
`REVIEW`.
