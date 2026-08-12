from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from test_pipeline import execution_fixture, fixture, requirement  # noqa: E402

from build_recette_report import _csv_safe_text  # noqa: E402
from event_feedback import event_feedback  # noqa: E402
from execution_contract import validate_session  # noqa: E402
from incremental_recette import event_view  # noqa: E402
from init_coverage_ledger import initialize_requirement  # noqa: E402
from preview_session_ledger import register_case  # noqa: E402
from runtime_state_contract import runtime_snapshot_errors  # noqa: E402
from state_io import (  # noqa: E402
    _pair_journal_path,
    atomic_write_json_pair,
    recover_file_pair,
)


class V220RegressionTests(unittest.TestCase):
    def test_interrupted_runtime_snapshot_is_honest_and_phase_specific(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        action = session["actions"][0]
        case = session["cases"][0]
        snapshot = deepcopy(session["runtime_checks"][1])
        snapshot.update(
            {
                "check_id": "INTERRUPTED-ACT-001",
                "network_capture_active": False,
                "stream_quiet": False,
                "failure_reason": "network_capture_lost",
            }
        )
        errors = runtime_snapshot_errors(
            snapshot,
            phase="interrupted_action",
            action_id=action["action_id"],
            case=case,
            ledger=session,
            results=data,
            expected_connection_epoch=1,
            recorded_at=snapshot["captured_at"],
            action_timestamp=action["action_timestamp"],
        )
        self.assertEqual([], errors)
        normal_errors = runtime_snapshot_errors(
            snapshot,
            phase="after_action",
            action_id=action["action_id"],
            case=case,
            ledger=session,
            results=data,
            expected_connection_epoch=1,
            recorded_at=snapshot["captured_at"],
            action_timestamp=action["action_timestamp"],
        )
        self.assertIn(
            "after-action settlement requires network_capture_active=true",
            normal_errors,
        )

    def test_voided_orphan_runtime_check_is_retained_and_valid(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        orphan = deepcopy(session["runtime_checks"][0])
        orphan.update(
            {
                "check_id": "READY-ORPHAN-001",
                "action_id": "ACT-NEVER-CREATED",
                "consumed": False,
                "voided": True,
                "void_reason": "Operator corrected the action ID before the click.",
                "voided_at": "2026-07-25T10:00:59+00:00",
            }
        )
        orphan.pop("consumed_by_action_id", None)
        session["runtime_checks"].append(orphan)
        self.assertEqual([], validate_session(session, results=data, final=True))

    def test_spa_page_match_requires_direct_route_evidence_only_when_urls_differ(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        action = session["actions"][0]
        case = session["cases"][0]
        snapshot = deepcopy(session["runtime_checks"][0])
        snapshot.update(
            {
                "website_url": "https://shop.example.test/product?variant=steam",
                "selected_page_url": "https://shop.example.test/product",
                "page_match_mode": "same_origin_spa",
                "route_transition_evidence_id": "EVD-ROUTE-001",
                "evidence_ids": [*snapshot["evidence_ids"], "EVD-ROUTE-001"],
            }
        )
        errors = runtime_snapshot_errors(
            snapshot,
            phase="before_action",
            action_id=action["action_id"],
            case=case,
            ledger=session,
            results=data,
            expected_connection_epoch=1,
            recorded_at=snapshot["captured_at"],
            action_timestamp=action["action_timestamp"],
        )
        self.assertEqual([], errors)
        snapshot["evidence_ids"].remove("EVD-ROUTE-001")
        self.assertTrue(
            any(
                "route_transition_evidence_id" in error
                for error in runtime_snapshot_errors(
                    snapshot,
                    phase="before_action",
                    action_id=action["action_id"],
                    case=case,
                    ledger=session,
                    results=data,
                    expected_connection_epoch=1,
                    recorded_at=snapshot["captured_at"],
                    action_timestamp=action["action_timestamp"],
                )
            )
        )

    def test_case_includes_every_configured_client_container(self) -> None:
        data = fixture()
        second = deepcopy(data["run"]["containers"][0])
        second.update(
            {"container_id": "GTM-MEDIA", "workspace": "Media recette", "role": "marketing"}
        )
        data["run"]["containers"].append(second)
        ledger = {
            "approved_origins": ["https://shop.example.test"],
            "cases": [],
            "authorizations": [],
        }
        with tempfile.TemporaryDirectory() as tempdir:
            results = Path(tempdir) / "results.json"
            results.write_text(json.dumps(data), encoding="utf-8")
            register_case(
                ledger,
                Namespace(
                    results=results,
                    case_id="CASE-MULTI",
                    event_group_id="EVG-001",
                    url="https://shop.example.test/product",
                    element="Add to cart",
                    placement="product detail",
                    action="click",
                    variant=[],
                    discovered_from="tracking_plan",
                    scope_status="IN_SCOPE",
                    reason=None,
                    authorization_id=[],
                    include_layer=[],
                    exclude_layer=[],
                    activate_condition=[],
                ),
            )
        self.assertEqual(["GTM-MEDIA", "GTM-TEST"], ledger["cases"][0]["container_ids"])

    def test_operator_interrupts_open_action_as_blocked_without_erasing_attempt(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        data["requirements"] = [initialize_requirement(requirement(data))]
        action = session["actions"][0]
        captured_at = datetime.now(UTC).replace(microsecond=0)
        action["action_timestamp"] = (captured_at - timedelta(seconds=1)).isoformat()
        action["state"] = "OPEN"
        action["layer_results"] = []
        action["tag_layer_results"] = []
        for field in (
            "settlement_check_id",
            "settlement_evidence_ids",
            "first_event_after",
            "settled_final_event",
            "network_request_cursor_after",
            "expected_seen",
            "preview_connected_after",
            "interaction_outcome",
            "completion_signal",
            "stream_settled",
            "settlement_reason",
            "observed_business_push_count",
            "settled_at",
        ):
            action.pop(field, None)
        session["runtime_checks"] = [session["runtime_checks"][0]]
        session["cases"][0].update({"execution_status": "PENDING", "final_action_id": None})
        session["event_closures"] = []
        session["operator_state"] = {
            "status": "ACTIVE",
            "current_event_group_id": "EVG-001",
        }
        snapshot = {
            **deepcopy(execution_fixture(fixture())["runtime_checks"][1]),
            "check_id": "INTERRUPT-ACT-001",
            "network_capture_active": False,
            "stream_quiet": False,
            "failure_reason": "network_capture_lost",
            "evidence_ids": ["EVD-INTERRUPT-ACTION-001"],
            "captured_at": captured_at.isoformat(),
        }
        data["evidence"].append(
            {
                "evidence_id": "EVD-INTERRUPT-ACTION-001",
                "kind": "action_boundary",
                "source": "Playwright",
                "capture_mode": "direct",
                "action_id": "ACT-001",
                "runtime_check_id": "INTERRUPT-ACT-001",
                "runtime_phase": "interrupted_action",
                "path_or_url": "evidence/interruption.json",
                "captured_at": snapshot["captured_at"],
                "description": "Network capture became unavailable during the action.",
            }
        )
        with tempfile.TemporaryDirectory() as tempdir:
            results = Path(tempdir) / "results.json"
            ledger = Path(tempdir) / "session.json"
            capture = Path(tempdir) / "interruption.json"
            results.write_text(json.dumps(data), encoding="utf-8")
            ledger.write_text(json.dumps(session), encoding="utf-8")
            capture.write_text(json.dumps(snapshot), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "recette_operator.py"),
                    "interrupt-action",
                    str(results),
                    str(ledger),
                    str(capture),
                    "--action-id",
                    "ACT-001",
                    "--blocker-id",
                    "BLK-RUNTIME-001",
                    "--reason",
                    "Browser network capture became unavailable before settlement.",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            updated = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual("SETTLED", updated["actions"][0]["state"])
        self.assertEqual("uncertain", updated["actions"][0]["interaction_outcome"])
        self.assertEqual("BLOCKED", updated["cases"][0]["execution_status"])
        self.assertEqual(2, updated["connection_epoch"])
        self.assertTrue(
            any(row["check_id"] == "INTERRUPT-ACT-001" for row in updated["runtime_checks"])
        )

    def test_primary_outcome_covers_sensitive_data_layer(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        requirement(data)["verdict"]["sensitive_data"] = "FAIL"
        requirement(data)["verdict"]["overall"] = "FAIL"
        layer = next(
            row
            for row in session["actions"][0]["layer_results"]
            if row["layer"] == "sensitive_data_scan"
        )
        layer.update({"status": "FAIL", "reason": "Sensitive field reached an unsafe layer."})
        self.assertEqual(
            "SENSITIVE_DATA_INVALID", event_feedback(data, session)[0]["primary_outcome"]
        )

    def test_pending_case_never_reports_not_tested(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        session["cases"][0].update({"execution_status": "PENDING", "final_action_id": None})
        session["actions"] = []
        session["runtime_checks"] = []
        session["business_pushes"] = []
        session["event_closures"] = []
        feedback = event_feedback(data, session)[0]
        self.assertNotEqual("NOT_TESTED", feedback["status"])
        self.assertEqual("PARTIAL_VARIANT_COVERAGE", feedback["primary_outcome"])

    def test_event_view_drops_unrelated_evidence(self) -> None:
        data = fixture()
        data["evidence"].append(
            {
                "evidence_id": "EVD-UNRELATED",
                "kind": "screenshot",
                "source": "Playwright",
                "capture_mode": "direct",
                "path_or_url": "evidence/unrelated.png",
                "captured_at": "2026-07-25T10:01:03+00:00",
                "description": "Evidence for another event.",
            }
        )
        visible = {row["evidence_id"] for row in event_view(data, "EVG-001")["evidence"]}
        self.assertNotIn("EVD-UNRELATED", visible)
        self.assertIn("EVD-RAW-011", visible)

    def test_csv_sidecar_text_blocks_formula_interpretation(self) -> None:
        self.assertEqual(
            '\'=HYPERLINK("https://example.test")',
            _csv_safe_text('=HYPERLINK("https://example.test")'),
        )
        self.assertEqual("-1", _csv_safe_text(-1))
        self.assertEqual("plain", _csv_safe_text("plain"))

    def test_report_cli_rejects_output_aliasing_input(self) -> None:
        data = fixture()
        with tempfile.TemporaryDirectory() as tempdir:
            aliased = Path(tempdir) / "results.xlsx"
            prior = json.dumps(data)
            aliased.write_text(prior, encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "build_recette_report.py"),
                    str(aliased),
                    str(aliased),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, completed.returncode)
            self.assertIn("cannot overwrite an input ledger", completed.stderr)
            self.assertEqual(prior, aliased.read_text(encoding="utf-8"))

    def test_import_layers_failure_does_not_persist_partial_rows(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        session["actions"][0]["layer_results"] = []
        payload = {
            "layer_results": [
                {
                    "layer": "raw_api_call",
                    "status": "PASS",
                    "reason": "Matched.",
                    "evidence_ids": ["EVD-RAW-011"],
                },
                {
                    "layer": "raw_api_call",
                    "status": "PASS",
                    "reason": "Duplicate should reject the batch.",
                    "evidence_ids": ["EVD-RAW-011"],
                },
            ]
        }
        with tempfile.TemporaryDirectory() as tempdir:
            ledger = Path(tempdir) / "session.json"
            layers = Path(tempdir) / "layers.json"
            ledger.write_text(json.dumps(session, indent=2), encoding="utf-8")
            layers.write_text(json.dumps(payload), encoding="utf-8")
            prior = ledger.read_bytes()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "preview_session_ledger.py"),
                    "import-layers",
                    str(ledger),
                    str(layers),
                    "--action-id",
                    "ACT-001",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertEqual(prior, ledger.read_bytes())

    def test_pair_write_rolls_back_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            first = Path(tempdir) / "results.json"
            second = Path(tempdir) / "session.json"
            first.write_text('{"old": 1}\n', encoding="utf-8")
            second.write_text('{"old": 2}\n', encoding="utf-8")
            prior = (first.read_bytes(), second.read_bytes())

            def fail_second_target(source: Path, target: Path) -> None:
                if target.resolve() == second.resolve():
                    raise KeyboardInterrupt
                source.replace(target)

            with (
                patch("state_io._replace", side_effect=fail_second_target),
                self.assertRaises(KeyboardInterrupt),
            ):
                atomic_write_json_pair(first, {"new": 1}, second, {"new": 2})
            self.assertEqual(prior, (first.read_bytes(), second.read_bytes()))

    def test_pair_write_recovers_a_prepared_crash_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            first = Path(tempdir) / "results.json"
            second = Path(tempdir) / "session.json"
            first_backup = Path(tempdir) / ".results.backup"
            second_backup = Path(tempdir) / ".session.backup"
            first.write_text('{"new": 1}\n', encoding="utf-8")
            second.write_text('{"new": 2}\n', encoding="utf-8")
            first_backup.write_text('{"old": 1}\n', encoding="utf-8")
            second_backup.write_text('{"old": 2}\n', encoding="utf-8")
            journal = _pair_journal_path(first, second)
            journal.write_text(
                json.dumps(
                    {
                        "transaction_id": "crash-simulation",
                        "state": "PREPARED",
                        "targets": [str(first.resolve()), str(second.resolve())],
                        "target_existed": [True, True],
                        "backups": [
                            str(first_backup.resolve()),
                            str(second_backup.resolve()),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(recover_file_pair(first, second))
            self.assertEqual({"old": 1}, json.loads(first.read_text(encoding="utf-8")))
            self.assertEqual({"old": 2}, json.loads(second.read_text(encoding="utf-8")))
            self.assertFalse(journal.exists())


if __name__ == "__main__":
    unittest.main()
