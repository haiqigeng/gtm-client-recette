# GTM Client Recette

[![Latest release](https://img.shields.io/github/v/release/haiqigeng/gtm-client-recette?sort=semver)](https://github.com/haiqigeng/gtm-client-recette/releases/latest)
[![CI](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml/badge.svg)](https://github.com/haiqigeng/gtm-client-recette/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Repository version: **v8.0.0**.

This is a personal expert skill for client-side GTM acceptance testing. It takes one
structured XLSX tracking plan, opens one standalone headed Playwright MCP browser, reuses
the prepared GTM Preview and website tabs, and produces immediate five-layer feedback
plus one final XLSX.

The north star is trustworthy findings per browser interaction. Technical consistency is
not enough: tracking fails when it contradicts the page, selected control, action, cart,
form, or visible outcome.

## One fixed path

- Input: exactly one `.xlsx` tracking plan.
- Browser: exactly one standalone headed Playwright MCP window opened by the agent.
- Output: immediate feedback after every scenario and one
  `gtm-client-recette-results.xlsx` after complete coverage.
- Runtime commands: `start`, `next`, `complete`, and `finish` only.
- No alternate input, browser, execution mode, feature flag, retry, repair, reopen,
  fallback, or backup path.

The intake asks for the XLSX, known protected prerequisites, and readiness. After the
user says `ready`, the agent opens Playwright at `about:blank` immediately. The user then
prepares GTM Preview, the target site, login, and ordinary consent in that window while
the XLSX compiles. Ordinary synthetic interactions and forms are authorized by default;
the user handles credentials, MFA, CAPTCHA, verification, and real payment.

## Five mandatory layers

Every tested scenario reports these rows in this order:

1. **Page/action reality** — reachable non-404 page, intended state, performed action,
   selected values, and visible outcome.
2. **Data Layer API Call** — exact expanded API Call from the selected Tag Assistant
   event, occurrence count, planned fields, types, and values.
3. **GTM Tags** — concerned tag mapping, firing count, Names configuration, and
   event-time Values runtime data, including a causal Trigger Group.
4. **Browser request** — action-bounded concerned request, normalized planned values,
   transport result, duplicates, and retries.
5. **Surrounding behavior** — continuous post-cursor chronology for missing, duplicate,
   premature, delayed, stale, or interjected business events.

Every planned field is checked independently at API Call, GTM mapping/runtime, and
browser request against both the plan rule and visible interaction context. Cross-layer
equality is supporting evidence only. If the UI adds quantity `1` while all technical
surfaces say `2`, all three technical layers fail.

The accumulated Tag Assistant Data Layer tab, GTM Variables tab, consent panels, and a
direct dataLayer recorder are not inspected. Missing mandatory evidence becomes an
explained `BLOCKED` result; it is never replaced by weaker evidence.

## Scenario coverage and anomalies

Scenario selection happens just in time for every event:

- test every reachable finite material value, including language, login state, shipping,
  payment, and cart state;
- treat a live plan-omitted value as a visible plan gap and test it when it can change
  behavior or the verdict;
- for high-cardinality products or content, test one representative per materially
  different behavior signature plus boundaries and exceptions;
- preserve every business API Call between interactions and explain any unexpected
  event before moving on.

One blocked event does not stop the run. A real tracking failure never stops it. The run
stops only after two consecutive events have all five layers `BLOCKED` and no
attributable evidence; the second feedback is still emitted and no final XLSX is made.

## Runtime

```powershell
python -B scripts/recette.py start tracking-plan.xlsx C:\path\to\new-run
python -B scripts/recette.py next C:\path\to\new-run 13
# Perform exactly one action and save the one-call Playwright evidence bundle.
python -B scripts/recette.py complete C:\path\to\new-run C:\path\to\new-run\evidence-A-0001.json
python -B scripts/recette.py finish C:\path\to\new-run
```

The one-time Tag Assistant observer is
[`scripts/playwright_collector.js`](scripts/playwright_collector.js). It has a fixed
five-second extraction bound and never reloads, retries, switches browser, or reads the
Data Layer/Variables tabs. Its bootstrap returns the current cursor and current-document
boundary. Use the document boundary for the first Core action and the current cursor for
any other first action; every later `next` must use the preceding completion cursor.

The final workbook contains only three analyst-facing sheets: a plan-ordered conclusion,
five-layer event feedback, and exact checks with expected/observed values and targeted
next inspection.

## Development verification

```powershell
python -m pip install -e ".[dev,browser-test]"
python -m ruff check scripts tests
python -m ruff format --check scripts tests
python -m unittest discover -s tests -v
python -B tests/run_browser_collector.py
python -m vulture scripts tests --min-confidence 80
python -B scripts/check_release.py --tag v8.0.0
python -B scripts/build_skill_package.py --output dist/gtm-client-recette-v8.0.0.zip
python -B scripts/verify_release_artifact.py dist/gtm-client-recette-v8.0.0.zip
```

See [v8 design and verification](docs/v8-design-and-verification.md).

## Boundaries

The skill does not design tracking plans, mutate or publish GTM, modify the website,
certify server-side/vendor receipt, bypass protected controls, or make legal consent
conclusions.
