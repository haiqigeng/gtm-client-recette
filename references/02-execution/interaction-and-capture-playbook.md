# Interaction And Capture Playbook

## Contents

1. [Inspect the supplied plan](#inspect-the-supplied-plan)
2. [Build the interaction census](#build-the-interaction-census)
3. [Execute real interactions](#execute-real-interactions)
4. [Verify completion and retry safely](#verify-completion-and-retry-safely)
5. [Use the supplemental dataLayer journal](#use-the-supplemental-datalayer-journal)
6. [Capture browser requests](#capture-browser-requests)
7. [Exercise specialized browser interactions](#exercise-specialized-browser-interactions)
8. [Check dataLayer runtime semantics](#check-datalayer-runtime-semantics)

Use only the sections applicable to the tracking plan and reachable website.
This playbook does not authorize a generic crawl or invented negative cases.

## Inspect the supplied plan

Run:

```powershell
python -B scripts/inspect_tracking_plan.py tracking-plan.xlsx plan-inspection.json
```

The inspector preserves sheet/row/cell order, formulas, hyperlinks, comments,
merged ranges, hidden source coordinates, and embedded-image anchors. Embedded
images are extracted beside the JSON by default so they can be inspected as
journey or element evidence. Treat the source workbook as acceptance evidence;
do not infer acceptance rules from generated files.

## Build the interaction census

Install `scripts/dom_interaction_census.js` in the current document and call:

```javascript
const censusSource = await fs.promises.readFile(
  "scripts/dom_interaction_census.js",
  "utf8"
)
await page.evaluate(censusSource)

window.__gtmRecetteCensus({
  rootSelector: "header",
  maxItems: 500
})
```

Run it separately for each applicable placement and viewport. For a
same-origin iframe, execute it inside that frame; for a cross-origin iframe,
use browser/frame locators and record the boundary.

Using browser-protocol evaluation avoids an inline-script injection that a
strict page Content Security Policy can reject. The census supplies labels,
accessible names, destinations, placement, tracking attributes, inherited
visibility, and selectors verified inside their query root. Open-shadow-root
items include `shadowHostChain` and `selectorChain`; `selectorUnique: false`
is a discovery limitation, never an executable locator claim. The census
discovers cases only. Map each candidate to the tracking plan, remove
irrelevant elements, and give each accepted instance its own action boundary.

Do not retain field values, account identifiers, or protected text from an
authenticated page. Redact or quarantine a census that contains personal
content.

## Execute real interactions

Use the browser's accessible locator or equivalent real user action first:

- click or tap the actual element;
- fill and select through normal control APIs;
- hover before choosing a hover-only submenu;
- use keyboard input when the interface requires it;
- drag a carousel/slider through its user-facing control;
- scroll the target into view before visibility checks.

Do not use `element.click()`, direct event dispatch, router calls, or application
methods as routine substitutes. A programmatic fallback is acceptable only
when the accepted implementation is itself programmatic or when the plan
explicitly allows it; record the mechanism and do not claim user-interaction
coverage that was not executed.

For repeated families, parameterize the actions but keep isolated state and
cursor windows. Verify every instance's event count and payload before rolling
up homogeneous success. Reset the page, form, basket, user state, consent
scenario, or funnel checkpoint whenever the previous case can influence the
next one.

## Verify completion and retry safely

After every real interaction, prove that the website action itself completed
without using the expected tracking event. Use the smallest safe independent
signal available:

- URL, route, title, or navigation change;
- visible menu, modal, validation, success, or confirmation state;
- control value, selected option, basket count, or rendered result change;
- a safe application response or DOM state tied to the action.

Record `interaction_outcome` as `completed`, `failed`, or `uncertain`, plus the
completion signal. A tracking event is evidence about tracking, not evidence
that the click, submit, or selection succeeded.

When a transient overlay, stale locator, animation, disabled control, or
similar execution condition prevents completion:

1. preserve the failed attempt and its complete action-window stream;
2. inspect any pushes in that failed window for premature or wrong-context
   behaviour;
3. correct only the transient execution condition without changing the
   implementation;
4. re-establish readiness and the quiet baseline;
5. retry once with a new action ID linked to the failed action.

Do not merge the two windows or erase the failed attempt. More than one retry
requires a recorded transient reason. If no valid interaction can be
completed, classify the case `BLOCKED`; do not call the expected event missing
from implementation. If the interaction completed and the relevant stream
settled without the event, the occurrence can be `FAIL`.

## Use the supplemental dataLayer journal

Install `scripts/datalayer_recorder.js` with a browser-context init script
before the first controlled navigation. Playwright evaluates init scripts
after document creation and before page scripts, which captures early pushes
without reconstructing them later:

```javascript
await context.addInitScript({
  path: "scripts/datalayer_recorder.js"
});
```

Before an action:

```javascript
window.__gtmRecetteJournal.markAction("ACT-017");
```

After settlement:

```javascript
window.__gtmRecetteJournal.recordsSince(lastCallIndex);
window.__gtmRecetteJournal.checkIntegrity("dataLayer");
window.__gtmRecetteJournal.clearAction();
```

After the selected records have been durably saved, reconciled to the session
ledger, and privacy-scanned:

```javascript
window.__gtmRecetteJournal.acknowledgeThrough(lastPersistedCallIndex);
```

This removes only retained records through that call index. It never resets
`nextCallIndex`, so action chronology remains stable. Do not acknowledge a
record that exists only in browser memory or before a failed bulk import.

The journal records every call, every argument, URL, timestamp, action ID,
array length, type marker, and available `gtm.uniqueEventId`. It also records
pre-existing entries when installed late.

Snapshots distinguish a repeated object (`shared_reference`) from a real
ancestor cycle (`circular_reference`). Depth, node, and elapsed-time budgets
protect the page from expensive capture; `snapshot_truncated` preserves the
limitation explicitly. A hostile array member becomes `unreadable` without
discarding readable siblings. Use `recordsSince(lastCallIndex)` so a long SPA
session is not repeatedly cloned from the beginning.

Rules:

- label this evidence `browser_interception`;
- keep Tag Assistant API Call authoritative whenever Preview-dependent layers
  are applicable;
- never relabel the journal as Tag Assistant evidence;
- verify the wrapper after navigation or suspected dataLayer reassignment;
- treat a required field behind `snapshot_truncated` as incomplete
  supplemental evidence;
- re-inject on every new document and applicable frame;
- quarantine and privacy-scan raw captures before report generation;
- use it to expose gaps, duplicates, wrong-context pushes, state-only updates,
  and unload-time chronology.

The journal is supplemental instrumentation and can slightly affect timing.
Confirm every material anomaly through Tag Assistant or a focused repeat when
Preview is available.

## Capture browser requests

Register request listeners on the browser context before the controlled page
load so popups, new tabs, redirects, fetch/XHR, image pixels, scripts, and
beacons are not missed. Playwright exposes request URL, method, post data,
resource type, redirect chain, and request lifecycle.

Prefer read-only `browserContext.on("request")` monitoring. Do not use routing
when observation is sufficient: routing can change cache and service-worker
behaviour. If expected events are missing, record whether a service worker
owned the request before concluding that the browser did not send it.

Assign each captured request:

- stable request ID;
- action ID and timestamp;
- initiating page/frame or service worker when available;
- method, exact URL, resource type and redirect relationship;
- safe required headers only;
- post data or a quarantined raw-body evidence path.

Keep listeners active until navigation/unload settles or the browser context
confirms the request. Do not close the context immediately after a conversion
click merely because the next page appeared.

Decode captured JSON with:

```powershell
python -B scripts/decode_browser_requests.py requests.json decoded-requests.json
```

The decoder preserves repeated query keys, parses JSON and form bodies, marks
newline-delimited batches, retains body length/hash, and excludes
secret-bearing headers. Use `--retain-raw-body` only in quarantined evidence.
Run the sensitive-data scanner before normalization.

Compare request count, endpoint, destination ID, vendor event name, and every
required outbound parameter inside the same action window. A batch is one
browser request containing multiple decoded records; it is not automatically
one event.

## Exercise specialized browser interactions

Apply these recipes only when the plan or an encountered relevant element
requires them:

- **Scroll/visibility:** establish initial viewport, scroll through the real
  page, respect required percentage/duration, and distinguish lazy rendering
  from the trigger.
- **Timer:** keep the page active for the prescribed interval and use event
  chronology rather than a fixed sleep as proof.
- **Video:** operate the embedded player's user controls for planned
  play/progress/complete milestones; record iframe/player limitations.
- **Download/outbound:** start listeners before the actual link action and
  retain navigation/download plus event chronology.
- **Hover menu:** hover the owning control, wait for visible interactive state,
  then activate every applicable leaf.
- **Carousel/slider:** use arrows, dots, swipe or drag as exposed; distinguish
  newly eligible promotions from duplicates.
- **Search/filter/pagination/infinite scroll:** reset query/state per finite
  case and retain result counts and loaded boundaries.
- **Popup/new tab:** register the new page through the browser context before
  acting in it, keep per-page action attribution, and verify Preview continuity
  throughout a multi-tab funnel.
- **iframe/shadow DOM:** use frame or shadow-aware locators for CMPs, payments,
  chat widgets, and embedded controls; record ownership and never substitute
  parent evidence. Hand protected payment/authentication content to the
  analyst.
- **SPA/back-forward cache:** distinguish initial load, push/replace state,
  popstate/hash and restored page state; preserve event source and count.
- **Form/error/success:** exercise only planned validation/error branches,
  then complete the ordinary synthetic success flow.
- **JavaScript error:** when the plan expects an error event, register page and
  console error listeners before the action, reproduce the specified error
  safely, and distinguish the application error from errors caused by test
  instrumentation.
- **HTTP Basic Auth/access wall:** let the analyst enter protected access
  material in the controlled browser, retain only a handback marker, then
  re-check the origin and Preview connection. Treat geo/anti-bot walls as
  evidenced access blockers; do not bypass them silently.

## Check dataLayer runtime semantics

Google processes queued dataLayer messages in order. Preserve raw messages and
resolved state separately and check:

- overwriting or reassigning `window.dataLayer`;
- a non-array layer or non-callable `.push`;
- an unexpected custom layer name;
- multiple arguments in one `.push` call;
- absent versus `undefined`, `null`, empty string, empty array and empty object;
- stale resolved values inherited from earlier messages;
- recursive object/array carry-over that leaves ghost ecommerce items;
- missing ecommerce clearing when the acceptance contract requires a clean
  object, including `ecommerce: null` where prescribed;
- reuse or mutation of payload objects;
- queued-message loss across navigation;
- event order, `gtm.uniqueEventId`, `eventCallback`, and `eventTimeout`;
- state-only pushes that set or clear a value used by the planned event.

Do not infer a defect from a platform detail alone. Assign `FAIL` only when the
observed runtime state contradicts the tracking plan or explains a confirmed
acceptance failure.
