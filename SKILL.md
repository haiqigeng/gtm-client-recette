---
name: gtm-client-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rules. Use for plan-ordered analytics and media-tag QA in the user's already-open Chromium session, with material-scenario coverage, continuous dataLayer anomaly detection, GTM and browser-delivery reconciliation, business-reality checks, per-event feedback, and a validated XLSX. Excludes tracking-plan design, GTM mutation or publication, server-side certification, implementation fixes, and legal consent decisions.
---

# GTM Client Recette

## North star

Maximize trustworthy findings per expensive browser interaction. Judge whether one
measurement claim is true in one material real-world scenario; do not merely prove that
an event exists or a tag fired.

A coherent technical chain still fails when reality is wrong: the page is dead, the
wrong container is active, the action did not succeed, a populated cart becomes empty
ecommerce data, a form event precedes failure, or an unrelated event appears between
interactions.

## Scope and authority

Require an existing plan or explicit acceptance rules, an approved origin/environment,
the client tag scope, and a run directory outside this skill. Summarize that boundary
once and proceed only when it is approved. Use ordinary reversible interactions and
synthetic test data within scope.

Resolve scope before browser work. A phrase such as "all planned client-side tags" means
the exact event tags/destinations actually declared in the plan; if none exist, `init`
must fail quickly and request a concise accepted category such as GA4/Google Ads and any
destination that must be certified. Never use broad prose as a literal runtime identity.

Reuse the user's already-open Chromium target and GTM Preview/Tag Assistant tabs. Do not
replace a usable signed-in session, open an authentication loop, or create another
browser as normal recovery. Re-prove only the live identity or capture surface affected
by a correction. A repeated full handshake needs an explicit correction/retest reason.

Pause at credentials, MFA, CAPTCHA, magic links, external approval, real payment, or
another protected/consequential gate. Never bypass it. Do not design the plan, change or
publish GTM, fix the site, certify server processing/vendor receipt, or make a legal
consent judgement.

## Inspection model

Compile plan rows losslessly into typed proof obligations: occurrence, value/state,
relationship, ordering, transport, and negative claims. A state-only dataLayer update or
source-only field must not inherit invented event, tag, or request requirements.

Group applicable checks into six diagnostic domains, not six sequential browser stages:

1. **Reality** - reachable/live page, correct scenario, visible state, action outcome,
   and independent business anchors.
2. **Source signal** - the exact fully expanded Tag Assistant API Call or a proven
   call-time dataLayer/direct-source observation, including JSON types,
   absent/null/empty states, occurrence, order, and unplanned pushes.
3. **GTM decision** - active container/Preview identity, matching GTM event, resolved
   variables, relevant tag configuration, consent/trigger controls, and firing count.
4. **Destination delivery** - runtime payload, logical vendor hit, destination and tag
   identity, browser transport, redirects/retries, response outcome, and non-send proof.
5. **Surrounding behavior** - duplicates, missing/premature/delayed/interjected events,
   contaminating state, stale item/cart values, and cross-surface disagreement.
6. **Data safety** - sensitive values in persisted evidence and reports.

Evidence confidence and scenario completeness are closure gates, not extra layers. Each
surface proves only itself. Missing source cannot be laundered through Preview; a fired
tag cannot substitute for its request; agreement between empty surfaces cannot prove a
populated business state. Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, `NOT_APPLICABLE`, and
`PENDING`; final reports display `PASS`/`FAIL` as `OK`/`KO`.

For an ordinary planned dataLayer event with a browser-sending tag, inspect these
applicable operational surfaces from the same action: page/action reality; call-time
dataLayer API Call; Tag Assistant event and accumulated Data Layer state; Tag Assistant
Variables; complete concerned fired/not-fired tags; concerned tag configuration and
effective mapping; tag runtime parameters; decoded browser request/destination; and the
continuous surrounding stream. Safety, confidence, and coverage are always reported.
Consent, acquisition, forms, trigger/sequence detail, media, and protected gates activate
only when relevant. This is an applicability rule, not a serial layer ceremony.

The normal source authority is a fully expanded Tag Assistant API Call. A proven
call-time/document-start capture is conditional stronger evidence when the API Call is
unavailable, incomplete, or exact pre-GTM invocation behavior matters.
The Tag Assistant **Data Layer** tab is post-message
accumulated state: inspect it separately, but never use it to prove what one push sent.
For every destination-applicable planned field, compare the plan predicate independently
with source, accumulated GTM state, resolved Variables, effective tag mapping, tag runtime,
and decoded request. A tag exposing one of twelve required fields fails the eleven missing
applicable mappings/values when those surfaces were completely captured.

Read [verdict and output](references/verdict-and-output.md) before judging the first
event.

## Fast vertical workflow

Resolve `<skill-root>` as this file's directory. Use
`python -B "<skill-root>/scripts/recette.py" --help` for the authoritative nine-command
interface.

1. Run `init` once. It directly compiles accepted JSON/YAML/delimited plans and supported
   XLSX layouts, including common event-metadata plus variable-table sheets. It does not
   prebuild future scenarios, event ledgers, layer rows, or reports. Reconcile row counts
   and ignored rows; code examples are not requirements. An orphan/ambiguous row stops
   intake, while a malformed later event is localized and cannot delay the first valid
   event.
