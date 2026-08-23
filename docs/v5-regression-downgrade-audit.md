# v5 Regression and Downgrade Audit

Status: v5.2.0 release audit, 2026-08-24.

## Executive result

No known deterministic accuracy regression remains against the retained v3.0.0,
v3.1.0, v5.0.0, or v5.1.0 contracts. v5.2 removes repeated browser handshakes, recorder-
driven reloads and stale-evidence rebinding while preserving scenario depth, continuous
anomaly analysis, cross-layer plan comparison, business-reality checks, protected
journeys, and mandatory per-event layer feedback.

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
| v5.2.0 | 28 / 12,004 | 95 pass | persisted handshake, API-Call-first source, exact/causal Preview join and scoped evidence |

The v5.2 runtime is about 27% smaller than v3.0 and 45% smaller than v3.1 by this
repository-level line count. Its increase over v5.1 is concentrated in enforceable phase
boundaries, stale-evidence rejection, causal Preview reconciliation, and generalized
regressions. No extra public command, ledger, browser implementation, service, or
dependency was added; the unused DOM evidence adapter was removed.

## Controlled latency

| Measure | v5.2 result | Interpretation |
| --- | ---: | --- |
| 100 events / 2,000 requirements compile | 0.08 s, one isolated test | Plan size creates no future cases or evidence. |
| Direct representative multi-sheet workbook intake | 2.515 s median, three runs | The unmodified supported layout compiles directly. |
| Three-event action/feedback cluster | 0.61 s, one isolated test | Uses one capability capture, one binding, and one Preview batch. |
| Unsupported Preview capability fast-fail | 0.21 s, one isolated test | Only dependent GTM claims block; source inspection proceeds. |

The tagged v5.0 compiler rejected that supported two-block workbook layout after about
2.8 seconds. v5.2 retains v5.1's direct acceptance at a measured 2.515-second
median; no custom normalizer or event-count-specific branch is involved. These timings
exclude real browser UI latency and are architecture regressions, not a live SLA.

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
| Broad scope prose became a literal runtime identity | Resolve it to exact event-level planned tags/destinations; fail intake when the declared identity is absent. | Necessary fast-fail; no vendor or workbook-specific branch. |
| Core inspection generated repeated reloads | Reuse an attributable current load or perform one required load; require a named reason for the same event/scenario again. | Necessary speed rule that leaves distinct scenarios unrestricted. |
| Capability/binding/health/Preview were repeated in every phase | Enforce one initial handshake, lightweight later starts, current commit deltas, and Preview-only sync. | Removes measured duplicate work; no new state system. |
| Old page/health evidence was attached to a later action | Reject pre-action timestamps and retain unbound between-action deltas for anomaly analysis. | Necessary false-attribution fix. |
| Tags fired on a following Trigger Group | Keep exact API Call/Data Layer/Variables on the source row and join only same-action technical follow-up rows for tag/runtime evidence. | Necessary causal correction; stops at the next business event. |
| Background request privacy fields failed the event | Scope findings to the action and concerned logical send while preserving redaction and in-scope failures. | Necessary false-failure correction; no privacy weakening. |
| Cumulative telemetry and repeated evidence were double-counted | Use latest cumulative counters and unique evidence digests. | Small reporting correction with no browser work. |

## Capability downgrade matrix

| Capability | v5.2 result |
| --- | --- |
| Plan order/provenance/types | Preserved; intake is more direct and loss-aware. |
| Exact API Call/call-time source versus accumulated state | Improved separation; no source laundering or mandatory recorder reload. |
| GTM event, Variables, tags, mapping, runtime | Preserved as distinct rows and expanded per planned field. |
| Browser delivery and destination | Preserved; GA4 batches/items and Ads identity are corrected. |
| Missing/duplicate/interjected chronology | Preserved across actions and through API Call fallback. |
| Dead page and business incoherence | Preserved as independent overall failures. |
| Languages and finite values | Preserved; values are strict inside their selected scenarios. |
| Shipping/payment dependencies | Preserved through reachable dependent combinations. |
| High-cardinality products/content | Preserved through behavior-signature representatives and adaptive expansion. |
| Plan-omitted live values | Preserved as visible gaps that expand coverage when material. |
| Forms, consent, acquisition, CAPTCHA/auth/payment | Preserved; ordinary journeys run and protected gates use same-session handoff. |
| Privacy and report safety | Strengthened; central redaction remains and event verdicts use only action/concerned-request findings. |
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

v5.2 is a quality-preserving correction and is safer and leaner in browser work than
v5.1. It does
not need a generic “slow but safe” mode: complex funnels already activate the same proof
rules and more scenarios when evidence requires them. Run a fresh live pilot and reject
the deployment only if measured browser attachment, Preview extraction, or first-event
feedback still performs global setup, opens replacement tabs, or stalls indefinitely.
