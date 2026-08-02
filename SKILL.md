---
name: gtm-preview-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rule. Use for plan-ordered analytics and media-tag QA that must cover every applicable interaction and material variant, complete safe gated flows, reconcile every business dataLayer push by action window, compare exact raw and resolved GTM, tag, runtime, and browser-send evidence, detect missing, duplicate, mistimed, or wrong-context occurrences, and deliver one evidence-backed verdict per event plus a validated XLSX. Excludes tracking-plan design, container audit or configuration, implementation fixes, publishing, server-side GTM, and legal consent decisions.
---

# GTM Preview Recette

## North star

> Execute an expert, tracking-plan-led GTM recette on the actual test website, covering every planned event in its original order. Use supplied URLs, screenshots, and journeys when available; otherwise identify and execute the relevant website interactions. For every event, use GTM Preview to compare the tracking-plan expectation with the exact live dataLayer.push payload, its variables, values and types, the resolved GTM variables, the expected tag firing or non-firing behaviour, and every required runtime tag parameter and value. Complete ordinary and authentication-gated journeys with safe synthetic data whenever possible, requesting analyst intervention only at protected, consequential, or genuinely ambiguous boundaries. Return an immediate, evidence-backed verdict and precise reason for each event, omit nothing silently, and finish with a complete plan-ordered status summary and validated detailed workbook.

Apply this north star automatically to every concerned client-side analytics
tag. Include exact plan-declared media destinations by default. Expand to every
relevant client-side tag or a fixed tag set only when the analyst explicitly
requests it. Keep every detected exclusion visible. A browser request proves
an attempted client send, not vendor ingestion, attribution, or reporting.

## One acceptance workflow

Use one workflow. Never choose a reduced or dataLayer-only mode. The tracking
plan supplies accepted dataLayer semantics and sometimes journey hints.
It never decides which evidence layers are inspected.

The tracking plan or an explicit analyst-defined acceptance rule is required.
Do not design or repair a tracking plan; audit, configure, submit, version, or
publish GTM; change the website; make legal decisions; test server-side GTM;
or claim vendor receipt from browser-only proof.

Complete ordinary forms, privacy acknowledgements, tested-conversion opt-ins,
sign-up, lead, account, authentication preparation, and submissions with safe
synthetic data unless the analyst excluded them. Do not ask again per event.
Pause only at protected credentials/sign-in, MFA, CAPTCHA, external
verification, magic links, real payment, external approval, irreversible or
consequential actions, or a genuinely verdict-changing ambiguity. Never store
credentials or synthetic personal values in chat, evidence, ledgers, or the
workbook.

An ordinary in-scope checkbox or form control that resists automation is a
`UI_CONTROL_BLOCKER`, not an authorization boundary. Try scroll, label,
direct-control, pointer, keyboard, and one clean-state retry first. Retain the
failed action window.

Do not invent arbitrary negative journeys. Detect unwanted behaviour by
classifying every business push observed during planned positive journeys.
Run an explicit non-firing scenario only when the acceptance specification
requires it.

## Fixed layer contract

For each executed case, record exactly these 19 canonical layers in this order:

1. `action_boundary`
2. `raw_api_call`
3. `resolved_data_layer`
4. `concerned_tag_inventory`
5. `gtm_variable`
6. `tag_configuration`
7. `tag_firing`
8. `tag_parameter`
9. `destination_request_when_applicable`
10. `sensitive_data_scan`
11. `consent_when_applicable`
12. `source_signal_when_no_data_layer_push`
13. `trigger_logic_when_applicable`
14. `tag_sequence_when_applicable`
15. `business_rules_when_declared`
16. `client_checks_when_applicable`
17. `regression_when_baseline_provided`
18. `container_context_when_applicable`
19. `conditional_scenarios_when_applicable`

