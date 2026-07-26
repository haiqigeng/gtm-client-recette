# Browser Session And Readiness

## Controlled browser context

Use an analyst-approved existing browser/extension session when the browser
connector can safely control the intended signed-in tabs. Otherwise use a
dedicated persistent Playwright profile and ask the analyst to authenticate
manually. Never copy cookies, login databases, session state, credentials, or
Preview tokens between profiles.

Use
[tag-assistant-operations.md](tag-assistant-operations.md)
for the physical Preview connection, panel extraction, history clearing,
extension permissions, connection troubleshooting, and recovery procedure.

Keep approved website origins explicit. Do not follow an unexpected
cross-origin redirect without confirming it is part of the journey.

## Surface registry

Maintain at least these roles, with a stable surface ID for every applicable
instance:

| Role | Identity evidence |
| --- | --- |
| GTM workspace | Tag Manager URL, account, container, workspace, title |
| Tag Assistant | Tag Assistant URL, connected domain and container |
| Debugged website | Approved origin, current URL, title, Preview context |
| Vendor helper/UI | Vendor, destination/account context, supplementary status |

Rediscover surfaces by role, URL, origin, and title before every action. A tab
index is never a durable identifier. Stop if the container, workspace, connected
domain, or target origin changes unexpectedly.

For multiple web containers, register each workspace and Tag Assistant
connection separately with `container_id`. Simultaneous or sequential Preview
evidence must remain container-specific.

Use `scripts/preview_session_ledger.py` alongside the browser tool when a run
needs resumable surface and action-boundary state. Do not store authentication or
Preview tokens in the ledger or user-facing evidence.

## Readiness gate

Before every business action, verify:

1. Tag Assistant is connected to the intended domain and container.
2. The intended website page is interactive.
3. No unexpected overlay or navigation state blocks the target.
4. Applicable lifecycle events have appeared.
5. The required event-level consent state is visible when consent matters.
6. The Preview stream is unchanged for a configurable quiet window, normally
   1.5–3 seconds.

Use state checks and event counts. A fixed sleep alone is not readiness proof.

## Action boundary

Record:

- Preview connection and target readiness before the action;
- last Preview event index before the action;
- URL, element, action, supplied/synthetic value, and timestamp;
- first Preview event index after the action;
- settled final index;
- quiet-window and bounded-timeout values;
- whether the stream settled.

Normalize the action value, JSON-compatible type, and source. Use explicit
`null`/`not_applicable` for a plain click or load. Preserve safe supplied or
synthetic values; for protected analyst entry store only
`<analyst-entered-protected>`.

After the action, wait until the expected event set is present and the stream is
quiet, or until a bounded timeout expires. Treat event absence as:

- `FAIL` when the action was valid, Preview remained connected, and the stream
  settled without the expected event;
- `BLOCKED` when execution, Preview connectivity, or an upstream/manual
  condition prevented a valid implementation check.

Use a timezone-qualified action timestamp and non-negative integer event
cursors. The target occurrence must fall after the last pre-action cursor and
at or before the settled final cursor. A finalized `REVIEW` attempt keeps the
same boundary and occurrence evidence.

## Continuous business-event cursor

Start the cursor at the first controlled website load after Preview connects.
Treat initial load, every navigation, each interaction, and required async
completion as an observation window. Join the windows without advancing past
an unreviewed event index. Clearing Preview history is acceptable only after
the prior cursor range is captured and the new baseline is recorded.

Within every window, inspect the Tag Assistant API Call sequence in event-index
order. Classify every:

- explicit non-`gtm.*` business event push;
- state-only push that supplies, changes, or clears an acceptance-relevant
  value;
- native or technical event only when it explains chronology, source,
  triggering, or non-firing.

For each business push retain event index, name, page/state, action or
navigation window, applicable plan event, trigger-context result, and one
classification:

- expected occurrence;
- expected companion occurrence;
- duplicate beyond the accepted count;
- premature, delayed, or wrong-order occurrence;
- wrong-page, wrong-action, wrong-state, or otherwise wrong-context occurrence;
- unplanned but relevant business occurrence.

Do not inspect only the event name being tested. A correct planned event pushed
on the wrong page is a defect in occurrence/trigger behaviour. Multiple
legitimate instances across different controlled actions are not duplicates;
multiple pushes inside one action window beyond its occurrence rule are.

Use a focused repeat after an anomaly when needed for confidence. Apply the
positive-journey and explicit non-firing rules in
[journey-inference-and-coverage.md](journey-inference-and-coverage.md).

## Connection watchdog

Check Preview before and after navigation and consequential actions. On a
disconnect, follow the recovery procedure in
[tag-assistant-operations.md](tag-assistant-operations.md). Never classify an
event as missing from implementation while Preview is unreliable.

## History and deduplication

Clear Preview history only through the procedure in
[tag-assistant-operations.md](tag-assistant-operations.md). Preserve:

- tracking-plan order for execution and reporting;
- Tag Assistant event index for runtime chronology;
- action ID for association.

For SPA or cumulative page history, deduplicate only on stable session identity,
Tag Assistant event index, event name, and push timestamp. Never deduplicate
solely by event name.

Distinguish initial load, History API navigation, popstate/hash navigation, GTM
native auto-events, GA4 enhanced-measurement events, and explicit
`dataLayer.push`. Apply the runtime checks in
`client-side-runtime-contexts.md`.

## Cross-domain flows

Register every authorised funnel origin before following it. After a
cross-domain navigation, rediscover all surfaces, verify Tag Assistant
connection for the new domain, and establish a new quiet baseline before the
next action.

When prescribed, also capture linker presence, cookie-domain behaviour,
redirect preservation, and iframe ownership/message path without storing full
identifiers or cookie values.

## Checkpoint and resume

Checkpoint after:

- initial Preview connection;
- analyst authentication handback;
- each protected or consequential step;
- every completed journey;
- consent-scenario changes;
- connection recovery.

On resume, rediscover surfaces and revalidate container, workspace, domain,
consent state, and event cursor before continuing.
