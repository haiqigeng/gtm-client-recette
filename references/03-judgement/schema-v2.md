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

Do not normalize a recette as prose collections. The atomic unit is one
source-bound tracking-plan requirement, not merely an event name.

Schema-v1 or observation-only data must be re-normalized from its original plan
and evidence. Do not mechanically promote incomplete v1 rows to schema-v2
`PASS`.

## Run context and inventories

`run` requires:

- `run_id`;
- `report_title`, `client`, `site_url`, `environment`, and
  `environment_class`;
- `container_id`, `workspace`, `tracking_plan_source`, and
  `acceptance_scope`;
- `executed_at`;
- `included_layers`;
- `requirement_inventory`: every requirement ID in original source order;
- `event_inventory`: every event group in original plan order.

Schema version remains 2, but every current run must explicitly prove its
client-side scope:

- `containers`: required non-empty inventory with one primary plus applicable
  analytics, marketing, or shared entries, each explicitly typed `web` or
  `client_side`;
- `browser_contexts`: stable viewport, device, user-state, and variant
  definitions;
- `regression_context`: optional previous-run source and acceptance-relevant
  read-only container changes.

The singular `container_id` and `workspace` must match the primary web
container. Server containers are not valid entries. Re-normalize a legacy row
that lacks this inventory before certification.

Use this event inventory shape:

```json
{
  "event_group_id": "EVG-007",
  "event_name": "add_to_cart",
  "plan_order": 7
}
```

Use one recette workflow. `acceptance_scope`, source-bound expectations, and
per-requirement applicability determine the required evidence links. Do not
add a run-mode field.

Enumerate every applicable base and extension layer in `included_layers`:

- `raw_api_call`;
- `resolved_data_layer`;
- `gtm_variable`;
- `tag_configuration`;
- `tag_firing`;
- `tag_parameter`;
- `consent_when_applicable`;
- `source_signal_when_no_data_layer_push`;
- `destination_request_when_applicable`;
- `trigger_logic_when_applicable`;
- `tag_sequence_when_applicable`;
- `business_rules_when_declared`;
- `sensitive_data_scan`;
- `client_checks_when_applicable`;
- `regression_when_baseline_provided`;
- `container_context_when_applicable`;
- `conditional_scenarios_when_applicable`.

The validator derives required layers from in-scope expectations and rejects
an omitted applicable layer. Extra names outside the supported set are also
invalid. An unavailable layer remains explicit in the requirement status and
cannot be silently substituted.

## Atomic requirement

Each `requirements` row contains:

```json
{
  "requirement_id": "REQ-Events-R42-ecommerce.value",
  "event_group_id": "EVG-007",
  "scope_status": "IN_SCOPE",
  "source": {},
  "journey": {},
  "container_id": "GTM-XXXX",
  "browser_context_id": "mobile-auth-b",
  "scenario": {},
  "expectation": {},
  "event_observed": true,
  "occurrence_evidence": {},
  "action_boundary": {},
  "raw_api_call": {},
  "source_signal": {},
  "resolved_data_layer": {},
  "gtm_variable": {},
  "tag": {},
  "destination_request": {},
  "trigger_evaluation": {},
  "tag_sequence": {},
  "consent": {},
  "business_rule_results": [],
  "sensitive_data_scan": {},
  "client_checks": [],
  "regression": {},
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
- `action_value`, exact `action_value_type`, and `action_value_source`;
- `selector_or_element`;
- `inferred`, `inference_source`, and `confidence`;
- every `attempted_routes` entry;
- `execution_status`: working `PENDING`, then `EXECUTED`, `BLOCKED`, or
  confirmed `NOT_TESTED`.

Use action-value source `not_applicable`, `synthetic`,
`analyst_supplied_non_sensitive`, `protected_analyst_entry`, or
`site_default`. `not_applicable` retains explicit `null`. Protected analyst
input stores only `<analyst-entered-protected>`, never the entered value.

Keep the lightweight interaction census and its per-case action boundaries in
the coverage/session ledger. Do not clone a source-bound requirement merely
because it has repeated element instances. Roll the normalized requirement up
from all applicable cases using the worst status, and bind distinct failures
or unexpected occurrences to their own evidence.

Each session case records stable `case_id`, event group, exact requirement IDs,
URL, element, placement, action, material variant, discovery source, scope,
execution status, applicable layers, container IDs, and authorization IDs. Its
attempts retain contiguous attempt numbers and retry lineage. Final validation
requires every in-scope case to be `EXECUTED` or explicitly `BLOCKED`.

### Expectation

Record:

- `event_name`, `field_path`, `match_rule`, `expected_value`, and
  `expected_type`;
- `expected_occurrence`;
- `variable_name` when a GTM variable is required;
- `tag_name`, `tag_delivery`, `expected_firing`,
  `tag_configuration_field`, exact `expected_tag_configuration`, and runtime
  parameter expectation when a tag is concerned;
- `source_mechanism` when the accepted signal is not an explicit
  `data_layer_push`;
- `vendor_family`, `destination_id`, `destination_event_name`, expected
  request behaviour, endpoint pattern, and destination parameter when a
  client-side destination is accepted;
- `destination_id_parameter_path`, `destination_event_parameter_path`, and
  `destination_parameter_path`, rooted at `query.`, `body.`, or `headers.`,
  when a browser send is expected;
- `trigger_contract` and `sequence_contract` when exact trigger/exception/order
  behaviour is accepted;
- `expected_consent_state` only when consent is an acceptance requirement;
- `consent_contract` for advanced four-signal, transition, transport,
  redaction, or passthrough requirements;
- `business_rules` and `sensitive_data_policy` when applicable;
- input, rule, and output for a `documented_transform`.

Preserve explicit expected `null`; do not omit `expected_value`.
Use `tag_delivery: browser_request` for a sending analytics/media tag and
`tag_delivery: local_only` only for a genuinely local tag. A browser-sending
tag requires vendor/destination ID, event identity, their exact request paths,
endpoint pattern, and expected request behaviour. `local_only` cannot retain
destination fields.
Quote literal vendor keys that contain path syntax:
`query["ep.value"]` and `query["cd[value]"]`. Use `[0]` for a numeric index and
`[]` only for an array wildcard.

Represent `expected_occurrence` as `once`, `at_least_once`, `absent`, or an
object such as:

```json
{
  "rule": "before_event",
  "anchor_event_name": "cmp_init"
}
```

Conditional branches use `rule: conditional`, stable `condition_id`, and
`branch_rule`. `non_deterministic` requires documented attempts and cannot pass
on silent absence.

### Action boundary

For an attempted in-scope action retain:

```json
{
  "action_id": "ACT-017",
  "retry_of_action_id": null,
  "preview_connected_before": true,
  "target_ready_before": true,
  "consent_state_before": {},
  "last_event_before": 37,
  "action_timestamp": "2026-07-25T10:01:00+00:00",
  "interaction_outcome": "completed",
  "completion_signal": "Visible confirmation state",
  "first_event_after": 38,
  "settled_final_event": 42,
  "quiet_window_ms": 2000,
  "timeout_ms": 15000,
  "stream_settled": true,
  "settlement_reason": "expected_and_quiet",
  "evidence_id": "EVD-ACTION-017"
}
```

The timestamp must be timezone-qualified. Cursor values are non-negative
integers with `last_event_before < first_event_after <= settled_final_event`,
and occurrence/anchor indexes must fit the retained window. For an absent
expected event, retain the same negative action evidence. A finalized
`REVIEW` attempt needs the boundary too; `REVIEW` cannot erase chronology.

Current session-ledger output also retains the stable `action_id`, optional
`retry_of_action_id`, `interaction_outcome`, independent safe
`completion_signal`, and `settlement_reason`. A completed interaction requires
a non-empty completion signal, and a failed or uncertain interaction cannot
support a missing-event occurrence `FAIL`. Final certification requires the
normalized boundary to match the retained session action exactly.

The session action also records `observed_business_push_count` and one
`layer_results` row for every layer declared applicable to the completed case.
The explicit count must equal the classified business-push rows assigned to
the action.

Each session business-push row records `stream_id`, positive
`connection_epoch`, and `event_index`. Their combination is unique.
`connection_epoch` defaults to `1` and increments when a recovered Preview
connection restarts event numbering.

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

When a resolved GTM, variable, tag, firing, or runtime-parameter link applies,
the payload must be the exact structured Tag Assistant API Call object. Do not
store prose, ellipses, or omitted placeholders. Browser interception uses
`capture_source: browser_interception`; it can preserve raw-browser chronology
but cannot certify an applicable Preview-dependent link.

### Non-dataLayer source signal

When the accepted signal is a GTM native/auto event, DOM event, direct vendor
call, Custom HTML execution, or enhanced-measurement event, do not fabricate a
raw API call. Record `source_signal` with mechanism, event name, actual capture
source, observed state, and evidence ID. Keep resolved, variable, tag, and
destination layers when they remain applicable.

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

Add `container_id`, `vendor_family`, `destination_id`, and `template_type` when
applicable. Preserve direct execution/console errors separately from firing.

### Destination request

For an accepted analytics or media send, record:

- applicable vendor, container, and destination ID;
- exact vendor-facing event/conversion name;
- request behaviour/count, method, URL, and browser-network source;
- stable `request_id` for the direct network capture;
- raw request paths for destination ID, vendor event, and tested parameter;
- decoded parameter state, value, and type;
- primary evidence ID and optional vendor-helper evidence.

Network `PASS` requires `capture_source: browser_network`. Vendor helpers are
supplementary and browser evidence does not certify vendor ingestion. The
validator derives query values from `request_url` and resolves structured body
or header paths; every decoded ID, event, and parameter claim must reconcile
with that raw request evidence.

### Trigger and sequence

`trigger_evaluation` records `ALL`, `ANY`, or `TRIGGER_GROUP`, actual result,
each condition, blocking exceptions, and evidence. `tag_sequence` records the
actual ordered tags and evidence. A passing row must reconcile with the
declared contracts. Condition truth is recomputed from expected/actual values,
matched blocking exceptions force a blocked result, and the default sequence
contract is exact. Set `allow_additional_steps: true` explicitly only when the
acceptance source permits intervening steps.

### Consent

Use `applicable: true` for an acceptance check or necessary tag-behaviour
context. Record `scenario_id`, scenario, one source, event-level state, and
evidence.

`session_override` additionally requires:

- explicit analyst approval and approval evidence;
- exact temporary method and `override_scope: session_only`;
- before and after state;
- non-PASS `native_cmp_status` and whether native CMP acceptance is in scope;
- a referenced `CMP_TEST_ENVIRONMENT` blocker outside production.

A production exception additionally requires
`production_exception_approved`, `production_approval_evidence_id`,
`restoration_confirmed`, and a `CMP_PRODUCTION_ENVIRONMENT` blocker. Simulated
consent can exercise downstream tags but cannot make native CMP acceptance
`PASS`.

Never merge a natural-CMP and override result into one requirement.

For Advanced Consent Mode v2, `consent_contract` can prescribe all four
signals, default/update transition, full/cookieless/blocked transport,
`ads_data_redaction`, `url_passthrough`, required tag-level consent types, and
tag-level checks. Each check status is recomputed from its exact expected and
actual state.

### Business, sensitive-data, and client checks

`business_rule_results` maps every declared safe rule ID to a deterministic
status, evidence ID, and `evaluation_source`. Declared rules require the
component verdict and use type-strict comparisons. Data-layer rules evaluate
the raw API Call payload; non-dataLayer rules evaluate the captured source
signal; resolved state is only a fallback. Invalid path syntax is rejected.

`sensitive_data_scan` records scanned targets and redacted findings. Findings
must never retain `value`, `raw_value`, `sample`, or a value-derived fingerprint
or length. The compatibility field `value_fingerprint` is always
`not-retained`. The target inventory and full redacted findings must match a
fresh deterministic scan, including encoded query values.

`client_checks` uses explicit categories for SPA/auto-event source, responsive
context, cross-domain/linker/cookie/iframe behaviour, dataLayer integrity,
platform mapping, debug mode/DebugView, current vendor limits, Custom
JavaScript, container conflicts, and tag dependencies.

`regression` is applicable only with a supplied baseline and records baseline
and current acceptance status, change classification, and evidence.

Every applicable extension requires its own component verdict. A normalized
row cannot omit destination, trigger, sequence, consent, business-rule,
sensitive-data, client-check, or regression evidence/verdict while preserving
an overall `PASS`.

The same rule applies to base layers: required raw API Call, resolved Data
Layer, GTM variable, tag configuration, tag firing, and runtime parameter each
retain their own component verdict. `tag_parameter` never substitutes for
`tag_configuration`.

### Evidence catalogue binding

Every top-level `evidence` row requires a unique ID, kind, actual source, path
or URL, timezone-qualified `captured_at`, and concise redacted description.
Nested evidence IDs are bound to their layer-specific kind: action boundary,
API Call, resolved Data Layer, variable, tag configuration/runtime,
source/scenario, browser request/helper, trigger, sequence, consent,
business-rule evaluation, privacy scan, client checks, and regression
comparison cannot be interchanged.

### Verdict

Use component fields:

```json
{
  "event_occurrence": "PASS",
  "source_signal": null,
  "raw_payload": "PASS",
  "resolved_data_layer": "PASS",
  "gtm_variable": "PASS",
  "tag_configuration": "PASS",
  "tag_firing": "PASS",
  "tag_parameter": "PASS",
  "destination_request": "PASS",
  "destination_parameter": "PASS",
  "trigger_logic": "PASS",
  "tag_sequence": "PASS",
  "consent": null,
  "business_rule": "PASS",
  "sensitive_data": "PASS",
  "client_checks": "PASS",
  "regression": null,
  "overall": "PASS",
  "failure_layer": null,
  "mismatch": null,
  "reason_source": "preview"
}
```

Use `null` for a non-applicable component. The overall result is the worst
applicable component. `PENDING` is allowed only in the working initializer and
cannot pass strict validation. `REVIEW` is valid only with
`review_basis: semantic_ambiguity` and a non-empty `review_question`; missing
execution or evidence is `BLOCKED`.

## Blockers and unexpected observations

Every blocker needs a stable ID, type, checkpoint, description, affected
requirement IDs, outcome, status, and evidence.

For a protected checkpoint, record whether analyst intervention was required,
requested, and completed. A final protected `BLOCKED` is invalid when help was
never requested.

Keep relevant unplanned, duplicate, premature, delayed, wrong-order, and
wrong-context business pushes, plus unexpected concerned tags, in `unexpected`.
Include the case/action identity, event index, page/state context,
classification, actual observation, status, and evidence IDs in the row or its
bound evidence. An anomalous push row also carries `observed_push_id` so strict
validation can reconcile it with the chronological session stream. Do not turn
every unrelated native `gtm.*` or container event into noise.

A mapped unexpected row participates in the affected event roll-up with its
own `REVIEW` or `FAIL`; it cannot remain visible while the event stays `PASS`.

## Evidence catalogue linkage

Every evidence row includes `capture_mode`: `direct`, `deterministic`,
`analyst_supplied`, or `supplemental`. Direct evidence additionally includes
the applicable `action_id`, `event_index`, `container_id`, `request_id`,
`tag_name`, and `configuration_field`. Naming conventions, reconstructed
values, and generic request-time correlation cannot claim direct evidence.

## Validation invariants

Strict mode rejects:

- incomplete or duplicate inventories;
- missing, pending, or unexecuted session cases and open actions;
- observed push counts that differ from classified stream rows;
- missing per-case applicable layer results;
- normalized action boundaries that differ from session actions;
- requirements stored out of plan order;
- missing source references;
- placeholder raw payloads;
- occurred events without exact Tag Assistant API Call evidence when a
  Preview-dependent link applies;
- non-dataLayer signals without exact source evidence;
- merged raw and resolved evidence;
- value/type/state contradictions;
- unsupported silent transformations;
- event absence without an independently completed interaction and stable
  relevant-stream action boundary;
- `PASS` values that contradict fixed expectations;
- wanted non-fired tags without a reason and source;
- destination PASS without browser-network evidence or with wrong ID,
  request ID, endpoint, send behaviour, parameter, value, or type;
- trigger, exception, or tag-sequence false PASSes;
- advanced consent false PASSes or unapproved/unsafe session overrides;
- cross-field results that contradict deterministic evaluation;
- unredacted or incomplete sensitive-data findings;
- client-context and prior-run false PASSes;
- unrelated tag comparisons;
- `NOT_TESTED` used for an attempted blocker;
- protected blockers where analyst help was never requested;
- production consent overrides without the explicit exception, approval
  evidence, correct blocker, and restoration;
- `REVIEW` without a precise semantic question;
- reconstructed evidence presented as direct capture;
- credentials or synthetic personal fields retained in the session ledger;
- unknown or duplicate evidence IDs;
- an overall status that hides a worse component verdict.

Executable examples are `tests/fixtures/valid_full.json`,
`tests/fixtures/valid_limited_layers.json`, and the client-side extension
fixture used by `tests/test_pipeline.py`. Validate normalized results with:

```powershell
python scripts/build_recette_report.py normalized-results.json `
  --strict `
  --validate-only `
  --session-ledger session.json
```