Layers 1-10 are mandatory for a planned dataLayer event, except that a
positively proved `local_only` tag has no destination request. Layers 11-19
are conditional and become mandatory exactly when their recorded predicate is
true. When false, record `NOT_APPLICABLE`, the predicate result, reason, and
proof. Never omit a canonical row.

For every in-scope tag, record exactly these 8 sublayers:

1. `gtm_variable`
2. `tag_configuration`
3. `tag_firing`
4. `tag_parameter`
5. `destination_request_when_applicable`
6. `consent_when_applicable`
7. `trigger_logic_when_applicable`
8. `tag_sequence_when_applicable`

Every per-tag row must carry the frozen tag identity and direct evidence bound
to that exact tag. Every expected comparison value must point to an accepted
requirement anchor. Every declared request ID/count must reconcile with the
referenced tag-bound browser-network evidence. Privacy-scan all normalized and
session/per-tag export surfaces before validation or workbook generation.

## Load references progressively

Do not preload the complete reference library. Always read:

- [interaction protocol](references/02-execution/interaction-protocol.md); and
- [core execution contract](references/03-judgement/execution-contract.md).

Then load the stage-specific references immediately before that stage:

- Normalize/cases: [inputs and outputs](references/01-orientation/inputs-outputs.md),
  [journey coverage](references/02-execution/journey-inference-and-coverage.md),
  and [schema v3](references/03-judgement/schema-v3.md).
- Connect/execute: [Tag Assistant operations](references/02-execution/tag-assistant-operations.md),
  [browser readiness](references/02-execution/browser-session-and-readiness.md),
  and [capture playbook](references/02-execution/interaction-and-capture-playbook.md).
- Compare/judge: [evidence model](references/03-judgement/evidence-model.md)
  and [comparison contract](references/03-judgement/comparison-contract.md).
- Incremental/final output: [incremental workflow](references/02-execution/incremental-evidence-workflow.md),
  [operator commands](references/02-execution/operator-command-reference.md), and
  [workbook architecture](references/03-judgement/workbook-architecture.md).

Load only when applicable: [consent and synthetic data](references/02-execution/consent-and-synthetic-data.md),
[destinations and containers](references/02-execution/client-side-destinations-and-containers.md),
[runtime contexts](references/02-execution/client-side-runtime-contexts.md),
[conditional/privacy rules](references/03-judgement/conditional-business-and-privacy-rules.md),
[matching rules](references/03-judgement/matching-rules.md),
[regression](references/03-judgement/regression-comparison.md), or
[cross-skill handoff](references/01-orientation/cross-skill-handoff.md).
Use [the gold mini-recette](references/gold-mini-recette.md) only for calibration.

## Execution workflow

### 0. Confirm readiness

Show the responsibility-labelled preflight from the interaction protocol in at
most five bullets. Wait for `READY` or equivalent before opening client files
or executing the site. The acceptance source and test origin are essential;
URLs, images, selectors, GTM IDs, consent scenarios, and journeys are
supporting inputs that can be inferred safely.

### 1. Normalize source requirements

Preserve source file, sheet, row/cell, section, screenshot, hyperlinks,
comments, hidden content, merged ranges, images, and original event order.
Use the supplied GA4 handoff importer when applicable; otherwise inspect the
plan and initialize schema v3 through the provided commands.

Create one stable source-bound requirement per expected event field, variable,
tag configuration, firing rule, runtime parameter, destination, consent,
trigger/sequence, or declared client rule. Create one plan-ordered event group
for feedback. Preserve exact expected value, type, match and occurrence rules,
context, source mechanism, variables, tag/runtime fields, destination IDs and
request paths. Separate destinations into atomic requirements. Ask only when
ambiguity can change a verdict.

Missing plan tag fields never remove runtime tag, variable, configuration,
firing, parameter, or request checks for a planned dataLayer event.

Declare tag scope once:

- `analytics_only` is default and includes plan-declared media destinations;
- `all_relevant_client_side_tags` includes every relevant client tag when
  explicitly requested; or
- `explicit_tag_set` uses the analyst's exact list.