2. Attach to the existing target and Preview session while compiling. Start continuous
   lightweight network/event observation and perform one bounded capability/identity
   handshake. Use fully expanded Preview API Call arguments as the normal source path;
   attempt a document-start recorder only when that path is insufficient. Reuse a valid
   current Core/page load; create at most one initial load when one is actually needed.
   Never generate a second clean repeat without a named evidence defect and retest reason.
3. Select the earliest safe, high-information event. Discover only its material scenario
   branches just in time.
4. The first `begin` carries the single capability/binding/health handshake and page
   before-state. Later `begin` calls carry only the page before-state plus any unbound
   continuous deltas between interactions. Perform the real interaction once, then
   `commit` current after-health/page and source/network/lifecycle deltas. Stale captures
   cannot be relabelled as current. Emit the immediate per-layer pulse; it is
   provisional and can never certify `PASS`.
5. Continue a short natural action cluster only while document, action, tag and logical
   hit identities remain unambiguous. Inspect every intervening source message, including
   messages not named in the plan.
6. Run `sync-preview` with Preview evidence only, once for all new indexes in the cluster.
   Capture complete
   event and concerned-tag summaries; deep-read the Variables, configuration, effective
   mapping and runtime needed by current planned fields, plus suspicious details. Never
   scan unrelated historical domains or the whole container. Synchronize earlier if
   navigation, ambiguity, or risk could lose evidence.
7. Emit canonical feedback as soon as all known material scenarios for an event close.
   Choose the next branch by information value and transition cost, not by creating the
   whole run up front.
8. `finish` only after global reconciliation. It refuses open actions, unresolved
   protected handoffs, incomplete material coverage, unclassified material observations,
   evidence-confidence gaps, or privacy blockers. `report` rebuilds only a frozen run;
   `reopen` requires explicit authorization.

Corrections invalidate only dependent proof. Distinguish website defects, plan
ambiguity, control-tool failures, evidence limitations, and protected gates. Never use
alternate state files or command routes to manufacture progress.

The same event/scenario may run again only with a concise `--retest-reason`; a distinct
material scenario remains a distinct action. This prevents automatic clean repeats
without limiting language, shipping, payment, product-signature, or other scenario
coverage.

After navigation or reload, retain the old page as the before-state but rebind the new
document before attributing post-navigation evidence. A proved old-to-new transition is
normal; mixed post-action documents or an unproved new binding remain blocked.

Read [browser and Preview](references/browser-and-preview.md) before attaching or
recovering the session.

## Material scenario coverage

The plan is an acceptance oracle, not a complete catalogue of live values. Discover
dimensions from the plan, visible UI, current journey state, captured evidence, and
known platform semantics.

- Exhaust every manageable finite material value, including live values omitted by the
  plan.
- Test reachable dependent combinations such as country-specific shipping methods; do
  not build an irrelevant global Cartesian product.
- For high-cardinality populations such as products, partition by behavior signature
  and test ordinary, contrasting, boundary, and exception representatives. Never
  brute-force every member or compare dynamic labels to one global literal.
- Keep strict contextual expectations: `page_language` may be `en` in one scenario and
  `fr` in another; fixed enums and per-scenario product/cart identities remain strict.
- Record plan gaps and expand coverage after a new signature, material value, anomaly,
  conditional branch, or failure. Unknown material branches stay `BLOCKED`/`REVIEW`.

Read [scenario coverage](references/scenario-coverage.md) just before selecting the
current event's branches.

## Special journeys

Complete ordinary forms with synthetic data and independently prove validation,
submission, and visible success/failure. Treat consent and acquisition as scenario
dimensions when applicable. A simulated fresh/referral visit tests the tracking response
and must state its method; it does not prove SEO ranking or a real search impression.

Read [protected journeys](references/protected-journeys.md) when forms, consent,
acquisition, authentication, CAPTCHA, or payment is involved.

## Required feedback

After each completed event, provide:

- a compact scenario matrix and six-domain summary;
- one operational row and status for every applicable layer/check, including page/API,
  call-time dataLayer/API Call, Tag Assistant Data Layer state, Variables, fired/not-fired
  inventory, each concerned tag's configuration/effective mapping/firing/runtime, browser
  request/destination, anomaly, safety, confidence, and coverage;
- status, simple observed-versus-expected detail, exact `Check next` target, and stable
  evidence reference for every row;
- concerned tags, anomalies, tested values/signatures, plan gaps, limitations, and exact
  retest instructions.

Identical passing rows may be grouped across scenarios, but every differing value and
every `FAIL`, `BLOCKED`, or `REVIEW` remains scenario-specific. A later cross-event
anomaly may amend earlier feedback.

At the end, deliver a plan-ordered conclusion plus validated XLSX, Markdown, JSON, defect
and retest views. The deterministic renderer owns every claim, row, domain, scenario,
event, and final status. Analyst/AI reasoning may only add an evidence-backed `FAIL` or
`REVIEW`; it cannot upgrade or suppress an objective result.
