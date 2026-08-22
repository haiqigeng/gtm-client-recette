#!/usr/bin/env python3
"""Adversarial tests for coverage, stream, gated-flow, and page-context audits."""

from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from test_v310_optimizations import TIMESTAMP, upgrade_to_v2  # noqa: E402

from execution_contract import _auxiliary_evidence_errors, validate_session  # noqa: E402
from gated_flow_contract import gated_flow_errors  # noqa: E402
from page_context_contract import (  # noqa: E402
    acquisition_errors,
    browser_runtime_errors,
    handoff_errors,
)
from scenario_coverage import EXPANSION_TRIGGERS, coverage_errors  # noqa: E402
from stream_contract import stream_errors  # noqa: E402


def _clone_case(source: dict, case_id: str, member_id: str, role: str) -> dict:
    case = deepcopy(source)
    case.update(
        {
            "case_id": case_id,
            "population_member_id": member_id,
            "sample_role": role,
            "final_action_id": None,
        }
    )
    return case


def _trigger_reviews(detected: set[str], outcome: str = "EXHAUSTED") -> dict:
    return {
        trigger: {
            "detected": trigger in detected,
            "outcome": outcome if trigger in detected else "NOT_TRIGGERED",
            "reason": "Ledger-derived trigger was reviewed."
            if trigger in detected
            else "No ledger signal for this trigger.",
            "additional_case_ids": [],
        }
        for trigger in EXPANSION_TRIGGERS
    }


def _runtime_binding(snapshot: dict) -> dict:
    return {
        "browser_instance_id": snapshot["browser_instance_id"],
        "browser_context_id": snapshot["browser_context_id"],
        "tab_id": snapshot["tab_id"],
        "preview_session_id": snapshot["preview_session_id"],
    }


def _reconnect_contract(previous: dict, segment: dict) -> dict:
    binding = {
        "browser_instance_id": "BROWSER-EXISTING-001",
        "browser_context_id": "desktop-default",
        "tab_id": "TAB-SITE-001",
        "preview_session_id": "PREVIEW-001",
    }
    return {
        "status": "RECONCILED",
        "reason": "Tag Assistant reconnected while the dataLayer recorder remained continuous.",
        "evidence_ids": ["EVD-PAGE-AFTER"],
        "previous_connection_epoch": previous["connection_epoch"],
        "new_connection_epoch": segment["connection_epoch"],
        "previous_segment_id": previous["segment_id"],
        "previous_preview_event_index": previous["end_preview_event_index"],
        "new_preview_event_index": segment["start_preview_event_index"],
        "datalayer_call_index": segment["start_datalayer_call_index"],
        "before_binding": binding,
        "after_binding": binding,
        "action_id": None,
        "case_id": None,
    }


def _acquisition_context() -> dict:
    return {
        "kind": "REFERRER",
        "method": "BROWSER_SIMULATED",
        "fresh_state": True,
        "referrer_url": "https://www.google.com/search?q=example",
        "observed_referrer_url": "https://www.google.com/search?q=example",
        "landing_url": "https://shop.example.test/product?utm_source=google",
        "storage_cookie_state": {
            "cookies_present": False,
            "local_storage_present": False,
            "session_storage_present": False,
            "raw_values_retained": False,
            "reason": "A fresh controlled acquisition state was captured without raw values.",
        },
        "acquisition_parameters": {"utm_source": "google"},
        "evidence_ids": ["EVD-ACQ-001"],
        "evidence_bindings": [
            {
                "evidence_id": "EVD-ACQ-001",
                "kind": "navigation",
                "capture_mode": "direct",
                "path_or_url": "evidence/acquisition-001.json",
                "captured_fields": sorted(
                    {
                        "referrer_url",
                        "landing_url",
                        "storage_cookie_state",
                        "acquisition_parameters",
                    }
                ),
            }
        ],
        "limitations": ["The Google referrer was simulated in the approved browser."],
    }


