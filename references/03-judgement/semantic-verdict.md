# Semantic and journey verdict

## Two results, one overall verdict

Keep `technical_delivery` separate from semantic/business truth. A tag can be
technically coherent while the page, interaction, or business state is wrong.
The event overall is the worst status across technical evidence, action/page
validity, journey/business semantics, chronology anomalies, and execution.

## Mandatory semantic checks

Every settled action has exactly one `PAGE_ACTION_VALIDITY` check, direct
before/after journey-state captures, and at least one `BUSINESS_STATE` judgement
tied to direct journey-state evidence. Every in-scope non-absence requirement
has a positive anchor or business-state check tied to the exact action and case.

Use visible page state, journey state, tracking plan, analyst specification,
platform documentation, or direct interaction as the named authority. Record
the anchor, observed value, comparison, field states, evidence, status, and
plain-language reason.

## Coherence rules

- A dead/soft-404/wrong page is overall `FAIL`, even if tags fired correctly.
- A populated visible cart with no `view_cart` items is `FAIL`; empty tracking
  and empty runtime tag configuration do not validate each other.
- Matching emptiness cannot pass a positive anchor.
- Strict equality preserves JSON type; boolean `true` is not numeric `1`.
- A completed website action with missing/wrong tracking is `FAIL`.
- An action that cannot be executed or evidenced is `BLOCKED`.
- A direct ambiguity with one precise question is `REVIEW`.

Use `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, and `NOT_TESTED` for events. Use
`NOT_APPLICABLE` only for a false conditional predicate. `PENDING` is never a
final state.

## Adaptive follow-up

A failure, ambiguity, unseen value, or new behavior signature triggers a
coverage expansion review. Add a materially distinct case when it can explain
or delimit the behavior; otherwise record why the population is exhausted or
why expansion is blocked. Do not repeat arbitrary products merely to increase
sample size.
