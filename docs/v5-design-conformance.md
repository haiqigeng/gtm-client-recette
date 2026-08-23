# v5 Design Conformance

Status: v5.0.0 release conformance, 2026-08-23. Local deterministic and package
validation pass. Real existing-browser acceptance was blocked by the unavailable browser
bridge and remains an explicit deployment limitation.

## Decision

The implementation corresponds to the zero-based design in its runtime model,
workflow, evidence authority, scenario model, verdict rules, output, and deliberately
rejected machinery. It is a redesign rather than a patch to a particular run.

The release is accepted for clean personal installation with that limitation disclosed.
Passing local fixtures does not replace the first-three-event pilot in the owner's
already-open Chromium and visible Tag Assistant session, and no live speed claim is made.

## North star implemented

The skill maximizes trustworthy findings per expensive browser interaction. Its unit of
certification is one typed measurement claim in one material scenario, not an event
name, tag firing, fixed layer row, or tracking-plan cell in isolation.

A technically coherent chain cannot pass when independent reality is wrong. Examples
implemented in the judge include dead/soft-404 pages, failed forms, unconfirmed
purchases, populated carts represented as empty, stale products, cart/order item
mismatches, wrong transaction/currency/value anchors, media-player inconsistencies,
and repeated purchase identifiers.

## Design-to-implementation crosswalk

| Designed contract | Implementation | Verification |
| --- | --- | --- |
| Lossless staged compiler | `scripts/core/plan.py` reads JSON, YAML, CSV/TSV, XLSX and the supported tracking-plan handoff. It retains source coordinates, contiguous merged/fill-down event identity, allowed values, types and tag/destination scope; intake row accounting is visible and orphan/ambiguous rows fail before browser work. Predicate errors remain event-local. | Compiler tests cover all primary formats, merged XLSX and fill-down CSV rows, orphan/separator safety, malformed later events, enum/type rules, source coordinates and identity validation. |
| One predicate vocabulary | `scripts/core/predicates.py` is used by both compilation and judgement. It preserves missing/null/empty/value distinctions, strict JSON types, safe regex, ranges, count/order, URLs and explicit-only wire coercion. | Differential and preserved-behaviour tests pass. An absent-state dispatch defect found during implementation was corrected and retained as a regression. |
| Typed claims rather than fixed layers | Plan rows compile to reality, source, GTM, delivery, sequence and safety archetypes. State-only/source-only claims do not inherit fabricated tag or request obligations. | State-only and missing-surface tests prove narrower applicability and cross-surface non-substitution. |
| Six diagnostic domains and two closure gates | `scripts/core/judge.py` renders Reality, Source, GTM, Delivery, Behavior and Safety independently. Evidence confidence and scenario completeness control closure. | Every event result contains all six domain summaries while every applicable operational check remains separate. |
| One causal occurrence model | `scripts/core/correlate.py` joins target, document/frame, action, source call, Preview event, tag, logical send and transport attempt. It never assigns evidence merely because an action is open. | Document/Preview identity conflicts, request-ID reuse, inter-action messages, retries and batched sends have executable regressions. |
| Capability-selected evidence authority | The first action records one capability profile and live binding. Document-start call-time capture is authoritative for raw dataLayer proof when available. Preview can remain primary for what GTM processed, but cannot be relabelled as raw API-call proof. | Capability failures block only dependent claims without waiting or opening another browser. Late snapshots cannot pass raw-source claims. |
| Continuous source and network deltas | Typed capture adapters retain all source arguments, state-only/unplanned messages, request lifecycle, redirects/retries, document/worker identity, payload completeness and privacy metadata. | Recorder/browser-helper, network lifecycle, privacy and interstitial anomaly tests pass. |
| Summary-first Preview micro-batches | One Preview sync can cover a short unambiguous event cluster. Fired/relevant-not-fired inventories stay complete; deep details remain scoped. Static configuration alone can be reused under exact container and workspace identity. | The three-event cluster uses one handshake and one Preview batch. Static-cache reuse and identity-change blocking are tested. Runtime values, consent, firing and requests are never cached. |
| Targeted reality anchors | Page/action captures carry URL/status/soft-404, target, before/after business state and completion evidence rather than forcing a full DOM census after every action. | Dead page, failed outcome, cart, product, checkout, purchase and media tests pass. Missing anchors block or fail according to evidence completeness. |
| Just-in-time scenario coverage | `scripts/core/coverage.py` validates finite values, reachable dependent combinations, high-cardinality behavior signatures, live plan gaps and honest unresolved branches without prebuilding future cases. | Language, shipping-country, products, plan gaps and unknown-population tests pass. |
| Human-like surrounding analysis | The judge inspects duplicates, absence, unexpected/interjected/premature/delayed activity, material state contamination, cross-surface count disagreement, runtime errors, ecommerce continuity, media state and duplicate transactions. | Quality and mutation tests prove the engine does not inspect planned events only in isolation. Later evidence can amend earlier feedback. |
| Typed consent and acquisition | Consent activates from plan/tag requirements, Preview consent state, and initialization/update/user-choice chronology. Acquisition requires a bound natural or controlled-navigation context. | Override-only consent blocks, denied sends fail, and fresh Google-referral simulation is accepted with explicit limits. |
| Consequence-aware protected journeys | `handoff` binds CAPTCHA, authentication, verification, payment and approval pauses to the exact browser/tab/document/action lineage. Consequential first actions require a cheap authoritative source self-test. | Same-lineage resume, wrong-lineage rejection and consequential-action preflight tests pass. |
| Renderer-owned statuses | Machine observations enter only through typed capture adapters. Semantic findings may add only evidence-backed `FAIL` or `REVIEW`; no public setter can author `PASS`. | Provenance, transactional bundle, CLI-surface and report-freeze tests pass. |
| Event-first actionable output | `commit` emits a non-certifying pulse. Canonical event feedback contains scenario rows, six domains and operational rows with expected, observed, reason, evidence and `Check next`. Final JSON/Markdown/XLSX/CSV views share the same result model. | Report generation is refused before freeze, formula/privacy safety is verified, and each non-pass row has a target for investigation. |
| Lightweight browser-cost diagnostics | Optional counters ride inside existing health captures for navigation/reset/reload, tab switches, full preflights, Preview summary/deep reads/retries and AI semantic passes. | Counter validation and final telemetry aggregation are tested; no new command or state authority was added. |

