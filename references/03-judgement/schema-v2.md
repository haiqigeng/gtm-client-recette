# Legacy schema-v2 migration boundary

Schema v2 is readable migration input only. Never create a new v2 run and
never promote a historical v2 verdict or evidence row into current proof.

Use:

```powershell
python scripts/migrate_schema_v2_to_v3.py old-results.json normalized-results.json `
  --legacy-session old-session.json --case-manifest retest-cases.json
```

The migration may retain only discovery support: source coordinates, original
event order, accepted expectations, journey locations, material variants, and
prior case locations. It resets actions, consent state, authorizations,
evidence, anomalies, blockers, component verdicts, and overall verdicts to a
fresh schema-v3 certification boundary.

After migration:

1. declare `run.action_boundary_contract_version: 1` through current
   normalization;
2. recreate a current session ledger with `operator_contract_version: 1`;
3. rediscover the live interactions and concerned tags;
4. recapture every action, runtime check, push, canonical layer, per-tag layer,
   and browser request; and
5. close every event again in original plan order.

See [schema-v3.md](schema-v3.md) for the only current normalized contract.
