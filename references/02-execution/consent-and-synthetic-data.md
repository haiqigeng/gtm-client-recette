# Consent And Synthetic Data

## Natural consent first

Capture the natural/default event-level consent state before interacting with
the CMP for every case, even when consent is not an acceptance requirement.

- For a normal functional journey with no consent acceptance requirement, use
  the site's ordinary choice needed to run the journey. Retain the baseline and
  mark the conditional consent layer `NOT_APPLICABLE` only after its predicate
  is recorded false.
- For required refused, partial, accepted, or preference-change scenarios,
  apply the specified choice and verify the resulting event-level state before
  executing the action.
- Treat Tag Assistant's event-level Consent panel as authoritative for tag
  gating. A banner click alone is not evidence of the resulting state.
- Preserve default, update, event-level state, tag behaviour, and timing order.

## Advanced Consent Mode v2

Only apply this section when the acceptance source requires it. Capture and
compare:

- `ad_storage`;
- `analytics_storage`;
- `ad_user_data`;
- `ad_personalization`;
- the default and every relevant update transition;
- the exact state at the concerned tag event;
- built-in and additional tag consent checks;
- expected `full`, `cookieless`, or `blocked` browser transport;
- applicable `ads_data_redaction` and `url_passthrough` settings and observable
  effects.

Denied storage can still produce consent-aware/cookieless browser requests in
an advanced setup; do not equate `denied` with every request being absent.
Compare the expected transport mode and actual request evidence.

Use current official references when interpreting Google behaviour:

- [Consent mode overview](https://developers.google.com/tag-platform/security/concepts/consent-mode)
- [Set up consent mode on websites](https://developers.google.com/tag-platform/security/guides/consent)

This is technical acceptance evidence, not a legal determination.

## Exceptional CMP override

Never inject or simulate consent routinely. Consider a browser-session override
only when all of these are true:

1. the environment is test, preprod, staging, or an explicitly approved
   production exception;
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

For production, require a distinct
`production_cmp_session_override` authorization, the exact temporary method,
a `CMP_PRODUCTION_ENVIRONMENT` blocker, and restoration confirmation. Keep
`native_cmp_status` non-PASS. A downstream event may be checked under the
simulated state, but any in-scope native-CMP acceptance remains failed,
blocked, or under a precise semantic review.

## Synthetic form data

For an in-scope journey:

- infer formats from label, locale, HTML validation, and server feedback;
- use unique, obviously synthetic values and reserved example domains;
- never use a real person's identity, inbox, phone, credentials, or payment
  data;
- never expose generated passwords in chat, the session ledger, evidence, or
  the report;
- accept only required terms, privacy notices, and declarations;
- leave optional marketing, profiling, partner-sharing, newsletter, and
  communication choices unchecked unless that opt-in is the tested conversion.

Required privacy acknowledgements and an opt-in that is itself part of the
tested conversion are ordinary journey controls, not new authorization or
consent checkpoints.

Use `scripts/generate_synthetic_profile.py` as a safe starting point. Adapt only
to the form's validated format and prefer a client-provided test range when a
phone number is required.

## Complete encountered gates by default

Treat a form, sign-up, login, lead, account, or checkout-preparation gate
encountered on a planned journey as required work unless the analyst explicitly
excludes it. Do not skip it, stop at the first page, or assign `BLOCKED` merely
because it requires data entry.

Complete all ordinary fields and reversible steps with synthetic data. In a
confirmed test, staging, or preproduction environment, execute the ordinary
final lead, registration, or conversion submission by default. Ask first only
when the environment is production or unconfirmed, the action mutates a real
account, the downstream consequence is unresolved, or the effect is
irreversible. Record only the non-sensitive outcome and cleanup status of any
created test account, lead, or subscription.

Synthetic credentials may be created, entered, and reused ephemerally inside
the same controlled run so sign-up and subsequent login can both be tested.
Never send them through chat or store them in JSON, logs, screenshots,
evidence, or the workbook. If an existing or protected account is required,
prepare the exact login state and ask the analyst to sign in inside the
dedicated browser.

Starting a full recette establishes run-wide authority for all equivalent safe
ordinary actions in its declared origin and environment: synthetic identity,
form fields, privacy acknowledgements, tested-conversion opt-ins, and ordinary
submission. It does not need to be requested again per event. Additional scopes
may cover non-production leads or explicitly approved reversible production
submissions. CMP overrides always retain their own separate approval. Every
scope excludes credentials/protected sign-in, MFA, CAPTCHA, verification, real
payment, external approval, and irreversible action.

## Ordinary UI-control recovery

Do not treat an inoperable checkbox, privacy control, or submit control as a
consent or authorization blocker. Preserve its failed action window, then try
all safe control paths: scroll into view, click the associated label, click the
control directly, use a pointer click, use the keyboard toggle, and retry once
from clean state. If none works, use `UI_CONTROL_BLOCKER` with every attempted
method and evidence. Tracking observed during failed attempts remains eligible
as premature or wrong-context evidence.

## Protected journey handoff

At Google or other protected sign-in, CAPTCHA, MFA, email/SMS verification,
magic link, real payment, external approval, or another protected boundary:

1. complete every safe step leading to the boundary;
2. preserve the session, Preview connection, and action checkpoint;
3. show the exact browser step that remains;
4. ask the analyst to complete it in the dedicated browser;
5. resume the same planned journey after `DONE` or `SIGNED IN`;
6. use final `BLOCKED` only when the analyst cannot complete it, no safe method
   exists, or an evidenced external blocker prevents completion.

Never automate real payment or an irreversible account action. Never silently
skip the events that follow a protected gate.
