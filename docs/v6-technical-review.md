# v6 Technical Review

Status: v6.0.1 technical review, 2026-08-24.

## Verdict

The v6 architecture is appropriate for a personal expert skill: sophisticated in
measurement judgement, narrow in browser control, and free of commercial-product
machinery. It reuses the existing typed compiler, evidence, causal model and deterministic
judge while replacing the error-prone browser choreography.

No client/run-bound path, event count, domain, selector, container, destination, prior
evidence, backup or repair branch is part of the active source tree.

## Runtime architecture

1. `plan.py` compiles accepted inputs into immutable typed claims and scope.
2. `capture.py` validates, minimizes and redacts typed observations.
3. `state.py` owns the append-only stream and evidence integrity.
4. `correlate.py` derives one action/document/Preview/tag/request occurrence model.
5. `judge.py` derives claims, six domains, anomalies, confidence, coverage and verdicts.
6. `workflow.py` enforces the frozen action and one-pass completion protocol.
7. `report.py` renders compact checkpoints and final artifacts from the same authority.
8. `recette.py` exposes eight public commands; only `next` and `complete` are in the
   repeated browser loop.

Low-level begin/commit/sync functions remain internal implementation seams for focused
tests and idempotent workflow composition. They are not public alternative routes.

## Necessity review

| Change | Keep? | Reason |
| --- | --- | --- |
| Playwright MCP-managed headed Edge default | Yes | Removes extension/CDP/existing-window ambiguity and standardizes semantic browser control. |
| Capability-based runtime check | Yes | Verifies the managed Edge/action/network contract without coupling startup to one package version; an explicit failed self-check still stops. |
| Existing-window explicit fallback | Yes | Retains a needed exceptional path without contaminating the normal workflow. |
| Browser preparation before compilation finishes | Yes | Lets the user complete sign-in, Preview and consent while deterministic plan intake runs. |
| `next` before the measured target load | Yes | Separates setup browsing from evidence and removes routine cleanup loads. |
| Frozen action ID, mode, event slice and document policy | Yes | Prevents drift, duplicate interactions and mismatched completion evidence with little runtime cost. |
| One typed `complete` bundle | Yes | Replaces separate file/commit/Preview/sync handshakes and creates immediate feedback. |
| Target navigation/reload/reset guard | Yes | Directly addresses repeated page loads; other counters are optional telemetry. |
| Exact-scope structured retest basis | Yes | Stops automatic clean repeats and prevents one event/scenario retest from erasing another action. |
| API-Call-first source | Yes | Avoids routine recorder installation while preserving exact-message authority. |
| Preview epoch/index cursor | Yes | Reads only rows produced by the frozen action and rejects stale or mixed-history evidence. |
| Separate Data Layer state and Variables | Yes | Prevents source laundering and exposes GTM state/resolution defects. |
| Per-plan-field cross-layer projection | Yes | Detects partially mapped tags and coherent-but-empty delivery. |
| Dynamic concise GA4 category resolution | Yes | Corrects generic scope without client-specific identity patches. |
| Continuous anomaly stream | Yes | Detects interjected, duplicate, premature, stale and contaminating behavior; one following completion can revise the prior event without another browser phase. |
| Just-in-time material scenarios | Yes | Preserves finite/dependent depth without whole-plan startup work. |
| Non-blocking coverage annotations | Yes | Records plan gaps immediately but does not delay the current browser capture. |
| Compact immediate feedback with full canonical detail | Yes | Gives the operator a useful verdict after each event without discarding field-level evidence. |
| Live release pilot gate | Yes | Prevents fast synthetic tests from hiding a slow or broken real browser workflow. |
| Firefox/cross-browser layer | No | Outside the owner's use case. |
| Automatic fallback/replacement browser | No | Reintroduces ambiguity and long failure searches. |
| Global tag/container scan | No | Adds Preview work unrelated to current accepted claims. |
| Fixed layer/event matrices | No | Creates non-applicable work and false requirements. |
| Database, service, workers or dashboard | No | No measured need for a personal skill. |
| Generic slow-but-safe mode | No | Masks control defects; deeper scenarios already use the same complete proof model. |

