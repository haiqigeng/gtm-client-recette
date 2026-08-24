# Browser and Preview

## Default runtime

Use the configured Microsoft Playwright MCP server as the normal browser controller. The
release contract is `@playwright/mcp@0.0.79` over stdio with one headed `msedge` window
and the server's persistent workspace profile. A suitable command is:

```text
npx -y @playwright/mcp@0.0.79 --browser msedge --caps=config --image-responses omit --timeout-action 5000 --timeout-navigation 30000 --console-level warning
```

Do not add `--extension`, `--isolated`, vision, screenshots, saved sessions, routing, or
unsafe code capabilities to the ordinary recette. The persistent profile preserves the
Tag Assistant login and is separate from the user's everyday Edge profile. Use an
isolated profile only for an approved fresh acquisition/consent scenario; that action
must supply a new isolated runtime self-check and operation baseline, not reuse the
persistent-profile identity. Existing-window
attachment, which needs the Playwright extension or an approved CDP endpoint, is a
scope-selected fallback rather than automatic recovery.

At startup call only available documented tools. Use `browser_get_config` once for the
version/config self-check, `browser_tabs` for the two managed tabs, `browser_navigate`,
`browser_snapshot`/`browser_find`, semantic target references with `browser_click`,
`browser_fill_form`/`browser_type`/`browser_select_option`, narrow `browser_evaluate`, and
`browser_network_requests` plus one-request detail. Never guess a helper name, click by
coordinates, or use screenshot interpretation when a semantic target exists.

The first capability record needs only stable target identity, network deltas, Preview
events, and this runtime object; unneeded future surfaces remain `unknown`:

```json
{
  "runtime": {
    "provider": "playwright_mcp",
    "mcp_version": "0.0.79",
    "browser_channel": "msedge",
    "profile_mode": "persistent",
    "headed": true,
    "self_check": "PASS"
  }
}
```

If the server, exact version, Edge channel, profile, or callable-tool self-check fails,
stop before `next`. Do not spend minutes probing alternate methods. A fallback runtime is
valid only when `scope.browser_runtime=existing_chromium` was explicitly approved.

## First useful action

Compile the plan and start Playwright in parallel. Once the runtime self-check passes,
call `next` before connecting Preview or loading the target. For Core/page load,
`next` returns `NAVIGATE_ONCE`; the target page opened by the Preview connection is the
single measured load. This avoids the historical setup load followed by two "clean"
reloads.

The first `next` rejects binding, page, source, network and Preview evidence; this makes
the no-preflight rule enforceable rather than advisory. Ordinary later `next` calls take
no evidence and reuse the prior completion baseline. Only an explicitly fresh isolated
context repeats the cheap capability/health self-check.

Later `next` calls reuse the same window, tabs, container/workspace identity and cumulative
collectors. They do not repeat capability, binding, tag inventory, report setup or future
scenario work. A current page interaction is `INTERACT_ONCE`; a no-action observation is
`OBSERVE_CURRENT`. A natural click-driven navigation is allowed once when the card says
`NATURAL_ALLOWED`. Explicit reload is zero by default.

For an existing-window fallback where Core already predates the action boundary, do not
pretend the old timestamp is current. Either test the next interaction without reload or
authorize exactly one `NAVIGATE_ONCE` Core load. A second load requires a structured
evidence-defect or user-request retest basis.

Record cumulative target-page navigation and reload counters in health; record reset
when a fresh context is authorized. These are agent-maintained browser-operation
counters, including target loads initiated by Preview; target navigation excludes
switching to or navigating inside the Tag Assistant tab. Tab-switch,
preflight, Preview-read/retry and semantic-pass counters are optional diagnostic telemetry,
not prerequisites. The engine compares before/after target navigation and reload counters
with the action card. An extra reload or target navigation is preserved as an
operator-protocol `BLOCKED` finding; it does not discard the client evidence, create a
client `FAIL`, or trigger another action.

After a legitimate navigation, keep the old page only as the before-state, capture one
new binding for the new document, and attribute source/Preview/request evidence to it.
Mixed post-action documents or an unbound new document block confidence. Historical
"found containers" in Tag Assistant never prove the active page runtime.

