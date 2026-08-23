# v5 Regression and Downgrade Audit

Status: final local audit for the v5.0.0 release, 2026-08-23.

## Executive result

No known deterministic regression or quality downgrade remains against the contracts
retained from v3.0.0, v3.1.0 and v3.2.0. The redesign removes procedural machinery, not
inspection questions. Local tests pass, packaging verifies, and controlled latency is
small.

Live deployment safety is still unproven because the configured existing-browser bridge
was unavailable. The real first-three-event pilot remains blocked and is disclosed as a
release limitation. It would be a false claim to compare local core milliseconds
directly with the historical live run that took hours.

## Historical comparison boundary

The Git repository contains tags through v3.2.0. It has no v4.0.0 tag, so v4 comparisons
use the prior worktree/design and documented field evidence; they are not independently
reproducible from a release tag.

Approximate active-source shape:

| Version | SKILL lines | References | Runtime/repository scripts | Public parser routes | Approx. active lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| v3.0.0 | 408 | 23 / 4,054 lines | 32 / 17,596 lines | 36 | 22,058 |
| v3.1.0 | 266 | 8 / 485 lines | 41 / 23,187 lines | 42 | 23,938 |
| v3.2.0 | 275 | 8 / 516 lines | 41 / 23,946 lines | 42 | 24,737 |
| v5.0.0 | 157 | 4 / 368 lines | 25 runtime files / 10,689 lines | 9 | 11,214 |

The current runtime figure excludes three repository-only package/release validators.
Line count is not used as a speed claim; it is evidence that removed ledgers/routes did
not survive under new names.

## Latency evidence

| Measure | Historical evidence | v5 controlled result | Interpretation |
| --- | --- | ---: | --- |
| Live time to first inspection | v3.1/v3.2/v4 field reports include 20+ minutes without inspection and one multi-attempt run lasting hours without first event feedback | Not measurable in the existing browser because its bridge was unavailable | Real acceptance remains blocked; no synthetic substitution. |
| CLI cold `--help` | Not a useful historical live metric | median 316.0 ms; min 310.6; max 327.0 (10 processes) | Import/CLI overhead is small but not the primary speed claim. |
| Compile 100 events / 2,000 requirements | Later versions could front-load per-event artifacts | median 63.6 ms; max 66.0 ms (5 local runs) | Plan size does not create runtime cases or evidence before action. |
| Cold local init-to-first canonical feedback | Older fixture results are not directly comparable across architectures | median 215.4 ms; max 218.6 ms (10 synthetic runs) | Deterministic core is not the bottleneck. Browser/Preview cost remains to be proven. |
| Three-event cluster | Later versions repeated setup and staged validation | controlled contract passes with one capability capture, one binding capture and one Preview batch, under its five-second local budget | Sharing is implemented; visible-browser behavior remains the acceptance gate. |
| Full deterministic suite | Not comparable because test contracts changed | 76 tests in about 15.5 s | Broad local regression coverage, not live-site proof. |

## Downgrade matrix

| Capability | v5 result | Downgrade assessment |
| --- | --- | --- |
| Plan order, source provenance and malformed rows | Preserved with source coordinates, tabular row accounting, safe contiguous fill-down, hard failure for orphan/ambiguous rows and event-local predicate errors | Improved: requirements cannot disappear silently and a later malformed predicate cannot block the first valid event. |
| Strict types and value states | Missing, null, empty, boolean, number/integer and strings remain distinct | No downgrade. |
| Raw dataLayer/API proof | Document-start call-time or declared direct source is required | No laundering downgrade; unavailable raw capture blocks only dependent source claims. |
| Complete unplanned stream | Every captured push/argument and state update is retained across and between actions | No downgrade; explicit interjection and contamination tests pass. |
| GTM event, variables and tags | Preview identity, event occurrence, full fired/relevant-not-fired inventory, configuration, firing count and runtime values are separate rows | No downgrade from collapsing six domains; operational detail remains. |
| Static configuration reuse | Reused only with exact container and workspace identity | Speed gain with no action-time cache. Identity change blocks reuse. |
| Browser delivery | Runtime parameter, logical vendor hit, destination, tag identity, request parameters, retry/redirect and outcome are independent | No downgrade; GA4 batches/items and Ads sends are decoded. |
| Several tags or destinations | Tag/destination identity is explicit and one request cannot silently certify unrelated tags | No downgrade. |
| Dead/soft-404 and failed actions | Reality independently controls overall result | Improved over coherent-tag false pass. |
| Cart/product/ecommerce truth | Visible item, cart membership/count/delta, order items, transaction, currency and anchored value are checked | Improved over coherent-empty false pass. |
| Media behavior | Player state, progress, identity, completion and declared visibility are independent anchors | Improved; missing player truth blocks rather than guessing. |
| Duplicate/missing/weird chronology | Duplicate, absent, unexpected, premature/delayed, interstitial state and repeated purchase are first-class findings | No downgrade; later events may amend earlier feedback. |
| Languages and finite enums | Every reachable manageable material value is required and expected values remain scenario-local | No downgrade. `en` and `fr` can each pass in their own context. |
| Shipping/payment dependencies | Reachable country/state-dependent combinations are required | No downgrade; no irrelevant global Cartesian matrix. |
| Hundreds of products/content | Behavior-signature representatives plus ordinary/contrast/boundary/exception expansion | No brute-force downgrade and no arbitrary sample cap. |
| Live values omitted by plan | Recorded as plan gaps and tested when material | Improved over plan-only coverage. |
| Consent | Typed event-time Preview/transition/tag-requirement evidence | Improved over keyword activation; denied sends fail and override-only proof blocks. |
| Acquisition/SEO-sensitive tracking | Natural or labelled controlled referral/fresh context supported | Improved; scope limits remain honest. |
| Forms/CAPTCHA/auth/payment | Ordinary synthetic forms are tested; protected or consequential gates use exact-lineage handoff | No safety downgrade and no unauthenticated replacement window. |
| Privacy and report safety | Pre-persistence redaction/quarantine, screenshot review and formula-safe output retained | No downgrade. |
| Per-event feedback | Scenario/domain summary plus each operational target/status/reason/check-next/evidence | Improved actionability without adding capture work. |
| Final output | Frozen canonical JSON, Markdown, XLSX and focused sidecars | No alternate report authority or premature finalization. |

