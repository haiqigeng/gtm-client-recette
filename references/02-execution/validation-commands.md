# Validation Commands

Run from the skill root. Python 3.11+ and `openpyxl` are required.

Validate normalized data without writing a workbook:

```powershell
python -B scripts/build_recette_report.py normalized-results.json --strict --validate-only
```

Build and reload-check the report:

```powershell
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Evaluate declared cross-field rules:

```powershell
python -B scripts/validate_business_rules.py normalized-results.json
```

Scan client-side surfaces with redacted findings:

```powershell
python -B scripts/scan_sensitive_data.py normalized-results.json
```

Compare a supplied previous run:

```powershell
python -B scripts/diff_recette_runs.py previous-results.json normalized-results.json
```

Run unit and negative regression tests:

```powershell
python -m unittest discover -s tests -v
```

Validate skill metadata:

```powershell
python C:\Users\<user>\.codex\skills\.system\skill-creator\scripts\quick_validate.py <skill-path>
```

Inspect a source workbook:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

Decode browser-request captures:

```powershell
python -B scripts/decode_browser_requests.py requests.json decoded-requests.json
```

Inspect the resumable session ledger, including interaction outcome, completion
signal, retry lineage, and settlement reason:

```powershell
python -B scripts/preview_session_ledger.py status session.json
```

Validate one completed event, inspect progress, and validate the final ledger:

```powershell
python -B scripts/incremental_recette.py apply-event working-results.json event-001-patch.json
python -B scripts/incremental_recette.py validate-event working-results.json --event-group-id EVG-001
python -B scripts/incremental_recette.py status working-results.json
python -B scripts/incremental_recette.py final-validate working-results.json
```

For changes to either browser helper, serve the repository locally, open
`tests/fixtures/browser_helpers_smoke.html` in a Playwright browser, and inspect
`window.__gtmRecetteSmokeResult`. The expected result includes one immutable
two-argument push record, numeric `29.9`, an explicit `undefined` marker, and
three discovered controls.

The report validator can prove schema completeness and semantic consistency. It
cannot prove that captured browser evidence is truthful; the agent and analyst
remain responsible for authentic evidence.
