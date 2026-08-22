# Forms, consent, CAPTCHA, and acquisition

## Ordinary forms

Use safe synthetic data and complete reversible form journeys in test/preprod.
Record the ordered state progression: `DISCOVERED`, `DATA_ENTERED`,
`CONSENT_ESTABLISHED`, `VALIDATION_COMPLETED`, `SUBMISSION_ATTEMPTED`, and a
terminal success/failure or blocker. A completed flow cannot skip an earlier
milestone. Prove website completion independently of tracking.

Try ordinary automation recovery before blocking: scroll, associated label,
direct control, pointer, keyboard, and one clean-state retry. A resistant normal
control is a UI failure, not an authorization boundary.

## Consent

Capture the natural event-level consent state. Make the ordinary CMP choice
needed for the tested journey. Test reject/partial/advanced behavior only when
the acceptance rule requires it. A banner click alone is not event-level proof.

Do not inject consent routinely. If a broken CMP blocks testing, request an
explicit session-only override, record exact values/method/scope/limitations,
and never use override evidence to pass the CMP itself.

## CAPTCHA and protected gates

Never bypass CAPTCHA, credentials, MFA, or external verification. Create a
protected handoff, ask the analyst to complete only that gate, then continue in
the same browser instance, context, tab, and Preview session. Record requested
and resumed bindings, the same flow/case/action IDs, and the gated-flow state.
A completed CAPTCHA flow requires a resumed same-flow handoff. If the handoff
cannot resume, mark it `BLOCKED`; do not open a new authentication flow and
pretend continuity.

## SEO and acquisition scenarios

Do not refuse an acquisition/referrer test simply because it is SEO-related.
Use, in order:

1. a natural same-context visit from a real referring page when practical;
2. a browser-controlled navigation with an explicit `Referer` in the approved
   context when the browser controller supports it;
3. URL campaign parameters for campaign semantics.

Label every case as natural, browser-simulated, URL-parameter-simulated, or
analyst-provided. A simulated fresh Google visit must state that it proves the
site/tag response to the simulated referrer, not indexing, ranking, or a real
search impression. Capture `document.referrer`, landing URL, storage/cookie
state, acquisition parameters, and Preview/network evidence.

Bind each claimed acquisition field to direct current-run evidence in the
normalized evidence catalog. The catalog row must belong to the same case and
record the captured fields; a self-described acquisition object is not proof.

Fresh-state preparation must remain in the approved browser context. Clearing
site state or reconnecting Preview requires the corresponding authority and a
new runtime snapshot; it does not justify moving to an unrelated window.
