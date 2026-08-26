from __future__ import annotations

import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from helpers import action_fixture, bundle_fixture, event_fixture

from judge import judge_event
from recette import feedback_markdown


def statuses(result: dict) -> dict[str, str]:
    return {layer["layer"]: layer["status"] for layer in result["layers"]}


class JudgeTests(unittest.TestCase):
    def test_all_five_layers_pass(self) -> None:
        result = judge_event(event_fixture(), action_fixture(), bundle_fixture())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["layers"]), 5)
        self.assertEqual(set(statuses(result).values()), {"PASS"})

    def test_coherent_chain_fails_when_reality_quantity_differs(self) -> None:
        bundle = bundle_fixture(quantity=2)
        bundle["reality"]["expected"]["ecommerce.items[].quantity"] = [1]
        result = judge_event(event_fixture(), action_fixture(), bundle)
        layer_status = statuses(result)
        self.assertEqual(layer_status["Page/action reality"], "PASS")
        self.assertEqual(layer_status["Data Layer API Call"], "FAIL")
        self.assertEqual(layer_status["GTM Tags"], "FAIL")
        self.assertEqual(layer_status["Browser request"], "FAIL")

    def test_missing_tag_mapping_for_planned_fields_fails(self) -> None:
        bundle = bundle_fixture()
        bundle["gtm"]["tags"][0]["mapped_paths"] = ["event"]
        bundle["gtm"]["tags"][0]["mappings"] = {"event": "view_item"}
        result = judge_event(event_fixture(), action_fixture(), bundle)
        layer = next(item for item in result["layers"] if item["layer"] == "GTM Tags")
        missing = [
            check["path"]
            for check in layer["checks"]
            if check["check"] == "gtm.mapping" and check["status"] == "FAIL"
        ]
        self.assertEqual(len(missing), 3)

    def test_parent_ecommerce_mapping_covers_nested_planned_fields(self) -> None:
        bundle = bundle_fixture()
        bundle["gtm"]["tags"][0]["mapped_paths"] = []
        bundle["gtm"]["tags"][0]["mappings"] = {
            "event": "view_item",
            "ecommerce": "Data Layer",
        }
        result = judge_event(event_fixture(), action_fixture(), bundle)
        mapping_statuses = [
            check["status"]
            for layer in result["layers"]
            if layer["layer"] == "GTM Tags"
            for check in layer["checks"]
            if check["check"] == "gtm.mapping"
        ]
        self.assertEqual(mapping_statuses, ["PASS", "PASS", "PASS"])

    def test_network_duplicate_is_derived_from_logical_hit_identity(self) -> None:
        bundle = bundle_fixture()
        bundle["network"]["requests"].append(deepcopy(bundle["network"]["requests"][0]))
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["Browser request"], "FAIL")

    def test_unknown_request_transport_is_blocked(self) -> None:
        bundle = bundle_fixture()
        request = bundle["network"]["requests"][0]
        request["status"] = None
        request["sent"] = False
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["Browser request"], "BLOCKED")

    def test_repeated_tag_across_causal_rows_is_a_duplicate(self) -> None:
        bundle = bundle_fixture()
        repeated = deepcopy(bundle["gtm"]["tags"][0])
        repeated["event_cursor"] = 2
        bundle["gtm"]["tags"].append(repeated)
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["GTM Tags"], "FAIL")

    def test_wrong_delivery_event_identity_fails_tag_and_request(self) -> None:
        bundle = bundle_fixture()
        bundle["gtm"]["tags"][0]["runtime"]["event"] = "add_to_cart"
        bundle["network"]["requests"][0]["parameters"]["event"] = "add_to_cart"
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["GTM Tags"], "FAIL")
        self.assertEqual(statuses(result)["Browser request"], "FAIL")

    def test_tracking_plan_destination_mismatch_fails_tag_and_request(self) -> None:
        bundle = bundle_fixture()
        bundle["gtm"]["tags"][0]["runtime"]["destination_id"] = "G-WRONG"
        bundle["network"]["requests"][0]["parameters"]["destination_id"] = "G-WRONG"
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["GTM Tags"], "FAIL")
        self.assertEqual(statuses(result)["Browser request"], "FAIL")

    def test_observed_destinations_must_agree_when_plan_has_none(self) -> None:
        event = event_fixture()
        event["expected_destination_id"] = None
        bundle = bundle_fixture()
        result = judge_event(event, action_fixture(), bundle)
        self.assertEqual(statuses(result)["GTM Tags"], "PASS")
        self.assertEqual(statuses(result)["Browser request"], "PASS")
        bundle["network"]["requests"][0]["parameters"]["destination_id"] = "G-OTHER"
        mismatch = judge_event(event, action_fixture(), bundle)
        self.assertEqual(statuses(mismatch)["GTM Tags"], "FAIL")
        self.assertEqual(statuses(mismatch)["Browser request"], "FAIL")

    def test_wrong_selected_api_call_identity_fails_source(self) -> None:
        bundle = bundle_fixture()
        bundle["source"]["selected"]["payload"]["event"] = "add_to_cart"
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["Data Layer API Call"], "FAIL")

    def test_immediate_feedback_has_five_layers_and_expected_observed_detail(self) -> None:
        bundle = bundle_fixture(quantity=2)
        bundle["reality"]["expected"]["ecommerce.items[].quantity"] = [1]
        result = judge_event(event_fixture(), action_fixture(), bundle)
        feedback = feedback_markdown(result)
        for layer in (
            "Page/action reality",
            "Data Layer API Call",
            "GTM Tags",
            "Browser request",
            "Surrounding behavior",
        ):
            self.assertIn(f"| {layer} |", feedback)
        self.assertIn("expected=", feedback)
        self.assertIn("observed=", feedback)

    def test_gtm_display_labels_resolve_to_plan_fields(self) -> None:
        bundle = bundle_fixture()
        tag = bundle["gtm"]["tags"][0]
        tag["mapped_paths"] = []
        tag["mappings"] = {
            "Item Name": "{{DLV item_name}}",
            "Quantity": "{{DLV quantity}}",
            "Currency": "{{DLV currency}}",
        }
        tag["runtime"] = {
            "Event Name": "view_item",
            "Measurement ID": "G-TEST",
            "Item Name": "Synthetic product",
            "Quantity": 1,
            "Currency": "EUR",
        }
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["GTM Tags"], "PASS")

    def test_dead_page_fails_even_when_tracking_chain_passes(self) -> None:
        bundle = bundle_fixture()
        bundle["reality"]["page"]["status_code"] = 404
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["Page/action reality"], "FAIL")
        self.assertEqual(result["status"], "FAIL")

    def test_duplicate_and_interjected_business_events_are_exposed(self) -> None:
        bundle = bundle_fixture()
        duplicate = deepcopy(bundle["behavior"]["messages"][0])
        duplicate["cursor"] = 2
        unexpected = {
            "cursor": 3,
            "event_name": "add_to_cart",
            "payload": {"event": "add_to_cart"},
            "business": True,
        }
        bundle["behavior"]["messages"].extend([duplicate, unexpected])
        bundle["preview_cursor"] = 3
        result = judge_event(event_fixture(), action_fixture(), bundle)
        layer = next(item for item in result["layers"] if item["layer"] == "Surrounding behavior")
        by_check = {check["check"]: check["status"] for check in layer["checks"]}
        self.assertEqual(by_check["behavior.duplicate_event"], "FAIL")
        self.assertEqual(by_check["behavior.interjected_event"], "REVIEW")

    def test_companion_business_event_is_reviewed(self) -> None:
        bundle = bundle_fixture()
        companion = {
            "cursor": 2,
            "event_name": "page_view",
            "payload": {"event": "page_view"},
            "business": True,
            "allowed": True,
        }
        bundle["behavior"]["messages"].append(companion)
        bundle["preview_cursor"] = 2
        result = judge_event(event_fixture(), action_fixture(), bundle)
        self.assertEqual(statuses(result)["Surrounding behavior"], "REVIEW")

    def test_value_outside_tracking_plan_allowed_values_fails(self) -> None:
        event = event_fixture()
        event["fields"][-1] = {
            "path": "ecommerce.currency",
            "type": "string",
            "required": True,
            "rule": "one_of",
            "allowed_values": ["EUR", "GBP"],
        }
        bundle = bundle_fixture()
        for surface in ("source", "gtm", "network"):
            if surface == "source":
                bundle[surface]["selected"]["payload"]["ecommerce"]["currency"] = "CHF"
            elif surface == "gtm":
                bundle[surface]["tags"][0]["runtime"]["ecommerce"]["currency"] = "CHF"
            else:
                bundle[surface]["requests"][0]["parameters"]["ecommerce"]["currency"] = "CHF"
        bundle["reality"]["expected"]["ecommerce.currency"] = "CHF"
        result = judge_event(event, action_fixture(), bundle)
        self.assertEqual(statuses(result)["Data Layer API Call"], "FAIL")
        self.assertEqual(statuses(result)["GTM Tags"], "FAIL")
        self.assertEqual(statuses(result)["Browser request"], "FAIL")

    def test_stale_preview_message_fails_surrounding_behavior(self) -> None:
        action = action_fixture()
        action["preview_cursor"] = 2
        bundle = bundle_fixture()
        bundle["preview_cursor"] = 3
        result = judge_event(event_fixture(), action, bundle)
        self.assertEqual(statuses(result)["Surrounding behavior"], "FAIL")

    def test_incomplete_absence_is_blocked_not_false_client_failure(self) -> None:
        bundle = bundle_fixture()
        bundle["source"].update(
            {"complete": False, "attributable": True, "occurrence_count": 0, "selected": None}
        )
        bundle["gtm"].update({"complete": False, "attributable": True, "tags": []})
        bundle["network"].update({"complete": False, "attributable": True, "requests": []})
        result = judge_event(event_fixture(), action_fixture(), bundle)
        layer_status = statuses(result)
        self.assertEqual(layer_status["Data Layer API Call"], "BLOCKED")
        self.assertEqual(layer_status["GTM Tags"], "BLOCKED")
        self.assertEqual(layer_status["Browser request"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
