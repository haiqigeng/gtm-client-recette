# v6 Regression and Downgrade Audit

> Historical v6 working audit. The active comparison is
> [v7 Regression and Downgrade Audit](v7-regression-downgrade-audit.md).

Status: v6.0.1 post-run optimization audit, 2026-08-24.

## Executive result

No deterministic quality downgrade is currently known. v6 changes the browser-control
path, not the acceptance standard: source, accumulated GTM state, Variables, concerned
tag configuration/mapping/firing/runtime, decoded requests, reality, chronology, safety,
confidence and scenario coverage remain distinct.

The unresolved risk is external integration. The new default must still pass a clean
live Playwright MCP and Tag Assistant pilot before release; controlled tests are not
presented as evidence of live latency.

## Historical architecture comparison

| Version | Relevant behavior | Main risk or limitation |
| --- | --- | --- |
| v3.0.0 | Reactive browser execution with broad layer coverage. | Full preflight, case/tag inventory and multiple ledgers made correctness expensive but could still begin browser work sooner than later designs. |
| v3.1.0 | Stronger semantic, coverage and closure rules. | All-event frozen coverage and staged ledgers moved too much work before the first inspection. |
| v3.2.0 | Added event-local lifecycle certification. | Retained the heavy staged control model and real runs could stall before an event. |
| v5.0.0 | Replaced fixed stages with typed claims and vertical judgement. | Initial plan/source/cross-layer contracts were incomplete. |
| v5.1.0 | Corrected workbook intake, source authority and per-field layer projection. | Browser handoff remained split across separate action and Preview operations. |
| v5.2.0 | Added API-Call-first source and smaller persisted handshake. | Existing-window control and agent-selected staging still produced repeated loads and long Preview handshakes in real use. |
| v6.0.0 | Playwright-managed Edge, frozen single action and one `complete` pass. | The action card did not yet provide a complete acquisition contract; real agents still assembled Preview evidence manually and could delay feedback. |
| v6.0.1 post-run working tree | Adds a prepared-session cursor/consent boundary, plan-derived capture specification, one bounded Tag Assistant collector, state-to-technical causal joins and compact persisted feedback. | Live Tag Assistant DOM extraction remains the release-pilot risk; incomplete extraction blocks rather than triggering a reload. |

The tagged historical suites are rerun separately during final validation. They prove
their own contracts; current adversarial tests prove that v6 retains the intended
behavior while replacing the slow control path.

Runtime size below uses one reproducible metric for every version: physical lines in all
`.py` and `.js` files under `scripts/`.

| Version | Runtime files/lines | Own tagged test result |
| --- | ---: | ---: |
| v3.0.0 | 32 / 17,596 | 189 pass |
| v3.1.0 | 41 / 23,187 | 255 pass |
| v5.0.0 | 28 / 11,150 | 76 pass |
| v5.1.0 | 28 / 12,541 | 88 pass |
| v5.2.0 | 28 / 13,063 | 95 pass |
| v6.0.1 post-run working tree | 29 / 15,434 | 135 pass + 4 subtests |

The optimized v6 tree remains about 13% smaller than v3.0 and 34% smaller than v3.1 by
this repository-level runtime line count. The increase over v5.2 is concentrated in the
enforceable Playwright/action contract, loss-aware intake, deterministic cross-layer
judgement, compact output and generalized regressions. One dependency-free browser helper
was added for bounded Tag Assistant acquisition; no Python dependency, browser family,
service or ledger was added. The obsolete pre-Preview pulse and duplicate model build
remain removed.

## Regression matrix

