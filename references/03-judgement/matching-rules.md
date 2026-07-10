# Matching Rules

Interpret the original client plan without forcing a new input template. Build
an internal matrix that preserves source references, journey/step, event,
field path, expected value, match rule, tag, variable, parameter, consent, and
required status.

Use the narrowest confirmed rule:

| Rule | Meaning |
| --- | --- |
| `equals` | Fixed value and type must match. |
| `absent` | The key must not exist. |
| `present` | The key must exist. |
| `not_empty` | The value is non-null and non-empty. |
| `type` | The value has the specified primitive/compound type. |
| `regex` | The confirmed pattern matches. |
| `one_of` | The value belongs to the confirmed enumeration. |
| `contains` | A required member or substring exists. |
| `changes` / `stable` | The value changes or remains stable across specified steps. |
| `documented_transform` | A confirmed input-to-output transformation applies. |

Evaluate the full chain independently:

`tracking plan -> raw API-call payload -> resolved Data Layer -> GTM variable -> runtime tag parameter`

Require strict equality across runtime links unless a documented transformation
applies. Preserve type distinctions. Do not weaken fixed-value checks to make a
result pass.

Use provided journeys first. Infer actions from mock-ups, labels, selectors,
URLs, and event context only when needed; mark inferred steps and ask before
ambiguous or consequential actions.
