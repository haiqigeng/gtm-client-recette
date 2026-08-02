# Comparison Contract

Create one schema-v3 requirement for every value or rule actually supplied by
the acceptance source. Group those requirements into plan-ordered events for
execution and feedback. Do not invent missing tag expectations, and do not use
missing plan columns to remove runtime evidence layers.

Evaluate each applicable link independently:

```text
tracking plan
-> event occurrence and chronology
-> exact raw dataLayer.push
-> resolved Data Layer
-> detected concerned-tag inventory and scope decision
-> each GTM variable used by every in-scope tag
-> each in-scope tag configuration
-> each tag firing/non-firing decision and fire count
-> each runtime tag parameter
-> each browser-sending tag request, destination/event identity, and outbound parameter
-> trigger, exception, and sequence contract
-> applicable event-level consent
-> business/privacy/client-context checks
-> supplied-baseline regression
```

For every per-tag expected value, retain an `expected_anchor` pointing to the
accepted requirement ID and exact path. The validator resolves that source and
rejects a stored expected value/type that differs from it; equal self-declared
expected/actual values are not proof. Anchor firing expectations and request
behaviour too. Redacted comparisons retain the anchor and safe comparison
basis but never raw values.

Keep the static tag configuration and resolved runtime value separate. A tag can
fire correctly while a parameter fails; firing is then `PASS`, parameter is
`FAIL`, and overall is `FAIL`.

Keep exact raw API Call and resolved Data Layer separate. A stale inherited
resolved value cannot repair a missing or wrong raw field.

Before judging event absence, prove the real website interaction completed
through a non-tracking signal and that the acceptance-relevant stream settled.
A failed or uncertain interaction is an execution blocker, not proof of a
tracking defect. Preserve and classify every push from a failed attempt before
one bounded retry with a new action ID.

Compare occurrence at both levels:

1. did every applicable interaction case produce its required event and count;
2. did every business push observed in the continuous action-window stream
   occur only under a compatible plan trigger, page, action, state, and order.

Inspect the complete business-push sequence for each controlled page load,
navigation, and interaction. Perform the full downstream comparison chain for
planned and relevant unexpected pushes; retain native `gtm.*` events only when
they explain chronology, source, or non-firing. Do not invent unrelated
negative journeys to look for absence.

Use one event verdict after all of its applicable cases. Aggregate the worst
case and preserve each distinct failed variant or placement; homogeneous
successes may be summarized with their executed count.

Inventory tags, then freeze the complete applicability card before each case
executes. Final certification requires one result for every canonical layer
and every in-scope tag/layer pair. Conditional predicates must be explicit;
false is `NOT_APPLICABLE`, and true requires a normal verdict. A planned raw
event missing after a valid settled interaction is `FAIL` and blocks its
unavailable downstream chain. Genuinely unavailable authoritative capture is
`BLOCKED`, never omitted or changed to `REVIEW`.

Under the default `analytics_only` scope, concerned in-scope tags are analytics
tags that are:

- expected to fire;
- expected to remain blocked;
- fired unexpectedly and are relevant to the requirement;
- necessary to explain why an expected tag did not fire.

An exact plan-declared media destination is also in scope. Expand to every
relevant client-side tag or a fixed list only when explicitly requested. Never
create an unrelated event-by-every-container-tag matrix, but always retain
detected exclusions visibly.

When resolved GTM state, variables, tag configuration, firing, or runtime
parameters apply, an occurred dataLayer event requires the exact structured
Tag Assistant API Call. A planned native, DOM, enhanced-measurement,
direct-vendor, or Custom HTML signal requires exact `source_signal` evidence
instead. Browser interception explains chronology and cannot replace an
applicable Preview link.

A journal-only push missing from Tag Assistant triggers the controlled
discrepancy procedure and cannot pass a required Preview-dependent layer.
Unreliable Preview is `BLOCKED`; an evidenced acceptance contradiction is
`FAIL`; unresolved semantics are `REVIEW`.

Browser network is authoritative for the outbound client send attempt; vendor
helpers and UIs are supplementary. Reconcile the decoded destination ID,
vendor event name, and tested value with their explicit raw query/body/header
paths. A `browser_request` tag requires this layer and a stable request/action/
container link; an explicitly `local_only` tag does not. Never infer vendor
ingestion or reporting.

Request count and unique request IDs must exactly reconcile with referenced
`browser_network_request` evidence bound to the same tag/action/container.
Accepted request absence requires a complete `browser_network_capture`, not an
empty hand-written ID list.

If the source/tag executed, browser capture is available, and the expected
request is absent, use `FAIL`; use `BLOCKED` only when capture is unavailable
or the upstream planned source already failed. A local-only row is
`NOT_APPLICABLE` only with positive configuration proof. If no in-scope
analytics tag exists for a planned dataLayer event, fail inventory,
configuration, and firing, then block the unavailable runtime/request layers.

Use a tracking plan or explicit analyst-defined acceptance rule. Unresolved
meaning is `REVIEW`; missing acceptance criteria blocks the run.
