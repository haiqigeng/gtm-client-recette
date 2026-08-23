# v5 Technical Review

Status: final v5.2.0 technical review, 2026-08-24.

## Verdict

The implementation is technically fit for this personal expert skill. The v5.2 code
addresses generalized run failures: unresolved scope prose, repeated handshakes/reloads,
stale action evidence, deferred Trigger Group details, global request-safety
contamination, contradictory transport state, telemetry overcounting, and delayed layer
visibility. It preserves the v5.1 intake, plan projection, scenario, anomaly, and business
truth contracts without recreating v3/v4 operating machinery.

No known run-bound path, client literal, selector, container/destination ID, event count,
prior evidence, backup, or compatibility branch is present in the release tree.

## Runtime architecture

The runtime has one authority at each stage:

1. `plan.py` compiles accepted inputs into immutable typed claims;
2. `capture.py` validates and redacts typed machine evidence;
3. `state.py` appends immutable records and evidence references;
4. `correlate.py` reconstructs one action/document/event/tag/request model;
5. `judge.py` derives all claims, domains, anomalies, gates, and verdicts;
6. `workflow.py` exposes nine non-bypassable commands;
7. `report.py` renders the same canonical result to immediate and final outputs.

There is no alternate ledger, mutable status file, manual PASS setter, browser adapter
family, background service, database, or migration runtime.

## Necessity review of v5.2 changes

| Change | Keep? | Reason |
| --- | --- | --- |
| Two-block XLSX parser | Yes | Removes a real intake blocker with a common structural rule and no client-specific branch. |
| Code/example row exclusion | Yes | Prevents fabricated requirements. |
| Source/delivery event split | Yes | Prevents impossible vendor expectations for source-only messages. |
| API Call fallback plus separate Data Layer state | Yes | Restores correct evidence authority when document-start injection is unavailable. |
| Per-field state/Variables/mapping/runtime/request claims | Yes | Detects partial tag implementations against the plan baseline. |
| Action-local completeness | Yes | Prevents evidence from one action deciding another. |
| Explicit navigation rebind rule | Yes | Avoids blocking normal navigation while retaining identity safety. |
| Continuous API-fallback anomaly stream | Yes | Preserves weird-event detection when the recorder is late. |
| Coverage reopening | Yes | Prevents a stale PASS after another scenario executes. |
| Exact commit idempotency | Yes | Makes safe retry recovery deterministic without a new state system. |
| Provisional per-layer pulse | Yes | Gives immediate targeted feedback from evidence already captured. |
| Optional operation counters | Yes | Diagnoses real browser cost without creating work or a gate. |
| Deterministic plan-scope resolution | Yes | Prevents broad prose from becoming a fake tag/destination and fails unresolved identity before browser work. |
| One handshake and minimal phase bundles | Yes | Directly removes repeated capability, binding, health, and Preview captures. |
| API Call as normal source; recorder conditional | Yes | Avoids ordinary install/reload work while keeping stronger call-time evidence available when needed. |
| Same-scenario retest reason | Yes | Stops automatic clean repeats without limiting distinct material scenarios. |
| Capture-time freshness enforcement | Yes | Prevents an agent-supplied action ID from laundering old observations. |
| Exact-row plus technical causal Preview join | Yes | Handles deferred GTM firing without mixing source-state evidence or crossing the next business event. |
| Concerned-request privacy scope | Yes | Removes unrelated false failures while retaining redaction and in-scope sensitive-data failure. |
| Full operational rows in the pulse | Yes | Reuses existing judgement and gives immediate targeted layer visibility. |
| DOM capture adapter | No; removed | It had no judgement consumer and created redundant run evidence. |
| Firefox/cross-browser framework | No | Outside the personal Chromium use case. |
| Global tag inventory/deep read | No | Slow and unrelated to current accepted claims. |
| Generic slow mode | No | Hides bottlenecks and is not needed for deeper scenario coverage. |
| Graph/worker/service/cache platform | No | No measured need. |
| Run-specific normalizer or selectors | No | Would merely patch one execution. |

## Size and complexity

