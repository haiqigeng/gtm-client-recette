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

Preserve `absent`, `undefined`, explicit `null`, empty string, empty array,
empty object, and actual value types. Do not silently equate string `"29.90"`
with number `29.90`.

Require runtime equality across raw, resolved, GTM-variable, and tag-parameter
links unless a documented transformation applies. Show every value and type
when they differ.

Apply dependencies:

- expected event absent after a valid settled action: occurrence/raw `FAIL`;
  occurrence `FAIL`; unavailable raw and downstream checks `BLOCKED`; overall
  `FAIL`;
- Preview disconnected or action not valid: affected execution `BLOCKED`, not
  implementation `FAIL`;
- raw field wrong but event present: raw `FAIL`; still inspect downstream
  values for stale or transformed state;
- tag fires with wrong or `undefined` parameter: firing `PASS`, parameter
  `FAIL`, overall `FAIL`;
- expected consent denial blocks the tag: consent and blocking `PASS`;
- ambiguous plan meaning: `REVIEW`, never guessed `PASS`.

The overall requirement and event status is the worst applicable component.