class CoverageAuditTests(unittest.TestCase):
    def test_final_coverage_reviews_every_trigger_even_when_no_signal_was_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            expansion = session["coverage_decisions"][0]["scenario_classes"][0]["expansion_review"]
            expansion.pop("trigger_reviews")
            errors = coverage_errors(session, results=data, final=True)
            self.assertTrue(any("every mandatory adaptive trigger" in error for error in errors))

    def test_exhaustive_values_must_be_bound_to_distinct_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            decision = session["coverage_decisions"][0]
            dimension = decision["dimensions"][0]
            dimension["values"] = ["default", "alternate"]
            scenario = decision["scenario_classes"][0]
            scenario.update(
                {
                    "selection_mode": "EXHAUSTIVE",
                    "population_estimate": 2,
                    "required_sample_roles": ["EXHAUSTIVE"],
                    "dimension_values": {"DIM-CONTRACT": ["default", "alternate"]},
                    "case_ids": ["CASE-001", "CASE-002"],
                }
            )
            first = session["cases"][0]
            first.update(
                {
                    "sample_role": "EXHAUSTIVE",
                    "dimension_values": {"DIM-CONTRACT": "default"},
                }
            )
            second = _clone_case(first, "CASE-002", "product-alternate", "EXHAUSTIVE")
            second["dimension_values"] = {"DIM-CONTRACT": "alternate"}
            session["cases"].append(second)
            self.assertEqual([], coverage_errors(session, results=data, final=True))

            second["dimension_values"] = {"DIM-CONTRACT": "default"}
            errors = coverage_errors(session, results=data, final=True)
            self.assertTrue(any("do not represent DIM-CONTRACT" in error for error in errors))

    def test_multi_case_scenario_rejects_unbound_material_values(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            scenario = session["coverage_decisions"][0]["scenario_classes"][0]
            scenario.update(
                {
                    "selection_mode": "EXHAUSTIVE",
                    "population_estimate": 2,
                    "required_sample_roles": ["EXHAUSTIVE"],
                    "case_ids": ["CASE-001", "CASE-002"],
                }
            )
            session["cases"][0]["sample_role"] = "EXHAUSTIVE"
            session["cases"][0].pop("dimension_values")
            session["cases"].append(
                _clone_case(session["cases"][0], "CASE-002", "product-2", "EXHAUSTIVE")
            )
            errors = coverage_errors(session, results=data, final=True)
            self.assertTrue(any("requires explicit dimension_values" in error for error in errors))

    def test_boundary_and_exception_roles_follow_explicit_applicability(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            scenario = session["coverage_decisions"][0]["scenario_classes"][0]
            scenario.update(
                {
                    "selection_mode": "SAMPLED",
                    "population_estimate": 500,
                    "required_sample_roles": ["ORDINARY", "CONTRAST"],
                    "sample_role_applicability": {
                        "BOUNDARY": {
                            "applicable": True,
                            "reason": "A maximum-quantity boundary exists.",
                        },
                        "EXCEPTION": {
                            "applicable": False,
                            "reason": "No distinct exception population was discovered.",
                        },
                    },
                    "case_ids": ["CASE-001", "CASE-002"],
                }
            )
            first = session["cases"][0]
            first.update(
                {
                    "sample_role": "ORDINARY",
                    "dimension_values": {"DIM-CONTRACT": "default"},
                }
            )
            second = _clone_case(first, "CASE-002", "contrast-product", "CONTRAST")
            session["cases"].append(second)
            errors = coverage_errors(session, results=data, final=True)
            self.assertTrue(any("missing BOUNDARY" in error for error in errors))

    def test_runtime_signals_force_explicit_trigger_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            case = session["cases"][0]
            case["observed_dimension_values"] = {"DIM-CONTRACT": "unseen"}
            case["observed_behavior_signature"] = {"action_path": "unexpected path"}
            session["actions"][0]["conditional_branch_observed"] = True
            session["business_pushes"].append(
                {
                    "push_id": "PUSH-UNEXPECTED",
                    "event_group_id": "EVG-001",
                    "classification": "unplanned_relevant",
                }
            )
            errors = coverage_errors(session, results=data, final=True)
            for trigger in EXPANSION_TRIGGERS:
                self.assertTrue(any(trigger in error for error in errors), trigger)

            detected = set(EXPANSION_TRIGGERS)
            scenario = session["coverage_decisions"][0]["scenario_classes"][0]
            scenario["expansion_review"] = {
                "status": "EXHAUSTED",
                "reason": "All four ledger-derived triggers were investigated.",
                "additional_case_ids": [],
                "trigger_reviews": _trigger_reviews(detected),
            }
            self.assertEqual([], coverage_errors(session, results=data, final=True))

    def test_expansion_case_ids_must_be_registered_and_in_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            session["actions"][0]["conditional_branch_observed"] = True
            reviews = _trigger_reviews({"CONDITIONAL_RUNTIME_BRANCH"})
            reviews["CONDITIONAL_RUNTIME_BRANCH"].update(
                {"outcome": "EXPANDED", "additional_case_ids": ["CASE-MISSING"]}
            )
            scenario = session["coverage_decisions"][0]["scenario_classes"][0]
            scenario["expansion_review"] = {
                "status": "EXPANDED",
                "reason": "A new case was requested.",
                "additional_case_ids": ["CASE-MISSING"],
                "trigger_reviews": reviews,
            }
            errors = coverage_errors(session, results=data, final=True)
            self.assertTrue(any("not registered" in error for error in errors))
            self.assertTrue(any("outside the scenario" in error for error in errors))


class StreamAuditTests(unittest.TestCase):
    def test_preview_reset_is_allowed_with_reconciled_reconnect(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            _, session = upgrade_to_v2(Path(tempdir))
            previous = session["stream_segments"][-2]
            final = session["stream_segments"][-1]
            final.update(
                {
                    "connection_epoch": 2,
                    "start_preview_event_index": 0,
                    "end_preview_event_index": 0,
                    "start_datalayer_call_index": 1,
                    "end_datalayer_call_index": 1,
                }
            )
            final["reconnect"] = _reconnect_contract(previous, final)
            session["stream_contract"]["reviewed_through_preview_event_index"] = 0
            self.assertEqual([], stream_errors(session, final=True))

    def test_cross_epoch_datalayer_gap_cannot_be_hidden_by_reconnect(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            _, session = upgrade_to_v2(Path(tempdir))
            previous = session["stream_segments"][-2]
            final = session["stream_segments"][-1]
            final.update(
                {
                    "connection_epoch": 2,
                    "start_preview_event_index": 0,
                    "end_preview_event_index": 0,
                    "start_datalayer_call_index": 2,
                    "end_datalayer_call_index": 2,
                }
            )
            final["reconnect"] = _reconnect_contract(previous, final)
            session["stream_contract"].update(
                {
                    "reviewed_through_preview_event_index": 0,
                    "reviewed_through_datalayer_call_index": 2,
                }
            )
            errors = stream_errors(session, final=True)
            self.assertTrue(any("cross-segment gap or overlap" in error for error in errors))


class FlowAndPageAuditTests(unittest.TestCase):
    def test_v2_sidecar_evidence_ids_resolve_and_bind_to_the_action(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            evidence = {row["evidence_id"]: row for row in data["evidence"]}
            self.assertEqual([], _auxiliary_evidence_errors(session, evidence))

            session["stream_segments"][0]["evidence_ids"] = ["EVD-UNKNOWN"]
            errors = _auxiliary_evidence_errors(session, evidence)
            self.assertTrue(any("unknown evidence ID 'EVD-UNKNOWN'" in error for error in errors))
            session["stream_segments"][0]["evidence_ids"] = ["EVD-PAGE-READY"]

            session["protected_handoffs"] = [
                {
                    "handoff_id": "HANDOFF-BINDING",
                    "case_id": "CASE-001",
                    "action_id": "ACT-OTHER",
                    "evidence_ids": ["EVD-PAGE-READY"],
                }
            ]
            errors = _auxiliary_evidence_errors(session, evidence)
            self.assertTrue(any("bound to another action" in error for error in errors))

    def test_completed_form_cannot_skip_entry_consent_validation_or_submission(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            _, session = upgrade_to_v2(Path(tempdir))
            session["cases"][0]["gated_flow_kind"] = "FORM"
            session["gated_flows"] = [
                {
                    "flow_id": "FLOW-001",
                    "case_id": "CASE-001",
                    "action_id": "ACT-001",
                    "kind": "FORM",
                    "status": "COMPLETED",
                    "safe_environment_confirmed": True,
                    "synthetic_data_used": False,
                    "consent_required": True,
                    "consent_outcome": "NOT_APPLICABLE",
                    "captcha_outcome": "NOT_PRESENT",
                    "states": ["DISCOVERED", "SUCCEEDED"],
                    "recorded_at": TIMESTAMP,
                    "reason": "Invalid direct jump used for the adversarial test.",
                    "evidence_ids": ["EVD-PAGE-READY"],
                }
            ]
            errors = gated_flow_errors(session, final=True)
            for milestone in (
                "synthetic_data_used=true",
                "CONSENT_ESTABLISHED",
                "VALIDATION_COMPLETED",
                "SUBMISSION_ATTEMPTED",
            ):
                self.assertTrue(any(milestone in error for error in errors), milestone)

    def test_captcha_completion_requires_resumed_same_flow_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            _, session = upgrade_to_v2(Path(tempdir))
            before = session["runtime_checks"][0]
            binding = _runtime_binding(before)
            session["cases"][0]["gated_flow_kind"] = "FORM"
            session["protected_handoffs"] = [
                {
                    "handoff_id": "HANDOFF-001",
                    "flow_id": "FLOW-OTHER",
                    "gate_type": "GOOGLE_SIGN_IN",
                    "status": "RESUMED",
                    "continuity_mode": "SAME_SESSION",
                    "analyst_help_requested": True,
                    "case_id": "CASE-001",
                    "action_id": "ACT-001",
                    "requested_at": TIMESTAMP,
                    "resumed_at": TIMESTAMP,
                    "reason": "Wrong gate used to challenge the validator.",
                    "evidence_ids": ["EVD-PAGE-READY"],
                    "before_binding": binding,
                    "after_binding": binding,
                }
            ]
            session["gated_flows"] = [
                {
                    "flow_id": "FLOW-001",
                    "case_id": "CASE-001",
                    "action_id": "ACT-001",
                    "kind": "FORM",
                    "status": "COMPLETED",
                    "safe_environment_confirmed": True,
                    "synthetic_data_used": True,
                    "consent_required": True,
                    "consent_outcome": "ACCEPTED",
                    "captcha_outcome": "PRESENT_HANDOFF",
                    "handoff_id": "HANDOFF-001",
                    "states": [
                        "DISCOVERED",
                        "SYNTHETIC_DATA_ENTERED",
                        "CONSENT_ESTABLISHED",
                        "VALIDATION_COMPLETED",
                        "SUBMISSION_ATTEMPTED",
                        "HANDOFF_REQUESTED",
                        "HANDOFF_RESUMED",
                        "SUCCEEDED",
                    ],
                    "recorded_at": TIMESTAMP,
                    "reason": "CAPTCHA was completed through an analyst handoff.",
                    "evidence_ids": ["EVD-PAGE-READY"],
                }
            ]
            errors = gated_flow_errors(session, final=True)
            self.assertTrue(any("requires a CAPTCHA handoff" in error for error in errors))
            self.assertTrue(any("another flow" in error for error in errors))

            handoff = session["protected_handoffs"][0]
            handoff.update({"flow_id": "FLOW-001", "gate_type": "CAPTCHA"})
            self.assertEqual([], gated_flow_errors(session, final=True))

    def test_acquisition_requires_fresh_directly_evidenced_browser_state(self) -> None:
        context = _acquisition_context()
        self.assertEqual([], acquisition_errors(context, require_direct_evidence=True))
        context["fresh_state"] = False
        self.assertTrue(any("fresh_state=true" in error for error in acquisition_errors(context)))
        context["fresh_state"] = True
        context["evidence_bindings"] = []
        errors = acquisition_errors(context, require_direct_evidence=True)
        self.assertTrue(any("do not resolve exactly" in error for error in errors))

    def test_runtime_validation_resolves_acquisition_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            session["cases"][0]["acquisition_context"] = _acquisition_context()
            data["evidence"].append(
                {
                    "evidence_id": "EVD-ACQ-001",
                    "kind": "navigation",
                    "source": "Playwright",
                    "capture_mode": "direct",
                    "case_id": "CASE-001",
                    "path_or_url": "evidence/acquisition-001.json",
                    "captured_at": TIMESTAMP,
                    "description": "Direct acquisition context capture.",
                    "captured_fields": sorted(
                        {
                            "referrer_url",
                            "landing_url",
                            "storage_cookie_state",
                            "acquisition_parameters",
                        }
                    ),
                }
            )
            evidence_catalog = {row["evidence_id"]: row for row in data["evidence"]}
            snapshot = session["runtime_checks"][0]
            self.assertEqual(
                [],
                browser_runtime_errors(
                    snapshot,
                    ledger=session,
                    expected_container_ids={"GTM-TEST"},
                    evidence_catalog=evidence_catalog,
                ),
            )
            session_errors = validate_session(session, results=data, final=False)
            self.assertFalse(
                any(
                    "acquisition evidence EVD-ACQ-001 is absent" in error
                    for error in session_errors
                )
            )
            evidence_catalog["EVD-ACQ-001"]["case_id"] = "CASE-OTHER"
            errors = browser_runtime_errors(
                snapshot,
                ledger=session,
                expected_container_ids={"GTM-TEST"},
                evidence_catalog=evidence_catalog,
            )
            self.assertTrue(any("bound to another case" in error for error in errors))

    def test_runtime_tab_or_preview_change_needs_bound_reconnect(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            _, session = upgrade_to_v2(Path(tempdir))
            before, after = session["runtime_checks"]
            after.update({"tab_id": "TAB-NEW", "preview_session_id": "PREVIEW-NEW"})
            errors = browser_runtime_errors(
                after,
                ledger=session,
                expected_container_ids={"GTM-TEST"},
            )
            self.assertTrue(any("without a bound" in error for error in errors))

            session["protected_handoffs"] = [
                {
                    "handoff_id": "HANDOFF-RECONNECT-001",
                    "gate_type": "CAPTCHA",
                    "status": "RESUMED",
                    "continuity_mode": "RECONNECT",
                    "analyst_help_requested": True,
                    "case_id": "CASE-001",
                    "action_id": "ACT-001",
                    "requested_at": TIMESTAMP,
                    "resumed_at": TIMESTAMP,
                    "reason": "The analyst resumed the protected action after reconnect.",
                    "reconnect_reason": "Tag Assistant assigned a new Preview session.",
                    "evidence_ids": ["EVD-PAGE-READY"],
                    "before_binding": _runtime_binding(before),
                    "after_binding": _runtime_binding(after),
                }
            ]
            handoff_contract_errors = handoff_errors(session, final=True)
            self.assertTrue(
                any("invalid continuity_mode" in error for error in handoff_contract_errors)
            )
            self.assertTrue(any("different tab_id" in error for error in handoff_contract_errors))
            runtime_errors = browser_runtime_errors(
                after,
                ledger=session,
                expected_container_ids={"GTM-TEST"},
            )
            self.assertTrue(
                any("protected handoff continuity changed" in error for error in runtime_errors)
            )


if __name__ == "__main__":
    unittest.main()
