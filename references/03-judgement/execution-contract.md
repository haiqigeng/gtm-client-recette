# Execution Contract

Read this compact contract with the interaction protocol before starting.
Load detailed references only at the stage that needs them.

Use this lifecycle:

```text
preflight and READY
-> normalize source-bound requirements and event inventory
-> infer or confirm journeys and applicable interaction cases
-> establish dedicated GTM Preview session
-> register cases and material variants
-> inventory detected tags, apply the declared tag scope, and freeze applicability cards
-> scaffold the exact in-scope tag x eight-layer matrix
-> capture natural starting consent
-> execute continuously in plan order
-> direct readiness capture and one derived action boundary per case
-> classify and count every business push in the continuous cursor
-> exact planned and relevant unexpected event evidence capture
-> mandatory raw/resolved/tag/runtime/request/sensitive chain
-> predicate-led consent, trigger/sequence, business, client, and context checks
-> per-layer, per-tag, and event verdict
-> immediate analyst feedback
-> coverage-gap closure
-> supplied-baseline regression comparison
-> final ordered event summary
-> strict normalized/session reconciliation and XLSX validation
```

Keep source plan order, runtime Preview order, and action boundaries distinct.
An inferred journey cannot silently become a confirmed acceptance expectation.
An observed event cannot become `PASS` without its source-bound rule. A
correctly shaped event cannot pass when it occurs outside that rule's trigger
context.

The tracking plan supplies acceptance values and optional journey hints. It is
never the evidence-layer selector. A planned dataLayer event always activates
the complete client-side core chain, even when the plan contains no tag column.

## Deterministic layer and tag-scope policy

Before every action, freeze an applicability card containing every canonical
layer. Each row is either:

- `MANDATORY`, with the concrete reason it is required for this case; or
- `CONDITIONAL`, with the explicit predicate that must be resolved after the
  action. Predicate false means `NOT_APPLICABLE`; predicate true requires a
  normal verdict and direct evidence.

For a planned dataLayer event, mandatory layers are action boundary, exact Tag
Assistant API Call, resolved Data Layer, concerned-tag inventory, GTM variables
used by in-scope tags, tag configuration, tag firing/count, runtime tag
parameters, browser request for browser-sending tags, and sensitive-data scan.

Tag scope is run-level and immutable:

- `analytics_only` is the default; exact plan-declared media destinations are
  also included;
- `all_relevant_client_side_tags` is used only when explicitly requested; and
- `explicit_tag_set` is an exact user-supplied tag list.

Every detected tag remains in the inventory. Tags outside the declared scope
are retained as `OUT_OF_SCOPE` with a reason and receive no in-scope result
matrix. Each in-scope tag receives a result for every tag-related layer.

If a material tag appears after freeze, settle the current action, retain the
old inventory/card as an immutable numbered revision, recompute the current
card, and force a retry. Never validate an earlier action against a later
inventory revision.

## Verdict-safety invariants

1. **Prove the interaction independently.** Use a safe website signal such as
   URL, visible state, navigation, control value, or success message. Never use
   the expected tracking event as proof that the action happened.
2. **Preserve failed attempts.** Reconcile their complete event windows. Retry
   one transient interaction failure with a new action ID and a restored quiet
   baseline; never collapse the attempts.
3. **Settle adaptively.** Select the quiet window from observed behaviour,
   restart it after every acceptance-relevant push, and keep a bounded timeout.
   An unsettled relevant stream cannot prove absence, count, or deduplication.
4. **Do not substitute evidence.** A supplemental journal record missing from
   Tag Assistant triggers a connection/page-node/window check and, when safe,
   one controlled repeat. It cannot pass a required Preview-dependent link.
5. **Separate execution from implementation.** An action that cannot be
   completed is `BLOCKED`; a valid completed action whose settled stream
   contradicts the acceptance rule is `FAIL`.
6. **Close every case.** Every in-scope case is `EXECUTED` or explicitly
   `BLOCKED`; only confirmed exclusions are `NOT_TESTED`. `PENDING` is working
   state, and `REVIEW` requires a precise semantic question.
7. **Reconcile the complete push stream.** The independently observed business
   push count must equal the classified ledger rows. Map each row to its
   action, case, page/state, container, and planned event or mark it unplanned
   relevant. After a reconnect that restarts numbering, identify rows by
   stream, connection epoch, and event index.
