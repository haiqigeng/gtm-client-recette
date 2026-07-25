# Consent And Synthetic Data

## Natural consent first

Capture the natural/default event-level consent state before interacting with
the CMP.

- For a normal functional journey with no consent acceptance requirement, use
  the site's ordinary choice needed to run the journey and mark consent checks
  `NOT_TESTED`.
- For required refused, partial, accepted, or preference-change scenarios,
  apply the specified choice and verify the resulting event-level state before
  executing the action.
- Treat Tag Assistant's event-level Consent panel as authoritative for tag
  gating. A banner click alone is not evidence of the resulting state.
- Preserve default, update, event-level state, tag behaviour, and timing order.

## Exceptional test-environment override

Never inject or simulate consent routinely. Consider a browser-session override
only when all of these are true:

1. the environment is test, preprod, or staging—not production;
2. the natural CMP is demonstrably missing or defective;
3. that defect blocks otherwise valid downstream tracking checks;
4. the intended consent setup and temporary values are known;
5. the analyst explicitly approves the exact proposed action.

Before requesting approval, state:

- the observed CMP blocker;
- the exact temporary method and values;
- the events or tags it is intended to unblock;
- that it will not validate the natural CMP implementation;
- how the override will be kept session-scoped and reversible.

Wait for `APPROVE CMP OVERRIDE` or equivalent explicit approval. Without
approval, keep affected requirements `BLOCKED` and continue unaffected work.

Record the blocker, approval evidence, before/after state, injection timing, and
event-level result as `session_override`. Keep it separate from `natural_cmp`
evidence and verdicts. Never convert a natural CMP failure to `PASS` because an
override enabled a downstream tag.

## Synthetic form data

For an authorised journey:

- infer formats from label, locale, HTML validation, and server feedback;
- use unique, obviously synthetic values and reserved example domains;
- never use a real person's identity, inbox, phone, credentials, or payment
  data;
- never expose generated passwords in chat evidence or the report;
- accept only required terms, privacy notices, and declarations;
- leave optional marketing, profiling, partner-sharing, newsletter, and
  communication choices unchecked unless that opt-in is the tested conversion.

Use `scripts/generate_synthetic_profile.py` as a safe starting point. Adapt only
to the form's validated format and prefer a client-provided test range when a
phone number is required.

## Protected journey handoff

Complete ordinary sign-up, lead, account, and pre-payment steps automatically.
At CAPTCHA, MFA, email/SMS verification, magic link, real payment, or external
approval:

1. preserve the session and action checkpoint;
2. ask the analyst to complete the protected step in the dedicated browser;
3. resume after `DONE` or `SIGNED IN`;
4. use final `BLOCKED` only when the step cannot be completed safely.

Record created test accounts, leads, or subscriptions in run context with their
cleanup status. Never automate real payment or irreversible account actions.
