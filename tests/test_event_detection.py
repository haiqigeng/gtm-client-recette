from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tag_assistant import TagAssistantError, detect_event, parse_api_call


def raw(*calls: str) -> dict:
    rows = []
    for index, call in enumerate(calls):
        semantic = re.search(r"event_name\s*:\s*['\"]([^'\"]+)", call)
        technical = re.search(r"event\s*:\s*['\"]([^'\"]+)", call)
        row_name = (semantic or technical).group(1) if semantic or technical else "Message"
        rows.append(
            {
                "cursor": 5 + index,
                "row_name": row_name,
                "api_call_text": call,
                "panel_text": "",
                "tags": [],
            }
        )
    return {
        "preview_cursor_before": 4,
        "preview_cursor_after": 4 + len(calls),
        "overview_rows": [{"cursor": row["cursor"], "row_name": row["row_name"]} for row in rows],
        "rows": rows,
    }


class EventDetectionTests(unittest.TestCase):
    def test_data_layer_and_gtag_are_parsed_without_evaluation(self) -> None:
        data_layer = parse_api_call(
            """window.dataLayer.push({
              event: 'view_item', // event identity
              ecommerce: {currency: 'E' + 'UR'},
              page: 'https://example.test/a//b' /* quoted slashes stay intact */
            });"""
        )
        gtag = parse_api_call("gtag('event', 'purchase', {value: 10, paid: true});")
        self.assertEqual(data_layer["payload"]["ecommerce"]["currency"], "EUR")
        self.assertEqual(data_layer["payload"]["page"], "https://example.test/a//b")
        self.assertEqual(gtag["payload"], {"event": "purchase", "value": 10, "paid": True})

    def test_wrapped_custom_event_requires_both_selector_fields(self) -> None:
        capture = raw(
            "dataLayer.push({event:'gtm.custom_event',event_name:'newsletter'});",
            "dataLayer.push({event:'gtm.custom_event',event_name:'click_contact'});",
        )
        detected = detect_event(
            capture, {"event": "gtm.custom_event", "event_name": "click_contact"}
        )
        self.assertEqual(detected["occurrence_count"], 1)
        self.assertEqual(detected["selected"]["cursor"], 6)

    def test_missing_and_duplicate_occurrences_are_preserved(self) -> None:
        missing = detect_event(raw("dataLayer.push({event:'view_item'});"), {"event": "purchase"})
        duplicate = detect_event(
            raw(
                "dataLayer.push({event:'purchase'});",
                "dataLayer.push({event:'purchase'});",
            ),
            {"event": "purchase"},
        )
        self.assertEqual(missing["occurrence_count"], 0)
        self.assertEqual(duplicate["occurrence_count"], 2)

    def test_malformed_or_noncontiguous_capture_is_incomplete(self) -> None:
        capture = raw("dataLayer.push({event:'view_item'")
        capture["rows"][0]["cursor"] = 6
        capture["overview_rows"][0]["cursor"] = 6
        detected = detect_event(capture, {"event": "view_item"})
        self.assertFalse(detected["complete"])
        self.assertFalse(detected["attributable"])
        self.assertEqual(detected["occurrence_count"], 0)

    def test_invalid_selector_fails_before_detection(self) -> None:
        with self.assertRaisesRegex(TagAssistantError, "containing event"):
            detect_event(raw(), {"event_name": "view_item"})


if __name__ == "__main__":
    unittest.main()
