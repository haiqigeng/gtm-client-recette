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
6. `Consent`
7. `Unexpected Events-Tags`
8. `Blockers`
9. `Evidence Catalogue`
10. `Run Context`

`Client Summary` includes the complete event list in original plan order,
status, requirement count, concise reason, and evidence IDs.

`Requirement Matrix` is the atomic technical deliverable. Show source
expectation, raw value/state/type, resolved value/state/type, GTM variable,
concerned tag configuration, firing status, runtime value/type, applicable
consent, occurrence evidence, component verdicts, overall verdict, mismatch,
and evidence side by side.

`Journey Coverage` lists supplied or inferred actions, attempted routes,
execution status, blockers, and evidence in source order.

Keep raw payload, resolved snapshot, tag configuration, runtime value, and
consent evidence distinct on their dedicated sheets. Serialize objects and
arrays for display only; retain structured values in normalized JSON.

The builder reloads the XLSX and verifies required sheets, order, row counts,
filters, links, and formatting. Do not declare completion when strict validation
or reload checks fail.
