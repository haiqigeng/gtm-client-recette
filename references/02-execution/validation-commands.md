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

The report validator can prove schema completeness and semantic consistency. It
cannot prove that captured browser evidence is truthful; the agent and analyst
remain responsible for authentic evidence.
