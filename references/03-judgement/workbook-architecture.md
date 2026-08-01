# Workbook Architecture

Generate schema-v2 reports with:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict `
  --session-ledger session.json
```

The workbook contains, in order:

1. `Client Summary`
2. `Defect Register`
3. `Requirement Matrix`
4. `Journey Coverage`
5. `Interaction Cases`
6. `Event Evidence`
7. `Observed Push Stream`
8. `Tag Evidence`
9. `Destination Evidence`
10. `Trigger & Sequence`
11. `Consent`
12. `Business Rules`
13. `Sensitive Data`
14. `Client Checks`
15. `Regression`
16. `Container Context`
17. `Unexpected Events-Tags`
18. `Blockers`
19. `Evidence Catalogue`
20. `Run Context`

`Client Summary` includes the complete event list in original plan order,
status, requirement and case counts, verified layer statuses, concise reason,
exact non-PASS retest interaction, and evidence IDs.

`Defect Register` contains one concise actionable row per non-PASS requirement
and unexpected occurrence: event order, case/placement/variant, failed layer,
expected and observed value/type, precise reason, evidence IDs, and exact
retest. It is the handoff table for developers and analysts; it does not hide
the detailed evidence sheets.

`Requirement Matrix` is the atomic technical deliverable. Show source
expectation, raw value/state/type, resolved value/state/type, GTM variable,
concerned tag configuration, firing status, runtime value/type, applicable
destination request, trigger/sequence, consent, business/privacy/client/regression
components, occurrence evidence, overall verdict, mismatch, and evidence side
by side.

`Journey Coverage` lists supplied or inferred actions, attempted routes,
safe action value/type/source, execution status, blockers, and evidence in
source order. Protected analyst input is represented only by its canonical
redacted marker.

`Interaction Cases` lists every case and retained attempt with placement,
material variant, applicable layers, completion signal, push count, retry
lineage, and layer results. `Observed Push Stream` lists every chronological
business push, action/case mapping, page/state, classification/reason,
container, connection epoch, and exact API Call evidence.

`Event Evidence` keeps action and retry IDs, independent interaction outcome
and completion signal, adaptive quiet/timeout values, stream-settlement reason,
event indexes, raw API Call, and resolved Data Layer evidence together without
collapsing their verdicts.

Keep raw payload, resolved snapshot, tag configuration, runtime value,
destination request, trigger/sequence, consent, business-rule, redacted
sensitive-data, client-check, regression, and container evidence distinct on
their dedicated sheets. Serialize objects and arrays for display only; retain
structured values in normalized JSON.

`Business Rules` exposes the deterministic evaluation source. Every exported
string is written as a literal cell value, including text beginning with `=`,
`+`, `-`, or `@`; evidence can never become an executable spreadsheet formula.

`Destination Evidence` shows the claimed destination ID and vendor event name,
their declared raw request paths, the expected and actual tested-parameter
paths, decoded value/type, request behaviour/count, endpoint, and evidence.
This lets an analyst trace each plan value back to the captured browser send.

`Evidence Catalogue` keeps canonical evidence kind/source/capture mode and
structured action/event/container/request/tag linkage separate from optional
`source_detail`, then path/URL, timezone-qualified capture time, and redacted
description.

Keep all 20 sheets even when an optional domain has zero rows. The empty,
filtered sheet makes non-applicability visible and prevents a missing worksheet
from hiding an omitted layer.

The builder reloads the XLSX and verifies required sheets, order, row counts,
filters, links, and formatting. Do not declare completion when strict validation
or reload checks fail.

Generate optional shareable sidecars from the same validated source:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict --session-ledger session.json `
  --defects-csv defects.csv --defects-md defects.md `
  --stakeholder-summary summary.md
```

The stakeholder summary reports scope, event totals, and non-PASS actions. It
does not invent a GO/NO-GO decision or hide technical evidence.
