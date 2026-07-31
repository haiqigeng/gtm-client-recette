# Conditional, Business, And Privacy Rules

## Conditional and non-deterministic coverage

Keep the standard statuses. Do not add `CONDITIONAL` or `AB_VARIANT` as
verdicts.

For a conditional branch use:

```json
{
  "expected_occurrence": {
    "rule": "conditional",
    "condition_id": "AUTHENTICATED",
    "branch_rule": "once"
  },
  "scenario": {
    "scenario_id": "SCN-AUTH",
    "kind": "personalized",
    "condition": "Synthetic user is authenticated",
    "branch": "authenticated",
    "condition_met": true,
    "attempts": ["..."],
    "evidence_id": "EVD-SCENARIO-001"
  }
}
```

Create separate atomic requirements for branches that have different
expectations. A conditional `PASS` requires evidence that the declared
condition was acquired and that the branch occurrence rule passed.

Use `non_deterministic` only when the plan itself accepts non-determinism.
Document every safe reproduction attempt. Observation can pass; absence cannot
silently pass. Apply the plan's declared bounded-attempt result. Use `REVIEW`
only when the plan does not define how that result should be judged and state
the exact semantic question; use `BLOCKED` when execution or authoritative
evidence is unavailable.

## Declarative business rules

Never execute a free-form tracking-plan expression. Normalize only allowlisted
operators:

- `equals_path`;
- `sum_product_equals`;
- `all_items_equal`;
- `implies`;
- `unique_across_requirements`;
- `range`;
- `format`;
- `regex`.

Every applicable rule needs a stable `rule_id`, operator, explicit
paths/options, result, reason, status, evidence ID, and deterministic
`evaluation_source`. Select the accepted source by mechanism:

- use the exact raw API Call payload for `source_mechanism: data_layer_push`;
- use captured `source_signal.payload` or `source_signal.value` for a native,
  DOM, direct-vendor, or other non-dataLayer mechanism; and
- use resolved Data Layer only as an evidenced fallback when the mechanism's
  authoritative surface is unavailable.

Do not evaluate payload-only business rules when the accepted occurrence
branch requires absence. Keep occurrence count, scenario acquisition, tag
non-firing, request absence, trigger, consent, and every other applicable
check. For `unique_across_requirements`, compare one evidence surface class;
if relevant occurrences mix raw, source-signal, and resolved fallback
surfaces, use `REVIEW` with that precise limitation rather than inventing a
duplicate or certifying uniqueness.

Malformed or empty configured paths are invalid and can never produce
`PASS`. Run:

```powershell
python scripts/validate_business_rules.py normalized-results.json
```

The validator supports common acceptance logic without `eval`, including:

- event value equals the sum of item price multiplied by quantity;
- every item currency equals event currency;
- coupon presence implies a positive discount;
- transaction identifiers are unique across normalized requirements;
- numeric ranges;
- UUID, ISO date/datetime, ISO currency, email, and regex formats.

Apply only rules declared by the plan or explicitly confirmed by the analyst.
Do not invent accounting, tax, discount, or rounding semantics. Set an explicit
tolerance where decimals are accepted.

Equality is JSON-type strict: `true` does not equal `1`. Item-array rules fail
when a member is not an object, and numeric tolerance is absolute only; a zero
tolerance means exact numeric equality. Invalid rule or regex configuration is
a validation error. Every declared rule set requires its component verdict, so
removing a failed result or verdict cannot leave the requirement passing.

Rule output summarizes structured values and redacts every string primitive
before CLI, workbook, or chat output. It retains no value-derived fingerprint
or length. Field-path context still classifies keyed phone, name, address, and
similar values when possible. This prevents an unrecognized identifier from
leaking through a diagnostic rule result.

For uniqueness, atomic requirements sharing the same event group and runtime
event index represent one occurrence and are counted once. This prevents
multiple vendor/destination rows for one purchase from being mistaken for
duplicate transactions.

