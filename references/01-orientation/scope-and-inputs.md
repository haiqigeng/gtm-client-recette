# Scope and inputs

## Use this skill when

- a tracking plan or explicit acceptance rule already exists;
- the work is client-side GTM Preview / Tag Assistant recette on an actual site;
- the analyst wants event, tag, browser-request, journey, and anomaly verdicts;
- all applicable interactions and material scenario classes must be covered.

Do not use it to design the tracking plan, change or publish GTM, repair the
site, certify server-side GTM, decide legal compliance, or prove vendor-side
receipt/reporting.

## Minimum input

The acceptance source and an approved test origin are essential. URLs,
journeys, screenshots, selectors, expected containers, consent scenarios, and
baseline results improve discovery but can be inspected or inferred. Ask only
when a missing fact changes authorization, scope, or a verdict.

Before opening client files or navigating, show a compact preflight naming the
inputs, approved origins/environment, existing browser/session, ordinary
actions, protected gates, evidence directory, and outputs. Wait for explicit
`READY`; renew it if scope, origin, or consequential authority changes.

Preserve source order and provenance. A requirement must retain its source
file/sheet/row or section, event group, exact expected value and JSON type,
matching rule, occurrence rule, source mechanism, tag and destination contract,
and journey hint.

## Authority and boundaries

The normal authority is to execute ordinary reversible website journeys with
safe synthetic data, including ordinary form fields and non-consequential
submissions. Redact at capture time before values enter chat or any ledger.
Never store credentials, cookies, tokens, form personal data, or another raw
sensitive value. Explicit raw-body inspection stays in a separate quarantine
that is never attached as result evidence.

Protected gates require an analyst handoff: credentials, federated sign-in,
MFA, CAPTCHA, email/SMS verification, magic link, real payment, external
approval, or an irreversible/consequential action. The handoff must return to
the same approved browser context, tab, and Preview session.

## Tag scope

`analytics_only` is the default and still includes exact media tags declared by
the acceptance plan. Use `all_relevant_client_side_tags` or `explicit_tag_set`
only when explicitly requested. Keep detected excluded tags visible with a
reason; never relabel a tag to alter scope.

## Supporting artifacts

Container audits, configuration exports, prior runs, and screenshots can guide
discovery but cannot decide a current live verdict. A prior run contributes only
discovery and comparison context; current actions, consent, evidence, and
verdicts must be captured again.
