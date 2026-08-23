# v5 Design Conformance

Status: v5.2.0 release review, 2026-08-24.

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
2. complete expanded Tag Assistant API Call, or conditional proven call-time dataLayer
   capture when stronger invocation-time evidence is necessary;
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
| Correct source authority | Fully expanded Preview API Call arguments are the normal exact-message source. Document-start invocation capture is conditional stronger evidence. Accumulated Data Layer state remains a separate GTM check. | Late snapshot laundering fails; complete API Call evidence passes and still exposes interjected events. |
| Plan-first cross-layer projection | Every destination-applicable planned field creates independent source, Data Layer state, Variables, effective mapping, runtime, and request obligations. Object/settings and automatic mapping count only when proved. | A twelve-field plan with a one-field tag creates eleven GTM, eleven runtime, and eleven request failures. |
| Source/delivery identity separation | State-only core fields have no fabricated source event. Explicit forwarding can target a real delivery event such as `page_view`. | Source-only/state-only tests and direct workbook compilation prevent a fictitious same-named vendor request. |
| One causal model | Actions, documents, frames, Preview epochs, source calls, tags, logical sends, transport attempts, and completeness windows join in one replay-derived model. | Identity conflicts, redirects/retries, request reuse, API fallback, and action-local completeness are tested. |
| Legitimate navigation | The old document remains the before-state; an explicitly rebound new document owns post-navigation occurrence evidence. | A proved rebind passes; mixed or foreign post-action identity remains blocked. |
| Human-like anomaly and reality checks | Duplicates, absence, interjection, premature/delayed events, state contamination, stale product/cart data, empty populated carts, dead pages, failed forms, media inconsistency, and repeated purchases are first-class findings. | Quality, ecommerce, media, mutation, and cross-event tests pass. |
| Scenario depth without brute force | Finite values are exhausted, dependent values are tested in reachable states, high-cardinality members are sampled by behavior signature, and live plan gaps reopen coverage. | Language, shipping dependency, product signatures, omitted values, per-scenario strictness, and coverage reopening are tested. |
| Fast vertical workflow | `init` creates no future cases/evidence. One persisted handshake, zero/one needed initial Core load, lightweight later starts, current commit deltas and one targeted Preview-only sync lead to feedback. Same-scenario repeats require a reason. | Large-plan, first-feedback, cluster, duplicate-action, phase-bundle, stale-evidence, idempotent-retry, and capability-fast-fail contracts pass. |
| Exact/causal Preview reconciliation | API Call, accumulated Data Layer and Variables stay on the exact selected row. Concerned tag firing/configuration/runtime may join same-action technical follow-up rows until the next business event. | A delayed Trigger Group proves the intended tag layers without replacing exact-message fields or crossing a business boundary. |
| Mandatory actionable output | `commit` emits every provisional operational row/status in a non-certifying pulse. Closed events render scenario/domain summaries and every applicable operational layer with status, expected, observed, reason, check-next, and evidence. | Renderer, telemetry, freeze, XLSX, and non-pass detail tests pass. |
| Request-scoped safety and transport | Privacy findings apply to the action and concerned logical send; unrelated requests remain redacted but do not contaminate the event. Contradictory aborted/success response state is reviewable. | Unrelated sensitive session noise passes the event safety row, a sensitive concerned GA4 send fails, and aborted plus HTTP 204 yields `REVIEW`. |
| One verdict authority | Typed capture paths create observations; deterministic replay owns status. Analyst reasoning may only add evidenced `FAIL` or `REVIEW`. | Invalid controls fail before persistence; no public pass/verdict setter exists. |

## Quality-preserving speed decisions

- Compile and attach concurrently where the control surface permits.
- Localize later-event compile errors; only the selected event must be executable.
- Use Tag Assistant API Call normally; install a recorder only for a proven dependent
  need. Keep network metadata continuous and deep-decode concerned/suspicious requests.
- Reuse the current Core load or create one required load; never add a clean repeat.
- Persist one handshake and reject capability/binding/health repetition by phase.
- Read only new Preview events, current planned Variables, and concerned/suspicious tags.
- Reuse only static configuration under exact container/workspace identity.
- Build coverage just in time and reuse safe journey prefixes.
- Retry one transient panel read; block only its dependent claims rather than restarting.
- Render from captured evidence without another browser pass.

Controlled release checks measured 0.08 seconds for a 100-event/2,000-requirement
compile, 0.61 seconds for a three-event action/feedback cluster, 0.21 seconds for a
dependent-surface fast-fail, and a 2.515-second median for direct representative
multi-sheet workbook intake. These are isolated local architecture checks, not a promise
for website or browser UI latency.

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
