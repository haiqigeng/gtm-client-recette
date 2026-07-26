# Execution Contract

Read this compact contract with the interaction protocol before starting.
Load detailed references only at the stage that needs them.

Use this lifecycle:

```text
preflight and READY
-> normalize source-bound requirements and event inventory
-> infer or confirm journeys and applicable interaction cases
-> establish dedicated GTM Preview session
-> capture natural starting consent
-> execute continuously in plan order
-> readiness and one action boundary per case
-> reconcile every business push in the continuous cursor
-> exact planned and relevant unexpected event evidence capture
-> destination, trigger/sequence, consent, business/privacy, and client checks
-> component and event verdict
-> immediate analyst feedback
-> coverage-gap closure
-> supplied-baseline regression comparison
-> final ordered event summary
-> strict schema and XLSX validation
```

Keep source plan order, runtime Preview order, and action boundaries distinct.
An inferred journey cannot silently become a confirmed acceptance expectation.
An observed event cannot become `PASS` without its source-bound rule. A
correctly shaped event cannot pass when it occurs outside that rule's trigger
context.

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

Pause for analyst action only at protected, consequential, or genuinely
ambiguous boundaries. Complete ordinary encountered gates and resume
automatically after protected handback.

Use one recette workflow. Record the supplied acceptance boundary and
applicable evidence layers without creating run modes. Never add an
observation-only workflow.
