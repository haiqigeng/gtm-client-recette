# v5 Technical Review

Status: final v5.1.0 technical review, 2026-08-23.

## Verdict

The implementation is technically fit for this personal expert skill. The added code
addresses real generalized correctness gaps: supported workbook intake, source authority,
source/delivery identity, action-local completeness, planned-field projection,
navigation identity, protocol decoding, coverage freshness, retry safety, and detailed
feedback. It does not recreate the v3/v4 operating machinery.

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

## Necessity review of v5.1 changes

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
| Firefox/cross-browser framework | No | Outside the personal Chromium use case. |
| Global tag inventory/deep read | No | Slow and unrelated to current accepted claims. |
| Generic slow mode | No | Hides bottlenecks and is not needed for deeper scenario coverage. |
| Graph/worker/service/cache platform | No | No measured need. |
| Run-specific normalizer or selectors | No | Would merely patch one execution. |

## Size and complexity

The source tree has 28 Python/JavaScript files under `scripts` and about 11,512 lines,
versus 16,472 in v3.0 and 21,712 in v3.1. v5.1 is larger than v5.0 by about 1,300 lines
because the previous release did not implement the required intake and cross-surface
contracts. The public interface remains nine commands and the installed reference set
remains four files.

Static analysis reports average cyclomatic complexity in grade B. The main maintainability
risk is concentrated in the workbook parser/compiler and deterministic judge. Splitting
them now would move the same domain logic across more modules without reducing browser
work or user-facing complexity, so no architecture-only refactor was added. Future splits
should follow stable boundaries only when another change makes those functions difficult
to verify.

The dead-code scan reports only known false positives for ZIP/openpyxl attributes.
Unreachable screenshot/file capture functions, unused status/path helpers, an unused
future-coverage helper, and an unused report wrapper were removed. Browser screenshots
are not a runtime evidence adapter in this release.

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

The controlled benchmarks show about 2.9 seconds from direct representative workbook
intake to the first provisional inspected-layer pulse and about 220 ms median for a
synthetic canonical-feedback path. A live run taking many minutes before inspection
therefore indicates browser/agent workflow nonconformance, not required deterministic
setup.

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

The tagged v3.0.0, v3.1.0, and v5.0.0 suites were also run from clean archives to make
the comparison explicit. Historical suites prove their own baselines; the v5.1 stress
tests prove the corrected contracts.

Final local results: Ruff and compilation pass; 88 deterministic tests pass in about
16 seconds; browser helpers pass; release-tree and skill validation pass; and the
deterministic v5.1.0 archive/manifest verifies successfully.

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

Release and install v5.1.0, then run a short representative live pilot before a full
funnel. The acceptance signs are: first layer pulse after the first action, no global
inventory/setup, one existing browser/Preview session, separate API Call and Data Layer
state evidence, complete per-field tag/request comparisons, and mandatory detailed
per-event feedback. Fix only a measured general issue if that pilot disagrees.