The initializer expresses the default as `--tag-scope analytics_only`.

Infer analytics classification deterministically from vendor/template
metadata, including GA4, Piano, Adobe Analytics, Matomo, Piwik PRO, Snowplow,
and Realytics. Do not manipulate category to alter scope.

Audit or Configuration artifacts are supporting context, never acceptance
authority. Schema-v2 inputs cross a hard boundary: use the v2→v3 migration,
preserve discovery/order/cases only, and recapture all proof from `PENDING`.

### 2. Build complete, proportionate coverage

For every event group enumerate every applicable interaction, placement,
branch, and material finite value. Use supplied journeys/images first;
otherwise inspect the actual website and optionally use the DOM census for
discovery. Execute real user-facing interactions, not census candidates.

- Test each distinct header/menu/card/CTA/footer/product interaction, not one
  representative.
- Exhaust practical finite sets. If counts 1-9 change payload/firing, execute
  nine isolated cases.
- Reset state when prior actions affect results.
- For large spaces, document partitions, boundaries, and risk combinations.
- Create cases for material conditional, responsive, error, experiment, or
  personalized branches; unacquired branches cannot pass.
- Explore alternate routes before calling an event unavailable.

Register each case before acting. Inventory every detected tag, keep excluded
tags visible, and `complete-tag-inventory` before the first action. This freezes
the full applicability card. If a material tag is discovered later, settle the
current action, use `revise-tag-inventory`, retain the previous card as an
immutable revision, and rerun the case. Never silently mutate a frozen card.

### 3. Establish the controlled browser and Preview session

Use an analyst-approved attached session or dedicated Playwright profile.
Confirm the intended GTM account, web container, workspace, environment,
origin, Tag Assistant connection, owning container per tag, natural consent,
and stable browser-surface identities. Keep separate cursors for separate
containers.

Initialize one resumable session ledger. Install the supplemental recorder at
document start and context-level request capture before navigation. The
recorder preserves early/mutated/state-clearing pushes but never substitutes
for Tag Assistant `API Call`. Context capture must retain redirects, unloads,
popups, iframes, service-worker and batched sends.

Check recorder integrity after dataLayer reassignment. Treat unreadable,
circular, replaced-unverified, or truncated snapshots as limitations. Persist,
reconcile, and privacy-scan records before acknowledging them. Keep monotonic
call indexes. Never retain cookies, authorization headers, credentials, or raw
sensitive values.

If recorder and Preview disagree, freeze the affected verdict, verify page
node/container/origin/connection/action window, and repeat once when safe.
Supplemental evidence can reveal the gap but cannot pass a required Preview
link.

### 4. Establish consent without silently changing it

Capture natural event-level consent for each case. Make the normal CMP choice
needed for an ordinary journey. Test refusal, partial choice, or Advanced
Consent Mode only when accepted requirements call for it. A banner click is
not event-level proof.

Do not inject consent routinely. If a broken/missing CMP blocks testing, show
the blocker and ask before a temporary session override. Record exact values,
method, scope, limitations, and reversal; separate native from override proof.
An override can exercise downstream tags but cannot pass the CMP itself.

### 5. Execute every case in plan order

For each case:

1. Confirm page, connection, consent, and a quiet baseline.
2. Record action ID, prior Preview index, page/state, element, placement, and
   material variant.
3. Perform one exact interaction with safe synthetic data where needed.
4. Prove website completion independently through URL/state/control/success.
5. Wait adaptively for expected evidence and a settled relevant stream.
6. Record first/final indexes, quiet window, timeout, settlement, and reason.
7. Inspect and classify every business push in the action window.
8. Capture all 19 canonical and 8 per-tag results with direct evidence.
9. Validate, report the event immediately after all its cases, and continue.

Use `scaffold-tag-results` after the frozen inventory to generate the exact
tag×layer matrix, then replace every placeholder with direct evidence before
`import-tag-results`. Final validation rejects `PENDING`, an omitted push,
open action, missing canonical/per-tag row, blank reason, wrong identity,
unanchored comparison, fake request ID, or mismatched action boundary.

