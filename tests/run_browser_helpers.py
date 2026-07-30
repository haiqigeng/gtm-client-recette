#!/usr/bin/env python3
"""Execute browser-level regression checks for the injected recette helpers."""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RECORDER = ROOT / "scripts" / "datalayer_recorder.js"
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
        require(smoke["recorderVersion"] == 2, "Recorder version mismatch.", smoke)
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
                captureType: record.arguments.__gtm_recette_type
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
            hostile["captureType"] == "snapshot_failed",
            "Hostile payload did not use the safe capture fallback.",
            hostile,
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
            and references["dag"]["right"] == {"value": 7},
            "Shared DAG references were mislabeled as circular.",
            references,
        )
        require(
            references["cycle"]["self"]["__gtm_recette_type"] == "circular_reference",
            "A real circular reference was not marked.",
            references,
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
        browser.close()

    print("Browser helper checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
