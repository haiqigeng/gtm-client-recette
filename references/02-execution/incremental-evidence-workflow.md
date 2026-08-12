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

Before each interaction, capture `before-action.json` from the controlled
browser/Preview/network context and open the action through the operator. The
operator verifies container/workspace/page/readiness and derives both initial
cursors. Record and classify every business push visible after that boundary:

```powershell
python -B scripts/recette_operator.py start-event `
  working-results.json session.json before-action.json `
  --event-group-id EVG-007 `
  --case-id CASE-ADD-HEADER-Q1 `
  --action-id ACT-001 `
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

python -B scripts/preview_session_ledger.py import-layers `
  session.json action-001-layers.json --action-id ACT-001

python -B scripts/recette_operator.py settle-action `
  working-results.json session.json after-action.json `
  --action-id ACT-001 `
  --expected-seen true `
  --interaction-outcome completed `
  --completion-signal "Basket count changed from 0 to 1" `
  --settlement-reason expected_and_quiet
```

`after-action.json` supplies the captured first/final Preview cursor, final
network cursor, settled state, and independently observed business-push count.
Settlement refuses a stale capture, backwards cursor, or count that differs
from classified push rows.

The imported tag file contains exactly one row for every in-scope tag and every
tag-related layer. `action-001-layers.json` is an array, or an object with a
`layer_results` array, containing every canonical layer on the frozen card. A
mandatory row uses a normal verdict. A conditional row requires boolean
`predicate_result`; false requires `NOT_APPLICABLE`. A malformed row rejects
the whole import without writing partial layer evidence. `record-layer`
remains available for an isolated correction. Evidence IDs
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

If the controlled browser, Preview, request capture, or required surface fails
mid-action, retain rather than discard the attempt. Capture
`interrupted_action` with the supported failure reason, last trustworthy
cursors and exact observed-push count, then use operator `interrupt-action`.
The action settles as uncertain and the case becomes `BLOCKED`; unavailable
canonical/tag rows remain unavailable rather than being fabricated. Restore a
clean boundary before a linked retry. The retry must name the retained action;
the blocker remains on that historical attempt while the case reopens as
`PENDING`. Only a Preview disconnect advances `connection_epoch`. Use
`void-runtime-check` only for an unconsumed check that never created an action.

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

Close the event atomically and validate only that completed event:

```powershell
python -B scripts/recette_operator.py close-event `
  working-results.json session.json event-007-patch.json `
  --event-group-id EVG-007
```

The command validates the patched normalized event and its complete session
reconciliation before replacing the working files. It then records the
plan-ordered closure and emits immediate feedback containing event status,
computed primary outcome, anomaly flags, every canonical layer, every in-scope
tag layer, reasons, evidence, and exact retest. Any failure leaves the existing
files byte-for-byte unchanged.

If either file replacement fails or the process stops during replacement, the
operator recovers both prior files from its transaction journal. A
late interaction, variant, or tag uses `reopen-event`; the affected plan suffix
is retained in `closure_history` and reclosed in order after the new case.

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

Pause without discarding state. Resume an open action only after a fresh direct
runtime capture proves the same container, workspace, page, Preview epoch, and
active network capture. Between events, resume without a snapshot; the next
`start-event` establishes its own fresh boundary:

```powershell
python -B scripts/recette_operator.py pause-run session.json `
  --results working-results.json `
  --label "Protected analyst handback"
python -B scripts/recette_operator.py resume-run `
  working-results.json session.json resume-runtime.json
python -B scripts/recette_operator.py resume-run working-results.json session.json
```

Inspect progress at any time:

```powershell
python -B scripts/incremental_recette.py status working-results.json `
  --session-ledger session.json
python -B scripts/preview_session_ledger.py status session.json
python -B scripts/recette_operator.py status working-results.json session.json
```

After every event is finalized:

```powershell
python -B scripts/recette_operator.py finish-run `
  working-results.json session.json gtm-recette-results.xlsx
```

The results, session, and workbook must be distinct paths. The validated XLSX
and FINISHED session state are published together through the same crash-
recoverable transaction contract.

Do not complete a run with a `PENDING` case, open action, unclassified or
unaccounted business push, missing canonical or per-tag layer, mismatched normalized
action boundary, failed incremental validation, sensitive raw evidence, or a
workbook that fails reload checks.
