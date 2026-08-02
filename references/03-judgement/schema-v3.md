# Normalized results and session schema v3

## Boundary

Every new normalized run and session ledger uses `schema_version: 3`.

```json
{
  "schema_version": 3,
  "run": {},
  "requirements": [],
  "unexpected": [],
  "blockers": [],
  "evidence": []
}
```

Schema v3 is a certification boundary. Migrate v2 only through
`migrate_schema_v2_to_v3.py`. The migration preserves source coordinates,
event order, accepted expectations, journey discovery, material variants, and
prior case locations. It resets actions, evidence, anomalies, blockers,
component verdicts, and overall verdicts. No historical `PASS` is inherited.

## Normalized run

`run` requires identity, client/site/environment, primary web container and
workspace, complete client-side container inventory, browser contexts,
tracking-plan source, acceptance scope, execution timestamp, exact requirement
and event inventories, deterministic included layers, tag scope, and journey
authority. Optional Audit/Configuration artifacts remain supporting-only and
cannot supply verdict evidence.

The 19 canonical layers and their order are defined only by
`layer_contract.py`; the tracking plan never removes a layer. The normalized
requirements preserve one source-bound expectation per atomic field/rule and
one plan-ordered event group for feedback.

## Requirement observations

Each requirement retains:

- stable requirement/event-group IDs and full source coordinates;
- journey/action/value/type/discovery context;
- exact event, field, occurrence, variable, tag, destination, consent,
  trigger/sequence and business-rule expectations supplied by acceptance;
- independent action, raw API Call or source-signal, resolved Data Layer, GTM
  variable, tag configuration/runtime, browser request, consent, rule,
  privacy, client-context, and regression observations;
- one component verdict per applicable evidence link; and
- evidence IDs bound to the evidence catalogue.

Preserve explicit `null`. Distinguish `present`, `absent`, `undefined`,
`null`, `empty_string`, `empty_array`, and `empty_object`; preserve the exact
JSON type. An occurred dataLayer event uses the exact Tag Assistant API Call
as raw evidence. The Data Layer panel is resolved state, never raw proof.

## Session case and action

Each case stores its event/requirements, exact URL/element/placement/action,
material variant, discovery source, scope, tag scope, container set, complete
tag inventory, all-layer applicability card, inventory revision, and final
execution state.

The applicability card contains every canonical layer exactly once, in order,
as `MANDATORY` or `CONDITIONAL`. Conditional false is explicit
`NOT_APPLICABLE`; no row may disappear.

Each action stores its retained retry lineage, connection epoch, Preview
cursor, page/action context, independent website completion signal, adaptive
settlement, complete business-push count, 19 layer rows, and the exact 8-row
matrix for every in-scope tag.

If a material tag appears after freeze, `revise-tag-inventory` stores the
prior inventory/card in `applicability_history`, increments
`inventory_revision`, adds the late tag, recomputes the card, resets the case
to `PENDING`, and requires a retry of the retained settled action. Historical
snapshots are never edited or used as current proof.

## Per-tag evidence matrix

Every in-scope tag has exactly one row for each of:

- `gtm_variable`;
- `tag_configuration`;
- `tag_firing`;
- `tag_parameter`;
- `destination_request_when_applicable`;
- `consent_when_applicable`;
- `trigger_logic_when_applicable`; and
- `tag_sequence_when_applicable`.

Each row repeats the frozen `tag_id`, name, container, category, and delivery.
Direct evidence kinds that identify a tag carry the same exact `tag_id`:
GTM variable, tag configuration/runtime, browser request, trigger, sequence,
and Tag Assistant consent. Evidence for another tag is invalid even when its
values happen to match.

## Expected comparison anchors

Every exact per-tag comparison has `expected_anchor`:

```json
{
  "name": "value",
  "expected_anchor": {
    "source": "tracking_plan",
    "requirement_id": "REQ-001",
    "path": "expectation.expected_value",
    "transform": "identity"
  },
  "expected_value": 29.9,
  "expected_type": "number",
  "actual_value": 29.9,
  "actual_type": "number",
  "status": "PASS"
}
```

Accepted anchor sources are `tracking_plan`, `explicit_acceptance_rule`,
`raw_data_layer_mapping`, `resolved_gtm_variable_contract`, and
`tag_template_semantics`. The requirement ID must belong to the action's event
group; the path must resolve uniquely; any declared transform is deterministic.
The stored expected value/type must equal the resolved anchor. Equality between
self-declared expected/actual values is insufficient.

Redacted comparisons retain the anchor, status, and safe comparison basis but
never expected/actual values.

`tag_firing.expected_firing` and destination expected request behaviour carry
their own anchors even though they are control fields rather than comparison
arrays.

## Browser request reconciliation

A browser-sending tag's positive request row contains unique `request_ids` and
`request_count`. The count equals the unique IDs, and the IDs exactly equal the
referenced `browser_network_request` evidence bound to the same tag/action/
container. Expected absence requires direct complete
`browser_network_capture` evidence. A fabricated, unrelated, or unreferenced
request ID is invalid.

## Privacy boundary

Run the deterministic sensitive-data scan across normalized requirements and
the entire exportable session: surfaces, case/action context, business-push
context, and every per-tag comparison/detail. Findings never retain raw values,
samples, value-derived lengths, or fingerprints. Any unredacted sensitive
content prevents validation and workbook generation.

## Workbook cell contract

Excel cells cannot exceed 32,767 characters. The report builder splits long
tabular serialized values into physical continuation rows prefixed
`[part i/n]`; short identity cells repeat for context. It recomputes physical
row counts after expansion and reloads the workbook to reject oversized cells.
Non-tabular oversized cells fail with an actionable error. Silent openpyxl/
Excel truncation is forbidden.

## Status and strict invariants

Working rows may be `PENDING`; final events use `PASS`, `FAIL`, `BLOCKED`,
`REVIEW`, or `NOT_TESTED`. Conditional layers alone may use
`NOT_APPLICABLE`. Event status is the worst applicable component/case/anomaly.

Strict validation rejects incomplete inventories, omitted layers, unclassified
pushes, open/pending actions, wrong retry lineage, cross-tag proof, unanchored
expectations, request-ID mismatches, unsafe session values, action-boundary
drift, raw/resolved substitution, missing direct evidence, unsupported silent
transforms, and any aggregate status that hides a worse result.
