# Changelog

## Unreleased

## [v1.2.2](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.2.2) (2026-08-01)

- Bound supplemental dataLayer snapshots by depth, node count, and elapsed
  time; distinguish shared references from real cycles; retain readable array
  siblings around hostile elements; and preserve stable snapshot/cursor API
  envelopes with explicit truncation markers.
- Require every unexpected finding to reference a known event group and make
  unplanned session pushes inherit their action group, preventing confirmed
  anomalies from disappearing from event feedback and plan-ordered roll-ups.
- Evaluate cross-requirement uniqueness within one authoritative evidence
  surface and return a precise `REVIEW` when raw, source-signal, and resolved
  fallbacks cannot be compared safely.
- Make payload business rules non-applicable when the accepted occurrence
  branch requires absence, while retaining occurrence, non-firing, request
  absence, scenario, and other downstream checks.
- Expand redacted sensitive-data detection across encoded URLs and decoded
  parameter objects for common analytics/media user-data keys. Classify
  supported SHA-256 and Google `tv.*` formats as `hashed_user_data`, while
  plaintext email, phone, name, postal, IP, and external-ID values remain
  failures under the default technical leakage policy.
- Make DOM census selectors resolve uniquely without structural truncation,
  traverse open shadow roots with selector chains, respect inherited hidden
  state and `aria-labelledby` precedence, and document CSP-compatible
  evaluation.
- Add regression coverage for recorder performance and truncation, hostile
  array elements, missing anomaly groups, mixed uniqueness surfaces,
  conditional absence with declared rules, plaintext-versus-hash detection,
  repeated selectors, strict CSP, hidden ancestors, accessible names, and
  shadow-root controls.

## [v1.2.1](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.2.1) (2026-07-30)

- Prevent conditional-absence, out-of-scope interaction, mapped unexpected
  push, malformed business-rule path, and non-dataLayer source-surface cases
  from producing an incorrect event or component `PASS`.
- Treat Preview event indexes as unique within a stream and connection epoch,
  preserving valid index reuse after reconnection while still rejecting true
  duplicates.
- Make `apply-event` transactional: validate the complete event patch and its
  session reconciliation before atomically replacing the working result.
- Harden the supplemental dataLayer recorder so snapshot failures never change
  the website's push outcome, real cycles remain distinguishable from shared
  references, safe reassignment and wrapper chains remain observable, and
  unverifiable replacements are reported rather than double-wrapped.
- Evaluate declared business rules on the accepted raw dataLayer payload or
  non-dataLayer source signal before using resolved state as a fallback, and
  retain the deterministic evaluation source.
- Detect sensitive values nested in encoded absolute or relative URL query
  parameters without persisting value-derived fingerprints or lengths.
- Export every workbook string as a literal value to prevent formula
  activation, and expose connection epoch and business-rule evaluation source
  in their evidence sheets.
- Derive browser-request layers for tagless direct vendor sends, emit valid
  initializer output when a requirement has no named tag, and centralize only
  the shared status/action-boundary acceptance constants.
- Add 13 focused contract regressions and a real Chromium Playwright suite for
  recorder installation, mutation safety, hostile objects, cycles,
  reassignment, wrappers, duplicate installation, and custom data layers.

## [v1.2.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.2.0) (2026-07-29)

- Promote the session ledger to the strict completion contract: register every
  interaction case and material variant, preserve contiguous retry attempts,
  and reject pending cases, open actions, or normalized boundaries that differ
  from the retained action.
- Require a compact chronological row for every observed business push and an
  explicit per-action push count; classify expected, companion, duplicate,
  premature, delayed, wrong-order, wrong-context, and unplanned-relevant
  occurrences, with anomalous rows reconciled to `unexpected`.
- Derive applicable layers once and require a direct evidence-backed layer
  result on every completed case. Browser-sending analytics/media tags require
  exact configuration, firing/count, runtime value/type, request identity,
  destination/event identity, and decoded parameters; local-only tags do not
  invent network evidence.
- Require structured evidence capture modes and action/event/container/request/
  tag linkage, rejecting reconstructed or inferred evidence as direct proof.
- Reserve final `REVIEW` for a precise semantic ambiguity, keep `PENDING`
  internal, and add consistent per-event feedback with case counts, layer
  results, reasons, and exact non-PASS retest interactions.
- Allow ephemeral same-run synthetic credentials without retention, support
  reusable run-wide safe authorizations, preserve protected checkpoints, and
  permit only explicitly approved/reversed production CMP test exceptions
  without ever passing the native CMP.
- Add `Interaction Cases` and `Observed Push Stream` worksheets and make the
  session ledger mandatory for strict final validation and workbook
  certification.
- Decompose the new session and feedback validators by metadata, case, action,
  layer, push-stream, and final-reconciliation responsibility; make feedback
  use only the retained final retry layers; standardize formatting; require
  every new execution module in release checks; and extend CI through Python
  3.13 with a format gate.

## [v1.1.1](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.1.1) (2026-07-26)

- Require independent, non-tracking proof that a real website interaction
  completed before an absent expected event can be judged as an implementation
  failure.
- Preserve failed or uncertain interaction windows, classify any business
  pushes they contain, and allow one bounded retry with a new linked action ID
  instead of merging or erasing attempts.
