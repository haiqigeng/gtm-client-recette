# v8 fixed personal design and verification

## Decision

v8 is a clean major redesign, not a patch to a client run. It deliberately removes
general-product flexibility and keeps one personal path: one XLSX, one standalone headed
Playwright MCP window, one prepared Tag Assistant tab, one target tab, one interaction
per observation, five fixed evidence layers, immediate feedback, and one final XLSX.

## Implemented architecture

The runtime consists of six files:

- `xlsx_plan.py` compiles semantic event-detail sheets directly and treats workbook
  indexes as non-authoritative navigation metadata.
- `playwright_collector.js` installs once in Tag Assistant and collects only post-cursor
  API Call and Tags/Names/Values evidence within five seconds.
- `judge.py` applies tracking-plan, visible-reality, type, occurrence, mapping, runtime,
  request, and chronology checks without letting cross-layer consistency override
  reality.
- `state.py` owns the append-only four-command lifecycle, just-in-time scenario coverage,
  and the two-consecutive-zero-evidence stop rule.
- `recette.py` exposes only `start`, `next`, `complete`, and `finish`, and emits the
  five-layer feedback block on every completion.
- `report.py` renders and reopens one three-sheet final workbook.

No runtime module supports another input, browser provider, mode, feature flag, retry,
repair, reopen, recorder, accumulated Data Layer state, GTM Variables, consent engine,
or run migration.

## Quality retained or strengthened

| Risk | v8 control |
|---|---|
| Coherently wrong tracking | Every technical layer is also compared with visible action values. |
| One tag variable for many planned fields | Mapping and runtime are checked independently for every planned field. |
| Dead URL with valid tracking | Page/action reality fails the event. |
| Duplicate or unexpected events | Every post-cursor business API Call remains in the surrounding chronology. |
| Delayed Trigger Group firing | Causal technical rows after the selected API Call are included until the next business event. |
| Missing plan values | Live valid omitted values produce an explicit plan-gap review and material scenario. |
| Unlimited products/content | Representatives are selected by materially different behavior signature, boundaries, and exceptions. |
| One unavailable evidence layer | That layer blocks; other attributable layers still report and the run continues. |
| Completely unusable session | Only two consecutive all-five-blocked/no-evidence events stop the run. |
| Agent skips feedback | `complete` deterministically returns the five rows before `next` can open another action. |

## Speed controls

- XLSX compilation and browser preparation happen concurrently after `ready`.
- Core observes the already prepared attributable document; there is no setup or cleanup
  reload.
- The Tag Assistant helper is installed once and retains one continuous cursor.
- A scenario uses one bounded Playwright call rather than repeated panel handshakes.
- Preview extraction is capped at five seconds and returns honest partial evidence.
- Scenario selection happens only when its event becomes current; no whole-run browser
  precomputation is performed.
- Evidence stores only selected API payloads, concerned tag detail, action-bounded
  requests, reality anchors, and post-cursor chronology—not full DOM or Preview dumps.

## Regression and downgrade assessment

Compared with v7/v6, v8 removes flexibility and recovery behavior intentionally. This is
not a downgrade for the personal contract because those paths were never wanted and were
the main source of delayed inspection and agent divergence. Compared with the responsive
v3 workflow, v8 restores a direct action-to-inspection sequence while retaining stronger
reality, variable-completeness, request, scenario, and anomaly checks.

The regression suite proves:

- direct XLSX compilation, including a large synthetic multi-sheet plan;
- fixed-value and dynamic-value semantics, custom wrapper selectors, and exclusion of
  code/image sections;
- five-layer pass, dead-page failure, reality-versus-chain contradiction, missing tag
  mappings, stale chronology, duplicates, interjected events, and live plan gaps;
- finite scenario completion, invalid-state rejection, one-blocked continuation,
  two-blocked stopping, and no final workbook after that stop;
- exactly five feedback rows per scenario and a plan-complete final conclusion;
- actual Chromium execution of the Tag Assistant helper against a synthetic DOM,
  including API Call parsing, Names/Values extraction, and reinstall rejection.

## Technical health results

| Release | Runtime files | Runtime lines | Skill lines |
|---|---:|---:|---:|
| v3.0.0 | 29 | 17,094 | 408 |
| v3.1.0 | 38 | 22,787 | 266 |
| v7.0.0 | 26 | 15,338 | 179 |
| v8.0.0 | 6 | 2,747 | under 180 |

The v8 runtime is more than 82% smaller than v7 and more than 83% smaller than v3.0.
Ruff and formatting checks pass. Vulture reports no unused code at 80% confidence.
Radon reports no E/F-complexity function after the parser and field-judge refactor. The
unit suite has 37 tests, the collector passes a real Chromium DOM execution, and a full
synthetic 24-event/192-field lifecycle including workbook rendering stays below ten
seconds. A real multi-sheet XLSX also compiles directly in under three seconds without a
normalization pre-run. The packaged archive is byte-for-byte deterministic across
successive builds and validates after a clean extraction.

## Honest residual boundary

The browser fixture validates the collector code but is not a live client Preview run.
If Google changes Tag Assistant's accessible DOM, the affected API Call or Tags layer
will become `BLOCKED` within five seconds. v8 intentionally has no weaker fallback; the
collector must be corrected and a new run started. Protected credentials, CAPTCHA, MFA,
verification, real payment, and ordinary consent remain explicit user actions in the
same Playwright window.
