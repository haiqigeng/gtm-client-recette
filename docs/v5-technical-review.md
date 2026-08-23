# v5 Technical Review

Status: final technical review of the v5.0.0 release, 2026-08-23.

## Overall verdict

The technical design is lean enough for a sophisticated personal skill and materially
healthier than the v3.1/v3.2 architecture. It has one immutable plan, one append-only
evidence/occurrence stream, one deterministic judge, one renderer and nine public
commands. No dead runtime route, legacy ledger, browser matrix or run-specific patch was
found.

Local technical quality and packaging are suitable for release. Operational deployment
is not accepted until the existing-browser first-three-event pilot passes.

## Runtime structure

The packaged runtime contains 25 Python/JavaScript files and approximately 10,689 lines.
Together with the 157-line skill entry and four references (368 lines), the active
instruction/runtime surface is approximately 11,214 lines. This is less than half the
approximate active surface of v3.1/v3.2 while preserving their useful quality questions.

The core responsibilities are cohesive:

1. `plan.py` and `predicates.py`: staged source-preserving compilation and one typed
   predicate vocabulary;
2. `capture.py`: typed, transactional, privacy-gated evidence intake;
3. `correlate.py` plus GA4/Ads decoders: canonical occurrences and logical delivery;
4. `coverage.py` and `judge.py`: JIT scenario closure, deterministic claims, business
   relations, anomalies, confidence and rollup;
5. `workflow.py` and `report.py`: minimal operating surface, pulses, event feedback,
   freeze and final outputs.

Separate recorder, request-decoder, DOM-census, safe-value/path/privacy and synthetic
form helpers survive because each owns a tested runtime contract. Three redundant
standalone inspection/diff/retest scripts were removed after their behavior became a
projection of the compiler or final report.

## Public operating surface

Exactly nine routes are exposed:

`init`, `begin`, `commit`, `sync-preview`, `status`, `handoff`, `finish`, `report`, and
`reopen`.

There is no generic append command, verdict setter, layer setter, alternate plan/results
file, per-event scaffold command or provenance override. `status` is read-only. Machine
observations can be written only through typed capture adapters. A finished run rejects
mutation until explicit user reopen authorization.

## Dependencies

Runtime dependencies are limited to:

- `openpyxl` for XLSX intake/output;
- `PyYAML` for YAML intake.

Playwright is optional and used only by the browser-helper development test. Ruff,
Vulture and Radon are development checks. No Firefox dependency, browser abstraction
framework, database, worker, service, dashboard, image library or vendor SDK was added.

## Static health results

| Check | Result |
| --- | --- |
| Ruff lint | PASS |
| Ruff format | PASS |
| Git whitespace check | PASS |
| JavaScript syntax (`datalayer_recorder.js`, `dom_interaction_census.js`) | PASS |
| Vulture at 80% confidence | No findings |
| Release metadata/tree check | PASS for v5.0.0 |
| Clean archive manifest verification | PASS |
| Extracted install verification and CLI startup | PASS |

Cyclomatic complexity averages grade B (about 7 across the script tree). After the
final media refactor, no function is grade E or F. The highest remaining functions are
grade D and are concentrated in parsing, capture normalization, coverage validation and
domain-specific judgement where branching is intrinsic and directly tested.

Maintainability-index tools grade the largest semantic modules (`judge.py`, `plan.py`,
`capture.py`, and the preserved client-side rule helper) as C because of size and dense
branching. This is a maintainability warning, not an executed correctness defect.
Splitting `judge.py` solely to improve a metric was rejected for now: it would add
cross-module plumbing without reducing the proof model. A split becomes justified when
two independent change streams or profiling/debugging evidence show real friction.

## Dynamic and regression results

- 76 deterministic unit/contract/metamorphic tests pass in about 15.5 seconds.
- Browser recorder/census helper tests pass in isolated Chromium, including observer
  non-interference checks.
- The 100-event/2,000-requirement compiler benchmark is about 64 ms median locally.
- Cold synthetic init-to-first canonical event feedback is about 215 ms median.
- The three-event sharing contract uses one capability record, one live binding and one
  Preview batch.
- Package build, manifest verification, clean extraction, installed-tree verification
  and packaged CLI startup all pass.

These timings prove the deterministic runtime is not recreating the old front-loaded
machinery. They do not prove live browser speed.

## Correctness and false-pass safeguards

- Compiler and judge share the same supported predicate registry; unsupported rules
  become localized compile errors before browser work.
