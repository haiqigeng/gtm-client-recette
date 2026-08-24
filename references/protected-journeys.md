# Protected journeys

## Ordinary forms

Within the approved test scope, use synthetic data and the ordinary visible user journey.
Ordinary navigation, field entry, validation, and form submission are authorized by the
skill invocation; do not pause for a second permission question. Pause only when the
submission reaches a protected or materially consequential gate. Capture:

- before-state and enabled/visible controls;
- field entry, validation and submit interaction;
- response/navigation and visible success/error outcome;
- continuous source activity, Preview decisions and browser requests.

Fill independent fields efficiently, but do not use hidden script submission to bypass
the UI. Try one ordinary recovery for scroll, enablement or normal validation. A tracking
event does not prove submission success: a technically correct event on a failed form is
an overall failure, and a successful form without required tracking also fails.

When useful, generate stable non-personal values with
`python -B "<skill-root>/scripts/generate_synthetic_profile.py" --help`; never seed it
with personal or client-sensitive data.

## Consent

For an ordinary tracking scenario, inspect the CMP and accept it before the measured
interaction when consent is not already granted. Do not wait for the user to notice the
banner: otherwise expected tags may be suppressed and every downstream layer can fail
for the wrong reason. If consent setup used an unmeasured page, authorize only one Core
load afterward.

Leave consent untouched, reject it, withdraw it, or select granular choices only when
that scenario is explicitly requested or materially discovered. Activate consent checks
from explicit plan requirements and observed behavior: CMP UI, Consent Mode events/state,
consent fields, consent-controlled tags/requests, or a known consent API.

Bind consent evidence to the action and scenario that produced it. A warm consent state
from another locale/session cannot certify the current branch. Keep natural CMP behavior
separate from any explicitly authorized override. An override tests only the override
path and cannot erase a natural-path defect.

If an ordinary action was accidentally captured while required consent remained denied,
classify dependent firing/delivery rows as setup `BLOCKED`, accept consent, and use one
structured retest. Do not blame the client implementation. In an explicitly denied
scenario, suppression passes only with complete fired/non-fired and network windows; an
unavailable surface remains `BLOCKED`.

The skill reports observed tracking behavior; it does not issue legal compliance advice.

## Protected or consequential gates

Credentials, MFA, CAPTCHA, email/SMS verification, magic links, real payments and
external approval require a same-session handoff:

1. stop before the gate and do not end the browser session;
2. record the event/scenario, exact target/tab/document, Preview epoch, action state and
   whether the consequential outcome may already have occurred;
3. ask the user to complete only the protected step;
4. resume after re-proving the same identity and collecting all evidence deltas;
5. if continuity is lost, preserve prior evidence and block only the affected claims.

Never bypass a gate, repeat a potentially completed consequential action automatically,
or open a new unauthenticated window merely to satisfy bookkeeping. If outcome is
uncertain, reconcile visible/server response evidence before any retry.

## Purchases and external outcomes

Use independent confirmation such as a success page/order reference, accepted response,
or authorized sandbox state. A `purchase` event or fired conversion tag alone is not
proof of purchase. Real monetary transactions require explicit authorization and remain
protected.

## Acquisition and fresh visits

Do not refuse acquisition-sensitive or SEO-related tracking tests. Use the strongest
authorized method available: natural referral, browser-controlled fresh/referrer
context, explicit campaign parameters, or a user-provided reproducible entry. Record
storage freshness, referrer/campaign input and method.

A simulated Google referral validates tracking response to that context. It does not
certify search indexing, ranking, attribution beyond the browser-observed chain, or a real
organic impression.
