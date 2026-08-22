# Operator and output contract

## Resolve the skill root

Resolve `<skill-root>` as the directory containing `SKILL.md`; never assume the
current working directory. Run scripts with:

```powershell
python -B "<skill-root>\scripts\script_name.py" ...
```

## New-run sequence

1. Inspect/import the acceptance source and initialize normalized results.
2. Initialize the session with `preview_session_ledger.py init` and explicitly
   use `--operator-contract-version 2`, `--run-id` copied exactly from
   normalized `run.run_id`, the current browser instance ID, browser context
   ID, profile, and approved origins.
3. Register existing GTM, Tag Assistant, and site surfaces.
4. Discover scenario classes, register cases with one `--dimension-value
   DIMENSION_ID=JSON_VALUE` for every material dimension, and
   `import-coverage`. Every final class records all four adaptive
   `trigger_reviews`, including explicit not-triggered reviews.
5. Inventory tags and `complete-tag-inventory` for each case.
6. Capture a v2 before snapshot and use `recette_operator.py start-event`.
7. Execute one exact website action, then record every business push and all
   canonical/per-tag rows.
8. Capture the after snapshot and use operator `settle-action`.
9. Import same-run stream segments, journey/semantic checks, protected
   handoffs, and gated-flow records as applicable. Every v2 sidecar carries the
   same `run_id`, and every referenced evidence ID resolves to the current
   normalized evidence catalog and action/case binding.
10. Apply the event result patch with operator `close-event`; it emits immediate
    per-event feedback and stores the frozen coverage revision.
11. Repeat in plan order. Close the stream, verify every evidence file, and
    use operator `finish-run`.

Use `--help` for exact command fields. Batch imports are transactional: one
malformed row rejects the batch.

## Immediate feedback

After each event, output event and case status, every canonical layer with a
simple reason, per-tag layers, technical delivery, page/journey, business
semantics, continuous-stream anomaly status, scenario coverage, affected cases,
evidence IDs, and an exact retest instruction for non-PASS cases.

## Final conclusion

Return every event in original plan order with status, human label (`OK`/`KO`),
layers inspected and their statuses, and a concise why. Then produce the
validated XLSX. Operator-v2 workbooks add coverage decisions/classes, semantic
checks, journey state, stream segments, handoffs, gated flows, and a final
conclusion to the legacy detailed sheets.

`finish-run` refuses open actions, pending cases, unclosed events, gaps in the
dataLayer review, stale coverage revisions, wrong browser/container identity,
missing semantic anchors, unresolved handoffs, any unverified evidence,
or normalized/session disagreement.

## Resume, reopen, and migration

Resume only from persisted results/session state and a fresh runtime snapshot.
If coverage, a material case, or a tag changes after closure, reopen that event;
the affected closure suffix becomes historical and must be reclosed in order.

Schema-v2 and operator-v1 artifacts remain readable for regression. Their
legacy workbook remains output contract 2; operator-v2 uses output contract 3.
New guided runs require normalized `operator_contract_version_required: 2`;
never fabricate missing browser, stream, semantic, or evidence-integrity
records during migration.
