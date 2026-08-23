# Browser and Preview

## Capability and identity handshake

Use the already-open approved Chromium target and Tag Assistant/Preview session. At the
first document boundary, establish only what the first useful action needs:

- target/browser/tab and current document/frame identity;
- reachable page, final URL, status evidence and soft-404 signals;
- active natural container and expected environment;
- Preview connection, workspace/container identity and event-list readability;
- the usable fully expanded Tag Assistant API Call path, or the reason a stronger
  recorder is needed;
- browser-network delta capture health.

Run plan compilation and browser attachment concurrently when the control environment
permits it. The handshake must not inventory every tag, expand future scenarios, render
reports, or create per-event setup records. After a stable navigation, use a cheap health
delta. Repeat the full handshake only after a proved identity/capture change and record
the correction/retest reason. Do not attach capability, binding, and health snapshots to
every action or Preview synchronization.

Use the current valid page load for Core/page-load evidence when it is attributable and
complete. If a new load is required, perform one. A second same-scenario load is a retest
and requires a named defect such as mixed identity, incomplete API Call, or failed
transport capture; “clean repeat” is not a reason.

A navigation/reload may legitimately replace the document. Preserve the old page only
as the `before` business/reality state, capture a new binding for the new document, and
attribute source/Preview/request evidence to that new document. Do not block solely
because before and after page IDs differ; do block mixed post-action documents or a new
document that was never rebound.

A browser/control failure blocks only dependent proof. Do not label it as a website
failure, open replacement tabs, or construct alternate evidence. Historical "found
containers" in Tag Assistant do not prove the current runtime container. Prefer the
documented Preview reconnect path; request blocking and script injection are not normal
repair mechanisms.

When observed, add delta counters to the existing health capture under `operations`:
navigation/reset/reload, target or Preview tab switch, full preflight, Preview summary
or deep read, Preview retry, and AI semantic pass. These counters diagnose browser cost;
they do not create gates, evidence, or another workflow state.

## Continuous source capture

Use a fully expanded Tag Assistant **API Call** as the normal exact-message source. It is
authoritative when the arguments, event index, Preview epoch, and completeness are
captured. This avoids a recorder-install/reload cycle in ordinary Preview recette.

Install `scripts/datalayer_recorder.js` before application code only when the API Call is
unavailable/incomplete or the claim specifically needs invocation-time behavior before
GTM processing. It records invocation-time snapshots rather than later mutable
references and preserves:

- every queue `push`, including unplanned and state-only messages;
- named-layer reassignment/replacement;
- timestamps, monotonic sequence, document, frame and action correlation context;
- array/object/arguments payload shape and explicit unserializable/truncated markers;
- lifecycle coverage and collector integrity.

Do not infer a raw push by reading the final dataLayer array or the Tag Assistant Data
Layer panel. When neither exact source path is complete, dependent source claims remain
`BLOCKED`; a collapsed, partial, or inferred panel never substitutes.
The separate **Data Layer** tab is accumulated post-message state and must be captured as
GTM-state evidence, never relabelled as the API Call. Before the first
consequential/protected action, require a complete cheap source self-test; do not discover
source failure after an irreversible step.

Keep the observer lightweight: no polling, DOM mutation, arbitrary getter execution,
network access, storage writes, or unbounded deep serialization. Capture deltas by cursor
at `commit`, including the quiet interval after one action and before the next.

## Continuous network capture

Collect lightweight browser request lifecycle metadata continuously. Deep-decode bodies
and parameters only for planned/analytics-like sends, failures, and suspicious requests;
never retain cookies, authorization headers, or an unrelated full-page request dump.
Preserve request, redirect, retry, frame/document/worker, initiator, response/error and
completion identity. Decode relevant protocol payloads while retaining safe hashes and
the fields needed for judgement:

- GA4 query/body/batched hits and item parameters;
- Google Ads conversion destinations and values;
- tag/destination IDs, consent-related fields and request outcomes;
- service-worker or other-frame provenance.

One logical vendor hit may have several transport attempts. Merge redirects/retries into
that hit while keeping their outcomes. Multiple logical hits are not one retry. Missing
request is a `FAIL` only when the applicable action-time request window is complete and
settled; otherwise it is `BLOCKED`.

Sensitive-data findings are action- and concerned-request-scoped. An unrelated vendor's
session field must not fail the planned event, while a prohibited field in that event's
source, runtime, or matching destination request still fails it.

## Action clusters and Preview micro-batches

The first `begin` captures capability, binding, health and before-page once. Later
`begin` bundles contain the before-page plus optional unbound continuous deltas only.
After the real interaction, `commit` captures current after-health/page,
source/network/lifecycle deltas and quiet settlement, then emits a non-certifying
per-layer pulse. `sync-preview` accepts only the Preview micro-batch plus analyst control
annotations. Evidence timestamped before the action is rejected instead of rebound.

Continue a short natural cluster only when all evidence remains attributable by action,
document, Preview epoch, event, tag and logical hit. Synchronize Preview immediately on
navigation risk, protected/consequential action, identity ambiguity, missing source
correlation, or suspected anomaly.

On one Preview visit:

1. ingest all new event indexes and each expanded API Call needed as exact source;
2. capture the Data Layer tab and Variables tab for current planned fields;
3. ingest complete fired-tag summaries and relevant expected-not-fired tags, not an
   unlimited container or historical-domain inventory;
4. deep-read each concerned tag's configuration, effective object/settings mapping,
   firing detail and runtime payload needed by the plan, plus suspicious details;
5. compare those observations with the independently captured browser request;
6. reuse static configuration only under exact container/workspace/environment identity;
7. never cache runtime values, occurrence, consent state, page outcome or requests.

Read API Call, accumulated Data Layer state, and Variables on the exact selected Preview
row. When GTM defers firing to a Trigger Group or another technical lifecycle row, join
only the bounded following technical rows in the same action and Preview epoch, stopping
before the next business event. Use that causal window for concerned tag inventory,
configuration, firing and runtime; never use it to replace the exact API Call, Data Layer,
or Variables values.

Use at most one immediate retry for a transient panel failure. The five-second budget in
the controlled fixture is a regression target, not a universal live-site timeout. A
partial panel blocks only its dependent claims and must not trigger an indefinite wait,
whole-container rescan, or browser restart.

## Acquisition context

For fresh/referral tests use, in descending strength: natural referring navigation,
browser-controlled referrer/fresh context, explicit campaign parameters, or a
user-provided reproducible context. Record the method and whether storage/cookies were
fresh. A simulated context proves response to that input, not organic ranking or a real
search impression.
