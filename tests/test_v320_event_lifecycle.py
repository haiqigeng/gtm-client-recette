from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from test_v310_optimizations import upgrade_to_v2  # noqa: E402

from evidence_integrity import build_integrity_record  # noqa: E402
from execution_contract import validate_session  # noqa: E402
from incremental_recette import scaffold_event_patch  # noqa: E402
from init_coverage_ledger import initialize_requirement  # noqa: E402
from layer_contract import CANONICAL_LAYERS, TAG_RESULT_LAYERS  # noqa: E402


def two_event_open_run(base_dir: Path) -> tuple[dict, dict, dict]:
    data, session = upgrade_to_v2(base_dir)
    second = initialize_requirement(deepcopy(data["requirements"][0]))
    second.update({"requirement_id": "REQ-002", "event_group_id": "EVG-002"})
    second["source"].update({"plan_order": 2, "row": 13})
    second["expectation"]["event_name"] = "view_cart"
    second["journey"].update(
        {
            "step_id": "S-CART",
            "action": "Open the cart",
            "url": "https://shop.example.test/cart",
        }
    )
    data["requirements"].append(second)
    data["run"]["requirement_inventory"].append("REQ-002")
    data["run"]["event_inventory"].append(
        {"event_group_id": "EVG-002", "event_name": "view_cart", "plan_order": 2}
    )

    session["event_closures"] = []
    session["closure_history"] = []
    session["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": "EVG-001",
    }
    session["stream_contract"].update(
        {
            "status": "OPEN",
            "reviewed_through_preview_event_index": 12,
            "reviewed_through_datalayer_call_index": 1,
        }
    )
    session["stream_contract"].pop("closed_at", None)
    session["stream_segments"] = [
        row for row in session["stream_segments"] if row.get("kind") != "FINAL"
    ]
    session["evidence_integrity"] = build_integrity_record(data, base_dir)
    patch = {
        "event_group_id": "EVG-001",
        "requirements": [deepcopy(data["requirements"][0])],
        # Simulates an interrupted commit where this exact evidence row already landed.
        "evidence": [deepcopy(data["evidence"][0])],
        "unexpected": [],
        "blockers": [],
    }
    return data, session, patch