- Replace fixed-sleep assumptions with adaptive acceptance-relevant stream
  settlement, recorded quiet/timeout values, and explicit settlement reasons;
  unsettled windows cannot certify absence, count, order, or deduplication.
- Add a deterministic recorder-versus-Tag Assistant discrepancy procedure that
  rechecks container, origin, page node, ownership, connection, full event
  window, and one safe controlled repeat without allowing supplemental evidence
  to pass a required Preview link.
- Extend the resumable session ledger, optional schema-v2 action fields, strict
  conditional validation, Event Evidence worksheet columns, runtime templates,
  and regression fixtures for interaction outcome, completion signal, retry
  lineage, and settlement reason.
- Replace the 12-reference mandatory preload with a compact core execution
  contract and stage-specific progressive loading while preserving every
  acceptance layer and the exact approved north star.
- Add forward-test cases for transient interaction failure, slow/noisy SPA
  settlement, and journal-only pushes missing from Preview.
- Validate release alignment across README, changelog, contribution guide,
  security policy, issue template, agent metadata, package name, and Git tag so
  repository sections cannot silently advertise different versions.
- Preserve one client-side recette workflow; add no container-audit, automatic
  negative-probe, publication, server-side, or legal-consent scope.

## [v1.1.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.1.0) (2026-07-26)

- Consolidate execution into one acceptance workflow whose required evidence
  layers derive from each tracking-plan requirement; remove the former
  full/scoped run-type labels without weakening any declared comparison.
- Preserve the non-substitutive coherence chain from tracking-plan expectation
  through raw API Call, resolved Data Layer, GTM variable, concerned tag
  configuration, firing/non-firing, runtime parameter, browser request, and
  verdict.
- Add practical Tag Assistant attachment, authenticated-session handback,
  connection recovery, history-clearing, and evidence-extraction guidance.
- Add an early document-start dataLayer recorder, visible-interaction census,
  robust query/body/batch request decoder, and atomic per-event
  validate/apply/resume tooling. These helpers supplement rather than replace
  authoritative Tag Assistant evidence.
- Preserve tracking-plan hyperlinks, comments, hidden/merged structure, and
  embedded image anchors/assets during plan inspection, and add a validated
  gold mini-recette plus a browser-helper smoke fixture.
- Require a lightweight census and execution of every applicable interaction,
  placement, branch, and material finite value rather than one representative
  click; exhaust practical low-cardinality domains and use documented
  boundary/pairwise coverage only for genuinely large spaces.
- Add a continuous business-event cursor across controlled loads, navigations,
  and actions so every explicit business push is classified against its
  trigger context, count, and order, exposing duplicate, premature, delayed,
  wrong-order, and wrong-context events without invented negative journeys.
- Make ordinary form, authentication, sign-up, lead, and account gates required
  journey steps; complete safe synthetic-data submissions by default on
  confirmed non-production environments and hand only protected boundaries to
  the analyst.
- Aggregate one plan-ordered verdict per event across all of its cases, grouping
  homogeneous successes while preserving every distinct failed variant or
  placement.
- Expand the utility-first recette from analytics-centric checks to complete
  client-side analytics and media-tag acceptance while preserving the exact
  approved north star.
- Add multi-vendor destination/network evidence, multiple web containers and
  destinations, native/direct signal sources, trigger groups, exceptions, tag
  sequencing, and Custom HTML/JavaScript failure evidence.
- Add Advanced Consent Mode v2 contracts, conditional and responsive
  scenarios, safe cross-field rules, redacted sensitive-data scanning,
  SPA/cross-domain/cookie/iframe/dataLayer/debug/limit checks, and optional
  previous-run regression comparison.
- Reconcile decoded destination IDs, vendor event names, and tested values to
  raw browser-request paths, including quoted literal vendor keys; recompute
  trigger, consent, business-rule,
  privacy, and client-check claims; and reject omitted applicable verdicts or
  provenance-free evidence.
- Require independent base-layer verdicts, client-web container inventory,
  safe action-value metadata, strict action chronology, canonical
  evidence-kind/source binding, and dedicated analyst-approval evidence.
- Refuse workbook generation while unallowlisted sensitive content remains in
  normalized evidence and include request headers/catalogue metadata in
  privacy safeguards.
- Expand the validated workbook from 10 to 17 sheets. Keep schema version 2,
  with re-normalization required for legacy rows missing the new strict fields.
- Keep server-side GTM explicitly out of scope.

## [v1.0.0](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v1.0.0)

- Consolidate the optimization handoff into the approved utility-first north star.
- Cover tracking-plan ingestion, journey inference, live GTM Preview evidence,
  plan-ordered verdicts, coverage control, and validated detailed workbooks.
- Adopt semantic `v` versioning for releases and reject calendar-date versions.

## [2026.7.11 (legacy calendar release)](https://github.com/haiqigeng/gtm-preview-recette/releases/tag/v2026.7.11)

- Establish the first-maturity orientation, execution, and judgement architecture.
- Add deterministic browser-surface, consent-readiness, action-boundary, and event-settling rules.
- Add synthetic-data and optional-marketing handling for authorised test journeys.
- Require canonical tracking-plan/dataLayer/tag comparison rows in strict mode.
- Make the concise Validation Matrix the first worksheet.
- Add CI, release packaging, release validation, and expanded regression tests.
