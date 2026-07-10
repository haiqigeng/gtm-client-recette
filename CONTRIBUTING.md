# Contributing

Use synthetic fixtures only. Never commit client tracking plans, domains,
container IDs, screenshots, reports, credentials, emails, or browser traces.

Before opening a pull request, run:

```powershell
python -m pip install -e ".[analysis,dev]"
python -m ruff check --no-cache .
python -m unittest discover -s tests -v
python -B scripts/check_release.py --tag v2026.7.11
```

Changes to verdict logic require a regression fixture that fails before the
change and passes after it. Keep the skill limited to recette execution; do not
add GTM audit, implementation, debugging, or publishing behaviour.