8. **Close every layer and in-scope tag.** The completed action records a
   status and reason for every canonical layer plus every in-scope tag/layer
   pair. A browser-sending tag includes network request identity and decoded
   parameters. Local-only is `NOT_APPLICABLE` only with positive configuration
   proof. After source/tag execution, available capture with no matching
   request is `FAIL`; only unavailable capture or an already failed upstream
   source is `BLOCKED`.
9. **Bind direct evidence.** Browser and Preview captures identify capture
   mode, action, event index, container, request, tag, and configuration field
   when applicable. Naming patterns and generic request correlation are not
   direct evidence.
10. **Anchor expected values.** Every per-tag expected value, firing rule, and
    request behaviour resolves from a source-bound accepted requirement. A
    matching self-declared pair cannot pass.
11. **Reconcile requests.** Declared request count/IDs exactly match the
    referenced tag-bound network evidence; absence requires complete capture.
12. **Roll up contradictions.** A mapped relevant unexpected push contributes
    its own `REVIEW` or `FAIL` to the affected event. Conditional expected
    absence and confirmed out-of-scope cases remain neutral only when their
    declared branch/scope conditions are satisfied.
13. **Derive action boundaries from runtime state.** Every attempt consumes one
    fresh `before_action` check and, when normally settled, one `after_action`
    check. A mid-action browser, Preview, network, or surface failure instead
    uses `interrupted_action`, preserves its last trustworthy cursors/pushes,
    settles uncertain, and blocks the case without invented downstream proof.
    A fresh action may retry that exact retained interruption after runtime
    recovery; the historical blocker remains attached to the prior attempt.
    Only a Preview disconnect advances the connection epoch.
    Exact browser context, container/workspace, selected Preview page,
    connection epoch, Preview cursor, and network cursor must reconcile. Agent-
    entered readiness booleans or cursors are not certification evidence.
14. **Close events before advancing.** Event closures form an exact prefix of
    the original plan order. Closure requires all cases resolved, all final
    actions settled, strict event/session validation, and an immediate feedback
    timestamp. Final validation requires one closure per event.
15. **Keep diagnosis computed.** `primary_outcome` reports the first actionable
    broken link and `anomaly_flags` expose missing, duplicate, premature,
    delayed, wrong-order, wrong-context, or unplanned occurrences. Neither can
    override canonical layer or event verdicts.
16. **Preserve compatibility without inventing proof.** A schema-v3 result
    without `run.action_boundary_contract_version` remains readable under the
    legacy boundary contract. Only version `1` may enter guided operation; a
    current certification recaptures checks/cursors instead of backfilling them.
17. **Reopen explicitly.** A late material interaction, variant, or tag moves
    the affected event closure and every later closure into auditable history.
    Retain proof, execute the new case, and reclose the suffix in plan order.
18. **Recover paired writes.** Event closure replaces normalized results and
    session state as one journaled, crash-recoverable operation. Finalization
    applies the same contract to the validated workbook and FINISHED session.
    A failure during either replace restores both prior files before reporting.
19. **Retain orphan checks explicitly.** An unconsumed runtime check created
    before a mistaken action identity can be voided only with an exact reason
    and timestamp. Never delete, reuse, or attach it silently.

Pause for analyst action only at credentials or protected sign-in, MFA,
CAPTCHA, verification, magic links, real payment, external approval,
irreversible/consequential action, or a genuinely ambiguous boundary. Complete
ordinary form inputs, privacy acknowledgements, tested-conversion opt-ins, and
ordinary submission with safe synthetic data, then resume automatically after
any protected handback.

Run-wide authorization prevents repeated prompts for equivalent safe actions
inside its exact scope. Synthetic credentials may exist only ephemerally in
the controlled browser. Protected credentials, MFA, CAPTCHA, verification,
real payment, external approval, and irreversible actions remain checkpoints.

An inoperable ordinary checkbox/control is `UI_CONTROL_BLOCKER`, not consent or
authorization. Before finalizing it, retain the failed window and try
scroll-into-view, label click, direct control, pointer click, keyboard toggle,
and one clean-state retry.

Use one recette workflow. Record the supplied acceptance boundary without
creating run modes. The deterministic layer policy—not plan column
completeness—sets evidence applicability. Never add an observation-only
workflow.
