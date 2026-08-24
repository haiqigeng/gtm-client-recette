# Browser and Preview

## Preparation sequence

After the intake reply says `ready`, open one headed Playwright MCP-managed Microsoft
Edge window at `about:blank`. Do this before long plan work so the user can authenticate
and prepare GTM Preview while `init` runs.

Tell the user to prepare GTM/Tag Assistant and the site in that managed window. If a site
load is needed to establish login or accept the CMP, classify it as setup and never as
Core evidence. When persistent consent is already granted, leave final Preview Connect or
target navigation until the first action card is open. Reuse this window and its
persistent workspace profile for the run. Do not open the user's everyday browser,
another Edge window, Firefox, an extension-attached replacement, or a fresh profile as an
automatic workaround.

Do not ask intake questions for URL, environment, container, or destination when the plan
and prepared tabs can supply them. Once ready, inspect the managed tabs and derive the
actual origin, document, Preview session/epoch, natural container, workspace, and observed
destinations. Exact identities declared by the plan remain strict.

## Capability-based runtime contract

Use the configured Playwright MCP tools that are actually exposed. Do not pin behavior to
one package version, call a guessed configuration helper, use coordinate clicks, or probe
alternate private methods. Prefer semantic snapshots/targets, narrow evaluation, and
filtered request inspection.

The first capability record declares each surface as `true`, `false`, or `unknown`:

```json
{
  "runtime": {
    "provider": "playwright_mcp",
    "browser_channel": "msedge",
    "profile_mode": "persistent",
    "headed": true
  },
  "surfaces": {
    "stable_target_identity": true,
    "network_deltas": true,
    "preview_events": true,
    "preview_tag_inventory": true,
    "preview_variables": true
  }
}
```

A wrong provider, browser channel, profile mode, or headed mode stops before action. A
missing evidence capability does not start a discovery loop: proceed with the usable
surfaces, preserve the interaction, and mark only dependent claims `BLOCKED`. Release
validation still requires a real pilot where mandatory surfaces are available.

An isolated profile is conditional for an explicitly fresh acquisition or consent
scenario. It is not ordinary startup. Existing-window attachment is valid only when the
approved scope explicitly selected `existing_chromium`.

## First measured load

`init` must finish before `next`, but browser authentication/Preview preparation may run
in parallel. Call the first `next` with only the capability profile and optional health
telemetry. Do not supply binding, page, source, network, or Preview evidence from setup.

For Core/page load, establish ordinary consent first. If consent is already persistent,
open the action before final Preview Connect/target navigation and use that target load as
Core. If consent preparation required an unmeasured site page, accept the CMP, open the
Core action, then authorize exactly one measured reload/navigation. Never perform a setup
load plus two cleanup reloads.

If an attributable current page load occurred after the action boundary and its exact
Preview/API Call evidence is complete, reuse it. Do not reload merely to make evidence
look cleaner. An old page that predates the action is setup evidence, not a current Core
pass.

Ordinary later `next` calls take no browser evidence and reuse the latest completed
binding/cursors. Only a new isolated context repeats the capability profile. Browser
operation counters are optional telemetry; observable document transitions and exact
bindings remain authoritative.

## One bounded action and Preview delta

Each action card freezes:

- event/scenario and expected interaction;
- `OBSERVE_CURRENT`, `NAVIGATE_ONCE`, or `INTERACT_ONCE`;
- document-change policy;
- prior Preview epoch/index cursor;
- current plan fields and known scenario dimensions.

Perform one user interaction. Settle by relevant completion signals rather than a long
fixed sleep. A normal UI operation should fast-fail near five seconds; navigation may use
its configured navigation timeout. One failure yields a precise block—it does not trigger
60-second retries or another page load.

On `complete`, return only Preview rows whose numeric index is greater than the frozen
cursor in the same epoch. `cursor_end` is the last returned index. Historical rows at or
before `cursor_start` are invalid. If the Preview epoch changed, start the new epoch at
zero and include the matching new binding.

Capture all new indexes caused by the action, including lifecycle, consent, state-only,
unplanned, and technical follow-up rows. Mark exactly one Core/state API Call row when a
state-only source anchor is needed. A top-level action ID may bind child Preview rows that
do not repeat it. One interaction can create multiple indexes and multiple causally
co-occurring planned events; it cannot hide a second user interaction.

Deep-read only the selected occurrence and its causal technical follow-up until the next
business-event boundary:

- fully expanded API Call arguments;
- accumulated Data Layer state;
- Variables;
- complete fired and relevant non-fired tag inventory;
- concerned tag configuration/effective mapping/firing/runtime;
- event-time consent when applicable.

Do not scan unrelated historical domains, every historical Preview event, or the whole
container.

## Source authority

The exact fully expanded Tag Assistant **API Call** is the ordinary source authority. It
is ingested once from the Preview record. Do not create a second handwritten source copy.
The **Data Layer** tab is accumulated post-message state and the **Variables** tab is GTM-
resolved state; compare both independently but never call either the original push.

Use `scripts/datalayer_recorder.js` only when the API Call is unavailable/incomplete or a
claim needs pre-GTM call-time behavior. A late injected wrapper is not document-start
evidence. If a new document is truly needed to install the recorder, require the smallest
structured retest and one authorized navigation.

When a direct recorder and Preview API Call both observe the same occurrence, reconcile
them one to one and deduplicate only that exact action/arguments/document occurrence.
Keep every surplus identical call and every other API Call so duplicates or unexpected
interjections cannot disappear merely because one direct source row exists.

## Network and privacy

Open the request delta before the action and close it at settlement. Filter to concerned
analytics/media sends, failed transports, and suspicious requests. Deep-read only those
requests. The decoder retains routing/outcome and planned payload fields while excluding
cookies, authorization headers, and unrelated traffic; do not persist a raw full-browser
request dump.

Preserve logical-hit identity, destination, event, document/frame/worker, redirects,
retries, response status, failure reason, and parameter/body completeness. Merge attempts
for one logical hit but keep duplicate logical hits separate. A missing request is a
`FAIL` only under a complete attributable request window; otherwise it is `BLOCKED`.

## Binding and recovery

After natural navigation, keep the old page only as before-state and capture one new
binding for the new document. Historical “found containers” in Tag Assistant do not prove
the active page. A wrong natural container, origin, document, or Preview epoch blocks
binding-dependent source/GTM/delivery claims; it is not itself a client tracking defect.

Do not inject another container, work outside the managed window, or open an
authentication replacement. Ask for user help only for an actual protected gate or when
the prepared Preview/container must be corrected. A repeat needs a structured
evidence-defect record or explicit user authorization; otherwise report the block and
move to safe independent work.
