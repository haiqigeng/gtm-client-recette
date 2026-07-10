# Consent And Synthetic Data

## Consent automation

- Default functional scenario: accept the standard banner, then verify the
  required granted state in Tag Assistant before continuing.
- Refused, partial, and update scenarios: apply the requested choice and verify
  the resulting state before executing the journey.
- Treat the verified event-level Consent panel as authoritative for tag gating;
  a clicked banner button is not proof of the resulting consent state.
- Record defaults, update events, final state, and timing order.

## Synthetic form data

For authorised test journeys, infer required field formats from labels,
validation, locale, and context. Generate unique synthetic values per run. Never
use a real person's identity, credentials, phone number, payment data, or inbox.

Accept required terms and declarations needed for the tested submission. Leave
optional marketing, profiling, partner sharing, and communication preferences
unchecked or explicitly refused, except when that opt-in is the tested action.

Stop at CAPTCHA, payment, email/SMS code, magic link, or external approval.
Record created accounts, leads, and subscriptions in run context with cleanup
status. Never put generated passwords in evidence or reports.
