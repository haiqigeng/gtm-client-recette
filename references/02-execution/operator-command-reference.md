# Operator command reference

Use these commands only at the stage routed from `SKILL.md`. They implement the
single full-recette workflow; they are not alternate recette modes.

## Normalize

For a reviewed/approved `ga4-tracking-plan` delivery:

```powershell
python scripts/import_ga4_tracking_plan_handoff.py DELIVERY -o interpreted-requirements.json
```

For a workbook:

```powershell
python scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

Initialize schema v3:

```powershell
python scripts/init_coverage_ledger.py interpreted-requirements.json normalized-results.json `
  --run-id RUN-001 --title "GTM recette" `
  --site-url https://example.test/ --environment Preprod `
  --environment-class preprod --container-id GTM-XXXX --workspace Recette `
  --tracking-plan-source tracking-plan.xlsx `
  --acceptance-scope "Confirmed tracking-plan requirements" `
  --tag-scope analytics_only
```

Migrate v2 discovery context without proof inheritance:

```powershell
python scripts/migrate_schema_v2_to_v3.py old-results.json normalized-results.json `
  --legacy-session old-session.json --case-manifest retest-cases.json
```

## Session and evidence

Initialize and register the controlled surfaces:

```powershell
python scripts/preview_session_ledger.py init session.json `
  --profile-path <controlled-profile> --approved-origin https://example.test
```

The guided operator is the default control plane. The ordered verbs are:

1. `register-surface`
2. `register-case`
3. `register-tag` for every detected tag
4. `complete-tag-inventory`
5. capture a `before_action` runtime snapshot and use operator `start-event`
6. `record-push` or transactional `import-pushes`
7. `scaffold-tag-results`, complete its exact rows, then `import-tag-results`
8. `record-layer` once for each canonical layer, or one transactional
   `import-layers`
9. capture an `after_action` runtime snapshot and use operator `settle-action`
10. use operator `close-event` for mandatory immediate feedback
11. repeat in plan order, then use operator `finish-run`

Each runtime snapshot is a direct browser/Preview/network state capture:

```json
{
  "check_id": "READY-ACT-001",
  "captured_at": "2026-08-12T10:00:00+02:00",
  "capture_source": "playwright_runtime_probe",
  "browser_context_id": "recette-profile",
  "connection_epoch": 1,
  "gtm_workspace_surface_id": "gtm-primary",
  "tag_assistant_surface_id": "preview-primary",
  "website_surface_id": "site-primary",
  "containers": [{"container_id": "GTM-XXXX", "workspace": "Recette"}],
  "website_url": "https://example.test/product",
  "selected_page_url": "https://example.test/product",
  "page_match_mode": "exact",
  "expected_overlay_active": false,
  "preview_connected": true,
  "target_interactive": true,
  "target_uncovered": true,
  "lifecycle_observed": true,
  "stream_quiet": true,
  "network_capture_active": true,
  "preview_event_cursor": 10,
  "network_request_cursor": 24,
  "evidence_ids": ["EVD-ACTION-001", "EVD-NET-CAPTURE-001"]
}
```

Use only `playwright_runtime_probe` or `browser_connector_runtime_probe`.
Capture and record within five minutes. Each referenced action-boundary and
network evidence row must bind to this exact check and phase:

```json
{
  "evidence_id": "EVD-ACTION-001",
  "kind": "action_boundary",
  "source": "Playwright",
  "capture_mode": "direct",
  "action_id": "ACT-001",
  "runtime_check_id": "READY-ACT-001",
  "runtime_phase": "before_action",
  "captured_at": "2026-08-12T10:00:00+02:00"
}
```

Use separate evidence IDs for `before_action` and `after_action`; generic or
reused proof is rejected.

The current guided runtime accepts exactly one container/workspace row. If
more than one client web container is applicable, run one normalized certified
session per container from the same reproducible checkpoint. A multi-container
snapshot is rejected because one Preview/network cursor cannot prove several
container streams.

Use `page_match_mode: same_origin_spa` only when the website and selected
Preview URLs differ because of an evidenced client-side route. Add
`route_transition_evidence_id` and include that same ID in `evidence_ids`.
This does not permit a different origin. `resume` requires the normal runtime
checks but may use `expected_overlay_active: true` when the retained action
legitimately owns the visible overlay.

An `after_action` snapshot additionally supplies `first_event_after` and
`observed_business_push_count`; its two cursors are the settled final cursors.
The operator derives action-boundary fields from these snapshots:

```powershell
python scripts/recette_operator.py start-event normalized-results.json session.json `
  before-action.json --event-group-id EVG-001 --case-id CASE-001 `
  --action-id ACT-001 --consent-state "analytics_storage=granted"

python scripts/recette_operator.py settle-action normalized-results.json session.json `
  after-action.json --action-id ACT-001 --expected-seen true `
  --interaction-outcome completed --completion-signal "Basket count changed" `
  --settlement-reason expected_and_quiet
