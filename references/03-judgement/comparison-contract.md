# Comparison Contract

Create one schema-v2 requirement for every planned field, variable, firing
condition, runtime tag parameter, or applicable consent condition. Group those
requirements into plan-ordered events for execution and feedback.

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
-> applicable event-level consent
```

Keep the static tag configuration and resolved runtime value separate. A tag can
fire correctly while a parameter fails; firing is then `PASS`, parameter is
`FAIL`, and overall is `FAIL`.

Keep exact raw API Call and resolved Data Layer separate. A stale inherited
resolved value cannot repair a missing or wrong raw field.

Concerned tags are only:

- expected to fire;
- expected to remain blocked;
- fired unexpectedly and are relevant to the requirement;
- necessary to explain why an expected tag did not fire.

Never create an event-by-every-container-tag matrix.

For a full recette, an occurred event requires exact structured Tag Assistant
API Call evidence. Browser interception may explain chronology but is
supplemental.

Use a tracking plan or explicit scoped acceptance rule. Unresolved plan meaning
is `REVIEW`; missing acceptance criteria blocks the run.
