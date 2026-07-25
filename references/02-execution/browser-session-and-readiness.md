# Browser Session And Readiness

## Dedicated profile

Use a dedicated persistent Playwright profile. Never copy cookies, login
databases, or session state from a personal Chrome profile. If a requested
profile is locked, ask the analyst to close that browser or authenticate
manually in a fresh dedicated profile.

Keep approved website origins explicit. Do not follow an unexpected
cross-origin redirect without confirming it is part of the journey.

## Surface registry

Maintain three surfaces:

| Role | Identity evidence |
| --- | --- |
| GTM workspace | Tag Manager URL, account, container, workspace, title |
| Tag Assistant | Tag Assistant URL, connected domain and container |
| Debugged website | Approved origin, current URL, title, Preview context |

Rediscover surfaces by role, URL, origin, and title before every action. A tab
index is never a durable identifier. Stop if the container, workspace, connected
domain, or target origin changes unexpectedly.

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

After the action, wait until the expected event set is present and the stream is
quiet, or until a bounded timeout expires. Treat event absence as:

- `FAIL` when the action was valid, Preview remained connected, and the stream
  settled without the expected event;
- `BLOCKED` when execution, Preview connectivity, or an upstream/manual
  condition prevented a valid implementation check.

## Connection watchdog

Check Preview before and after navigation and consequential actions. If the
debug window closes or Tag Assistant disconnects:

1. stop assigning implementation verdicts;
2. retain the last confirmed event cursor;
3. reconnect the intended container/domain;
4. record the disconnect and reconnection evidence;
5. repeat the affected action from a stable checkpoint when safe.

Never classify an event as missing from implementation when Preview was
disconnected.

## History and deduplication

Clear Preview history when supported, or record an explicit last-event
baseline. Preserve:

- tracking-plan order for execution and reporting;
- Tag Assistant event index for runtime chronology;
- action ID for association.

For SPA or cumulative page history, deduplicate only on stable session identity,
Tag Assistant event index, event name, and push timestamp. Never deduplicate
solely by event name.

## Cross-domain flows

Register every authorised funnel origin before following it. After a
cross-domain navigation, rediscover all surfaces, verify Tag Assistant
connection for the new domain, and establish a new quiet baseline before the
next action.

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
