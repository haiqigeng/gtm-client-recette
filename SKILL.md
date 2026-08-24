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

Playwright MCP `0.0.79` is the default browser contract. Launch one headed managed Edge
window with its persistent workspace profile; open and reuse one target tab and one GTM
Preview/Tag Assistant tab there. The default path needs no browser extension. Existing-
window attachment is an explicit scope fallback only, never an automatic recovery path.
If the configured Playwright runtime, version, channel, profile, or self-check is wrong,
stop before opening an action rather than trying guessed methods or another browser.

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
`python -B "<skill-root>/scripts/recette.py" --help` for the authoritative command
interface. The browser loop is only `init -> next -> complete -> finish`; internal
capture stages are not public agent choices.

1. Run `init` once. It directly compiles accepted JSON/YAML/delimited plans and supported
   XLSX layouts, including common event-metadata plus variable-table sheets. It does not
   prebuild future scenarios, event ledgers, layer rows, or reports. Reconcile row counts
   and ignored rows; code examples are not requirements. An orphan/ambiguous row stops
   intake, while a malformed later event is localized and cannot delay the first valid
   event.
2. While compilation runs, start the configured Playwright MCP server with headed Edge,
   its persistent profile, core tools plus config self-check, and no extension/vision
   coordinates. Verify the pinned version and callable tools once. The first `next`
   persists only that cheap runtime/operation baseline and returns a frozen action card
   before the site/Preview connection creates the first measured page load. Thus the
   Preview connection's page load is the Core action; do not generate two cleanup loads.
3. Select the earliest safe, high-information event. Discover only its material scenario
   branches just in time. `next` freezes `OBSERVE_CURRENT`, `NAVIGATE_ONCE`, or
   `INTERACT_ONCE`, plus whether document change is forbidden, naturally allowed, or one
   explicitly authorized reload.
4. Perform exactly the action card once. Then call `complete` once with the returned
   action ID and current
   binding/health/page, continuous source/network/lifecycle deltas since the previous
   committed boundary, the complete bounded
   Preview event-list delta, concerned deep details, and coverage annotations. It commits
   and synchronizes Preview together, emits canonical per-layer feedback, and checkpoints
   the run. A browser/control violation preserves useful evidence but blocks confidence;
   it never launches a clean repeat or becomes a client defect.
5. Complete after every real interaction. One interaction may legitimately create
   several Preview indexes or satisfy several causally co-occurring planned claims; it
   must not contain a second user interaction. Inspect every intervening source message,
   including messages not named in the plan.
6. On that `complete`, capture Preview once for all new indexes caused by the action. Capture
   complete event and concerned-tag summaries; deep-read the Variables, configuration, effective
   mapping and runtime needed by current planned fields, plus suspicious details. Never
   scan unrelated historical domains or the whole container. Synchronize earlier if
   navigation, ambiguity, or risk could lose evidence.
7. Emit canonical feedback as soon as all known material scenarios for an event close.
   If the next completion contains a timestamped between-action anomaly, revise the
   affected prior event in the same model pass; do not add a pre-action capture phase.
   Choose the next branch by information value and transition cost, not by creating the
   whole run up front.
8. `finish` only after global reconciliation. It refuses open actions, unresolved
   protected handoffs, incomplete material coverage, unclassified material observations,
   evidence-confidence gaps, or privacy blockers. `report` rebuilds only a frozen run;
   `reopen` requires explicit authorization.

Corrections invalidate only dependent proof. Distinguish website defects, plan
ambiguity, control-tool failures, evidence limitations, and protected gates. Never use
alternate state files or command routes to manufacture progress.

The same event/scenario may run again only with a structured retest basis: a known
evidence-defect record or explicit user authorization. Free text alone is not authority.
A distinct material scenario remains a distinct action, so this guard does not limit
language, shipping, payment, product-signature, or other scenario coverage.

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
