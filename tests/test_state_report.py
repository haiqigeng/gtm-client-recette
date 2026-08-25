from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from helpers import action_bundle, add_event_sheet, blocked_bundle, bundle_fixture, make_plan

from state import RunError, complete_action, finish_run, read_records, start_action, start_run


def write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def evidence(run: Path, action: dict, value: dict) -> Path:
    return write_json(run / f"evidence-{action['action_id']}.json", value)


class StateAndReportTests(unittest.TestCase):
    def test_complete_fixed_lifecycle_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = make_plan(root / "plan.xlsx")
            run = root / "run"
            plan = start_run(plan_path, run)
            action = start_action(run, 0)
            bundle = bundle_fixture()
            bundle["action_id"] = action["action_id"]
            bundle["event_id"] = action["event_id"]
            bundle["network"]["requests"][0]["url"] += "?session_id=secret"
            bundle["reality"]["findings"].append(
                {"status": "REVIEW", "code": "synthetic.formula", "reason": "=1+1"}
            )
            completed = complete_action(run, evidence(run, action, bundle))
            self.assertFalse(completed["stopped"])
            self.assertNotIn("secret", (run / "evidence-A-0001.json").read_text(encoding="utf-8"))
            self.assertNotIn('"evidence":', (run / "events.ndjson").read_text(encoding="utf-8"))
            output = finish_run(run)
            workbook = load_workbook(output, read_only=True)
            try:
                self.assertEqual(workbook.sheetnames, ["Conclusion", "Event feedback", "Checks"])
                self.assertEqual(workbook["Conclusion"].max_row, plan["event_count"] + 1)
                self.assertEqual(workbook["Event feedback"].max_row, 6)
                values = [
                    cell.value
                    for sheet in workbook.worksheets
                    for row in sheet.iter_rows()
                    for cell in row
                ]
                self.assertIn("'=1+1", values)
            finally:
                workbook.close()
            with self.assertRaisesRegex(RunError, "already finished"):
                start_action(run, 1)

    def test_two_consecutive_all_blocked_events_stop_without_xlsx(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx", two_events=True), run)
            first = start_action(run, 0)
            result = complete_action(
                run,
                evidence(
                    run,
                    first,
                    blocked_bundle(first["action_id"], first["event_id"]),
                ),
            )
            self.assertFalse(result["stopped"])
            second = start_action(run, 0)
            result = complete_action(
                run,
                evidence(
                    run,
                    second,
                    blocked_bundle(second["action_id"], second["event_id"]),
                ),
            )
            self.assertTrue(result["stopped"])
            self.assertFalse((run / "gtm-client-recette-results.xlsx").exists())
            with self.assertRaisesRegex(RunError, "stopped run"):
                finish_run(run)

    def test_two_blocked_scenarios_of_one_event_do_not_trigger_event_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx", two_events=True, finite=True), run)

            first = start_action(run, 0)
            first_bundle = blocked_bundle(first["action_id"], first["event_id"])
            first_bundle["scenario"] = {
                "id": "english",
                "signature": "language-en",
                "values": {"ecommerce.page_language": "en"},
            }
            first_bundle["coverage"]["complete"] = False
            first_bundle["coverage"]["remaining"] = ["ecommerce.page_language=fr"]
            self.assertFalse(complete_action(run, evidence(run, first, first_bundle))["stopped"])

            second = start_action(run, 0)
            second_bundle = blocked_bundle(second["action_id"], second["event_id"])
            second_bundle["scenario"] = {
                "id": "french",
                "signature": "language-fr",
                "values": {"ecommerce.page_language": "fr"},
            }
            self.assertFalse(complete_action(run, evidence(run, second, second_bundle))["stopped"])

            third = start_action(run, 0)
            third_bundle = blocked_bundle(third["action_id"], third["event_id"])
            self.assertTrue(complete_action(run, evidence(run, third, third_bundle))["stopped"])

    def test_finite_values_must_be_tested_or_declared_unreachable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx", finite=True), run)
            first = start_action(run, 0)
            bundle = bundle_fixture()
            bundle["action_id"] = first["action_id"]
            bundle["event_id"] = first["event_id"]
            bundle["scenario"]["id"] = "english"
            bundle["scenario"]["values"]["ecommerce.page_language"] = "en"
            bundle["coverage"]["complete"] = False
            bundle["coverage"]["remaining"] = ["ecommerce.page_language=fr"]
            complete_action(run, evidence(run, first, bundle))

            second = start_action(run, 1)
            bundle["action_id"] = second["action_id"]
            bundle["scenario"]["id"] = "french"
            bundle["scenario"]["values"]["ecommerce.page_language"] = "fr"
            bundle["coverage"]["complete"] = True
            bundle["coverage"]["remaining"] = []
            complete_action(run, evidence(run, second, bundle))
            self.assertTrue(finish_run(run).is_file())

    def test_false_complete_finite_coverage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx", finite=True), run)
            action = start_action(run, 0)
            bundle = bundle_fixture()
            bundle["action_id"] = action["action_id"]
            bundle["event_id"] = action["event_id"]
            bundle["scenario"]["values"]["ecommerce.page_language"] = "en"
            with self.assertRaisesRegex(RunError, "planned finite values"):
                complete_action(run, evidence(run, action, bundle))

    def test_corrupted_stream_is_not_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx"), run)
            with (run / "events.ndjson").open("a", encoding="utf-8") as handle:
                handle.write("not-json\n")
            with self.assertRaisesRegex(RunError, "corrupted"):
                read_records(run)

    def test_cursor_must_continue_from_preceding_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / "run"
            start_run(make_plan(root / "plan.xlsx", finite=True), run)
            first = start_action(run, 7)
            bundle = bundle_fixture()
            bundle["action_id"] = first["action_id"]
            bundle["event_id"] = first["event_id"]
            bundle["preview_cursor"] = 9
            bundle["behavior"]["messages"][0]["cursor"] = 8
            bundle["source"]["selected"]["cursor"] = 8
            bundle["source"]["calls"][0]["cursor"] = 8
            bundle["scenario"]["values"]["ecommerce.page_language"] = "en"
            bundle["coverage"]["complete"] = False
            bundle["coverage"]["remaining"] = ["ecommerce.page_language=fr"]
            complete_action(run, evidence(run, first, bundle))
            with self.assertRaisesRegex(RunError, "preceding completed action cursor"):
                start_action(run, 8)
            self.assertEqual(start_action(run, 9)["preview_cursor"], 9)

    def test_multi_event_lifecycle_stays_fast_as_evidence_grows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "stress.xlsx"
            workbook = Workbook()
            workbook.active.title = "Cover"
            for event_index in range(24):
                add_event_sheet(
                    workbook,
                    f"Event {event_index + 1}",
                    f"event_{event_index + 1}",
                    [(f"field_{index}", "string", "dynamic") for index in range(8)],
                )
            workbook.save(plan_path)
            workbook.close()
            run = root / "run"
            started = time.perf_counter()
            start_run(plan_path, run)
            for cursor in range(1, 25):
                action = start_action(run, cursor - 1)
                bundle = action_bundle(action, cursor)
                result = complete_action(run, evidence(run, action, bundle))
                self.assertFalse(result["stopped"])
            output = finish_run(run)
            elapsed = time.perf_counter() - started
            self.assertTrue(output.is_file())
            self.assertLess(elapsed, 10.0)


if __name__ == "__main__":
    unittest.main()
