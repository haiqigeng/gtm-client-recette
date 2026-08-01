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

## Failure-focused retest preparation

Build a manifest from current `FAIL`, `BLOCKED`, and `REVIEW` events:

```powershell
python -B scripts/build_retest_manifest.py `
  normalized-results.json session.json retest-manifest.json
```

Import its cases into a newly initialized session:

```powershell
python -B scripts/preview_session_ledger.py import-cases new-session.json `
  retest-manifest.json --results new-results.json
```

This caches only interaction discovery, URL, placement, action, and material
variant. Every case begins `PENDING`; no prior evidence, verdict,
authorization, consent simulation, or PASS is inherited. Revalidate the
tracking-plan scope and current container/context before execution.

If a non-PASS event has no reusable URL, action, or element, the manifest puts
it in `limitations` rather than silently omitting it or inventing a case.
Resolve every listed limitation before `import-cases` accepts the manifest.