The source tree has 28 Python/JavaScript files under `scripts` and about 12,004 lines,
versus 16,472 in v3.0 and 21,712 in v3.1. The v5.2 increase over v5.1 is about 492 lines,
mostly enforceable freshness/phase/causal rules and seven generalized regression tests.
The public interface remains nine commands, with one compatible `begin` option, and the
installed reference set remains four files.

Static analysis reports average cyclomatic complexity in grade B. The main maintainability
risk is concentrated in the workbook parser/compiler and deterministic judge. Splitting
them now would move the same domain logic across more modules without reducing browser
work or user-facing complexity, so no architecture-only refactor was added. Future splits
should follow stable boundaries only when another change makes those functions difficult
to verify.

The dead-code scan reports no findings at 80% confidence. The unused generic DOM capture
adapter was removed; the DOM interaction census remains a scenario-discovery helper.
Browser screenshots are not a runtime evidence adapter.

## Correctness and safety controls

- strict missing/undefined/null/empty/value and JSON-type semantics;
- source, accumulated GTM state, Variables, tag mapping/runtime, and request
  non-substitution;
- complete-window requirements for absence and missing-delivery failures;
- exact action/document/frame/Preview/container/destination attribution;
- old-before/new-after document handling only with an explicit rebind;
- centralized persistence redaction and sensitive-data findings;
- immutable plan and append-only stream with digest-bound evidence;
- exact retry idempotency and pre-persistence validation;
- deterministic status ownership and final freeze;
- formula-safe, reload-validated XLSX output.

## Performance health

No wait, sleep, polling loop, browser retry loop, network call, model call, or whole-plan
scenario generation exists in the deterministic core. The principal startup cost for a
multi-sheet XLSX is openpyxl parsing. Field projection increases comparisons but does not
increase browser interactions because all layers reuse the same action and targeted
Preview extraction.

The controlled checks measured 0.08 seconds for a 100-event/2,000-requirement compile,
0.61 seconds for a three-event action/feedback cluster, 0.21 seconds for a dependent-
surface fast-fail, and a 2.515-second median for direct representative multi-sheet
workbook intake. v5.2 also prevents repeated setup by contract. A live run taking many
minutes before inspection therefore indicates browser/agent workflow nonconformance,
not required deterministic setup.

## Verification gates

The release requires:

- Ruff lint and formatting;
- Python compile check;
- full deterministic unit/stress suite;
- real-browser helper smoke test;
- release metadata/tree/residue check;
- skill package validation;
- deterministic archive and manifest verification;
- clean installation manifest verification;
- repository diff scan for user-bound/run-bound residue.

The tagged v3.0.0, v3.1.0, v5.0.0, and v5.1.0 suites are rerun from clean archives for
the release audit. Historical suites prove their own baselines; the v5.2 stress tests
prove the corrected contracts.

Final local results: Ruff and compilation pass; 95 deterministic tests plus four subtests
pass in 18.650 seconds; browser helpers pass; vulture reports no findings; Radon reports
average grade B (8.03); release-tree and skill validation pass. Clean tagged archives
also pass 189 tests for v3.0.0, 255 for v3.1.0, 76 for v5.0.0, and 88 for v5.1.0. The
deterministic v5.2.0 archive and clean installed manifest are verified during release.

## Remaining risks

1. **Live control/Preview integration — medium until retested.** A fresh existing-browser
   pilot must confirm attachment, expanded API Call/Data Layer/Variables extraction, and
   targeted concerned-tag reads.
2. **Agent compliance — medium.** Instructions are explicit and the CLI prevents verdict
   fabrication, but a weak agent can still waste time before invoking the vertical path.
3. **Large deterministic modules — low-to-medium maintainability risk.** They are tested
   and cohesive; profile or split only after evidence of change friction.
4. **Very long streams — low unmeasured risk.** Replay is currently fast. Add indexing
   only if a real profile shows it is material.

## Deployment recommendation

Release and install v5.2.0, then run a short representative live pilot before a full
funnel. The acceptance signs are: first layer pulse after the first action, no global
inventory/setup, one existing browser/Preview session, separate API Call and Data Layer
state evidence, complete per-field tag/request comparisons, and mandatory detailed
per-event feedback. Fix only a measured general issue if that pilot disagrees.
