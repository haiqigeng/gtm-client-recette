# Validation Commands

Run from the skill root. Python 3.11+ and `openpyxl` are required.

Validate normalized data without writing a workbook:

```powershell
python -B scripts/build_recette_report.py normalized-results.json `
  --strict `
  --validate-only `
  --session-ledger session.json
```

Build and reload-check the report:

```powershell
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx `
  --strict `
  --session-ledger session.json
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
python -X utf8 C:\Users\<user>\.codex\skills\.system\skill-creator\scripts\quick_validate.py <skill-path>
```

Inspect a source workbook:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

Decode browser-request captures:

```powershell
python -B scripts/decode_browser_requests.py requests.json decoded-requests.json
```

Inspect and validate the resumable session ledger, including case census,
interaction outcome, completion signal, retry lineage, classified push count,
applicable layers, and settlement reason:

```powershell
python -B scripts/preview_session_ledger.py status session.json
python -B scripts/preview_session_ledger.py validate session.json `
  --results normalized-results.json `
  --final
```

Validate one completed event, inspect progress, and validate the final ledger:

```powershell
python -B scripts/incremental_recette.py apply-event `
  working-results.json event-001-patch.json `
  --session-ledger session.json
python -B scripts/incremental_recette.py validate-event `
  working-results.json `
  --event-group-id EVG-001 `
  --session-ledger session.json
python -B scripts/incremental_recette.py status working-results.json `
  --session-ledger session.json
python -B scripts/incremental_recette.py final-validate working-results.json `
  --session-ledger session.json
```

For changes to either browser helper, install the optional browser-test
dependency and Chromium, then run the real-browser regression:

```powershell
python -m pip install -e ".[browser-test]"
python -m playwright install chromium
python -B tests/run_browser_helpers.py
```

It checks the smoke fixture plus hostile snapshot objects and array elements,
shared references versus cycles, snapshot budgets, reassignment, wrapper
chains, duplicate installation, honest detachment reporting, custom data
layers, strict-CSP census loading, unique structural selectors, inherited
visibility, accessible-name precedence, and open shadow roots.

Strict final validation cross-checks normalized action boundaries against the
session ledger, case/layer completion, classified push counts, and direct
evidence linkage. It cannot independently prove that a captured browser
artifact is truthful; the agent and analyst remain responsible for authentic
capture.
