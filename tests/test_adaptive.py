from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from helpers import action_fixture, bundle_fixture, event_fixture

from adaptive import AdaptiveError, build_reality_evidence, validate_visual_assessment
from evidence import build_behavior_evidence
from judge import judge_event


def assessment(**changes: object) -> dict:
    value = {
        "event_id": "View-Item",
        "scenario_id": "view_item",
        "target_match": "MATCH",
        "outcome": "EXPECTED",
        "observed_values": {"ecommerce.currency": "EUR"},
        "anomaly_codes": [],
        "summary": "The intended product view is visible.",
        "evidence_refs": ["image-before", "image-after"],
    }
    value.update(changes)
    return value


class AdaptiveTests(unittest.TestCase):
    def test_visual_assessment_is_strict_and_cannot_assign_status(self) -> None:
        event = event_fixture()
        valid = validate_visual_assessment(assessment(), event, {"image-before", "image-after"})
        self.assertEqual(valid["outcome"], "EXPECTED")
        invalid = assessment(status="PASS")
        with self.assertRaisesRegex(AdaptiveError, "unknown=.*status"):
            validate_visual_assessment(invalid, event, {"image-before", "image-after"})

    def test_visual_contradiction_deterministically_fails_reality(self) -> None:
        event = event_fixture()
        visual = validate_visual_assessment(
            assessment(
                target_match="MISMATCH",
                outcome="UNEXPECTED",
                anomaly_codes=["WRONG_TARGET", "UNEXPECTED_VISIBLE_OUTCOME"],
                summary="The click opened an unrelated support panel.",
            ),
            event,
            {"image-before", "image-after"},
        )
        state = {
            "url": "https://example.test/product",
            "aria_snapshot": "- heading: Product",
            "screenshot_path": "image.png",
        }
        reality = build_reality_evidence(state, state, {"executed": True}, visual)
        bundle = bundle_fixture()
        bundle["reality"] = reality
        result = judge_event(event, action_fixture(), bundle)
        self.assertEqual(result["layers"][0]["status"], "FAIL")

    def test_undetermined_visual_evidence_is_blocked(self) -> None:
        event = event_fixture()
        visual = validate_visual_assessment(
            assessment(
                target_match="UNDETERMINED",
                outcome="UNDETERMINED",
                anomaly_codes=["VISUAL_EVIDENCE_INCOMPLETE"],
            ),
            event,
            {"image-before", "image-after"},
        )
        state = {
            "url": "https://example.test",
            "aria_snapshot": "",
            "screenshot_path": "x",
        }
        reality = build_reality_evidence(state, state, {"executed": True}, visual)
        self.assertFalse(reality["complete"])
        self.assertIsNone(reality["outcome"])

    def test_plan_gap_is_visible_as_review_without_blocking_evidence(self) -> None:
        event = event_fixture()
        visual = validate_visual_assessment(assessment(), event, {"image-before", "image-after"})
        state = {
            "url": "https://example.test/product",
            "aria_snapshot": "- heading: Product",
            "screenshot_path": "image.png",
        }
        action = {
            "executed": True,
            "target_url": state["url"],
            "target_source": "LIVE",
            "setup_action_count": 0,
            "plan_findings": [
                {
                    "code": "MISSING_PLAN_FIELD",
                    "field": "entry_url",
                    "message": "The plan supplies no exact URL.",
                    "source_refs": ["Plan!A1"],
                }
            ],
        }
        reality = build_reality_evidence(state, state, action, visual)
        bundle = bundle_fixture()
        bundle["reality"] = reality
        result = judge_event(event, action_fixture(), bundle)
        self.assertEqual(result["layers"][0]["status"], "REVIEW")
        self.assertTrue(result["layers"][0]["attributable"])

    def test_continuous_chronology_preserves_wrapped_business_identity(self) -> None:
        source = {
            "complete": True,
            "attributable": True,
            "calls": [
                {
                    "cursor": 10,
                    "row_name": "gtm.custom_event",
                    "payload": {
                        "event": "gtm.custom_event",
                        "event_name": "click_contact",
                    },
                    "complete": True,
                }
            ],
        }
        behavior = build_behavior_evidence(source)
        self.assertTrue(behavior["messages"][0]["business"])
        self.assertEqual(behavior["messages"][0]["event_name"], "click_contact")


if __name__ == "__main__":
    unittest.main()
