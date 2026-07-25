# Normalized Results Schema V2

## Contents

1. [Top-level contract](#top-level-contract)
2. [Run context and inventories](#run-context-and-inventories)
3. [Atomic requirement](#atomic-requirement)
4. [Evidence layers](#evidence-layers)
5. [Blockers and unexpected observations](#blockers-and-unexpected-observations)
6. [Validation invariants](#validation-invariants)

## Top-level contract

Use schema version 2 for every new run:

```json
{
  "schema_version": 2,
  "run": {},
  "requirements": [],
  "unexpected": [],
  "blockers": [],
  "evidence": []
}
```

Do not normalize a full recette as prose collections. The atomic unit is one
source-bound tracking-plan requirement, not merely an event name.

Schema-v1 or observation-only data must be re-normalized from its original plan
and evidence. Do not mechanically promote incomplete v1 rows to schema-v2
`PASS`.

## Run context and inventories

`run` requires:

- `run_id`;
- `run_type`: `FULL_TRACKING_PLAN_RECETTE` or
  `SCOPED_ACCEPTANCE_RECETTE`;
- `report_title`, `client`, `site_url`, `environment`, and
  `environment_class`;
- `container_id`, `workspace`, `tracking_plan_source`, and
  `acceptance_scope`;
- `executed_at`;
- `included_layers`;
- `requirement_inventory`: every requirement ID in original source order;
- `event_inventory`: every event group in original plan order.

Use this event inventory shape:

```json
{
  "event_group_id": "EVG-007",
  "event_name": "add_to_cart",
  "plan_order": 7
}
```

For a full recette, the applicable evidence chain includes raw API call,
resolved Data Layer, GTM variable, tag configuration, tag firing, runtime tag
parameter, and consent when applicable.

For a scoped recette, list the exact included layers. Never imply certification
of an excluded layer.

## Atomic requirement

Each `requirements` row contains:

```json
{
  "requirement_id": "REQ-Events-R42-ecommerce.value",
  "event_group_id": "EVG-007",
  "scope_status": "IN_SCOPE",
  "source": {},
  "journey": {},
  "expectation": {},
  "event_observed": true,
  "occurrence_evidence": {},
  "action_boundary": {},
  "raw_api_call": {},
  "resolved_data_layer": {},
  "gtm_variable": {},
  "tag": {},
  "consent": {},
  "verdict": {},
  "evidence_ids": [],
  "notes": ""
}
```

### Source

Preserve all available coordinates:

```json
{
  "reference": "tracking-plan.xlsx / Events / row 42 / F42",
  "file": "tracking-plan.xlsx",
  "sheet": "Events",
  "row": 42,
  "cells": ["B42", "F42", "J42"],
  "section": "Checkout",
  "plan_order": 17
}
```

`plan_order` is the stable normalized requirement order. Do not replace the
original row/cell coordinates with that number.

### Journey

Record:

- `journey_id`, `step_id`, `action`, and `url`;
- `selector_or_element`;
- `inferred`, `inference_source`, and `confidence`;
- every `attempted_routes` entry;
- `execution_status`: `PENDING`, `EXECUTED`, `BLOCKED`, `REVIEW`, or
  `NOT_TESTED`.

### Expectation

Record:

- `event_name`, `field_path`, `match_rule`, `expected_value`, and
  `expected_type`;
- `expected_occurrence`;
- `variable_name` when a GTM variable is required;
- `tag_name`, `expected_firing`, `tag_configuration_field`, and runtime
  parameter expectation when a tag is concerned;
- `expected_tag_configuration` when the plan prescribes an exact variable or
  configuration mapping;
- `expected_consent_state` only when consent is an acceptance requirement;
- input, rule, and output for a `documented_transform`.

Preserve explicit expected `null`; do not omit `expected_value`.

Represent `expected_occurrence` as `once`, `at_least_once`, `absent`, or an
object such as:

```json
{
  "rule": "before_event",
  "anchor_event_name": "cmp_init"
}
```

### Action boundary

For an attempted in-scope action retain:

```json
{
  "preview_connected_before": true,
  "target_ready_before": true,
  "consent_state_before": {},
  "last_event_before": 37,
  "action_timestamp": "ISO-8601",
  "first_event_after": 38,
  "settled_final_event": 42,
  "quiet_window_ms": 2000,
  "timeout_ms": 15000,
  "stream_settled": true
}
```

For an absent expected event, retain the same negative action evidence.

### Occurrence evidence

Keep occurrence and chronology separate from payload correctness:

```json
{
  "actual_count": 1,
  "event_indexes": [39],
  "anchor_event_name": "cmp_init",
  "anchor_event_index": 42,
  "evidence_id": "EVD-RAW-039"
}
```

Use `event_occurrence` as its own component verdict. For a missing expected
event after a stable action, occurrence is `FAIL` and unavailable downstream
payload, variable, and tag checks are `BLOCKED`.

## Evidence layers

### Raw API call

For an occurred event:

```json
{
  "capture_source": "tag_assistant_api_call",
  "event_index": 39,
  "timestamp": "ISO-8601",
  "payload": {},
  "field_state": "present",
  "field_value": 42.5,
  "field_type": "number",
  "evidence_id": "EVD-RAW-039"
}
```

The payload must be the exact structured Tag Assistant API Call object. Do not
store prose, ellipses, or omitted placeholders. Browser interception is
supplemental and must use `capture_source: browser_interception`.

### Resolved Data Layer and GTM variable

Keep the resolved Data Layer snapshot separate:

```json
{
  "snapshot": {},
  "field_state": "present",
  "field_value": 42.5,
  "field_type": "number",
  "evidence_id": "EVD-DL-039"
}
```

Use the same field-state contract for a GTM variable and add `applicable` and
`name`.

Allowed states are:

- `present`;
- `absent`;
- `undefined`;
- `null`;
- `empty_string`;
- `empty_array`;
- `empty_object`.

Allowed types are `string`, `number`, `boolean`, `array`, `object`, `null`,
`undefined`, and `absent`.

### Concerned tag

Use `applicable: true` only for a concerned tag. Record:

- `relevance`: expected fire, expected block, relevant unexpected firing, or
  explanation of a wanted non-fire;
- name, expected firing, actual firing, and fire count;
- configuration field and configured value;
- runtime state, value, and type;
- separate configuration and runtime evidence IDs;
- non-firing reason and source when applicable.

Do not add unrelated tags.

### Consent

Use `applicable: true` for an acceptance check or necessary tag-behaviour
context. Record `scenario_id`, scenario, one source, event-level state, and
evidence.

`session_override` additionally requires:

- non-production environment;
- explicit analyst approval and approval evidence;
- exact temporary method;
- before and after state;
- a referenced `CMP_TEST_ENVIRONMENT` blocker.

Never merge a natural-CMP and override result into one requirement.

### Verdict

Use component fields:

```json
{
  "event_occurrence": "PASS",
  "raw_payload": "PASS",
  "resolved_data_layer": "PASS",
  "gtm_variable": "PASS",
  "tag_firing": "PASS",
  "tag_parameter": "PASS",
  "consent": null,
  "overall": "PASS",
  "failure_layer": null,
  "mismatch": null,
  "reason_source": "preview"
}
```

Use `null` for a non-applicable component. The overall result is the worst
applicable component.

## Blockers and unexpected observations

Every blocker needs a stable ID, type, checkpoint, description, affected
requirement IDs, outcome, status, and evidence.

For a protected checkpoint, record whether analyst intervention was required,
requested, and completed. A final protected `BLOCKED` is invalid when help was
never requested.

Keep relevant unexpected events, duplicate pushes, and unexpected concerned
tags in `unexpected`. Do not turn every unrelated native or container event into
noise.

## Validation invariants

Strict mode rejects:

- incomplete or duplicate inventories;
- requirements stored out of plan order;
- missing source references;
- placeholder raw payloads;
- occurred events without exact Tag Assistant API Call evidence in a full run;
- merged raw and resolved evidence;
- value/type/state contradictions;
- unsupported silent transformations;
- event absence without a stable action boundary;
- `PASS` values that contradict fixed expectations;
- wanted non-fired tags without a reason and source;
- unrelated tag comparisons;
- `NOT_TESTED` used for an attempted blocker;
- protected blockers where analyst help was never requested;
- unapproved or production consent overrides;
- unknown or duplicate evidence IDs;
- an overall status that hides a worse component verdict.

The executable example is
`tests/fixtures/valid_full.json`. Validate normalized results with:

```powershell
python scripts/build_recette_report.py normalized-results.json --strict --validate-only
```
