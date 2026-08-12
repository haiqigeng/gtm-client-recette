# Normalized results and session schema v3

## Boundary

Every new normalized run and session ledger uses `schema_version: 3`. New
normalized runs also use `run.action_boundary_contract_version: 1`; new guided
session ledgers use `operator_contract_version: 1`.

```json
{
  "schema_version": 3,
  "run": {"action_boundary_contract_version": 1},
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
and browser-network cursors before/after, readiness/settlement check IDs,
page/action context, independent website completion signal, adaptive
settlement, complete business-push count, 19 layer rows, and the exact 8-row
matrix for every in-scope tag. Its normalized `action_boundary` repeats these
check IDs and cursors so strict reconciliation detects drift.

New session ledgers carry `operator_contract_version: 1`, `runtime_checks`,
`event_closures`, `closure_history`, and `operator_state`. A runtime check is a normalized direct
capture bound to one action/case/connection epoch and the exact registered GTM,
Tag Assistant, and website surfaces. It records exact containers/workspaces,
website and selected Preview URLs, readiness booleans, Preview cursor, network
cursor, and direct evidence IDs. An after-action check additionally records
`first_event_after` and `observed_business_push_count`. Consumed check IDs and
cursors must match the action exactly.

`page_match_mode` is `exact` by default. `same_origin_spa` is valid only for a
URL difference backed by a direct route-transition evidence ID in the same
capture. A mid-action runtime failure uses `interrupted_action`, a supported
failure reason, last trustworthy cursors and exact observed-push count. It
settles the retained action as uncertain and blocks the case without requiring
or fabricating unavailable downstream layer/tag rows. A strictly linked retry
reopens the case as `PENDING` without removing the prior action's blocker.
Only a Preview disconnect advances the connection epoch. A mistaken, unconsumed
orphan check can be retained as `voided` with a timestamp and exact reason;
voided checks cannot be consumed or linked to actions.

One guided run contains exactly one configured client web container. Multiple
applicable containers require separate container-scoped normalized runs until
the runtime contract exposes per-container Preview and network cursors.

Only `playwright_runtime_probe` and `browser_connector_runtime_probe` are valid
runtime producers. Captured and recorded timestamps must be fresh and ordered
around the action. Runtime action-boundary/network evidence uses exact
`runtime_check_id` and `runtime_phase` bindings; before/after checks cannot
reuse evidence IDs.

Each event closure stores `event_group_id`, original `plan_order`, exact case
IDs, executed final-action IDs, `closed_at`, and `feedback_emitted_at`.
Closures form an exact prefix during execution and equal the complete event
inventory at final validation. A late material tag discovery removes the
affected closure and reopens the event for the required retained retry.
`reopen-event` does the same for a late interaction or variant: it moves the
affected closure suffix into `closure_history` with reason and timestamp, then
requires plan-ordered reclosure. Closure case/action membership is exact but
does not depend on incidental list order.

Schema-v3 results created before this boundary contract remain readable when
the marker is absent. They use the earlier action-boundary validation and
cannot use the guided operator. Never synthesize missing checks or cursors;
freshly normalize and recapture when current certification is needed.

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

Feedback also derives `primary_outcome` and `anomaly_flags`. They are output
taxonomy only: the former names the first actionable broken chain link; the
latter surfaces missing/duplicate/premature/delayed/wrong-order/wrong-context/
unplanned occurrences. Neither is stored as acceptance evidence or allowed to
change canonical component status.

Generated workbooks and sidecars expose `Output contract: 2`; defect CSV rows
repeat `output_contract_version`. Consumers that depend on exact headers must
use that value; it covers the primary-outcome, anomaly, and runtime-cursor
columns. CSV text beginning with `=`, `+`, `-`, or `@` is escaped as literal
text. The final workbook and FINISHED session state use a crash-recoverable
paired transaction, and input/output paths cannot alias each other.
