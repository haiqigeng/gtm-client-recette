# Browser and Preview

## Responsibility and sequence

1. The agent asks the minimal intake questions.
2. After `ready`, the agent opens one headed Playwright MCP-managed Microsoft Edge
   window at `about:blank` immediately and starts plan compilation.
3. The user signs in where necessary, connects GTM Preview/Tag Assistant, opens the
   target site, and accepts ordinary consent.
4. The agent derives runtime identities and freezes one setup cursor.
5. The agent executes one measured action and one bounded observation.

Do not open the user's everyday browser, Firefox, an extension-attached replacement,
another profile, or a new authentication window as an automatic workaround. Login and
consent loads are setup, not Core evidence.

## One setup boundary

Record the configured runtime and available surfaces once:

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
    "preview_tag_inventory": true
  }
}
```

Then freeze `setup_boundary.preview_cursor` at the last setup event and record
`ORDINARY_GRANTED`, `EXPLICIT_VARIANT`, or `NOT_APPLICABLE` consent context. The first
`next` accepts this boundary plus the capability profile. Setup page/source/network data
is not measured evidence.

A wrong Playwright provider, Edge channel, profile mode, or headed mode stops before the
action. An unavailable surface does not start a recovery loop; complete the action and
report dependent checks `BLOCKED`.

## One measured action

The action card freezes event/scenario, interaction, mode, document policy, prior Preview
cursor, planned paths, tag scope/IDs, destination/protocol, and conditional panels.
Perform exactly that action once. Use visible completion signals and a short bounded
settlement check, not a long fixed sleep.

For Core, the setup page may already be open, but its tracking predates the frozen
cursor. Perform at most one measured navigation after `next`. A current attributable
post-boundary load may be reused. Never create a second cleanup reload because a panel is
mixed or incomplete.

Natural navigation may produce a new document. Preserve the prior page as before-state
and capture one post-action binding for the new document. Historical “found containers”
in Tag Assistant do not prove the active page; use the target's active scripts/runtime.

## Paste-ready completion collector

`next` returns `playwright_completion.code`, a complete `async (page) => {...}` callback
for the exposed Playwright browser-code tool. Run it once after the action. Do not import
`tag_assistant_collector.js`, copy panel text into handwritten JSON, or reopen tabs. The
callback embeds the collector and returns a bundle directly consumable by `complete`.

The collector is bounded to five seconds with one selector fallback. It:

- lists every Preview index after the frozen cursor;
- parses fully expanded `dataLayer.push(...)`/`gtag(...)` API Call arguments without
  evaluating observed code;
- reads API Calls for planned and unplanned business rows needed for chronology;
- reads Tags summaries on the selected occurrence and causal technical follow-ups;
- deep-reads only declared or runtime-discovered concerned tags;
- switches Names/Values inside concerned tag detail to capture effective configuration
  and runtime parameters;
- returns component completeness separately for event list, API Call, fired list,
  non-fired set, tag detail, and runtime parameters.

Tag firing may appear on a later Trigger Group. Join causal technical rows until the next
unrelated business API Call. Do not scan historical domains, every historical tag, or the
whole container.

The default panels are only **API Call** and **Tags**. The accumulated **Data Layer** tab
activates for an explicit state diagnostic; **Variables** activates for an explicit
resolved-variable diagnostic. Consent activates only for an applicable consent
requirement/scenario. These diagnostics never substitute for the API Call, effective tag
runtime, or browser request.

If the collector times out or one component is unreadable, it returns all event indexes
and the usable canonical evidence with that component incomplete. Submit it immediately.
Do not reload, replace the browser, install a recorder, or spend minutes normalizing it.

## Source authority

The exact fully expanded Tag Assistant API Call is the ordinary source authority and is
ingested once. Use `scripts/datalayer_recorder.js` only when the API Call is incomplete or
pre-GTM call-time behavior is itself material. A late wrapper is not document-start
proof. A new document needed for the recorder requires a structured retest and one
authorized navigation.

When direct call-time and API Call evidence observe the same occurrence, reconcile only
the same action, arguments, and document. Keep surplus identical calls and every other
interjected push so duplicates cannot disappear.

## Network evidence

Prefer a native Playwright/MCP request delta opened at the action boundary and closed at
settlement. Retain only concerned analytics/media requests, failures, and suspicious
requests. Preserve logical-hit identity, URL without secrets, method, event,
destination, planned decoded parameters, redirects/retries, response status/outcome, and
parameter/body completeness.

The paste-ready callback includes Resource Timing as a quick fallback. It can prove a
visible endpoint and URL parameters but deliberately marks the window/body incomplete;
missing values therefore become `BLOCKED`, not false `FAIL`. Replace that fallback with
the native request delta when available.

Never retain cookies, authorization headers, session tokens, or an unrelated raw browser
dump. A missing request is `FAIL` only under a complete attributable request window;
otherwise it is `BLOCKED`.

## Recovery

A wrong origin/container/document/Preview binding blocks dependent layers and is a setup
problem, not a client tracking defect. Preserve the action and feedback. Ask the user
only to correct the prepared Preview/target or complete a protected gate. A repeat needs
a structured evidence-defect record or explicit user authorization.
