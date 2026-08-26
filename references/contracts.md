# Fixed contracts

## Inputs and preflight

- `workbook_input`: an XLSX filename, an absolute XLSX path, or information about its location.
- `ready`, then `prepared`: authorization for one headed Playwright MCP browser with an identifiable target website and one connected Tag Assistant tab.

`resolve_workbook_input()` searches only the supplied location, active workspace, and Downloads. It must resolve exactly one readable `.xlsx`; zero matches fail and multiple plausible matches return to the user without starting a run. `preflight_run()` proves that the active workspace is writable and returns the validated absolute workbook path plus output directory. No literal scope phrase is requested; GA4 client tags are intrinsic to this release. Before `start_run()`, `validate_mcp_preflight()` receives the exact visible target-tab URL and proves that it, one connected Tag Assistant tab, and the required MCP tools exist. Every other tab is ignored. A preflight failure creates no run.

## Canonical inspection plan

`extract_workbook()` runs once and returns source-addressed cells, formulas, links, images, and supported `dataLayer.push`/`gtag` calls parsed as text without evaluation. `WorkbookInterpreter` receives only that evidence and returns this fixed record directly to `validate_inspection_plan()`:

```json
{"schema_version":"3.0.0","events":[{"event_name":"view_item","parameters":[{"data_layer_path":"ecommerce.items[].item_id","ga4_parameter_name":"item_id","value":"SKU-1","value_semantics":"EXAMPLE","json_type":"string","required":null,"source_refs":["Event!F10"]}],"data_layer_payload":null,"definition":null,"trigger_description":null,"entry_url":null,"expected_destination_id":null,"source_refs":["Event!A1","Event!F10"]}]}
```

Every parameter contains exactly the seven shown fields. `value_semantics` is `FIXED`, `EXAMPLE`, or `DYNAMIC`; `json_type` and `required` may be null when the workbook does not declare them. The interpreter may leave `event_name` empty and `parameters` empty only when a cited complete Data Layer payload supplies them. It may leave `data_layer_payload` null only when event name plus parameter/value records can reconstruct it.

`validate_inspection_plan()` deterministically reconstructs the missing representation, reconciles table and Data Layer when both exist, and produces one agent-friendly canonical plan. Every final event contains an event name, non-empty parameters with values/value semantics, `data_layer_payload`, and `data_layer_snippet`. Missing mandatory semantics, unknown citations, duplicate event identity, or an unresolved contradiction is fatal. Missing URL, trigger, screenshot, definition, destination, type, or requiredness is nonfatal. No mapping, workbook-evidence, Base64 handoff, or second validated-plan file is created.

Authority is fixed:

- One unambiguous parsed code call owns technical identity, selector, payload paths, and literal JSON types. Its sample literals never create equality rules.
- A structured table owns meaning, trigger, requiredness, and value rules only when its headings or prose explicitly state `expected`, `fixed`, `constant`, `allowed`, `one of`, or an equivalent unambiguous instruction.
- Generic `Value`/`Values` columns, examples, samples, placeholders, ellipses, and dynamic commerce values authorize only `present` plus JSON type. A stronger mapped rule is deterministically reduced to `present` with `AMBIGUOUS_VALUE_RULE`.
- Prose and images supply interaction context. They do not invent technical fields or runtime rules.

Optional gaps and non-mandatory ambiguities become cited `REVIEW` notices. `start_run()` receives the validated inspection plan and verifies its source hash; it never reopens, re-extracts, or reinterprets the XLSX.

## Adaptive records

`ScenarioDecision` contains exactly `event_id`, `scenario_id`, `target_url`, `target_source`, `setup_actions`, `measured_action`, `reason`, and `evidence_refs`. `scenario_id` equals the canonical event name. `target_source` is `PLAN` or `LIVE`. A plan URL is exact; otherwise the live target remains on the prepared origin.

Each `InteractionDecision` contains exactly `event_id`, `scenario_id`, `operation`, `semantic_locator`, `value`, `reason`, and `evidence_refs`. Operation is `navigate`, `click`, `fill`, `select`, `press`, or `submit`. Non-navigation locators contain exactly `role`, `name`, and `exact:true`. Setup is the shortest finite genuinely necessary non-navigation sequence; it has no arbitrary numeric limit. Measured navigation has no setup.

`VisualAssessment` contains exactly `event_id`, `scenario_id`, `target_match`, `outcome`, `observed_values`, `anomaly_codes`, `summary`, and `evidence_refs`. It interprets only the two target-page images and accessibility evidence and cannot assign statuses or infer hidden technical values.

## Sole MCP production path

Python never owns a browser or executes arbitrary page JavaScript. It validates adaptive records, resolves exact refs from native MCP accessibility text, compiles MCP call manifests, parses MCP evidence, judges, and persists. The agent executes compiled calls verbatim. One `mcp_bridge.py` process is started per run with no arguments; raw MCP text is sent to it as JSONL over stdin and parsed results return over stdout. The text exists only in the MCP result and bridge memory, never in workspace or run files.

| Stage | Allowed calls |
|---|---|
| Browser identity | `browser_tabs`, `browser_snapshot` |
| Target navigation/action | `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_fill_form`, `browser_select_option`, `browser_press_key`, `browser_wait_for` |
| Visible target evidence | `browser_snapshot`, `browser_take_screenshot` |
| Network evidence | `browser_network_requests`, `browser_network_request` |
| Tag Assistant evidence | `browser_tabs`, `browser_snapshot`, `browser_click`; exactly one bridge-produced `browser_run_code_unsafe` call per collapsed candidate API Call |
| Cleanup | `browser_close` |

