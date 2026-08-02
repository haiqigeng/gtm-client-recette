# Incremental Evidence Workflow

## Contents

1. [Initialize once](#initialize-once)
2. [Open and checkpoint the browser session](#open-and-checkpoint-the-browser-session)
3. [Complete one event group](#complete-one-event-group)
4. [Apply and validate an event](#apply-and-validate-an-event)
5. [Resume and finish](#resume-and-finish)

Use one recette workflow. `acceptance_scope` defines accepted semantics; the
deterministic layer policy defines the evidence links. A tracking plan never
selects or removes evidence layers. Do not create run modes.

## Initialize once

Inspect the plan, interpret source-bound requirements, then initialize the
plan-ordered schema-v3 working file:

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
  --acceptance-scope "All requirements in the supplied tracking plan" `
  --tag-scope analytics_only
```

The initializer applies the mandatory core chain to every planned dataLayer
event, independently of plan tag columns. It does not create a different
workflow for a smaller acceptance boundary. Use
`--tag-scope all_relevant_client_side_tags` only when explicitly requested, or
`--tag-scope explicit_tag_set --explicit-tag "Exact tag name"` for a fixed set.

## Open and checkpoint the browser session

Use `preview_session_ledger.py` to keep stable surfaces, case coverage, action
boundaries, applicable layers, and the classified business-push stream:

```powershell
python -B scripts/preview_session_ledger.py init session.json `
  --profile-path "<approved-browser-context>" `
  --approved-origin https://example.test
```

Register the GTM workspace, Tag Assistant and website. Register every material
interaction case before its first attempt:

```powershell
python -B scripts/preview_session_ledger.py register-case session.json `
  --results working-results.json `
  --case-id CASE-ADD-HEADER-Q1 `
  --event-group-id EVG-007 `
  --url https://example.test/product `
  --element "Add to cart" `
  --placement "product header" `
  --action click `
  --variant quantity=1 `
  --discovered-from tracking_plan
```

The command derives the case's requirement IDs and client container ownership.
Register separate cases for each placement, responsive instance, branch, and
finite material value. Then inventory all detected tags and freeze the
mandatory/conditional applicability card before `begin-action`:

```powershell
python -B scripts/preview_session_ledger.py register-tag session.json `
  --case-id CASE-ADD-HEADER-Q1 `
  --tag-id TAG-GA4-ADD `
  --tag-name "GA4 - add_to_cart" `
  --container-id GTM-XXXX `
  --tag-category analytics `
  --tag-delivery browser_request `
  --vendor-family ga4 `
  --destination-id G-XXXX `
  --template-type "GA4 Event" `
  --consent-required true `
  --evidence-id EVD-TAG-INVENTORY-001

python -B scripts/preview_session_ledger.py complete-tag-inventory session.json `
  --case-id CASE-ADD-HEADER-Q1 `
  --reason "Tag Assistant and container inventory completed" `
  --evidence-id EVD-TAG-INVENTORY-001
```

Repeat `register-tag` for detected excluded tags too. Their scope status and
reason are computed from the run contract. An empty inventory still requires
direct inventory evidence and becomes an explicit failure chain for a planned
dataLayer event.

Before each interaction, open one action. Record and classify every business
push visible after the previous cursor. Settle only after the relevant stream
reaches the quiet boundary and the explicit observed push count matches the
ledger:

```powershell
python -B scripts/preview_session_ledger.py begin-action session.json `
  --action-id ACT-001 `
  --case-id CASE-ADD-HEADER-Q1 `
  --last-event-before 10 `
  --consent-state "analytics_storage=granted" `
  --quiet-window-ms 3000 `
  --timeout-ms 20000

python -B scripts/preview_session_ledger.py record-push session.json `
  --push-id PUSH-011 `
  --action-id ACT-001 `
  --connection-epoch 1 `
  --event-index 11 `
  --event-name add_to_cart `
  --classification expected `
  --classification-reason "Expected after the completed header CTA case" `
  --page-state "Basket count is 1" `
  --evidence-id EVD-RAW-011 `
  --container-id GTM-XXXX

python -B scripts/preview_session_ledger.py import-tag-results `
  session.json action-001-tag-results.json `
  --action-id ACT-001

python -B scripts/preview_session_ledger.py settle-action session.json `
  --action-id ACT-001 `
  --first-event-after 11 `
  --settled-final-event 12 `
  --expected-seen true `
  --preview-connected-after true `
  --interaction-outcome completed `
  --completion-signal "Basket count changed from 0 to 1" `
  --stream-settled true `
  --settlement-reason expected_and_quiet `
  --observed-business-push-count 1

python -B scripts/preview_session_ledger.py record-layer session.json `
  --action-id ACT-001 `
  --layer raw_api_call `
  --status PASS `
  --reason "Exact API Call matched value and type" `
  --evidence-id EVD-RAW-011

python -B scripts/preview_session_ledger.py record-layer session.json `
  --action-id ACT-001 `
  --layer destination_request_when_applicable `
  --status PASS `
  --reason "One decoded request reached the planned destination" `
  --evidence-id EVD-NET-011
```

The imported file contains exactly one row for every in-scope tag and every
tag-related layer. Repeat `record-layer` for every canonical layer on the
frozen card. A mandatory row uses a normal verdict. A conditional row requires
`--predicate-result true|false`; false requires `NOT_APPLICABLE`. Evidence IDs
must refer to direct structured capture tied to the same action and, when
applicable, event index, tag, request, and container. A screenshot is optional
and cannot replace these records.

`connection_epoch` is `1` for the initial Preview connection and increments
when a settled disconnect/reconnect causes event indexes to restart. The
session ledger stores the current epoch explicitly and assigns it to each new
action; `record-push` must match that action epoch. A push identity is the
combination of stream, connection epoch, and event index, so valid index reuse
after reconnect does not hide a true duplicate inside one epoch.

For many captured pushes, use one transactional import instead of repeated CLI
calls:

```powershell
python -B scripts/preview_session_ledger.py import-pushes `
  session.json action-window-pushes.json
```

The file is an array, or `{ "pushes": [...] }`, with the same fields as
`record-push`. A malformed row, duplicate ID, or duplicate stream/epoch/index
rejects the complete import without writing a partial ledger. Only after the
successful durable import may the browser recorder acknowledge those calls.

For one bounded retry, begin a new action with
`--retry-of-action-id <retained-action-id>`. Never reuse an action ID or merge
the failed and repeated windows.

Full-recette initialization already authorizes ordinary fields, privacy
acknowledgements, tested-conversion opt-ins, safe synthetic data, and ordinary
form submission. Do not ask again. Record only additional safe scope once, and
never record any credential:

```powershell
python -B scripts/preview_session_ledger.py authorize session.json `
  --authorization-id AUTH-SAFE-FORMS `
  --scope ordinary_form_submission `
  --environment-class preprod `
  --description "Complete reversible synthetic forms in this run"
```

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
-> detected tag inventory and scope
-> each in-scope tag's GTM variables
-> each tag configuration
-> each firing/non-firing result and count
-> each runtime tag parameter
-> each browser-sending tag's destination request
-> verdict
```

Every canonical layer and in-scope tag/layer pair keeps its own status. A
correct earlier link cannot repair a later mismatch, and a later browser
request cannot repair an earlier payload/configuration failure.

Create an event patch:

```powershell
python -B scripts/incremental_recette.py scaffold-event working-results.json `
  --event-group-id EVG-007 `
  --session-ledger session.json `
  --output event-007-patch.json
```

The shell resets every requirement to `PENDING`, empties evidence, unexpected,
and blocker rows, and places previous case/action/push information under a
supporting-only `capture_context`. Replace that context with current direct
evidence; never apply it as proof.

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
  working-results.json event-007-patch.json `
  --session-ledger session.json
```

The command validates the patched normalized event and its complete session
reconciliation before replacing the working file. Any failure leaves the
existing file byte-for-byte unchanged.

Or validate an already populated event:

```powershell
python -B scripts/incremental_recette.py validate-event `
  working-results.json `
  --event-group-id EVG-007 `
  --session-ledger session.json
```

Do not issue the analyst verdict until the incremental validator passes. Then
return:

```text
Event 07 — add_to_cart: FAIL
- Cases: 4/4 executed
- raw_api_call: PASS; exact payload matched
- GA4 - add_to_cart / Tag firing: PASS, once per action
- GA4 - add_to_cart / Runtime price: FAIL; expected number 29.90, observed string "29.90"
- GA4 - add_to_cart / Browser request: PASS; one request with decoded numeric value 29.9
- Retest: product page, header "Add to cart", quantity=1
```

Continue automatically to the next event.

## Resume and finish

Inspect progress at any time:

```powershell
python -B scripts/incremental_recette.py status working-results.json `
  --session-ledger session.json
python -B scripts/preview_session_ledger.py status session.json
```

After every event is finalized:

```powershell
python -B scripts/incremental_recette.py final-validate working-results.json `
  --session-ledger session.json
python -B scripts/validate_business_rules.py working-results.json
python -B scripts/scan_sensitive_data.py working-results.json
python -B scripts/build_recette_report.py `
  working-results.json gtm-recette-results.xlsx `
  --strict `
  --session-ledger session.json `
  --defects-csv gtm-recette-defects.csv `
  --stakeholder-summary gtm-recette-summary.md
```

Do not complete a run with a `PENDING` case, open action, unclassified or
unaccounted business push, missing canonical or per-tag layer, mismatched normalized
action boundary, failed incremental validation, sensitive raw evidence, or a
workbook that fails reload checks.
