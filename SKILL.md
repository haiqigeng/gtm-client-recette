---
name: gtm-client-recette
description: Execute one personal GA4 client-side GTM acceptance recette from an imperfect XLSX through one prepared Playwright MCP target tab and Tag Assistant tab, testing one live scenario per identifiable event and producing immediate five-layer feedback plus one XLSX.
---

# GTM Client Recette

Read [references/contracts.md](references/contracts.md) before execution. The input, GA4 client-tag scope, workflow, evidence layers, one-scenario coverage, feedback, and final XLSX are fixed.

## Execution law

- Use the supplied deterministic scripts and only the MCP calls named by the current stage. Never write run-specific parsers, browser-control code, JavaScript, selectors, raw MCP files, or repairs.
- Never use browser evaluation, tool discovery, CSS alternatives, Tag Assistant screenshots, retries, fallbacks, resume, backup, or a second scenario. The sole unsafe-code call is the verbatim API Call chevron manifest returned by `compile_api_call_expand()`.
- A missing or ambiguous browser/Tag Assistant method is `FATAL: METHOD_UNAVAILABLE`. An unresolved target-site scenario is event-level `BLOCKED`; commit its five rows and continue.
- An interrupted run is abandoned. A new invocation starts a new workspace run directory at event one.

## Fixed pipeline

1. Pass the user's XLSX filename, absolute path, or location description to `resolve_workbook_input()` once. It must resolve one readable workbook and the active writable workspace; ambiguity returns to the user without starting a run. No scope confirmation phrase is requested.
2. Run `extract_workbook()` once. Invoke `WorkbookInterpreter` once on its source-addressed cells, formulas, links, parsed code, and images. Pass that record to `validate_inspection_plan()` once. This deterministically reconciles or reconstructs each event's name, parameters and values/value semantics, canonical Data Layer payload, and canonical snippet, then persists only `inspection-plan.json`. Missing URL, trigger, screenshot, definition, destination, type, or requiredness is nonfatal; missing mandatory event/parameter/value semantics or a contradiction between table and Data Layer is fatal.
3. Ask for `ready`, open one headed Playwright MCP browser, then ask the user to prepare the target website and connected Tag Assistant. After `prepared`, start `mcp_bridge.py` once. Validate the fixed MCP inventory and identify one target website tab and one connected Tag Assistant tab. Ignore extra tabs.
4. Run `start_run()` once. For each inspection-plan event in order, use the event name as scenario identity. Invoke `ScenarioResolver` once to return one same-origin target, the shortest finite genuinely necessary non-navigation setup sequence, and one measured action. Use an exact workbook URL when present; otherwise infer from event meaning, optional context, screenshots, and live website evidence. An unreliable inference is `BLOCKED`, never invented.
5. Compile and execute navigation/setup before the cursor fence. Resolve each non-navigation interaction from one accessibility snapshot to exactly one role/name ref. Capture one target-page before snapshot/image and network list; execute the measured action once; wait once; capture one after snapshot/image and network list.
6. Capture one post-cursor Tag Assistant overview. Inspect selector candidates and bounded causal carrier rows through accessibility text. Expand each candidate API Call once with the immutable right-edge chevron manifest and leave it expanded. Read Tags only on carrier rows and Names/Values only for fired Google/GA4 tags.
7. Invoke `VisualAssessor` once on the two target-page images and accessibility evidence. Deterministically judge and commit Page/action reality, Data Layer API Call, GTM Tags, Browser request, and Surrounding behavior; immediately show `event_name`, `layer_name`, `status`, and `details` for all five.
8. After every event commits, run `finish_run()` once, close the bridge, deliver only `gtm-client-recette-results.xlsx` plus the terminal record, and attempt browser close once. On a fatal run error, call `abandon_run()` once.

## Adaptive boundary

Only `WorkbookInterpreter` once per run, `ScenarioResolver` once per event, and `VisualAssessor` once per event are adaptive. They may interpret workbook layouts, embedded images, event meaning, website controls, and visible outcomes, but return only their fixed records. They cannot execute code, control tools, assign final statuses, change event identity or requirements, retry, or reorder the workflow.

## Handoff boundary

The user handles credentials, MFA, CAPTCHA, protected preparation, ordinary consent, and real payment. Never bypass protection, invent credentials, complete real payment, mutate GTM or site code, publish, or make legal conclusions.

There is no mode, no retry, no fallback, no repair, no resume, no backup, and no second scenario.
