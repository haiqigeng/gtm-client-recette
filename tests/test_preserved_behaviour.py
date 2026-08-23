from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from client_side_rules import MISSING, path_value, path_values, scan_sensitive_value
from core.capture import classify_datalayer_argument, redact_for_persistence
from core.report import formula_safe_text, set_safe_cell
from decode_browser_requests import decode_requests
from import_ga4_tracking_plan_handoff import interpreted_requirements, verify_delivery
from safe_regex import compile_pattern
from value_semantics import field_state_for, json_value_type, strict_equal


class PreservedBehaviourTests(unittest.TestCase):
    def test_strict_comparison_keeps_boolean_number_and_string_distinct(self) -> None:
        self.assertFalse(strict_equal(True, 1))
        self.assertFalse(strict_equal("29.9", 29.9))
        self.assertTrue(strict_equal(29.9, 29.9))
        self.assertEqual(json_value_type(True), "boolean")
        self.assertEqual(json_value_type(1), "number")

    def test_field_state_keeps_absent_null_empty_and_value_distinct(self) -> None:
        self.assertIs(path_value({}, "missing"), MISSING)
        self.assertEqual(field_state_for(None), "null")
        self.assertEqual(field_state_for(""), "empty")
        self.assertEqual(field_state_for(0), "value")

    def test_quoted_paths_address_literal_vendor_keys(self) -> None:
        value = {"query": {"ep.value": 29.9, "cd[value]": "gold"}}
        self.assertEqual(path_value(value, 'query["ep.value"]'), 29.9)
        self.assertEqual(path_value(value, 'query["cd[value]"]'), "gold")

    def test_wildcard_paths_expand_arrays_without_ambiguity(self) -> None:
        value = {"items": [{"id": "A"}, {"id": "B"}]}
        self.assertEqual(path_values(value, "items[].id"), ["A", "B"])
        self.assertIs(path_value(value, "items[].id"), MISSING)

    def test_ga4_newline_batch_and_repeated_keys_are_preserved(self) -> None:
        decoded = decode_requests(
            {
                "requests": [
                    {
                        "request_id": "R1",
                        "url": (
                            "https://www.google-analytics.com/g/collect?"
                            "v=2&tid=G-TEST&ep.item=alpha&ep.item=beta"
                        ),
                        "method": "POST",
                        "headers": {
                            "content-type": "text/plain",
                            "authorization": "Bearer secret",
                        },
                        "post_data": "en=view_item&_s=1\nen=add_to_cart&_s=2",
                    }
                ]
            }
        )
        request = decoded["requests"][0]
        self.assertEqual(request["query"]["ep.item"], ["alpha", "beta"])
        self.assertEqual(request["body"]["format"], "newline_batch")
        self.assertEqual(len(request["body"]["records"]), 2)
        self.assertNotIn("raw", request["body"])
        self.assertIn("authorization", request["excluded_header_names"])

    def test_raw_request_body_requires_named_quarantine(self) -> None:
        request = {"requests": [{"url": "https://example.test/collect", "post_data": "secret"}]}
        with self.assertRaisesRegex(ValueError, "quarantine"):
            decode_requests(request, retain_raw_body=True)
        value = decode_requests(request, retain_raw_body=True, quarantine=True)
        self.assertTrue(value["quarantine"]["must_not_be_attached_to_results"])

    def test_sensitive_scanner_recurses_into_encoded_query_values(self) -> None:
        findings = scan_sensitive_value(
            "https://example.test/?redirect=https%3A%2F%2Fother.test%2F%3Femail%3Da%2540b.test"
        )
        self.assertTrue(any(row["category"] == "email" for row in findings))
        self.assertTrue(all(row["value_fingerprint"] == "not-retained" for row in findings))

    def test_sensitive_vendor_aliases_and_hashes_are_classified(self) -> None:
        raw = scan_sensitive_value("https://example.test/?em=person%40example.com")
        hashed = scan_sensitive_value("https://example.test/?em=" + "a" * 64)
        self.assertTrue(any(row["category"] == "email" and row["status"] == "FAIL" for row in raw))
        self.assertTrue(any(row["category"] == "hashed_user_data" for row in hashed))

    def test_redaction_does_not_retain_raw_value_hash_or_length(self) -> None:
        safe, _ = redact_for_persistence({"external_id": "customer-123"})
        text = json.dumps(safe)
        self.assertNotIn("customer-123", text)
        self.assertNotIn(hashlib.sha256(b"customer-123").hexdigest()[:8], text)
        self.assertNotIn("length", text)

    def test_formula_safe_workbook_and_csv_text(self) -> None:
        workbook = Workbook()
        cell = workbook.active["A1"]
        set_safe_cell(cell, "=1+1")
        self.assertEqual(cell.value, "'=1+1")
        self.assertEqual(formula_safe_text("@SUM(A1:A2)"), "'@SUM(A1:A2)")

    def test_dynamic_regex_rejects_nested_repetition(self) -> None:
        with self.assertRaises(ValueError):
            compile_pattern("(a+)+$", label="test")

    def test_datalayer_classification_retains_business_technical_state_and_non_event(self) -> None:
        self.assertEqual(classify_datalayer_argument({"event": "view_item"}), "BUSINESS_EVENT")
        self.assertEqual(classify_datalayer_argument({"event": "gtm.js"}), "TECHNICAL_EVENT")
        self.assertEqual(classify_datalayer_argument({"ecommerce": None}), "STATE_UPDATE")
        self.assertEqual(classify_datalayer_argument("arguments-object"), "NON_EVENT")

    def test_ga4_handoff_preserves_exact_plan_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = {
                "events": [
                    {
                        "event_name": "quote_request",
                        "trigger": "successful quote",
                        "journey_ids": ["lead"],
                        "locations": [{"url_pattern": "https://example.test/quote"}],
                        "data_layer": {"push": {"event": "quote_request", "form_name": "quote"}},
                        "parameters": [
                            {
                                "name": "form_name",
                                "scope": "event",
                                "data_layer_path": "form_name",
                                "type": "string",
                                "allowed_values": ["quote"],
                            }
                        ],
                    }
                ]
            }
            expected = {"events": [{"event_name": "quote_request"}]}
            plan_path = root / "plan.json"
            expected_path = root / "expected.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            expected_path.write_text(json.dumps(expected), encoding="utf-8")

            def digest(path: Path) -> str:
                return hashlib.sha256(path.read_bytes()).hexdigest()

            handoff = {
                "handoff_version": "1.0.0",
                "skill": {"name": "ga4-tracking-plan"},
                "approval": {"state": "approved"},
                "plan": {
                    "canonical_sha256": digest(plan_path),
                    "target_sites": ["https://example.test"],
                },
                "artifacts": [
                    {
                        "role": "canonical_tracking_plan",
                        "path": "plan.json",
                        "sha256": digest(plan_path),
                    },
                    {
                        "role": "runtime_expected_events_contract",
                        "path": "expected.json",
                        "sha256": digest(expected_path),
                    },
                ],
            }
            (root / "handoff.json").write_text(json.dumps(handoff), encoding="utf-8")
            verified = verify_delivery(root)
            imported = interpreted_requirements(*verified)
            self.assertEqual(
                [row["source"]["plan_order"] for row in imported["requirements"]], [1, 2]
            )
            self.assertEqual(
                imported["requirements"][0]["expectation"]["event_name"], "quote_request"
            )

    def test_battle_hardened_browser_helpers_are_still_present(self) -> None:
        recorder = (SCRIPTS / "datalayer_recorder.js").read_text(encoding="utf-8")
        census = (SCRIPTS / "dom_interaction_census.js").read_text(encoding="utf-8")
        for marker in (
            "shared_reference",
            "circular_reference",
            "maxElapsedMs",
            "acknowledgeThrough",
            "captureSince",
            "push_replaced_unverified",
        ):
            self.assertIn(marker, recorder)
        for marker in ("shadowHostChain", "selectorUnique", "aria-labelledby"):
            self.assertIn(marker, census)


if __name__ == "__main__":
    unittest.main()
