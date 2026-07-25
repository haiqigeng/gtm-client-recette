# Contributing

Use synthetic fixtures only. Never commit client tracking plans, domains,
container IDs, screenshots, reports, credentials, emails, or browser traces.

## Versioning

Use semantic `v` versioning, never calendar-date versioning:

- Store `MAJOR.MINOR.PATCH` in `pyproject.toml`, for example `1.0.0`.
- Prefix Git tags and release archives with `v`, for example `v1.0.0` and
  `gtm-preview-recette-v1.0.0.zip`.
- Increment PATCH for compatible fixes, MINOR for compatible functionality,
  and MAJOR for incompatible changes.

Before opening a pull request, run:

```powershell
python -m pip install -e ".[dev]"
python -m ruff check --no-cache .
python -m unittest discover -s tests -v
python -B scripts/check_release.py --tag v1.0.0
```

Changes to verdict logic require a regression fixture that fails before the
change and passes after it. Keep the skill limited to recette execution; do not
add GTM audit, implementation, debugging, or publishing behaviour.
