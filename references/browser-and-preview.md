# Browser and Preview

## Capability and identity handshake

Use the already-open approved Chromium target and Tag Assistant/Preview session. At the
first document boundary, establish only what the first useful action needs:

- target/browser/tab and current document/frame identity;
- reachable page, final URL, status evidence and soft-404 signals;
- active natural container and expected environment;
- Preview connection, workspace/container identity and event-list readability;
- document-start call-time source recorder health;
- browser-network delta capture health.

Run plan compilation and browser attachment concurrently when the control environment
permits it. The handshake must not inventory every tag, expand future scenarios, render
reports, or create per-event setup records. After a stable navigation, use a cheap health
delta. Repeat the full handshake only when target, document, container, Preview epoch,
recorder, or network identity changes.

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

Install `scripts/datalayer_recorder.js` before application code whenever the control
surface supports document-start injection. It records invocation-time snapshots rather
than later mutable references and preserves:

- every queue `push`, including unplanned and state-only messages;
- named-layer reassignment/replacement;
- timestamps, monotonic sequence, document, frame and action correlation context;
- array/object/arguments payload shape and explicit unserializable/truncated markers;
- lifecycle coverage and collector integrity.

Do not infer a raw push by reading the final dataLayer array or the Preview Data Layer
panel. If the recorder starts late, mark pre-install source completeness unavailable.
Before the first consequential/protected action, require a complete cheap source
self-test; do not discover recorder failure after an irreversible step.

Keep the observer lightweight: no polling, DOM mutation, arbitrary getter execution,
network access, storage writes, or unbounded deep serialization. Capture deltas by cursor
at `commit`, including the quiet interval after one action and before the next.

## Continuous network capture

Collect browser request lifecycle deltas continuously. Preserve request, redirect,
retry, frame/document/worker, initiator, response/error and completion identity. Decode
protocol payloads without discarding raw evidence:

- GA4 query/body/batched hits and item parameters;
- Google Ads conversion destinations and values;
- tag/destination IDs, consent-related fields and request outcomes;
- service-worker or other-frame provenance.

One logical vendor hit may have several transport attempts. Merge redirects/retries into
that hit while keeping their outcomes. Multiple logical hits are not one retry. Missing
request is a `FAIL` only when the applicable action-time request window is complete and
settled; otherwise it is `BLOCKED`.

## Action clusters and Preview micro-batches

`begin` marks a causal boundary and captures before-state plus identity. After the real
interaction, `commit` captures after-state, source/network/lifecycle deltas and quiet
settlement, then emits a non-certifying pulse.

Continue a short natural cluster only when all evidence remains attributable by action,
document, Preview epoch, event, tag and logical hit. Synchronize Preview immediately on
navigation risk, protected/consequential action, identity ambiguity, missing source
correlation, or suspected anomaly.

On one Preview visit:

1. ingest all new event indexes and complete fired-tag summaries;
2. include relevant expected-not-fired tags, not an unlimited container inventory;
3. deep-read only in-scope or suspicious tag configuration, resolved variables, firing
   detail, runtime payload and consent state;
4. reuse static configuration only under exact container/workspace/environment identity;
5. never cache runtime values, occurrence, consent state, page outcome or requests.

Keep a Preview summary/deep batch, including at most one immediate retry, within a
five-second controlled-fixture budget. A partial panel blocks only Preview-dependent
claims and must not trigger an indefinite wait or browser restart.

## Acquisition context

For fresh/referral tests use, in descending strength: natural referring navigation,
browser-controlled referrer/fresh context, explicit campaign parameters, or a
user-provided reproducible context. Record the method and whether storage/cookies were
fresh. A simulated context proves response to that input, not organic ranking or a real
search impression.
