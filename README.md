# GTM Preview Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-preview-recette?sort=semver)](https://github.com/haiqigeng/gtm-preview-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-preview-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Current release

[v1.0.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.0.0) is
the current supported release. Download the validated package:
[gtm-preview-recette-v1.0.0.zip](https://github.com/haiqigeng/gtm-preview-recette/releases/download/v1.0.0/gtm-preview-recette-v1.0.0.zip).

An expert-only workflow for testing an existing Google Tag Manager implementation
against a client tracking plan. It coordinates Playwright, GTM Preview, Tag
Assistant, website journeys, consent scenarios, event-level evidence, and a
detailed XLSX result workbook.

## Who It Serves

- Web analysts, analytics consultants, GTM specialists, and agencies.
- Expert QA teams that already understand dataLayer, GTM variables, triggers,
  tags, consent, and Tag Assistant.
- Codex and other Markdown-capable agents that can operate a Playwright browser.

It is intentionally not a beginner marketing-team guide.

## How It Works

The workflow is organized into three layers:

1. **Orientation**: establish scope, interpret the client's bespoke tracking plan,
   define journeys, and confirm expectations.
2. **Execution**: open the dedicated browser, connect GTM Preview, reproduce
   journeys, inspect every event, and capture evidence.
3. **Judgement**: compare raw API-call payloads, resolved Data Layer state,
   variables, tag values, tag firing, non-firing reasons, and consent against the
   confirmed specification.

Every run begins with a concise responsibility-labelled preflight, waits for
`READY`, and then pauses only at protected checkpoints.

## Inputs And Outputs

Inputs may be an XLSX, CSV, sheet export, document, screenshot, mock-up, or
analyst explanation. The skill recognizes the client's structure and maps it to
an internal test matrix without forcing a new template.

The required output is a concise XLSX validation matrix. Each row shows the
tracking-plan value, raw or resolved dataLayer value, GTM/tag configuration,
runtime value, verdict, exact mismatch, and evidence.

## Boundaries

The workflow tests behaviour only. It does not create a tracking plan, audit or
clean a GTM container, debug or fix implementation, change the website, publish
GTM, or make legal/privacy decisions.

## Run

Install the small deterministic dependency set:

```powershell
python -m pip install -e ".[dev]"
```

Build a workbook from normalized evidence:

```powershell
python -B scripts/build_recette_report.py normalized-results.json gtm-recette-results.xlsx --strict
```

Run regression tests:

```powershell
python -m unittest discover -s tests -v
```

The full agent workflow starts in `SKILL.md`. The reference map is:

- `references/01-orientation/`: purpose, users, inputs, outputs, acceptance, and non-goals.
- `references/02-execution/`: interaction, browser readiness, consent, test data, and QA commands.
- `references/03-judgement/`: comparison, evidence, matching, verdict, workbook, and completion rules.
- `scripts/`: deterministic XLSX report generation.
- `tests/`: regression coverage for strict evidence and report output.

Do not store client exports, screenshots, container IDs, domains, emails,
credentials, or generated reports in a release bundle.
