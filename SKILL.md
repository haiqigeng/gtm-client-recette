---
name: gtm-client-recette
description: Execute expert client-side GTM Preview and Tag Assistant acceptance recette against an existing tracking plan or explicit acceptance rule. Use for plan-ordered analytics and media-tag QA that must cover every applicable interaction and material behavior variant, complete safe gated flows, account for the continuous dataLayer stream, compare raw, resolved, tag, runtime, and browser-send evidence, detect journey and business-semantic anomalies, and deliver one evidence-backed verdict per event plus a validated XLSX. Excludes tracking-plan design, container configuration, implementation fixes, publishing, server-side GTM, and legal consent decisions.
---

# GTM Client Recette

## Objective

Test the actual website like an expert human analyst, not like a tag-fire
checker. Follow the accepted plan in source order, execute every material
scenario class, inspect what happens before, during, and between interactions,
and judge whether the page, business state, dataLayer, GTM, tag runtime, and
browser request tell one truthful story.

Keep two results distinct:

- `technical_delivery`: whether the declared tracking chain behaved correctly;
- overall event verdict: the worst result across technical delivery, page/action
  validity, journey/business semantics, continuous-stream anomalies, coverage,
  and execution.

A tag may therefore be technically `PASS` while the event is overall `FAIL`,
for example on a dead URL or when a populated cart produces empty tracking.

## Scope and authority

Require an existing tracking plan or explicit acceptance rule and an approved
test origin. Inspect or infer supporting URLs, journeys, selectors, containers,
and scenarios when safe; ask only when missing information changes authority,
scope, or a verdict. Preserve requirement provenance and original event order.

Before opening client files or executing the site, present one concise
preflight: accepted inputs, origins/environment, browser/session to reuse,
planned ordinary actions, protected gates, evidence location, and outputs.
Continue only after the analyst explicitly replies `READY` for that scope. A
later scope/origin or consequential-action change needs renewed approval.

Execute ordinary reversible website journeys with safe synthetic data. Redact
sensitive values at capture time, before they enter chat, normalized results,
session ledgers, decoded requests, logs, screenshots, or reports. Never retain
credentials, cookies, tokens, form personal data, or raw sensitive values.
Raw-body inspection, if explicitly needed, stays in a separate named local
quarantine and is never imported as result evidence. Pause only for a
protected gate: credentials, federated sign-in, MFA, CAPTCHA, email/SMS
verification, magic link, real payment, external approval, or an irreversible
or consequential action. Resume in the same browser context, tab, and Preview
session.

Do not design the plan, mutate or publish GTM, fix the site, certify server-side
GTM or vendor receipt, or make legal/privacy-compliance decisions. Audit and
configuration artifacts are supporting context, never current-runtime proof.

Read [scope and inputs](references/01-orientation/scope-and-inputs.md) before
normalization.

## Non-negotiable controls

1. Reuse the approved in-app browser and its existing authenticated GTM, Tag
   Assistant, and site surfaces. Do not replace a broken Preview with a new
   unauthenticated window.
2. Certify one expected client web container per run. Capture the containers
   actually loaded on the page. A wrong container blocks positive
   certification until the opened Preview is corrected.
3. Capture page health before interaction. A 404, soft 404, wrong page, or
   absent target is an executed failed case, even if tags fire coherently.
4. Bind every action to captured before/after browser, tab, Preview, network,
   and dataLayer cursors. Never type inferred action boundaries.
5. Account for every dataLayer push argument from recorder installation to
   final closure, including events between planned interactions.
6. Use direct current-run evidence. Reject previous-run recorder data,
   fabricated cursors, stale coverage revisions, and any missing or changed
   final evidence artifact.
7. Never infer correctness from internal coherence alone. Empty dataLayer and
   empty runtime configuration cannot pass when visible business state is
   populated.

Read [browser and Preview control](references/02-execution/browser-preview-runtime.md)
immediately before connecting or executing.

## Scenario discovery and sampling

At run setup, map the full event order, known journeys, and protected gates.
Then, immediately before each event's first action, build and freeze that
event's explainable coverage decision:

1. Discover candidate interactions from the plan, supplied assets, journeys,
   and live site.