## Continuous source capture

Use the fully expanded Tag Assistant **API Call** on the exact Preview row as the normal
call-time source. It is authoritative only when arguments, Preview event index and epoch,
history, and completeness are captured. The API Call is ingested once; the model derives
source evidence from that same Preview record, so no duplicate hand-written source file
is needed.

The separate **Data Layer** tab is accumulated post-message state. Capture it for the
concerned Preview row and compare it independently, but never relabel it as the API Call
or infer a raw push from it. Capture Variables separately as GTM-resolved state.

Use `scripts/datalayer_recorder.js` only when the API Call is unavailable/incomplete or a
claim specifically needs pre-GTM invocation behavior. Because document-start capture
must exist before application code, authorize the smallest new navigation and install it
through Playwright's init-script configuration; a late injected wrapper is not equivalent.
Before a protected/consequential action, require a prior cheap complete source canary.

Keep the observer lightweight: no polling, DOM mutation, arbitrary getter execution,
network access, storage writes, or unbounded serialization. Preserve every event,
state-only message, named-layer replacement, JSON state, call order, document/frame, and
explicit truncation marker so interjected behavior remains visible.

## Continuous network capture

Start the browser request window before the action. Use the filtered request list, then
deep-read only planned analytics/media sends, failed transports, or suspicious requests.
Do not persist cookies, authorization headers, or unrelated full-page traffic. Preserve
request/logical-hit identity, event, destination, frame/document/worker, retry/redirect,
response status, failure reason and parameter completeness.

Decode GA4 query/body/batches and item parameters, and applicable Google Ads conversion
fields. Merge attempts for one logical hit but keep duplicate logical hits separate. A
missing request is `FAIL` only when its applicable action window is complete and settled;
otherwise it is `BLOCKED`. A browser `ERR_ABORTED` paired with a successful response is a
transport conflict for review, not an invented hard failure.

Sensitive-data findings are scoped to the concerned event request. Unrelated background
traffic remains redacted evidence and cannot fail the event; a prohibited value in the
matching source, runtime, or destination request still fails safety.

## One completion pass

After the action reaches a bounded quiet state, call `complete` once with the exact
action ID returned by `next` and one typed bundle containing:

- current binding, after health and page/business outcome;
- continuous source, network and lifecycle deltas since the previous committed boundary;
- one complete Preview event-list delta, including every intervening message;
- exact API Call, accumulated Data Layer and Variables for the planned row;
- complete concerned fired/not-fired inventory and only the concerned tag details;
- static configuration, effective mapping, firing/runtime parameters and event-time consent;
- coverage, acquisition, handoff or evidence-backed semantic annotations when applicable.

On that one Preview visit, read all new event indexes first, then deep-read only concerned
or suspicious rows. When firing is deferred to Trigger Group or another technical row,
join only bounded following technical rows in the same action/epoch, stopping before the
next business event. Those rows may supply tag details but never replace the exact API
Call, Data Layer state or Variables of the planned row.

Static configuration may be reused only under exact container/workspace/environment
identity. Never cache occurrence, runtime values, consent, page outcome or requests. Use
at most one immediate retry for a transient panel failure; after the five-second action
timeout, preserve partial evidence and block only dependent checks.

`complete` commits source/network evidence, synchronizes Preview, and emits detailed
per-event/per-layer feedback. If interrupted after commit, rerun it only with the exact
same bundle and action ID; idempotency resumes the existing action instead of opening
another one. The typed completion bundle is the normal single handoff into the engine;
do not create separate ad-hoc evidence files per layer.

Rows timestamped between the prior commit and the current action remain unbound. The
same model pass revises the prior event when such a row changes its behavior verdict;
this preserves anomaly detection without a second `next` capture or browser visit.

## Acquisition context

Do not refuse fresh/referral tracking tests. Use natural referring navigation,
browser-controlled isolated context, explicit campaign parameters, or a user-provided
reproducible entry, in that order. Record the method, referrer/campaign input and storage
freshness. A simulated Google referral proves the tracking response to that input, not
organic ranking or a real search impression.