## Bugs found and corrected during implementation audit

1. `state == absent` could not pass because generic missing-value handling ran first.
   Predicate dispatch was corrected and regression-tested.
2. Missing expected static tag configuration was classified as mismatch `FAIL` before
   checking extraction completeness. It now becomes `BLOCKED`; an observed different
   configuration remains `FAIL`.
3. Static configuration was re-read per event. Exact container/workspace reuse was added
   for configuration only, with identity-change and conflict blocking.
4. The initial business evaluator lacked explicit cart/order item continuity,
   transaction/currency/anchored-value checks, media-player relations and repeated
   transaction detection. These are now general event-family checks with executable
   regressions.
5. The final telemetry omitted the browser operations that explain field delays.
   Optional counters now reuse health captures without creating another ledger.
6. Tabular intake skipped non-empty requirement rows when an XLSX/CSV event identity was
   visually merged or filled down. The compiler now carries identity only inside a
   contiguous table, reports row accounting, and fails on orphan/ambiguous rows before
   browser work.

None of these fixes contains a client URL, container/destination ID, client-specific
workbook layout, selector, run path or prior-run evidence.

## Stress-test result

The research catalogue contains 978 unique design-space scenarios. It is a saturation
catalogue, not 978 executed browser tests. Claiming otherwise would repeat the earlier
fixture-confidence error.

The implementation suite executes 76 generalized tests covering:

- all 13 orthogonal taxonomy dimensions;
- all 12 mutation operators through the mutation contract and focused cases;
- all 32 generalized failed-run cases through a complete contract crosswalk;
- compiler/tabular-intake/predicate, occurrence/correlation, identity/confidence, privacy/integrity,
  finite/dependent/high-cardinality coverage, typed consent/acquisition, business
  reality, weird chronology, reports/freeze and workflow/startup contracts;
- one controlled three-event sharing test and one real Playwright Chromium helper suite
  for recorder/census behavior and observer non-interference.

Browser-UI-only catalogue items remain skill instructions plus mandatory real-pilot
gates. They are not marked passed by local mocks.

## Risk matrix

| Risk | Level | Evidence and disposition |
| --- | --- | --- |
| Compiler drops rows/rules/allowed values/types | Low | Shared predicate registry, merged/fill-down fixtures, source coordinates, row accounting, orphan hard-fail and event-local error tests pass. |
| Speed optimization skips GTM or request inspection | Low locally | Source/GTM/runtime/request non-substitution and partial-evidence tests pass. Real extraction still needs the pilot. |
| Preview batching causes wrong attribution | Low locally | Document/action/epoch tests and one-cluster batch pass; ambiguity requires early sync. |
| Static reuse leaks stale dynamic values | Low | Only configuration is reused under exact identity; current runtime/consent/firing/request remain uncached. |
| Weird events or coherent business errors pass | Low locally | Interjection, duplicate, cart, checkout, purchase and media tests pass. |
| High-cardinality sampling misses a new signature | Medium | Coverage must reopen on new signatures/anomalies; sampling cannot mathematically prove an unknown population. |
| Very long real stream replay becomes material | Medium-low | No evidence in current profiles; add an index only after measurement, not pre-emptively. |
| Existing-browser attachment/Preview extraction stalls | High until tested | Actual bridge unavailable here; first-three-event pilot is mandatory and blocked. |
| Agent ignores the workflow | Medium | Renderer-owned status and one command model reduce bypasses, but cannot force an unconstrained external agent. Weak-agent live testing remains required. |

## Recommendation

Do not add a generic “slow but safe” fallback. It would restore the machinery that
caused the delay. If a surface is unavailable, block only its dependent claims within a
bounded attempt and continue independent checks.

The redesign is technically suitable for this personal v5.0.0 release. Before treating
it as live-deployment accepted, restore the existing-browser bridge and run the
authorized real first-three-event pilot. Accept the live workflow only if the first event
meets the controlled time envelope, the second and third reuse setup/static facts, all
applicable operational rows remain visible, and there is no ad hoc repair loop.
