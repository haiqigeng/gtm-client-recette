# v7 Design Conformance

Status: release candidate review, 2026-08-25.

## Result

v7 conforms to the intended personal expert-skill design: inspect one real interaction
quickly, preserve the full causal stream, compare every applicable planned field across
the actual delivery chain, and give useful feedback before moving to the next event.

The design is general. It contains no client name, site URL, container, destination,
event count, workbook path, prior-run evidence, or run-repair branch.

## North star

Maximize trustworthy findings per expensive browser interaction. A passing source push
or firing tag is not enough: the page must make business sense, the exact source message,
GTM mapping/runtime, and browser request must agree with the tracking plan, and the
surrounding sequence must not contain unexplained behavior.

## Default proof contract

Every tested event always receives these five output rows, in this order:

| Layer | Default check | Non-applicable case |
| --- | --- | --- |
| Page/action reality | Reachability, intended state, action outcome, and visible business truth | Never omitted; an unavailable page is `BLOCKED`, a dead/wrong page is `FAIL` |
| Data Layer API Call | Exact selected `dataLayer.push(...)`/`gtag(...)`, occurrence, planned paths, types, values, and interjected business calls | `NOT_APPLICABLE` only when the accepted requirement has no client source obligation |
| GTM Tags | Concerned inventory, effective mapping, firing count, and event-time runtime values | `NOT_APPLICABLE` for a true source-only requirement |
| Browser request | Logical hit, destination, planned parameters, transport, duplicate/retry behavior | `NOT_APPLICABLE` when the plan creates no browser-delivery obligation |
| Surrounding behavior | Missing, duplicate, premature, delayed, interjected, stale, or implausible chronology | Never omitted |

The five rows are a reporting contract, not five serial browser phases. One bounded
capture supplies all applicable evidence.

For every destination-applicable field, the tracking plan remains the baseline:

`planned field -> exact API Call -> effective tag mapping -> tag runtime -> browser request`

A field may legitimately differ between language, product, shipping, or payment
scenarios. Inside one action, however, the observed value must remain coherent through
the chain. Complete tag detail containing one of twelve planned fields fails the eleven
missing fields; empty downstream payloads cannot pass merely because they match an empty
source when page reality proves data should exist.

## Conditional diagnostics

The accumulated Tag Assistant **Data Layer** tab and **Variables** tab are not default
proof layers. They activate only for explicit `state_path`/`resolved_path` requirements
or a precise stale-state/mapping ambiguity. A call-time recorder, consent details,
acquisition, forms, media, and protected-gate handling are likewise conditional.

Evidence confidence, scenario coverage, and data safety remain automatic gates, but are
displayed only when non-pass. Removing them from the normal table does not remove their
judgement logic.

## Operating sequence

1. Ask one compact intake and announce the browser-preparation responsibility.
2. After `ready`, open one blank headed Playwright-managed Edge window immediately.
3. Normalize the plan locally while the user prepares login, Preview, target tabs, and
   ordinary consent.
4. Freeze one setup cursor and capability boundary; do not ingest setup loads as Core.
5. Select one material scenario just in time and execute its frozen action once.
6. Run the returned paste-ready callback once. It collects page/binding, every
   post-cursor event, exact business API Calls, causally relevant Tags rows, and a safe
   network fallback in a five-second bound.
7. Prefer the native action-bounded Playwright request delta when available.
8. Call `complete` once and show the five-layer feedback before the next action.
9. Expand only the affected scenario tree when live evidence reveals a material value,
   boundary, exception, or behavior signature.

There is no cleanup reload, automatic retest, whole-container inventory, historical-
domain scan, all-scenario startup scaffold, or manual panel-to-JSON handoff.

## Implementation crosswalk

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Start useful work early | Browser preparation overlaps local plan compilation; only one setup boundary precedes `next` | Workflow regressions and one-load guards |
| Lossless plan intake | One compiler handles supported JSON/YAML/tabular/XLSX structures and localizes later-event errors | Compiler/workbook tests plus real 21-event workbook benchmark |
| Exact source authority | Directly parsed fully expanded API Call; accumulated state cannot substitute | Collector browser fixture and source-authority tests |
| Fast Preview handshake | One directly evaluable, dependency-free, five-second collector with one selector fallback | JavaScript syntax and real Chromium DOM test |
| No irrelevant GTM traversal | Tags open only on the planned occurrence and causal technical follow-ups | Browser fixture verifies initial lifecycle and later unrelated business rows are skipped |
| Full field coherence | Independent plan claims plus API-to-runtime/request coherence judgement | Missing-field and dynamic-value mismatch tests |
| Weird-event detection | All post-cursor event names and every business API Call remain chronological | Interjection, duplicate, missing, stale-cart/item, and causal-boundary tests |
| Variable scenarios | Finite/reachable values are exhausted; high cardinality samples by behavior signature and expands on differences | Coverage and plan-gap tests |
| Partial-safe execution | Missing Preview/page/network evidence completes with dependent `BLOCKED` rows | Partial-bundle completion regressions |
| Immediate useful feedback | Deterministic renderer always emits all five rows and detailed non-pass reasons | Markdown, persistence, JSON, and XLSX tests |

## Measured deterministic evidence

- Current suite: 139 tests passed.
- Browser helper suite: passed in headless Chromium, including exact API Call parsing,
  tag Names/Values, causal technical rows, and interjected events.
- Large real workbook: 21 event groups, 167 requirements, 875 claims compiled in 2.551
  seconds on this machine; default state/Variables claims are zero.
- Ruff lint and formatting: passed.
- JavaScript syntax: passed.
- Vulture at 80% confidence: no dead-code findings.
- Release-tree validation: passed for `v7.0.0`.

These results validate local design and browser-DOM behavior. They do not fabricate a
third-party live Tag Assistant latency result.

## Conformance verdict

| Area | Verdict |
| --- | --- |
| Five-layer event contract | Conforms |
| Tracking-plan-first field comparison | Conforms |
| Human-like chronology/business judgement | Conforms |
| Material scenario variability | Conforms |
| Partial-safe immediate feedback | Conforms |
| Speed-oriented browser handshake | Conforms in deterministic/browser fixture tests |
| Generality and run-residue hygiene | Conforms |
| Live client/environment behavior | Must be measured in the next real recette |
