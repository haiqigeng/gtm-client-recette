from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from build_recette_report import REQUIRED_SHEETS, build_workbook  # noqa: E402
from inspect_tracking_plan import inspect_xlsx  # noqa: E402
from recette_schema import ReportValidationError, event_rollup, validate  # noqa: E402


def fixture(name: str = "valid_full.json") -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def requirement(data: dict) -> dict:
    return data["requirements"][0]


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
        "approval_evidence_id": "EVD-ACTION-001",
        "override_method": "Session-scoped gtag consent update",
        "blocker_id": "BLK-CMP",
        "evidence_id": "EVD-CONSENT-001",
    }
    req["evidence_ids"].append("EVD-CONSENT-001")
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
            self.assertIsNotNone(
                workbook["Evidence Catalogue"].cell(row=2, column=4).hyperlink
            )
            workbook.close()

    def test_valid_scoped_run_does_not_imply_tag_layers(self) -> None:
        data = fixture("valid_scoped.json")
        self.assertEqual([], validate(data, strict=True))
        self.assertIsNone(requirement(data).get("tag"))

    def test_schema_v1_is_rejected_actionably(self) -> None:
        data = fixture()
        data["schema_version"] = 1
        self.assert_invalid(data, "re-normalized from source evidence")

    def test_missing_acceptance_source_is_rejected(self) -> None:
        data = fixture()
        data["run"]["tracking_plan_source"] = ""
        self.assert_invalid(data, "tracking_plan_source")

    def test_inventory_omission_is_rejected(self) -> None:
        data = fixture()
        data["run"]["requirement_inventory"] = []
        self.assert_invalid(data, "requirement_inventory")

    def test_placeholder_raw_payload_is_rejected(self) -> None:
        data = fixture()
        requirement(data)["raw_api_call"]["payload"]["ecommerce"]["value"] = "..."
        self.assert_invalid(data, "placeholder")

    def test_browser_interception_cannot_pass_as_full_api_call(self) -> None:
        data = fixture()
        requirement(data)["raw_api_call"]["capture_source"] = "browser_interception"
        self.assert_invalid(data, "requires exact Tag Assistant API Call")

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

    def test_expected_event_absence_with_settled_boundary_is_valid_failure(self) -> None:
        data = fixture()
        configure_absent_event(data)
        self.assertEqual([], validate(data, strict=True))
        self.assertEqual("FAIL", event_rollup(data)[0]["status"])

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

    def test_scoped_chronology_requires_anchor_evidence(self) -> None:
        data = fixture("valid_scoped.json")
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
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Events"
            sheet["B12"] = "add_to_cart"
            sheet["F12"] = 29.9
            workbook.save(path)
            result = inspect_xlsx(path, max_rows=0)
            cells = result["sheets"][0]["populated_rows"][0]["cells"]
            self.assertEqual(["B12", "F12"], [cell["cell"] for cell in cells])
            self.assertEqual("number", cells[1]["value_type"])

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
                "--first-event-after",
                "11",
                "--settled-final-event",
                "12",
                "--expected-seen",
                "true",
                "--preview-connected-after",
                "true",
            )
            state = json.loads(run("status", str(ledger)).stdout)
            self.assertEqual("SETTLED", state["actions"][0]["state"])
            self.assertTrue(state["actions"][0]["preview_connected_after"])


if __name__ == "__main__":
    unittest.main()