2. Record material dimensions: route/template, component/placement, locale,
   responsive state, user state, content/product shape, quantity/value
   boundary, consent, acquisition, and journey state.
3. Group candidates only when their behavior signatures match: action path,
   page/component, data source, payload contract, tag contract, consent,
   acquisition, and journey precondition.
4. Use `EXHAUSTIVE` for finite material branches, `PARTITIONED` for known
   behavioral partitions, `SAMPLED` only inside a large homogeneous class,
   `SINGLETON` for one member, and `BLOCKED` for an unacquired class.
5. For a sampled class select at least an `ORDINARY` and `CONTRAST` member,
   plus applicable `BOUNDARY` and `EXCEPTION` members.

Bind every registered case to explicit values for every material dimension.
At finalization, review all four adaptive triggers—new signature,
anomaly/failure, unseen material value, and conditional runtime branch—even
when current-run evidence says that a trigger did not occur.

Test all distinct finite semantic branches and parameter-value scenarios. Do
not test hundreds of interchangeable products. Never sample across different
behavior signatures.

Reopen coverage when a case reveals a new behavior signature, anomaly/failure,
unseen material value, or conditional runtime branch. Record whether the
coverage expanded, the population was exhausted, or expansion was blocked.
Changing a frozen coverage revision invalidates affected closures.

Read [scenario coverage and sampling](references/02-execution/scenario-coverage-and-sampling.md)
before registering cases.

## Evidence layers

Always record the 19 canonical rows in order, but do not treat all 19 as
substantive by default. For a normal planned dataLayer event with a
browser-sending tag, the default mandatory chain is:

1. action boundary;
2. exact raw API Call/dataLayer payload;
3. resolved Data Layer state;
4. complete concerned-tag inventory;
5. GTM variables consumed or positively unused;
6. tag configuration;
7. firing/non-firing and count;
8. runtime parameters and JSON types;
9. matching browser destination request;
10. sensitive-data scan.

The remaining canonical rows activate only when their predicates are true:
consent, non-dataLayer source signal, trigger logic, tag sequence, declared
business rules, client checks, supplied regression baseline, multi-container
context, and conditional scenarios. Record a false predicate as
`NOT_APPLICABLE` with reason and proof; never omit the row.

For every in-scope tag, record the eight tag-bound rows for variable,
configuration, firing, runtime parameter, destination, consent, trigger, and
sequence. A non-dataLayer source replaces raw/resolved proof with direct source
proof but does not remove applicable downstream tag checks.

Read [evidence and layers](references/03-judgement/evidence-and-layers.md) before
comparison.

## Continuous stream

Install `scripts/datalayer_recorder.js` at document start with the current run
ID. Review one gapless sequence of `INITIAL_LOAD`, `ACTION`, `INTER_ACTION`, and
`FINAL` segments. Every settled action has exactly one action segment; segment
Preview and dataLayer cursors must be adjacent without gaps or overlaps.

Classify every argument of every recorded dataLayer call as
`BUSINESS_EVENT`, `TECHNICAL_EVENT`, `STATE_UPDATE`, or `NON_EVENT`. A custom
event cannot be hidden as state or noise. Map each business event to one push
and judge it as expected, companion, duplicate, premature, delayed, wrong
order, wrong context, or unplanned relevant. Anomalies between two planned
events affect the relevant event verdict and appear in feedback.

Use adaptive quiet windows. If the stream never settles, absence/count/order
is `BLOCKED`, not guessed. The recorder supplements but never replaces Tag
Assistant API Call and resolved-event evidence. Call `dispose()` at run end and
record any safe-cleanup limitation.

Read [continuous stream](references/02-execution/continuous-stream.md) before
the first capture.

## Forms, consent, acquisition, and gates

Complete ordinary forms and consent choices with synthetic data and prove the
website outcome independently of tracking. Try normal control recovery before
declaring a UI blocker. Never bypass CAPTCHA or authentication; create a
protected handoff and resume the same browser/context/tab/Preview identities.

Do not refuse SEO/acquisition tests. Exercise a fresh referral context with a
natural referring visit when practical, otherwise a browser-controlled
`Referer`, otherwise explicit campaign parameters. Label the simulation method
and limitations. Simulated Google referral proves site/tag response to that
context, not indexing, ranking, or a real search impression.

