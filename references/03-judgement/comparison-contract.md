# Comparison Contract

Create one schema-v2 requirement for every planned field, variable, concerned
tag/destination, firing condition, trigger/sequence contract, runtime or
outbound parameter, consent condition, business rule, or applicable
client-side check. Group those requirements into plan-ordered events for
execution and feedback.

Evaluate each applicable link independently:

```text
tracking plan
-> event occurrence and chronology
-> exact raw dataLayer.push
-> resolved Data Layer
-> resolved GTM variable
-> concerned tag configuration
-> tag firing and fire count
-> runtime tag parameter
-> browser destination request, destination/event identity, and outbound parameter
-> trigger, exception, and sequence contract
-> applicable event-level consent
-> business/privacy/client-context checks
-> supplied-baseline regression
```

Keep the static tag configuration and resolved runtime value separate. A tag can
fire correctly while a parameter fails; firing is then `PASS`, parameter is
`FAIL`, and overall is `FAIL`.

Keep exact raw API Call and resolved Data Layer separate. A stale inherited
resolved value cannot repair a missing or wrong raw field.

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

Concerned tags are only:

- expected to fire;
- expected to remain blocked;
- fired unexpectedly and are relevant to the requirement;
- necessary to explain why an expected tag did not fire.

Never create an event-by-every-container-tag matrix.

When resolved GTM state, variables, tag configuration, firing, or runtime
parameters apply, an occurred dataLayer event requires the exact structured
Tag Assistant API Call. A planned native, DOM, enhanced-measurement,
direct-vendor, or Custom HTML signal requires exact `source_signal` evidence
instead. Browser interception explains chronology and cannot replace an
applicable Preview link.

Browser network is authoritative for the outbound client send attempt; vendor
helpers and UIs are supplementary. Reconcile the decoded destination ID,
vendor event name, and tested value with their explicit raw query/body/header
paths. Never infer vendor ingestion or reporting.

Use a tracking plan or explicit analyst-defined acceptance rule. Unresolved
meaning is `REVIEW`; missing acceptance criteria blocks the run.
