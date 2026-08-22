#!/usr/bin/env python3
"""Execute browser-level regression checks for the injected recette helpers."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "scripts" / "datalayer_recorder.js"
CENSUS = ROOT / "scripts" / "dom_interaction_census.js"
SMOKE_PAGE = ROOT / "tests" / "fixtures" / "browser_helpers_smoke.html"


def require(condition: bool, message: str, details: object = None) -> None:
    if condition:
        return
    suffix = f"\n{json.dumps(details, ensure_ascii=False, indent=2)}" if details is not None else ""
    raise AssertionError(message + suffix)


def main() -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        context.add_init_script(path=RECORDER)
        page = context.new_page()
        page.goto(SMOKE_PAGE.as_uri())

        smoke = page.evaluate("window.__gtmRecetteSmokeResult")
        require(smoke["recorderVersion"] == 3, "Recorder version mismatch.", smoke)
        require(smoke["recorderAttached"] is True, "Recorder did not attach.", smoke)
        require(smoke["recordCount"] == 1, "Smoke push count is not one.", smoke)
        require(smoke["argumentCount"] == 2, "Multi-argument push was not retained.", smoke)
        require(smoke["snapshottedValue"] == 29.9, "Payload mutation altered its snapshot.", smoke)
        require(smoke["undefinedMarker"] == "undefined", "Undefined marker was lost.", smoke)
        require(smoke["censusCount"] == 3, "DOM census did not find all controls.", smoke)

        hostile = page.evaluate(
            """() => {
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              const payload = new Proxy(
                {event: "hostile_payload"},
                {ownKeys() { throw new Error("hostile ownKeys"); }}
              );
              const returned = window.dataLayer.push(payload);
              const snapshot = window.__gtmRecetteJournal.snapshot();
              const record = snapshot.records[snapshot.records.length - 1];
              return {
                before,
                after: snapshot.records.length,
                returned,
                arrayLength: window.dataLayer.length,
                captureType: record.arguments[0].__gtm_recette_type
              };
            }"""
        )
        require(
            hostile["after"] == hostile["before"] + 1, "Hostile payload was not journaled.", hostile
        )
        require(
            hostile["returned"] == hostile["arrayLength"], "Original push result changed.", hostile
        )
        require(
            hostile["captureType"] == "unreadable",
            "Hostile payload did not use the per-argument unreadable marker.",
            hostile,
        )

        hostile_array = page.evaluate(
            """() => {
              const values = [{kept: true}, {unreadable: true}];
              Object.defineProperty(values, 1, {
                enumerable: true,
                get() { throw new Error("hostile array element"); }
              });
              const before = window.__gtmRecetteJournal.snapshot().records.at(-1).callIndex;
              window.dataLayer.push({event: "hostile_array", values});
              const captured = window.__gtmRecetteJournal.recordsSince(before)[0].arguments[0];
              return captured.values;
            }"""
        )
        require(
            hostile_array[0] == {"kept": True}
            and hostile_array[1]["__gtm_recette_type"] == "unreadable",
            "One hostile array element discarded readable sibling evidence.",
            hostile_array,
        )

        references = page.evaluate(
            """() => {
              const shared = {value: 7};
              const circular = {event: "circular"};
              circular.self = circular;
              window.dataLayer.push({event: "dag", left: shared, right: shared});
              window.dataLayer.push(circular);
              const records = window.__gtmRecetteJournal.snapshot().records;
              const dag = records[records.length - 2].arguments[0];
              const cycle = records[records.length - 1].arguments[0];
              return {dag, cycle};
            }"""
        )
        require(
            references["dag"]["left"] == {"value": 7}
            and references["dag"]["right"]["__gtm_recette_type"] == "shared_reference",
            "Shared DAG references were not retained safely and distinctly from cycles.",
            references,
        )
        require(
            references["cycle"]["self"]["__gtm_recette_type"] == "circular_reference",
            "A real circular reference was not marked.",
            references,
        )

        diamond = page.evaluate(
            """() => {
              let shared = {leaf: true};
              for (let index = 0; index < 28; index += 1) {
                shared = {left: shared, right: shared};
              }
              const before = window.__gtmRecetteJournal.snapshot().records.at(-1).callIndex;
              const startedAt = performance.now();
              window.dataLayer.push({event: "bounded_diamond", payload: shared});
              const elapsedMs = performance.now() - startedAt;
              const record = window.__gtmRecetteJournal.recordsSince(before)[0];
              return {
                elapsedMs,
                containsSharedMarker: JSON.stringify(record).includes("shared_reference")
              };
            }"""
        )
        require(
            diamond["elapsedMs"] < 150 and diamond["containsSharedMarker"] is True,
            "Shared-reference snapshot exceeded its passive-instrumentation budget.",
            diamond,
        )

        depth_budget = page.evaluate(
            """() => {
              const payload = {event: "depth_budget"};
              let cursor = payload;
              for (let index = 0; index < 80; index += 1) {
                cursor.next = {};
                cursor = cursor.next;
              }
              const before = window.__gtmRecetteJournal.snapshot().records.at(-1).callIndex;
              const returned = window.dataLayer.push(payload);
              const record = window.__gtmRecetteJournal.recordsSince(before)[0];
              return {
                returned,
                arrayLength: window.dataLayer.length,
                containsTruncation: JSON.stringify(record).includes("snapshot_truncated"),
                reason: JSON.stringify(record).includes("max_depth")
              };
            }"""
        )
        require(
            depth_budget["returned"] == depth_budget["arrayLength"]
            and depth_budget["containsTruncation"] is True
            and depth_budget["reason"] is True,
            "Snapshot depth budget did not preserve push semantics with an explicit marker.",
            depth_budget,
        )

        reassignment = page.evaluate(
            """() => {
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              window.dataLayer = window.dataLayer.slice();
              window.dataLayer.push({event: "after_reassignment"});
              const after = window.__gtmRecetteJournal.snapshot().records.length;
              return {
                before,
                after,
                integrity: window.__gtmRecetteJournal.checkIntegrity()
              };
            }"""
        )
        require(
            reassignment["after"] == reassignment["before"] + 1,
            "Recorder did not survive dataLayer reassignment.",
            reassignment,
        )
        require(
            reassignment["integrity"]["recorderAttached"] is True,
            "Recorder integrity failed after reassignment.",
            reassignment,
        )

        duplicate_install = page.evaluate(
            """() => {
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              const first = window.__gtmRecetteJournal.install();
              const second = window.__gtmRecetteJournal.install();
              window.dataLayer.push({event: "after_duplicate_install"});
              const after = window.__gtmRecetteJournal.snapshot().records.length;
              return {before, after, first, second};
            }"""
        )
        require(
            duplicate_install["after"] == duplicate_install["before"] + 1,
            "Repeated install created duplicate journal records.",
            duplicate_install,
        )

        exposed_chain = page.evaluate(
            """() => {
              const previous = window.dataLayer.push;
              function gtmStylePush(...args) {
                return Reflect.apply(previous, this, args);
              }
              Object.defineProperty(
                gtmStylePush,
                "__gtmRecetteOriginalPush",
                {value: previous}
              );
              window.dataLayer.push = gtmStylePush;
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              const installed = window.__gtmRecetteJournal.install();
              window.dataLayer.push({event: "through_exposed_chain"});
              const after = window.__gtmRecetteJournal.snapshot().records.length;
              return {
                before,
                after,
                installed,
                integrity: window.__gtmRecetteJournal.checkIntegrity()
              };
            }"""
        )
        require(
            exposed_chain["installed"] is True
            and exposed_chain["after"] == exposed_chain["before"] + 1
            and exposed_chain["integrity"]["recorderAttached"] is True,
            "An exposed delegating push chain was not recognized safely.",
            exposed_chain,
        )

        unexposed_chain = page.evaluate(
            """() => {
              const previous = window.dataLayer.push;
              window.dataLayer.push = function unexposedDelegate(...args) {
                return Reflect.apply(previous, this, args);
              };
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              const installed = window.__gtmRecetteJournal.install();
              window.dataLayer.push({event: "through_unexposed_chain"});
              const after = window.__gtmRecetteJournal.snapshot().records.length;
              return {
                before,
                after,
                installed,
                integrity: window.__gtmRecetteJournal.checkIntegrity()
              };
            }"""
        )
        require(
            unexposed_chain["installed"] is False
            and unexposed_chain["after"] == unexposed_chain["before"] + 1
            and unexposed_chain["integrity"]["pushReplacedUnverified"] is True,
            "An unexposed push replacement was rewrapped or misreported.",
            unexposed_chain,
        )

        custom_layer = page.evaluate(
            """() => {
              window.customDataLayer = [];
              const watched = window.__gtmRecetteJournal.watch("customDataLayer");
              const before = window.__gtmRecetteJournal.snapshot().records.length;
              window.customDataLayer.push({event: "custom_layer_event"});
              const after = window.__gtmRecetteJournal.snapshot().records.length;
              return {watched, before, after};
            }"""
        )
        require(
            custom_layer["watched"] is True and custom_layer["after"] == custom_layer["before"] + 1,
            "Configured custom data layer was not recorded.",
            custom_layer,
        )

        acknowledgement = page.evaluate(
            """() => {
              const journal = window.__gtmRecetteJournal;
              const before = journal.snapshot();
              const acknowledged = before.records[Math.floor(before.records.length / 2)].callIndex;
              const result = journal.acknowledgeThrough(acknowledged);
              const after = journal.snapshot();
              window.dataLayer.push({event: "after_acknowledgement"});
              const finalSnapshot = journal.snapshot();
              return {before, acknowledged, result, after, finalSnapshot};
            }"""
        )
        require(
            acknowledgement["result"]["removed"] > 0
            and acknowledgement["after"]["acknowledgedThrough"] == acknowledgement["acknowledged"]
            and all(
                row["callIndex"] > acknowledgement["acknowledged"]
                for row in acknowledgement["after"]["records"]
            )
            and acknowledgement["finalSnapshot"]["nextCallIndex"]
            == acknowledgement["before"]["nextCallIndex"] + 1,
            "Durable acknowledgement did not prune safely or preserve monotonic call indexes.",
            acknowledgement,
        )

        census_page = context.new_page()
        census_page.set_content(
            """
            <meta http-equiv="Content-Security-Policy" content="script-src 'none'">
            <style>.hidden-parent { opacity: 0; }</style>
            <div class="branch"><div><div><div><div><div><div><button>CTA one</button></div></div></div></div></div></div></div>
            <div class="branch"><div><div><div><div><div><div><button>CTA two</button></div></div></div></div></div></div></div>
            <span id="preferred-label">Labelled name</span>
            <button aria-label="Wrong fallback" aria-labelledby="preferred-label">Fallback</button>
            <div class="hidden-parent"><button>Hidden action</button></div>
            <div id="shadow-host"></div>
            """
        )
        census_page.evaluate(CENSUS.read_text(encoding="utf-8"))
        census_page.evaluate(
            """() => {
              const root = document.querySelector("#shadow-host").attachShadow({mode: "open"});
              root.innerHTML = "<button>Shadow action</button><button>Shadow secondary</button>";
            }"""
        )
        census = census_page.evaluate(
            "window.__gtmRecetteCensus({includeOffscreen: true, maxItems: 20})"
        )
        by_name = {item["accessibleName"]: item for item in census["items"]}
        require("Hidden action" not in by_name, "Inherited opacity was treated as visible.", census)
        require(
            "Labelled name" in by_name and "Wrong fallback" not in by_name,
            "aria-labelledby did not take precedence over aria-label.",
            census,
        )
        cta_one = by_name["CTA one"]
        cta_two = by_name["CTA two"]
        require(
            cta_one["selectorUnique"] is True
            and cta_two["selectorUnique"] is True
            and cta_one["selector"] != cta_two["selector"],
            "Structurally similar controls received an ambiguous selector.",
            census,
        )
        shadow = by_name["Shadow action"]
        shadow_secondary = by_name["Shadow secondary"]
        require(
            shadow["selectorUnique"] is True
            and shadow_secondary["selectorUnique"] is True
            and shadow["selector"] != shadow_secondary["selector"]
            and shadow["shadowHostChain"] == ["#shadow-host"]
            and len(shadow["selectorChain"]) == 2,
            "Open-shadow-root interaction discovery is incomplete.",
            shadow,
        )

        run_context = browser.new_context()
        run_context.add_init_script(
            script='window.__gtmRecetteRunId = "RUN-A";\n' + RECORDER.read_text(encoding="utf-8")
        )
        run_page = run_context.new_page()
        run_page.goto("data:text/html,<title>recorder lifecycle</title>")
        lifecycle = run_page.evaluate(
            """() => {
              const journal = window.__gtmRecetteJournal;
              const initialRunId = journal.snapshot().runId;
              window.dataLayer.push({event: "run_a"});
              let residueRefused = false;
              try {
                journal.beginRun("RUN-B");
              } catch (error) {
                residueRefused = String(error.message).includes("another run");
              }
              journal.beginRun("RUN-B", {reset: true});
              const reset = journal.snapshot();
              window.dataLayer.push({event: "run_b"});
              const beforeDisposeLength = window.dataLayer.length;
              const disposed = journal.dispose();
              const deleteResult = delete window.__gtmRecetteJournal;
              const pushResult = window.dataLayer.push({event: "after_dispose"});
              return {
                initialRunId,
                residueRefused,
                resetRunId: reset.runId,
                resetRecordCount: reset.records.length,
                resetNextCallIndex: reset.nextCallIndex,
                disposed,
                globalRetained: window.__gtmRecetteJournal === journal,
                deleteRefused: deleteResult === false,
                disposedState: journal.snapshot().disposed,
                pushStillWorks: pushResult === beforeDisposeLength + 1
              };
            }"""
        )
        require(
            lifecycle["initialRunId"] == "RUN-A"
            and lifecycle["residueRefused"] is True
            and lifecycle["resetRunId"] == "RUN-B"
            and lifecycle["resetRecordCount"] == 0
            and lifecycle["resetNextCallIndex"] == 1,
            "Recorder run binding did not reject or reset previous-run residue safely.",
            lifecycle,
        )
        require(
            lifecycle["disposed"]["disposed"] is True
            and lifecycle["globalRetained"] is True
            and lifecycle["deleteRefused"] is True
            and lifecycle["disposedState"] is True
            and lifecycle["pushStillWorks"] is True,
            "Recorder disposal did not restore the page or protect the control API.",
            lifecycle,
        )
        run_context.close()
        browser.close()

    print("Browser helper checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