class EventLifecycleV320Tests(unittest.TestCase):
    def run_operator(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "recette_operator.py"), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_first_event_closes_on_a_certified_open_prefix_and_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            base = Path(tempdir)
            data, session, patch = two_event_open_run(base)
            results_path = base / "results.json"
            session_path = base / "session.json"
            patch_path = base / "event-1.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            session_path.write_text(json.dumps(session), encoding="utf-8")
            patch_path.write_text(json.dumps(patch), encoding="utf-8")

            arguments = (
                "close-event",
                str(results_path),
                str(session_path),
                str(patch_path),
                "--event-group-id",
                "EVG-001",
                "--evidence-base-dir",
                str(base),
            )
            closed = self.run_operator(*arguments)
            self.assertEqual(0, closed.returncode, closed.stdout + closed.stderr)
            feedback = json.loads(closed.stdout)
            self.assertEqual("CLOSED", feedback["commit_status"])
            self.assertEqual("PASS", feedback["component_statuses"]["continuous_stream"])

            persisted_session = json.loads(session_path.read_text(encoding="utf-8"))
            closure = persisted_session["event_closures"][0]
            self.assertEqual("OPEN", persisted_session["stream_contract"]["status"])
            self.assertEqual(2, closure["closure_contract_version"])
            self.assertEqual("VERIFIED", closure["evidence_integrity"]["status"])
            self.assertEqual(64, len(closure["event_patch_sha256"]))
            self.assertEqual(64, len(closure["stream_prefix_sha256"]))

            tampered_session = deepcopy(persisted_session)
            tampered_session["event_closures"][0]["stream_prefix_sha256"] = "0" * 64
            tamper_errors = validate_session(
                tampered_session,
                results=json.loads(results_path.read_text(encoding="utf-8")),
                final=False,
            )
            self.assertTrue(
                any("certified stream prefix digest is stale" in row for row in tamper_errors),
                tamper_errors,
            )

            replayed = self.run_operator(*arguments)
            self.assertEqual(0, replayed.returncode, replayed.stdout + replayed.stderr)
            self.assertEqual("ALREADY_CLOSED", json.loads(replayed.stdout)["commit_status"])
            self.assertEqual(
                1,
                len(json.loads(session_path.read_text(encoding="utf-8"))["event_closures"]),
            )

            changed_patch = deepcopy(patch)
            changed_patch["requirements"][0]["notes"] = "Different material result."
            patch_path.write_text(json.dumps(changed_patch), encoding="utf-8")
            rejected = self.run_operator(*arguments)
            self.assertEqual(2, rejected.returncode)
            self.assertIn("already closed with different material results", rejected.stdout)

            final_errors = validate_session(
                json.loads(session_path.read_text(encoding="utf-8")),
                results=json.loads(results_path.read_text(encoding="utf-8")),
                final=True,
            )
            self.assertTrue(any("one closure for every plan event" in row for row in final_errors))
            self.assertTrue(any("CLOSED for final certification" in row for row in final_errors))

    def test_unreconciled_inter_action_gap_prevents_event_certification(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            base = Path(tempdir)
            data, session, patch = two_event_open_run(base)
            session["stream_segments"].append(
                {
                    "segment_id": "SEG-GAP",
                    "kind": "INTER_ACTION",
                    "status": "CAPTURING",
                    "connection_epoch": 1,
                    "action_id": None,
                    "previous_segment_id": "SEG-ACT-001",
                    "start_preview_event_index": 12,
                    "end_preview_event_index": 13,
                    "start_datalayer_call_index": 1,
                    "end_datalayer_call_index": 2,
                    "started_at": "2026-07-25T10:01:03+00:00",
                    "ended_at": None,
                    "evidence_ids": [],
                    "observed_push_ids": [],
                    "datalayer_call_reviews": [],
                }
            )
            session["stream_contract"].update(
                {
                    "reviewed_through_preview_event_index": 13,
                    "reviewed_through_datalayer_call_index": 2,
                }
            )
            results_path = base / "results.json"
            session_path = base / "session.json"
            patch_path = base / "event-1.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            session_path.write_text(json.dumps(session), encoding="utf-8")
            patch_path.write_text(json.dumps(patch), encoding="utf-8")
            rejected = self.run_operator(
                "close-event",
                str(results_path),
                str(session_path),
                str(patch_path),
                "--event-group-id",
                "EVG-001",
                "--evidence-base-dir",
                str(base),
            )
            self.assertEqual(2, rejected.returncode)
            self.assertIn("certified stream prefix requires RECONCILED", rejected.stdout)
            self.assertEqual(
                [], json.loads(session_path.read_text(encoding="utf-8"))["event_closures"]
            )

    def test_equivalent_timezone_timestamps_bind_to_the_same_action(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            original = datetime.fromisoformat(session["actions"][0]["action_timestamp"])
            equivalent = original.astimezone(timezone(timedelta(hours=2))).isoformat()
            data["requirements"][0]["action_boundary"]["action_timestamp"] = equivalent
            errors = validate_session(session, results=data, final=True)
            self.assertFalse(
                any("action_boundary.action_timestamp differs" in row for row in errors),
                errors,
            )

    def test_event_scaffold_targets_the_settled_final_retry_and_all_layer_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            data, session = upgrade_to_v2(Path(tempdir))
            prior = deepcopy(session["actions"][0])
            prior["action_id"] = "ACT-INTERRUPTED"
            prior["interaction_outcome"] = "uncertain"
            session["actions"].insert(0, prior)
            patch = scaffold_event_patch(data, "EVG-001", session)
            context = patch["capture_context"]
            self.assertEqual(
                "ACT-001",
                context["action_boundaries_by_case"][0]["action_id"],
            )
            self.assertEqual("ACT-001", patch["requirements"][0]["action_boundary"]["action_id"])
            self.assertEqual(
                list(CANONICAL_LAYERS),
                [row["layer"] for row in context["action_layer_scaffolds"][0]["layer_results"]],
            )
            self.assertEqual(
                list(TAG_RESULT_LAYERS),
                [row["layer"] for row in context["tag_layer_scaffolds"][0]["tag_layer_results"]],
            )

    def test_operator_v2_rejects_the_non_atomic_low_level_apply_command(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            base = Path(tempdir)
            data, session, patch = two_event_open_run(base)
            results_path = base / "results.json"
            session_path = base / "session.json"
            patch_path = base / "event-1.json"
            results_path.write_text(json.dumps(data), encoding="utf-8")
            session_path.write_text(json.dumps(session), encoding="utf-8")
            patch_path.write_text(json.dumps(patch), encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "incremental_recette.py"),
                    "apply-event",
                    str(results_path),
                    str(patch_path),
                    "--session-ledger",
                    str(session_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn(
                "must use recette_operator.py close-event",
                rejected.stdout + rejected.stderr,
            )


if __name__ == "__main__":
    unittest.main()
