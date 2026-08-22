#!/usr/bin/env python3
"""Adversarial regressions for operator compatibility and atomic v2 imports."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
TESTS = ROOT / "tests"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from test_pipeline import execution_fixture, fixture  # noqa: E402
from test_v310_optimizations import upgrade_to_v2  # noqa: E402

from execution_contract import validate_session  # noqa: E402
from preview_session_ledger import (  # noqa: E402
    import_coverage,
    import_gated_flows,
    import_protected_handoffs,
    import_semantic,
    import_stream,
    import_tag_results,
    init_command,
    register_case,
)
from preview_session_ledger import (  # noqa: E402
    parser as session_parser,
)
from recette_operator import (  # noqa: E402
    _pause_run,
    _require_guided_contract,
    _require_v2_resume_check_continuity,
    _resume_run,
    _status,
)
from recette_schema import validate  # noqa: E402


class OperatorCompatibilityAuditTests(unittest.TestCase):
    def test_direct_session_validation_rejects_another_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            session["run_id"] = "RUN-PREVIOUS"
            errors = validate_session(session, results=data, final=True)
            self.assertTrue(any("run_id differs" in error for error in errors))

    def test_v2_case_registration_requires_explicit_dimension_bindings(self) -> None:
        data = fixture()
        ledger = {
            "operator_contract_version": 2,
            "approved_origins": ["https://shop.example.test"],
            "cases": [],
            "authorizations": [],
        }
        with tempfile.TemporaryDirectory() as tempdir:
            results_path = Path(tempdir) / "results.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            args = Namespace(
                results=results_path,
                case_id="CASE-V2",
                event_group_id="EVG-001",
                url="https://shop.example.test/product",
                element="Add to cart",
                placement="product detail",
                action="click",
                variant=["quantity=1"],
                dimension_value=[],
                discovered_from="tracking_plan",
                scope_status="IN_SCOPE",
                reason=None,
                authorization_id=[],
                coverage_decision_id="COV-EVG-001",
                scenario_class_id="SCN-DEFAULT",
                sample_role="SINGLETON",
                selection_rationale="One material behavior class.",
                population_member_id="product-default",
                acquisition_context={
                    "kind": "NOT_APPLICABLE",
                    "method": "NOT_APPLICABLE",
                    "limitations": [],
                },
                gated_flow_kind="NONE",
                include_layer=[],
                exclude_layer=[],
                activate_condition=[],
            )
            with self.assertRaisesRegex(SystemExit, "--dimension-value"):
                register_case(ledger, args)
            self.assertEqual([], ledger["cases"])

            args.dimension_value = ['DIM-CONTRACT="default"']
            register_case(ledger, args)
            self.assertEqual({"DIM-CONTRACT": "default"}, ledger["cases"][0]["dimension_values"])

    def test_session_init_defaults_to_v2_and_binds_normalized_run(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            ledger_path = Path(tempdir) / "session.json"
            args = session_parser().parse_args(
                [
                    "init",
                    str(ledger_path),
                    "--profile-path",
                    str(Path(tempdir) / "profile"),
                    "--approved-origin",
                    "https://shop.example.test",
                    "--run-id",
                    "RUN-CURRENT-001",
                    "--browser-instance-id",
                    "BROWSER-EXISTING-001",
                    "--browser-context-id",
                    "desktop-default",
                ]
            )
            self.assertEqual(2, args.operator_contract_version)
            init_command(args)
            session = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(2, session["operator_contract_version"])
            self.assertEqual("RUN-CURRENT-001", session["run_id"])
            self.assertEqual(
                {"version": 2, "status": "PENDING"},
                session["evidence_integrity"],
            )

    def test_explicit_v1_is_valid_for_old_automation_and_markerless_is_readable(self) -> None:
        data = fixture()
        data["run"]["operator_contract_version_required"] = 1
        self.assertEqual([], validate(data, strict=True))
        session = execution_fixture(data)
        session["operator_contract_version"] = 1
        _require_guided_contract(data, session)

        markerless = deepcopy(data)
        markerless["run"].pop("operator_contract_version_required")
        self.assertEqual([], validate(markerless, strict=True))

    def test_status_rejects_an_incompatible_pair_instead_of_reporting_active(self) -> None:
        data = fixture()
        data["run"]["operator_contract_version_required"] = 2
        session = execution_fixture(data)
        with tempfile.TemporaryDirectory() as tempdir:
            results_path = Path(tempdir) / "results.json"
            session_path = Path(tempdir) / "session.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            session_path.write_text(json.dumps(session), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "operator_contract_version=2"):
                _status(Namespace(results=results_path, session=session_path))

            session["operator_contract_version"] = 2
            session["run_id"] = "RUN-PREVIOUS"
            session_path.write_text(json.dumps(session), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "run_id differs"):
                _status(Namespace(results=results_path, session=session_path))

    def test_operator_v2_pause_resume_and_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data, session = upgrade_to_v2(root)
            session["run_id"] = data["run"]["run_id"]
            session["operator_state"] = {
                "status": "ACTIVE",
                "current_event_group_id": None,
            }
            for push in session["business_pushes"]:
                push.setdefault("connection_epoch", 1)
            results_path = root / "results.json"
            session_path = root / "session.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            session_path.write_text(json.dumps(session), encoding="utf-8")

            paused = _pause_run(
                Namespace(
                    session=session_path,
                    results=results_path,
                    label="handoff between event cases",
                )
            )
            self.assertEqual(2, paused["operator_contract_version"])
            resumed = _resume_run(
                Namespace(
                    results=results_path,
                    session=session_path,
                    runtime_snapshot=None,
                )
            )
            self.assertTrue(resumed["resumed"])

            _pause_run(
                Namespace(
                    session=session_path,
                    results=results_path,
                    label="tamper probe",
                )
            )
            tampered = json.loads(session_path.read_text(encoding="utf-8"))
            tampered["stream_contract"]["reviewed_through_preview_event_index"] += 1
            session_path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pause continuity changed"):
                _resume_run(
                    Namespace(
                        results=results_path,
                        session=session_path,
                        runtime_snapshot=None,
                    )
                )

    def test_operator_v2_open_action_resume_rejects_a_different_tab(self) -> None:
        readiness = {
            "check_id": "CHECK-BEFORE",
            "browser_instance_id": "BROWSER-1",
            "browser_context_id": "CONTEXT-1",
            "tab_id": "TAB-1",
            "preview_session_id": "PREVIEW-1",
            "loaded_client_container_ids": ["GTM-TEST"],
            "preview_event_cursor": 10,
            "network_request_cursor": 20,
            "datalayer_call_cursor": 30,
        }
        session = {"runtime_checks": [readiness]}
        action = {"readiness_check_id": "CHECK-BEFORE"}
        resumed = {
            **readiness,
            "check_id": "CHECK-RESUME",
            "tab_id": "TAB-OTHER",
        }
        checkpoint = {
            "stream_contract": {
                "reviewed_through_preview_event_index": 10,
                "reviewed_through_datalayer_call_index": 30,
            }
        }
        with self.assertRaisesRegex(ValueError, "tab_id differs"):
            _require_v2_resume_check_continuity(
                session,
                action,
                resumed,
                checkpoint,
            )

    def test_all_v2_sidecar_imports_reject_another_run_without_mutation(self) -> None:
        ledger = {
            "operator_contract_version": 2,
            "run_id": "RUN-CURRENT",
            "coverage_decisions": [],
            "event_closures": [],
            "stream_contract": {},
            "stream_segments": [],
            "journey_states": [],
            "semantic_checks": [],
            "protected_handoffs": [],
            "gated_flows": [],
        }
        imports = (
            (
                import_coverage,
                "coverage",
                {"run_id": "RUN-CURRENT", "coverage_decisions": []},
            ),
            (
                import_stream,
                "stream",
                {
                    "run_id": "RUN-CURRENT",
                    "stream_contract": {},
                    "stream_segments": [],
                },
            ),
            (
                import_semantic,
                "semantic",
                {
                    "run_id": "RUN-CURRENT",
                    "journey_states": [],
                    "semantic_checks": [],
                },
            ),
            (
                import_protected_handoffs,
                "handoffs",
                {"run_id": "RUN-CURRENT", "protected_handoffs": []},
            ),
            (
                import_gated_flows,
                "flows",
                {"run_id": "RUN-CURRENT", "gated_flows": []},
            ),
        )
        with tempfile.TemporaryDirectory() as tempdir:
            for function, argument_name, valid_payload in imports:
                with self.subTest(importer=function.__name__):
                    artifact_path = Path(tempdir) / f"{function.__name__}.json"
                    wrong_payload = {**valid_payload, "run_id": "RUN-PREVIOUS"}
                    artifact_path.write_text(json.dumps(wrong_payload), encoding="utf-8")
                    before = deepcopy(ledger)
                    with self.assertRaisesRegex(SystemExit, "previous-run artifacts"):
                        function(ledger, Namespace(**{argument_name: artifact_path}))
                    self.assertEqual(before, ledger)

                    artifact_path.write_text(json.dumps(valid_payload), encoding="utf-8")
                    function(ledger, Namespace(**{argument_name: artifact_path}))

    def test_tag_batch_is_exact_atomic_and_replaceable_while_open(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        action = session["actions"][0]
        valid_rows = deepcopy(action["tag_layer_results"])
        action["state"] = "OPEN"
        action["tag_layer_results"] = []
        session["cases"][0]["execution_status"] = "PENDING"
        session["cases"][0]["final_action_id"] = None
        session["event_closures"] = []
        session["operator_state"] = {
            "status": "ACTIVE",
            "current_event_group_id": "EVG-001",
        }

        with tempfile.TemporaryDirectory() as tempdir:
            results_path = Path(tempdir) / "results.json"
            artifact_path = Path(tempdir) / "tag-results.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            args = Namespace(
                tag_results=artifact_path,
                action_id="ACT-001",
                results=results_path,
            )

            artifact_path.write_text(json.dumps(valid_rows[:-1]), encoding="utf-8")
            before = deepcopy(session)
            with self.assertRaisesRegex(SystemExit, "missing tag/layer rows"):
                import_tag_results(session, args)
            self.assertEqual(before, session)

            artifact_path.write_text(json.dumps(valid_rows), encoding="utf-8")
            import_tag_results(session, args)
            self.assertEqual(len(valid_rows), len(session["actions"][0]["tag_layer_results"]))

            replacement = deepcopy(valid_rows)
            replacement[0]["reason"] = "Replacement batch retained direct evidence."
            artifact_path.write_text(json.dumps(replacement), encoding="utf-8")
            import_tag_results(session, args)
            self.assertEqual(
                "Replacement batch retained direct evidence.",
                session["actions"][0]["tag_layer_results"][0]["reason"],
            )

            invalid = deepcopy(replacement)
            invalid[0]["status"] = "BROKEN"
            artifact_path.write_text(json.dumps(invalid), encoding="utf-8")
            before_invalid = deepcopy(session)
            with self.assertRaisesRegex(SystemExit, "staged session validation"):
                import_tag_results(session, args)
            self.assertEqual(before_invalid, session)

    def test_v2_tag_batch_rejects_previous_run_before_replacement(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        action = session["actions"][0]
        rows = deepcopy(action["tag_layer_results"])
        action["state"] = "OPEN"
        session["operator_contract_version"] = 2
        session["run_id"] = "RUN-CURRENT"
        with tempfile.TemporaryDirectory() as tempdir:
            artifact = Path(tempdir) / "tag-results.json"
            artifact.write_text(
                json.dumps(
                    {
                        "run_id": "RUN-PREVIOUS",
                        "action_id": "ACT-001",
                        "inventory_revision": action.get("inventory_revision", 1),
                        "tag_layer_results": rows,
                    }
                ),
                encoding="utf-8",
            )
            before = deepcopy(session)
            with self.assertRaisesRegex(SystemExit, "previous-run artifacts"):
                import_tag_results(
                    session,
                    Namespace(
                        tag_results=artifact,
                        action_id="ACT-001",
                        results=None,
                    ),
                )
            self.assertEqual(before, session)


if __name__ == "__main__":
    unittest.main()