## Independent-review conditions

### 1. Probe the real browser integration

Performed before final acceptance. The configured Chrome and Edge control clients were
not available to this task. Local diagnostics found Edge installed, but its ChatGPT
extension was disabled and the native-host registration was absent. No replacement
browser was opened and no isolated Playwright fixture was misreported as the user's
existing session.

Design consequence: the skill remains capability-adaptive and fails dependent proof
quickly. Preview may prove GTM-processed state; raw dataLayer claims remain blocked
without document-start or another declared direct source.

### 2. Harvest the verified evaluator kernel, not the old architecture

Satisfied. The redesign retains characterized path/value/privacy/recorder/report-safety
utilities. It replaces the old plan normalization, correlation, ledgers, fixed-layer
rollup, command surface and output projection. No legacy schema migration or alternate
result authority remains active.

### 3. Require a real first-three-event slice before live deployment acceptance

Not yet satisfied. The controlled three-event contract passes locally, but the authorized
real-site run could not be executed without the existing-browser bridge. This limitation
is `BLOCKED`, not simulated or reported as passed; it does not invalidate deterministic
release packaging, but it prevents claiming live operational acceptance.

### Consent and agent-authority clarifications

Satisfied. Consent is typed and vendor-neutral; keyword detection or a CMP registry is
not used. The deterministic renderer owns status and closure. Agent judgment can expose
an evidence-bound semantic concern but cannot upgrade, suppress or invent machine proof.

## Quality-preserving speed decisions

- Compile the accepted plan once and expose its first executable event; do not build
  future-event scenarios, layer rows, reports or ledgers.
- Share persistent source/network capture and one live identity handshake.
- Let one natural action cover several planned events when identities remain clear.
- Batch Preview summaries, then deep-read only expected or suspicious details.
- Reuse only immutable tag configuration under exact identity; never cache action-time
  evidence.
- Discover scenarios just in time and schedule by information value and transition cost.
- Render the pulse and event feedback from already captured evidence; output adds no
  browser work.
- Fast-fail an unavailable surface and continue independent checks instead of retrying
  indefinitely or opening a replacement browser.

## Machinery deliberately not implemented

- fixed nine- or nineteen-layer matrices;
- whole-plan scenario/result scaffolds;
- event/session/coverage/runtime ledger families;
- a generic slow mode;
- Firefox or a cross-browser adapter program;
- private Tag Assistant API reverse engineering;
- graph database, workers, service, dashboard or telemetry platform;
- exhaustive products/pages, arbitrary scenario caps or a global Cartesian matrix;
- full DOM, Preview, variable or request-body dumps after every action;
- one AI call per field/layer;
- ad hoc container injection or browser replacement as normal recovery;
- CMP/vendor registries, migration framework or client/run-specific branches.

## Conformance verdict

| Area | Verdict |
| --- | --- |
| Architecture and runtime model | CONFORMS |
| Inspection depth and operational detail | CONFORMS |
| Scenario variability and sampling | CONFORMS |
| Weird-behavior and business-semantic detection | CONFORMS |
| Speed-oriented workflow shape | CONFORMS in code and controlled fixtures |
| Repository/general-use hygiene | CONFORMS |
| Existing-browser controlled pilot | BLOCKED by unavailable browser bridge |
| Real-site first-three-event acceptance | NOT RUN; required before live deployment acceptance |

The implementation conforms and is release-accepted with the existing-browser limitation
explicitly documented. Live deployment acceptance remains pending the real pilot.
