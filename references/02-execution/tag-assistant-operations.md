# Tag Assistant Operations

## Contents

1. [Choose the browser session](#choose-the-browser-session)
2. [Connect Preview](#connect-preview)
3. [Prove readiness](#prove-readiness)
4. [Extract event evidence](#extract-event-evidence)
5. [Reconcile a recorder and Preview gap](#reconcile-a-recorder-and-preview-gap)
6. [Clear history safely](#clear-history-safely)
7. [Recover a session](#recover-a-session)
8. [Handle common connection failures](#handle-common-connection-failures)
9. [Return an authenticated session](#return-an-authenticated-session)

Use this reference for the physical GTM Preview and Tag Assistant workflow.
Keep the comparison and verdict rules in the judgement references.

Google's current Preview procedure is documented in
[Preview and debug containers](https://support.google.com/tagmanager/answer/6107056)
and its connection troubleshooting in
[Troubleshoot with Tag Assistant](https://support.google.com/tagmanager/answer/10039345).

## Choose the browser session

Use one browser context that the browser automation can continue controlling.
Choose in this order:

1. an already attached browser/extension session that the analyst explicitly
   approves and that exposes the intended signed-in GTM and website tabs;
2. a dedicated persistent Playwright profile;
3. a new dedicated session in which the analyst signs in manually.

Do not copy cookies, login databases, authentication storage, or Preview tokens
between profiles. Do not request or record credentials. Existing-browser
attachment is a control handoff, not authorization to extract session data.

Tag Assistant Preview is browser-bound. Open the GTM workspace, Tag Assistant,
and debugged website in that same browser context. If the browser connector
cannot see the analyst's existing tabs, open a dedicated session and ask for
manual authentication there.

The current unified Tag Assistant extension is useful for iframes, popups,
new tabs, and multi-window sessions. Verify that it has permission for the
tested origin before relying on those surfaces.

## Connect Preview

1. Identify the exact GTM account, web container, workspace or version, Preview
   environment, and target origin from the analyst's request.
2. Open the intended workspace and choose **Preview**.
3. In Tag Assistant, enter the exact test URL and connect.
4. If the debug query parameter breaks the page, reconnect with **Include debug
   signal in the URL** disabled and record that choice.
5. Wait for the website and Tag Assistant to show the connection.
6. Return to Tag Assistant and enter the debug interface.
7. Register the GTM, Tag Assistant, and website surfaces by stable identity.
8. Confirm the container/domain pair again after redirects or navigation.

Do not begin a verdict because a website tab merely opened. Prove the intended
container and domain are connected and that lifecycle events are arriving.

## Prove readiness

Before the first controlled page load and every business action:

- rediscover the Tag Assistant and website surfaces by URL, title, origin, and
  container rather than tab index;
- confirm the selected website/page node in Tag Assistant belongs to the
  current page;
- record the last event index;
- wait for the observed-baseline quiet window from the browser-readiness
  reference;
- confirm the website is interactive and the target is not covered;
- capture applicable event-level consent state;
- check that the supplemental dataLayer journal, when installed, remains
  attached.

Register popups and new tabs through the browser context before acting in them.
For an iframe, identify whether the tag and interaction live in the parent,
same-origin child, or cross-origin child. The extension may expose iframe tag
activity, but the evidence must retain the owning surface.

## Extract event evidence

For each occurred planned event, select the exact event index and capture these
panels independently:

1. **API Call**: the exact structured `dataLayer.push` object.
2. **Data Layer**: resolved state at that event.
3. **Variables**: each concerned GTM variable and exact type/state.
4. **Tags Fired / Tags Not Fired**: concerned tag status and fire count.
5. **Tag details**: configured field, resolved runtime parameter, trigger,
   exception, sequence, consent and direct error when applicable.

Use the API Call panel for raw-push truth. Do not reconstruct it from the
cumulative Data Layer panel or from a screenshot. Use the supplemental journal
to locate candidate indexes and detect gaps, then cross-check the selected
Tag Assistant events.

For a wanted tag that did not fire, inspect the event where it should have
fired. Capture the evaluated trigger, blocking exception, variable values,
event-level consent, and direct Preview message. Do not inspect unrelated tags.

## Reconcile a recorder and Preview gap

When the supplemental dataLayer journal records a candidate push but no
corresponding Tag Assistant API Call is visible, stop the affected verdict and:

1. retain the journal call index, action ID, timestamp, URL, arguments, and
   integrity result;
2. confirm the intended container, origin, selected Tag Assistant page node,
   iframe/SPA ownership, and connection before and after the action;
3. inspect every Tag Assistant event index in the retained action window,
   including the correct page node after navigation;
4. check for dataLayer reassignment, late recorder installation, multi-argument
   pushes, and a disconnected or changed Preview surface;
5. when the action is safe and repeatable, restore the checkpoint and repeat
   once with a new action ID after reconnection or reload;
6. preserve both attempts and their independent event windows.

If reconnection restarts Preview event numbering, advance the session
`connection_epoch`. The same event index can be valid in a later epoch, but a
duplicate stream/epoch/index remains invalid.

Apply these outcomes:

- when the exact API Call is found, continue with the normal evidence chain;
- when Preview was unreliable, use `BLOCKED` for unavailable Preview-dependent
  layers rather than an implementation `FAIL`;
- when the journal-only observation reproduces under a reliable Preview
  connection, retain it as supplemental discrepancy evidence, but do not use it
  to pass raw API Call, resolved state, variable, tag, firing, or runtime
  checks;
- use `FAIL` only when the evidenced discrepancy itself contradicts a confirmed
  acceptance requirement; otherwise state the unavailable authoritative
  evidence as `BLOCKED`, or use `REVIEW` only for a precise unresolved plan
  meaning;
- when the first journal-only observation does not reproduce, retain it as an
  isolated supplemental observation rather than silently deleting it. It
  cannot become direct acceptance evidence; block an affected required layer
  if authoritative evidence remains unavailable.

A browser request, console object, or journal call cannot be relabelled as a
Tag Assistant API Call.

## Clear history safely

Clear Tag Assistant history only:

1. after every event through the current cursor is classified;
2. after the last event index and action boundary are saved;
3. before a new controlled baseline is loaded;
4. after recording that the visible history was cleared.

After clearing, reload or navigate to the required checkpoint, wait for a quiet
stream, and record the new first index. Never clear history to hide an
unclassified push or to simplify evidence after the fact.

## Recover a session

When Tag Assistant disconnects, the debugged page closes, or the selected page
is no longer current:

1. stop assigning implementation verdicts;
2. preserve the last confirmed event/action cursor;
3. record the disconnect and affected action;
4. reconnect the same container and origin;
5. advance the connection epoch if Preview numbering restarted;
6. rediscover all registered surfaces;
7. restore the last safe website checkpoint;
8. prove readiness and repeat only the affected action;
9. retain the abandoned and repeated action IDs separately.

Never call a missing event `FAIL` when the Preview connection was not reliable.

## Handle common connection failures

Use the smallest relevant recovery:

| Symptom | Check |
| --- | --- |
| Container or Google tag not found | Confirm that the current route actually loads the intended web container; try a known tagged URL before concluding the route is untagged. |
| Page opens but does not connect | Retry after the tag loads; check extension site access, redirects, blockers, and the debug-parameter option. |
| Popup or new tab is absent from the session | Confirm the unified Tag Assistant extension is installed and permitted, then reconnect before repeating. |
| iframe tag is missing | Confirm extension permission and iframe ownership; do not treat parent-page evidence as child-frame evidence. |
| Page breaks with debug parameter | Reconnect without adding the debug signal to the URL and record the limitation. |
| Events stop after navigation | Check selected page node, current domain, container presence, SPA navigation, and connection status before repeating. |
| CMP prevents tags | Follow the consent reference. Never inject consent without the analyst's explicit approval for the exact temporary override. |

If a route truly does not load the container, continue only with requirements
whose evidence remains available and state the unavailable Preview links. Do
not create a separate recette mode or imply certification of missing layers.

## Return an authenticated session

At Google sign-in, MFA, CAPTCHA, external verification, or another protected
checkpoint:

1. preserve current surfaces and action cursor;
2. ask the analyst to complete only the protected step in the controlled
   browser;
3. wait for handback;
4. rediscover every surface and recheck Preview;
5. resume the same journey automatically.

Ordinary website forms, sign-up, login preparation, lead and conversion flows
remain normal recette work with safe synthetic data. Only the protected
credential or consequential step belongs to the analyst.