Do not use the tracking event to prove the website action completed. Retain a
failed attempt and any tracking emitted during it. Retry once after a clean
baseline for evidenced transient UI failure; more retries require an evidenced
reason. A valid completed action with missing/wrong tracking is `FAIL`; an
unexecutable action is `BLOCKED`.

Use adaptive quiet windows, not blind sleep. Restart on relevant business or
state pushes. If the stream does not settle, absence/count/deduplication cannot
pass or fail conclusively; block that occurrence evidence.

Maintain a gapless stream cursor. Identify Preview occurrences by connection
epoch plus event index. Classify each push as expected, companion, duplicate,
premature, delayed, wrong-order, wrong-context, or unplanned relevant. A planned
event name firing while its trigger is false is a failure.

### 6. Reconcile the independent chain

Compare in this order:

```text
accepted requirement
-> action window, occurrence, count, context, chronology
-> exact Tag Assistant API Call / raw dataLayer.push
-> resolved Data Layer at that event
-> frozen concerned-tag inventory
-> each in-scope tag's resolved GTM variables
-> tag configuration
-> firing/non-firing and count
-> runtime parameters and types
-> decoded browser request for each browser-sending tag
-> applicable consent, trigger, sequence, business, client, regression rules
-> requirement/event verdict
```

The chain is non-substitutive. Raw and resolved data are different. A fired
tag does not prove configuration/runtime correctness. Runtime does not prove
configured source. “Send ecommerce data” and Custom JavaScript still require
resolved runtime and request proof. Compare absent, `undefined`, `null`, empty,
value, and type exactly.

After a browser-sending tag executes, available capture with no matching
request is `FAIL`; use `BLOCKED` only when capture or an upstream source is
genuinely unavailable. Expected absence needs a complete capture. `local_only`
needs positive configuration proof. No in-scope analytics tag for a planned
dataLayer event fails inventory/configuration/firing and leaves unavailable
downstream layers explicitly blocked.

When no custom push is expected, replace only the raw-push link with direct
`source_signal` evidence. Keep every applicable downstream check. For a
non-firing wanted tag, inspect trigger/exception variables, event consent,
sequence, and Preview errors. If no cause is evidenced, say: `Reason not
established from available Preview evidence`.

### 7. Judge and report incrementally

Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_TESTED` for events;
`NOT_APPLICABLE` only for a false conditional predicate. `PENDING` is working
state only. The event status is the worst applicable component status.

- `PASS`: exact accepted expectation is proved.
- `FAIL`: settled evidence contradicts a confirmed expectation.
- `BLOCKED`: an evidenced blocker prevents execution or proof.
- `REVIEW`: direct evidence exists but one precise semantic question remains.
- `NOT_TESTED`: deliberately outside confirmed scope.

Validate and apply each event patch transactionally. Then give an immediate
evidence-backed verdict with one row/status for every canonical layer and one
subrow for every in-scope tag layer. Compact homogeneous passing cases, but
name every failed/blocked/review placement or variant. Each non-PASS row needs
the reason, evidence/blocker, and exact website retest interaction.

### 8. Close and export

Confirm original plan order, complete cases, classified pushes, all 19/8 rows,
ordinary gates completed, protected checkpoints offered, anomalies visible,
and no raw sensitive content. Run final normalized/session validation,
business rules, privacy scan, and strict workbook generation using the operator
commands reference.

The workbook writer must split oversized structured values with explicit part
markers; it must never accept Excel's silent 32,767-character truncation.
Reload and validate all sheets, physical row counts, filters, hyperlinks,
structured values, notes, and status formatting.

Finish with every event in original order and its aggregate status, followed
by component and affected-case detail. State missing evidence precisely. A
prior run can contribute only a discovery manifest; no earlier verdict,
evidence, consent, or authorization becomes current truth.
