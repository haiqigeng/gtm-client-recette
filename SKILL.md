---
name: gtm-client-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rules. Use for plan-ordered analytics and media-tag QA in a Playwright MCP-managed headed Microsoft Edge session, with material-scenario coverage, continuous dataLayer anomaly detection, GTM and browser-delivery reconciliation, business-reality checks, per-event feedback, and a validated XLSX. Excludes tracking-plan design, GTM mutation or publication, server-side certification, implementation fixes, and legal consent decisions.
---

# GTM Client Recette

## North star

Maximize trustworthy findings per expensive browser interaction. Judge whether one
measurement claim is true in one material real-world scenario; do not merely prove that
an event exists or a tag fired.

A coherent technical chain still fails when reality is wrong: the page is dead, the
wrong container is active, the interaction failed, a populated cart becomes empty
ecommerce data, a form event precedes submission failure, or an unrelated event appears
between interactions.

## Authority and boundaries

Require an existing tracking plan or explicit acceptance rules and a client-side tag
scope. Invocation authorizes ordinary reversible navigation, interaction, synthetic test
data, and ordinary form submission inside that test scope. Do not ask separately for
those permissions. Pause only at credentials, MFA, CAPTCHA, magic links, external
approval, real payment, or another protected/consequential gate.

Do not design the plan, change or publish GTM, fix the site, certify server-side
processing/vendor receipt, or make a legal consent judgement. Keep the run directory
outside this skill. Distinguish client defects, plan gaps, setup/binding problems,
evidence limitations, protected gates, and agent execution errors.

## Inspection model

Compile accepted plan rows into typed occurrence, value/state, relationship, ordering,
transport, and negative proof obligations. A state-only dataLayer update or source-only
field must not inherit an invented source event, tag, or browser send.

Use six diagnostic domains, not six serial browser stages:

1. **Reality** - live/reachable page, intended scenario, visible state, successful action,
   and independent business anchors.
2. **Source signal** - exact fully expanded Tag Assistant API Call or proven call-time
   dataLayer/direct-source observation, with JSON type, state, count, order, and unplanned
   pushes.
3. **GTM decision** - current container/Preview identity, GTM event, accumulated Data
   Layer state, Variables, concerned tag configuration/effective mapping, consent/control,
   and firing count.
4. **Destination delivery** - tag runtime values, logical hit, destination/tag identity,
   decoded browser request, retries/redirects, outcome, and complete-window non-send.
5. **Surrounding behavior** - duplicate, missing, premature, delayed, interjected, stale,
   contaminating, or cross-surface behavior.
6. **Data safety** - sensitive values retained in evidence or output.

Evidence confidence and scenario completeness are closure gates. Each surface proves
only itself: accumulated state cannot prove one API call; tag firing cannot prove its
request; matching empty technical surfaces cannot prove an empty real cart. Use `PASS`,
`FAIL`, `BLOCKED`, `REVIEW`, `NOT_APPLICABLE`, and `PENDING`.

For an ordinary planned browser-delivered event, inspect from the same action:

- page/action reality and current binding;
- the exact Data Layer API Call;
- the matching Tag Assistant event and accumulated Data Layer state;
- GTM Variables;
- complete concerned fired/non-fired inventory;
- each concerned tag's configuration, effective field mapping, firing, and runtime;
- decoded browser request, destination, and outcome;
- every intervening source/Preview message and surrounding anomaly;
- safety, evidence confidence, and scenario coverage.

Consent, acquisition, form, media, trigger/sequence, and protected-gate checks activate
only when applicable. For every destination-applicable planned field, compare the plan
predicate independently on every applicable source, GTM, runtime, and request surface.
A tag exposing one of twelve required fields fails the eleven missing mappings/values
when those surfaces are complete.

The normal source authority is the fully expanded Tag Assistant **API Call** on the exact
Preview occurrence. A proven document-start recorder is conditional stronger evidence
only when that API Call is unavailable/incomplete or exact pre-GTM invocation behavior
matters. The Tag Assistant **Data Layer** tab is accumulated post-message state and stays
a separate check.
The call-time dataLayer observation and accumulated state must never be conflated.

## Ordered operating workflow

Resolve `<skill-root>` as this file's directory. The public loop is only
`init -> next -> complete -> finish`; use
`python -B "<skill-root>/scripts/recette.py" --help` for exact CLI syntax.

### 1. Minimal intake, then browser preparation

Ask once for the plan/rules, the client tag category only if the plan does not resolve
it, any known protected prerequisites, and readiness to prepare the managed browser.
State: after the user replies `ready`, open one blank headed managed Edge window; the user
can sign in and prepare GTM Preview there, and the target site will be opened in that
window. Do not ask up front for target URL, environment, GTM container, destination, or
submission permission when they can be derived from the plan and prepared runtime.

