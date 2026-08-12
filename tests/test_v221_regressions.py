from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from test_pipeline import execution_fixture, fixture  # noqa: E402

from preview_session_ledger import begin_action, settle_action  # noqa: E402
from runtime_state_contract import (  # noqa: E402
    runtime_snapshot_errors,
    validate_runtime_evidence,
)
from state_io import _pair_journal_path  # noqa: E402

SETTLEMENT_FIELDS = (
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
)


def open_first_action(data: dict, session: dict) -> dict:
    action = session["actions"][0]
    action["state"] = "OPEN"
    for field in SETTLEMENT_FIELDS:
        action.pop(field, None)
    session["runtime_checks"][1].update({"consumed": False})
    session["runtime_checks"][1].pop("consumed_by_action_id", None)
    session["cases"][0].update(
        {
            "execution_status": "PENDING",
            "final_action_id": None,
            "blocker_id": None,
            "reason": None,
        }
    )
    session["event_closures"] = []
    session["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": "EVG-001",
    }
    return action


class V221RegressionTests(unittest.TestCase):
    def test_interrupted_case_can_start_one_linked_retry_without_erasing_blocker(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        prior = session["actions"][0]
        prior.update(
            {
                "interaction_outcome": "uncertain",
                "completion_signal": "Network capture was lost.",
                "stream_settled": False,
                "settlement_reason": "network_capture_lost",
                "interruption_blocker_id": "BLK-NETWORK-001",
                "interruption_reason": "Network capture was lost before settlement.",
            }
        )
        settlement = session["runtime_checks"][1]
        settlement.update(
            {
                "phase": "interrupted_action",
                "network_capture_active": False,
                "stream_quiet": False,
                "failure_reason": "network_capture_lost",
            }
        )
        case = session["cases"][0]
        case.update(
            {
                "execution_status": "BLOCKED",
                "final_action_id": None,
                "blocker_id": "BLK-NETWORK-001",
                "reason": "Network capture was lost before settlement.",
            }
        )
        session["event_closures"] = []
        session["operator_state"] = {
            "status": "ACTIVE",
            "current_event_group_id": "EVG-001",
        }
        readiness = deepcopy(session["runtime_checks"][0])
        readiness.update(
            {
                "check_id": "READY-ACT-002",
                "action_id": "ACT-002",
                "consumed": False,
                "captured_at": "2026-07-25T10:01:10+00:00",
                "recorded_at": "2026-07-25T10:01:10+00:00",
            }
        )
        readiness.pop("consumed_by_action_id", None)
        session["runtime_checks"].append(readiness)

        begin_action(
            session,
            Namespace(
                action_id="ACT-002",
                case_id="CASE-001",
                readiness_check_id="READY-ACT-002",
                consent_state="analytics_storage=granted",
                quiet_window_ms=2000,
                timeout_ms=15000,
                retry_of_action_id="ACT-001",
            ),
        )

        self.assertEqual("PENDING", case["execution_status"])
        self.assertIsNone(case["blocker_id"])
        self.assertEqual("BLK-NETWORK-001", prior["interruption_blocker_id"])
        self.assertEqual("ACT-001", session["actions"][1]["retry_of_action_id"])

    def test_normal_settlement_rejects_an_interruption_reason(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        open_first_action(data, session)
        with self.assertRaisesRegex(SystemExit, "interrupted_action"):
            settle_action(
                session,
                Namespace(
                    action_id="ACT-001",
                    settlement_check_id=session["runtime_checks"][1]["check_id"],
                    expected_seen="true",
                    interaction_outcome="uncertain",
                    completion_signal="Preview disconnected.",
                    settlement_reason="preview_disconnected",
                ),
            )

    def test_only_preview_disconnect_advances_the_connection_epoch(self) -> None:
        for reason, expected_epoch in (
            ("network_capture_lost", 1),
            ("preview_disconnected", 2),
        ):
            with self.subTest(reason=reason):
                data = fixture()
                session = execution_fixture(data)
                open_first_action(data, session)
                settlement = session["runtime_checks"][1]
                settlement.update(
                    {
                        "phase": "interrupted_action",
                        "failure_reason": reason,
                        "stream_quiet": False,
                        "network_capture_active": reason != "network_capture_lost",
                        "preview_connected": reason != "preview_disconnected",
                    }
                )
                settle_action(
                    session,
                    Namespace(
                        action_id="ACT-001",
                        settlement_check_id=settlement["check_id"],
                        expected_seen="true",
                        interaction_outcome="uncertain",
                        completion_signal=f"Runtime interruption: {reason}",
                        settlement_reason=reason,
                    ),
                )
                self.assertEqual(expected_epoch, session["connection_epoch"])

    def test_spa_route_proof_must_be_direct_navigation_evidence(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        check = deepcopy(session["runtime_checks"][0])
        check.update(
            {
                "website_url": "https://shop.example.test/product?variant=steam",
                "selected_page_url": "https://shop.example.test/product",
                "page_match_mode": "same_origin_spa",
                "route_transition_evidence_id": "EVD-ROUTE-001",
                "evidence_ids": [*check["evidence_ids"], "EVD-ROUTE-001"],
            }
        )
        evidence = {row["evidence_id"]: row for row in data["evidence"]}
        route = deepcopy(evidence[check["evidence_ids"][0]])
        route.update(
            {
                "evidence_id": "EVD-ROUTE-001",
                "kind": "action_boundary",
                "runtime_check_id": check["check_id"],
                "runtime_phase": check["phase"],
                "action_id": check["action_id"],
                "captured_at": check["captured_at"],
            }
        )
        evidence[route["evidence_id"]] = route
        errors = validate_runtime_evidence(check, evidence)
        self.assertTrue(any("must be navigation" in error for error in errors))
        route["kind"] = "navigation"
        self.assertEqual([], validate_runtime_evidence(check, evidence))

    def test_same_origin_spa_mode_rejects_identical_urls(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        action = session["actions"][0]
        case = session["cases"][0]
        snapshot = deepcopy(session["runtime_checks"][0])
        snapshot["page_match_mode"] = "same_origin_spa"
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
        self.assertTrue(any("valid only when" in error for error in errors))

    def test_multi_container_runtime_fails_closed(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        second = deepcopy(data["run"]["containers"][0])
        second.update(
            {"container_id": "GTM-MEDIA", "workspace": "Media recette", "role": "marketing"}
        )
        data["run"]["containers"].append(second)
        case = session["cases"][0]
        case["container_ids"].append("GTM-MEDIA")
        session["surfaces"]["gtm-media"] = {
            "role": "gtm_workspace",
            "url": "https://tagmanager.google.com/",
            "container_id": "GTM-MEDIA",
            "workspace": "Media recette",
        }
        snapshot = deepcopy(session["runtime_checks"][0])
        snapshot["containers"].append({"container_id": "GTM-MEDIA", "workspace": "Media recette"})
        errors = runtime_snapshot_errors(
            snapshot,
            phase="before_action",
            action_id=session["actions"][0]["action_id"],
            case=case,
            ledger=session,
            results=data,
            expected_connection_epoch=1,
            recorded_at=snapshot["captured_at"],
            action_timestamp=session["actions"][0]["action_timestamp"],
        )
        self.assertTrue(
            any("cannot certify multiple client containers" in error for error in errors)
        )

    def test_import_layers_rejects_invalid_status_without_touching_the_ledger(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        open_first_action(data, session)
        session["actions"][0]["layer_results"] = []
        payload = {
            "layer_results": [
                {
                    "layer": "raw_api_call",
                    "status": "BROKEN",
                    "reason": "Unsupported status must fail.",
                    "evidence_ids": ["EVD-RAW-011"],
                }
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
            self.assertIn("unsupported status", completed.stderr + completed.stdout)
            self.assertEqual(prior, ledger.read_bytes())

    def test_operator_status_recovers_a_prepared_result_session_pair(self) -> None:
        data = fixture()
        session = execution_fixture(data)
        with tempfile.TemporaryDirectory() as tempdir:
            results = Path(tempdir) / "results.json"
            ledger = Path(tempdir) / "session.json"
            results_backup = Path(tempdir) / ".results.backup"
            session_backup = Path(tempdir) / ".session.backup"
            results.write_text('{"torn": true}\n', encoding="utf-8")
            ledger.write_text('{"torn": true}\n', encoding="utf-8")
            results_backup.write_text(json.dumps(data), encoding="utf-8")
            session_backup.write_text(json.dumps(session), encoding="utf-8")
            journal = _pair_journal_path(results, ledger)
            journal.write_text(
                json.dumps(
                    {
                        "transaction_id": "crash-simulation",
                        "state": "PREPARED",
                        "targets": [str(results.resolve()), str(ledger.resolve())],
                        "target_existed": [True, True],
                        "backups": [
                            str(results_backup.resolve()),
                            str(session_backup.resolve()),
                        ],
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "recette_operator.py"),
                    "status",
                    str(results),
                    str(ledger),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertEqual(data, json.loads(results.read_text(encoding="utf-8")))
            self.assertEqual(session, json.loads(ledger.read_text(encoding="utf-8")))
            self.assertFalse(journal.exists())


if __name__ == "__main__":
    unittest.main()
