# Evidence Model

## Browser surfaces

Preserve the relationship among:

1. GTM workspace: account, web container, workspace, Preview, and environment.
2. Tag Assistant: connection, timeline, event panels, tags, variables, Data
   Layer, consent, and console.
3. Debugged website: journey actions, consent interactions, and page state.

Human sign-in, MFA, CAPTCHA, payment, email confirmation, and irreversible
actions remain manual. Do not store credentials or publish GTM changes.

## Event evidence

For every selected timeline event capture event order/name, raw API call, Data
Layer panel, variables, fired tags, not-fired tags, consent, console, and
evidence IDs.

The `API call` is the exact live object passed to `dataLayer.push(...)` and is
the authoritative raw payload. The `Data Layer` panel is the resolved state at
that moment and may include inherited values from earlier pushes. Never merge
these sources.

## Tag evidence

For fired or failed tags record name, type, fire count, runtime parameters,
variable values, consent, and direct error evidence. For a wanted tag that does
not fire, capture trigger evaluation, blocking exception, variable values,
consent, failure text, and the most specific observed reason.

Use `preview`, `console`, `consent`, or `inferred` as reason source. If no reason
is established, write `Reason not established from available Preview evidence`.
Do not convert this observation into a fix or root-cause diagnosis.

Assign stable evidence IDs. Capture screenshots or equivalent machine-readable
evidence for connection, every tested event, every failure/review, every wanted
non-fired tag, and every consent transition.
