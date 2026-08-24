# v7 Technical Review

Status: release candidate review, 2026-08-25.

## Verdict

v7 is technically fit for this personal expert skill. The architecture is intentionally
deep in deterministic analytics judgement and narrow in browser choreography. It adds
no database, service, worker, dashboard, browser-family abstraction, commercial
configuration system, or run-specific branch.

## Runtime architecture

1. `plan.py` normalizes accepted inputs once into immutable typed claims.
2. `workflow.py` freezes setup/action scope and exposes the `next -> complete` loop.
3. `tag_assistant_collector.js` performs one direct, dependency-free Preview read.
4. `capture.py` validates, minimizes, and redacts supplied evidence.
5. `correlate.py` builds the causal action/source/tag/request occurrence model.
6. `judge.py` derives field, layer, anomaly, confidence, safety, and coverage verdicts.
7. `report.py` owns immediate five-layer feedback and final JSON/Markdown/XLSX.
8. `state.py` keeps the immutable plan and append-only evidence/verdict stream.

The public CLI remains eight commands, with only `next` and `complete` repeated during
browser execution. Low-level capture/correlation functions are implementation seams, not
alternate agent workflows.

## Necessity review

| Component | Decision | Reason |
| --- | --- | --- |
| Headed Playwright-managed Edge | Keep | Standardizes the browser/Preview context and avoids extension/existing-window ambiguity |
| Early blank browser plus parallel plan compilation | Keep | Uses user preparation time without adding a synchronization system |
| One setup cursor | Keep | Excludes historical Preview rows and prevents setup loads becoming Core evidence |
| Frozen action ID/mode/document policy | Keep | Prevents accidental duplicate interactions and mixed-action evidence |
| Paste-ready completion callback | Keep | Removes imports, local-file reads, and handwritten normalization from agent execution |
| Five-second collector bound | Keep | Fast-fails external UI problems while preserving partial evidence |
| Exact API Call parser | Keep | Required to distinguish a push from accumulated GTM state and compare exact values |
| Planned plus causal technical Tags rows | Keep | Covers Trigger Group delivery without scanning unrelated lifecycle rows |
| Native request evidence plus incomplete fallback | Keep | Browser delivery is mandatory when applicable; fallback cannot false-pass missing data |
| Conditional state/Variables/recorder | Keep | Retains targeted diagnosis without paying the cost on every field/action |
| Typed claims and deterministic judge | Keep | Prevents coherent-empty and partial-tag false positives |
| Continuous chronology/anomaly model | Keep | Provides the requested human-like detection between interactions |
| Just-in-time material scenarios | Keep | Preserves finite/dependent coverage without full population enumeration |
| Immediate five-layer renderer | Keep | Makes every event actionable and prevents agents from postponing feedback |
| Health telemetry as optional evidence | Keep optional | Useful when available but not part of measurement proof |
| Automatic reload/retry/fallback browser | Reject | Adds delay, mixed documents, and ambiguous evidence |
| Default accumulated Data Layer/Variables | Reject | Duplicate normal proof already available in exact API Call and tag Names/Values |
| Whole-container/tag inventory | Reject | Unrelated to the selected accepted claims |
| Generic slow-safe mode | Reject | Hides acquisition defects and reintroduces long stalls |
| Firefox/cross-browser product layer | Reject | Outside the owner's current use case |
| Database/service/worker/telemetry platform | Reject | No need for a personal deterministic workflow |

## Technical health results

- 29 runtime Python/JavaScript files, 15,895 physical lines.
- `SKILL.md`: 179 lines, below the 240-line progressive-disclosure budget.
- Ruff lint and formatter: passed.
- Python unit/adversarial suite: 139 passed.
- Real Chromium browser helper: passed.
- JavaScript syntax check: passed.
- Vulture at 80% confidence: no dead-code findings.
- Radon average cyclomatic complexity: grade B, 9.02.
- Real large-plan normalization: 2.551 seconds, 21 events, 167 requirements, 875 claims.
- Release metadata/tree/residue validation: passed for `v7.0.0`.

No run output, backup, workbook, screenshot, user path, client/container/destination, or
previous-run patch is packaged.

## Complexity review

The main maintainability risk remains several large compiler, workflow, judge, and
renderer functions; Radon grades individual hotspots D–F. They contain branch-heavy
domain rules rather than browser waits. Splitting them now would move logic across more
files without measured runtime benefit and would add integration seams. Keep them under
tests and refactor only at a stable domain boundary when a concrete change becomes hard
to verify.

The 457-line collector is the only new browser-specific unit. Its size is justified by
replacing manual parsing and many UI calls with one bounded operation; it uses no
dependency, code evaluation, navigation, retry loop, or persisted raw panel dump. Its
real-browser fixture protects the exact parsing and causal-row behavior.

## Failure and trust model

- A complete contradictory observation is `FAIL`.
- Missing/incomplete acquisition is `BLOCKED`, never an inferred pass or client defect.
- A source/tag/request value mismatch is `FAIL` inside the same action.
- A dead/wrong page can fail independently of technically coherent tracking.
- An incomplete request window cannot prove an absent hit.
- Every non-pass event layer reports the reason, affected checks/fields, evidence, and
  target for human verification.
- Retesting requires an evidence defect or explicit user request; the engine never starts
  a cleanup reload automatically.

## Remaining risks

1. Live Tag Assistant selectors and latency are external and must be observed in real
   use. The bounded partial-result contract contains the risk.
2. Native Playwright request capture remains preferable because Resource Timing cannot
   prove every request body.
3. Large branch-heavy domain modules are maintainability risks, not current runtime
   regressions; all are covered and Vulture finds no dead code.

## Recommendation

Release and install v7.0.0. Measure the next live run rather than adding speculative
machinery. If a real failure remains, correct the narrow plan-normalization,
Preview-collector, or native-network boundary that produced it; do not restore global
preflight, default diagnostic panels, or repeated navigation.
