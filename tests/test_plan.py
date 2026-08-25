from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from helpers import add_event_sheet, make_plan

from xlsx_plan import PlanError, compile_xlsx


class PlanTests(unittest.TestCase):
    def test_xlsx_detail_sheets_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = make_plan(Path(directory) / "plan.xlsx", finite=True)
            plan = compile_xlsx(path)
        self.assertEqual(plan["event_count"], 1)
        self.assertEqual(plan["events"][0]["label"], "view_item")
        paths = {field["path"]: field for field in plan["events"][0]["fields"]}
        self.assertNotIn("images", paths)
        self.assertEqual(paths["ecommerce.page_language"]["allowed_values"], ["en", "fr"])
        self.assertEqual(paths["ecommerce.items[].item_name"]["rule"], "present")
        self.assertEqual(paths["ecommerce.currency"]["expected"], "EUR")

    def test_custom_wrapper_has_semantic_selector(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.xlsx"
            workbook = Workbook()
            workbook.active.title = "Cover"
            add_event_sheet(
                workbook,
                "Newsletter",
                "gtm.custom_event",
                [("event", "string", "gtm.custom_event"), ("event_name", "string", "newsletter")],
            )
            workbook.save(path)
            workbook.close()
            event = compile_xlsx(path)["events"][0]
        self.assertEqual(event["label"], "Newsletter")
        self.assertEqual(
            event["selector"],
            {"event": "gtm.custom_event", "event_name": "newsletter"},
        )

    def test_only_xlsx_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.yaml"
            path.write_text("events: []", encoding="utf-8")
            with self.assertRaisesRegex(PlanError, "exactly one .xlsx"):
                compile_xlsx(path)

    def test_ambiguous_type_fails_with_sheet_and_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.xlsx"
            workbook = Workbook()
            workbook.active.title = "Cover"
            add_event_sheet(workbook, "Bad Event", "bad_event", [("value", "mystery", "x")])
            workbook.save(path)
            workbook.close()
            with self.assertRaisesRegex(PlanError, r"Bad Event!10.*unsupported JSON type"):
                compile_xlsx(path)

    def test_large_plan_compiles_without_preprocessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.xlsx"
            workbook = Workbook()
            workbook.active.title = "Cover"
            for event_index in range(24):
                fields = [
                    (f"field_{field_index}", "string", f"dynamic-{field_index}")
                    for field_index in range(12)
                ]
                add_event_sheet(
                    workbook,
                    f"Event {event_index + 1}",
                    f"event_{event_index + 1}",
                    fields,
                )
            workbook.save(path)
            workbook.close()
            started = time.perf_counter()
            plan = compile_xlsx(path)
            elapsed = time.perf_counter() - started
        self.assertEqual(plan["event_count"], 24)
        self.assertEqual(plan["field_count"], 288)
        self.assertLess(elapsed, 5.0)


if __name__ == "__main__":
    unittest.main()
