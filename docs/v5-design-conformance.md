# v5 Design Conformance

Status: v5.1.0 release review, 2026-08-23.

## Decision

The implementation conforms to the accepted target architecture in the deterministic
runtime, capture contracts, judgement, output, and controlled performance tests. It is a
general redesign correction, not a branch for one client, workbook, event count, or run.

The release is suitable for clean personal installation. A fresh end-to-end run in the
owner's existing Chromium and Tag Assistant session remains the live acceptance gate;
local fixtures do not prove browser-control latency or panel availability.

## North star

Maximize trustworthy findings per expensive browser interaction. The unit of judgement
is one typed measurement claim in one material real-world scenario. An event cannot pass
only because a tag fired or because empty technical surfaces agree: page reality,
business state, source, GTM decisions, delivery, surrounding behavior, evidence quality,
and scenario coverage must tell one attributable story.

## Default applicable evidence chain

For an ordinary planned dataLayer event with a browser-sending tag, one captured action
supports these separate operational checks:

1. page/action and business reality;
2. document-start call-time dataLayer capture, or a complete expanded Tag Assistant API
   Call fallback;
3. Tag Assistant accumulated Data Layer state;
4. Tag Assistant Variables;
5. complete concerned fired/not-fired tag inventory;
6. concerned tag configuration, effective mapping, firing count, and runtime payload;
7. decoded browser request, destination, and transport result;
8. continuous surrounding source/network behavior;
9. safety, evidence confidence, and scenario coverage.

These are applicable proof surfaces, not nine sequential setup stages. Source-only or
state-only requirements do not receive invented delivery obligations. Consent,
acquisition, forms, trigger/sequence evidence, media, and protected handoffs activate
only when relevant.

## Design-to-implementation crosswalk

| Contract | Implementation | Verification |
| --- | --- | --- |
| Direct, loss-aware plan intake | One compiler reads JSON, YAML, delimited files, ordinary tabular XLSX, event-metadata/variable-table XLSX, and supported handoffs. It retains source coordinates, typed values, contiguous fill-down identity, ignored-row diagnostics, and event-local errors. | Flat and two-block workbooks, code-section exclusion, merged/fill-down rows, orphan rows, duplicate IDs, types, enums, and malformed later events are tested. |
| Correct source authority | Document-start invocation capture is primary. Fully expanded Preview API Call arguments are the fallback. Accumulated Data Layer state is a separate GTM check and cannot prove one push. | Late snapshot laundering fails; API Call fallback passes when complete and still exposes interjected events. |
| Plan-first cross-layer projection | Every destination-applicable planned field creates independent source, Data Layer state, Variables, effective mapping, runtime, and request obligations. Object/settings and automatic mapping count only when proved. | A twelve-field plan with a one-field tag creates eleven GTM, eleven runtime, and eleven request failures. |
| Source/delivery identity separation | State-only core fields have no fabricated source event. Explicit forwarding can target a real delivery event such as `page_view`. | Source-only/state-only tests and direct workbook compilation prevent a fictitious same-named vendor request. |
| One causal model | Actions, documents, frames, Preview epochs, source calls, tags, logical sends, transport attempts, and completeness windows join in one replay-derived model. | Identity conflicts, redirects/retries, request reuse, API fallback, and action-local completeness are tested. |
| Legitimate navigation | The old document remains the before-state; an explicitly rebound new document owns post-navigation occurrence evidence. | A proved rebind passes; mixed or foreign post-action identity remains blocked. |
| Human-like anomaly and reality checks | Duplicates, absence, interjection, premature/delayed events, state contamination, stale product/cart data, empty populated carts, dead pages, failed forms, media inconsistency, and repeated purchases are first-class findings. | Quality, ecommerce, media, mutation, and cross-event tests pass. |
| Scenario depth without brute force | Finite values are exhausted, dependent values are tested in reachable states, high-cardinality members are sampled by behavior signature, and live plan gaps reopen coverage. | Language, shipping dependency, product signatures, omitted values, per-scenario strictness, and coverage reopening are tested. |
| Fast vertical workflow | `init` creates no future cases/evidence. One handshake and persistent collectors feed `begin`, `commit`, one targeted Preview sync, and immediate feedback. Static configuration alone is cacheable under exact identity. | Large-plan, first-feedback, three-event cluster, idempotent retry, and capability-fast-fail contracts pass. |
| Mandatory actionable output | `commit` emits a non-certifying layer pulse. Closed events render scenario/domain summaries and every applicable operational layer with status, expected, observed, reason, check-next, and evidence. | Renderer, telemetry, freeze, XLSX, and non-pass detail tests pass. |
| One verdict authority | Typed capture paths create observations; deterministic replay owns status. Analyst reasoning may only add evidenced `FAIL` or `REVIEW`. | Invalid controls fail before persistence; no public pass/verdict setter exists. |

## Quality-preserving speed decisions

- Compile and attach concurrently where the control surface permits.
- Localize later-event compile errors; only the selected event must be executable.
- Install persistent source/network observers once and consume deltas.
- Read only new Preview events, current planned Variables, and concerned/suspicious tags.
- Reuse only static configuration under exact container/workspace identity.
- Build coverage just in time and reuse safe journey prefixes.
- Retry one transient panel read; block only its dependent claims rather than restarting.
- Render from captured evidence without another browser pass.

Controlled results on the release machine were approximately 63 ms median for a
100-event/2,000-requirement synthetic compile, 220 ms median for a synthetic
init-to-canonical-feedback path, and 2.9 seconds from direct multi-sheet workbook intake
to the first provisional inspected-layer pulse. These are local architecture checks, not
a promise for website or browser UI latency.

## Machinery deliberately absent

- fixed 19-layer rows or whole-plan scenario/tag scaffolds;
- result/session/coverage/runtime ledger families;
- global tag/container or historical-domain inventories;
- Firefox or a cross-browser abstraction for this personal skill;
- databases, workers, services, dashboards, or a telemetry platform;
- private Tag Assistant APIs, container injection, or replacement-browser recovery;
- arbitrary scenario caps, exhaustive product browsing, or Cartesian combinations;
- one model call per field/layer or caching of action-time evidence;
- client/run-specific paths, values, counts, selectors, or repair branches.

## Conformance verdict

| Area | Verdict |
| --- | --- |
| Architecture and authority | CONFORMS |
| Plan normalization | CONFORMS |
| Inspection depth and per-field comparison | CONFORMS |
| Scenario variability and anomaly detection | CONFORMS |
| Controlled startup/performance | CONFORMS |
| Output and repository hygiene | CONFORMS |
| Fresh existing-browser end-to-end pilot | PENDING |

No known deterministic blocker remains. Deployment confidence becomes complete only
after a fresh live pilot confirms the browser-control and Tag Assistant extraction path.
