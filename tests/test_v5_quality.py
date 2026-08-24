from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.v5_harness import V5Harness, default_event

from core.constants import utc_now
from core.workflow import commit_action, sync_preview


class QualityAndAnomalyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_unexpected_planned_event_between_interactions_fails_prior_flow(self) -> None:
        events = [
            default_event("E-list", "view_item_list"),
            default_event("E-item", "view_item"),
            default_event("E-cart", "add_to_cart"),
        ]
        harness = V5Harness(self.root, events=events)
        list_payload = {"event": "view_item_list", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}
        first = harness.begin(["E-list"])
        harness.commit(first, [list_payload])
        harness.sync(
            ["E-list"],
            [list_payload],
            action_id=first,
            coverage=harness.coverage("E-list", [first]),
        )

        interstitial = harness.datalayer(
            [{"event": "add_to_cart", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}],
            action_id=None,
            timestamp=utc_now(),
        )
        second = harness.begin(["E-item"], first_bundle_updates={"datalayer": interstitial})
        item_payload = {"event": "view_item", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}
        harness.commit(second, [item_payload])
        harness.sync(
            ["E-item"],
            [item_payload],
            action_id=second,
            coverage=harness.coverage("E-item", [second]),
        )

        revised = harness.feedback("E-list")
        self.assertEqual(revised["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "behavior.unexpected_event" and "add_to_cart" in row["reason"]
                for row in revised["inspections"]
            )
        )

    def test_preview_api_fallback_still_detects_unexpected_interjected_events(self) -> None:
        events = [
            default_event("E-list", "view_item_list"),
            default_event("E-cart", "add_to_cart"),
        ]
        harness = V5Harness(self.root, events=events)
        action = harness.begin(["E-list"])
        expected = {"event": "view_item_list"}
        unexpected = {"event": "add_to_cart"}
        commit_action(
            harness.run,
            {
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer(
                    [],
                    action_id=action,
                    capture_mode="late_snapshot",
                    document_start=False,
                ),
                "network": harness.network(["view_item_list"], action_id=action),
            },
            action_id=action,
        )
        result = harness.sync(
            ["E-list"],
            [expected, unexpected],
            action_id=action,
            coverage=harness.coverage("E-list", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "PASS")
        self.assertEqual(result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "behavior.unexpected_event" and "add_to_cart" in row["reason"]
                for row in result["inspections"]
            )
        )

    def test_material_state_update_between_interactions_is_reported_for_review(self) -> None:
        events = [default_event("E-list", "view_item_list"), default_event("E-item", "view_item")]
        harness = V5Harness(self.root, events=events)
        payload = {"event": "view_item_list", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}
        first = harness.begin(["E-list"])
        harness.commit(first, [payload])
        harness.sync(
            ["E-list"],
            payloads=[payload],
            action_id=first,
            coverage=harness.coverage("E-list", [first]),
        )
        state_update = harness.datalayer([{"ecommerce": None}], action_id=None, timestamp=utc_now())
        second = harness.begin(["E-item"], first_bundle_updates={"datalayer": state_update})
        item = {"event": "view_item", "ecommerce": {"items": [{"item_id": "SKU-1"}]}}
        harness.commit(second, [item])
        harness.sync(
            ["E-item"],
            [item],
            action_id=second,
            coverage=harness.coverage("E-item", [second]),
        )
        revised = harness.feedback("E-list")
        self.assertEqual(revised["domains"]["behavior"]["status"], "REVIEW")
        self.assertTrue(
            any(
                row["reason_code"] == "behavior.interstitial_state_update"
                for row in revised["inspections"]
            )
        )

    def test_duplicate_and_missing_event_occurrences_are_never_passed(self) -> None:
        duplicate = V5Harness(self.root / "duplicate")
        action = duplicate.begin()
        payload = {"event": "view_item"}
        duplicate.commit(action, [payload, payload])
        duplicate_result = duplicate.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=duplicate.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(duplicate_result["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "behavior.duplicate"
                for row in duplicate_result["inspections"]
            )
        )

        missing = V5Harness(self.root / "missing")
        action = missing.begin()
        missing.commit(action, [])
        missing_result = missing.sync(
            ["E-view_item"],
            [],
            action_id=action,
            coverage=missing.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(missing_result["domains"]["source"]["status"], "FAIL")
        self.assertEqual(missing_result["domains"]["gtm"]["status"], "FAIL")
        self.assertEqual(missing_result["status"], "FAIL")

    def test_populated_cart_with_empty_tracking_is_business_failure(self) -> None:
        event = default_event("E-cart", "view_cart")
        harness = V5Harness(self.root, events=[event])
        _, result = harness.execute_pass(
            event_id="E-cart",
            payload={"event": "view_cart", "ecommerce": {"items": []}},
            page_updates={"business": {"item_count": 2}},
        )
        self.assertEqual(result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "business.populated_cart_empty_payload"
                for row in result["inspections"]
            )
        )

    def test_visible_item_and_selected_checkout_values_must_match_tracking(self) -> None:
        stale = V5Harness(self.root / "stale")
        _, stale_result = stale.execute_pass(
            payload={"event": "view_item", "ecommerce": {"items": [{"item_id": "OLD"}]}},
            page_updates={"business": {"item_id": "VISIBLE"}},
        )
        self.assertEqual(stale_result["domains"]["behavior"]["status"], "FAIL")

        shipping_event = default_event("E-shipping", "add_shipping_info")
        shipping_event["requirements"].append(
            {
                "field_path": "shipping_tier",
                "match_rule": "one_of",
                "allowed_values": ["standard", "express"],
                "expected_type": "string",
            }
        )
        shipping = V5Harness(self.root / "shipping", events=[shipping_event])
        _, shipping_result = shipping.execute_pass(
            event_id="E-shipping",
            payload={"event": "add_shipping_info", "shipping_tier": "standard"},
            page_updates={"business": {"selected_shipping_tier": "express"}},
        )
        self.assertEqual(shipping_result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "business.context_value_mismatch"
                for row in shipping_result["inspections"]
            )
        )

    def test_checkout_items_must_match_the_independent_cart_state(self) -> None:
        event = default_event("E-checkout", "begin_checkout")
        harness = V5Harness(self.root, events=[event])
        _, result = harness.execute_pass(
            event_id="E-checkout",
            payload={
                "event": "begin_checkout",
                "ecommerce": {"items": [{"item_id": "SKU-1"}]},
            },
            page_updates={"business": {"cart_item_ids": ["SKU-1", "SKU-2"]}},
        )
        self.assertEqual(result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "business.ecommerce_items_mismatch"
                for row in result["inspections"]
            )
        )

    def test_media_events_require_and_match_independent_player_state(self) -> None:
        event = default_event("E-video", "video_progress")
        mismatch = V5Harness(self.root / "mismatch", events=[event])
        _, mismatch_result = mismatch.execute_pass(
            event_id="E-video",
            payload={"event": "video_progress", "video_percent": 25},
            page_updates={
                "business": {
                    "media": {
                        "player_state": "playing",
                        "progress_percent": 50,
                        "media_title": "Demo",
                    }
                }
            },
        )
        self.assertEqual(mismatch_result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "business.media_progress_mismatch"
                for row in mismatch_result["inspections"]
            )
        )

        unanchored = V5Harness(self.root / "unanchored", events=[event])
        _, unanchored_result = unanchored.execute_pass(
            event_id="E-video",
            payload={"event": "video_progress", "video_percent": 25},
            page_updates={"business": {}},
        )
        self.assertEqual(unanchored_result["domains"]["behavior"]["status"], "BLOCKED")
        self.assertTrue(
            any(
                row["reason_code"] == "business.media_state_unobserved"
                for row in unanchored_result["inspections"]
            )
        )

    def test_repeated_purchase_transaction_is_detected_across_actions(self) -> None:
        event = default_event("E-purchase", "purchase")
        harness = V5Harness(self.root, events=[event])
        payload = {
            "event": "purchase",
            "ecommerce": {
                "transaction_id": "ORDER-42",
                "items": [{"item_id": "SKU-1"}],
            },
        }

        first = harness.begin(["E-purchase"], scenario_id="first-order-view")
        harness.commit(
            first,
            [payload],
            page_updates={
                "business": {
                    "transaction_id": "ORDER-42",
                    "order_item_ids": ["SKU-1"],
                },
                "completion": {"confirmed": True, "signal": "order confirmation"},
            },
        )
        harness.sync(
            ["E-purchase"],
            [payload],
            action_id=first,
            coverage=harness.coverage("E-purchase", [first], scenario_id="first-order-view"),
        )

        second = harness.begin(["E-purchase"], scenario_id="confirmation-revisit")
        harness.commit(
            second,
            [payload],
            page_updates={
                "business": {
                    "transaction_id": "ORDER-42",
                    "order_item_ids": ["SKU-1"],
                },
                "completion": {"confirmed": True, "signal": "order confirmation"},
            },
        )
        result = harness.sync(
            ["E-purchase"],
            [payload],
            action_id=second,
            coverage=harness.coverage(
                "E-purchase",
                [first, second],
                scenario_id="confirmation-revisit",
            ),
        )["events"][0]

        self.assertEqual(result["domains"]["behavior"]["status"], "FAIL")
        self.assertTrue(
            any(
                row["reason_code"] == "business.repeated_transaction"
                for row in result["inspections"]
            )
        )

    def test_success_events_require_independent_business_confirmation(self) -> None:
        lead_event = default_event("E-lead", "generate_lead")
        lead = V5Harness(self.root / "lead", events=[lead_event])
        _, lead_result = lead.execute_pass(
            event_id="E-lead",
            payload={"event": "generate_lead"},
            page_updates={"completion": {}},
        )
        self.assertEqual(lead_result["domains"]["behavior"]["status"], "FAIL")

        purchase_event = default_event("E-purchase", "purchase")
        purchase = V5Harness(self.root / "purchase", events=[purchase_event])
        _, purchase_result = purchase.execute_pass(
            event_id="E-purchase",
            payload={"event": "purchase", "transaction_id": "T-1"},
            page_updates={"completion": {"succeeded": True}},
        )
        self.assertEqual(purchase_result["domains"]["behavior"]["status"], "FAIL")

    def test_late_snapshot_and_accumulated_state_cannot_replace_authoritative_source(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        bundle = {
            "health": harness._health("after"),
            "page": {"states": [harness._page("after")]},
            "datalayer": harness.datalayer(
                [payload],
                action_id=action,
                capture_mode="late_snapshot",
                document_start=False,
            ),
            "network": harness.network(["view_item"], action_id=action),
        }
        commit_action(harness.run, bundle, action_id=action)
        preview = harness.preview([payload], action_id=action)
        preview["events"][0]["api_call"] = None
        preview["events"][0]["completeness"]["api_call"] = False
        result = sync_preview(
            harness.run,
            {
                "preview": preview,
                "coverage": harness.coverage("E-view_item", [action]),
            },
            event_ids=["E-view_item"],
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "BLOCKED")
        self.assertEqual(result["domains"]["behavior"]["status"], "BLOCKED")

    def test_fully_expanded_preview_api_call_is_an_authoritative_source_fallback(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        commit_action(
            harness.run,
            {
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer(
                    [payload],
                    action_id=action,
                    capture_mode="late_snapshot",
                    document_start=False,
                ),
                "network": harness.network(["view_item"], action_id=action),
            },
            action_id=action,
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "PASS")
        self.assertEqual(result["domains"]["behavior"]["status"], "PASS")
        source_rows = [row for row in result["inspections"] if row["domain"] == "source"]
        self.assertTrue(all(row["status"] == "PASS" for row in source_rows))

    def test_failed_browser_transport_is_delivery_failure(self) -> None:
        harness = V5Harness(self.root)
        action = harness.begin()
        payload = {"event": "view_item"}
        harness.commit(
            action,
            [payload],
            network_updates={"outcome": "failed"},
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(result["domains"]["delivery"]["status"], "FAIL")
        self.assertTrue(
            any(row["reason_code"] == "delivery.transport_failed" for row in result["inspections"])
        )

    def test_source_value_cannot_hide_empty_tag_runtime_or_request_parameter(self) -> None:
        event = default_event()
        event["requirements"].append(
            {
                "field_path": "currency",
                "match_rule": "equals",
                "expected_value": "EUR",
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        action = harness.begin()
        payload = {"event": "view_item", "currency": "EUR"}
        commit_action(
            harness.run,
            {
                "health": harness._health("after"),
                "page": {"states": [harness._page("after")]},
                "datalayer": harness.datalayer([payload], action_id=action),
                # Complete transport capture deliberately omits currency.
                "network": harness.network(["view_item"], action_id=action),
            },
            action_id=action,
        )
        preview = harness.preview([payload], action_id=action)
        preview["events"][0]["tags"][0]["runtime_parameters"] = {"event": "view_item"}
        result = sync_preview(
            harness.run,
            {
                "preview": preview,
                "coverage": harness.coverage("E-view_item", [action]),
            },
            event_ids=["E-view_item"],
        )["events"][0]
        self.assertEqual(result["domains"]["source"]["status"], "PASS")
        self.assertEqual(result["domains"]["gtm"]["status"], "FAIL")
        self.assertEqual(result["domains"]["delivery"]["status"], "FAIL")
        codes = {row["reason_code"] for row in result["inspections"]}
        self.assertIn("delivery.runtime_parameter_absent", codes)
        self.assertIn("delivery.request_parameter.value.absent", codes)
        self.assertIn("gtm.effective_mapping_absent", codes)

    def test_wildcard_item_requirements_validate_every_cart_item(self) -> None:
        event = default_event("E-cart", "view_cart")
        event["requirements"].extend(
            [
                {
                    "field_path": "ecommerce.items[].item_id",
                    "match_rule": "present",
                    "expected_type": "string",
                },
                {
                    "field_path": "ecommerce.items[].price",
                    "match_rule": "present",
                    "expected_type": "number",
                },
            ]
        )
        harness = V5Harness(self.root, events=[event])
        payload = {
            "event": "view_cart",
            "ecommerce": {
                "items": [
                    {"item_id": "SKU-1", "price": 10.0},
                    {"item_id": "SKU-2", "price": 20.0},
                ]
            },
        }
        _, result = harness.execute_pass(event_id="E-cart", payload=payload)
        self.assertEqual(result["status"], "PASS")
        item_rows = [row for row in result["inspections"] if "items[]" in row["inspection_target"]]
        self.assertTrue(item_rows)
        self.assertTrue(all(row["status"] == "PASS" for row in item_rows))

    def test_consent_override_only_blocks_and_denied_send_fails(self) -> None:
        event = default_event()
        event["tags"][0]["consent_requirements"] = ["analytics_storage"]
        override = V5Harness(self.root / "override", events=[event])
        action = override.begin()
        payload = {"event": "view_item"}
        override.commit(
            action,
            [payload],
            lifecycle={
                "action_id": action,
                "complete": True,
                "events": [],
                "errors": [],
                "consent_transitions": [
                    {
                        "action_id": action,
                        "kind": "update",
                        "method": "override",
                        "state": {"analytics_storage": "granted"},
                    }
                ],
            },
        )
        override_result = override.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=override.coverage("E-view_item", [action]),
            preview_updates={"consent": {"analytics_storage": "granted"}},
        )["events"][0]
        self.assertTrue(
            any(
                row["reason_code"] == "consent.override_only"
                for row in override_result["inspections"]
            )
        )

        denied = V5Harness(self.root / "denied", events=[event])
        action = denied.begin()
        denied.commit(
            action,
            [payload],
            lifecycle={
                "action_id": action,
                "complete": True,
                "events": [],
                "errors": [],
                "consent_transitions": [
                    {
                        "action_id": action,
                        "kind": "user_choice",
                        "method": "natural",
                        "state": {"analytics_storage": "denied"},
                    }
                ],
            },
        )
        denied_result = denied.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=denied.coverage("E-view_item", [action]),
            preview_updates={"consent": {"analytics_storage": "denied"}},
        )["events"][0]
        self.assertTrue(
            any(
                row["reason_code"] == "consent.denied_tag_or_send"
                for row in denied_result["inspections"]
            )
        )
        self.assertEqual(denied_result["status"], "FAIL")

    def test_fresh_organic_acquisition_is_simulated_with_evidence_not_refused(self) -> None:
        event = default_event()
        event["journey"] = {
            "url": "https://shop.example.test/product",
            "acquisition": {"source": "google"},
        }
        harness = V5Harness(self.root, events=[event])
        isolated_capability = harness.capability()
        isolated_capability["runtime"]["profile_mode"] = "isolated"
        action = harness.begin(
            fresh_context_required=True,
            first_bundle_updates={"capability": isolated_capability},
        )
        evidence_refs = list(harness.last_begin_result["captures"])
        payload = {"event": "view_item"}
        harness.commit(
            action,
            [payload],
            acquisition_context={
                "method": "CONTROLLED_NAVIGATION",
                "fresh": True,
                "source": "google",
                "referrer": "https://www.google.com/",
                "landing_url": "https://shop.example.test/product",
                "evidence_refs": evidence_refs,
            },
        )
        result = harness.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=harness.coverage("E-view_item", [action]),
        )["events"][0]
        acquisition = next(
            row for row in result["inspections"] if row["reason_code"].startswith("acquisition.")
        )
        self.assertEqual(acquisition["status"], "PASS")

    def test_wrong_natural_container_fails_unless_override_is_explicitly_approved(self) -> None:
        wrong = V5Harness(self.root / "wrong")
        action = wrong.begin(
            first_bundle_updates={
                "binding": wrong.binding(
                    natural_container_ids=["GTM-WRONG"],
                    active_container_ids=["GTM-WRONG"],
                )
            }
        )
        payload = {"event": "view_item"}
        wrong.commit(action, [payload])
        wrong_result = wrong.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=wrong.coverage("E-view_item", [action]),
        )["events"][0]
        self.assertEqual(wrong_result["domains"]["reality"]["status"], "BLOCKED")
        self.assertEqual(wrong_result["domains"]["source"]["status"], "BLOCKED")
        self.assertEqual(wrong_result["domains"]["gtm"]["status"], "BLOCKED")
        self.assertEqual(wrong_result["domains"]["delivery"]["status"], "BLOCKED")

        approved = V5Harness(self.root / "approved", scope={"allow_container_override": True})
        action = approved.begin(
            first_bundle_updates={
                "binding": approved.binding(
                    natural_container_ids=["GTM-WRONG"],
                    active_container_ids=["GTM-EXPECTED"],
                    override_container_ids=["GTM-EXPECTED"],
                )
            }
        )
        approved.commit(action, [payload])
        approved_result = approved.sync(
            ["E-view_item"],
            [payload],
            action_id=action,
            coverage=approved.coverage("E-view_item", [action]),
        )["events"][0]
        binding = next(
            row for row in approved_result["inspections"] if row["reason_code"] == "binding.current"
        )
        self.assertEqual(binding["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
