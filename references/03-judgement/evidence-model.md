# Evidence Model

## Authoritative evidence

For every applicable requirement use:

- Tag Assistant event `API Call`: exact object passed to `dataLayer.push`;
- Tag Assistant `Data Layer`: resolved state at that event;
- Tag Assistant `Variables`: resolved GTM-variable values;
- `Tags Fired` and `Tags Not Fired`;
- tag detail: configuration, runtime parameters, fire count, and direct error;
- event-level Consent panel when applicable;
- read-only GTM configuration inspection when Preview lacks static detail.
- first-party browser-network capture for accepted analytics/media destination,
  ID, request count, endpoint, and outbound parameters;
- direct browser-console evidence for Custom JavaScript/HTML errors.

## Supplemental evidence

Label browser interception, vendor helpers, vendor UIs, DebugView, screenshot,
and navigation observations with their actual source. Supplemental evidence
may prove chronology or add corroboration. It cannot silently satisfy exact Tag
Assistant API Call evidence for a planned dataLayer push or browser-network
evidence for an outbound request.

Install `scripts/datalayer_recorder.js` only as the supplemental
`browser_interception` journal described in the execution playbook. When no
Preview-dependent layer applies to a requirement, its exact raw-browser
capture may satisfy that declared raw layer; it still cannot certify resolved
GTM state, variables, tag configuration, firing, or runtime parameters.

Network capture is authoritative only for what the browser attempted to send.
It does not prove vendor receipt, processing, attribution, reporting, or
server-side forwarding.

## Raw versus resolved

The API Call is the authoritative raw push. The Data Layer panel is cumulative
resolved state and can inherit earlier values. Never merge them, backfill a raw
field from resolved state, or summarize either with ellipses.

## Continuous stream evidence

Retain a gapless event-index cursor across controlled page-load, navigation,
and interaction windows. For each explicit business push, record:

- event index, event name, timestamp, and exact API Call source;
- action/case identity and current URL, page, user state, and relevant branch;
- mapped plan event and evaluated occurrence/trigger condition;
- classification as expected, companion, duplicate, mistimed/wrong-order,
  wrong-context, or unplanned relevant;
- evidence IDs for any full comparison or unexpected-item row.

Inspect state-only pushes when they set or clear an acceptance-relevant value.
Do not retain every native `gtm.*` event mechanically; keep one only when it
explains chronology, source, trigger evaluation, or non-firing. A correct
payload on an incompatible page or action remains wrong-context evidence.

Give every executed interaction instance its own action boundary in the
session/coverage ledger. Homogeneous cases may roll up compactly only after
their individual windows have been reconciled.

## Wanted tag not fired

Capture:

- firing trigger evaluation;
- blocking trigger or exception;
- relevant variable values;
- event-level consent;
- direct Preview or console failure text;
- most specific reason and source.

Use reason sources `preview`, `console`, `consent`, `inferred`, or
`not_established`. When evidence cannot establish a reason, write exactly:

`Reason not established from available Preview evidence`

Do not convert that observation into an unproved root cause or fix.

## Evidence IDs

Assign stable unique IDs. Every normalized result references catalogue entries.
Every catalogue entry requires its evidence kind, actual source, path or URL,
timezone-qualified capture time, and concise description. An ID alone is not
provenance. Nested references are kind-bound: an API Call cannot point to a
screenshot row, a trigger cannot point to a sequence row, and a privacy scan
cannot point to generic navigation evidence.

Use the canonical `source` value accepted for each primary kind:

| Evidence kind | Canonical source |
| --- | --- |
| `action_boundary`, `browser_interception`, `navigation` | `Playwright` |
| `api_call`, `resolved_data_layer`, `gtm_variable`, `tag_runtime`, `trigger_evaluation`, `tag_sequence`, `tag_assistant_consent` | `Tag Assistant` |
| `consent_state` | `Tag Assistant` or `Playwright` |
| `tag_configuration` | `Tag Assistant` or `GTM read-only` |
| `browser_network_request` | `Browser Network` |
| `browser_console`, `console_error` | `Browser Console` |
| `vendor_helper` | `Vendor Helper` |
| `business_rule_evaluation`, `sensitive_data_scan`, `previous_run_comparison` | `Deterministic Validator` |
| `analyst_approval` | `Analyst supplied` |
| `scenario_branch`, `screenshot` | `Playwright` or `Analyst supplied` |
| `client_side_checks` | `Playwright`, `Tag Assistant`, `Browser Network`, or `Browser Console` |
| `source_signal` | `Playwright`, `Tag Assistant`, `Browser Network`, or `Browser Console` |
| `gtm_native_event`, `gtm_auto_event` | `Tag Assistant` |
| `dom_event` | `Playwright` |
| `direct_vendor_call` | `Browser Console`, `Browser Network`, or `Playwright` |
| `custom_html` | `Tag Assistant` or `Browser Console` |
| `ga4_enhanced_measurement` | `Tag Assistant` or `Browser Network` |

Use `source_detail` for tool names or combined supplementary context; do not
replace the canonical source with free prose. Direct/native signal kinds use
their actual canonical browser or Tag Assistant source.

Capture connection, action boundary, each occurred event, every failure or
review, every wanted non-fire, every protected blocker, every relevant consent
transition, and every approved override.

Never place authentication credentials, Preview tokens, real personal data, or
generated passwords in evidence. Catalogue
source/source-detail/path/description metadata is also privacy-scanned; redact
it rather than copying an identifier into prose.

Sensitive-data findings must replace the raw match with a category marker,
confidence, path, allowlist decision, short fingerprint, and length. If real
personal data appears in a live payload, do not reproduce it in screenshots,
JSON, workbook cells, or chat.

Keep evidence separate by web container, browser context, scenario branch, and
baseline/current run. A shared event index is not proof that two Preview
connections observed the same container execution.
