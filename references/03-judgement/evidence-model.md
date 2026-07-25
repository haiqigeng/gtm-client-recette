# Evidence Model

## Authoritative evidence

For a full recette use:

- Tag Assistant event `API Call`: exact object passed to `dataLayer.push`;
- Tag Assistant `Data Layer`: resolved state at that event;
- Tag Assistant `Variables`: resolved GTM-variable values;
- `Tags Fired` and `Tags Not Fired`;
- tag detail: configuration, runtime parameters, fire count, and direct error;
- event-level Consent panel when applicable;
- read-only GTM configuration inspection when Preview lacks static detail.

## Supplemental evidence

Label browser interception, console, network, screenshot, and navigation
observations with their actual source. Supplemental evidence may prove
chronology or explain an event pushed before Preview attached. It cannot
silently satisfy exact Tag Assistant API Call evidence in a full run.

## Raw versus resolved

The API Call is the authoritative raw push. The Data Layer panel is cumulative
resolved state and can inherit earlier values. Never merge them, backfill a raw
field from resolved state, or summarize either with ellipses.

## Wanted tag not fired

Capture:

- firing trigger evaluation;
- blocking trigger or exception;
- relevant variable values;
- event-level consent;
- direct Preview or console failure text;
- most specific reason and source.

Use reason sources `preview`, `console`, `consent`, `inferred`, or
`not_established`. When evidence cannot establish a reason, write exactly:

`Reason not established from available Preview evidence`

Do not convert that observation into an unproved root cause or fix.

## Evidence IDs

Assign stable unique IDs. Every normalized result references catalogue entries.
Capture connection, action boundary, each occurred event, every failure or
review, every wanted non-fire, every protected blocker, every relevant consent
transition, and every approved override.

Never place authentication credentials, Preview tokens, real personal data, or
generated passwords in evidence.