Read [forms, consent, CAPTCHA, and acquisition](references/02-execution/forms-consent-acquisition.md)
when any of these applies.

## Operator-v2 workflow

Resolve `<skill-root>` as the directory containing this file; never assume the
working directory. Run `python -B "<skill-root>/scripts/<script>.py" --help`
for exact command fields.

1. Inspect/import the plan and initialize normalized schema-v3 results. New
   runs must declare `operator_contract_version_required: 2`.
2. Initialize `preview_session_ledger.py` with operator contract 2 and the
   normalized `run_id`, current browser instance/context, profile, origins, and
   container.
3. Register the existing GTM, Tag Assistant, and site surfaces.
4. For the current plan-ordered event, discover/register its cases with exact
   dimension values and tag inventory, then import and freeze its coverage.
   Do not require future events to be fully prepared before event 1 can close.
5. Capture a v2 before-runtime snapshot and start that event with
   `recette_operator.py start-event`.
6. Execute one exact action. Capture website outcome, all pushes, all canonical
   and tag rows, before/after journey state, and a v2 after snapshot.
7. Settle the action, import stream/semantic records and any acquisition,
   handoff, or gated-flow records, and generate the event patch scaffold from
   the settled final actions. Replace every scaffold placeholder with current
   direct proof.
8. Close through `recette_operator.py close-event`. It atomically commits the
   event patch, verified event-only evidence catalog, frozen coverage revision,
   and digest-bound reviewed stream prefix. Safe replay of the identical close
   is idempotent; a different patch requires explicit reopening.
9. Emit its immediate event/case/layer feedback before preparing the next
   event. The continuous stream may remain `OPEN`; the closed event passes that
   component only when its exact prefix is certified and unchanged.
10. After the final event, close the stream, verify every evidence-file digest,
   call `recette_operator.py finish-run`, and build the validated XLSX.

Batch imports are transactional. Preserve interrupted attempts and observed
pushes; retry only from a new controlled boundary linked to the retained
attempt. Resume from persisted state plus a fresh snapshot. If a material
case, tag, or coverage decision changes, reopen and reclose the affected event
suffix in plan order.

Read [operator and output](references/03-judgement/operator-and-output.md) while
operating the ledger.

## Semantic judgement

Every action requires direct `PAGE_ACTION_VALIDITY`, before/after journey
state, and an explicit `BUSINESS_STATE` judgement tied to that journey-state
evidence. Every positive requirement needs an external anchor: the plan,
visible page/business state, direct interaction, analyst specification, or
documented platform semantics. Matching emptiness cannot prove a positive
requirement.

Judge exact value, JSON type, field state (absent/undefined/null/empty/value),
occurrence, action window, context, and order. Use:

- `PASS`: the accepted behavior is directly proved;
- `FAIL`: settled evidence contradicts it;
- `BLOCKED`: an evidenced blocker prevents a trustworthy decision;
- `REVIEW`: direct evidence leaves one precise verdict-changing ambiguity;
- `NOT_TESTED`: explicitly out of executed scope.

`NOT_APPLICABLE` belongs only to false conditional layers. `PENDING` is never
final. Overall status is the worst of technical, page/journey, business
semantics, continuous stream, coverage, and execution.

Read [semantic verdict](references/03-judgement/semantic-verdict.md) before
closing an event.

## Required delivery

After each tested event, return one concise feedback block containing:

- event and case status with human label `OK`/`KO`;
- every inspected canonical layer and simple reason;
- per-tag technical layers;
- technical delivery, page/journey, business semantics, stream anomalies, and
  scenario coverage;
- affected cases, direct evidence IDs, and exact retest instruction when not
  `PASS`.

After all events, return a plan-ordered conclusion listing every event, layers
inspected and statuses, overall status, and a concise why. Produce the
validated XLSX with coverage, scenarios, semantic checks, journey state,
continuous segments, protected handoffs, gated flows, detailed legacy sheets,
and final conclusion.

Refuse finalization when actions are open, cases/events remain pending,
coverage is stale, stream calls are unclassified, containers/browser bindings
disagree, semantic anchors are missing, handoffs are unresolved, or any final
evidence artifact is missing, external-only, or digest-mismatched.