When the user is ready, read [browser and Preview](references/browser-and-preview.md),
open `about:blank` immediately, and let the user prepare authentication, Preview, and the
site while `init` compiles the plan. A site load used to establish login/consent is setup,
not Core evidence. If consent is already granted, keep final Connect/target navigation
until the first action card so that load becomes Core evidence.

### 2. Compile and reconcile before the first action

Run `init` once. Origins may be absent at intake and derived from the plan or prepared
runtime. Compile JSON/YAML/delimited plans and supported XLSX layouts directly. For XLSX,
account for every sheet, continue recognized variable tables across blank rows, ignore
classified code/examples, preserve exact machine identifiers/case, and reconcile index
events against requirement sheets. An orphan row stops intake; an index-only or malformed
later event is localized and must not delay the first executable event.

Do not prebuild all scenarios, layer ledgers, tag inventories, or reports. Resolve broad
"all planned" scope through actual plan identities or a concise accepted category; never
use prose as a literal runtime tag/destination.

### 3. Verify the prepared runtime once

Record the configured Playwright MCP provider, headed managed Edge channel/profile, and
available capabilities once; do not require an exact package version or guess absent
tools. A wrong provider/channel/profile stops before action. An unavailable evidence
surface blocks only dependent claims and must not trigger minutes of fallback probing,
another browser, or an automatic repeat.

Derive the expected origin, Preview session, natural container, workspace, and observed
destinations from the prepared tabs. Re-prove the action document and binding after the
measured navigation. A wrong/unattributable binding is `BLOCKED` setup evidence, not a
client implementation `FAIL`.

For an ordinary run, accept the CMP banner during preparation when consent is not already
granted. Then perform exactly one action-card-authorized Core load. If persistent consent
was already granted, the first post-`next` target load can be Core directly. Do not add
two "clean" reloads. Leave consent untouched/denied only when that scenario is explicitly
requested.

### 4. Select and freeze one material action

Read [scenario coverage](references/scenario-coverage.md) just before choosing the current
event branch. Discover dimensions from the plan, UI, live evidence, and platform
semantics. Exhaust manageable finite values and reachable dependent branches. For a
high-cardinality population, test one representative per materially distinct behavior
signature, plus applicable boundaries/exceptions; do not brute-force equivalent items.

Call `next` for the earliest safe, high-information event/scenario. It freezes one
`OBSERVE_CURRENT`, `NAVIGATE_ONCE`, or `INTERACT_ONCE` action and its document policy,
Preview cursor, planned fields, and known scenario dimensions. Perform exactly that
interaction once.

Read [protected journeys](references/protected-journeys.md) only when consent,
acquisition, forms, authentication, CAPTCHA, or payment is involved.

### 5. Capture once and judge immediately

Read [verdict and output](references/verdict-and-output.md) before the first `complete`.
After the action settles, call `complete` once with current binding/health/page,
continuous source/network/lifecycle deltas since the prior boundary, and exactly the new
Preview indexes after the frozen cursor. Capture Preview once for the action: event list,
exact API Call, accumulated Data Layer state, Variables, concerned tag details/runtime,
and every intervening message. Filter network evidence to concerned analytics/media sends,
failed transports, and suspicious requests; never persist cookies or unrelated traffic.

One interaction may produce several Preview indexes or satisfy causally co-occurring
planned claims, but it cannot contain a second user interaction. A browser/control violation
preserves useful evidence and blocks confidence; it never creates a client
failure or starts a cleanup repeat.

`complete` must emit compact per-event feedback immediately even when coverage is still
`PENDING` or invalid. Coverage gaps affect closure, not evidence ingestion. Show one row
per operational layer with status, concise observed-versus-expected exceptions, exact
`Check next`, and evidence IDs. Keep all detailed claim rows in canonical JSON/XLSX.

### 6. Expand only when evidence requires it

Update the current event's scenario tree after each action. Preserve plan-known dimensions
and constraints even if an annotation omits or weakens them. Test a second
high-cardinality member only when it represents another known signature or an
anomaly/boundary/exception. Inspect every intervening source message; a later
between-action anomaly may revise prior feedback in the same model pass.

Repeat the same event/scenario only with a structured retest basis: the affected action or
machine-capture record for an evidence defect, or explicit user authorization. A
successful evidence-defect retest supersedes only the same event slice and scenario; it
does not erase real client failures. Distinct language, shipping, payment,
product-signature, consent, or other material scenarios remain distinct actions.

### 7. Finish once

`finish` only after every event has an honest final confidence and coverage decision and
no open action/protected handoff remains. `report` renders the frozen run once; `reopen`
requires explicit authorization. Deliver the plan-ordered conclusion, canonical JSON,
Markdown, validated XLSX, defects, limitations, and retest targets. The deterministic renderer owns every
claim, row, domain, scenario, event, and final status; analyst reasoning may only add an
evidence-backed `FAIL` or `REVIEW`.
