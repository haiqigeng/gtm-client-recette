from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.v5_harness import V5Harness, default_event

from core.capture import capture_value
from core.constants import utc_now
from core.plan import normalize_plan
from core.report import telemetry_view
from core.state import StateError, load_plan, read_stream
from core.workflow import commit_action, sync_preview


class FastPathRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_generic_scope_is_resolved_from_plan_not_used_as_runtime_identity(self) -> None:
        harness = V5Harness(
            self.root,
            scope={
                "tag_scope": ["everything specified in the tracking plan; client-side only"],
                "destination": ["all planned browser destinations"],
            },
        )
        scope = harness.plan["scope"]
        event = harness.plan["events"][0]
        self.assertEqual(scope["tag_scope"], [])
        self.assertEqual(scope["destination"], [])
        self.assertEqual(scope["tag_scope_mode"], "plan_declared")
        self.assertEqual(event["tags"][0]["tag_id"], "GA4-event")
        self.assertEqual(event["destinations"], ["G-TEST123"])
        self.assertTrue(event["executable"])

        no_identity = default_event()
        no_identity["tags"] = []
        source = self.root / "no-identity.json"
        source.write_text(json.dumps({"events": [no_identity]}), encoding="utf-8")
        with self.assertRaisesRegex(StateError, "broad plan-declared tag scope"):
            normalize_plan(
                source,
                scope={
                    "approved": True,
                    "origins": ["https://shop.example.test"],
                    "tag_scope": ["everything specified in the tracking plan"],
                    "destination": ["all planned browser destinations"],
                },
            )

        media_event = default_event()
        media_event["tags"] = [
            {
                "tag_id": "Meta-lead",
                "tag_name": "Meta lead",
                "category": "Meta Pixel",
                "expected": "fire",
                "browser_send_required": False,
            }
        ]
        media = V5Harness(
            self.root / "media",
            events=[media_event],
            scope={"tag_scope": ["Meta Pixel"], "destination": []},
        )
        self.assertEqual(media.plan["scope"]["tag_scope"], ["Meta Pixel"])
        self.assertEqual(media.plan["events"][0]["tags"][0]["tag_id"], "Meta-lead")

    def test_one_action_per_scenario_requires_a_structured_retest_basis(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        harness.commit(action, [{"event": "view_item"}])
        with self.assertRaisesRegex(StateError, "structured retest basis"):
            harness.begin()
        distinct = harness.begin(scenario_id="alternate-product")
        self.assertTrue(distinct.startswith("A-"))

        other = V5Harness(self.root / "retest")
        first = other.begin()
        committed = other.commit(first, [{"event": "view_item"}])
        repeated = other.begin(
            retest_basis={
                "type": "EVIDENCE_DEFECT",
                "record_id": committed["commit"]["record_id"],
                "reason": "Corrected a proven capture defect",
            }
        )
        self.assertTrue(repeated.startswith("A-"))

    def test_phase_bundles_reject_repeated_handshake_and_stale_after_state(self) -> None:
        events = [default_event(), default_event("E-add", "add_to_cart")]
        harness = V5Harness(self.root, events=events)
        first = harness.begin(["E-view_item"])
        harness.commit(first, [{"event": "view_item"}])
        with self.assertRaisesRegex(StateError, "workflow phase"):
            harness.begin(
                ["E-add"],
                first_bundle_updates={"health": harness._health("before")},
            )
        with self.assertRaisesRegex(StateError, "workflow phase"):
            sync_preview(
                harness.run,
                {
                    "preview": harness.preview([], action_id=first),
                    "health": harness._health("after"),
                },
                event_ids=["E-view_item"],
            )

        stale = V5Harness(self.root / "stale")
        action = stale.begin()
        bundle = {
            "health": {**stale._health("after"), "observed_at": "2020-01-01T00:00:00Z"},
            "page": {"states": [{**stale._page("after"), "timestamp": "2020-01-01T00:00:00Z"}]},
        }
        with self.assertRaisesRegex(StateError, "predates the action"):
            commit_action(stale.run, bundle, action_id=action)
        self.assertFalse(
            any(record["kind"] == "ACTION_COMMIT" for record in read_stream(stale.run)[0])
        )

    def test_delayed_trigger_group_is_joined_without_mixing_exact_message_layers(self) -> None:
        event = default_event()
        event["requirements"].append(
            {
                "requirement_id": "currency",
                "field_path": "ecommerce.currency",
                "match_rule": "equals",
                "expected_value": "EUR",
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        payload = {"event": "view_item", "ecommerce": {"currency": "EUR"}}
        action = harness.begin()
        harness.commit(action, [payload])
        self.assertFalse(
            any(row["kind"] == "EVENT_FEEDBACK_ISSUED" for row in read_stream(harness.run)[0])
        )

        preview = harness.preview([payload], action_id=action)
        source = preview["events"][0]
        source.update(
            {
                "full_tag_summary": False,
                "fired_tags": [],
                "not_fired_tags": [],
                "tags": [],
            }
        )
        source["completeness"].update(
            {
                "fired_list": False,
                "not_fired_set": False,
                "tag_details": False,
                "runtime_parameters": False,
            }
        )
        trigger_index = source["index"] + 7
        preview["events"].extend(
            [
                {
                    "index": source["index"] + offset,
                    "epoch": source["epoch"],
                    "timestamp": utc_now(),
                    "action_id": action,
                    "event_name": name,
                    "history_stable": True,
                    "full_tag_summary": False,
                    "fired_tags": [],
                    "not_fired_tags": [],
                    "tags": [],
                    "completeness": {"event_list": True},
                }
                for offset, name in enumerate(
                    ("Set", "Consent Update", "cmp-ready", "DOM Ready", "Message", "Set"),
                    start=1,
                )
            ]
        )
        preview["events"].append(
            {
                "index": trigger_index,
                "epoch": source["epoch"],
                "timestamp": utc_now(),
                "action_id": action,
                "event_name": "Trigger Group",
                "history_stable": True,
                "full_tag_summary": True,
                "api_call": {"arguments": [{"event": "gtm.triggerGroup"}], "complete": True},
                "fired_tags": ["GA4-event"],
                "not_fired_tags": [],
                "tags": [
                    {
                        "tag_id": "GA4-event",
                        "tag_name": "GA4 event",
                        "category": "GA4",
                        "fired": True,
                        "firing_count": 1,
                        "configuration": {"measurement_id": "G-TEST123"},
                        "runtime_parameters": payload,
                        "runtime_complete": True,
                    }
                ],
                "completeness": {
                    "event_list": True,
                    "api_call": True,
                    "fired_list": True,
                    "not_fired_set": True,
                    "tag_details": True,
                    "runtime_parameters": True,
                },
            }
        )
        coverage = harness.coverage("E-view_item", [action])
        result = sync_preview(
            harness.run,
            {"preview": preview, "coverage": coverage},
            event_ids=["E-view_item"],
        )["events"][0]
        checks = {
            (row["target"].get("check"), row["target"].get("path")): row["status"]
            for row in result["inspections"]
        }
        self.assertEqual(checks[("data_layer_state", "ecommerce.currency")], "PASS")
        self.assertEqual(checks[("resolved_variable", "ecommerce.currency")], "PASS")
        self.assertEqual(checks[("effective_mapping", "ecommerce.currency")], "PASS")
        self.assertEqual(checks[("runtime_parameter", "ecommerce.currency")], "PASS")
        self.assertEqual(checks[("request_parameter", "ecommerce.currency")], "PASS")
        self.assertEqual(checks[("tag_firing", None)], "PASS")

    def test_network_safety_is_limited_to_the_concerned_event_requests(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        harness.commit(action, [payload])
        capture_value(
            harness.run,
            "network",
            {
                "complete": True,
                "requests": [
                    {
                        "request_id": "NOISE-1",
                        "action_id": action,
                        "timestamp": utc_now(),
                        "url": "https://noise.example.test/collect",
                        "headers": {"content-type": "application/json"},
                        "post_data": '{"session_id":"secret-session"}',
                    }
                ],
            },
            source_id="unrelated-noise",
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["safety"]["status"], "PASS")

        concerned = V5Harness(self.root / "concerned")
        concerned_action = concerned.begin()
        concerned.commit(concerned_action, [payload])
        capture_value(
            concerned.run,
            "network",
            {
                "complete": True,
                "requests": [
                    {
                        "request_id": "GA4-SENSITIVE",
                        "action_id": concerned_action,
                        "timestamp": utc_now(),
                        "url": (
                            "https://www.google-analytics.com/g/collect?"
                            "tid=G-TEST123&en=view_item&ep.email=person%40example.test"
                        ),
                    }
                ],
            },
            source_id="concerned-sensitive-send",
        )
        concerned_result = concerned.sync(
            ["E-view_item"],
            [payload],
            action_id=concerned_action,
            coverage=concerned.coverage("E-view_item", [concerned_action]),
        )["events"][0]
        self.assertEqual(concerned_result["domains"]["safety"]["status"], "FAIL")

    def test_conflicting_transport_is_review_not_false_failure(self) -> None:
        harness = V5Harness(self.root)
        payload = {"event": "view_item"}
        action = harness.begin()
        network = harness.network(
            ["view_item"], action_id=action, payloads=[payload], outcome="aborted"
        )
        network["requests"][0]["response_status"] = 204
        commit_action(
            harness.run,
            {
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer([payload], action_id=action),
                "network": network,
            },
            action_id=action,
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        transport = [
            row
            for row in result["inspections"]
            if row["reason_code"] == "delivery.transport_conflicting_outcome"
        ]
        self.assertTrue(transport)
        self.assertTrue(all(row["status"] == "REVIEW" for row in transport))

    def test_telemetry_uses_latest_cumulative_counters_and_unique_evidence(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        for count in (1, 2):
            capture_value(
                harness.run,
                "health",
                {
                    **harness._health("after"),
                    "action_id": action,
                    "operations": {"navigations": count},
                },
                source_id=f"health-{count}",
            )
        preview = harness.preview([], action_id=action)
        capture_value(harness.run, "preview", preview, source_id="preview-one")
        capture_value(harness.run, "preview", preview, source_id="preview-two")
        records = read_stream(harness.run)[0]
        telemetry = telemetry_view(load_plan(harness.run), records)
        self.assertEqual(telemetry["navigations"], 2)
        self.assertEqual(telemetry["preview_captures"], 1)


if __name__ == "__main__":
    unittest.main()
