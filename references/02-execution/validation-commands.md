# Validation Commands

Run from the package root. Python 3.11+ and `openpyxl` are required for the
deterministic workbook path.

Install dependencies:

```powershell
python -m pip install -e ".[analysis,dev]"
```

Build and strictly validate the report:

```powershell
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Validate the skill metadata from the auto-discovered source copy when changing
the skill itself:

```powershell
python C:\Users\Guillaume\.codex\skills\.system\skill-creator\scripts\quick_validate.py C:\Users\Guillaume\.codex\skills\gtm-preview-recette
```

The report builder checks structure and evidence references. It cannot prove
that browser observations are truthful; the analyst/agent remains responsible
for evidence accuracy and coverage.
