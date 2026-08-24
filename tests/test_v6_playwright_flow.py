from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.v5_harness import SCRIPTS, V5Harness, default_event, write_json

from check_release import validate_live_pilot
from core.correlate import build_model, source_event_names
from core.judge import _configuration_has_automatic_mapping
from core.report import MANDATORY_LAYER_ORDER, compact_status_view, status_view
from core.state import StateError, read_stream
from core.workflow import complete_action, next_action, sync_preview


class PlaywrightDefaultFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_first_next_requires_one_prepared_boundary_and_returns_capture_contract(self) -> None:
        harness = V5Harness(self.root)
        with self.assertRaisesRegex(StateError, "setup_boundary"):
            next_action(
                harness.run,
                {"capability": harness.capability()},
                event_ids=["E-view_item"],
            )
        self.assertEqual(read_stream(harness.run)[0], [])

        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        card = started["action_card"]
        self.assertEqual(card["preview_cursor"]["index"], 0)
        self.assertEqual(card["capture_spec"]["collection"]["bounded_passes"], 1)
        self.assertEqual(card["capture_spec"]["collection"]["semantic_fallbacks"], 1)
        self.assertEqual(card["capture_spec"]["timeout_ms"], 5000)
        self.assertIn("API Call", card["capture_spec"]["preview_panels"])
        self.assertEqual(card["capture_spec"]["preview_panels"], ["API Call", "Tags"])
        self.assertEqual(len(card["evidence_targets"]), 5)
        self.assertIn("event", {row["path"] for row in card["capture_spec"]["planned_fields"]})
        self.assertEqual(card["capture_spec"]["tag_ids"], ["GA4-event"])
        completion = started["playwright_completion"]
        self.assertEqual(completion["tool"], "browser_run_code")
        self.assertTrue(completion["code"].startswith("async (page) =>"))
        self.assertNotIn("require(", completion["code"])
        self.assertNotIn("requires_canonical_normalization", completion["code"])

    def test_accumulated_state_and_variables_activate_only_when_explicit(self) -> None:
        event = default_event()
        event["requirements"][0].update({"state_path": "event", "resolved_path": "event"})
        harness = V5Harness(self.root, events=[event])
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        self.assertEqual(
            started["action_card"]["capture_spec"]["preview_panels"],
            ["API Call", "Data Layer", "Variables", "Tags"],
        )

    def test_collector_returns_canonical_bounded_evidence_without_default_diagnostics(self) -> None:
        collector = (SCRIPTS / "tag_assistant_collector.js").read_text(encoding="utf-8")
        self.assertTrue(collector.startswith("(async (spec) =>"))
        self.assertIn(
            'const wantedPanels = new Set(contract.preview_panels || ["API Call", "Tags"])',
            collector,
        )
        self.assertIn("const parsed = callArguments(text);", collector)
        self.assertIn("runtime_parameters: valuesSelected ? runtime : {}", collector)
        self.assertIn("event_list_complete: eventListComplete", collector)
        self.assertNotIn("requires_canonical_normalization", collector)
        self.assertNotIn("module.exports", collector)

    def test_scope_aliases_are_categories_not_literal_runtime_destinations(self) -> None:
        event = default_event()
        event["tags"] = []
        harness = V5Harness(
            self.root,
            events=[event],
            scope={"tag_scope": ["GA4 tags only"], "destination": ["GA4"]},
        )
        scope = harness.plan["scope"]
        self.assertEqual(scope["tag_scope"], ["GA4"])
        self.assertEqual(scope["destination"], [])
        self.assertEqual(scope["destination_categories"], ["GA4"])
        self.assertEqual(scope["destination_mode"], "runtime_discovered")
        self.assertEqual(scope["browser_runtime"], "playwright_mcp")
        self.assertEqual(scope["browser_channel"], "msedge")
        delivery_targets = [
            claim["target"]
            for claim in harness.plan["events"][0]["claims"]
            if claim["target"].get("check") == "destination_request"
        ]
        self.assertEqual(len(delivery_targets), 1)
        self.assertEqual(delivery_targets[0]["protocol"], "ga4")
        self.assertIsNone(delivery_targets[0]["destination"])

    def test_google_analytics_alias_keeps_declared_ga_tag_in_scope(self) -> None:
        event = default_event()
        event["tags"][0]["category"] = "Google Analytics"
        event["tags"][0]["tag_name"] = "Google Analytics event"
        harness = V5Harness(
            self.root,
            events=[event],
            scope={"tag_scope": ["Google Analytics tags"]},
        )
        self.assertEqual(harness.plan["scope"]["tag_scope"], ["GA4"])
        self.assertEqual(len(harness.plan["events"][0]["tags"]), 1)

    def test_one_causal_ga4_tag_and_destination_can_satisfy_category_scope(self) -> None:
        event = default_event()
        event["tags"] = []
        harness = V5Harness(
            self.root,
            events=[event],
            scope={"tag_scope": ["GA4 tags only"], "destination": ["GA4"]},
        )
        action_id = harness.begin()
        payload = {"event": "view_item"}
        harness.commit(action_id, [payload])
        preview = harness.preview([payload], action_id=action_id)
        preview["events"][0]["fired_tags"] = ["runtime-ga4"]
        preview["events"][0]["tags"] = [
            {
                "tag_id": "runtime-ga4",
                "tag_name": "GA4 product event",
                "category": "GA4",
                "fired": True,
                "firing_count": 1,
                "configuration": {"measurement_id": "G-TEST123"},
                "runtime_parameters": payload,
                "runtime_complete": True,
            }
        ]
        from core.workflow import sync_preview

        result = sync_preview(
            harness.run,
            {
                "preview": preview,
                "coverage": harness.coverage("E-view_item", [action_id]),
            },
            event_ids=["E-view_item"],
        )["events"][0]
        self.assertEqual(result["status"], "PASS")
        destination = next(
            row
            for row in result["inspections"]
            if row["inspection_target"] == "Runtime-discovered GA4 destination routing"
        )
        self.assertEqual(destination["status"], "PASS")
        self.assertEqual(destination["observed"][0]["destination"], "G-TEST123")

    def test_wrong_or_failed_runtime_stops_before_action_or_capture(self) -> None:
        harness = V5Harness(self.root)
        capability = harness.capability()
        capability["runtime"] = {
            **capability["runtime"],
            "provider": "existing_chromium",
        }
        with self.assertRaisesRegex(StateError, "requires playwright_mcp"):
            next_action(
                harness.run,
                harness.next_input(capability),
                event_ids=["E-view_item"],
            )
        self.assertEqual(read_stream(harness.run)[0], [])

        capability = harness.capability()
        capability["runtime"]["self_check"] = "FAIL"
        with self.assertRaisesRegex(StateError, "capability probe"):
            next_action(
                harness.run,
                harness.next_input(capability),
                event_ids=["E-view_item"],
            )
        self.assertEqual(read_stream(harness.run)[0], [])

    def test_next_rejects_old_preflight_evidence_before_any_action(self) -> None:
        harness = V5Harness(self.root)
        with self.assertRaisesRegex(StateError, "capability probe and optional health"):
            next_action(
                harness.run,
                {
                    "capability": harness.capability(),
                    "health": harness._health("before"),
                    "setup_boundary": harness.setup_boundary(),
                    "binding": harness.binding(),
                    "page": {"states": [harness._page("before")]},
                },
                event_ids=["E-view_item"],
            )
        self.assertEqual(read_stream(harness.run)[0], [])

    def test_fresh_context_requires_an_isolated_runtime_refresh(self) -> None:
        harness = V5Harness(self.root)
        with self.assertRaisesRegex(StateError, "requires a verified isolated profile"):
            next_action(
                harness.run,
                harness.next_input(),
                event_ids=["E-view_item"],
                fresh_context_required=True,
            )
        self.assertEqual(read_stream(harness.run)[0], [])

        capability = harness.capability()
        capability["runtime"]["profile_mode"] = "isolated"
        started = next_action(
            harness.run,
            harness.next_input(capability),
            event_ids=["E-view_item"],
            fresh_context_required=True,
        )
        self.assertTrue(started["action"]["data"]["fresh_context_required"])

    def test_next_and_complete_create_one_action_one_preview_pass_and_feedback(self) -> None:
        harness = V5Harness(self.root)
        started_at = time.perf_counter()
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        action_id = started["action"]["data"]["action_id"]
        payload = {"event": "view_item"}
        coverage = harness.coverage("E-view_item", [action_id])
        completion_bundle = {
            "binding": harness.binding(),
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "network": harness.network(["view_item"], action_id=action_id, payloads=[payload]),
            "preview": harness.preview([payload], action_id=None),
            "coverage": coverage,
        }
        with patch("core.workflow.build_model", wraps=build_model) as model_builder:
            completed = complete_action(
                harness.run,
                completion_bundle,
                action_id=action_id,
            )
        self.assertEqual(model_builder.call_count, 1)
        self.assertEqual(completed["events"][0]["status"], "PASS")
        records, _ = read_stream(harness.run)
        kinds = [record["kind"] for record in records]
        self.assertEqual(kinds.count("ACTION_BEGIN"), 1)
        self.assertEqual(kinds.count("ACTION_COMMIT"), 1)
        self.assertEqual(kinds.count("CAPTURE_PREVIEW"), 1)
        self.assertEqual(kinds.count("PREVIEW_SYNC"), 1)
        self.assertEqual(kinds.count("EVENT_FEEDBACK_ISSUED"), 1)
        feedback_record = next(row for row in records if row["kind"] == "EVENT_FEEDBACK_ISSUED")
        self.assertEqual(feedback_record["data"]["feedback"]["event_id"], "E-view_item")
        self.assertTrue(feedback_record["data"]["feedback"]["layers"])
        self.assertIn("before opening", completed["instruction"])
        model = build_model(harness.run, harness.plan, records)
        self.assertEqual(
            source_event_names(model, action_id, authoritative_only=True), ["view_item"]
        )
        completion_path = write_json(self.root / "completion.json", completion_bundle)
        markdown = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS / "recette.py"),
                "complete",
                "--run-dir",
                str(harness.run),
                "--action",
                action_id,
                "--input",
                str(completion_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn("Event: view_item", markdown)
        self.assertIn("| Layer | Status |", markdown)
        self.assertLess(time.perf_counter() - started_at, 5.0)
        with self.assertRaisesRegex(StateError, "no evidence; reuse"):
            next_action(
                harness.run,
                {"health": harness._health("before")},
                event_ids=["E-view_item"],
                scenario_id="another-scenario",
            )
        self.assertEqual(
            sum(row["kind"] == "ACTION_BEGIN" for row in read_stream(harness.run)[0]), 1
        )

    def test_complete_without_optional_health_still_returns_all_five_layers(self) -> None:
        harness = V5Harness(self.root)
        started = next_action(harness.run, harness.next_input(), event_ids=["E-view_item"])
        action_id = started["action"]["data"]["action_id"]
        payload = {"event": "view_item"}
        completed = complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "page": {"states": [harness._page("after")]},
                "network": harness.network(["view_item"], action_id=action_id, payloads=[payload]),
                "preview": harness.preview([payload], action_id=action_id),
                "coverage": harness.coverage("E-view_item", [action_id]),
            },
            action_id=action_id,
        )
        event = completed["events"][0]
        self.assertEqual(event["status"], "PASS")
        self.assertEqual(
            [row["layer"] for row in compact_status_view(event)["layers"][:5]],
            list(MANDATORY_LAYER_ORDER),
        )

    def test_missing_capture_surfaces_emit_blocked_feedback_instead_of_throwing(self) -> None:
        harness = V5Harness(self.root)
        started = next_action(harness.run, harness.next_input(), event_ids=["E-view_item"])
        action_id = started["action"]["data"]["action_id"]
        completed = complete_action(
            harness.run,
            {"coverage": harness.coverage("E-view_item", [action_id])},
            action_id=action_id,
        )
        event = completed["events"][0]
        self.assertEqual(event["status"], "BLOCKED")
        layers = compact_status_view(event)["layers"]
        self.assertEqual([row["layer"] for row in layers[:5]], list(MANDATORY_LAYER_ORDER))
        self.assertTrue(all(row["detail"] for row in layers if row["status"] != "PASS"))
        self.assertTrue(
            any(row["kind"] == "EVENT_FEEDBACK_ISSUED" for row in read_stream(harness.run)[0])
        )

    def test_present_dynamic_values_must_still_match_api_call_and_tag_runtime(self) -> None:
        event = default_event()
        event["requirements"].append(
            {
                "requirement_id": "currency",
                "field_path": "ecommerce.currency",
                "match_rule": "present",
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        action_id = harness.begin()
        payload = {"event": "view_item", "ecommerce": {"currency": "EUR"}}
        harness.commit(action_id, [payload])
        preview = harness.preview([payload], action_id=action_id)
        preview["events"][0]["tags"][0]["runtime_parameters"] = {
            "event": "view_item",
            "ecommerce": {"currency": "USD"},
        }
        result = sync_preview(
            harness.run,
            {
                "preview": preview,
                "coverage": harness.coverage("E-view_item", [action_id]),
            },
            event_ids=["E-view_item"],
        )["events"][0]
        mismatch = next(
            row
            for row in result["inspections"]
            if row["reason_code"] == "coherence.api_to_tag_mismatch"
        )
        self.assertEqual(mismatch["status"], "FAIL")
        self.assertEqual(mismatch["observed"], "USD")
        self.assertEqual(mismatch["expected"], "EUR")

    def test_core_uses_preview_open_as_one_load_without_cleanup_reload(self) -> None:
        core = default_event("E-core", "page_view")
        core["mode"] = "state_only"
        harness = V5Harness(self.root, events=[core])
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-core"],
        )
        action_id = started["action"]["data"]["action_id"]
        self.assertEqual(started["action_card"]["mode"], "NAVIGATE_ONCE")
        records, _ = read_stream(harness.run)
        self.assertFalse(any(row["kind"] in {"CAPTURE_BINDING", "CAPTURE_PAGE"} for row in records))

        harness.bump_operations(navigations=1)
        payload = {"event": "page_view"}
        completed = complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "network": harness.network(["page_view"], action_id=action_id, payloads=[payload]),
                "preview": harness.preview([payload], action_id=None),
                "coverage": harness.coverage("E-core", [action_id]),
            },
            action_id=action_id,
        )
        execution = next(
            row
            for row in completed["events"][0]["inspections"]
            if row["target"].get("check") == "execution_protocol"
        )
        self.assertEqual(execution["status"], "PASS")
        records, _ = read_stream(harness.run)
        commit = next(row for row in records if row["kind"] == "ACTION_COMMIT")
        self.assertEqual(commit["data"]["operation_deltas"]["navigations"], 1)
        self.assertEqual(commit["data"]["operation_deltas"]["reloads"], 0)
        self.assertEqual(sum(row["kind"] == "ACTION_BEGIN" for row in records), 1)

    def test_state_source_can_causally_join_a_later_trigger_group_without_false_event_missing(
        self,
    ) -> None:
        core_fields = [
            "device_type",
            "site_country",
            "env_template",
            "env_country",
            "env_language",
            "env_work",
            "navigation_level_1",
            "navigation_level_2",
            "navigation_level_3",
            "user_status",
            "user_id_hashed",
            "email_hashed",
        ]
        core = {
            "event_id": "E-core",
            "event_name": "Core DataLayer",
            "mode": "state_only",
            "delivery_event_name": "page_view",
            "url": "https://shop.example.test/product",
            "requirements": [
                {
                    "field_path": field,
                    "match_rule": "present",
                    "expected_type": "string",
                }
                for field in core_fields
            ],
            "tags": [
                {
                    "tag_id": "GA4-config",
                    "tag_name": "GA4 configuration",
                    "category": "GA4",
                    "expected": "fire",
                    "destination": "G-TEST123",
                    "configuration": {"measurement_id": "G-TEST123"},
                }
            ],
        }
        harness = V5Harness(self.root, events=[core])
        started = next_action(harness.run, harness.next_input(), event_ids=["E-core"])
        action_id = started["action"]["data"]["action_id"]
        state = {field: f"value-{index}" for index, field in enumerate(core_fields, start=1)}
        state["device_type"] = "desktop"
        preview = harness.preview([state], action_id=None)
        preview["events"][0]["event_name"] = "Message"
        preview["events"].append(
            {
                **preview["events"][0],
                "index": 2,
                "event_name": "gtm.triggerGroup",
                "bookmarked": False,
                "api_call": {"arguments": [{"event": "gtm.triggerGroup"}], "complete": True},
                "fired_tags": ["GA4-config"],
                "not_fired_tags": [],
                "tags": [
                    {
                        "tag_id": "GA4-config",
                        "tag_name": "GA4 configuration",
                        "category": "GA4",
                        "fired": True,
                        "firing_count": 1,
                        "configuration": {
                            "measurement_id": "G-TEST123",
                            "send_page_view": True,
                        },
                        "runtime_parameters": {"event": "page_view"},
                        "runtime_complete": True,
                    }
                ],
            }
        )
        preview["cursor_end"] = 2
        result = complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "network": harness.network(
                    ["page_view"], action_id=action_id, payloads=[{"event": "page_view"}]
                ),
                "preview": preview,
                "coverage": harness.coverage("E-core", [action_id]),
            },
            action_id=action_id,
        )["events"][0]
        firing = next(
            row for row in result["inspections"] if row["target"].get("check") == "tag_firing"
        )
        mapping = next(
            row
            for row in result["inspections"]
            if row["target"].get("check") == "effective_mapping"
        )
        request = next(
            row
            for row in result["inspections"]
            if row["target"].get("check") == "request_parameter"
        )
        self.assertEqual(firing["status"], "PASS")
        self.assertEqual(mapping["status"], "FAIL")
        self.assertEqual(request["status"], "FAIL")
        self.assertNotEqual(
            result["reason"],
            "No matching Preview occurrence was observed in a complete event list.",
        )
        compact = compact_status_view(result)
        self.assertLess(len(json.dumps(compact)), 15000)
        request_layer = next(row for row in compact["layers"] if row["layer"] == "Browser request")
        self.assertIsInstance(request_layer["detail"], str)
        self.assertIn("+", request_layer["detail"])

    def test_coverage_annotation_cannot_duplicate_one_action_into_two_scenarios(self) -> None:
        harness = V5Harness(self.root)
        action_id = harness.begin()
        payload = {"event": "view_item"}
        harness.commit(action_id, [payload])
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action_id,
            coverage=harness.coverage(
                "E-view_item",
                [action_id],
                scenarios=[
                    {
                        "scenario_id": "coverage-label-only",
                        "label": "Ordinary product",
                        "role": "ORDINARY",
                        "values": {},
                        "action_ids": [action_id],
                    }
                ],
            ),
        )["events"][0]
        self.assertEqual(len(result["scenarios"]), 1)
        self.assertEqual(result["scenarios"][0]["scenario_id"], "ordinary")
        self.assertEqual(result["scenarios"][0]["action_ids"], [action_id])

    def test_declared_ecommerce_data_layer_mapping_remains_valid_automatic_mapping(self) -> None:
        event = default_event()
        event["requirements"].append(
            {
                "field_path": "ecommerce.currency",
                "match_rule": "equals",
                "expected_value": "EUR",
                "expected_type": "string",
            }
        )
        event["tags"][0]["configuration"]["send_ecommerce_data"] = True
        harness = V5Harness(self.root, events=[event])
        action_id = harness.begin()
        payload = {"event": "view_item", "ecommerce": {"currency": "EUR"}}
        harness.commit(action_id, [payload])
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action_id,
            coverage=harness.coverage("E-view_item", [action_id]),
        )["events"][0]
        mapping = next(
            row
            for row in result["inspections"]
            if row["target"].get("check") == "effective_mapping"
            and row["target"].get("path") == "ecommerce.currency"
        )
        self.assertEqual(mapping["status"], "PASS")
        self.assertEqual(mapping["observed"]["automatic_mapping"], ["GA4-event"])

    def test_automatic_ecommerce_mapping_accepts_nested_source_but_not_clear_flag(self) -> None:
        self.assertTrue(
            _configuration_has_automatic_mapping(
                {"Ecommerce": {"Data Source": "Data Layer"}}, "ecommerce.currency"
            )
        )
        self.assertFalse(
            _configuration_has_automatic_mapping({"clear_ecommerce": True}, "ecommerce.currency")
        )

    def test_single_completion_delta_preserves_and_reports_between_action_anomaly(self) -> None:
        events = [
            default_event("E-list", "view_item_list"),
            default_event("E-item", "view_item"),
            default_event("E-cart", "add_to_cart"),
        ]
        harness = V5Harness(self.root, events=events)
        first = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-list"],
        )
        first_id = first["action"]["data"]["action_id"]
        list_payload = {"event": "view_item_list"}
        first_result = complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "network": harness.network(
                    ["view_item_list"], action_id=first_id, payloads=[list_payload]
                ),
                "preview": harness.preview([list_payload], action_id=None),
                "coverage": harness.coverage("E-list", [first_id]),
            },
            action_id=first_id,
        )
        self.assertEqual(first_result["events"][0]["status"], "PASS")

        between = harness.datalayer(
            [{"event": "add_to_cart", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}],
            action_id=None,
        )
        second = next_action(harness.run, event_ids=["E-item"])
        second_id = second["action"]["data"]["action_id"]
        item_payload = {"event": "view_item"}
        current = harness.datalayer([item_payload], action_id=second_id)
        continuous_delta = {**current, "records": [*between["records"], *current["records"]]}
        second_bundle = {
            "binding": harness.binding(),
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "datalayer": continuous_delta,
            "network": harness.network(["view_item"], action_id=second_id, payloads=[item_payload]),
            "preview": harness.preview([item_payload], action_id=None),
            "coverage": harness.coverage("E-item", [second_id]),
        }
        second_result = complete_action(
            harness.run,
            second_bundle,
            action_id=second_id,
        )

        self.assertEqual(second_result["events"][0]["event_id"], "E-item")
        self.assertEqual(second_result["events"][0]["status"], "PASS")
        self.assertEqual(len(second_result["revised_events"]), 1)
        revised = second_result["revised_events"][0]
        self.assertEqual(revised["event_id"], "E-list")
        self.assertEqual(revised["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "behavior.unexpected_event" and "add_to_cart" in row["reason"]
                for row in revised["inspections"]
            )
        )
        records, _ = read_stream(harness.run)
        model = build_model(harness.run, harness.plan, records)
        interstitial = next(
            row for row in model["source_calls"] if "add_to_cart" in row.get("events", [])
        )
        self.assertIsNone(interstitial["action_id"])
        self.assertEqual(sum(row["kind"] == "ACTION_BEGIN" for row in records), 2)

        input_path = write_json(self.root / "second-complete.json", second_bundle)
        cli = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS / "recette.py"),
                "complete",
                "--run-dir",
                str(harness.run),
                "--action",
                second_id,
                "--input",
                str(input_path),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        cli_result = json.loads(cli.stdout)
        self.assertEqual(cli_result["revised_events"][0]["event_id"], "E-list")
        self.assertEqual(cli_result["revised_events"][0]["domains"]["behavior"]["status"], "FAIL")

    def test_completion_rejects_continuous_history_older_than_the_prior_boundary(self) -> None:
        events = [
            default_event("E-list", "view_item_list"),
            default_event("E-item", "view_item"),
        ]
        harness = V5Harness(self.root, events=events)
        first = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-list"],
        )
        first_id = first["action"]["data"]["action_id"]
        payload = {"event": "view_item_list"}
        complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "network": harness.network(
                    ["view_item_list"], action_id=first_id, payloads=[payload]
                ),
                "preview": harness.preview([payload], action_id=None),
                "coverage": harness.coverage("E-list", [first_id]),
            },
            action_id=first_id,
        )

        second = next_action(harness.run, event_ids=["E-item"])
        second_id = second["action"]["data"]["action_id"]
        stale = harness.datalayer(
            [{"event": "stale_history"}],
            action_id=None,
            timestamp="2020-01-01T00:00:00Z",
        )
        with self.assertRaisesRegex(StateError, "previous continuous boundary"):
            complete_action(
                harness.run,
                {
                    "binding": harness.binding(),
                    "health": harness._health("after"),
                    "page": {"states": [harness._page("after")]},
                    "datalayer": stale,
                    "preview": harness.preview([{"event": "view_item"}], action_id=None),
                },
                action_id=second_id,
            )
        actions = [row for row in read_stream(harness.run)[0] if row["kind"] == "ACTION_COMMIT"]
        self.assertEqual(len(actions), 1)

    def test_complete_retry_reuses_the_exact_committed_action_and_feedback(self) -> None:
        harness = V5Harness(
            self.root,
            events=[
                default_event("E-view_item", "view_item"),
                default_event("E-add_to_cart", "add_to_cart"),
            ],
        )
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        action_id = started["action"]["data"]["action_id"]
        payload = {"event": "view_item"}
        bundle = {
            "binding": harness.binding(),
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "network": harness.network(["view_item"], action_id=action_id, payloads=[payload]),
            "preview": harness.preview([payload], action_id=None),
            "coverage": harness.coverage("E-view_item", [action_id]),
        }
        first = complete_action(harness.run, bundle, action_id=action_id)
        record_count = len(read_stream(harness.run)[0])
        second = complete_action(harness.run, bundle, action_id=action_id)
        self.assertEqual(len(read_stream(harness.run)[0]), record_count)
        self.assertEqual(first["commit_record_id"], second["commit_record_id"])
        self.assertEqual(first["sync_record_id"], second["sync_record_id"])
        self.assertEqual(
            first["events"][0]["feedback_record_id"],
            second["events"][0]["feedback_record_id"],
        )
        evidence_names = {path.name for path in (harness.run / "evidence").iterdir()}
        changed = json.loads(json.dumps(bundle))
        changed["page"]["states"][0]["url"] = "https://shop.example.test/changed"
        with self.assertRaisesRegex(StateError, "exact original bundle"):
            complete_action(harness.run, changed, action_id=action_id)
        self.assertEqual(len(read_stream(harness.run)[0]), record_count)
        self.assertEqual(
            {path.name for path in (harness.run / "evidence").iterdir()}, evidence_names
        )

        later = next_action(harness.run, event_ids=["E-add_to_cart"])
        later_id = later["action"]["data"]["action_id"]
        later_payload = {"event": "add_to_cart"}
        later_bundle = {
            "binding": harness.binding(),
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "network": harness.network(
                ["add_to_cart"], action_id=later_id, payloads=[later_payload]
            ),
            "preview": harness.preview([later_payload], action_id=None),
            "coverage": harness.coverage("E-add_to_cart", [later_id]),
        }
        later_first = complete_action(harness.run, later_bundle, action_id=later_id)
        later_count = len(read_stream(harness.run)[0])
        later_second = complete_action(harness.run, later_bundle, action_id=later_id)
        self.assertEqual(len(read_stream(harness.run)[0]), later_count)
        self.assertEqual(later_first["commit_record_id"], later_second["commit_record_id"])

    def test_unauthorized_reload_is_preserved_as_operator_block_not_auto_repeat(self) -> None:
        harness = V5Harness(self.root)
        action_id = harness.begin(mode="OBSERVE_CURRENT", document_policy="FORBIDDEN")
        harness.bump_operations(reloads=1)
        committed = harness.commit(action_id, [{"event": "view_item"}])
        violations = committed["execution_violations"]
        self.assertTrue(any(row["code"] == "execution.reloads_exceeded" for row in violations))
        result = harness.sync(
            ["E-view_item"],
            [{"event": "view_item"}],
            action_id=action_id,
            coverage=harness.coverage("E-view_item", [action_id]),
        )["events"][0]
        execution = next(
            row
            for row in result["inspections"]
            if row["target"].get("check") == "execution_protocol"
        )
        self.assertEqual(execution["status"], "BLOCKED")
        self.assertEqual(result["domains"]["behavior"]["status"], "BLOCKED")
        records, _ = read_stream(harness.run)
        self.assertEqual(sum(row["kind"] == "ACTION_BEGIN" for row in records), 1)

    def test_repeated_preflight_and_preview_collection_are_operator_blocks(self) -> None:
        harness = V5Harness(self.root)
        action_id = harness.begin()
        harness.bump_operations(
            full_preflights=1,
            preview_summary_reads=2,
            preview_retries=2,
        )
        committed = harness.commit(action_id, [{"event": "view_item"}])
        codes = {row["code"] for row in committed["execution_violations"]}
        self.assertTrue(
            {
                "execution.full_preflights_exceeded",
                "execution.preview_summary_reads_exceeded",
                "execution.preview_retries_exceeded",
            }.issubset(codes)
        )

    def test_one_natural_navigation_and_exact_rebind_are_allowed(self) -> None:
        harness = V5Harness(self.root)
        action_id = harness.begin(mode="INTERACT_ONCE", document_policy="NATURAL_ALLOWED")
        harness.bump_operations(navigations=1)
        payload = {"event": "view_item"}
        datalayer = harness.datalayer([payload], action_id=action_id)
        for row in datalayer["records"]:
            row["documentId"] = "DOC-2"
        datalayer["document_id"] = "DOC-2"
        network = harness.network(["view_item"], action_id=action_id, payloads=[payload])
        network["document_id"] = "DOC-2"
        for row in network["requests"]:
            row["document_id"] = "DOC-2"
        from core.workflow import commit_action

        committed = commit_action(
            harness.run,
            {
                "binding": harness.binding(document_id="DOC-2"),
                "health": harness._health("after"),
                "page": {"states": [harness._page("after", document_id="DOC-2")]},
                "datalayer": datalayer,
                "network": network,
            },
            action_id=action_id,
        )
        self.assertEqual(committed["execution_violations"], [])
        preview = harness.preview([payload], action_id=action_id)
        for row in preview["events"]:
            row["document_id"] = "DOC-2"
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action_id,
            coverage=harness.coverage("E-view_item", [action_id]),
            preview_updates={},
        )["events"][0]
        execution = next(
            row
            for row in result["inspections"]
            if row["target"].get("check") == "execution_protocol"
        )
        self.assertEqual(execution["status"], "PASS")

    def test_complete_reports_missing_preview_as_blocked_instead_of_refusing_feedback(self) -> None:
        harness = V5Harness(self.root)
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        action_id = started["action"]["data"]["action_id"]
        completed = complete_action(
            harness.run,
            {
                "binding": harness.binding(),
                "page": {"states": [harness._page("after")]},
            },
            action_id=action_id,
        )
        self.assertEqual(completed["events"][0]["status"], "BLOCKED")
        self.assertIn("Preview evidence was omitted", completed["capture_warning"])
        records, _ = read_stream(harness.run)
        self.assertTrue(any(row["kind"] == "ACTION_COMMIT" for row in records))
        self.assertTrue(any(row["kind"] == "EVENT_FEEDBACK_ISSUED" for row in records))

    def test_complete_cannot_change_the_frozen_event_slice(self) -> None:
        harness = V5Harness(
            self.root,
            events=[
                default_event("E-view_item", "view_item"),
                default_event("E-add_to_cart", "add_to_cart"),
            ],
        )
        started = next_action(
            harness.run,
            harness.next_input(),
            event_ids=["E-view_item"],
        )
        action_id = started["action"]["data"]["action_id"]
        with self.assertRaisesRegex(StateError, "exactly match the frozen action card"):
            complete_action(
                harness.run,
                {
                    "binding": harness.binding(),
                    "health": harness._health("after"),
                    "page": {"states": [harness._page("after")]},
                    "preview": harness.preview([{"event": "view_item"}], action_id=None),
                },
                action_id=action_id,
                event_ids=["E-add_to_cart"],
            )
        records, _ = read_stream(harness.run)
        self.assertFalse(any(row["kind"] == "ACTION_COMMIT" for row in records))

    def test_compact_checkpoint_keeps_every_layer_with_less_payload(self) -> None:
        harness = V5Harness(self.root)
        harness.execute_pass()
        full = status_view(harness.run)
        compact = compact_status_view(full)
        self.assertLess(len(json.dumps(compact)), len(json.dumps(full)))
        self.assertTrue(compact["events"][0]["layers"])
        self.assertTrue(
            all("status" in row and "layer" in row for row in compact["events"][0]["layers"])
        )

    def test_release_pilot_gate_rejects_slow_or_nonstandard_browser_execution(self) -> None:
        pilot = {
            "runtime": {
                "provider": "playwright_mcp",
                "browser_channel": "msedge",
                "profile_mode": "persistent",
                "headed": True,
                "self_check": "PASS",
            },
            "capabilities": {
                "stable_target_identity": True,
                "network_deltas": True,
                "preview_events": True,
            },
            "latency_seconds": {"first_action": 30, "first_feedback": 90},
            "operations": {
                "unsupported_method_errors": 0,
                "coordinate_actions": 0,
                "ad_hoc_evidence_files": 0,
                "unauthorized_reloads": 0,
                "scope_restarts": 0,
                "preview_passes_first_event": 1,
            },
            "quality": {
                "core_event_completed": True,
                "ordinary_event_completed": True,
                "mandatory_layers_complete": True,
                "continuous_anomaly_stream_complete": True,
                "per_event_feedback_emitted": True,
            },
        }
        path = self.root / "pilot.json"
        path.write_text(json.dumps(pilot), encoding="utf-8")
        self.assertEqual(validate_live_pilot(path), [])
        pilot["runtime"].pop("self_check")
        path.write_text(json.dumps(pilot), encoding="utf-8")
        self.assertEqual(validate_live_pilot(path), [])
        pilot["runtime"]["self_check"] = "FAIL"
        path.write_text(json.dumps(pilot), encoding="utf-8")
        self.assertTrue(any("self_check" in error for error in validate_live_pilot(path)))
        pilot["runtime"]["self_check"] = "PASS"
        pilot["latency_seconds"]["first_feedback"] = 301
        pilot["operations"]["unsupported_method_errors"] = 1
        path.write_text(json.dumps(pilot), encoding="utf-8")
        errors = validate_live_pilot(path)
        self.assertTrue(any("first_feedback exceeds" in error for error in errors))
        self.assertTrue(any("unsupported_method_errors" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
