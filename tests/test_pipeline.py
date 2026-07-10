from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_recette_report import (  # noqa: E402
    ReportValidationError,
    build_workbook,
    load_workbook,
    validate,
)


def valid_payload() -> dict:
    return {
        "run": {
            "site_url": "https://example.test/",
            "container_id": "GTM-TEST",
            "workspace": "Recette",
            "tracking_plan_source": "tracking-plan.xlsx",
        },
        "journeys": [],
        "checks": [
            {
                "check_id": "CHK-001",
                "check_type": "tag_firing",
                "expected": "fired",
                "actual": "not_fired",
                "status": "FAIL",
                "non_firing_reason": "Consent denied.",
                "reason_source": "preview",
                "evidence_ids": ["E-001"],
            }
        ],
        "events": [],
        "tags": [],
        "consent_checks": [],
        "unexpected": [],
        "comparisons": [
            {
                "comparison_id": "CMP-001",
                "journey_id": "J-001",
                "event_order": 12,
                "data_layer_event": "newsletter_subscribe",
                "data_layer_field": "newsletter_action",
                "tag_name": "GA4 - newsletter_subscribe",
                "tag_configuration_field": "event_name",
                "tracking_plan_value": "newsletter_subscribe",
                "data_layer_value": "newsletter_subscribe",
                "tag_configuration_value": "newsletter_subscribe",
                "resolved_tag_value": "newsletter_subscribe",
                "status": "PASS",
                "mismatch_or_reason": "",
                "evidence_ids": ["E-001"],
                "notes": "",
            }
        ],
        "evidence": [
            {
                "evidence_id": "E-001",
                "kind": "tag_detail",
                "source": "Tag Assistant",
                "path_or_url": "evidence/tag.png",
                "description": "Non-firing reason",
            }
        ],
    }


class PipelineTests(unittest.TestCase):
    def test_strict_report_has_expected_sheets(self) -> None:
        data = valid_payload()
        warnings = validate(data, strict=True)
        self.assertEqual([], warnings)
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "recette.xlsx"
            build_workbook(data, output, warnings)
            workbook = load_workbook(output, read_only=True)
            self.assertEqual(
                [
                    "Validation Matrix",
                    "Summary",
                    "Event Evidence",
                    "Evidence",
                    "Run Context",
                ],
                workbook.sheetnames,
            )
            self.assertEqual("FAIL", workbook["Summary"]["B3"].value)
            self.assertEqual("newsletter_subscribe", workbook["Validation Matrix"]["D2"].value)
            workbook.close()

    def test_strict_report_requires_wanted_tag_reason(self) -> None:
        data = valid_payload()
        data["checks"][0].pop("non_firing_reason")
        data["checks"][0].pop("reason_source")
        with self.assertRaises(ReportValidationError):
            validate(data, strict=True)

    def test_payload_is_json_serializable(self) -> None:
        json.dumps(valid_payload())

    def test_strict_report_requires_comparisons(self) -> None:
        data = valid_payload()
        data["comparisons"] = []
        with self.assertRaises(ReportValidationError):
            validate(data, strict=True)

    def test_strict_comparison_requires_three_value_sources(self) -> None:
        data = valid_payload()
        data["comparisons"][0].pop("tag_configuration_value")
        with self.assertRaises(ReportValidationError):
            validate(data, strict=True)


if __name__ == "__main__":
    unittest.main()
