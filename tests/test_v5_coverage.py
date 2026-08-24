from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.v5_harness import V5Harness, default_event

from core.coverage import coverage_result, validate_coverage_annotation
from core.state import load_plan, read_stream


class ScenarioCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _execute_without_final_coverage(
        self,
        harness: V5Harness,
        event_id: str,
        payload: dict,
        scenario_id: str,
        values: dict,
        page_business: dict | None = None,
    ) -> str:
        action = harness.begin([event_id], scenario_id=scenario_id, scenario_values=values)
        harness.commit(
            action,
            [payload],
            page_updates={"business": page_business or {}},
        )
        harness.sync([event_id], [payload], action_id=action)
        return action

    def test_manageable_language_enum_tests_every_reachable_value(self) -> None:
        event = default_event("E-page", "page_view")
        event["requirements"].append(
            {
                "field_path": "page_language",
                "match_rule": "one_of",
                "allowed_values": ["en", "fr"],
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        en = self._execute_without_final_coverage(
            harness,
            "E-page",
            {"event": "page_view", "page_language": "en"},
            "english",
            {"page_language": "en"},
            {"page_language": "en"},
        )
        fr = self._execute_without_final_coverage(
            harness,
            "E-page",
            {"event": "page_view", "page_language": "fr"},
            "french",
            {"page_language": "fr"},
            {"page_language": "fr"},
        )
        review = harness.coverage(
            "E-page",
            [en, fr],
            dimensions=[
                {
                    "name": "page_language",
                    "kind": "manageable_finite",
                    "material": True,
                    "values": [
                        {"value": "en", "source": "plan"},
                        {"value": "fr", "source": "plan"},
                    ],
                }
            ],
            scenarios=[
                {
                    "scenario_id": "english",
                    "label": "English",
                    "role": "ORDINARY",
                    "values": {"page_language": "en"},
                    "action_ids": [en],
                },
                {
                    "scenario_id": "french",
                    "label": "French",
                    "role": "CONTRAST",
                    "values": {"page_language": "fr"},
                    "action_ids": [fr],
                },
            ],
        )
        harness.add_coverage(review)
        result = harness.feedback("E-page")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([row["status"] for row in result["scenarios"]], ["PASS", "PASS"])

    def test_enum_value_must_match_the_specific_scenario_context(self) -> None:
        event = default_event("E-page", "page_view")
        event["requirements"].append(
            {
                "field_path": "page_language",
                "match_rule": "one_of",
                "allowed_values": ["en", "fr"],
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        action = harness.begin(
            ["E-page"], scenario_id="english", scenario_values={"page_language": "en"}
        )
        payload = {"event": "page_view", "page_language": "fr"}
        harness.commit(action, [payload])
        result = harness.sync(
            ["E-page"],
            [payload],
            action_id=action,
            coverage=harness.coverage(
                "E-page",
                [action],
                scenario_id="english",
                scenario_values={"page_language": "en"},
            ),
        )["events"][0]
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(
            any(
                row["inspection_target"].endswith("page_language") and row["status"] == "FAIL"
                for row in result["inspections"]
            )
        )

    def test_live_discovered_value_is_tested_and_reported_as_plan_gap_not_passed(self) -> None:
        event = default_event("E-page", "page_view")
        event["requirements"].append(
            {
                "field_path": "page_language",
                "match_rule": "one_of",
                "allowed_values": ["en", "fr"],
                "expected_type": "string",
            }
        )
        harness = V5Harness(self.root, events=[event])
        action = self._execute_without_final_coverage(
            harness,
            "E-page",
            {"event": "page_view", "page_language": "de"},
            "german",
            {"page_language": "de"},
            {"page_language": "de"},
        )
        evidence_ref = str(harness.last_begin_result["captures"][0])
        review = harness.coverage(
            "E-page",
            [action],
            dimensions=[
                {
                    "name": "page_language",
                    "kind": "manageable_finite",
                    "material": True,
                    "values": [
                        {
                            "value": "de",
                            "source": "dom",
                            "evidence_ref": evidence_ref,
                        }
                    ],
                }
            ],
            scenarios=[
                {
                    "scenario_id": "german",
                    "label": "Live German locale",
                    "role": "ORDINARY",
                    "values": {"page_language": "de"},
                    "action_ids": [action],
                }
            ],
        )
        harness.add_coverage(review)
        result = harness.feedback("E-page")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(any("untested values" in error for error in result["coverage"]["errors"]))
        self.assertTrue(result["coverage"]["plan_gaps"])
        self.assertTrue(
            any(row["reason_code"] == "plan.live_value_gap" for row in result["inspections"])
        )

    def test_high_cardinality_products_use_representative_behavior_classes(self) -> None:
        harness = V5Harness(self.root)
        ordinary = self._execute_without_final_coverage(
            harness,
            "E-view_item",
            {"event": "view_item", "ecommerce": {"items": [{"item_id": "SKU-1"}]}},
            "ordinary-product",
            {"product_class": "ordinary"},
            {"item_id": "SKU-1"},
        )
        contrast = self._execute_without_final_coverage(
            harness,
            "E-view_item",
            {"event": "view_item", "ecommerce": {"items": [{"item_id": "SKU-2"}]}},
            "variant-product",
            {"product_class": "variant"},
            {"item_id": "SKU-2"},
        )
        review = harness.coverage(
            "E-view_item",
            [ordinary, contrast],
            mode="SAMPLED",
            dimensions=[
                {
                    "name": "product",
                    "kind": "high_cardinality",
                    "material": True,
                    "values": ["SKU-1", "SKU-2", "SKU-3", "SKU-4"],
                }
            ],
            scenarios=[
                {
                    "scenario_id": "ordinary-product",
                    "label": "Ordinary product",
                    "role": "ORDINARY",
                    "values": {"product_class": "ordinary"},
                    "behavior_signature": "standard product detail template",
                    "action_ids": [ordinary],
                },
                {
                    "scenario_id": "variant-product",
                    "label": "Variant product",
                    "role": "CONTRAST",
                    "values": {"product_class": "variant"},
                    "behavior_signature": "variant selector changes item identity",
                    "action_ids": [contrast],
                },
            ],
        )
        harness.add_coverage(review)
        result = harness.feedback("E-view_item")
        self.assertEqual(result["coverage"]["mode"], "SAMPLED")
        self.assertEqual(result["coverage"]["status"], "PASS")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["scenarios"]), 2)

    def test_high_cardinality_is_not_allowed_to_masquerade_as_exhaustive(self) -> None:
        harness = V5Harness(self.root)
        action, _ = harness.execute_pass()
        invalid = harness.coverage(
            "E-view_item",
            [action],
            mode="EXHAUSTIVE",
            dimensions=[
                {
                    "name": "product",
                    "kind": "high_cardinality",
                    "material": True,
                    "values": ["SKU-1", "SKU-2"],
                }
            ],
            scenarios=[
                {
                    "scenario_id": "ordinary",
                    "role": "ORDINARY",
                    "values": {},
                    "action_ids": [action],
                }
            ],
        )
        errors = validate_coverage_annotation(
            load_plan(harness.run), read_stream(harness.run)[0], invalid
        )
        self.assertTrue(any("cannot be EXHAUSTIVE" in error for error in errors))

    def test_dependent_shipping_and_country_combinations_must_be_covered(self) -> None:
        event = default_event("E-shipping", "add_shipping_info")
        harness = V5Harness(self.root, events=[event])
        action, _ = harness.execute_pass(
            event_id="E-shipping",
            payload={"event": "add_shipping_info", "shipping_tier": "standard"},
        )
        invalid = harness.coverage(
            "E-shipping",
            [action],
            dimensions=[
                {
                    "name": "country_x_shipping",
                    "kind": "dependent",
                    "material": True,
                    "values": [],
                    "required_combinations": [
                        {"country": "FR", "shipping_tier": "standard"},
                        {"country": "FR", "shipping_tier": "express"},
                    ],
                }
            ],
            scenarios=[
                {
                    "scenario_id": "standard",
                    "role": "ORDINARY",
                    "values": {"country": "FR", "shipping_tier": "standard"},
                    "action_ids": [action],
                }
            ],
        )
        errors = validate_coverage_annotation(
            load_plan(harness.run), read_stream(harness.run)[0], invalid
        )
        self.assertTrue(any("express" in error for error in errors))

    def test_unknown_material_dimension_yields_honest_blocked_coverage(self) -> None:
        harness = V5Harness(self.root)
        action, _ = harness.execute_pass()
        blocked = harness.coverage(
            "E-view_item",
            [action],
            mode="BLOCKED",
            dimensions=[
                {
                    "name": "member_price_tier",
                    "kind": "unknown",
                    "material": True,
                    "values": [],
                }
            ],
        )
        harness.add_coverage(blocked)
        result = coverage_result(load_plan(harness.run), read_stream(harness.run)[0], "E-view_item")
        self.assertEqual(result["status"], "BLOCKED")

    def test_new_executed_scenario_reopens_previous_coverage(self) -> None:
        harness = V5Harness(self.root)
        first, result = harness.execute_pass()
        self.assertEqual(result["coverage"]["status"], "PASS")
        second = harness.begin(["E-view_item"], scenario_id="new-context")
        payload = {"event": "view_item"}
        harness.commit(second, [payload])
        harness.sync(["E-view_item"], [payload], action_id=second)
        reopened = harness.feedback("E-view_item")
        self.assertEqual(reopened["coverage"]["status"], "BLOCKED")
        self.assertTrue(
            any(
                "absent from scenario coverage" in error for error in reopened["coverage"]["errors"]
            )
        )
        self.assertNotEqual(reopened["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
