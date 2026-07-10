# Browser Session And Readiness

## Surface registry

Maintain three browser surfaces throughout a run:

| Role | Identity evidence |
| --- | --- |
| GTM workspace | Tag Manager URL, container ID, workspace ID, title |
| Tag Assistant | Tag Assistant URL, connected domain, container output |
| Debugged website | Target origin, current URL, title, Preview context |

Rediscover surfaces by URL and title before every action. Tab indexes are
temporary observations, not durable identifiers. Stop if the GTM container,
workspace, connected domain, or website origin changes unexpectedly.

## Readiness gate

Before a business action, verify:

1. Tag Assistant is connected to the intended domain and container.
2. The website is interactive and no blocking overlay remains.
3. Required page lifecycle events have appeared when applicable.
4. The requested consent state is visible in Tag Assistant.
5. Relevant events have remained unchanged for a short configurable quiet
   window, normally 1.5 to 3 seconds.

Use state checks and event counts. A fixed sleep alone is not readiness proof.

## Action boundary

For each action, record the last event before the action, the action timestamp,
the element and page, the first event after the action, and the settled final
event index. Associate only events inside this boundary with the action unless
evidence proves an asynchronous continuation.

After the action, wait until either the expected event set is present and the
stream is quiet, or a bounded timeout expires. A timeout is `BLOCKED` or `FAIL`
according to whether execution or implementation caused the absence.

## Timing judgement

Preserve actual event order even when a business event appears before a CMP
update or another asynchronous callback. Do not reorder events to fit an
expected journey. Compare each event against the consent state that Tag
Assistant shows at that exact event.
