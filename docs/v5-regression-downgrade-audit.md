# v5 Regression and Downgrade Audit

Status: v5.1.0 release audit, 2026-08-23.

## Executive result

No known deterministic accuracy regression remains against the retained v3.0.0,
v3.1.0, or v5.0.0 contracts. v5.1 removes startup gates and fixes false authority and
cross-layer gaps while preserving scenario depth, continuous anomaly analysis,
business-reality checks, protected journeys, and mandatory per-event layer feedback.

The remaining deployment risk is external: the release was not rerun end to end in the
owner's live Chromium/Tag Assistant session after these changes. Controlled latency is
evidence about the architecture, not a substitute for that pilot.

## Reproducible historical comparison

The tagged source trees were extracted without changing the working tree and their own
test suites were run successfully.

| Version | Repository runtime files/lines | Test result | Startup architecture |
| --- | ---: | ---: | --- |
| v3.0.0 | 32 / 16,472 | 189 pass | preflight approval, full case/tag inventory, fixed layer scaffolds, results plus session ledger |
| v3.1.0 | 41 / 21,712 | 255 pass | all-event frozen coverage, normalized results, Preview/session ledger, staged operator closure |
| v5.0.0 | 28 / 10,164 | 76 pass | vertical workflow, but incomplete direct workbook/API Call/cross-layer handling |
| v5.1.0 | 28 / 11,512 | 88 pass | vertical workflow with corrected intake and evidence contracts |

The v5.1 runtime is about 30% smaller than v3.0 and 47% smaller than v3.1 by this
repository-level line count. Its increase over v5.0 is concentrated in general workbook
intake, action-local correlation, and per-field cross-surface judgement. No extra public
command, ledger, browser implementation, service, or dependency was added.

## Controlled latency

| Measure | v5.1 result | Interpretation |
| --- | ---: | --- |
| 100 events / 2,000 requirements compile | 63.2 ms median; 66.8 ms max, five runs | Plan size creates no future cases or evidence. |
| Synthetic init-to-canonical-feedback | 219.9 ms median; 222.6 ms max, ten runs | Deterministic replay and output are not a minutes-long bottleneck. |
| Direct representative multi-sheet workbook intake | 2.77 s median, three runs | The unmodified supported layout compiles directly. |
| Same workbook start to first provisional inspected-layer pulse | 2.88 s, one controlled run | Includes intake, begin, commit, 79 current-event claims, and layer pulse; excludes real browser UI time. |
| Three-event cluster | Under five-second test budget with one capability capture, one binding, and one Preview batch | Shared collection and targeted batching remain intact. |

The tagged v5.0 compiler rejected that supported two-block workbook layout after about
2.8 seconds. v5.1 accepts it directly; no custom normalizer or event-count-specific
branch is involved.

## v5 field-feedback problems and general resolutions

| Observed class | General resolution | Patch/overengineering review |
| --- | --- | --- |
| Raw workbook required custom normalization | Recognize the common event-metadata plus variable-table structure, typed headers, stop markers, and code examples in the single compiler. | Necessary intake fix; no client names, sheet counts, or paths. |
| Code examples became requirements | Reject code/script-shaped field paths and stop at explicit code/image sections. | Necessary false-requirement prevention. |
| A source-only message acquired a vendor delivery expectation | Separate source event, state-only mode, forwarding requirement, and delivery event identity. | Necessary semantic model correction. |
| Data Layer tab was treated as the API Call | Only call-time recorder or complete expanded API Call is source authority; accumulated state remains a separate GTM row. | Necessary non-substitution rule. |
| One tag field could appear coherent against a much wider plan | Project every destination-applicable plan field to state, Variables, effective mapping, runtime, and request; fail each absent field when complete. | Necessary acceptance baseline; no count heuristic. |
| Missing concerned-tag details were not exposed | Require complete fired/relevant-not-fired inventory and targeted tag details for current plan fields. | Necessary; scoped deep reads avoid global scans. |
| Evidence completeness leaked between actions | Bind source, Preview, and network completeness to each action. | Necessary false-pass/false-fail prevention. |
| A normal reload caused a document conflict | Exclude only the old before-page from occurrence identity after an explicit new-document rebind. | Narrow general fix; mixed post-action documents still block. |
| API fallback lost weird events | Feed authoritative expanded API Calls into the same continuous anomaly stream. | Necessary quality preservation. |
| Coverage stayed closed after another action | Require all executed actions in the latest coverage decision and reopen on new work. | Necessary stale-coverage prevention. |
| Immediate output hid layer state | Commit emits provisional domain statuses/counts; final event feedback includes every applicable operational row. | Output-only reuse of existing evidence; no browser cost. |
| Retries duplicated stream state | Exact commit replay returns the existing capture/commit/pulse records; changed replay is rejected. | Necessary recovery fix without another ledger. |

## Capability downgrade matrix

| Capability | v5.1 result |
| --- | --- |
| Plan order/provenance/types | Preserved; intake is more direct and loss-aware. |
| Call-time source versus accumulated state | Improved separation; no source laundering. |
| GTM event, Variables, tags, mapping, runtime | Preserved as distinct rows and expanded per planned field. |
| Browser delivery and destination | Preserved; GA4 batches/items and Ads identity are corrected. |
| Missing/duplicate/interjected chronology | Preserved across actions and through API Call fallback. |
| Dead page and business incoherence | Preserved as independent overall failures. |
| Languages and finite values | Preserved; values are strict inside their selected scenarios. |
| Shipping/payment dependencies | Preserved through reachable dependent combinations. |
| High-cardinality products/content | Preserved through behavior-signature representatives and adaptive expansion. |
| Plan-omitted live values | Preserved as visible gaps that expand coverage when material. |
| Forms, consent, acquisition, CAPTCHA/auth/payment | Preserved; ordinary journeys run and protected gates use same-session handoff. |
| Privacy and report safety | Preserved; central redaction and formula-safe output remain. Runtime screenshot persistence was removed because it had no caller. |
| Per-event feedback | Strengthened: scenario plus every applicable layer/check, status, expected, observed, reason, check-next, and evidence. |
| Final output | Preserved as one frozen canonical JSON/Markdown/XLSX/CSV projection. |

## Regression risks reviewed

- **More claims per field:** required to expose missing mapping/runtime/request values;
  they reuse one action and one Preview read and therefore add deterministic comparisons,
  not browser interactions.
- **API Call fallback:** accepted only when fully expanded and complete; partial panels
  block rather than pass.
- **Preview batching:** retained only while action/document/event/tag attribution is
  unambiguous; navigation or anomaly triggers an earlier sync.
- **Navigation tolerance:** applies only to the before-page after an explicit rebind;
  foreign post-action evidence is still blocked.
- **Dynamic scenarios:** no arbitrary cap or full Cartesian product was introduced.
- **Static cache:** configuration only; runtime, occurrence, consent, requests, and page
  outcomes remain action-specific.
- **Later anomaly revisions:** earlier event feedback may be amended, preserving the
  continuous-session truth rather than freezing an incorrect pass.

## Release conclusion

v5.1 is a quality-preserving correction and is safer than v5.0 for deployment. It does
not need a generic “slow but safe” mode: complex funnels already activate the same proof
rules and more scenarios when evidence requires them. Run a fresh live pilot and reject
the deployment only if measured browser attachment, Preview extraction, or first-event
feedback still performs global setup, opens replacement tabs, or stalls indefinitely.
