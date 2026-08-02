# Operator command reference

Use these commands only at the stage routed from `SKILL.md`. They implement the
single full-recette workflow; they are not alternate recette modes.

## Normalize

For a reviewed/approved `ga4-tracking-plan` delivery:

```powershell
python scripts/import_ga4_tracking_plan_handoff.py DELIVERY -o interpreted-requirements.json
```

For a workbook:

```powershell
python scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

Initialize schema v3:

```powershell
python scripts/init_coverage_ledger.py interpreted-requirements.json normalized-results.json `
  --run-id RUN-001 --title "GTM recette" `
  --site-url https://example.test/ --environment Preprod `
  --environment-class preprod --container-id GTM-XXXX --workspace Recette `
  --tracking-plan-source tracking-plan.xlsx `
  --acceptance-scope "Confirmed tracking-plan requirements" `
  --tag-scope analytics_only
```

Migrate v2 discovery context without proof inheritance:

```powershell
python scripts/migrate_schema_v2_to_v3.py old-results.json normalized-results.json `
  --legacy-session old-session.json --case-manifest retest-cases.json
```

## Session and evidence

Initialize and register the controlled surfaces:

```powershell
python scripts/preview_session_ledger.py init session.json `
  --profile-path <controlled-profile> --approved-origin https://example.test
```

The ordered session verbs are:

1. `register-surface`
2. `register-case`
3. `register-tag` for every detected tag
4. `complete-tag-inventory`
5. `begin-action`
6. `record-push` or transactional `import-pushes`
7. `scaffold-tag-results`, complete its exact rows, then `import-tag-results`
8. `record-layer` once for each canonical layer
9. `settle-action`
10. `checkpoint`, `validate`, or `status`

If a material tag appears after the inventory was frozen, first settle the
current action, then version the inventory and force a retained retry:

```powershell
python scripts/preview_session_ledger.py revise-tag-inventory session.json `
  --case-id CASE-001 --tag-id TAG-NEW --tag-name "GA4 - Event" `
  --container-id GTM-XXXX --tag-category analytics `
  --tag-delivery browser_request --vendor-family ga4 `
  --template-type "GA4 Event" --consent-required false `
  --evidence-id EVD-TAG-NEW --reason "Late tag appeared in direct Preview inventory"
```

Install the recorder before navigation and decode safe request records:

```javascript
await context.addInitScript({ path: "scripts/datalayer_recorder.js" })
```

```powershell
python scripts/decode_browser_requests.py requests.json decoded-requests.json
```

## Incremental event delivery

```powershell
python scripts/incremental_recette.py scaffold-event normalized-results.json `
  --event-group-id EVG-001 --session-ledger session.json `
  --output event-001-patch.json
python scripts/incremental_recette.py apply-event normalized-results.json event-001-patch.json `
  --session-ledger session.json
python scripts/incremental_recette.py validate-event normalized-results.json `
  --event-group-id EVG-001 --session-ledger session.json
```

Scaffolds preserve discovery only. They never inherit verdicts or evidence.

## Final validation and workbook

```powershell
python scripts/incremental_recette.py final-validate normalized-results.json `
  --session-ledger session.json
python scripts/validate_business_rules.py normalized-results.json
python scripts/scan_sensitive_data.py normalized-results.json
python scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict --session-ledger session.json `
  --defects-csv gtm-recette-defects.csv `
  --defects-md gtm-recette-defects.md `
  --stakeholder-summary gtm-recette-summary.md
```

## Release provenance

Release archives carry `RELEASE-MANIFEST.json` with the exact source file set,
per-file SHA-256 hashes, and an aggregate tree hash:

```powershell
python scripts/build_skill_package.py --output dist/gtm-preview-recette-vX.Y.Z.zip
python scripts/verify_release_artifact.py dist/gtm-preview-recette-vX.Y.Z.zip
```