## Correctness and safety controls

- strict missing/undefined/null/empty/value and JSON-type semantics;
- no evidence substitution across API Call, Data Layer state, Variables, tag runtime and
  request;
- complete-window requirements for absence and missing delivery;
- action/document/frame/Preview/container/tag/destination/logical-hit attribution;
- explicit old-document before state and exact new-document rebind;
- centralized evidence minimization/redaction and formula-safe output;
- immutable plan, append-only stream, digest-bound evidence and exact retry idempotency;
- deterministic status ownership; semantic annotations can only add `FAIL` or `REVIEW`;
- finalization refuses open actions, unresolved gates, incomplete confidence/coverage and
  unsafe output.

## Performance characteristics

The deterministic core contains no browser polling loop, wait/sleep, network call, model
call or whole-plan scenario generation. Plan compilation, evidence correlation and
judgement are local. Browser cost is limited by one semantic action, one bounded event-list
read, selective concerned details and filtered network inspection per interaction.

The runtime operation guard requires only cumulative target navigation and reload counts;
context reset is conditional. Tab-switch and Preview-read counters are optional telemetry
for diagnosing real latency and do not block an action.

## Static health

The runtime remains 28 Python/JavaScript files and 14,643 physical lines; the supporting
Python test/harness tree has 11 files and 5,129 lines. The optimization adds no Python
dependency or runtime module. Vulture reports no dead-code finding at 80% confidence.
Radon reports overall grade B (average 8.80); high complexity remains concentrated in
the source normalizer, plan compiler, deterministic judge, report renderer and action validator.

Those functions are the principal maintainability risk. They should be split only around
a stable domain boundary when a real change becomes hard to test; moving the same logic
into more modules would not improve runtime speed. The v5 pre-Preview pulse was removed
because it caused a duplicate whole-stream model build before the canonical post-Preview
judgement and had no public consumer.

## Required verification

- Ruff lint and formatting;
- Python compilation and full deterministic unit/adversarial/stress suite;
- real-browser JavaScript helper smoke tests;
- skill-package quick validation;
- release metadata/tree/residue and absolute-path checks;
- dead-code and complexity review;
- historical tagged-suite comparison;
- clean Playwright MCP live pilot before a release tag.

Current local result: Ruff lint/format and Python compilation pass; 128 deterministic
tests pass; browser helper checks, release-tree validation and skill quick validation
pass; Vulture reports no finding. The separately audited tagged v3.0.0, v3.1.0, v5.0.0,
v5.1.0 and v5.2.0 suites passed 189, 255, 76, 88 and 95 tests respectively. These are
controlled engine results, not a claim that the live Playwright pilot has passed.

## Remaining risks

1. **Live Tag Assistant extraction — medium until pilot.** DOM/accessibility details and
   panel latency are external to the deterministic engine.
2. **Managed-profile setup — low.** The owner may need to sign in once; persistence then
   avoids repeated authentication.
3. **Agent evidence transcription — medium-low.** One typed completion bundle remains
   necessary because MCP observations must enter the deterministic engine. The public
   action/event contract prevents most drift, but the live pilot must prove this handoff
   is prompt and accurate.
4. **Large compiler/judge/workflow functions — low-to-medium maintainability risk.** They
   are cohesive and covered; refactor only with evidence, not for architecture cosmetics.
5. **Very long append-only streams — low unmeasured risk.** Add indexing only if a real
   profile shows replay cost is material.

## Deployment recommendation

Do not call the release live-ready until the pilot passes. If it does, the redesign is
fit for clean personal installation without a generic slow fallback. If it fails, treat
the measured Playwright/Preview handoff as the defect and correct that narrow general
boundary; do not weaken inspection layers or scenario coverage.
