# Browser, Preview, and runtime control

## Reuse the approved browser

Use the in-app browser's existing authenticated window/context and already open
GTM, Tag Assistant, and site surfaces. Do not open a replacement window merely
because the current Preview is wrong or inconvenient. First reconnect/debug the
selected Tag Assistant page and verify the actual loaded client container.

Bind the run to a browser instance, browser context/profile, site tab, and
Preview session. A protected handoff must resume those same identities.

If a Preview disconnect creates a new connection epoch, record a reconciled
reconnect contract with before/after browser bindings, action/case when the
disconnect occurred mid-action, direct evidence IDs, and a reason. Preview
event indexes may restart after a proved reconnect; the supplemental dataLayer
call cursor must remain gapless across epochs.

## Container truth

The configured result says which one client web container this run certifies.
Every runtime snapshot must independently capture:

- accepted container/workspace in GTM;
- loaded client container IDs on the site;
- selected Tag Assistant page and Preview session;
- owning container for each observed tag.

If preprod loads another container, stop positive certification and repair the
opened Preview connection. Never continue in a separate unauthenticated window
or treat an offline inspection as evidence from the open browser.

## Before/after runtime snapshot

Capture browser/context/tab/Preview IDs, exact site and selected-page URLs,
Preview connection epoch and event cursor, dataLayer recorder call cursor,
browser-network cursor, lifecycle/quiet/readiness booleans, loaded containers,
page health, and direct evidence IDs. The operator derives action boundaries
from these snapshots; never type inferred cursors into an action.

Use exact URL matching. A same-origin SPA mismatch needs route-transition proof.
Cross-origin or unevidenced page mismatches are invalid.

## Page health

Before interacting, directly record reachability, HTTP status when available,
error-template and soft-404 signals, expected content, and target presence. A
404/soft-404 or wrong page is an executed failed recette case: retain any tags
that fired, mark `PAGE_ACTION_VALIDITY` and overall status `FAIL`, and keep the
technical tag-delivery status separate. Healthy tag evidence cannot turn a dead
business URL into OK.

## Supplemental recorder lifecycle

Inject `datalayer_recorder.js` at document start and set
`window.__gtmRecetteRunId` before it. Export a snapshot only when its `runId`
matches the current normalized run. A different run ID is previous-run residue.

Use `beginRun(runId, {reset: true})` only after exporting or intentionally
discarding the prior run. Check recorder integrity before every action and after
dataLayer reassignment. At the end call `dispose()`; if safe automatic removal
is impossible because later site wrappers enclose it, close the controlled tab
or context and record the limitation. Disposal restores page wrappers and
clears captured state but deliberately leaves an inert, non-configurable control
API so page scripts cannot delete or replace the recorder during a run; closing
the controlled tab removes it.

The recorder is chronology evidence, not a substitute for Tag Assistant API
Call or resolved GTM evidence.

## Runtime interruption

If browser, Preview, network capture, or a controlled surface fails after an
action starts, retain the action and every observed push, capture the last
trustworthy cursors, and use an interrupted settlement. Retry only from a fresh
controlled boundary linked to that retained attempt. Only a Preview disconnect
advances the connection epoch.
