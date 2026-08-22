#!/usr/bin/env python3
"""Adversarial regressions for semantic truth and event-status roll-up."""

from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
for path in (SCRIPTS, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_pipeline import execution_fixture, fixture  # noqa: E402
from test_v310_optimizations import upgrade_to_v2  # noqa: E402

from event_feedback import event_feedback, final_conclusion  # noqa: E402
from scenario_coverage import coverage_errors  # noqa: E402
from semantic_contract import semantic_contract_errors, semantic_summary  # noqa: E402
from stream_contract import stream_errors  # noqa: E402


def evidence(data: dict, evidence_id: str) -> dict:
    return next(row for row in data["evidence"] if row.get("evidence_id") == evidence_id)


class SemanticAndFeedbackAuditTests(unittest.TestCase):
    def test_page_validity_requires_both_page_health_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            page_check = next(
                row for row in session["semantic_checks"] if row["kind"] == "PAGE_ACTION_VALIDITY"
            )
            page_check["evidence_ids"] = ["EVD-PAGE-READY"]
            errors = semantic_contract_errors(session, results=data, final=True)
            self.assertTrue(
                any("requires before and after page-health evidence" in error for error in errors)
            )

    def test_existing_valid_v2_fixture_remains_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            self.assertEqual([], semantic_contract_errors(session, results=data, final=True))
            self.assertEqual("PASS", event_feedback(data, session)[0]["status"])

    def test_present_positive_anchor_cannot_hide_as_not_applicable(self) -> None:
        for kind in ("BUSINESS_STATE", "POSITIVE_ANCHOR"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tempdir:
                data, session = upgrade_to_v2(Path(tempdir))
                if kind == "BUSINESS_STATE":
                    check = session["semantic_checks"][1]
                else:
                    check = deepcopy(session["semantic_checks"][1])
                    check.update({"check_id": "SEM-POSITIVE-EMPTY", "kind": kind})
                    session["semantic_checks"].append(check)
                check.update(
                    {
                        "status": "NOT_APPLICABLE",
                        "anchor_state": "PRESENT",
                        "anchor_value": "",
                        "observed_value": "",
                        "anchor_field_state": "empty",
                        "observed_field_state": "empty",
                    }
                )
                errors = semantic_contract_errors(session, results=data, final=True)
                self.assertTrue(any("cannot be NOT_APPLICABLE" in row for row in errors))
                self.assertTrue(any("must be non-empty" in row for row in errors))

    def test_semantic_evidence_must_belong_to_same_action_and_case(self) -> None:
        mutations = (
            ("action_id", "ACT-OTHER", "same action"),
            ("case_id", "CASE-OTHER", "same case"),
        )
        for field, value, expected in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tempdir:
                data, session = upgrade_to_v2(Path(tempdir))
                evidence(data, "EVD-JOURNEY-AFTER")[field] = value
                errors = semantic_contract_errors(session, results=data, final=True)
                self.assertTrue(any(expected in row for row in errors), errors)

    def test_page_evidence_must_match_its_before_after_runtime_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            evidence(data, "EVD-PAGE-READY")["runtime_phase"] = "after_action"
            errors = semantic_contract_errors(session, results=data, final=True)
            self.assertTrue(any("runtime_phase differs" in row for row in errors), errors)
            self.assertTrue(any("wrong before/after action phase" in row for row in errors), errors)

    def test_page_evidence_cannot_omit_its_runtime_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            page_evidence = evidence(data, "EVD-PAGE-READY")
            page_evidence.pop("runtime_check_id")
            page_evidence.pop("runtime_phase")
            errors = semantic_contract_errors(session, results=data, final=True)
            self.assertTrue(
                any("requires an explicit before/after" in row for row in errors), errors
            )

    def test_business_state_requires_after_journey_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            session["semantic_checks"][1]["evidence_ids"] = [
                "EVD-JOURNEY-BEFORE",
                "EVD-RAW-011",
            ]
            errors = semantic_contract_errors(session, results=data, final=True)
            self.assertTrue(any("requires AFTER journey evidence" in row for row in errors), errors)

    def test_after_action_soft_404_forces_semantic_and_overall_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            after = next(
                row for row in session["runtime_checks"] if row.get("phase") == "after_action"
            )
            after["page_health"].update(
                {
                    "status": "FAIL",
                    "reachable": True,
                    "http_status": 200,
                    "is_error_page": False,
                    "is_soft_404": True,
                    "expected_content_present": False,
                    "action_target_present": False,
                    "reason": "The post-action route is a directly observed soft 404.",
                }
            )
            self.assertTrue(
                all(row["status"] == "PASS" for row in session["semantic_checks"]),
                "The probe must leave the analyst-authored semantic statuses falsely passing.",
            )

            errors = semantic_contract_errors(session, results=data, final=True)
            self.assertTrue(any("PAGE_ACTION_VALIDITY must be FAIL" in row for row in errors))
            self.assertTrue(any("BUSINESS_STATE cannot PASS" in row for row in errors))
            self.assertEqual("FAIL", semantic_summary(session, "EVG-001")["status"])

            feedback = event_feedback(data, session)[0]
            self.assertEqual("FAIL", feedback["status"])
            self.assertEqual("FAIL", feedback["semantic_status"])
            self.assertEqual("PASS", feedback["technical_status"])
            self.assertEqual("FAIL", final_conclusion(data, session)["status"])

    def test_continuous_stream_status_is_mandatory_in_event_and_final_rollup(self) -> None:
        expectations = {
            "OPEN": "BLOCKED",
            "BLOCKED": "BLOCKED",
            "REVIEW": "REVIEW",
            "FAIL": "FAIL",
        }
        for stream_state, expected in expectations.items():
            with self.subTest(stream_state=stream_state), tempfile.TemporaryDirectory() as tempdir:
                data, session = upgrade_to_v2(Path(tempdir))
                session["stream_contract"]["status"] = stream_state
                feedback = event_feedback(data, session)[0]
                self.assertEqual(expected, feedback["status"])
                self.assertEqual(expected, feedback["component_statuses"]["continuous_stream"])
                self.assertEqual(expected, final_conclusion(data, session)["status"])

    def test_scenario_coverage_status_is_mandatory_in_event_and_final_rollup(self) -> None:
        expectations = {
            "DRAFT": "BLOCKED",
            "BLOCKED": "BLOCKED",
            "REVIEW": "REVIEW",
            "FAIL": "FAIL",
        }
        for coverage_state, expected in expectations.items():
            with (
                self.subTest(coverage_state=coverage_state),
                tempfile.TemporaryDirectory() as tempdir,
            ):
                data, session = upgrade_to_v2(Path(tempdir))
                session["coverage_decisions"][0]["status"] = coverage_state
                feedback = event_feedback(data, session)[0]
                self.assertEqual(expected, feedback["status"])
                self.assertEqual(expected, feedback["component_statuses"]["scenario_coverage"])
                self.assertEqual(expected, final_conclusion(data, session)["status"])

    def test_closed_but_invalid_stream_cannot_roll_up_as_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            session["stream_segments"][1]["start_datalayer_call_index"] = 1
            self.assertTrue(stream_errors(session, final=True))
            feedback = event_feedback(data, session)[0]
            self.assertEqual("FAIL", feedback["status"])
            self.assertEqual("FAIL", feedback["component_statuses"]["continuous_stream"])
            self.assertTrue(feedback["stream"]["validation_errors"])
            self.assertEqual("FAIL", final_conclusion(data, session)["status"])

    def test_frozen_but_invalid_coverage_cannot_roll_up_as_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            del session["coverage_decisions"][0]["scenario_classes"][0]["expansion_review"][
                "trigger_reviews"
            ]
            self.assertTrue(coverage_errors(session, results=data, final=True))
            feedback = event_feedback(data, session)[0]
            self.assertEqual("FAIL", feedback["status"])
            self.assertEqual("FAIL", feedback["component_statuses"]["scenario_coverage"])
            self.assertTrue(feedback["coverage"]["validation_errors"])
            self.assertEqual("FAIL", final_conclusion(data, session)["status"])

    def test_v1_feedback_remains_backward_readable(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        feedback = event_feedback(data, session)[0]
        self.assertEqual("PASS", feedback["status"])
        self.assertEqual("NOT_TESTED", feedback["component_statuses"]["continuous_stream"])
        self.assertEqual("NOT_TESTED", feedback["component_statuses"]["scenario_coverage"])
        self.assertEqual("PASS", final_conclusion(data, session)["status"])


if __name__ == "__main__":
    unittest.main()
