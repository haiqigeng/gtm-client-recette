# Incremental Evidence Workflow

## Contents

1. [Initialize once](#initialize-once)
2. [Open and checkpoint the browser session](#open-and-checkpoint-the-browser-session)
3. [Complete one event group](#complete-one-event-group)
4. [Apply and validate an event](#apply-and-validate-an-event)
5. [Resume and finish](#resume-and-finish)

Use one recette workflow. `acceptance_scope`, source-bound requirements and
their applicability determine which evidence links are required; do not create
run modes.

## Initialize once

Inspect the plan, interpret source-bound requirements, then initialize the
plan-ordered schema-v2 working file:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json

python -B scripts/init_coverage_ledger.py interpreted-requirements.json working-results.json `
  --run-id RUN-001 `
  --title "GTM recette" `
  --site-url https://example.test/ `
  --environment Preprod `
  --environment-class preprod `
  --container-id GTM-XXXX `
  --workspace Recette `
  --tracking-plan-source tracking-plan.xlsx `
  --acceptance-scope "All requirements in the supplied tracking plan"
```

The initializer infers applicable evidence layers from each expectation. It
does not create a different workflow for a smaller acceptance boundary.

## Open and checkpoint the browser session

Use `preview_session_ledger.py` to keep stable surfaces and action boundaries:

```powershell
python -B scripts/preview_session_ledger.py init session.json `
  --profile-path "<approved-browser-context>" `
  --approved-origin https://example.test
```

Register the GTM workspace, Tag Assistant and website. Before each interaction,
open one action; settle it only after the event stream reaches the quiet
boundary. Checkpoint after Preview connection, authentication handback,
completed journeys and connection recovery.

Record the action and its independent website completion signal:

```powershell
python -B scripts/preview_session_ledger.py begin-action session.json `
  --action-id ACT-001 `
  --requirement-id REQ-001 `
  --url https://example.test/product `
  --element "Add to cart" `
  --action click `
  --last-event-before 10 `
  --consent-state "analytics_storage=granted" `
  --quiet-window-ms 3000 `
  --timeout-ms 20000

python -B scripts/preview_session_ledger.py settle-action session.json `
  --action-id ACT-001 `
  --first-event-after 11 `
  --settled-final-event 12 `
  --expected-seen true `
  --preview-connected-after true `
  --interaction-outcome completed `
  --completion-signal "Basket count changed from 0 to 1" `
  --stream-settled true `
  --settlement-reason expected_and_quiet
```

For one bounded retry, begin a new action with
`--retry-of-action-id <retained-action-id>`. Never reuse an action ID or merge
the failed and repeated windows.

## Complete one event group

Execute every applicable case for the next event in plan order. Reconcile every
business push in every case window, then populate all source-bound requirement
rows for that event.

Preserve the comparison chain:

```text
tracking-plan requirement
-> occurrence and chronology
-> raw dataLayer/API Call or accepted source signal
-> resolved Data Layer
-> GTM variable
-> tag configuration
-> firing/non-firing and count
-> runtime tag parameter
-> browser destination request
-> verdict
```

Every applicable component keeps its own status. A correct earlier link cannot
repair a later mismatch, and a later browser request cannot repair an earlier
payload/configuration failure.

Create an event patch:

```json
{
  "event_group_id": "EVG-007",
  "requirements": [
    {
      "requirement_id": "REQ-007-event",
      "event_group_id": "EVG-007"
    }
  ],
  "evidence": [],
  "unexpected": [],
  "blockers": []
}
```

`requirements` must contain the complete normalized rows for every requirement
in the event group. Evidence IDs must be new and unique.

## Apply and validate an event

Apply the patch atomically and validate only that completed event:

```powershell
python -B scripts/incremental_recette.py apply-event `
  working-results.json event-007-patch.json
```

Or validate an already populated event:

```powershell
python -B scripts/incremental_recette.py validate-event `
  working-results.json --event-group-id EVG-007
```

Do not issue the analyst verdict until the incremental validator passes. Then
return:

```text
Event 07 — add_to_cart: FAIL
- Cases: 4/4 executed
- Tag firing: PASS, once per action
- Runtime price: FAIL; expected number 29.90, observed string "29.90"
```

Continue automatically to the next event.

## Resume and finish

Inspect progress at any time:

```powershell
python -B scripts/incremental_recette.py status working-results.json
python -B scripts/preview_session_ledger.py status session.json
```

After every event is finalized:

```powershell
python -B scripts/incremental_recette.py final-validate working-results.json
python -B scripts/validate_business_rules.py working-results.json
python -B scripts/scan_sensitive_data.py working-results.json
python -B scripts/build_recette_report.py `
  working-results.json gtm-recette-results.xlsx --strict
```

Do not complete a run with `PENDING` events, unclassified business pushes,
failed incremental validation, sensitive raw evidence, or a workbook that
fails reload checks.
