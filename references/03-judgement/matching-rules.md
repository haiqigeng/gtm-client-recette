# Matching Rules

Interpret the original plan without weakening its semantics.

| Rule | Required comparison |
| --- | --- |
| `equals` | Value and type match exactly. |
| `absent` | Key does not exist. |
| `present` | Key exists and is not JavaScript `undefined`. |
| `not_empty` | Value is present and not an empty state. |
| `type` | Exact primitive or compound type matches. |
| `regex` | Confirmed complete pattern matches. |
| `one_of` | Value and type belong to the confirmed enumeration. |
| `contains` | Required member or substring exists. |
| `changes` | Value changes across the specified steps. |
| `stable` | Identifier remains stable across the specified steps. |
| `documented_transform` | Confirmed input, rule, and output match. |
| `range` | Numeric value/type is within confirmed inclusive min/max. |
| `format` | Complete value matches an allowlisted format. |
| `anti_pattern` | Confirmed forbidden pattern does not occur. |
| `vendor_equivalent` | Explicit vendor parameter mapping preserves accepted value/type. |
| `business_rule` | One or more declared safe cross-field rules pass. |

Preserve `absent`, `undefined`, explicit `null`, empty string, empty array,
empty object, and actual value types. Do not silently equate string `"29.90"`
with number `29.90`.

Require runtime equality across raw, resolved, GTM-variable, and tag-parameter
links unless a documented transformation applies. Show every value and type
when they differ.

Use one destination-specific requirement for `vendor_equivalent`; record the
canonical field and actual vendor parameter name. Do not infer a GA4-to-media
mapping from convention alone.

For browser sends, map the destination ID, vendor event name, and tested
parameter to explicit `query.`, `body.`, or `headers.` paths. A copied decoded
field cannot pass unless it agrees with the retained raw request at that path.

Use only the declarative operators documented in
`conditional-business-and-privacy-rules.md`. Never evaluate a plan expression
as Python or JavaScript.

Apply dependencies:

- expected event absent after a valid settled action: occurrence `FAIL`;
  unavailable raw and downstream checks, including applicable event-level
  consent, `BLOCKED`; overall `FAIL`;
- planned event present while its page/action/state trigger condition is false:
  occurrence or trigger `FAIL` even when its payload is otherwise correct;
- event count exceeds the accepted count inside one controlled action window:
  occurrence `FAIL`; legitimate occurrences from separately required
  interaction instances remain separate cases rather than duplicates;
- event occurs in the wrong action window, before its prerequisite, after its
  accepted boundary, or in the wrong sequence: occurrence/chronology `FAIL`
  unless the acceptance rule explicitly permits that timing;
- observed business push has no acceptance mapping: record relevant unexpected
  `REVIEW`; use `FAIL` only when it contradicts a confirmed trigger, occurrence,
  exclusion, sequence, or sensitive-data rule;
- Preview disconnected or action not valid: affected execution `BLOCKED`, not
  implementation `FAIL`;
- raw field wrong but event present: raw `FAIL`; still inspect downstream
  values for stale or transformed state;
- tag fires with wrong or `undefined` parameter: firing `PASS`, parameter
  `FAIL`, overall `FAIL`;
- tag fires but browser request is missing or has the wrong destination or
  parameter: firing `PASS`, destination `FAIL`, overall `FAIL`;
- trigger or setup/main/cleanup order differs: firing may pass, trigger or
  sequence fails;
- expected consent denial blocks the tag: consent and blocking `PASS`;
- confirmed forbidden sensitive data is emitted: sensitive-data `FAIL` even
  when event/tag/request layers pass;
- previous `PASS` is now a confirmed `FAIL`: current layer status remains
  visible and regression is `FAIL`; a blocked/review/not-tested retest is
  unverified, not a proven regression;
- ambiguous plan meaning: `REVIEW`, never guessed `PASS`.

Aggregate an event across its applicable interaction cases using the worst
case status. A successful representative instance cannot hide another
placement or finite value that failed.

Every declared applicable component keeps a verdict. Removing a destination,
trigger, sequence, consent, business-rule, privacy, client-check, or regression
verdict is an invalid result, not a way to improve the roll-up.

The overall requirement and event status is the worst applicable component.
