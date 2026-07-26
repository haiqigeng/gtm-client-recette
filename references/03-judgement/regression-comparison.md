# Regression Comparison

Regression awareness is conditional on a supplied previous normalized recette
or explicit baseline. It does not authorize repository history mining, GTM
mutation, or a general container audit.

## Requirement comparison

Run:

```powershell
python scripts/diff_recette_runs.py previous-results.json current-results.json
```

Match stable requirement IDs first. The script classifies:

- `UNCHANGED`;
- `IMPROVED`;
- `REGRESSED`;
- `UNVERIFIED`;
- `CHANGED`;
- `NEW`;
- `REMOVED`.

A previous `PASS` that is now a confirmed `FAIL` is `REGRESSED`. A previous
`PASS` that is now `BLOCKED`, `REVIEW`, or `NOT_TESTED` is `UNVERIFIED`, not a
proven implementation regression. Keep the current acceptance verdict and
regression verdict visible separately. New or removed requirements require
source-scope review; do not call them implementation regressions automatically.

Record the baseline source, baseline run ID, baseline/current status, change,
and evidence ID in each matched requirement. Keep removed rows in the diff
artifact and final notes because no current requirement row exists for them.

## Container comparison boundary

When read-only container version or workspace evidence is supplied, record only
changes relevant to an accepted requirement, such as:

- concerned tag mapping changed;
- trigger/exception changed;
- variable mapping changed;
- destination ID changed;
- consent setting changed;
- sequencing changed.

Do not enumerate unrelated container changes, hygiene findings, naming issues,
or cleanup recommendations. If the comparison source is missing, report
requirement regression from runtime evidence only and leave container-cause
claims unestablished.

## Reporting

The workbook `Regression` sheet shows matched requirement changes. `Container
Context` and `Run Context` retain the baseline/current source and relevant
version evidence.

Do not let a regression label hide the actual layer failure. The event feedback
must still say what currently failed and why.