- XLSX and delimited intake preserve contiguous merged/fill-down event rows, expose row
  accounting, and reject orphan/ambiguous rows instead of silently dropping them.
- Missing, null, empty and populated values remain distinct. JSON booleans cannot pass
  as numbers; wire coercion is explicit and transport-only.
- Each evidence surface proves only itself. Source, Preview, tag runtime and request
  rows cannot substitute for one another.
- Empty complete windows can prove absence; partial/late/truncated windows block.
- Current origin/document/container/Preview identity is an independent gate.
- Dead pages and failed business outcomes control the overall verdict even when tags
  and requests look coherent.
- Full fired and relevant-not-fired inventories remain required before selective deep
  inspection can pass.
- Static reuse is confined to configuration under exact container/workspace identity.
- Continuous source messages and cross-event anomalies remain available to revise
  earlier feedback.
- Semantic annotations can only add evidence-backed `FAIL` or `REVIEW`.
- Privacy redaction occurs before ordinary persistence; raw bodies require named
  quarantine and cannot enter results.

## Bugs discovered by the review

Three deterministic defects were found by adversarial tests and fixed:

1. the `state: absent` predicate was intercepted by generic missing-value failure;
2. an unextracted expected static tag configuration was reported as a mismatch `FAIL`
   instead of observability `BLOCKED`.
3. tabular requirements under merged/fill-down event cells were silently skipped; they
   are now retained within a contiguous event block, while orphan rows fail at intake.

Both have focused regressions. The review also closed semantic omissions for cart/order
continuity, media-player state and repeated transactions, and added exact static reuse
plus browser-cost counters.

## Dead code, residues and genericity

- Vulture reports no probable dead Python code at the selected confidence threshold.
- The release checker enforces the exact active reference/core/protocol/CLI trees and
  rejects unclassified root scripts.
- Obsolete v3/v4 ledger, layer, migration, operator and duplicate report utilities were
  removed rather than retained behind compatibility switches.
- An untracked prior-run directory and the stale local v4 distribution archive were
  removed. They were not Git-tracked and are not recoverable through this worktree;
  external copies and Git history are unaffected.
- `runs/`, evidence, reports, logs, spreadsheets, caches and build output are ignored and
  excluded from the release artifact.
- Generic scans found no user-bound absolute path, client/container/destination literal,
  run selector, prior evidence or specific site patch in active source/guides.
- Historical behavior remains in Git/tests and documentation, not as discoverable
  installed backup skills or runtime compatibility code.

## Overengineering review

Necessary mechanisms retained:

- typed compiler and predicate registry;
- one capability profile and current live binding;
- append-only evidence with provenance and transactional bundles;
- continuous source/network capture and protocol decoding;
- one occurrence correlation model;
- JIT finite/dependent/signature coverage;
- deterministic business/anomaly/confidence judgement;
- consequence-aware protected handoff;
- detailed event-first and final reporting;
- small operation counters needed to diagnose browser cost.

Rejected as unnecessary:

- fixed-layer bureaucracy, whole-plan setup, parallel ledgers and migration framework;
- databases, workers, services, dashboards or telemetry platform;
- Firefox/cross-browser support for this personal use case;
- a generic slow mode or repeated global validation;
- private Preview API integration, vendor/CMP registries and broad static inventories;
- exhaustive high-cardinality browsing, arbitrary caps or full Cartesian combinations;
- one model call per check and cache of action-time evidence.

## Remaining risks and next technical action

1. **Existing-browser integration — high acceptance risk.** The actual Chrome/Edge
   control bridge was unavailable, so document-start injection, continuous network
   events and visible Tag Assistant extraction could not be validated end to end.
2. **Long real streams — medium-low risk.** Replay remains authoritative and currently
   fast. Add an in-memory cursor/index only if an actual long-run profile shows material
   cost.
3. **Large semantic modules — medium-low maintainability risk.** Functions are bounded
   and tested; split by stable domain boundaries only when change evidence justifies it.
4. **Agent compliance — medium operational risk.** Renderer-owned statuses and nine
   routes prevent many bypasses, but a weak-agent existing-browser run remains necessary.

The next action is not more machinery. Restore the configured browser bridge, run the
authorized first-three-event pilot, inspect its operation counters and phase timing, and
fix only a measured general bottleneck or correctness gap. Do not treat live deployment
as accepted if that pilot requires replacement tabs, improvised plan rebuilding,
repeated full preflight, evidence recreation or hidden repair loops.
