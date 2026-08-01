# Cross-Skill Handoff

Use this only when the analyst supplies output from
`gtm-container-audit-cleanup` or `configure-gtm`. The recette remains a runtime
acceptance test against the tracking plan; it does not absorb an audit or
configuration workflow.

## Supporting-only contract

Register the artifact with:

```powershell
python -B scripts/register_supporting_artifact.py normalized-results.json artifact.json `
  --artifact-id ART-CONFIG-001 `
  --artifact-type gtm_configuration_change_manifest `
  --source-skill configure-gtm `
  --source-run-id CONFIG-001 `
  --source-version 1.0.0
```

The registration stores only contract version, stable identity, source skill,
source run/version, file name, SHA-256 digest, registration time, and optional
notes. It never stores the artifact body in the normalized result.

Every registered row must state:

```json
{
  "role": "supporting_only",
  "verdict_authority": false
}
```

The artifact can help identify concerned tags, variables, destinations,
containers, changed objects, and likely retest cases. It cannot prove runtime
behaviour, replace GTM Preview or browser evidence, close a layer, or determine
PASS/FAIL. If runtime evidence contradicts the supplied artifact, report the
runtime evidence and preserve the artifact hash as context; do not silently
rewrite either source.

Do not create a shared executable `core-utils` dependency across the skills.
Use this small versioned metadata contract so each skill can evolve and remain
installable independently.
