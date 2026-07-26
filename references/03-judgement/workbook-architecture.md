# Workbook Architecture

Generate schema-v2 reports with:

```powershell
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

The workbook contains, in order:

1. `Client Summary`
2. `Requirement Matrix`
3. `Journey Coverage`
4. `Event Evidence`
5. `Tag Evidence`
6. `Destination Evidence`
7. `Trigger & Sequence`
8. `Consent`
9. `Business Rules`
10. `Sensitive Data`
11. `Client Checks`
12. `Regression`
13. `Container Context`
14. `Unexpected Events-Tags`
15. `Blockers`
16. `Evidence Catalogue`
17. `Run Context`

`Client Summary` includes the complete event list in original plan order,
status, requirement count, concise reason, and evidence IDs.

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

`Event Evidence` keeps action and retry IDs, independent interaction outcome
and completion signal, adaptive quiet/timeout values, stream-settlement reason,
event indexes, raw API Call, and resolved Data Layer evidence together without
collapsing their verdicts.

Keep raw payload, resolved snapshot, tag configuration, runtime value,
destination request, trigger/sequence, consent, business-rule, redacted
sensitive-data, client-check, regression, and container evidence distinct on
their dedicated sheets. Serialize objects and arrays for display only; retain
structured values in normalized JSON.

`Destination Evidence` shows the claimed destination ID and vendor event name,
their declared raw request paths, the expected and actual tested-parameter
paths, decoded value/type, request behaviour/count, endpoint, and evidence.
This lets an analyst trace each plan value back to the captured browser send.

`Evidence Catalogue` keeps canonical evidence kind/source separate from
optional `source_detail`, then path/URL, timezone-qualified capture time, and
redacted description.

Keep all 17 sheets even when an optional domain has zero rows. The empty,
filtered sheet makes non-applicability visible and prevents a missing worksheet
from hiding an omitted layer.

The builder reloads the XLSX and verifies required sheets, order, row counts,
filters, links, and formatting. Do not declare completion when strict validation
or reload checks fail.
