# Workbook Architecture

Generate schema-v3 reports with:

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
6. `Layer Verdicts`
7. `Event Evidence`
8. `Observed Push Stream`
9. `Tag Evidence`
10. `Destination Evidence`
11. `Trigger & Sequence`
12. `Consent`
13. `Business Rules`
14. `Sensitive Data`
15. `Client Checks`
16. `Regression`
17. `Container Context`
18. `Unexpected Events-Tags`
19. `Blockers`
20. `Evidence Catalogue`
21. `Run Context`

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
material variant, tag scope and inventory, immutable applicability card,
completion signal, push count, retry lineage, and layer results. `Observed Push
Stream` lists every chronological
business push, action/case mapping, page/state, classification/reason,
container, connection epoch, and exact API Call evidence.

`Layer Verdicts` is the omission-control surface. It contains one row per
event/case/canonical layer plus one subrow per in-scope tag and tag-related
layer. Each row has status, reason, predicate result, evidence, blocker, and
retest. Detected out-of-scope tags remain visible with their scope reason. The
event roll-up is the worst layer status.

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
The same literal-text rule applies to defect CSV sidecars, which prefix unsafe
leading characters before spreadsheet import.

`Destination Evidence` shows the claimed destination ID and vendor event name,
their declared raw request paths, the expected and actual tested-parameter
paths, decoded value/type, request behaviour/count, endpoint, and evidence.
This lets an analyst trace each plan value back to the captured browser send.

`Evidence Catalogue` keeps canonical evidence kind/source/capture mode and
structured action/event/container/request/tag-ID linkage separate from optional
`source_detail`, then path/URL, timezone-qualified capture time, and redacted
description.

Keep all 21 sheets even when an optional domain has zero rows. The empty,
filtered sheet makes non-applicability visible and prevents a missing worksheet
from hiding an omitted layer.

The builder reloads the XLSX and verifies required sheets, order, row counts,
filters, links, and formatting. Do not declare completion when strict validation
or reload checks fail. Structured text longer than Excel's 32,767-character
cell limit is split into explicit `[part i/n]` continuation rows before save;
physical row counts are recomputed and silent truncation is rejected.

Generate optional shareable sidecars from the same validated source:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict --session-ledger session.json `
  --defects-csv defects.csv --defects-md defects.md `
  --stakeholder-summary summary.md
```

The stakeholder summary reports scope, event totals, and non-PASS actions. It
does not invent a GO/NO-GO decision or hide technical evidence.
Workbook, sidecar, normalized-result, and session paths must be distinct; the
CLI refuses aliases that could overwrite an input. Guided finalization
publishes the validated workbook and FINISHED session state together through
a crash-recoverable paired transaction.