```

The lower-level `record-runtime-check`, `begin-action`, and `settle-action`
commands remain available for diagnosis. They enforce the same captured-state
contract; `begin-action` never accepts a manually entered cursor.

If runtime control fails after the action opened, preserve the failed boundary:

```powershell
python scripts/recette_operator.py interrupt-action normalized-results.json session.json `
  interrupted-action.json --action-id ACT-001 `
  --blocker-id BLK-RUNTIME-001 `
  --reason "Browser network capture became unavailable before settlement"
```

The snapshot uses phase `interrupted_action`, one supported `failure_reason`
(`browser_crashed`, `network_capture_lost`, `preview_disconnected`, or
`surface_unavailable`), the last trustworthy cursors, and the exact observed
push count. The action is retained as `SETTLED`/`uncertain`; the case becomes
`BLOCKED`. No unavailable layer or tag result is invented. Restore the runtime
and use a fresh action with `--retry-of-action-id` for that exact retained
attempt. The prior action keeps its blocker while the active case returns to
`PENDING`. Only `preview_disconnected` advances the connection epoch.

If a before-action check was captured under a mistaken action ID and no action
was ever created, retain it explicitly:

```powershell
python scripts/preview_session_ledger.py void-runtime-check session.json `
  --check-id READY-WRONG-ID --reason "Corrected action ID before interaction"
```

Only an unconsumed, unreferenced check can be voided.

Import the complete event-layer card in one write when useful:

```powershell
python scripts/preview_session_ledger.py import-layers session.json layers.json `
  --action-id ACT-001
```

The file is an array or `{ "layer_results": [...] }`. A malformed, duplicate,
or inapplicable row rejects the whole command without persisting partial rows.

If a material tag appears after the inventory was frozen, first settle the
current action, then version the inventory and force a retained retry:

```powershell
python scripts/preview_session_ledger.py revise-tag-inventory session.json `
  --case-id CASE-001 --tag-id TAG-NEW --tag-name "GA4 - Event" `
  --container-id GTM-XXXX --tag-category analytics `
  --tag-delivery browser_request --vendor-family ga4 `
  --template-type "GA4 Event" --consent-required false `
  --evidence-id EVD-TAG-NEW --reason "Late tag appeared in direct Preview inventory"
```

If an interaction, variant, or tag is found after closure, reopen explicitly:

```powershell
python scripts/recette_operator.py reopen-event normalized-results.json session.json `
  --event-group-id EVG-001 `
  --reason "Late material footer interaction discovered"
```

The selected closure and later closure suffix move to `closure_history`.
Prior proof stays available, but the selected event and preserved later events
must be reclosed in plan order before final output.

Install the recorder before navigation and decode safe request records:

```javascript
await context.addInitScript({ path: "scripts/datalayer_recorder.js" })
```

```powershell
python scripts/decode_browser_requests.py requests.json decoded-requests.json
```

## Incremental event delivery and mandatory closure

```powershell
python scripts/incremental_recette.py scaffold-event normalized-results.json `
  --event-group-id EVG-001 --session-ledger session.json `
  --output event-001-patch.json
python scripts/recette_operator.py close-event normalized-results.json session.json `
  event-001-patch.json --event-group-id EVG-001
```

Scaffolds preserve discovery only. They never inherit verdicts or evidence.
`close-event` applies and validates the exact event slice, records closure in
plan order, and prints the complete per-layer/per-tag feedback object. The next
event cannot start before this succeeds.

## Final validation and workbook

```powershell
python scripts/recette_operator.py finish-run normalized-results.json session.json `
  gtm-recette-results.xlsx
```

`finish-run` performs strict normalized/session reconciliation, verifies one
plan-ordered closure per event, and publishes the validated workbook plus
FINISHED session ledger as one crash-recoverable transaction. Results,
session, and workbook paths must be distinct. Use the
lower-level validators and sidecar flags only when additional diagnostic or
delivery files are required.

Pause/resume accepts both safe states:

```powershell
# Open action: supply a fresh resume capture.
python scripts/recette_operator.py resume-run normalized-results.json session.json `
  resume-runtime.json

# Between events: omit the capture; the next start-event captures readiness.
python scripts/recette_operator.py resume-run normalized-results.json session.json
```

Pause with both paired paths so an interrupted result/session transaction is
recovered before the session is read:

```powershell
python scripts/recette_operator.py pause-run session.json `
  --results normalized-results.json --label "Protected analyst handback"
```

The guided operator accepts only normalized results declaring
`run.action_boundary_contract_version: 1`. Older schema-v3 files remain
readable through the legacy validator; re-normalize and recapture instead of
inventing their missing runtime proof.

## Release provenance

Release archives carry `RELEASE-MANIFEST.json` with the exact source file set,
per-file SHA-256 hashes, and an aggregate tree hash:

```powershell
python scripts/build_skill_package.py --output dist/gtm-client-recette-vX.Y.Z.zip
python scripts/verify_release_artifact.py dist/gtm-client-recette-vX.Y.Z.zip
```