| Capability at risk | v6 result | Why quality is not reduced |
| --- | --- | --- |
| Exact source push | Preserved | Expanded API Call remains the ordinary source authority; accumulated state cannot substitute. |
| Accumulated Data Layer tab | Preserved | It remains an independent GTM-state check rather than being removed. |
| Variables and tag mapping | Preserved | Every destination-applicable planned field receives separate resolved-variable and effective-mapping obligations. |
| Runtime and request | Preserved | Tag runtime and decoded logical request/destination remain required when applicable. |
| Tag inventory/firing | Preserved | Only concerned fired and relevant not-fired tags are read, but completeness is still required. |
| Intervening weird events | Preserved | Continuous deltas start at the prior committed boundary. Between-action rows remain timestamp-unbound, amend the prior event immediately and cannot be replaced with stale session history. |
| Duplicates and missing sends | Preserved | Complete occurrence and logical-hit windows retain exact counts and non-send proof; direct/Preview reconciliation is one to one so surplus identical calls remain visible. |
| Dead page/business mismatch | Preserved | Reality remains an independent domain and can fail a coherent technical chain. |
| Language and finite enums | Preserved | Values are strict within each selected scenario and every reachable material finite value is required. |
| Shipping/payment dependencies | Preserved | Reachable dependent combinations remain exhaustive without a global Cartesian product. |
| High-cardinality products | Preserved | Sampling is by observed behavior signature, with expansion after anomalies or new branches. |
| Forms, consent and acquisition | Preserved conditionally | Ordinary interactions run; protected credentials/CAPTCHA/payment use same-session handoff. |
| Per-event detail | Preserved and clearer | Every applicable layer retains status, reason, expected/observed, check-next and evidence. |
| Failure attribution | Improved | Browser/control mistakes are `BLOCKED`, separate from client implementation `FAIL`. |
| State-only Core correlation | Improved | Planned fields identify the source API Call; accumulated state/Variables stay on that row while declared delivery or Trigger Group tag/runtime rows join causally until the next unrelated business event. |
| Scenario identity | Improved | A coverage label can annotate an action but cannot duplicate that action into a second judged scenario. |

## New-control-path risks reviewed

### Managed profile instead of an existing everyday window

The managed persistent Edge profile standardizes tabs, tools and identity and removes
extension/CDP attachment ambiguity. It may require a one-time Tag Assistant sign-in.
Existing-window attachment remains available only when explicitly selected; the skill
does not silently switch paths.

### One interaction per completion

This increases the number of deterministic `complete` calls compared with batching
several user interactions, but it protects chronology and immediate feedback. One
interaction can still satisfy multiple co-occurring claims and all technical rows from
that action are read in one Preview pass.

### API Call as normal source

This removes the routine recorder-install navigation. It is accepted only when the API
Call is fully expanded, attributable and complete. Partial or unavailable source remains
`BLOCKED`; document-start capture is still used when a claim needs stronger invocation
evidence.

### Runtime-discovered GA4 identity

Concise category scope no longer becomes a fake literal destination. Runtime discovery
passes only on complete causal tag/request evidence and reports the concrete identities.
Exact plan-declared tag or destination IDs remain strict.

### Operation guard

Target navigation, reload and approved context reset remain guarded. When supplied,
existing counters now also enforce zero repeated full preflights, one Preview summary
pass and one semantic retry at most. A violation preserves evidence, blocks confidence
and never starts an automatic clean repeat.

### Prepared-session boundary and user-owned consent

The first action cannot open without a Preview cursor and explicit ordinary, variant or
not-applicable consent context. This is a small control object, not a setup evidence
ledger. The user handles ordinary CMP preparation; the agent does not spend browser time
probing vendor-specific consent selectors. If Preview is explicitly unavailable, a null
epoch at index zero is accepted and only Preview-dependent claims block.

### Bounded Tag Assistant collector

The new helper performs one post-cursor event-list read and selected panel/tag reads in a
five-second window. It explicitly opens API Call, scores state anchors from that panel
only, reads Tags alone on ordinary technical rows, preserves unplanned business API calls,
and resolves current-event tags from a declared category when exact IDs are absent. A
missing Preview index or panel blocks completion. It never navigates, reloads, opens a
tab, installs a recorder or switches browser. Raw panel output must still be normalized
to the canonical schema; partial output remains `BLOCKED`. This removes manual multi-call
discovery without claiming that unparsed text is proof.

### Capability contract instead of an exact version pin

The runtime is accepted from observed capabilities: provider, managed profile, headed
Edge channel and the required action/network/Preview surfaces. Package version and
self-check metadata are diagnostic, not ordinary startup gates; an explicitly failed
self-check still blocks. If Preview is unavailable, one already-authorized action can be
completed with the dependent layers marked `BLOCKED`, without an automatic reload or a
slow fallback search. This avoids both version churn and false client failures.

## Downgrades deliberately accepted

- The normal path does not reuse an arbitrary already-open everyday browser window.
  This trades one-time profile setup for reproducible control and much lower attachment
  ambiguity.
- Firefox is not supported by default. It adds no value to the owner's present GTM
  Preview use case.
- Automatic browser/runtime fallback is removed. Explicit failure is preferable to an
  18-minute recovery search that may inspect the wrong session.

These do not weaken measurement acceptance quality. They narrow unsupported control
paths.

## Release conclusion

Deterministic deployment risk is low; live control risk remains medium until the required
pilot passes. Release is safe only when the pilot proves one Core action and one ordinary
event with one Preview pass, complete mandatory layers, no extra reload/restart or ad-hoc
evidence path, and detailed feedback inside the release thresholds.