`browser_evaluate`, `browser_find`, tool discovery, CSS alternatives, generated runtime code, and Tag Assistant screenshots are forbidden. The only `browser_run_code_unsafe` call is the immutable `compile_api_call_expand()` manifest: it requires exactly one collapsed `.api-call` header, obtains its box, clicks twenty pixels from its right edge, and verifies exactly one expanded card. It neither evaluates code in the page nor changes across runs. A target interaction whose exact semantic locator does not resolve once is event-level `BLOCKED`. A missing production MCP method, lost browser/Preview identity, or missing/ambiguous exact Tag Assistant inspector control is fatal `METHOD_UNAVAILABLE`; the run does not probe another method.

The bridge accepts only these fixed stages: `preflight`, `target_ref`, `page_capture`, `network_window`, `network_detail`, `tag_overview`, `tag_selected`, `tag_api`, `tag_tabs`, `tag_summary`, `tag_properties`, then `close`. Every JSON object must contain exactly the fields enforced by that stage; unknown or missing fields terminate the bridge with `MCP_BRIDGE_CONTRACT`. The process creates no file. It is started once, reused for the run, and explicitly closed once, avoiding one interpreter startup per capture.

## Action and page evidence

Before each non-navigation action, one target-page accessibility snapshot is resolved by `resolve_snapshot_ref()`. `compile_mcp_action()` returns `playwright-mcp-action-v1` and the exact MCP call list. `click` and `submit` use one exact click; `fill` uses one one-field form fill; `select` uses one select call; `press` uses one exact focus click followed by one key call; `navigate` uses one exact URL.

The target page receives exactly one before screenshot and one after screenshot. Screenshots are never used to locate controls. Target-page snapshots and screenshots feed Page/action reality and `VisualAssessor` only.

## Network evidence

Immediately before the measured action, capture one non-static request list. After one completion wait, capture it once again. `network_delta()` returns new rows; when navigation occurred, the current post-navigation list is the action window. Retrieve full detail only for `ga4_candidate_indices()`, parse it through `parse_network_detail()`, then decode GA4 protocol data. No listener, page script, polling loop, request retry, or non-MCP network source exists. If MCP evidence cannot establish an attributable delta, Browser request is `BLOCKED`; another layer cannot substitute.

## Tag Assistant evidence

After the deterministic completion wait:

1. Capture one full connected Tag Assistant accessibility snapshot and run `parse_event_overview()` for every row after the fenced cursor.
2. Run `candidate_and_carrier_rows()`. Candidate rows exactly match the canonical technical `event` or wrapped `event_name`. Carrier rows are candidates plus subsequent Trigger Group, Container Loaded, DOM Ready, Window Loaded, and Initialization rows within the same completed action window.
3. For every candidate row, click its exact overview ref once and snapshot once. Send that snapshot to bridge stage `tag_selected`; it verifies the event identity and one collapsed API Call, then returns the immutable right-edge chevron call. Execute it once, snapshot once, and send the result to bridge stage `tag_api`. A still-collapsed API Call is fatal inspector failure; never click the text/card, try another element, or collapse it again.
4. For every carrier row, click its exact overview ref once, snapshot once, resolve and click the exact `Tags` button once, then snapshot once. `concerned_tag_buttons()` retains only fired Google/GA4 tags.
5. For each concerned tag, click its exact ref once and snapshot Names once. Parse `properties_table()`, resolve and click the exact `Values` radio once, snapshot and parse Values once, then click the exact `Close screen` button once.

The overview supplies complete chronology. API Call detail is collected only for selector candidates; tag summaries only for bounded carrier rows; Names/Values only for concerned tags. This preserves target evidence and delayed Trigger Group firing without inspecting generic Message, Set, consent, or unrelated vendor-tag details.

## Evidence, persistence, and output

Every event bundle has `observer_contract: playwright-mcp-v1`, matching event/action/scenario identity, non-regressed cursor, and exactly five object layers: `reality`, `source`, `gtm`, `network`, and `behavior`.

Rows are always Page/action reality, Data Layer API Call, GTM Tags, Browser request, and Surrounding behavior. Status is `PASS`, `FAIL`, `BLOCKED`, `REVIEW`, or `NOT_APPLICABLE`. No layer substitutes for another. Event-level non-PASS results commit and continue.

`start_event()` returns the only two temporary screenshot destinations, both inside the run directory. Each event atomically commits them as `image-E-####-before.png` and `image-E-####-after.png` with `evidence-E-####.json`, then immediately emits five rows with exactly `event_name`, `layer_name`, `status`, and `details`. Details are always `reason=<text>; expected=<canonical JSON>; observed=<canonical JSON>; evidence=<IDs>`. `commit_event()` accepts no arbitrary file paths. On a fatal error, `abandon_run()` removes the fixed uncommitted temporary images and records `RUN_ABORTED`.

Raw accessibility snapshots, network lists/details, Tag Assistant panel text, Base64, DOM dumps, and duplicate mapping/validated-plan JSON are never files. Committed files are limited to `inspection-plan.json`, `events.ndjson`, two target images plus one evidence JSON per event, and the final workbook.

An interrupted run with an open action cannot continue or finalize. The next invocation creates a new absent run directory and begins at event one. After every event commits, `finish_run()` creates only `gtm-client-recette-results.xlsx`, containing one `Event feedback` sheet and the exact four columns with five rows per event.
