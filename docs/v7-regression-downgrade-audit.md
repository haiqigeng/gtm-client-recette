# v7 Regression and Downgrade Audit

Status: release candidate audit, 2026-08-25.

## Executive verdict

No known deterministic quality regression remains. v7 deliberately removes default
browser work, not acceptance depth: the exact source call, effective tag mapping/runtime,
browser delivery, page truth, chronology, material scenarios, safety, and confidence are
still judged independently.

The principal residual risk is live Tag Assistant/Playwright latency on an external
site. Incomplete acquisition now yields immediate targeted `BLOCKED` feedback instead
of a reload or long recovery loop, so it cannot create a false pass.

## Reproducible version comparison

Each tagged version was extracted from Git and ran its own test suite unchanged. Runtime
size is physical lines in `.py` and `.js` files under `scripts/`.

| Version | Runtime files / lines | `SKILL.md` lines | Own suite |
| --- | ---: | ---: | ---: |
| v3.0.0 | 32 / 17,596 | 408 | 189 passed in 8.303 s |
| v6.0.1 | 28 / 14,643 | 194 | 128 passed in 22.231 s |
| v7.0.0 candidate | 29 / 15,895 | 179 | 139 passed in 23.663 s + browser helper passed |

Suite durations are not live recette timings and are not directly comparable because
the contracts differ. They prove that each source tree is internally green. v7 adds one
dependency-free browser collector and stronger partial-output/coherence tests; its
instruction entry point is shorter than both comparison versions.

## Capability comparison

| Capability at risk | v7 outcome | Downgrade check |
| --- | --- | --- |
| Exact Data Layer occurrence | Preserved | Fully expanded API Call is mandatory when applicable; state cannot substitute |
| Accumulated Data Layer state | Narrowed to diagnostic | Explicit state requirements still compile and activate the panel |
| GTM Variables tab | Narrowed to diagnostic | Explicit resolved-variable requirements still compile and activate the panel; tag Names/Values are the normal proof |
| Tag identity/inventory/firing | Preserved | Complete concerned fired/not-fired summary remains required for a GTM pass |
| Effective mapping/runtime | Preserved and strengthened | Every destination-applicable planned field is checked; API/runtime mismatches fail |
| Browser request | Preserved | Exact native request is preferred; incomplete Resource Timing can only block, never pass missing fields |
| Dead/wrong page | Preserved | Reality is independent and can fail a technically coherent chain |
| Interjected events | Preserved | Every post-cursor event and business API Call is retained in order |
| Duplicate/missing events or sends | Preserved | Complete source/request windows retain occurrence counts and retries |
| Causal Trigger Group firing | Preserved | Planned row opens a technical causal window that ends at the next unrelated business event |
| Finite/dependent scenario values | Preserved | Reachable material values remain exhaustive and strict per selected scenario |
| High-cardinality values | Preserved without brute force | Sample by materially different behavior signature and expand on anomalies/new branches |
| Plan-omitted live values | Preserved | Record a plan gap and add a scenario only when materially distinct |
| Consent/forms/protected journeys | Preserved conditionally | User prepares ordinary consent; protected gates pause in the same session |
| Per-event feedback | Strengthened | All five rows always render; every non-pass contains reason and targeted details |
| Missing acquisition evidence | Improved | Completion returns partial feedback instead of throwing or causing cleanup navigation |

## Speed changes and their quality guard

| Removed default work | Why it was slow | Guard against quality loss |
| --- | --- | --- |
| Accumulated Data Layer claims for every field | Duplicated each plan field and opened another Preview panel | Exact API Call remains source authority; explicit state checks still work |
| GTM Variables claims for every field | Duplicated each plan field and panel traversal | Effective tag Names/mapping and runtime Values remain mandatory |
| Tags on every lifecycle row | Repeated UI switches unrelated to the interaction | Tags remain read on the planned row and causal technical follow-ups |
| Mandatory health telemetry | Blocked completion on optional control metadata | Wrong supplied runtime still blocks; absent telemetry cannot fabricate evidence |
| Manual collector normalization | Added an agent/browser handshake and execution errors | Collector returns canonical typed evidence directly |
| Cleanup reload/retry after partial evidence | Repeated the most expensive action and mixed documents | Partial components become explicit `BLOCKED`; retest needs a structured basis |
| Up-front state/coverage scaffolding | Delayed first inspection | Claims compile locally and scenarios expand just in time |

On the measured 21-event/167-requirement workbook, this reduces compiled claims from
1,209 to 875 by deleting exactly 167 default state and 167 default Variables mirrors.
No tracking requirement or default source/tag/runtime/request field obligation was
removed.

## Regression risks reviewed

1. **Resource Timing fallback — medium.** It cannot prove every POST body. It is marked
   incomplete, so missing request fields are `BLOCKED`; native Playwright request
   evidence remains the acceptance source.
2. **External Tag Assistant DOM — medium.** UI changes may make one component partial.
   The collector is bounded and fail-closed; it cannot reload or silently pass.
3. **Conditional state/Variables — low.** A plan explicitly declaring `state_path` or
   `resolved_path` still activates the relevant panel. General ambiguity can request the
   same targeted diagnostic.
4. **Partial completion — low.** It improves progress but does not weaken verdicts:
   dependent claims block and the reason is visible per layer.
5. **Causal-window narrowing — low.** Initial lifecycle rows and later unrelated
   business rows skip Tags only; their chronology remains visible and every unexpected
   business API Call is still parsed.

## Deployment decision

The candidate is safe for an official personal release. The next live run should measure
time to first action and first feedback, but it does not require a generic slow fallback.
Any live collector incompatibility should be fixed at that narrow acquisition boundary,
not by restoring default panels, repeated reloads, or whole-session scans.