## GA4 ecommerce depth

When the acceptance source adopts GA4 recommended ecommerce semantics, resolve
the applicable event and item fields against current official references:

- [Recommended events](https://developers.google.com/analytics/devguides/collection/ga4/reference/events)
- [Measure ecommerce](https://developers.google.com/analytics/devguides/collection/ga4/ecommerce)
- [Validate ecommerce](https://developers.google.com/analytics/devguides/collection/ga4/validate-ecommerce)

Validate the complete accepted array, not only `value`:

- event-specific required fields;
- `items[]` presence and per-item required identity;
- event and item value types;
- currency/value coupling required by the acceptance source;
- promotion or list context where planned;
- transaction ID presence, consistency, and uniqueness where planned.

Official recommendations inform interpretation only when the tracking plan
adopts them. A bespoke client contract remains authoritative.

## Sensitive-data safeguards

For a full new run, initialize a `sensitive_data_policy` and scan:

- exact raw API-call payloads;
- resolved Data Layer snapshots;
- runtime tag values;
- destination request URLs, query parameters, bodies, and decoded tested
  values, including retained request headers;
- journey URLs and page titles;
- non-dataLayer source-signal payloads/values;
- actual values retained by applicable client checks.

The deterministic scanner recognizes confirmed sensitive field names, email
patterns, sensitive URL keys, keyed phone/IP values, optional unkeyed
heuristics, allowlisted paths, and analyst-supplied custom patterns.
It recursively inspects decoded query values from absolute and relative URLs,
including vendor parameters whose values are percent-encoded.
Custom patterns require a stable ID, valid regex, `custom` category, and
confirmed/suspected confidence.

Common encoded and decoded analytics/media user-data keys such as `em`, `ph`,
`fn`, `ln`, `external_id`, `uip`, and normalized `ep.*`/`up.*` families are
classified by their technical value. Plaintext values remain in their
confirmed email, phone, person-name, postal, IP, or sensitive-query category.
A syntactically recognized SHA-256 value or Google `tv.*` user-data bundle is
reported as `hashed_user_data`, which is visible but not forbidden by the
default technical leakage policy. This format check does not prove source
normalization, consent, vendor receipt, or legal compliance; those remain
separate accepted requirements.

Run:

```powershell
python scripts/scan_sensitive_data.py normalized-results.json
```

Never retain the detected raw value in findings, workbook cells, chat, or saved
evidence. Keep only:

- path;
- category;
- confidence;
- detection basis;
- allowlist decision;
- `PASS`, `FAIL`, or `REVIEW`;
- redacted marker;
- the constant marker `value_fingerprint: "not-retained"` for schema
  compatibility.

`scanned_targets` must exactly enumerate the normalized client-side surfaces,
and stored findings must exactly equal a fresh deterministic scan, including
their redacted marker, basis, and non-retention marker. Naming a scan layer
without a policy, scan evidence, or sensitive-data verdict is invalid.

Use:

- `FAIL` for an unallowlisted, confirmed category forbidden by the accepted
  policy;
- `REVIEW` for a heuristic/suspected match that needs analyst confirmation;
- `PASS` when no forbidden finding remains.

The scanner is a technical leakage check, not a legal classification system.
The analyst owns allowlists and policy interpretation. If live real data is
detected, stop copying it, redact derived evidence, and report the location and
category only.

Exact evidence means exact safe test evidence; it never authorizes retaining
real personal data. An unallowlisted `FAIL` or unresolved `REVIEW` finding makes
the normalized artifact unsafe: the validator and workbook builder refuse it.
Use the scanner's redacted output for the immediate finding, quarantine the
source capture, and either rerun with synthetic data or create a safe redacted
evidence record before workbook generation. Report the affected event as
incomplete/failed with path, category, and detection basis only.

Allowlist only an analyst-confirmed safe test path or accepted technical value.
Do not use an allowlist to make real personal data exportable.
