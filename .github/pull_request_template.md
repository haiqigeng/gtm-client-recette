## Change

Describe the analyst-facing behaviour changed.

## Verification

- [ ] Synthetic fixtures only
- [ ] Ruff passes
- [ ] Regression tests pass
- [ ] Strict report validation passes
- [ ] Client-side destination/business/privacy/regression fixtures pass when affected
- [ ] Interaction coverage, continuous business-stream, and gated-journey
      forward cases pass when affected
- [ ] Plan inspection, browser helper, request-decoding, and incremental
      event-validation checks pass when affected
- [ ] Action completion is proved independently, retries retain linked action
      windows, and relevant-stream settlement is recorded when affected
- [ ] Supplemental journal evidence does not substitute for required Tag
      Assistant API Call evidence
- [ ] Applicable evidence derives from requirements; no reduced run type or
      layer-substitution shortcut was introduced
- [ ] Schema-v2 fixtures include current strict client-side and action-safety
      fields, and any legacy upgrade impact is documented
- [ ] Server-side GTM behaviour was not introduced
- [ ] No client data, reports, screenshots, IDs, domains, or credentials

## Release metadata

- [ ] If this changes the release, `pyproject.toml`, `CHANGELOG.md`, `README.md`,
      `SECURITY.md`, CI, and package naming are aligned to the same `v` version.
