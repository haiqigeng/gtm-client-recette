from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.drawing.image import Image as WorkbookImage
from PIL import Image as PillowImage

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from build_recette_report import REQUIRED_SHEETS, build_workbook  # noqa: E402
from client_side_rules import (  # noqa: E402
    evaluate_business_rule,
    path_value,
    scan_requirement_sensitive_data,
)
from decode_browser_requests import decode_requests  # noqa: E402
from diff_recette_runs import compare as compare_runs  # noqa: E402
from incremental_recette import apply_event, status_rows, validate_event  # noqa: E402
from inspect_tracking_plan import inspect_xlsx  # noqa: E402
from recette_schema import ReportValidationError, event_rollup, validate  # noqa: E402


def fixture(name: str = "valid_full.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def requirement(data: dict) -> dict:
    return data["requirements"][0]


def client_side_fixture() -> dict:
    data = fixture()
    extension = fixture("client_side_extension.json")
    data["run"].update(extension["run_patch"])
    req = requirement(data)
    patch = extension["requirement_patch"]
    req["container_id"] = patch["container_id"]
    req["browser_context_id"] = patch["browser_context_id"]
    req["scenario"] = patch["scenario"]
    req["expectation"].update(patch["expectation_patch"])
    req["raw_api_call"]["payload"].update(patch["raw_payload_patch"])
    req["resolved_data_layer"]["snapshot"] = deepcopy(req["raw_api_call"]["payload"])
    req["tag"].update(patch["tag_patch"])
    for field in (
        "destination_request",
        "trigger_evaluation",
        "tag_sequence",
        "consent",
        "business_rule_results",
        "sensitive_data_scan",
        "client_checks",
        "regression",
    ):
        req[field] = deepcopy(patch[field])
    req["verdict"].update(patch["verdict_patch"])
    new_ids = [item["evidence_id"] for item in extension["evidence"]]
    req["evidence_ids"].extend(new_ids)
    data["evidence"].extend(deepcopy(extension["evidence"]))
    return data


def configure_absent_event(data: dict, blocker_status: str | None = None) -> dict:
    req = requirement(data)
    req["event_observed"] = False
    req["occurrence_evidence"] = {
        "actual_count": 0,
        "event_indexes": [],
        "evidence_id": "EVD-ACTION-001",
    }
    req["raw_api_call"] = None
    req["resolved_data_layer"] = None
    req["gtm_variable"] = {
        "applicable": True,
        "name": "DLV - ecommerce.value",
    }
    req["tag"] = {
        "applicable": True,
        "relevance": "explains_non_firing",
        "name": "GA4 - Event - add_to_cart",
        "expected_firing": "fired_once",
        "actual_firing": "not_evaluated",
        "fire_count": 0,
        "configuration_field": "eventParameters.value",
        "configured_value": "{{DLV - ecommerce.value}}",
        "configuration_evidence_id": "EVD-TAG-CONFIG-011",
        "non_firing_reason": "Expected event did not occur.",
        "reason_source": "preview",
    }
    component = blocker_status or "BLOCKED"
    req["verdict"].update(
        {
            "event_occurrence": "FAIL" if blocker_status is None else blocker_status,
            "raw_payload": component,
            "resolved_data_layer": component,
            "gtm_variable": component,
            "tag_configuration": component,
            "tag_firing": component,
            "tag_parameter": component,
            "overall": "FAIL" if blocker_status is None else blocker_status,
            "failure_layer": "event_occurrence",
            "mismatch": "Expected event was not observed.",
        }
    )
    req["action_boundary"]["first_event_after"] = None
    return req


def add_blocker(
    data: dict,
    blocker_type: str,
    *,
    help_requested: bool,
    settled: bool = True,
) -> dict:
    req = configure_absent_event(data, blocker_status="BLOCKED")
    req["journey"]["execution_status"] = "BLOCKED"
    req["blocker_id"] = "BLK-001"
    req["action_boundary"]["stream_settled"] = settled
    if not settled:
        req["action_boundary"]["settlement_reason"] = (
            "preview_disconnected"
            if blocker_type == "PREVIEW_DISCONNECTED"
            else "timeout"
        )
    data["blockers"] = [
        {
            "blocker_id": "BLK-001",
            "type": blocker_type,
            "checkpoint": "Protected or external checkpoint",
            "description": "Synthetic blocker",
            "requirement_ids": ["REQ-001"],
            "analyst_intervention_required": blocker_type
            in {
                "GOOGLE_SIGN_IN",
                "MFA",
                "CAPTCHA",
                "EMAIL_VERIFICATION",
                "SMS_VERIFICATION",
                "MAGIC_LINK",
                "REAL_PAYMENT",
                "EXTERNAL_APPROVAL",
                "IRREVERSIBLE_ACTION",
            },
            "analyst_help_requested": help_requested,
            "analyst_response": "Unable to complete" if help_requested else "",
            "outcome": "Blocked",
            "status": "BLOCKED",
            "evidence_ids": ["EVD-ACTION-001"],
            "notes": "",
        }
    ]
    return req


def add_consent_override(data: dict, *, approved: bool, production: bool = False) -> dict:
    req = requirement(data)
    data["run"]["environment_class"] = "production" if production else "preprod"
    data["blockers"] = [
        {
            "blocker_id": "BLK-CMP",
            "type": "CMP_TEST_ENVIRONMENT",
            "checkpoint": "CMP initialization",
            "description": "CMP did not initialize in preprod.",
            "requirement_ids": ["REQ-001"],
            "analyst_intervention_required": False,
            "analyst_help_requested": False,
            "analyst_response": "",
            "outcome": "Downstream test state proposed",
            "status": "BLOCKED",
            "evidence_ids": ["EVD-ACTION-001"],
            "notes": "",
        }
    ]
    req["expectation"]["expected_consent_state"] = "analytics_storage=granted"
    req["consent"] = {
        "applicable": True,
        "scenario_id": "CONSENT-OVERRIDE",
        "scenario": "Approved test-environment override",
        "source": "session_override",
        "state_at_event": {"analytics_storage": "granted"},
        "before_state": {"analytics_storage": "denied"},
        "override_approved": approved,
        "approval_evidence_id": "EVD-CMP-APPROVAL-001",
        "override_method": "Session-scoped gtag consent update",
        "blocker_id": "BLK-CMP",
        "evidence_id": "EVD-CONSENT-001",
    }
    req["evidence_ids"].append("EVD-CONSENT-001")
    req["evidence_ids"].append("EVD-CMP-APPROVAL-001")
    data["evidence"].append(
        {
            "evidence_id": "EVD-CONSENT-001",
            "kind": "consent_state",
            "source": "Tag Assistant",
            "path_or_url": "evidence/consent-001.json",
            "captured_at": "2026-07-25T10:01:03+00:00",
            "description": "Event-level consent after the approved session override.",
        }
    )
    data["evidence"].append(
        {
            "evidence_id": "EVD-CMP-APPROVAL-001",
            "kind": "analyst_approval",
            "source": "Analyst supplied",
            "path_or_url": "evidence/cmp-approval-001.json",
            "captured_at": "2026-07-25T10:01:03+00:00",
            "description": "Explicit analyst decision for the proposed CMP override.",
        }
    )
    req["verdict"]["consent"] = "PASS"
    req["verdict"]["overall"] = "PASS"
    return req


class PipelineTests(unittest.TestCase):
    def assert_invalid(self, data: dict, message: str) -> None:
        with self.assertRaises(ReportValidationError) as context:
            validate(data, strict=True)
        self.assertIn(message, str(context.exception))

    def test_valid_full_schema_and_workbook(self) -> None:
        data = fixture()
        self.assertEqual([], validate(data, strict=True))
        data["evidence"][0]["path_or_url"] = "https://example.test/evidence/action"
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "recette.xlsx"
            build_workbook(data, output)
            workbook = load_workbook(output, read_only=False)
            self.assertEqual(REQUIRED_SHEETS, workbook.sheetnames)
            self.assertEqual("PASS", workbook["Client Summary"]["B3"].value)
            self.assertEqual(2, workbook["Requirement Matrix"].max_row)
            event_sheet = workbook["Event Evidence"]
            event_headers = {cell.value: cell.column for cell in event_sheet[1]}
            self.assertEqual(
                "ACT-001",
                event_sheet.cell(row=2, column=event_headers["action_id"]).value,
            )
            self.assertEqual(
                "completed",
                event_sheet.cell(
                    row=2,
                    column=event_headers["interaction_outcome"],
                ).value,
            )
            self.assertEqual(
                "expected_and_quiet",
                event_sheet.cell(
                    row=2,
                    column=event_headers["settlement_reason"],
                ).value,
            )
            evidence_sheet = workbook["Evidence Catalogue"]
            evidence_headers = {
                cell.value: cell.column for cell in evidence_sheet[1]
            }
            self.assertIsNotNone(
                evidence_sheet.cell(
                    row=2,
                    column=evidence_headers["path_or_url"],
                ).hyperlink
            )
            workbook.close()

    def test_applicability_does_not_imply_tag_layers(self) -> None:
        data = fixture("valid_limited_layers.json")
        self.assertEqual([], validate(data, strict=True))
        self.assertIsNone(requirement(data).get("tag"))

    def test_valid_full_client_side_extension_and_workbook(self) -> None:
        data = client_side_fixture()
        self.assertEqual([], validate(data, strict=True))
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "client-side-recette.xlsx"
            build_workbook(data, output)
            workbook = load_workbook(output, read_only=False)
            self.assertEqual(REQUIRED_SHEETS, workbook.sheetnames)
            self.assertEqual(2, workbook["Destination Evidence"].max_row)
            self.assertEqual(8, workbook["Business Rules"].max_row)
            self.assertEqual(15, workbook["Client Checks"].max_row)
            self.assertEqual(3, workbook["Container Context"].max_row)
            workbook.close()

    def test_declared_client_layer_cannot_be_omitted_from_run_metadata(self) -> None:
        data = client_side_fixture()
        data["run"]["included_layers"].remove(
            "destination_request_when_applicable"
        )
        self.assert_invalid(data, "included_layers omits declared client-side layers")

    def test_destination_parameter_mismatch_cannot_pass(self) -> None:
        data = client_side_fixture()
        requirement(data)["destination_request"]["field_value"] = 30
        self.assert_invalid(data, "PASS destination parameter contradicts")

    def test_destination_event_name_mismatch_cannot_pass(self) -> None:
        data = client_side_fixture()
        requirement(data)["destination_request"]["event_name"] = "Purchase"
        self.assert_invalid(data, "destination event_name differs from expectation")

    def test_destination_claim_must_match_browser_request(self) -> None:
        data = client_side_fixture()
        requirement(data)["destination_request"]["request_url"] = (
            "https://www.facebook.com/tr/"
            "?id=META-WRONG&ev=AddToCart&value=29.9"
        )
        self.assert_invalid(data, "decoded destination ID differs from browser request")

    def test_destination_value_must_match_browser_request(self) -> None:
        data = client_side_fixture()
        requirement(data)["destination_request"]["request_url"] = (
            "https://www.facebook.com/tr/"
            "?id=META-TEST-001&ev=AddToCart&value=999"
        )
        self.assert_invalid(
            data, "decoded destination parameter differs from browser request"
        )

    def test_literal_vendor_request_keys_are_addressable(self) -> None:
        self.assertEqual(
            ["29.9", "EUR"],
            [
                path_value(
                    {"query": {"cd[value]": "29.9", "ep.currency": "EUR"}},
                    'query["cd[value]"]',
                ),
                path_value(
                    {"query": {"cd[value]": "29.9", "ep.currency": "EUR"}},
                    'query["ep.currency"]',
                ),
            ],
        )
        data = client_side_fixture()
        req = requirement(data)
        req["expectation"]["destination_parameter_path"] = 'query["cd[value]"]'
        req["destination_request"]["parameter_path"] = 'query["cd[value]"]'
        req["destination_request"]["request_url"] = (
            "https://www.facebook.com/tr/"
            "?id=META-TEST-001&ev=AddToCart&cd%5Bvalue%5D=29.9"
        )
        self.assertEqual([], validate(data, strict=True))

    def test_destination_verdict_cannot_be_omitted(self) -> None:
        data = client_side_fixture()
        requirement(data)["verdict"].pop("destination_request")
        self.assert_invalid(
            data, "destination expectation requires destination_request verdict"
        )

    def test_vendor_helper_alone_cannot_prove_browser_send(self) -> None:
        data = client_side_fixture()
        requirement(data)["destination_request"]["capture_source"] = "vendor_helper"
        self.assert_invalid(data, "first-party browser-network evidence")

    def test_advanced_consent_v2_requires_all_four_signals(self) -> None:
        data = client_side_fixture()
        del requirement(data)["expectation"]["consent_contract"]["signals"][
            "ad_user_data"
        ]
        self.assert_invalid(data, "must declare all four consent signals")

    def test_conditional_pass_requires_condition_evidence(self) -> None:
        data = client_side_fixture()
        requirement(data)["scenario"]["condition_met"] = False
        self.assert_invalid(data, "conditional PASS requires evidence")

    def test_trigger_logic_false_pass_is_rejected(self) -> None:
        data = client_side_fixture()
        requirement(data)["trigger_evaluation"]["actual_result"] = "blocked"
        self.assert_invalid(data, "PASS trigger result differs")

    def test_trigger_condition_truth_is_recomputed(self) -> None:
        data = client_side_fixture()
        requirement(data)["trigger_evaluation"]["conditions"][0]["actual"] = "wrong"
        self.assert_invalid(data, "matched differs from its expected/actual values")

    def test_matched_blocking_exception_cannot_hide_behind_pass(self) -> None:
        data = client_side_fixture()
        requirement(data)["trigger_evaluation"]["blocking_exceptions"][0][
            "matched"
        ] = True
        self.assert_invalid(
            data, "trigger actual_result differs from condition/exception evidence"
        )

    def test_tag_sequence_false_pass_is_rejected(self) -> None:
        data = client_side_fixture()
        requirement(data)["tag_sequence"]["actual_order"] = [
            "Meta - AddToCart",
            "Media - Setup",
            "Media - Cleanup",
        ]
        self.assert_invalid(data, "PASS tag sequence contradicts")

    def test_extra_sequence_step_requires_explicit_allowance(self) -> None:
        data = client_side_fixture()
        requirement(data)["tag_sequence"]["actual_order"].append("Unexpected - Cleanup")
        self.assert_invalid(data, "PASS tag sequence contradicts")

    def test_cross_field_business_rule_false_pass_is_rejected(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["raw_api_call"]["payload"]["ecommerce"]["items"][0]["price"] = 10
        req["resolved_data_layer"]["snapshot"] = deepcopy(req["raw_api_call"]["payload"])
        self.assert_invalid(data, "business rule result BR-VALUE contradicts")

    def test_business_rule_verdict_cannot_be_omitted(self) -> None:
        data = client_side_fixture()
        requirement(data)["verdict"].pop("business_rule")
        self.assert_invalid(data, "declared business_rules require business_rule verdict")

    def test_business_rule_equality_is_type_strict(self) -> None:
        result = evaluate_business_rule(
            {
                "rule_id": "BR-TYPE-STRICT",
                "operator": "equals_path",
                "left_path": "left",
                "right_path": "right",
            },
            {"left": True, "right": 1},
        )
        self.assertEqual("FAIL", result["status"])

    def test_all_items_equal_rejects_non_object_items(self) -> None:
        result = evaluate_business_rule(
            {
                "rule_id": "BR-ITEMS",
                "operator": "all_items_equal",
                "items_path": "items",
                "item_field": "currency",
                "expected_path": "currency",
            },
            {"items": [{"currency": "EUR"}, "EUR"], "currency": "EUR"},
        )
        self.assertEqual("FAIL", result["status"])

    def test_zero_business_tolerance_has_no_relative_slack(self) -> None:
        result = evaluate_business_rule(
            {
                "rule_id": "BR-EXACT",
                "operator": "sum_product_equals",
                "target_path": "value",
                "items_path": "items",
                "price_field": "price",
                "quantity_field": "quantity",
                "tolerance": 0,
            },
            {
                "value": 1_000_000_000_001,
                "items": [{"price": 1_000_000_000_000, "quantity": 1}],
            },
        )
        self.assertEqual("FAIL", result["status"])

    def test_business_rule_output_redacts_sensitive_primitives(self) -> None:
        email = "synthetic.user@example.com"
        result = evaluate_business_rule(
            {
                "rule_id": "BR-EMAIL",
                "operator": "equals_path",
                "left_path": "left",
                "right_path": "right",
            },
            {"left": email, "right": email},
        )
        self.assertEqual("PASS", result["status"])
        self.assertNotIn(email, json.dumps(result))

    def test_business_rule_output_redacts_keyed_names_and_phones(self) -> None:
        for path, value, payload in (
            (
                "profile.phone",
                "+33 6 12 34 56 78",
                {
                    "profile": {
                        "phone": "+33 6 12 34 56 78",
                        "first_name": "Synthetic Alice",
                    }
                },
            ),
            (
                "profile.first_name",
                "Synthetic Alice",
                {
                    "profile": {
                        "phone": "+33 6 12 34 56 78",
                        "first_name": "Synthetic Alice",
                    }
                },
            ),
            ("left", "Synthetic Alice", {"left": "Synthetic Alice"}),
        ):
            with self.subTest(path=path):
                result = evaluate_business_rule(
                    {
                        "rule_id": "BR-SENSITIVE",
                        "operator": "equals_path",
                        "left_path": path,
                        "right_path": path,
                    },
                    payload,
                )
                self.assertEqual("PASS", result["status"])
                self.assertNotIn(value, json.dumps(result))

    def test_sensitive_data_false_pass_is_rejected_and_output_is_redacted(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["raw_api_call"]["payload"]["contact_email"] = "synthetic.user@example.com"
        req["resolved_data_layer"]["snapshot"] = deepcopy(req["raw_api_call"]["payload"])
        self.assert_invalid(data, "sensitive_data_scan differs from deterministic scan")
        findings = scan_requirement_sensitive_data(
            req, req["expectation"]["sensitive_data_policy"]
        )
        self.assertTrue(findings)
        self.assertNotIn("synthetic.user@example.com", json.dumps(findings))
        self.assertTrue(all("value_fingerprint" in item for item in findings))

    def test_sensitive_policy_cannot_disappear_from_active_scan_layer(self) -> None:
        data = client_side_fixture()
        requirement(data)["expectation"].pop("sensitive_data_policy")
        requirement(data).pop("sensitive_data_scan")
        requirement(data)["verdict"].pop("sensitive_data")
        self.assert_invalid(
            data, "sensitive_data_scan layer requires sensitive_data_policy"
        )

    def test_invalid_custom_sensitive_pattern_is_rejected(self) -> None:
        data = client_side_fixture()
        requirement(data)["expectation"]["sensitive_data_policy"][
            "custom_patterns"
        ] = [
            {
                "pattern_id": "CUSTOM-BAD",
                "pattern": "[",
                "category": "custom",
                "confidence": "confirmed",
            }
        ]
        self.assert_invalid(data, "has invalid regular expression")

    def test_destination_field_value_is_a_sensitive_scan_target(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["destination_request"]["field_value"] = "synthetic.user@example.com"
        findings = scan_requirement_sensitive_data(
            req, req["expectation"]["sensitive_data_policy"]
        )
        self.assertTrue(
            any(
                item["path"] == "destination_request.field_value"
                for item in findings
            )
        )

    def test_request_headers_are_sensitive_scan_targets(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["destination_request"]["request_headers"] = {
            "X-Test-Contact": "synthetic.user@example.com"
        }
        findings = scan_requirement_sensitive_data(
            req, req["expectation"]["sensitive_data_policy"]
        )
        self.assertTrue(
            any(
                item["path"].startswith("destination_request.request_headers")
                for item in findings
            )
        )

    def test_stored_redaction_cannot_retain_raw_sensitive_value(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        email = "synthetic.user@example.com"
        req["raw_api_call"]["payload"]["contact_email"] = email
        req["resolved_data_layer"]["snapshot"] = deepcopy(req["raw_api_call"]["payload"])
        findings = scan_requirement_sensitive_data(
            req, req["expectation"]["sensitive_data_policy"]
        )
        req["sensitive_data_scan"]["findings"] = findings
        req["sensitive_data_scan"]["status"] = "FAIL"
        req["verdict"]["sensitive_data"] = "FAIL"
        req["verdict"]["overall"] = "FAIL"
        req["sensitive_data_scan"]["findings"][0]["redacted_value"] = email
        self.assert_invalid(data, "sensitive_data_scan differs from deterministic scan")

    def test_sensitive_data_scan_includes_page_title(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["journey"]["page_title"] = "Account synthetic.user@example.com"
        findings = scan_requirement_sensitive_data(
            req, req["expectation"]["sensitive_data_policy"]
        )
        self.assertTrue(
            any(item["path"] == "journey.page_title" for item in findings)
        )

    def test_sensitive_data_cli_returns_redacted_failure(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["raw_api_call"]["payload"]["contact_email"] = "synthetic.user@example.com"
        req["resolved_data_layer"]["snapshot"] = deepcopy(req["raw_api_call"]["payload"])
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "recette.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "scan_sensitive_data.py"),
                    str(path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(1, result.returncode)
        self.assertNotIn("synthetic.user@example.com", result.stdout)
        self.assertEqual("FAIL", json.loads(result.stdout)["status"])

    def test_workbook_refuses_unquarantined_sensitive_evidence(self) -> None:
        data = client_side_fixture()
        req = requirement(data)
        req["raw_api_call"]["payload"]["contact_email"] = (
            "synthetic.user@example.com"
        )
        req["resolved_data_layer"]["snapshot"] = deepcopy(
            req["raw_api_call"]["payload"]
        )
        with tempfile.TemporaryDirectory() as tempdir:
            output = Path(tempdir) / "unsafe.xlsx"
            with self.assertRaises(ReportValidationError) as context:
                build_workbook(data, output)
            self.assertIn("unsafe sensitive content", str(context.exception))
            self.assertFalse(output.exists())

    def test_client_check_false_pass_is_rejected(self) -> None:
        data = client_side_fixture()
        requirement(data)["client_checks"][6]["actual"]["push_method_intact"] = False
        self.assert_invalid(data, "client check CHECK-DATALAYER status contradicts")

    def test_invalid_client_check_regex_cannot_pass(self) -> None:
        data = client_side_fixture()
        check = requirement(data)["client_checks"][0]
        check.update(
            {
                "comparison": "regex",
                "expected": "[",
                "actual": "history_push",
                "status": "PASS",
            }
        )
        self.assert_invalid(data, "client check CHECK-SPA status contradicts")

    def test_client_check_verdict_cannot_be_omitted(self) -> None:
        data = client_side_fixture()
        requirement(data)["verdict"].pop("client_checks")
        self.assert_invalid(data, "supplied client_checks require client_checks verdict")

    def test_tag_consent_check_is_recomputed(self) -> None:
        data = client_side_fixture()
        requirement(data)["consent"]["tag_consent_checks"][0]["actual"] = "denied"
        self.assert_invalid(data, "status differs from expected/actual values")

    def test_consent_verdict_cannot_be_omitted(self) -> None:
        data = client_side_fixture()
        requirement(data)["verdict"].pop("consent")
        self.assert_invalid(data, "consent_contract requires consent verdict")

    def test_server_container_is_explicitly_out_of_scope(self) -> None:
        data = client_side_fixture()
        data["run"]["containers"][1]["container_type"] = "server"
        self.assert_invalid(data, "server-side GTM is out of scope")

    def test_regression_classification_false_pass_is_rejected(self) -> None:
        data = client_side_fixture()
        requirement(data)["regression"]["change"] = "REGRESSED"
        self.assert_invalid(data, "regression change classification is inconsistent")

    def test_run_baseline_requires_requirement_regression_evidence(self) -> None:
        data = client_side_fixture()
        requirement(data).pop("regression")
        requirement(data)["verdict"].pop("regression")
        self.assert_invalid(
            data, "run regression_context requires requirement regression evidence"
        )

    def test_evidence_rows_require_provenance_metadata(self) -> None:
        data = client_side_fixture()
        data["evidence"][0].pop("source")
        self.assert_invalid(data, "missing provenance field 'source'")

    def test_evidence_source_must_match_evidence_kind(self) -> None:
        data = client_side_fixture()
        raw_evidence = next(
            row for row in data["evidence"] if row["evidence_id"] == "EVD-RAW-011"
        )
        raw_evidence["source"] = "Analyst supplied"
        self.assert_invalid(data, "source is incompatible with kind 'api_call'")

    def test_evidence_provenance_cannot_contain_sensitive_content(self) -> None:
        data = client_side_fixture()
        data["evidence"][0]["description"] = "Captured synthetic.user@example.com"
        self.assert_invalid(data, "provenance contains sensitive content")

    def test_nested_evidence_ids_are_bound_to_expected_kinds(self) -> None:
        evidence_ids = (
            "EVD-ACTION-001",
            "EVD-RAW-011",
            "EVD-DL-011",
            "EVD-VAR-011",
            "EVD-TAG-CONFIG-011",
            "EVD-TAG-RUNTIME-011",
            "EVD-SCENARIO-001",
            "EVD-TRIGGER-001",
            "EVD-SEQUENCE-001",
            "EVD-BUSINESS-001",
            "EVD-SENSITIVE-001",
            "EVD-CLIENT-CHECKS-001",
            "EVD-REGRESSION-001",
        )
        for evidence_id in evidence_ids:
            with self.subTest(evidence_id=evidence_id):
                data = client_side_fixture()
                evidence = next(
                    row
                    for row in data["evidence"]
                    if row["evidence_id"] == evidence_id
                )
                evidence["kind"] = "screenshot"
                self.assert_invalid(data, "evidence kind must be")

    def test_consent_override_approval_has_dedicated_evidence_kind(self) -> None:
        data = fixture()
        add_consent_override(data, approved=True)
        approval = next(
            row
            for row in data["evidence"]
            if row["evidence_id"] == "EVD-CMP-APPROVAL-001"
        )
        approval["kind"] = "screenshot"
        self.assert_invalid(data, "consent.approval: evidence kind must be")

    def test_blocked_retest_is_unverified_not_a_proven_regression(self) -> None:
        baseline = client_side_fixture()
        current = deepcopy(baseline)
        requirement(current)["verdict"]["overall"] = "BLOCKED"
        result = compare_runs(baseline, current)[0]
        self.assertEqual("UNVERIFIED", result["change"])
        self.assertFalse(result["regression"])

    def test_non_datalayer_client_source_is_supported_without_fabricated_push(self) -> None:
        data = fixture()
        req = requirement(data)
        data["run"]["included_layers"].append(
            "source_signal_when_no_data_layer_push"
        )
        req["expectation"]["source_mechanism"] = "direct_vendor_call"
        req["expectation"]["resolved_data_layer_applicable"] = False
        req["expectation"].pop("variable_name")
        req["expectation"].pop("tag_configuration_field")
        req["raw_api_call"] = None
        req["resolved_data_layer"] = None
        req["gtm_variable"] = None
        req["source_signal"] = {
            "mechanism": "direct_vendor_call",
            "event_name": "add_to_cart",
            "capture_source": "browser_console",
            "observed": True,
            "evidence_id": "EVD-SOURCE-001",
        }
        req["occurrence_evidence"]["evidence_id"] = "EVD-SOURCE-001"
        req["verdict"].update(
            {
                "source_signal": "PASS",
                "raw_payload": None,
                "resolved_data_layer": None,
                "gtm_variable": None,
                "tag_configuration": "PASS",
                "tag_parameter": None,
            }
        )
        req["evidence_ids"].append("EVD-SOURCE-001")
        data["evidence"].append(
            {
                "evidence_id": "EVD-SOURCE-001",
                "kind": "direct_vendor_call",
                "source": "Browser Console",
                "source_detail": "Observed through Playwright console instrumentation",
                "path_or_url": "evidence/source-001.json",
                "captured_at": "2026-07-25T10:01:03+00:00",
                "description": "Direct client-side vendor call with no dataLayer push.",
            }
        )
        self.assertEqual([], validate(data, strict=True))

    def test_multiple_vendors_and_destinations_use_atomic_requirements(self) -> None:
        data = client_side_fixture()
        second = deepcopy(requirement(data))
        second["requirement_id"] = "REQ-002"
        second["source"]["reference"] = "tracking-plan.xlsx / Events / row 12 / K12"
        second["source"]["plan_order"] = 2
        second["container_id"] = "GTM-TEST"
        second["expectation"]["vendor_family"] = "ga4"
        second["expectation"]["destination_id"] = "G-TEST000001"
        second["expectation"]["destination_event_name"] = "add_to_cart"
        second["expectation"]["destination_id_parameter_path"] = "query.tid"
        second["expectation"]["destination_event_parameter_path"] = "query.en"
        second["expectation"]["tag_name"] = "GA4 - Event - add_to_cart"
        second["expectation"]["expected_endpoint_pattern"] = (
            "^https://www\\.google-analytics\\.com/g/collect"
        )
        second["resolved_data_layer"]["snapshot"] = deepcopy(
            second["raw_api_call"]["payload"]
        )
        second["tag"].update(
            {
                "container_id": "GTM-TEST",
                "vendor_family": "ga4",
                "destination_id": "G-TEST000001",
                "event_name": "add_to_cart",
                "name": "GA4 - Event - add_to_cart",
            }
        )
        second["destination_request"].update(
            {
                "container_id": "GTM-TEST",
                "vendor_family": "ga4",
                "destination_id": "G-TEST000001",
                "event_name": "add_to_cart",
                "request_url": (
                    "https://www.google-analytics.com/g/collect"
                    "?tid=G-TEST000001&en=add_to_cart&value=29.9"
                ),
            }
        )
        data["requirements"].append(second)
        data["run"]["requirement_inventory"].append("REQ-002")
        self.assertEqual([], validate(data, strict=True))

    def test_business_rule_and_regression_clis(self) -> None:
        baseline = client_side_fixture()
        current = deepcopy(baseline)
        current["run"]["run_id"] = "RUN-CURRENT-001"
        requirement(current)["verdict"]["tag_firing"] = "FAIL"
        requirement(current)["verdict"]["overall"] = "FAIL"
        with tempfile.TemporaryDirectory() as tempdir:
            baseline_path = Path(tempdir) / "baseline.json"
            current_path = Path(tempdir) / "current.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            current_path.write_text(json.dumps(current), encoding="utf-8")
            rules = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "validate_business_rules.py"),
                    str(baseline_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            diff = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "diff_recette_runs.py"),
                    str(baseline_path),
                    str(current_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(0, rules.returncode)
        self.assertEqual("PASS", json.loads(rules.stdout)["status"])
        self.assertEqual(1, diff.returncode)
        self.assertEqual("REGRESSED", json.loads(diff.stdout)["results"][0]["change"])

    def test_schema_v1_is_rejected_actionably(self) -> None:
        data = fixture()
        data["schema_version"] = 1
        self.assert_invalid(data, "re-normalized from source evidence")

    def test_missing_acceptance_source_is_rejected(self) -> None:
        data = fixture()
        data["run"]["tracking_plan_source"] = ""
        self.assert_invalid(data, "tracking_plan_source")

    def test_run_type_modes_are_rejected(self) -> None:
        data = fixture()
        data["run"]["run_type"] = "FULL_TRACKING_PLAN_RECETTE"
        self.assert_invalid(data, "run_type is obsolete")

    def test_inventory_omission_is_rejected(self) -> None:
        data = fixture()
        data["run"]["requirement_inventory"] = []
        self.assert_invalid(data, "requirement_inventory")

    def test_placeholder_raw_payload_is_rejected(self) -> None:
        data = fixture()
        requirement(data)["raw_api_call"]["payload"]["ecommerce"]["value"] = "..."
        self.assert_invalid(data, "placeholder")

    def test_browser_interception_cannot_replace_preview_dependent_api_call(self) -> None:
        data = fixture()
        requirement(data)["raw_api_call"]["capture_source"] = "browser_interception"
        self.assert_invalid(data, "Preview-dependent evidence requires exact Tag Assistant")

    def test_fixed_value_mismatch_cannot_hide_behind_pass(self) -> None:
        data = fixture()
        requirement(data)["raw_api_call"]["field_value"] = 30
        requirement(data)["raw_api_call"]["payload"]["ecommerce"]["value"] = 30
        self.assert_invalid(data, "PASS raw_payload contradicts")

    def test_raw_absent_and_stale_resolved_value_remain_separate(self) -> None:
        data = fixture()
        req = requirement(data)
        raw = req["raw_api_call"]
        raw["payload"]["ecommerce"] = {}
        raw["field_state"] = "absent"
        raw["field_type"] = "absent"
        raw.pop("field_value")
        req["verdict"]["raw_payload"] = "FAIL"
        req["verdict"]["resolved_data_layer"] = "FAIL"
        req["verdict"]["overall"] = "FAIL"
        req["verdict"]["failure_layer"] = "raw_payload"
        req["verdict"]["mismatch"] = "Raw field absent; resolved state retained 29.9."
        self.assertEqual([], validate(data, strict=True))

    def test_tag_firing_and_undefined_parameter_have_separate_verdicts(self) -> None:
        data = fixture()
        req = requirement(data)
        tag = req["tag"]
        tag["runtime_state"] = "undefined"
        tag["runtime_type"] = "undefined"
        tag.pop("runtime_value")
        req["verdict"]["tag_firing"] = "PASS"
        req["verdict"]["tag_parameter"] = "FAIL"
        req["verdict"]["overall"] = "FAIL"
        req["verdict"]["failure_layer"] = "tag_parameter"
        req["verdict"]["mismatch"] = "Runtime parameter was undefined."
        self.assertEqual([], validate(data, strict=True))

    def test_wrong_runtime_parameter_cannot_pass(self) -> None:
        data = fixture()
        tag = requirement(data)["tag"]
        tag["runtime_value"] = "29.9"
        tag["runtime_type"] = "string"
        self.assert_invalid(data, "PASS tag parameter differs")

    def test_wrong_tag_configuration_cannot_pass(self) -> None:
        data = fixture()
        requirement(data)["tag"]["configured_value"] = "{{Wrong Variable}}"
        self.assert_invalid(data, "PASS tag configuration differs")

    def test_correct_data_layer_cannot_mask_configuration_or_runtime_failures(
        self,
    ) -> None:
        data = fixture()
        req = requirement(data)
        req["tag"]["configured_value"] = "{{Wrong Variable}}"
        req["tag"]["runtime_value"] = "29.9"
        req["tag"]["runtime_type"] = "string"
        req["verdict"].update(
            {
                "tag_configuration": "FAIL",
                "tag_parameter": "FAIL",
                "overall": "FAIL",
                "failure_layer": "tag_configuration",
                "mismatch": "Configured source and runtime type differ from plan.",
            }
        )
        self.assertEqual([], validate(data, strict=True))
        req["verdict"]["overall"] = "PASS"
        self.assert_invalid(data, "does not equal worst applicable component")

    def test_expected_tag_configuration_cannot_be_silently_omitted(self) -> None:
        data = fixture()
        requirement(data)["verdict"].pop("tag_configuration")
        self.assert_invalid(data, "requires a configuration verdict")

    def test_required_base_layer_verdicts_cannot_be_omitted(self) -> None:
        cases = (
            ("raw_payload", "required raw API-call layer"),
            ("resolved_data_layer", "required resolved Data Layer"),
            ("gtm_variable", "expected GTM variable requires"),
            ("tag_configuration", "requires a configuration verdict"),
        )
        for verdict_field, expected_error in cases:
            with self.subTest(verdict_field=verdict_field):
                data = fixture()
                requirement(data)["verdict"].pop(verdict_field)
                self.assert_invalid(data, expected_error)

    def test_wrong_gtm_variable_mapping_cannot_pass(self) -> None:
        data = fixture()
        variable = requirement(data)["gtm_variable"]
        variable["field_value"] = 30
        self.assert_invalid(data, "PASS GTM variable differs")

    def test_wanted_nonfired_tag_requires_reason(self) -> None:
        data = fixture()
        req = requirement(data)
        req["tag"]["actual_firing"] = "not_fired"
        req["tag"]["fire_count"] = 0
        req["verdict"]["tag_firing"] = "FAIL"
        req["verdict"]["tag_parameter"] = "BLOCKED"
        req["verdict"]["overall"] = "FAIL"
        self.assert_invalid(data, "lacks non_firing_reason")

    def test_action_boundary_timestamp_and_cursor_order_are_strict(self) -> None:
        data = fixture()
        requirement(data)["action_boundary"]["action_timestamp"] = "not-a-time"
        self.assert_invalid(data, "action_timestamp must be ISO 8601 with timezone")

        data = fixture()
        requirement(data)["action_boundary"]["first_event_after"] = 9
        self.assert_invalid(data, "first_event_after must follow last_event_before")

        data = fixture()
        requirement(data)["occurrence_evidence"]["event_indexes"] = [13]
        self.assert_invalid(data, "occurrence event index exceeds settled_final_event")

    def test_completed_interaction_requires_independent_completion_signal(self) -> None:
        data = fixture()
        requirement(data)["action_boundary"].pop("completion_signal")
        self.assert_invalid(
            data,
            "completed interaction requires an independent completion_signal",
        )

    def test_failed_interaction_cannot_prove_expected_event_absence(self) -> None:
        data = fixture()
        req = configure_absent_event(data)
        req["action_boundary"]["interaction_outcome"] = "failed"
        req["action_boundary"]["completion_signal"] = "Overlay intercepted the click"
        req["action_boundary"]["settlement_reason"] = "interaction_failed"
        self.assert_invalid(
            data,
            "failed or uncertain interaction cannot prove expected-event absence",
        )

    def test_reviewed_attempt_still_requires_action_boundary(self) -> None:
        data = fixture()
        req = requirement(data)
        req["journey"]["execution_status"] = "REVIEW"
        req.pop("action_boundary")
        self.assert_invalid(data, "missing action_boundary")

    def test_journey_action_value_contract_is_required(self) -> None:
        data = fixture()
        requirement(data)["journey"].pop("action_value_source")
        self.assert_invalid(data, "journey missing 'action_value_source'")

    def test_client_container_inventory_is_required(self) -> None:
        data = fixture()
        data["run"].pop("containers")
        self.assert_invalid(data, "non-empty client-side web-container array")

    def test_expected_event_absence_with_settled_boundary_is_valid_failure(self) -> None:
        data = fixture()
        configure_absent_event(data)
        self.assertEqual([], validate(data, strict=True))
        self.assertEqual("FAIL", event_rollup(data)[0]["status"])

    def test_duplicate_push_cannot_pass_an_expected_once_rule(self) -> None:
        data = fixture()
        occurrence = requirement(data)["occurrence_evidence"]
        occurrence["actual_count"] = 2
        occurrence["event_indexes"] = [11, 12]
        self.assert_invalid(
            data,
            "PASS event occurrence contradicts observed chronology/count",
        )

    def test_absent_event_requires_applicable_consent_to_be_blocked(self) -> None:
        data = client_side_fixture()
        req = configure_absent_event(data)
        for component in (
            "destination_request",
            "destination_parameter",
            "trigger_logic",
            "tag_sequence",
            "business_rule",
        ):
            req["verdict"][component] = "BLOCKED"
        req["verdict"]["consent"] = "PASS"
        self.assert_invalid(
            data,
            "absent expected event requires downstream consent=BLOCKED",
        )

    def test_preview_disconnect_is_blocked_not_implementation_fail(self) -> None:
        data = fixture()
        req = add_blocker(
            data,
            "PREVIEW_DISCONNECTED",
            help_requested=False,
            settled=False,
        )
        req["action_boundary"]["preview_connected_before"] = False
        req["action_boundary"]["target_ready_before"] = False
        self.assertEqual([], validate(data, strict=True))

    def test_protected_blocker_requires_analyst_help_request(self) -> None:
        data = fixture()
        add_blocker(data, "MFA", help_requested=False)
        self.assert_invalid(data, "analyst help must be requested")

    def test_protected_blocker_with_handoff_is_valid(self) -> None:
        data = fixture()
        add_blocker(data, "EMAIL_VERIFICATION", help_requested=True)
        self.assertEqual([], validate(data, strict=True))

    def test_http_403_is_blocked_not_not_tested(self) -> None:
        data = fixture()
        add_blocker(data, "HTTP_403", help_requested=False)
        self.assertEqual([], validate(data, strict=True))

    def test_not_tested_cannot_hide_attempted_blocker(self) -> None:
        data = fixture()
        req = add_blocker(data, "HTTP_403", help_requested=False)
        for key in (
            "event_occurrence",
            "raw_payload",
            "resolved_data_layer",
            "gtm_variable",
            "tag_firing",
            "tag_parameter",
        ):
            req["verdict"][key] = "NOT_TESTED"
        req["verdict"]["overall"] = "NOT_TESTED"
        self.assert_invalid(data, "only valid for confirmed OUT_OF_SCOPE")

    def test_limited_layer_chronology_requires_anchor_evidence(self) -> None:
        data = fixture("valid_limited_layers.json")
        requirement(data)["occurrence_evidence"].pop("anchor_event_index")
        self.assert_invalid(data, "requires anchor_event_index")

    def test_unrelated_tag_matrix_row_is_rejected(self) -> None:
        data = fixture()
        requirement(data)["tag"]["relevance"] = "unrelated"
        self.assert_invalid(data, "tag relevance")

    def test_unapproved_cmp_override_is_rejected(self) -> None:
        data = fixture()
        add_consent_override(data, approved=False)
        self.assert_invalid(data, "lacks explicit analyst approval")

    def test_approved_nonproduction_cmp_override_is_valid(self) -> None:
        data = fixture()
        add_consent_override(data, approved=True)
        self.assertEqual([], validate(data, strict=True))

    def test_production_cmp_override_is_rejected(self) -> None:
        data = fixture()
        add_consent_override(data, approved=True, production=True)
        self.assert_invalid(data, "forbidden in production")

    def test_duplicate_evidence_id_is_rejected(self) -> None:
        data = fixture()
        data["evidence"][1]["evidence_id"] = data["evidence"][0]["evidence_id"]
        self.assert_invalid(data, "duplicate IDs")

    def test_tracking_plan_inspector_preserves_coordinates(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "plan.xlsx"
            assets = Path(tempdir) / "plan-assets"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Events"
            sheet["B12"] = "add_to_cart"
            sheet["B12"].hyperlink = "https://shop.example.test/product"
            sheet["B12"].comment = Comment("Open the product card.", "Analyst")
            sheet["F12"] = 29.9
            sheet.merge_cells("H2:I3")
            image_path = Path(tempdir) / "journey.png"
            PillowImage.new("RGB", (4, 4), color="white").save(image_path)
            with PillowImage.open(image_path) as image_source:
                plan_image = WorkbookImage(image_source)
                plan_image.anchor = "J4"
                sheet.add_image(plan_image)
                workbook.save(path)
            result = inspect_xlsx(path, max_rows=0, assets_dir=assets)
            cells = result["sheets"][0]["populated_rows"][0]["cells"]
            self.assertEqual(["B12", "F12"], [cell["cell"] for cell in cells])
            self.assertEqual("number", cells[1]["value_type"])
            self.assertEqual(
                "https://shop.example.test/product",
                cells[0]["hyperlink"]["target"],
            )
            self.assertEqual("Open the product card.", cells[0]["comment"]["text"])
            self.assertEqual(["H2:I3"], result["sheets"][0]["merged_ranges"])
            image = result["sheets"][0]["images"][0]
            self.assertEqual("J4", image["anchor"]["from_cell"])
            self.assertTrue(Path(image["extracted_file"]).is_file())

    def test_browser_request_decoder_preserves_repeated_and_batched_values(self) -> None:
        result = decode_requests(
            [
                {
                    "request_id": "NET-1",
                    "action_id": "ACT-1",
                    "url": (
                        "https://collect.example.test/g/collect"
                        "?id=G-TEST&ep.item=alpha&ep.item=beta"
                    ),
                    "method": "POST",
                    "headers": {
                        "Content-Type": "text/plain",
                        "Authorization": "Bearer secret",
                    },
                    "post_data": "en=one&value=1\nen=two&value=2",
                }
            ]
        )
        request = result["requests"][0]
        self.assertEqual(["alpha", "beta"], request["query"]["ep.item"])
        self.assertEqual("newline_batch", request["body"]["format"])
        self.assertEqual(2, len(request["body"]["records"]))
        self.assertNotIn("raw", request["body"])
        self.assertIn("authorization", request["excluded_header_names"])

    def test_incremental_event_validation_and_status(self) -> None:
        data = fixture()
        result = validate_event(data, "EVG-001")
        self.assertEqual("PASS", result["status"])
        self.assertEqual("PASS", status_rows(data)[0]["status"])

    def test_incremental_event_patch_preserves_layer_coherence(self) -> None:
        data = fixture()
        patch = {
            "event_group_id": "EVG-001",
            "requirements": deepcopy(data["requirements"]),
            "evidence": [],
        }
        updated, event_group_id = apply_event(data, patch)
        self.assertEqual("EVG-001", event_group_id)
        self.assertEqual("PASS", validate_event(updated, event_group_id)["status"])


    def test_synthetic_profile_uses_reserved_example_domain(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "generate_synthetic_profile.py"),
                "--seed",
                "RUN-001",
                "--locale",
                "fr-FR",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        profile = json.loads(result.stdout)
        self.assertTrue(profile["synthetic"])
        self.assertTrue(profile["email"].endswith("@example.com"))
        self.assertNotIn("password", profile)

    def test_coverage_initializer_preserves_plan_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            input_path = Path(tempdir) / "requirements.json"
            output_path = Path(tempdir) / "ledger.json"
            source = fixture()["requirements"]
            input_path.write_text(
                json.dumps({"requirements": source}),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "init_coverage_ledger.py"),
                    str(input_path),
                    str(output_path),
                    "--run-id",
                    "RUN-LEDGER",
                    "--title",
                    "Ledger test",
                    "--site-url",
                    "https://shop.example.test/",
                    "--environment",
                    "Preprod",
                    "--environment-class",
                    "preprod",
                    "--container-id",
                    "GTM-TEST",
                    "--workspace",
                    "Recette",
                    "--tracking-plan-source",
                    "tracking-plan.xlsx",
                    "--acceptance-scope",
                    "Full plan",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            ledger = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(["REQ-001"], ledger["run"]["requirement_inventory"])
            self.assertEqual("EVG-001", ledger["run"]["event_inventory"][0]["event_group_id"])
            self.assertEqual(
                "PENDING",
                ledger["requirements"][0]["journey"]["execution_status"],
            )

    def test_preview_session_ledger_supports_checkpointed_action(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            ledger = Path(tempdir) / "session.json"
            script = str(SCRIPTS / "preview_session_ledger.py")

            def run(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, script, *args],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            run(
                "init",
                str(ledger),
                "--profile-path",
                str(Path(tempdir) / "profile"),
                "--approved-origin",
                "https://shop.example.test",
            )
            run(
                "register-surface",
                str(ledger),
                "--role",
                "gtm_workspace",
                "--url",
                "https://tagmanager.google.com/",
                "--title",
                "GTM",
            )
            run(
                "register-surface",
                str(ledger),
                "--role",
                "tag_assistant",
                "--url",
                "https://tagassistant.google.com/",
                "--title",
                "Tag Assistant",
                "--connected",
                "true",
            )
            run(
                "register-surface",
                str(ledger),
                "--role",
                "website",
                "--url",
                "https://shop.example.test/product",
                "--title",
                "Product",
            )
            run(
                "begin-action",
                str(ledger),
                "--action-id",
                "ACT-001",
                "--requirement-id",
                "REQ-001",
                "--url",
                "https://shop.example.test/product",
                "--element",
                "Add to cart",
                "--action",
                "click",
                "--last-event-before",
                "10",
                "--consent-state",
                "analytics_storage=granted",
            )
            run(
                "settle-action",
                str(ledger),
                "--action-id",
                "ACT-001",
                "--settled-final-event",
                "10",
                "--expected-seen",
                "false",
                "--preview-connected-after",
                "true",
                "--interaction-outcome",
                "failed",
                "--completion-signal",
                "Overlay intercepted the click",
                "--stream-settled",
                "true",
                "--settlement-reason",
                "interaction_failed",
            )
            run(
                "begin-action",
                str(ledger),
                "--action-id",
                "ACT-002",
                "--retry-of-action-id",
                "ACT-001",
                "--requirement-id",
                "REQ-001",
                "--url",
                "https://shop.example.test/product",
                "--element",
                "Add to cart",
                "--action",
                "click",
                "--last-event-before",
                "10",
                "--consent-state",
                "analytics_storage=granted",
                "--quiet-window-ms",
                "3000",
                "--timeout-ms",
                "20000",
            )
            run(
                "settle-action",
                str(ledger),
                "--action-id",
                "ACT-002",
                "--first-event-after",
                "11",
                "--settled-final-event",
                "12",
                "--expected-seen",
                "true",
                "--preview-connected-after",
                "true",
                "--interaction-outcome",
                "completed",
                "--completion-signal",
                "Basket count changed from 0 to 1",
                "--stream-settled",
                "true",
                "--settlement-reason",
                "expected_and_quiet",
            )
            state = json.loads(run("status", str(ledger)).stdout)
            self.assertEqual("SETTLED", state["actions"][0]["state"])
            self.assertEqual("failed", state["actions"][0]["interaction_outcome"])
            self.assertEqual("ACT-001", state["actions"][1]["retry_of_action_id"])
            self.assertEqual("completed", state["actions"][1]["interaction_outcome"])
            self.assertEqual(
                "Basket count changed from 0 to 1",
                state["actions"][1]["completion_signal"],
            )
            self.assertTrue(state["actions"][1]["preview_connected_after"])
            self.assertTrue(state["actions"][1]["stream_settled"])
            run(
                "begin-action",
                str(ledger),
                "--action-id",
                "ACT-003",
                "--retry-of-action-id",
                "ACT-002",
                "--requirement-id",
                "REQ-001",
                "--url",
                "https://shop.example.test/product",
                "--element",
                "Add to cart",
                "--action",
                "click",
                "--last-event-before",
                "12",
                "--consent-state",
                "analytics_storage=granted",
            )
            invalid = subprocess.run(
                [
                    sys.executable,
                    script,
                    "settle-action",
                    str(ledger),
                    "--action-id",
                    "ACT-003",
                    "--settled-final-event",
                    "12",
                    "--expected-seen",
                    "false",
                    "--preview-connected-after",
                    "true",
                    "--interaction-outcome",
                    "completed",
                    "--stream-settled",
                    "true",
                    "--settlement-reason",
                    "quiet_without_expected",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(0, invalid.returncode)
            self.assertIn("requires an independent --completion-signal", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
