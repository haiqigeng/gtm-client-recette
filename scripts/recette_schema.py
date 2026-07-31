#!/usr/bin/env python3
"""Schema-v2 validation and shared semantics for GTM Preview recette results."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from acceptance_contract import (
    VALID_STATUSES,
    expects_absence,
    occurrence_rule,
    status_of,
    worst_status,
)
from client_side_rules import (
    BUSINESS_RULE_OPERATORS,
    DEFAULT_FORBIDDEN_CATEGORIES,
    FORMATS,
    MISSING,
    SENSITIVE_CATEGORIES,
    evaluate_report_business_rules,
    format_matches,
    path_value,
    requirement_sensitive_targets,
    scan_requirement_sensitive_data,
    scan_sensitive_value,
    valid_path,
)
from evidence_contract import (
    ACTION_BOUND_EVIDENCE_KINDS,
    ANALYST_CAPTURE_KINDS,
    CAPTURE_MODES,
    CONTAINER_BOUND_EVIDENCE_KINDS,
    DETERMINISTIC_CAPTURE_KINDS,
    DIRECT_CAPTURE_KINDS,
    EVENT_INDEX_EVIDENCE_KINDS,
)
from layer_contract import (
    CANONICAL_LAYERS,
    TAG_DELIVERY_TYPES,
    applicable_layers,
    is_browser_sending_tag,
)

SCHEMA_VERSION = 2
MATCH_RULES = {
    "equals",
    "absent",
    "present",
    "not_empty",
    "type",
    "regex",
    "one_of",
    "contains",
    "changes",
    "stable",
    "documented_transform",
    "range",
    "format",
    "anti_pattern",
    "vendor_equivalent",
    "business_rule",
}
OCCURRENCE_RULES = {
    "once",
    "at_least_once",
    "absent",
    "before_event",
    "after_event",
    "conditional",
    "non_deterministic",
}
FIELD_STATES = {
    "present",
    "absent",
    "undefined",
    "null",
    "empty_string",
    "empty_array",
    "empty_object",
}
VALUE_TYPES = {"string", "number", "boolean", "array", "object", "null", "undefined", "absent"}
EXECUTION_STATUSES = {"PENDING", "EXECUTED", "BLOCKED", "REVIEW", "NOT_TESTED"}
ACTION_VALUE_SOURCES = {
    "not_applicable",
    "synthetic",
    "analyst_supplied_non_sensitive",
    "protected_analyst_entry",
    "site_default",
}
INTERACTION_OUTCOMES = {"completed", "failed", "uncertain"}
SETTLEMENT_REASONS = {
    "expected_and_quiet",
    "quiet_without_expected",
    "timeout",
    "interaction_failed",
    "preview_disconnected",
}
SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE"}
RAW_SOURCES = {"tag_assistant_api_call", "browser_interception", "not_observed"}
CONSENT_SOURCES = {"natural_cmp", "session_override", "not_in_scope"}
SOURCE_MECHANISMS = {
    "data_layer_push",
    "gtm_native_event",
    "gtm_auto_event",
    "dom_event",
    "direct_vendor_call",
    "custom_html",
    "ga4_enhanced_measurement",
}
SOURCE_CAPTURE_SOURCES = {
    "tag_assistant",
    "browser_interception",
    "browser_console",
    "browser_network",
}
VENDOR_FAMILIES = {
    "ga4",
    "google_ads",
    "floodlight",
    "meta",
    "linkedin",
    "tiktok",
    "pinterest",
    "microsoft_ads",
    "x_ads",
    "custom",
}
DESTINATION_CAPTURE_SOURCES = {
    "browser_network",
    "tag_assistant",
    "browser_console",
    "vendor_helper",
}
REQUEST_BEHAVIOURS = {"sent", "not_observed", "blocked", "cookieless", "full"}
EXPECTED_REQUEST_BEHAVIOURS = {
    "sent",
    "sent_once",
    "absent",
    "blocked",
    "cookieless",
    "full",
}
TRIGGER_MODES = {"ALL", "ANY", "TRIGGER_GROUP"}
TRIGGER_RESULTS = {"matched", "not_matched", "blocked"}
SCENARIO_KINDS = {
    "deterministic",
    "conditional",
    "ab_variant",
    "error_path",
    "personalized",
    "responsive",
}
CONSENT_SIGNALS = {
    "ad_storage",
    "analytics_storage",
    "ad_user_data",
    "ad_personalization",
}
CONSENT_VALUES = {"granted", "denied"}
CONSENT_MODES = {"basic", "advanced_v2", "platform_specific"}
TRANSPORT_MODES = {"full", "cookieless", "blocked"}
CLIENT_CHECK_CATEGORIES = {
    "spa_navigation_source",
    "auto_event_source",
    "responsive_context",
    "cross_domain_linker",
    "cookie_domain",
    "iframe_tracking",
    "data_layer_integrity",
    "platform_convention",
    "debug_mode",
    "debugview",
    "client_limit",
    "custom_javascript",
    "container_conflict",
    "tag_dependency",
}
CLIENT_CHECK_COMPARISONS = {
    "equals",
    "contains",
    "present",
    "absent",
    "regex",
    "ordered",
    "maximum",
    "warning_only",
}
EVIDENCE_KIND_SOURCES = {
    "action_boundary": {"Playwright"},
    "api_call": {"Tag Assistant"},
    "resolved_data_layer": {"Tag Assistant"},
    "gtm_variable": {"Tag Assistant"},
    "tag_configuration": {"Tag Assistant", "GTM read-only"},
    "tag_runtime": {"Tag Assistant"},
    "browser_interception": {"Playwright"},
    "browser_network_request": {"Browser Network"},
    "browser_console": {"Browser Console"},
    "console_error": {"Browser Console"},
    "scenario_branch": {"Playwright", "Analyst supplied"},
    "vendor_helper": {"Vendor Helper"},
    "trigger_evaluation": {"Tag Assistant"},
    "tag_sequence": {"Tag Assistant"},
    "tag_assistant_consent": {"Tag Assistant"},
    "consent_state": {"Tag Assistant", "Playwright"},
    "business_rule_evaluation": {"Deterministic Validator"},
    "sensitive_data_scan": {"Deterministic Validator"},
    "client_side_checks": {
        "Playwright",
        "Tag Assistant",
        "Browser Network",
        "Browser Console",
    },
    "previous_run_comparison": {"Deterministic Validator"},
    "analyst_approval": {"Analyst supplied"},
    "screenshot": {"Playwright", "Analyst supplied"},
    "navigation": {"Playwright"},
    "source_signal": {
        "Playwright",
        "Tag Assistant",
        "Browser Network",
        "Browser Console",
    },
    "gtm_native_event": {"Tag Assistant"},
    "gtm_auto_event": {"Tag Assistant"},
    "dom_event": {"Playwright"},
    "direct_vendor_call": {"Browser Console", "Browser Network", "Playwright"},
    "custom_html": {"Tag Assistant", "Browser Console"},
    "ga4_enhanced_measurement": {"Tag Assistant", "Browser Network"},
}
CONTAINER_ROLES = {"primary", "analytics", "marketing", "shared"}
CONTAINER_TYPES = {"web", "client_side"}
TAG_RELEVANCE = {
    "expected_fire",
    "expected_block",
    "unexpected_relevant",
    "explains_non_firing",
}
REASON_SOURCES = {"preview", "console", "consent", "inferred", "not_established"}
PROTECTED_BLOCKERS = {
    "GOOGLE_SIGN_IN",
    "MFA",
    "CAPTCHA",
    "EMAIL_VERIFICATION",
    "SMS_VERIFICATION",
    "MAGIC_LINK",
    "REAL_PAYMENT",
    "EXTERNAL_APPROVAL",
    "IRREVERSIBLE_ACTION",
}
BASE_LAYERS = {
    "raw_api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "consent_when_applicable",
}
CLIENT_SIDE_OPTIONAL_LAYERS = set(CANONICAL_LAYERS) - BASE_LAYERS
PLACEHOLDER_VALUES = {"...", "…", "<omitted>", "[omitted]", "<placeholder>", "[placeholder]"}


class ReportValidationError(ValueError):
    """Raised when normalized recette data fails semantic validation."""


def as_rows(value: Any, key: str) -> list[dict[str, Any]]:
    """Return an object-list collection or raise a useful validation error."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ReportValidationError(f"'{key}' must be an array.")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ReportValidationError(f"'{key}' row {index} must be an object.")
        rows.append(item)
    return rows


def evidence_ids(value: Any) -> list[str]:
    """Normalize a scalar or list evidence reference."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def js_value_type(value: Any) -> str:
    """Return the JSON-compatible JavaScript type used by the schema."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without treating booleans as numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    left_number = isinstance(left, (int, float)) and not isinstance(left, bool)
    right_number = isinstance(right, (int, float)) and not isinstance(right, bool)
    if left_number or right_number:
        return left_number and right_number and left == right
    return type(left) is type(right) and left == right


def field_state_for(value: Any) -> str:
    """Infer the explicit field state for a represented JSON value."""
    if value is None:
        return "null"
    if value == "":
        return "empty_string"
    if value == []:
        return "empty_array"
    if value == {}:
        return "empty_object"
    return "present"


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nested_ids(requirement: dict[str, Any]) -> set[str]:
    ids: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence_ids":
                    ids.update(evidence_ids(item))
                elif key.endswith("evidence_id") and _is_nonempty_string(item):
                    ids.add(item.strip())
                elif key.endswith("evidence_ids"):
                    ids.update(evidence_ids(item))
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for section_name in (
        "occurrence_evidence",
        "action_boundary",
        "raw_api_call",
        "source_signal",
        "resolved_data_layer",
        "gtm_variable",
        "tag",
        "destination_request",
        "trigger_evaluation",
        "tag_sequence",
        "consent",
        "scenario",
        "business_rule_results",
        "sensitive_data_scan",
        "client_checks",
        "regression",
    ):
        section = requirement.get(section_name)
        if section is not None:
            walk(section)
    return ids


def _require_evidence_kind(
    evidence_by_id: dict[str, dict[str, Any]],
    evidence_id: Any,
    allowed_kinds: set[str],
    evidence_label: str,
    errors: list[str],
) -> None:
    if not _is_nonempty_string(evidence_id):
        return
    row = evidence_by_id.get(str(evidence_id).strip())
    if row is not None and row.get("kind") not in allowed_kinds:
        errors.append(
            f"{evidence_label}: evidence kind must be " + " or ".join(sorted(allowed_kinds))
        )


def _validate_requirement_evidence_kinds(
    requirement: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    boundary = requirement.get("action_boundary")
    if isinstance(boundary, dict):
        _require_evidence_kind(
            evidence_by_id,
            boundary.get("evidence_id"),
            {"action_boundary"},
            f"{label}.action_boundary",
            errors,
        )
    raw = requirement.get("raw_api_call")
    if isinstance(raw, dict):
        raw_kind = {
            "tag_assistant_api_call": {"api_call"},
            "browser_interception": {"browser_interception"},
            "not_observed": {"action_boundary"},
        }.get(str(raw.get("capture_source")), {"api_call", "browser_interception"})
        _require_evidence_kind(
            evidence_by_id,
            raw.get("evidence_id"),
            raw_kind,
            f"{label}.raw_api_call",
            errors,
        )
    occurrence = requirement.get("occurrence_evidence")
    if isinstance(occurrence, dict):
        mechanism = str(
            requirement.get("expectation", {}).get("source_mechanism", "data_layer_push")
        )
        if requirement.get("event_observed") is False:
            allowed_occurrence = {"action_boundary"}
        elif mechanism == "data_layer_push":
            allowed_occurrence = {"api_call", "browser_interception"}
        else:
            allowed_occurrence = {"source_signal", mechanism}
        _require_evidence_kind(
            evidence_by_id,
            occurrence.get("evidence_id"),
            allowed_occurrence,
            f"{label}.occurrence_evidence",
            errors,
        )
    for field, allowed in (
        ("resolved_data_layer", {"resolved_data_layer"}),
        ("gtm_variable", {"gtm_variable"}),
        ("scenario", {"scenario_branch"}),
        ("trigger_evaluation", {"trigger_evaluation"}),
        ("tag_sequence", {"tag_sequence"}),
        ("sensitive_data_scan", {"sensitive_data_scan"}),
        ("regression", {"previous_run_comparison"}),
    ):
        section = requirement.get(field)
        if isinstance(section, dict):
            _require_evidence_kind(
                evidence_by_id,
                section.get("evidence_id"),
                allowed,
                f"{label}.{field}",
                errors,
            )
    signal = requirement.get("source_signal")
    if isinstance(signal, dict):
        _require_evidence_kind(
            evidence_by_id,
            signal.get("evidence_id"),
            {"source_signal", str(signal.get("mechanism", ""))},
            f"{label}.source_signal",
            errors,
        )
    tag = requirement.get("tag")
    if isinstance(tag, dict):
        configuration_evidence = evidence_by_id.get(
            str(tag.get("configuration_evidence_id", "")).strip()
        )
        _require_evidence_kind(
            evidence_by_id,
            tag.get("configuration_evidence_id"),
            {"tag_configuration"},
            f"{label}.tag.configuration",
            errors,
        )
        _require_evidence_kind(
            evidence_by_id,
            tag.get("runtime_evidence_id"),
            {"tag_runtime"},
            f"{label}.tag.runtime",
            errors,
        )
        if configuration_evidence is not None:
            if configuration_evidence.get("tag_name") != tag.get("name"):
                errors.append(f"{label}.tag.configuration: evidence tag_name differs from tag")
            if configuration_evidence.get("configuration_field") != tag.get("configuration_field"):
                errors.append(
                    f"{label}.tag.configuration: evidence configuration_field differs from tag"
                )
        runtime_evidence = evidence_by_id.get(str(tag.get("runtime_evidence_id", "")).strip())
        if runtime_evidence is not None:
            if runtime_evidence.get("tag_name") != tag.get("name"):
                errors.append(f"{label}.tag.runtime: evidence tag_name differs from tag")
            if runtime_evidence.get("configuration_field") != tag.get("configuration_field"):
                errors.append(f"{label}.tag.runtime: evidence configuration_field differs from tag")
    destination = requirement.get("destination_request")
    if isinstance(destination, dict):
        _require_evidence_kind(
            evidence_by_id,
            destination.get("evidence_id"),
            {"browser_network_request"},
            f"{label}.destination_request",
            errors,
        )
        request_evidence = evidence_by_id.get(str(destination.get("evidence_id", "")).strip())
        if request_evidence is not None and (
            request_evidence.get("request_id") != destination.get("request_id")
        ):
            errors.append(f"{label}.destination_request: evidence request_id differs from request")
        _require_evidence_kind(
            evidence_by_id,
            destination.get("vendor_helper_evidence_id"),
            {"vendor_helper"},
            f"{label}.destination_request.vendor_helper",
            errors,
        )
    consent = requirement.get("consent")
    if isinstance(consent, dict) and consent.get("applicable") is True:
        _require_evidence_kind(
            evidence_by_id,
            consent.get("evidence_id"),
            {"consent_state", "tag_assistant_consent"},
            f"{label}.consent",
            errors,
        )
        _require_evidence_kind(
            evidence_by_id,
            consent.get("approval_evidence_id"),
            {"analyst_approval"},
            f"{label}.consent.approval",
            errors,
        )
        _require_evidence_kind(
            evidence_by_id,
            consent.get("production_approval_evidence_id"),
            {"analyst_approval"},
            f"{label}.consent.production_approval",
            errors,
        )
    for index, result in enumerate(requirement.get("business_rule_results", []), start=1):
        if isinstance(result, dict):
            _require_evidence_kind(
                evidence_by_id,
                result.get("evidence_id"),
                {"business_rule_evaluation"},
                f"{label}.business_rule_results[{index}]",
                errors,
            )
    for index, check in enumerate(requirement.get("client_checks", []), start=1):
        if isinstance(check, dict):
            _require_evidence_kind(
                evidence_by_id,
                check.get("evidence_id"),
                {"client_side_checks"},
                f"{label}.client_checks[{index}]",
                errors,
            )


def _validate_occurrence(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    rule, anchor_name = occurrence_rule(expectation)
    if rule not in OCCURRENCE_RULES:
        errors.append(f"{label}: invalid or missing expected_occurrence rule")
        return
    occurrence = requirement.get("occurrence_evidence")
    if not isinstance(occurrence, dict):
        errors.append(f"{label}: missing occurrence_evidence")
        return
    actual_count = occurrence.get("actual_count")
    indexes = occurrence.get("event_indexes")
    if not isinstance(actual_count, int) or actual_count < 0:
        errors.append(f"{label}: occurrence actual_count must be a non-negative integer")
    if not isinstance(indexes, list) or not all(isinstance(item, int) for item in indexes):
        errors.append(f"{label}: occurrence event_indexes must be an integer array")
        indexes = []
    elif isinstance(actual_count, int) and len(indexes) != actual_count:
        errors.append(f"{label}: occurrence event_indexes length differs from actual_count")
    if not _is_nonempty_string(occurrence.get("evidence_id")):
        errors.append(f"{label}: occurrence evidence_id is required")

    event_observed = requirement.get("event_observed")
    if event_observed is True and isinstance(actual_count, int) and actual_count < 1:
        errors.append(f"{label}: observed event requires a positive occurrence count")
    if event_observed is False and isinstance(actual_count, int) and actual_count != 0:
        errors.append(f"{label}: unobserved event requires occurrence count zero")

    status = status_of(verdict.get("event_occurrence"))
    if status not in VALID_STATUSES:
        errors.append(f"{label}: verdict.event_occurrence has invalid status '{status}'")
        return
    if status != "PASS":
        return
    passed = False
    if rule == "once":
        passed = actual_count == 1
    elif rule == "at_least_once":
        passed = isinstance(actual_count, int) and actual_count >= 1
    elif rule == "absent":
        passed = actual_count == 0
    elif rule in {"before_event", "after_event"}:
        anchor_index = occurrence.get("anchor_event_index")
        if not anchor_name:
            errors.append(f"{label}: {rule} requires expected anchor_event_name")
        if occurrence.get("anchor_event_name") != anchor_name:
            errors.append(f"{label}: occurrence anchor event differs from expectation")
        if not isinstance(anchor_index, int):
            errors.append(f"{label}: {rule} requires anchor_event_index")
        elif not indexes:
            passed = False
        elif rule == "before_event":
            passed = max(indexes) < anchor_index
        else:
            passed = min(indexes) > anchor_index
    elif rule == "conditional":
        configured = expectation.get("expected_occurrence")
        scenario = requirement.get("scenario")
        branch_rule = configured.get("branch_rule") if isinstance(configured, dict) else None
        if branch_rule not in {"once", "at_least_once", "absent"}:
            errors.append(
                f"{label}: conditional occurrence requires branch_rule once, "
                "at_least_once, or absent"
            )
        if not isinstance(configured, dict) or not _is_nonempty_string(
            configured.get("condition_id")
        ):
            errors.append(f"{label}: conditional occurrence requires condition_id")
        if not isinstance(scenario, dict) or scenario.get("condition_met") is not True:
            errors.append(
                f"{label}: conditional PASS requires evidence that the declared condition was met"
            )
        if branch_rule == "once":
            passed = actual_count == 1
        elif branch_rule == "at_least_once":
            passed = isinstance(actual_count, int) and actual_count >= 1
        elif branch_rule == "absent":
            passed = actual_count == 0
    elif rule == "non_deterministic":
        scenario = requirement.get("scenario")
        if (
            not isinstance(scenario, dict)
            or not isinstance(scenario.get("attempts"), list)
            or not scenario.get("attempts")
        ):
            errors.append(
                f"{label}: non_deterministic occurrence requires documented scenario attempts"
            )
        passed = isinstance(actual_count, int) and actual_count >= 1
    if not passed:
        errors.append(f"{label}: PASS event occurrence contradicts observed chronology/count")


def _contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in PLACEHOLDER_VALUES
    if isinstance(value, dict):
        return any(_contains_placeholder(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_placeholder(item) for item in value)
    return False


def _validate_observation(
    observation: Any,
    label: str,
    errors: list[str],
    *,
    require_payload: bool = False,
) -> None:
    if not isinstance(observation, dict):
        errors.append(f"{label}: missing observation object")
        return
    state = str(observation.get("field_state", "")).strip()
    value_type = str(observation.get("field_type", "")).strip()
    if state not in FIELD_STATES:
        errors.append(f"{label}: invalid or missing field_state")
    if value_type not in VALUE_TYPES:
        errors.append(f"{label}: invalid or missing field_type")

    has_value = "field_value" in observation
    value = observation.get("field_value")
    if state == "absent" and value_type != "absent":
        errors.append(f"{label}: absent field must use field_type 'absent'")
    elif state == "undefined" and value_type != "undefined":
        errors.append(f"{label}: undefined field must use field_type 'undefined'")
    elif state == "null" and (value_type != "null" or not has_value or value is not None):
        errors.append(f"{label}: null field must retain explicit null value and type")
    elif state not in {"absent", "undefined"}:
        if not has_value:
            errors.append(f"{label}: represented field state requires field_value")
        elif js_value_type(value) != value_type:
            errors.append(
                f"{label}: field_type '{value_type}' does not match represented value type "
                f"'{js_value_type(value)}'"
            )
        expected_state = field_state_for(value)
        if state != expected_state:
            errors.append(
                f"{label}: field_state '{state}' does not match represented value state "
                f"'{expected_state}'"
            )

    if not _is_nonempty_string(observation.get("evidence_id")):
        errors.append(f"{label}: missing evidence_id")
    if require_payload:
        payload = observation.get("payload")
        if not isinstance(payload, dict):
            errors.append(f"{label}: exact raw payload must be a structured object")
        elif _contains_placeholder(payload):
            errors.append(f"{label}: exact raw payload contains an omitted/placeholder value")


def _matches_expectation(expectation: dict[str, Any], observation: dict[str, Any]) -> bool | None:
    rule = str(expectation.get("match_rule", "")).strip()
    state = str(observation.get("field_state", "")).strip()
    actual = observation.get("field_value")
    actual_type = str(observation.get("field_type", "")).strip()
    expected = expectation.get("expected_value")
    expected_type = str(expectation.get("expected_type", "")).strip()

    if rule == "equals":
        return (
            state == field_state_for(expected)
            and actual == expected
            and actual_type == expected_type
        )
    if rule == "absent":
        return state == "absent"
    if rule == "present":
        return state not in {"absent", "undefined"}
    if rule == "not_empty":
        return state == "present"
    if rule == "type":
        return actual_type == expected_type
    if rule == "regex":
        pattern = expectation.get("pattern")
        if not isinstance(pattern, str) or not isinstance(actual, str):
            return False
        return re.fullmatch(pattern, actual) is not None
    if rule == "one_of":
        allowed = expectation.get("allowed_values")
        return isinstance(allowed, list) and actual in allowed and actual_type == expected_type
    if rule == "contains":
        member = expectation.get("required_member")
        if isinstance(actual, str) and isinstance(member, str):
            return member in actual
        if isinstance(actual, (list, dict)):
            return member in actual
        return False
    if rule == "range":
        allowed = expectation.get("allowed_range")
        if (
            not isinstance(allowed, dict)
            or not isinstance(actual, (int, float))
            or isinstance(actual, bool)
        ):
            return False
        minimum = allowed.get("min")
        maximum = allowed.get("max")
        return (
            (minimum is None or actual >= minimum)
            and (maximum is None or actual <= maximum)
            and actual_type == expected_type
        )
    if rule == "format":
        format_name = expectation.get("format")
        return format_name in FORMATS and format_matches(actual, str(format_name))
    if rule == "anti_pattern":
        pattern = expectation.get("pattern")
        if not isinstance(pattern, str) or not isinstance(actual, str):
            return False
        try:
            return re.search(pattern, actual) is None
        except re.error:
            return False
    if rule == "vendor_equivalent":
        return (
            _is_nonempty_string(expectation.get("vendor_parameter_name"))
            and state == field_state_for(expected)
            and actual == expected
            and actual_type == expected_type
        )
    if rule in {"changes", "stable", "documented_transform", "business_rule"}:
        return None
    return None


def _validate_action_boundary(
    boundary: Any,
    label: str,
    errors: list[str],
    *,
    observed: bool,
    require_ready: bool,
    require_settled: bool = True,
) -> None:
    if not isinstance(boundary, dict):
        errors.append(f"{label}: missing action_boundary")
        return
    for field in (
        "action_timestamp",
        "quiet_window_ms",
        "timeout_ms",
        "stream_settled",
        "evidence_id",
    ):
        if field not in boundary:
            errors.append(f"{label}: action_boundary missing '{field}'")
    if not _is_nonempty_string(boundary.get("evidence_id")):
        errors.append(f"{label}: action_boundary requires evidence_id")
    action_id = boundary.get("action_id")
    if action_id is not None and not _is_nonempty_string(action_id):
        errors.append(f"{label}: action_id must be a non-empty string when supplied")
    retry_of_action_id = boundary.get("retry_of_action_id")
    if retry_of_action_id not in (None, ""):
        if not _is_nonempty_string(retry_of_action_id):
            errors.append(f"{label}: retry_of_action_id must be a non-empty string when supplied")
        if not _is_nonempty_string(action_id):
            errors.append(f"{label}: retry_of_action_id requires action_id")
        if retry_of_action_id == action_id:
            errors.append(f"{label}: an action cannot retry itself")
    interaction_outcome = boundary.get("interaction_outcome")
    if interaction_outcome is not None and interaction_outcome not in INTERACTION_OUTCOMES:
        errors.append(f"{label}: invalid interaction_outcome")
    completion_signal = boundary.get("completion_signal")
    if completion_signal is not None and not _is_nonempty_string(completion_signal):
        errors.append(f"{label}: completion_signal must be a non-empty string when supplied")
    if interaction_outcome == "completed" and not _is_nonempty_string(completion_signal):
        errors.append(f"{label}: completed interaction requires an independent completion_signal")
    settlement_reason = boundary.get("settlement_reason")
    if settlement_reason is not None and settlement_reason not in SETTLEMENT_REASONS:
        errors.append(f"{label}: invalid settlement_reason")
    if require_ready:
        for field in ("preview_connected_before", "target_ready_before"):
            if boundary.get(field) is not True:
                errors.append(f"{label}: action_boundary requires {field}=true")
    quiet = boundary.get("quiet_window_ms")
    timeout = boundary.get("timeout_ms")
    if not isinstance(quiet, int) or quiet <= 0:
        errors.append(f"{label}: quiet_window_ms must be a positive integer")
    if not isinstance(timeout, int) or timeout <= 0:
        errors.append(f"{label}: timeout_ms must be a positive integer")
    if require_settled and boundary.get("stream_settled") is not True:
        errors.append(f"{label}: event stream was not recorded as settled")
    if boundary.get("stream_settled") is False and settlement_reason in {
        "expected_and_quiet",
        "quiet_without_expected",
    }:
        errors.append(f"{label}: unsettled stream cannot use a quiet settlement_reason")
    if "last_event_before" not in boundary:
        errors.append(f"{label}: action_boundary missing 'last_event_before'")
    if "settled_final_event" not in boundary:
        errors.append(f"{label}: action_boundary missing 'settled_final_event'")
    action_timestamp = boundary.get("action_timestamp")
    if not _is_nonempty_string(action_timestamp):
        errors.append(f"{label}: action_timestamp must be ISO 8601 with timezone")
    else:
        try:
            parsed_action_time = datetime.fromisoformat(
                str(action_timestamp).replace("Z", "+00:00")
            )
        except ValueError:
            errors.append(f"{label}: action_timestamp must be ISO 8601 with timezone")
        else:
            if parsed_action_time.tzinfo is None:
                errors.append(f"{label}: action_timestamp must be ISO 8601 with timezone")
    last_event = boundary.get("last_event_before")
    first_event = boundary.get("first_event_after")
    settled_event = boundary.get("settled_final_event")
    if not isinstance(last_event, int) or isinstance(last_event, bool) or last_event < 0:
        errors.append(f"{label}: last_event_before must be a non-negative integer")
    if not isinstance(settled_event, int) or isinstance(settled_event, bool) or settled_event < 0:
        errors.append(f"{label}: settled_final_event must be a non-negative integer")
    if first_event is not None and (
        not isinstance(first_event, int) or isinstance(first_event, bool) or first_event < 0
    ):
        errors.append(f"{label}: first_event_after must be a non-negative integer or null")
    if observed and not isinstance(first_event, int):
        errors.append(f"{label}: observed event requires first_event_after")
    if isinstance(last_event, int) and isinstance(first_event, int) and first_event <= last_event:
        errors.append(f"{label}: first_event_after must follow last_event_before")
    if (
        isinstance(last_event, int)
        and isinstance(settled_event, int)
        and settled_event < last_event
    ):
        errors.append(f"{label}: settled_final_event cannot precede last_event_before")
    if (
        isinstance(first_event, int)
        and isinstance(settled_event, int)
        and settled_event < first_event
    ):
        errors.append(f"{label}: settled_final_event cannot precede first_event_after")


def _validate_tag(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    tag = requirement.get("tag")
    tag_expected = _is_nonempty_string(expectation.get("tag_name"))
    if not tag_expected and not isinstance(tag, dict):
        return
    if not isinstance(tag, dict):
        errors.append(f"{label}: concerned tag expectation requires tag evidence")
        return
    if tag.get("applicable") is not True:
        errors.append(f"{label}: supplied concerned tag must be applicable")
    if tag.get("relevance") not in TAG_RELEVANCE:
        errors.append(f"{label}: tag relevance must identify why the tag is concerned")
    for field in (
        "name",
        "expected_firing",
        "actual_firing",
        "configuration_field",
        "configured_value",
        "configuration_evidence_id",
    ):
        if field not in tag or tag.get(field) in ("", None):
            errors.append(f"{label}: tag missing '{field}'")
    if not isinstance(tag.get("fire_count"), int) or tag.get("fire_count") < 0:
        errors.append(f"{label}: tag fire_count must be a non-negative integer")

    expected_firing = str(tag.get("expected_firing", "")).strip()
    actual_firing = str(tag.get("actual_firing", "")).strip()
    firing_status = status_of(verdict.get("tag_firing"))
    if expectation.get("expected_firing") not in (None, "") and firing_status not in VALID_STATUSES:
        errors.append(f"{label}: expected tag firing requires tag_firing verdict")
    firing_pass = firing_status == "PASS"
    if firing_pass:
        if expected_firing == "fired_once" and not (
            actual_firing in {"fired", "fired_once"} and tag.get("fire_count") == 1
        ):
            errors.append(f"{label}: PASS tag firing contradicts expected fired_once")
        elif expected_firing == "fired" and not (
            actual_firing in {"fired", "fired_once"} and tag.get("fire_count", 0) >= 1
        ):
            errors.append(f"{label}: PASS tag firing contradicts expected fired")
        elif expected_firing in {"not_fired", "blocked"} and tag.get("fire_count") != 0:
            errors.append(f"{label}: PASS tag blocking contradicts observed fire_count")

    wanted_to_fire = expected_firing in {"fired", "fired_once"}
    did_not_fire = actual_firing not in {"fired", "fired_once"} or tag.get("fire_count") == 0
    if wanted_to_fire and did_not_fire:
        reason = str(tag.get("non_firing_reason", "")).strip()
        source = str(tag.get("reason_source", "")).strip()
        if not reason:
            errors.append(f"{label}: wanted non-fired tag lacks non_firing_reason")
        if source not in REASON_SOURCES:
            errors.append(f"{label}: wanted non-fired tag lacks valid reason_source")
        if source == "not_established" and reason != (
            "Reason not established from available Preview evidence"
        ):
            errors.append(f"{label}: reason-not-established text must use the canonical statement")

    parameter_status = status_of(verdict.get("tag_parameter"))
    if (
        expectation.get("tag_configuration_field") not in (None, "")
        and parameter_status not in VALID_STATUSES
    ):
        errors.append(f"{label}: expected runtime tag parameter requires tag_parameter verdict")
    if parameter_status in {"PASS", "FAIL", "REVIEW"}:
        for field in ("runtime_state", "runtime_type", "runtime_evidence_id"):
            if field not in tag or tag.get(field) in ("", None):
                errors.append(f"{label}: tag parameter verdict requires '{field}'")
        runtime_state = tag.get("runtime_state")
        if runtime_state not in FIELD_STATES:
            errors.append(f"{label}: invalid tag runtime_state")
        runtime_type = tag.get("runtime_type")
        if runtime_type not in VALUE_TYPES:
            errors.append(f"{label}: invalid tag runtime_type")
        if runtime_state not in {"absent", "undefined"}:
            if "runtime_value" not in tag:
                errors.append(f"{label}: tag runtime evidence requires runtime_value")
            elif js_value_type(tag.get("runtime_value")) != runtime_type:
                errors.append(f"{label}: tag runtime_type does not match runtime_value")
    if status_of(verdict.get("tag_firing")) == "PASS" and tag.get("execution_error") not in (
        None,
        "",
    ):
        errors.append(f"{label}: PASS tag firing contradicts the recorded execution_error")
    vendor_family = expectation.get("vendor_family")
    if vendor_family not in (None, ""):
        if vendor_family not in VENDOR_FAMILIES:
            errors.append(f"{label}: unsupported expectation vendor_family '{vendor_family}'")
        if tag.get("vendor_family") != vendor_family:
            errors.append(f"{label}: concerned tag vendor_family differs from expectation")
    destination_id = expectation.get("destination_id")
    if destination_id not in (None, "") and tag.get("destination_id") != destination_id:
        errors.append(f"{label}: concerned tag destination_id differs from expectation")
    destination_event_name = expectation.get("destination_event_name")
    if destination_event_name not in (None, "") and tag.get("event_name") != destination_event_name:
        errors.append(f"{label}: concerned tag event_name differs from expectation")
    expected_configuration = expectation.get("expected_tag_configuration")
    configuration_status = status_of(verdict.get("tag_configuration"))
    if tag_expected and configuration_status not in VALID_STATUSES:
        errors.append(f"{label}: concerned tag requires a configuration verdict")
    if (
        expected_configuration not in (None, "")
        and configuration_status == "PASS"
        and tag.get("configured_value") != expected_configuration
    ):
        errors.append(f"{label}: PASS tag configuration differs from the tracking-plan expectation")


def _validate_consent_override(
    requirement: dict[str, Any],
    run: dict[str, Any],
    blockers: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    consent = requirement.get("consent")
    if not isinstance(consent, dict) or consent.get("source") != "session_override":
        return
    if consent.get("override_approved") is not True:
        errors.append(f"{label}: session consent override lacks explicit analyst approval")
    for field in (
        "approval_evidence_id",
        "override_method",
        "override_scope",
        "before_state",
        "state_at_event",
        "native_cmp_status",
        "native_cmp_acceptance_in_scope",
        "blocker_id",
    ):
        if field not in consent or consent.get(field) in ("", None):
            errors.append(f"{label}: session consent override missing '{field}'")
    if consent.get("override_scope") != "session_only":
        errors.append(f"{label}: consent override must be session_only")
    if consent.get("native_cmp_status") not in {"FAIL", "BLOCKED", "REVIEW"}:
        errors.append(f"{label}: simulated consent can never mark the native CMP as PASS")
    if (
        consent.get("native_cmp_acceptance_in_scope") is True
        and status_of(requirement.get("verdict", {}).get("consent")) == "PASS"
    ):
        errors.append(f"{label}: native CMP acceptance cannot PASS from simulated consent")
    blocker = blockers.get(str(consent.get("blocker_id", "")))
    if run.get("environment_class") == "production":
        for field in (
            "production_exception_approved",
            "production_approval_evidence_id",
            "restoration_confirmed",
        ):
            if consent.get(field) is not True and field != "production_approval_evidence_id":
                errors.append(f"{label}: production consent override requires {field}=true")
            if field == "production_approval_evidence_id" and not _is_nonempty_string(
                consent.get(field)
            ):
                errors.append(
                    f"{label}: production consent override requires production_approval_evidence_id"
                )
        if not blocker or blocker.get("type") != "CMP_PRODUCTION_ENVIRONMENT":
            errors.append(
                f"{label}: production consent override must reference a "
                "CMP_PRODUCTION_ENVIRONMENT blocker"
            )
    elif not blocker or blocker.get("type") != "CMP_TEST_ENVIRONMENT":
        errors.append(
            f"{label}: session consent override must reference a CMP_TEST_ENVIRONMENT blocker"
        )


def _validate_run_client_context(run: dict[str, Any], errors: list[str]) -> None:
    containers = run.get("containers")
    if not isinstance(containers, list) or not containers:
        errors.append("run: containers must be a non-empty client-side web-container array")
    else:
        ids: list[str] = []
        primary_count = 0
        for index, container in enumerate(containers, start=1):
            label = f"run.containers row {index}"
            if not isinstance(container, dict):
                errors.append(f"{label}: must be an object")
                continue
            container_id = str(container.get("container_id", "")).strip()
            if not container_id:
                errors.append(f"{label}: missing container_id")
            ids.append(container_id)
            if not _is_nonempty_string(container.get("workspace")):
                errors.append(f"{label}: missing workspace")
            if container.get("role") not in CONTAINER_ROLES:
                errors.append(f"{label}: invalid role")
            if container.get("role") == "primary":
                primary_count += 1
            container_type = container.get("container_type")
            if container_type not in CONTAINER_TYPES:
                errors.append(
                    f"{label}: only client-side web containers are supported; "
                    "server-side GTM is out of scope"
                )
        if len(set(ids)) != len(ids):
            errors.append("run: containers contains duplicate container_id values")
        if primary_count != 1:
            errors.append("run: containers must identify exactly one primary container")
        if run.get("container_id") not in ids:
            errors.append("run: primary container_id is absent from containers")
        else:
            primary = next(
                (
                    item
                    for item in containers
                    if isinstance(item, dict)
                    and item.get("container_id") == run.get("container_id")
                ),
                {},
            )
            if primary.get("role") != "primary":
                errors.append("run: container_id must identify the primary container")
            if primary.get("workspace") != run.get("workspace"):
                errors.append("run: primary container workspace differs from run.workspace")

    contexts = run.get("browser_contexts")
    if contexts is not None:
        if not isinstance(contexts, list) or not contexts:
            errors.append("run: browser_contexts must be a non-empty array when supplied")
        else:
            context_ids: list[str] = []
            for index, context in enumerate(contexts, start=1):
                label = f"run.browser_contexts row {index}"
                if not isinstance(context, dict):
                    errors.append(f"{label}: must be an object")
                    continue
                context_id = str(context.get("context_id", "")).strip()
                if not context_id:
                    errors.append(f"{label}: missing context_id")
                context_ids.append(context_id)
                if context.get("device_class") not in {"desktop", "mobile", "tablet", "responsive"}:
                    errors.append(f"{label}: invalid device_class")
                viewport = context.get("viewport")
                if not isinstance(viewport, dict):
                    errors.append(f"{label}: missing viewport")
                elif not all(
                    isinstance(viewport.get(field), int) and viewport.get(field) > 0
                    for field in ("width", "height")
                ):
                    errors.append(f"{label}: viewport width and height must be positive integers")
            if len(set(context_ids)) != len(context_ids):
                errors.append("run: browser_contexts contains duplicate context_id values")


def _validate_scenario(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expected_rule, _ = occurrence_rule(requirement.get("expectation", {}))
    scenario = requirement.get("scenario")
    if expected_rule not in {"conditional", "non_deterministic"} and scenario is None:
        return
    if not isinstance(scenario, dict):
        errors.append(f"{label}: conditional/non-deterministic work requires scenario evidence")
        return
    for field in ("scenario_id", "kind", "condition", "branch", "evidence_id"):
        if field not in scenario or scenario.get(field) in ("", None):
            errors.append(f"{label}: scenario missing '{field}'")
    if scenario.get("kind") not in SCENARIO_KINDS:
        errors.append(f"{label}: invalid scenario.kind")
    if expected_rule == "conditional" and scenario.get("condition_met") not in {True, False}:
        errors.append(f"{label}: conditional scenario requires condition_met")
    if expected_rule == "non_deterministic":
        attempts = scenario.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            errors.append(f"{label}: non_deterministic scenario requires attempted branches/routes")


def _validate_source_signal(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    mechanism = str(expectation.get("source_mechanism", "data_layer_push"))
    signal = requirement.get("source_signal")
    if mechanism not in SOURCE_MECHANISMS:
        errors.append(f"{label}: unsupported source_mechanism '{mechanism}'")
        return
    if mechanism == "data_layer_push" and signal is None:
        return
    if status_of(verdict.get("source_signal")) not in VALID_STATUSES:
        errors.append(f"{label}: non-dataLayer source requires source_signal verdict")
    if not isinstance(signal, dict):
        errors.append(f"{label}: non-dataLayer source requires source_signal evidence")
        return
    for field in ("mechanism", "event_name", "capture_source", "evidence_id"):
        if field not in signal or signal.get(field) in ("", None):
            errors.append(f"{label}: source_signal missing '{field}'")
    if signal.get("mechanism") != mechanism:
        errors.append(f"{label}: source_signal mechanism differs from expectation")
    if signal.get("event_name") != expectation.get("event_name"):
        errors.append(f"{label}: source_signal event_name differs from expectation")
    if signal.get("capture_source") not in SOURCE_CAPTURE_SOURCES:
        errors.append(f"{label}: invalid source_signal capture_source")
    if status_of(verdict.get("source_signal")) == "PASS" and signal.get("observed") is not True:
        errors.append(f"{label}: PASS source_signal requires observed=true")


def _request_surface(destination: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic view of values retained from browser request evidence."""
    query: dict[str, Any] = {}
    request_url = destination.get("request_url")
    if isinstance(request_url, str):
        for key, value in parse_qsl(urlsplit(request_url).query, keep_blank_values=True):
            if key in query:
                existing = query[key]
                query[key] = existing + [value] if isinstance(existing, list) else [existing, value]
            else:
                query[key] = value
    return {
        "query": query,
        "body": destination.get("request_body", {}),
        "headers": destination.get("request_headers", {}),
    }


def _wire_value(destination: dict[str, Any], declared_path: Any) -> Any:
    if not _is_nonempty_string(declared_path):
        return MISSING
    path = str(declared_path).strip()
    if not path.startswith(
        (
            "query.",
            "query[",
            "body.",
            "body[",
            "headers.",
            "headers[",
        )
    ):
        return MISSING
    return path_value(_request_surface(destination), path)


def _coerce_wire_value(value: Any, value_type: Any) -> Any:
    """Coerce a scalar wire string only when the declared protocol type permits it."""
    if not isinstance(value, str):
        return value
    try:
        if value_type == "number":
            parsed = float(value)
            return int(parsed) if parsed.is_integer() else parsed
        if value_type == "boolean" and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        if value_type in {"array", "object"}:
            parsed = json.loads(value)
            return parsed if js_value_type(parsed) == value_type else MISSING
        if value_type == "null" and value.lower() == "null":
            return None
    except (ValueError, TypeError, json.JSONDecodeError):
        return MISSING
    return value


def _validate_destination(
    requirement: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    expected_behavior = expectation.get("expected_request_behavior")
    destination_expected = is_browser_sending_tag(expectation)
    destination = requirement.get("destination_request")
    if not destination_expected and destination is None:
        return
    if expectation.get("vendor_family") not in VENDOR_FAMILIES:
        errors.append(f"{label}: destination expectation requires a supported vendor_family")
    if expected_behavior not in EXPECTED_REQUEST_BEHAVIOURS:
        errors.append(f"{label}: destination expectation requires expected_request_behavior")
    if not isinstance(destination, dict):
        errors.append(f"{label}: destination expectation requires destination_request evidence")
        return
    if destination.get("applicable") is not True:
        errors.append(f"{label}: supplied destination_request must be applicable")
    for field in (
        "vendor_family",
        "request_behavior",
        "request_count",
        "capture_source",
        "evidence_id",
        "request_id",
    ):
        if field not in destination or destination.get(field) in ("", None):
            errors.append(f"{label}: destination_request missing '{field}'")
    if destination.get("vendor_family") != expectation.get("vendor_family"):
        errors.append(f"{label}: destination vendor_family differs from expectation")
    expected_destination = expectation.get("destination_id")
    if (
        expected_destination not in (None, "")
        and destination.get("destination_id") != expected_destination
    ):
        errors.append(f"{label}: destination_id differs from expectation")
    expected_destination_event = expectation.get("destination_event_name")
    if (
        expected_destination_event not in (None, "")
        and destination.get("event_name") != expected_destination_event
    ):
        errors.append(f"{label}: destination event_name differs from expectation")
    if destination.get("capture_source") not in DESTINATION_CAPTURE_SOURCES:
        errors.append(f"{label}: invalid destination capture_source")
    if destination.get("request_behavior") not in REQUEST_BEHAVIOURS:
        errors.append(f"{label}: invalid destination request_behavior")
    if (
        not isinstance(destination.get("request_count"), int)
        or destination.get("request_count") < 0
    ):
        errors.append(f"{label}: destination request_count must be a non-negative integer")

    request_status = status_of(verdict.get("destination_request"))
    if request_status not in VALID_STATUSES:
        errors.append(f"{label}: destination expectation requires destination_request verdict")
    actual_behavior = destination.get("request_behavior")
    count = destination.get("request_count")
    if isinstance(count, int):
        if actual_behavior in {"sent", "full", "cookieless"} and count < 1:
            errors.append(f"{label}: observed destination send requires request_count >= 1")
        if actual_behavior in {"not_observed", "blocked"} and count != 0:
            errors.append(f"{label}: absent/blocked destination request requires request_count=0")
    if request_status == "PASS":
        if destination.get("capture_source") != "browser_network":
            errors.append(
                f"{label}: destination request PASS requires first-party browser-network evidence; "
                "vendor helpers are supplementary"
            )
        request_evidence = evidence_by_id.get(str(destination.get("evidence_id", "")))
        if not request_evidence or request_evidence.get("kind") != "browser_network_request":
            errors.append(
                f"{label}: destination request PASS requires browser_network_request evidence"
            )
        if actual_behavior in {"sent", "full", "cookieless"} and not _is_nonempty_string(
            destination.get("request_url")
        ):
            errors.append(f"{label}: observed browser request requires request_url")
        behavior_matches = {
            "sent": (
                actual_behavior in {"sent", "full", "cookieless"}
                and isinstance(count, int)
                and count >= 1
            ),
            "sent_once": (actual_behavior in {"sent", "full", "cookieless"} and count == 1),
            "absent": actual_behavior == "not_observed" and count == 0,
            "blocked": actual_behavior == "blocked" and count == 0,
            "cookieless": (
                actual_behavior == "cookieless" and isinstance(count, int) and count >= 1
            ),
            "full": (actual_behavior == "full" and isinstance(count, int) and count >= 1),
        }.get(str(expected_behavior), False)
        if not behavior_matches:
            errors.append(f"{label}: PASS destination request contradicts expected behavior")
        endpoint_pattern = expectation.get("expected_endpoint_pattern")
        if endpoint_pattern:
            try:
                endpoint_matches = re.search(
                    str(endpoint_pattern), str(destination.get("request_url", ""))
                )
            except re.error:
                endpoint_matches = None
                errors.append(f"{label}: invalid expected_endpoint_pattern")
            if endpoint_matches is None:
                errors.append(f"{label}: PASS destination endpoint differs from expectation")

    for expectation_field, destination_field, field_label in (
        ("destination_id_parameter_path", "destination_id", "destination ID"),
        ("destination_event_parameter_path", "event_name", "destination event name"),
    ):
        claimed_value = destination.get(destination_field)
        expected_value = expectation.get(destination_field)
        if expectation_field == "destination_event_parameter_path":
            expected_value = expectation.get("destination_event_name")
        if (
            expected_value in (None, "")
            or expected_behavior in {"absent", "blocked"}
            or request_status == "BLOCKED"
        ):
            continue
        wire_path = expectation.get(expectation_field)
        if not _is_nonempty_string(wire_path):
            errors.append(f"{label}: {field_label} expectation requires {expectation_field}")
            continue
        wire_value = _wire_value(destination, wire_path)
        if wire_value is MISSING:
            errors.append(f"{label}: {field_label} was not found at declared browser request path")
        elif not _strict_equal(wire_value, claimed_value):
            errors.append(f"{label}: decoded {field_label} differs from browser request evidence")

    parameter_path = expectation.get("destination_parameter_path")
    parameter_status = status_of(verdict.get("destination_parameter"))
    if parameter_path not in (None, "") or parameter_status:
        if parameter_status not in VALID_STATUSES:
            errors.append(
                f"{label}: destination parameter expectation requires destination_parameter verdict"
            )
        if destination.get("parameter_path") != parameter_path:
            errors.append(f"{label}: destination parameter_path differs from expectation")
        if parameter_status == "BLOCKED":
            return
        _validate_observation(destination, f"{label}.destination_request", errors)
        wire_value = _wire_value(destination, parameter_path)
        if wire_value is MISSING:
            errors.append(
                f"{label}: destination parameter was not found at declared browser request path"
            )
        else:
            wire_value = _coerce_wire_value(wire_value, destination.get("field_type"))
            if wire_value is MISSING or not _strict_equal(
                wire_value, destination.get("field_value")
            ):
                errors.append(
                    f"{label}: decoded destination parameter differs from browser request evidence"
                )
        if parameter_status == "PASS":
            destination_expectation = {
                "match_rule": expectation.get("destination_match_rule", "equals"),
                "expected_value": expectation.get(
                    "expected_destination_value", expectation.get("expected_value")
                ),
                "expected_type": expectation.get(
                    "expected_destination_type", expectation.get("expected_type")
                ),
                "pattern": expectation.get("destination_pattern"),
                "allowed_values": expectation.get("destination_allowed_values"),
                "required_member": expectation.get("destination_required_member"),
            }
            if _matches_expectation(destination_expectation, destination) is False:
                errors.append(
                    f"{label}: PASS destination parameter contradicts expected value/type"
                )


def _ordered_subset(expected: list[Any], actual: list[Any]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == item for candidate in iterator) for item in expected)


def _trigger_condition_matches(condition: dict[str, Any]) -> bool | None:
    operator = str(condition.get("operator", "")).strip()
    expected = condition.get("expected")
    actual = condition.get("actual")
    if operator == "equals":
        return _strict_equal(actual, expected)
    if operator == "does_not_equal":
        return not _strict_equal(actual, expected)
    if operator == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected in actual
        if isinstance(actual, (list, dict)):
            return expected in actual
        return False
    if operator == "does_not_contain":
        contained = _trigger_condition_matches({**condition, "operator": "contains"})
        return None if contained is None else not contained
    if operator == "starts_with":
        return isinstance(actual, str) and isinstance(expected, str) and actual.startswith(expected)
    if operator == "ends_with":
        return isinstance(actual, str) and isinstance(expected, str) and actual.endswith(expected)
    if operator == "regex":
        if not isinstance(actual, str) or not isinstance(expected, str):
            return False
        try:
            return re.fullmatch(expected, actual) is not None
        except re.error:
            return None
    numeric = (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    )
    if operator == "greater_than":
        return numeric and actual > expected
    if operator == "greater_than_or_equal":
        return numeric and actual >= expected
    if operator == "less_than":
        return numeric and actual < expected
    if operator == "less_than_or_equal":
        return numeric and actual <= expected
    if operator == "present":
        return actual not in (None, "", [], {})
    if operator == "absent":
        return actual in (None, "", [], {})
    return None


def _validate_trigger_and_sequence(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    trigger_contract = expectation.get("trigger_contract")
    trigger = requirement.get("trigger_evaluation")
    if trigger_contract is not None:
        if not isinstance(trigger_contract, dict):
            errors.append(f"{label}: trigger_contract must be an object")
        elif not isinstance(trigger, dict):
            errors.append(f"{label}: trigger_contract requires trigger_evaluation evidence")
        else:
            if status_of(verdict.get("trigger_logic")) not in VALID_STATUSES:
                errors.append(f"{label}: trigger_contract requires trigger_logic verdict")
            for field in ("mode", "expected_result", "conditions"):
                if field not in trigger_contract:
                    errors.append(f"{label}: trigger_contract missing '{field}'")
            if trigger_contract.get("mode") not in TRIGGER_MODES:
                errors.append(f"{label}: invalid expected trigger mode")
            if trigger_contract.get("expected_result") not in TRIGGER_RESULTS:
                errors.append(f"{label}: invalid expected trigger result")
            contract_conditions = trigger_contract.get("conditions")
            if not isinstance(contract_conditions, list) or not contract_conditions:
                errors.append(f"{label}: trigger_contract conditions must be a non-empty array")
                contract_conditions = []
            contract_by_id: dict[str, dict[str, Any]] = {}
            for index, condition in enumerate(contract_conditions, start=1):
                if not isinstance(condition, dict):
                    errors.append(f"{label}: trigger contract condition {index} must be an object")
                    continue
                condition_id = str(condition.get("condition_id", "")).strip()
                if not condition_id:
                    errors.append(
                        f"{label}: trigger contract condition {index} missing condition_id"
                    )
                if condition_id in contract_by_id:
                    errors.append(
                        f"{label}: trigger_contract contains duplicate condition_id values"
                    )
                contract_by_id[condition_id] = condition
            for field in ("mode", "actual_result", "conditions", "evidence_id"):
                if field not in trigger or trigger.get(field) in ("", None):
                    errors.append(f"{label}: trigger_evaluation missing '{field}'")
            if trigger.get("mode") not in TRIGGER_MODES:
                errors.append(f"{label}: invalid trigger mode")
            if trigger.get("actual_result") not in TRIGGER_RESULTS:
                errors.append(f"{label}: invalid trigger result")
            conditions = trigger.get("conditions")
            if not isinstance(conditions, list):
                errors.append(f"{label}: trigger conditions must be an array")
                conditions = []
            actual_by_id: dict[str, dict[str, Any]] = {}
            condition_matches: list[bool] = []
            for index, condition in enumerate(conditions, start=1):
                if not isinstance(condition, dict):
                    errors.append(f"{label}: trigger condition {index} must be an object")
                    continue
                for field in (
                    "condition_id",
                    "variable",
                    "operator",
                    "expected",
                    "actual",
                    "matched",
                ):
                    if field not in condition:
                        errors.append(f"{label}: trigger condition {index} missing '{field}'")
                condition_id = str(condition.get("condition_id", "")).strip()
                if condition_id in actual_by_id:
                    errors.append(
                        f"{label}: trigger_evaluation contains duplicate condition_id values"
                    )
                actual_by_id[condition_id] = condition
                if not isinstance(condition.get("matched"), bool):
                    errors.append(
                        f"{label}: trigger condition {condition_id or index} matched must be boolean"
                    )
                    continue
                computed_match = _trigger_condition_matches(condition)
                if computed_match is None:
                    errors.append(
                        f"{label}: trigger condition {condition_id or index} has an "
                        "unsupported or invalid operator"
                    )
                    continue
                condition_matches.append(computed_match)
                if condition["matched"] != computed_match:
                    errors.append(
                        f"{label}: trigger condition {condition_id or index} matched "
                        "differs from its expected/actual values"
                    )

            exceptions = trigger.get("blocking_exceptions", [])
            if not isinstance(exceptions, list):
                errors.append(f"{label}: trigger blocking_exceptions must be an array")
                exceptions = []
            exception_by_name: dict[str, dict[str, Any]] = {}
            exception_matches: list[bool] = []
            for index, exception in enumerate(exceptions, start=1):
                if not isinstance(exception, dict):
                    errors.append(f"{label}: blocking exception {index} must be an object")
                    continue
                name = str(exception.get("name", "")).strip()
                matched = exception.get("matched")
                if not name:
                    errors.append(f"{label}: blocking exception {index} missing name")
                if name in exception_by_name:
                    errors.append(
                        f"{label}: trigger_evaluation contains duplicate blocking exceptions"
                    )
                exception_by_name[name] = exception
                if not isinstance(matched, bool):
                    errors.append(
                        f"{label}: blocking exception {name or index} matched must be boolean"
                    )
                else:
                    exception_matches.append(matched)

            computed_result: str | None = None
            if len(condition_matches) == len(conditions):
                if any(exception_matches):
                    computed_result = "blocked"
                elif trigger.get("mode") == "ANY":
                    computed_result = "matched" if any(condition_matches) else "not_matched"
                elif trigger.get("mode") in {"ALL", "TRIGGER_GROUP"}:
                    computed_result = (
                        "matched" if condition_matches and all(condition_matches) else "not_matched"
                    )
            if computed_result and trigger.get("actual_result") != computed_result:
                errors.append(
                    f"{label}: trigger actual_result differs from condition/exception evidence"
                )

            if status_of(verdict.get("trigger_logic")) == "PASS":
                if trigger.get("mode") != trigger_contract.get("mode"):
                    errors.append(f"{label}: PASS trigger mode differs from expectation")
                if trigger.get("actual_result") != trigger_contract.get("expected_result"):
                    errors.append(f"{label}: PASS trigger result differs from expectation")
                if set(contract_by_id) != set(actual_by_id):
                    errors.append(
                        f"{label}: PASS trigger evidence must exactly match expected conditions"
                    )
                for condition_id, contract_condition in contract_by_id.items():
                    actual_condition = actual_by_id.get(condition_id, {})
                    for field, expected_value in contract_condition.items():
                        if field != "condition_id" and not _strict_equal(
                            actual_condition.get(field), expected_value
                        ):
                            errors.append(
                                f"{label}: PASS trigger condition {condition_id} differs "
                                f"from contract field '{field}'"
                            )
                expected_exceptions = trigger_contract.get("blocking_exceptions", [])
                if not isinstance(expected_exceptions, list):
                    errors.append(f"{label}: trigger_contract blocking_exceptions must be an array")
                    expected_exceptions = []
                if set(map(str, expected_exceptions)) != set(exception_by_name):
                    errors.append(
                        f"{label}: PASS trigger evidence must exactly match blocking exceptions"
                    )

    sequence_contract = expectation.get("sequence_contract")
    sequence = requirement.get("tag_sequence")
    if sequence_contract is None:
        return
    if not isinstance(sequence_contract, dict) or not isinstance(
        sequence_contract.get("expected_order"), list
    ):
        errors.append(f"{label}: sequence_contract requires expected_order")
        return
    if not isinstance(sequence, dict):
        errors.append(f"{label}: sequence_contract requires tag_sequence evidence")
        return
    if status_of(verdict.get("tag_sequence")) not in VALID_STATUSES:
        errors.append(f"{label}: sequence_contract requires tag_sequence verdict")
    if not isinstance(sequence.get("actual_order"), list):
        errors.append(f"{label}: tag_sequence requires actual_order")
    if not _is_nonempty_string(sequence.get("evidence_id")):
        errors.append(f"{label}: tag_sequence requires evidence_id")
    if status_of(verdict.get("tag_sequence")) == "PASS" and isinstance(
        sequence.get("actual_order"), list
    ):
        exact = sequence_contract.get("allow_additional_steps") is not True
        sequence_matches = (
            sequence_contract["expected_order"] == sequence["actual_order"]
            if exact
            else _ordered_subset(sequence_contract["expected_order"], sequence["actual_order"])
        )
        if not sequence_matches:
            errors.append(f"{label}: PASS tag sequence contradicts expected order")


def _parse_consent_state(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    if isinstance(value, str):
        parsed: dict[str, str] = {}
        for part in value.split(","):
            if "=" not in part:
                return None
            key, item = part.split("=", 1)
            parsed[key.strip()] = item.strip()
        return parsed
    return None


def _validate_consent_details(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    contract = expectation.get("consent_contract")
    consent = requirement.get("consent")
    if contract is None:
        return
    if not isinstance(contract, dict):
        errors.append(f"{label}: consent_contract must be an object")
        return
    consent_status = status_of(verdict.get("consent"))
    if consent_status not in VALID_STATUSES:
        errors.append(f"{label}: consent_contract requires consent verdict")
    if contract.get("mode") not in CONSENT_MODES:
        errors.append(f"{label}: consent_contract requires a supported mode")
    if not isinstance(consent, dict) or consent.get("applicable") is not True:
        errors.append(f"{label}: consent_contract requires applicable consent evidence")
        return
    expected_signals = _parse_consent_state(contract.get("signals"))
    actual_signals = _parse_consent_state(consent.get("state_at_event"))
    if expected_signals is None:
        errors.append(f"{label}: consent_contract.signals must be an object")
        expected_signals = {}
    if actual_signals is None:
        errors.append(f"{label}: consent state_at_event must be an object")
        actual_signals = {}
    if contract.get("mode") == "advanced_v2" and set(expected_signals) != CONSENT_SIGNALS:
        errors.append(
            f"{label}: advanced_v2 consent contract must declare all four consent signals"
        )
    for signal, value in {**expected_signals, **actual_signals}.items():
        if signal not in CONSENT_SIGNALS:
            errors.append(f"{label}: unsupported consent signal '{signal}'")
        if value not in CONSENT_VALUES:
            errors.append(f"{label}: consent signal '{signal}' must be granted or denied")
    transport = contract.get("transport_mode")
    if transport not in (None, "") and transport not in TRANSPORT_MODES:
        errors.append(f"{label}: invalid expected consent transport_mode")
    if consent.get("transport_mode") not in (None, "", *TRANSPORT_MODES):
        errors.append(f"{label}: invalid observed consent transport_mode")
    checks = consent.get("tag_consent_checks", [])
    if not isinstance(checks, list):
        errors.append(f"{label}: tag_consent_checks must be an array")
        checks = []
    if contract.get("tag_checks_applicable", True) is True and not checks:
        errors.append(f"{label}: consent_contract requires tag_consent_checks")
    check_types: list[str] = []
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            errors.append(f"{label}: tag consent check {index} must be an object")
            continue
        for field in ("consent_type", "expected", "actual", "status"):
            if field not in check:
                errors.append(f"{label}: tag consent check {index} missing '{field}'")
        consent_type = str(check.get("consent_type", "")).strip()
        check_types.append(consent_type)
        expected = check.get("expected")
        actual = check.get("actual")
        if not consent_type:
            errors.append(f"{label}: tag consent check {index} missing consent_type")
        if expected not in CONSENT_VALUES or actual not in CONSENT_VALUES:
            errors.append(
                f"{label}: tag consent check {consent_type or index} must use granted/denied values"
            )
        computed_status = "PASS" if _strict_equal(actual, expected) else "FAIL"
        if status_of(check.get("status")) != computed_status:
            errors.append(
                f"{label}: tag consent check {consent_type or index} status differs "
                "from expected/actual values"
            )
    if len(set(check_types)) != len(check_types):
        errors.append(f"{label}: tag_consent_checks contains duplicate consent_type values")
    required_check_types = contract.get("required_tag_consent_types")
    if required_check_types is not None:
        if not isinstance(required_check_types, list) or not required_check_types:
            errors.append(f"{label}: required_tag_consent_types must be a non-empty array")
        elif set(map(str, required_check_types)) != set(check_types):
            errors.append(
                f"{label}: tag_consent_checks do not exactly match required consent types"
            )
    if consent_status == "PASS":
        if any(actual_signals.get(key) != value for key, value in expected_signals.items()):
            errors.append(f"{label}: PASS consent state differs from consent_contract")
        for field in ("transport_mode", "ads_data_redaction", "url_passthrough"):
            if field in contract and consent.get(field) != contract.get(field):
                errors.append(f"{label}: PASS consent {field} differs from consent_contract")
        transition = contract.get("transition")
        if transition is not None and consent.get("transition") != transition:
            errors.append(f"{label}: PASS consent transition differs from consent_contract")
        if any(status_of(check.get("status")) != "PASS" for check in checks):
            errors.append(f"{label}: PASS consent contradicts a tag consent check")


def _validate_business_rule_results(
    requirement: dict[str, Any],
    computed: list[dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    rules = expectation.get("business_rules")
    results = requirement.get("business_rule_results")
    verdict = requirement.get("verdict", {})
    if rules is None:
        return
    if not isinstance(rules, list) or not rules:
        errors.append(f"{label}: business_rules must be a non-empty array")
        return
    rule_ids: list[str] = []
    for index, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            errors.append(f"{label}: business rule {index} must be an object")
            continue
        rule_id = str(rule.get("rule_id", "")).strip()
        rule_ids.append(rule_id)
        if not rule_id:
            errors.append(f"{label}: business rule {index} missing rule_id")
        operator = rule.get("operator")
        if operator not in BUSINESS_RULE_OPERATORS:
            errors.append(f"{label}: business rule {rule_id or index} has unsupported operator")
            continue
        required_fields = {
            "equals_path": ("left_path", "right_path"),
            "sum_product_equals": ("target_path", "items_path"),
            "all_items_equal": ("items_path", "item_field", "expected_path"),
            "implies": ("if", "then"),
            "unique_across_requirements": ("path",),
            "range": ("path",),
            "format": ("path", "format"),
            "regex": ("path", "pattern"),
        }[operator]
        for field in required_fields:
            if field not in rule or rule.get(field) in ("", None):
                errors.append(f"{label}: business rule {rule_id or index} missing '{field}'")
        path_fields = {
            "equals_path": ("left_path", "right_path"),
            "sum_product_equals": ("target_path", "items_path"),
            "all_items_equal": ("items_path", "expected_path"),
            "unique_across_requirements": ("path",),
            "range": ("path",),
            "format": ("path",),
            "regex": ("path",),
        }.get(operator, ())
        for field in path_fields:
            if rule.get(field) not in ("", None) and not valid_path(rule.get(field)):
                errors.append(
                    f"{label}: business rule {rule_id or index} has invalid path syntax "
                    f"in '{field}'"
                )
        if operator == "sum_product_equals":
            tolerance = rule.get("tolerance", 0)
            if (
                not isinstance(tolerance, (int, float))
                or isinstance(tolerance, bool)
                or tolerance < 0
            ):
                errors.append(
                    f"{label}: business rule {rule_id or index} tolerance must be "
                    "a non-negative number"
                )
        if operator == "range":
            bounds = [rule.get(field) for field in ("min", "max") if field in rule]
            if not bounds or any(
                not isinstance(value, (int, float)) or isinstance(value, bool) for value in bounds
            ):
                errors.append(
                    f"{label}: business rule {rule_id or index} range requires numeric bounds"
                )
        if operator == "format" and rule.get("format") not in FORMATS:
            errors.append(f"{label}: business rule {rule_id or index} has unsupported format")
        if operator == "regex":
            try:
                re.compile(str(rule.get("pattern", "")))
            except re.error:
                errors.append(
                    f"{label}: business rule {rule_id or index} has invalid regular expression"
                )
        if operator == "implies" and (
            not isinstance(rule.get("if"), dict) or not isinstance(rule.get("then"), dict)
        ):
            errors.append(
                f"{label}: business rule {rule_id or index} implies requires object conditions"
            )
        elif operator == "implies":
            for branch in ("if", "then"):
                condition = rule[branch]
                if not valid_path(condition.get("path")):
                    errors.append(
                        f"{label}: business rule {rule_id or index} has invalid path syntax "
                        f"in '{branch}.path'"
                    )
    if len(set(rule_ids)) != len(rule_ids):
        errors.append(f"{label}: business_rules contains duplicate rule_id values")
    if expects_absence(expectation):
        if results not in (None, []):
            errors.append(
                f"{label}: expected absence must not retain payload business_rule_results"
            )
        if status_of(verdict.get("business_rule")) in VALID_STATUSES:
            errors.append(
                f"{label}: expected absence must not retain a payload business_rule verdict"
            )
        return
    if not isinstance(results, list):
        errors.append(f"{label}: declared business_rules require business_rule_results")
        return
    result_by_id: dict[str, dict[str, Any]] = {}
    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            errors.append(f"{label}: business rule result {index} must be an object")
            continue
        result_id = str(result.get("rule_id", "")).strip()
        if not result_id:
            errors.append(f"{label}: business rule result {index} missing rule_id")
        if result_id in result_by_id:
            errors.append(f"{label}: business_rule_results contains duplicate rule_id values")
        result_by_id[result_id] = result
        if status_of(result.get("status")) not in VALID_STATUSES:
            errors.append(f"{label}: business rule result {result_id or index} invalid status")
        if not _is_nonempty_string(result.get("evidence_id")):
            errors.append(f"{label}: business rule result {result_id or index} missing evidence_id")
    if set(result_by_id) != set(rule_ids):
        errors.append(f"{label}: business_rule_results do not exactly match declared rules")
    computed_by_id = {str(item.get("rule_id")): item for item in computed}
    for rule_id, result in result_by_id.items():
        expected_status = status_of(computed_by_id.get(rule_id, {}).get("status"))
        actual_status = status_of(result.get("status"))
        if expected_status not in {"PASS", "FAIL", "REVIEW"}:
            errors.append(
                f"{label}: business rule {rule_id} could not be deterministically evaluated"
            )
        elif expected_status != actual_status:
            errors.append(
                f"{label}: business rule result {rule_id} contradicts deterministic evaluation"
            )
        computed_source = computed_by_id.get(rule_id, {}).get("evaluation_source")
        supplied_source = result.get("evaluation_source")
        if supplied_source not in (None, "") and supplied_source != computed_source:
            errors.append(
                f"{label}: business rule result {rule_id} evaluation_source differs "
                "from deterministic evaluation"
            )
    component = status_of(verdict.get("business_rule"))
    result_statuses = [status_of(item.get("status")) for item in result_by_id.values()]
    if component not in VALID_STATUSES:
        errors.append(f"{label}: declared business_rules require business_rule verdict")
    elif result_statuses and component != worst_status(result_statuses):
        errors.append(f"{label}: verdict.business_rule differs from worst rule result")


def _validate_sensitive_data(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
    *,
    required: bool,
) -> None:
    expectation = requirement.get("expectation", {})
    policy = expectation.get("sensitive_data_policy")
    scan = requirement.get("sensitive_data_scan")
    verdict = requirement.get("verdict", {})
    if policy is None:
        if required:
            errors.append(f"{label}: sensitive_data_scan layer requires sensitive_data_policy")
        return
    if not isinstance(policy, dict):
        errors.append(f"{label}: sensitive_data_policy must be an object")
        return
    forbidden = policy.get("forbidden_categories", DEFAULT_FORBIDDEN_CATEGORIES)
    if not isinstance(forbidden, list) or not forbidden:
        errors.append(f"{label}: forbidden_categories must be an array")
    elif any(str(item) not in SENSITIVE_CATEGORIES for item in forbidden):
        errors.append(f"{label}: forbidden_categories contains unsupported categories")
    if not isinstance(policy.get("allowlisted_paths", []), list):
        errors.append(f"{label}: allowlisted_paths must be an array")
    for field in ("scan_unkeyed_phone_values", "scan_unkeyed_ip_values"):
        if field in policy and not isinstance(policy.get(field), bool):
            errors.append(f"{label}: {field} must be boolean")
    custom_patterns = policy.get("custom_patterns", [])
    if not isinstance(custom_patterns, list):
        errors.append(f"{label}: custom_patterns must be an array")
    else:
        pattern_ids: list[str] = []
        for index, custom in enumerate(custom_patterns, start=1):
            if not isinstance(custom, dict):
                errors.append(f"{label}: custom pattern {index} must be an object")
                continue
            for field in ("pattern_id", "pattern", "category", "confidence"):
                if not _is_nonempty_string(custom.get(field)):
                    errors.append(f"{label}: custom pattern {index} missing '{field}'")
            pattern_id = str(custom.get("pattern_id", "")).strip()
            pattern_ids.append(pattern_id)
            if custom.get("category") != "custom":
                errors.append(
                    f"{label}: custom pattern {pattern_id or index} category must be custom"
                )
            if custom.get("confidence") not in {"confirmed", "suspected"}:
                errors.append(
                    f"{label}: custom pattern {pattern_id or index} has invalid confidence"
                )
            try:
                re.compile(str(custom.get("pattern", "")))
            except re.error:
                errors.append(
                    f"{label}: custom pattern {pattern_id or index} has invalid regular expression"
                )
        if len(set(pattern_ids)) != len(pattern_ids):
            errors.append(f"{label}: custom_patterns contains duplicate pattern_id values")
    if not isinstance(scan, dict) or scan.get("applicable") is not True:
        errors.append(f"{label}: sensitive_data_policy requires sensitive_data_scan")
        return
    scanned_targets = scan.get("scanned_targets")
    if not isinstance(scanned_targets, list) or not scanned_targets:
        errors.append(f"{label}: sensitive_data_scan requires scanned_targets")
    else:
        expected_targets = set(requirement_sensitive_targets(requirement))
        if (
            len(scanned_targets) != len(set(map(str, scanned_targets)))
            or set(map(str, scanned_targets)) != expected_targets
        ):
            errors.append(
                f"{label}: sensitive_data_scan.scanned_targets must exactly cover "
                "client-side sensitive surfaces"
            )
    if not _is_nonempty_string(scan.get("evidence_id")):
        errors.append(f"{label}: sensitive_data_scan requires evidence_id")
    findings = scan.get("findings")
    if not isinstance(findings, list):
        errors.append(f"{label}: sensitive_data_scan.findings must be an array")
        findings = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            errors.append(f"{label}: sensitive finding {index} must be an object")
            continue
        if any(field in finding for field in ("value", "raw_value", "sample")):
            errors.append(f"{label}: sensitive finding {index} must not retain an unredacted value")
        for field in (
            "path",
            "category",
            "confidence",
            "allowlisted",
            "status",
            "redacted_value",
            "value_fingerprint",
        ):
            if field not in finding:
                errors.append(f"{label}: sensitive finding {index} missing '{field}'")
    computed = scan_requirement_sensitive_data(requirement, policy)
    if findings != computed:
        errors.append(f"{label}: sensitive_data_scan differs from deterministic scan")
    scan_status = status_of(scan.get("status"))
    computed_status = worst_status(item["status"] for item in computed) if computed else "PASS"
    if scan_status != computed_status:
        errors.append(f"{label}: sensitive_data_scan.status differs from its findings")
    if computed_status in {"FAIL", "REVIEW"}:
        errors.append(
            f"{label}: unallowlisted sensitive content remains in normalized evidence; "
            "quarantine/redact it before workbook generation"
        )
    if status_of(verdict.get("sensitive_data")) not in VALID_STATUSES:
        errors.append(f"{label}: sensitive_data_policy requires sensitive_data verdict")
    elif status_of(verdict.get("sensitive_data")) != scan_status:
        errors.append(f"{label}: verdict.sensitive_data differs from scan status")


def _client_check_matches(check: dict[str, Any]) -> bool | None:
    comparison = check.get("comparison", "equals")
    expected = check.get("expected")
    actual = check.get("actual")
    if comparison == "equals":
        return _strict_equal(actual, expected)
    if comparison == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected in actual
        if isinstance(actual, list):
            return any(_strict_equal(item, expected) for item in actual)
        if isinstance(actual, dict):
            return expected in actual
        return False
    if comparison == "present":
        return actual not in (None, "", [], {})
    if comparison == "absent":
        return actual in (None, "", [], {})
    if comparison == "regex":
        try:
            return isinstance(actual, str) and re.fullmatch(str(expected), actual) is not None
        except re.error:
            return None
    if comparison == "ordered":
        return isinstance(expected, list) and isinstance(actual, list) and expected == actual
    if comparison == "maximum":
        return (
            isinstance(expected, (int, float))
            and not isinstance(expected, bool)
            and isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and actual <= expected
        )
    if comparison == "warning_only":
        return None
    return None


def _validate_client_checks(
    requirement: dict[str, Any],
    run: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    checks = requirement.get("client_checks")
    verdict = requirement.get("verdict", {})
    if checks is None:
        return
    if not isinstance(checks, list):
        errors.append(f"{label}: client_checks must be an array")
        return
    context_ids = {
        str(item.get("context_id"))
        for item in run.get("browser_contexts", [])
        if isinstance(item, dict)
    }
    statuses: list[str] = []
    check_ids: list[str] = []
    for index, check in enumerate(checks, start=1):
        if not isinstance(check, dict):
            errors.append(f"{label}: client check {index} must be an object")
            continue
        check_id = str(check.get("check_id", "")).strip()
        check_ids.append(check_id)
        for field in (
            "check_id",
            "category",
            "comparison",
            "expected",
            "actual",
            "status",
            "evidence_id",
        ):
            if field not in check:
                errors.append(f"{label}: client check {index} missing '{field}'")
        if check.get("category") not in CLIENT_CHECK_CATEGORIES:
            errors.append(f"{label}: client check {check_id or index} invalid category")
        if check.get("comparison") not in CLIENT_CHECK_COMPARISONS:
            errors.append(f"{label}: client check {check_id or index} invalid comparison")
        check_status = status_of(check.get("status"))
        if check_status not in VALID_STATUSES:
            errors.append(f"{label}: client check {check_id or index} invalid status")
        else:
            statuses.append(check_status)
        if check.get("context_id") and str(check.get("context_id")) not in context_ids:
            errors.append(f"{label}: client check {check_id or index} unknown context_id")
        if check.get("category") == "client_limit" and not _is_nonempty_string(
            check.get("limit_source")
        ):
            errors.append(f"{label}: client_limit check requires current limit_source")
        if not _is_nonempty_string(check.get("evidence_id")):
            errors.append(f"{label}: client check {check_id or index} missing evidence_id")
        computed_match = _client_check_matches(check)
        expected_status = (
            "PASS" if computed_match is True else "FAIL" if computed_match is False else "REVIEW"
        )
        if check_status in VALID_STATUSES and check_status != expected_status:
            errors.append(f"{label}: client check {check_id or index} status contradicts evidence")
    if len(set(check_ids)) != len(check_ids):
        errors.append(f"{label}: client_checks contains duplicate check_id values")
    component = status_of(verdict.get("client_checks"))
    if checks and component not in VALID_STATUSES:
        errors.append(f"{label}: supplied client_checks require client_checks verdict")
    elif component and statuses and component != worst_status(statuses):
        errors.append(f"{label}: verdict.client_checks differs from worst client check")


def _validate_regression(
    requirement: dict[str, Any],
    acceptance_status: str,
    regression_context: dict[str, Any] | None,
    label: str,
    errors: list[str],
) -> None:
    regression = requirement.get("regression")
    verdict = requirement.get("verdict", {})
    if regression is None:
        if regression_context is not None:
            errors.append(
                f"{label}: run regression_context requires requirement regression evidence"
            )
        return
    if not isinstance(regression, dict) or regression.get("applicable") is not True:
        errors.append(f"{label}: supplied regression evidence must be applicable")
        return
    for field in (
        "baseline_run_id",
        "baseline_status",
        "current_status",
        "change",
        "evidence_id",
    ):
        if field not in regression or regression.get(field) in ("", None):
            errors.append(f"{label}: regression missing '{field}'")
    baseline = status_of(regression.get("baseline_status"))
    current = status_of(regression.get("current_status"))
    if regression_context is not None and regression.get(
        "baseline_run_id"
    ) != regression_context.get("baseline_run_id"):
        errors.append(f"{label}: regression baseline_run_id differs from run context")
    if baseline not in VALID_STATUSES or current not in VALID_STATUSES:
        errors.append(f"{label}: regression statuses must use recette statuses")
    if current != acceptance_status:
        errors.append(f"{label}: regression current_status differs from current acceptance status")
    expected_change = (
        "UNCHANGED"
        if baseline == current
        else "REGRESSED"
        if baseline == "PASS" and current == "FAIL"
        else "UNVERIFIED"
        if baseline == "PASS" and current in {"BLOCKED", "REVIEW", "NOT_TESTED"}
        else "IMPROVED"
        if baseline != "PASS" and current == "PASS"
        else "CHANGED"
    )
    if regression.get("change") != expected_change:
        errors.append(f"{label}: regression change classification is inconsistent")
    component = status_of(verdict.get("regression"))
    expected_component = (
        "FAIL"
        if expected_change == "REGRESSED"
        else "REVIEW"
        if expected_change == "UNVERIFIED"
        else "PASS"
    )
    if component != expected_component:
        errors.append(f"{label}: verdict.regression differs from regression classification")


def semantic_errors(data: dict[str, Any]) -> list[str]:
    """Return every structural and semantic validation error."""
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        return [
            "schema_version must be 2; schema-v1 or observation-only results must be "
            "re-normalized from source evidence into the schema-v2 requirement model"
        ]

    run = data.get("run")
    if not isinstance(run, dict):
        return ["run must be an object"]
    if "run_type" in run:
        errors.append(
            "run: run_type is obsolete; use one recette workflow and describe "
            "applicability in acceptance_scope and included_layers"
        )
    for field in (
        "run_id",
        "report_title",
        "site_url",
        "environment",
        "environment_class",
        "container_id",
        "workspace",
        "tracking_plan_source",
        "acceptance_scope",
        "executed_at",
    ):
        if not _is_nonempty_string(run.get(field)):
            errors.append(f"run: missing required field '{field}'")
    if run.get("environment_class") not in {"test", "preprod", "staging", "production"}:
        errors.append("run: environment_class must be test, preprod, staging, or production")
    _validate_run_client_context(run, errors)
    if "observation-only" in (
        f"{run.get('tracking_plan_source', '')} {run.get('acceptance_scope', '')}".lower()
    ):
        errors.append("run: observation-only mode is not an acceptance recette")

    included_layers = run.get("included_layers")
    if not isinstance(included_layers, list) or not included_layers:
        errors.append("run: recette requires non-empty included_layers")
        included_layers = []
    active_layers = set(included_layers) if isinstance(included_layers, list) else set()
    supported_layers = BASE_LAYERS | CLIENT_SIDE_OPTIONAL_LAYERS
    unknown_layers = sorted(active_layers - supported_layers)
    if unknown_layers:
        errors.append("run: unsupported included_layers " + ", ".join(unknown_layers))

    try:
        requirements = as_rows(data.get("requirements"), "requirements")
        unexpected = as_rows(data.get("unexpected"), "unexpected")
        blockers_rows = as_rows(data.get("blockers"), "blockers")
        evidence = as_rows(data.get("evidence"), "evidence")
    except ReportValidationError as exc:
        return errors + [str(exc)]
    if not requirements:
        errors.append("requirements: at least one source-bound requirement is required")
    if not evidence:
        errors.append("evidence: at least one evidence row is required")

    declared_client_layers = set(
        applicable_layers(
            requirements,
            container_count=(
                len(run["containers"]) if isinstance(run.get("containers"), list) else 1
            ),
        )
    )
    if any(
        isinstance(requirement.get("destination_request"), dict) for requirement in requirements
    ):
        declared_client_layers.add("destination_request_when_applicable")
    if run.get("regression_context") is not None:
        declared_client_layers.add("regression_when_baseline_provided")
    missing_declared_layers = sorted(declared_client_layers - active_layers)
    if missing_declared_layers:
        errors.append(
            "run: included_layers omits declared client-side layers "
            + ", ".join(missing_declared_layers)
        )

    evidence_catalog = [str(row.get("evidence_id", "")).strip() for row in evidence]
    empty_evidence_rows = [
        index for index, value in enumerate(evidence_catalog, start=1) if not value
    ]
    for index in empty_evidence_rows:
        errors.append(f"evidence row {index}: missing evidence_id")
    for index, row in enumerate(evidence, start=1):
        evidence_label = str(row.get("evidence_id", "")).strip() or str(index)
        for field in ("kind", "source", "path_or_url", "captured_at", "description"):
            if not _is_nonempty_string(row.get(field)):
                errors.append(f"evidence {evidence_label}: missing provenance field '{field}'")
        kind = row.get("kind")
        source_name = row.get("source")
        if kind not in EVIDENCE_KIND_SOURCES:
            errors.append(f"evidence {evidence_label}: unsupported evidence kind")
        elif source_name not in EVIDENCE_KIND_SOURCES[kind]:
            errors.append(f"evidence {evidence_label}: source is incompatible with kind '{kind}'")
        capture_mode = row.get("capture_mode")
        if capture_mode not in CAPTURE_MODES:
            errors.append(
                f"evidence {evidence_label}: capture_mode must identify direct, "
                "deterministic, analyst_supplied, or supplemental evidence"
            )
        if kind in DIRECT_CAPTURE_KINDS and capture_mode != "direct":
            errors.append(
                f"evidence {evidence_label}: browser/Preview evidence must be a "
                "direct structured capture, not reconstructed or inferred"
            )
        if kind in DETERMINISTIC_CAPTURE_KINDS and capture_mode != "deterministic":
            errors.append(
                f"evidence {evidence_label}: validator evidence requires capture_mode=deterministic"
            )
        if kind in ANALYST_CAPTURE_KINDS and capture_mode not in {
            "analyst_supplied",
            "direct",
        }:
            errors.append(
                f"evidence {evidence_label}: analyst evidence requires "
                "capture_mode=analyst_supplied or direct"
            )
        if kind in ACTION_BOUND_EVIDENCE_KINDS and not _is_nonempty_string(row.get("action_id")):
            errors.append(f"evidence {evidence_label}: direct action evidence requires action_id")
        if kind in EVENT_INDEX_EVIDENCE_KINDS and (
            not isinstance(row.get("event_index"), int) or isinstance(row.get("event_index"), bool)
        ):
            errors.append(f"evidence {evidence_label}: direct event evidence requires event_index")
        if kind in CONTAINER_BOUND_EVIDENCE_KINDS and not _is_nonempty_string(
            row.get("container_id")
        ):
            errors.append(f"evidence {evidence_label}: direct GTM evidence requires container_id")
        if kind in {"tag_configuration", "tag_runtime"}:
            for link_field in ("tag_name", "configuration_field"):
                if not _is_nonempty_string(row.get(link_field)):
                    errors.append(f"evidence {evidence_label}: tag evidence requires {link_field}")
        if kind == "tag_configuration" and source_name == "Tag Assistant":
            if not _is_nonempty_string(row.get("action_id")):
                errors.append(
                    f"evidence {evidence_label}: Tag Assistant configuration requires action_id"
                )
            if not isinstance(row.get("event_index"), int):
                errors.append(
                    f"evidence {evidence_label}: Tag Assistant configuration requires event_index"
                )
        if kind == "browser_network_request" and not _is_nonempty_string(row.get("request_id")):
            errors.append(
                f"evidence {evidence_label}: browser request evidence requires request_id"
            )
        captured_at = row.get("captured_at")
        if _is_nonempty_string(captured_at):
            try:
                parsed_captured_at = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"evidence {evidence_label}: captured_at must be ISO 8601")
            else:
                if parsed_captured_at.tzinfo is None:
                    errors.append(f"evidence {evidence_label}: captured_at must include timezone")
        if _contains_placeholder(row):
            errors.append(f"evidence {evidence_label}: provenance contains placeholder content")
        provenance_findings = scan_sensitive_value(
            {
                "source": row.get("source"),
                "source_detail": row.get("source_detail"),
                "path_or_url": row.get("path_or_url"),
                "description": row.get("description"),
            },
            root_path=f"evidence.{evidence_label}",
            policy={"forbidden_categories": DEFAULT_FORBIDDEN_CATEGORIES},
        )
        if any(
            status_of(finding.get("status")) in {"FAIL", "REVIEW"}
            for finding in provenance_findings
        ):
            errors.append(
                f"evidence {evidence_label}: provenance contains sensitive content; "
                "retain only a redacted description/path"
            )
    duplicate_evidence = sorted(
        item
        for item, count in Counter(item for item in evidence_catalog if item).items()
        if count > 1
    )
    if duplicate_evidence:
        errors.append("evidence: duplicate IDs " + ", ".join(duplicate_evidence))
    known_evidence = {item for item in evidence_catalog if item}
    evidence_by_id = {
        str(row.get("evidence_id", "")).strip(): row
        for row in evidence
        if str(row.get("evidence_id", "")).strip()
    }
    regression_context = run.get("regression_context")
    if regression_context is not None:
        if not isinstance(regression_context, dict):
            errors.append("run: regression_context must be an object")
        else:
            for field in ("baseline_source", "baseline_run_id"):
                if not _is_nonempty_string(regression_context.get(field)):
                    errors.append(f"run: regression_context missing '{field}'")
            changes = regression_context.get("acceptance_relevant_container_changes", [])
            if not isinstance(changes, list):
                errors.append("run: acceptance_relevant_container_changes must be an array")
            for ref in evidence_ids(regression_context.get("evidence_ids")):
                if ref not in known_evidence:
                    errors.append(f"run: regression_context references unknown evidence ID '{ref}'")
                else:
                    _require_evidence_kind(
                        evidence_by_id,
                        ref,
                        {"previous_run_comparison"},
                        "run.regression_context",
                        errors,
                    )

    blockers: dict[str, dict[str, Any]] = {}
    for index, blocker in enumerate(blockers_rows, start=1):
        blocker_id = str(blocker.get("blocker_id", "")).strip()
        if not blocker_id:
            errors.append(f"blockers row {index}: missing blocker_id")
            continue
        if blocker_id in blockers:
            errors.append(f"blockers: duplicate blocker_id '{blocker_id}'")
        blockers[blocker_id] = blocker
        blocker_status = status_of(blocker)
        if blocker_status not in {"PASS", "BLOCKED"}:
            errors.append(f"blocker {blocker_id}: status must be PASS or BLOCKED")
        refs = evidence_ids(blocker.get("evidence_ids"))
        if not refs:
            errors.append(f"blocker {blocker_id}: missing evidence_ids")
        unknown = sorted(set(refs) - known_evidence)
        if unknown:
            errors.append(f"blocker {blocker_id}: unknown evidence IDs {', '.join(unknown)}")
        if blocker.get("type") in PROTECTED_BLOCKERS:
            if blocker.get("analyst_intervention_required") is not True:
                errors.append(
                    f"blocker {blocker_id}: protected checkpoint must be analyst-controlled"
                )
            if blocker_status == "BLOCKED" and blocker.get("analyst_help_requested") is not True:
                errors.append(
                    f"blocker {blocker_id}: analyst help must be requested before final BLOCKED"
                )

    requirement_ids = [str(row.get("requirement_id", "")).strip() for row in requirements]
    duplicate_requirements = sorted(
        item
        for item, count in Counter(item for item in requirement_ids if item).items()
        if count > 1
    )
    if duplicate_requirements:
        errors.append("requirements: duplicate IDs " + ", ".join(duplicate_requirements))
    inventory = run.get("requirement_inventory")
    if not isinstance(inventory, list) or not inventory:
        errors.append("run: requirement_inventory is required")
        inventory = []
    normalized_inventory = [str(item).strip() for item in inventory]
    if len(set(normalized_inventory)) != len(normalized_inventory):
        errors.append("run: requirement_inventory contains duplicate IDs")
    if set(normalized_inventory) != {item for item in requirement_ids if item}:
        errors.append("run: requirement_inventory does not exactly match normalized requirements")

    event_inventory = run.get("event_inventory")
    if not isinstance(event_inventory, list) or not event_inventory:
        errors.append("run: event_inventory is required")
        event_inventory = []
    event_group_ids: list[str] = []
    prior_order: int | float | None = None
    for index, item in enumerate(event_inventory, start=1):
        if not isinstance(item, dict):
            errors.append(f"run: event_inventory row {index} must be an object")
            continue
        group_id = str(item.get("event_group_id", "")).strip()
        if not group_id:
            errors.append(f"run: event_inventory row {index} missing event_group_id")
        event_group_ids.append(group_id)
        order = item.get("plan_order")
        if not isinstance(order, (int, float)):
            errors.append(f"run: event_inventory row {index} missing numeric plan_order")
        elif prior_order is not None and order <= prior_order:
            errors.append("run: event_inventory is not in strictly increasing plan order")
        prior_order = order if isinstance(order, (int, float)) else prior_order
        if not _is_nonempty_string(item.get("event_name")):
            errors.append(f"run: event_inventory row {index} missing event_name")
    if len(set(event_group_ids)) != len(event_group_ids):
        errors.append("run: event_inventory contains duplicate event_group_id values")

    requirement_group_ids = {
        str(requirement.get("event_group_id", "")).strip() for requirement in requirements
    }
    if set(event_group_ids) != requirement_group_ids:
        errors.append("run: event_inventory does not exactly match requirement event groups")

    computed_business_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for result in evaluate_report_business_rules(data):
        computed_business_by_requirement.setdefault(
            str(result.get("requirement_id", "")), []
        ).append(result)
    container_ids = {
        str(item.get("container_id"))
        for item in run.get("containers", [])
        if isinstance(item, dict)
    } or {str(run.get("container_id", ""))}
    browser_context_ids = {
        str(item.get("context_id"))
        for item in run.get("browser_contexts", [])
        if isinstance(item, dict)
    }

    prior_requirement_order: int | float | None = None
    sorted_ids: list[str] = []
    sortable_requirements: list[tuple[float, str]] = []
    for index, requirement in enumerate(requirements, start=1):
        requirement_id = str(requirement.get("requirement_id", "")).strip()
        label = f"requirement {requirement_id or index}"
        if not requirement_id:
            errors.append(f"requirements row {index}: missing requirement_id")
        event_group_id = str(requirement.get("event_group_id", "")).strip()
        if not event_group_id:
            errors.append(f"{label}: missing event_group_id")
        scope_status = str(requirement.get("scope_status", "")).strip()
        if scope_status not in SCOPE_STATUSES:
            errors.append(f"{label}: invalid scope_status")

        source = requirement.get("source")
        if not isinstance(source, dict):
            errors.append(f"{label}: missing source object")
            source = {}
        if not _is_nonempty_string(source.get("reference")):
            errors.append(f"{label}: source.reference is required")
        plan_order = source.get("plan_order")
        if not isinstance(plan_order, (int, float)):
            errors.append(f"{label}: source.plan_order must be numeric")
        else:
            sortable_requirements.append((float(plan_order), requirement_id))
            if prior_requirement_order is not None and plan_order <= prior_requirement_order:
                errors.append(f"{label}: requirements are not stored in original plan order")
            prior_requirement_order = plan_order

        journey = requirement.get("journey")
        if not isinstance(journey, dict):
            errors.append(f"{label}: missing journey object")
            journey = {}
        for field in ("journey_id", "step_id", "action", "url", "execution_status"):
            if not _is_nonempty_string(journey.get(field)):
                errors.append(f"{label}: journey missing '{field}'")
        for field in ("action_value", "action_value_type", "action_value_source"):
            if field not in journey:
                errors.append(f"{label}: journey missing '{field}'")
        action_value_source = journey.get("action_value_source")
        action_value_type = journey.get("action_value_type")
        action_value = journey.get("action_value")
        if action_value_source not in ACTION_VALUE_SOURCES:
            errors.append(f"{label}: invalid journey.action_value_source")
        if action_value_type not in VALUE_TYPES:
            errors.append(f"{label}: invalid journey.action_value_type")
        elif js_value_type(action_value) != action_value_type:
            errors.append(f"{label}: journey action value/type mismatch")
        if action_value_source == "not_applicable" and action_value is not None:
            errors.append(f"{label}: not_applicable action value must retain explicit null")
        if (
            action_value_source == "protected_analyst_entry"
            and action_value != "<analyst-entered-protected>"
        ):
            errors.append(f"{label}: protected action value must use the canonical redacted marker")
        if journey.get("execution_status") not in EXECUTION_STATUSES:
            errors.append(f"{label}: invalid journey.execution_status")
        if journey.get("inferred") is True and not _is_nonempty_string(
            journey.get("inference_source")
        ):
            errors.append(f"{label}: inferred journey requires inference_source")
        if not isinstance(journey.get("attempted_routes"), list):
            errors.append(f"{label}: journey.attempted_routes must be an array")
        requirement_container = str(requirement.get("container_id", run.get("container_id", "")))
        if requirement_container not in container_ids:
            errors.append(f"{label}: unknown client-side container_id")
        context_id = str(requirement.get("browser_context_id", "")).strip()
        if context_id and context_id not in browser_context_ids:
            errors.append(f"{label}: unknown browser_context_id")
        if len(browser_context_ids) > 1 and not context_id:
            errors.append(f"{label}: multiple browser contexts require browser_context_id")

        expectation = requirement.get("expectation")
        if not isinstance(expectation, dict):
            errors.append(f"{label}: missing expectation object")
            expectation = {}
        for field in (
            "event_name",
            "field_path",
            "match_rule",
            "expected_type",
        ):
            if not _is_nonempty_string(expectation.get(field)):
                errors.append(f"{label}: expectation missing '{field}'")
        if not isinstance(expectation.get("expected_occurrence"), (str, dict)):
            errors.append(f"{label}: expectation missing 'expected_occurrence'")
        if "expected_value" not in expectation:
            errors.append(f"{label}: expectation must preserve expected_value, including null")
        if expectation.get("match_rule") not in MATCH_RULES:
            errors.append(f"{label}: unsupported match_rule '{expectation.get('match_rule')}'")
        if expectation.get("expected_type") not in VALUE_TYPES:
            errors.append(
                f"{label}: unsupported expected_type '{expectation.get('expected_type')}'"
            )
        if expectation.get("match_rule") == "documented_transform":
            transform = expectation.get("transformation")
            if not isinstance(transform, dict) or not all(
                key in transform for key in ("input_path", "rule", "expected_output")
            ):
                errors.append(f"{label}: documented_transform requires input, rule, and output")
        if expectation.get("match_rule") == "range":
            allowed_range = expectation.get("allowed_range")
            if not isinstance(allowed_range, dict) or not any(
                key in allowed_range for key in ("min", "max")
            ):
                errors.append(f"{label}: range match requires allowed_range min and/or max")
            elif any(
                key in allowed_range
                and (
                    not isinstance(allowed_range[key], (int, float))
                    or isinstance(allowed_range[key], bool)
                )
                for key in ("min", "max")
            ):
                errors.append(f"{label}: range bounds must be numeric")
        if expectation.get("match_rule") == "format" and expectation.get("format") not in FORMATS:
            errors.append(f"{label}: format match requires a supported format")
        if expectation.get("match_rule") == "anti_pattern":
            pattern = expectation.get("pattern")
            if not _is_nonempty_string(pattern):
                errors.append(f"{label}: anti_pattern requires a valid regular expression")
            else:
                try:
                    re.compile(pattern)
                except re.error:
                    errors.append(f"{label}: anti_pattern requires a valid regular expression")
        if expectation.get("match_rule") == "vendor_equivalent" and not _is_nonempty_string(
            expectation.get("vendor_parameter_name")
        ):
            errors.append(f"{label}: vendor_equivalent requires vendor_parameter_name")
        if expectation.get("match_rule") == "business_rule" and not isinstance(
            expectation.get("business_rules"), list
        ):
            errors.append(f"{label}: business_rule match requires business_rules")
        if expectation.get("vendor_family") not in (None, "", *VENDOR_FAMILIES):
            errors.append(f"{label}: unsupported vendor_family")
        if expectation.get("source_mechanism", "data_layer_push") not in SOURCE_MECHANISMS:
            errors.append(f"{label}: unsupported source_mechanism")
        tag_name = expectation.get("tag_name")
        tag_delivery = expectation.get("tag_delivery")
        if _is_nonempty_string(tag_name):
            if tag_delivery not in TAG_DELIVERY_TYPES:
                errors.append(
                    f"{label}: every concerned tag requires tag_delivery="
                    "browser_request or local_only"
                )
            if not _is_nonempty_string(expectation.get("tag_configuration_field")):
                errors.append(f"{label}: concerned tag requires tag_configuration_field")
            if expectation.get("expected_tag_configuration") in (None, ""):
                errors.append(f"{label}: concerned tag requires exact expected_tag_configuration")
            if tag_delivery == "browser_request":
                for field in (
                    "vendor_family",
                    "destination_id",
                    "destination_event_name",
                    "destination_id_parameter_path",
                    "destination_event_parameter_path",
                    "expected_endpoint_pattern",
                    "expected_request_behavior",
                ):
                    if not _is_nonempty_string(expectation.get(field)):
                        errors.append(f"{label}: browser-sending tag requires expectation.{field}")
            elif tag_delivery == "local_only" and is_browser_sending_tag(expectation):
                errors.append(f"{label}: local_only tag cannot declare browser destination fields")
        elif tag_delivery not in (None, ""):
            errors.append(f"{label}: tag_delivery requires a concerned tag_name")

        verdict = requirement.get("verdict")
        if not isinstance(verdict, dict):
            errors.append(f"{label}: missing verdict object")
            verdict = {}
        components = []
        acceptance_components = []
        for field in (
            "event_occurrence",
            "source_signal",
            "raw_payload",
            "resolved_data_layer",
            "gtm_variable",
            "tag_configuration",
            "tag_firing",
            "tag_parameter",
            "destination_request",
            "destination_parameter",
            "trigger_logic",
            "tag_sequence",
            "consent",
            "business_rule",
            "sensitive_data",
            "client_checks",
            "regression",
        ):
            value = verdict.get(field)
            if value in (None, ""):
                continue
            status = status_of(value)
            if status not in VALID_STATUSES:
                errors.append(f"{label}: verdict.{field} has invalid status '{status}'")
            else:
                components.append(status)
                if field != "regression":
                    acceptance_components.append(status)
        overall = status_of(verdict.get("overall"))
        if overall not in VALID_STATUSES:
            errors.append(f"{label}: verdict.overall has invalid status '{overall}'")
        elif components and overall != worst_status(components):
            errors.append(
                f"{label}: overall status '{overall}' does not equal worst applicable "
                f"component '{worst_status(components)}'"
            )
        if "REVIEW" in components or overall == "REVIEW":
            if verdict.get("review_basis") != "semantic_ambiguity":
                errors.append(
                    f"{label}: REVIEW is reserved for semantic ambiguity and requires "
                    "verdict.review_basis=semantic_ambiguity"
                )
            if not _is_nonempty_string(verdict.get("review_question")):
                errors.append(
                    f"{label}: REVIEW requires the precise verdict.review_question "
                    "the analyst must resolve"
                )
        acceptance_status = worst_status(acceptance_components)

        refs = evidence_ids(requirement.get("evidence_ids"))
        if not refs:
            errors.append(f"{label}: missing evidence_ids")
        unknown = sorted(set(refs) - known_evidence)
        if unknown:
            errors.append(f"{label}: unknown evidence IDs {', '.join(unknown)}")
        nested = _nested_ids(requirement)
        if not nested.issubset(set(refs)):
            missing = sorted(nested - set(refs))
            errors.append(
                f"{label}: nested evidence IDs absent from evidence_ids: {', '.join(missing)}"
            )
        _validate_requirement_evidence_kinds(requirement, evidence_by_id, label, errors)

        blocker_id = str(requirement.get("blocker_id", "")).strip()
        if overall == "BLOCKED":
            if not blocker_id or blocker_id not in blockers:
                errors.append(f"{label}: BLOCKED requirement must reference a blocker")
            if journey.get("execution_status") != "BLOCKED":
                errors.append(f"{label}: BLOCKED verdict requires BLOCKED journey execution")
        if overall == "NOT_TESTED":
            if scope_status != "OUT_OF_SCOPE" or journey.get("execution_status") != "NOT_TESTED":
                errors.append(f"{label}: NOT_TESTED is only valid for confirmed OUT_OF_SCOPE work")
            if not _is_nonempty_string(requirement.get("notes")):
                errors.append(f"{label}: NOT_TESTED requires an explicit reason")
        elif scope_status == "OUT_OF_SCOPE":
            errors.append(f"{label}: OUT_OF_SCOPE requirement must use NOT_TESTED")

        observed = requirement.get("event_observed")
        if not isinstance(observed, bool):
            errors.append(f"{label}: event_observed must be true or false")
            observed = False
        _validate_scenario(requirement, label, errors)
        _validate_source_signal(requirement, label, errors)
        if scope_status == "IN_SCOPE" and journey.get("execution_status") in {
            "EXECUTED",
            "BLOCKED",
            "REVIEW",
        }:
            preview_disconnected = (
                overall == "BLOCKED"
                and blocker_id in blockers
                and blockers[blocker_id].get("type") == "PREVIEW_DISCONNECTED"
            )
            _validate_action_boundary(
                requirement.get("action_boundary"),
                label,
                errors,
                observed=observed,
                require_ready=not preview_disconnected,
                require_settled=not preview_disconnected,
            )
            boundary = requirement.get("action_boundary")
            if (
                observed is False
                and status_of(verdict.get("event_occurrence")) == "FAIL"
                and isinstance(boundary, dict)
                and boundary.get("interaction_outcome") in {"failed", "uncertain"}
            ):
                errors.append(
                    f"{label}: failed or uncertain interaction cannot prove expected-event absence"
                )
            _validate_occurrence(requirement, label, errors)
            occurrence = requirement.get("occurrence_evidence")
            if isinstance(boundary, dict) and isinstance(occurrence, dict):
                event_indexes = occurrence.get("event_indexes")
                if isinstance(event_indexes, list) and all(
                    isinstance(item, int) and not isinstance(item, bool) for item in event_indexes
                ):
                    last_event = boundary.get("last_event_before")
                    first_event = boundary.get("first_event_after")
                    settled_event = boundary.get("settled_final_event")
                    if isinstance(last_event, int) and any(
                        item <= last_event for item in event_indexes
                    ):
                        errors.append(
                            f"{label}: occurrence event index does not follow last_event_before"
                        )
                    if isinstance(first_event, int) and any(
                        item < first_event for item in event_indexes
                    ):
                        errors.append(f"{label}: occurrence event index precedes first_event_after")
                    if isinstance(settled_event, int) and any(
                        item > settled_event for item in event_indexes
                    ):
                        errors.append(
                            f"{label}: occurrence event index exceeds settled_final_event"
                        )
                anchor_index = occurrence.get("anchor_event_index")
                if (
                    isinstance(anchor_index, int)
                    and isinstance(boundary.get("settled_final_event"), int)
                    and anchor_index > boundary["settled_final_event"]
                ):
                    errors.append(f"{label}: anchor_event_index exceeds settled_final_event")

        if observed:
            source_mechanism = expectation.get("source_mechanism", "data_layer_push")
            raw_required = source_mechanism == "data_layer_push" and "raw_api_call" in active_layers
            resolved_applicable = expectation.get(
                "resolved_data_layer_applicable",
                source_mechanism in {"data_layer_push", "gtm_native_event", "gtm_auto_event"},
            )
            resolved_required = resolved_applicable and "resolved_data_layer" in active_layers
            raw = requirement.get("raw_api_call")
            resolved = requirement.get("resolved_data_layer")
            if raw_required:
                if status_of(verdict.get("raw_payload")) not in VALID_STATUSES:
                    errors.append(
                        f"{label}: required raw API-call layer requires raw_payload verdict"
                    )
                _validate_observation(
                    raw,
                    f"{label}.raw_api_call",
                    errors,
                    require_payload=True,
                )
                if isinstance(raw, dict) and raw.get("capture_source") not in RAW_SOURCES:
                    errors.append(f"{label}: invalid raw capture_source")
                if (
                    isinstance(raw, dict)
                    and raw.get("capture_source") != "tag_assistant_api_call"
                    and (
                        resolved_required
                        or bool(expectation.get("variable_name"))
                        or bool(expectation.get("tag_name"))
                        or bool(expectation.get("tag_configuration_field"))
                    )
                ):
                    errors.append(
                        f"{label}: Preview-dependent evidence requires exact "
                        "Tag Assistant API Call evidence"
                    )
                if isinstance(raw, dict) and status_of(verdict.get("raw_payload")) == "PASS":
                    match = _matches_expectation(expectation, raw)
                    if match is False:
                        errors.append(
                            f"{label}: PASS raw_payload contradicts expected value/type/rule"
                        )
            if resolved_required:
                if status_of(verdict.get("resolved_data_layer")) not in VALID_STATUSES:
                    errors.append(
                        f"{label}: required resolved Data Layer requires "
                        "resolved_data_layer verdict"
                    )
                _validate_observation(
                    resolved,
                    f"{label}.resolved_data_layer",
                    errors,
                )
            if (
                isinstance(raw, dict)
                and isinstance(resolved, dict)
                and status_of(verdict.get("resolved_data_layer")) == "PASS"
                and expectation.get("match_rule") != "documented_transform"
                and (
                    raw.get("field_state") != resolved.get("field_state")
                    or raw.get("field_value") != resolved.get("field_value")
                    or raw.get("field_type") != resolved.get("field_type")
                )
            ):
                errors.append(
                    f"{label}: PASS resolved Data Layer differs from raw value without "
                    "a documented transformation"
                )
        elif overall == "PASS" and not expects_absence(expectation):
            errors.append(f"{label}: PASS requires an observed event or an expected absence")
        elif status_of(verdict.get("event_occurrence")) == "FAIL":
            _validate_action_boundary(
                requirement.get("action_boundary"),
                label,
                errors,
                observed=False,
                require_ready=True,
            )
            source_mechanism = expectation.get("source_mechanism", "data_layer_push")
            downstream_components: list[str] = []
            if source_mechanism == "data_layer_push":
                downstream_components.append("raw_payload")
            else:
                downstream_components.append("source_signal")
            if expectation.get(
                "resolved_data_layer_applicable",
                source_mechanism in {"data_layer_push", "gtm_native_event", "gtm_auto_event"},
            ):
                downstream_components.append("resolved_data_layer")
            if expectation.get("variable_name"):
                downstream_components.append("gtm_variable")
            if expectation.get("expected_tag_configuration") not in (None, ""):
                downstream_components.append("tag_configuration")
            if expectation.get("tag_name"):
                downstream_components.append("tag_firing")
            if expectation.get("tag_configuration_field"):
                downstream_components.append("tag_parameter")
            if expectation.get("expected_request_behavior") not in (None, ""):
                downstream_components.append("destination_request")
            if expectation.get("destination_parameter_path") not in (None, ""):
                downstream_components.append("destination_parameter")
            if expectation.get("trigger_contract") is not None:
                downstream_components.append("trigger_logic")
            if expectation.get("sequence_contract") is not None:
                downstream_components.append("tag_sequence")
            consent = requirement.get("consent")
            if expectation.get("expected_consent_state") not in (None, "") or (
                isinstance(consent, dict) and consent.get("applicable") is True
            ):
                downstream_components.append("consent")
            if expectation.get("business_rules") is not None:
                downstream_components.append("business_rule")
            for component in downstream_components:
                status = status_of(verdict.get(component))
                if status != "BLOCKED":
                    errors.append(
                        f"{label}: absent expected event requires downstream {component}=BLOCKED"
                    )

        variable = requirement.get("gtm_variable")
        variable_name = expectation.get("variable_name")
        if variable_name:
            if status_of(verdict.get("gtm_variable")) not in VALID_STATUSES:
                errors.append(f"{label}: expected GTM variable requires gtm_variable verdict")
            variable_blocked_by_absence = (
                not observed and status_of(verdict.get("gtm_variable")) == "BLOCKED"
            )
            if variable_blocked_by_absence:
                pass
            elif not isinstance(variable, dict) or variable.get("applicable") is not True:
                errors.append(f"{label}: expected GTM variable lacks applicable evidence")
            else:
                _validate_observation(variable, f"{label}.gtm_variable", errors)
                if variable.get("name") != variable_name:
                    errors.append(f"{label}: GTM variable name differs from expectation")
                if (
                    status_of(verdict.get("gtm_variable")) == "PASS"
                    and isinstance(requirement.get("resolved_data_layer"), dict)
                    and expectation.get("match_rule") != "documented_transform"
                ):
                    resolved = requirement["resolved_data_layer"]
                    if (
                        variable.get("field_state") != resolved.get("field_state")
                        or variable.get("field_value") != resolved.get("field_value")
                        or variable.get("field_type") != resolved.get("field_type")
                    ):
                        errors.append(
                            f"{label}: PASS GTM variable differs from resolved Data Layer "
                            "without a documented transformation"
                        )

        _validate_tag(requirement, label, errors)
        tag = requirement.get("tag")
        if isinstance(tag, dict) and tag.get("applicable") is True:
            tag_container = str(tag.get("container_id", requirement_container)).strip()
            if tag_container not in container_ids:
                errors.append(f"{label}: concerned tag references unknown container_id")
            if len(container_ids) > 1 and not _is_nonempty_string(tag.get("container_id")):
                errors.append(
                    f"{label}: multiple containers require explicit tag.container_id ownership"
                )
        if isinstance(tag, dict) and status_of(verdict.get("tag_parameter")) == "PASS":
            comparison_source: dict[str, Any] | None = None
            transform = expectation.get("transformation")
            if expectation.get("match_rule") == "documented_transform" and isinstance(
                transform, dict
            ):
                expected_runtime = transform.get("expected_output")
                expected_runtime_type = js_value_type(expected_runtime)
                expected_runtime_state = field_state_for(expected_runtime)
            else:
                for candidate in (
                    requirement.get("gtm_variable"),
                    requirement.get("resolved_data_layer"),
                    requirement.get("raw_api_call"),
                ):
                    if isinstance(candidate, dict) and candidate.get("field_state"):
                        comparison_source = candidate
                        break
                expected_runtime = (
                    comparison_source.get("field_value")
                    if comparison_source
                    else expectation.get("expected_value")
                )
                expected_runtime_type = (
                    comparison_source.get("field_type")
                    if comparison_source
                    else expectation.get("expected_type")
                )
                expected_runtime_state = (
                    comparison_source.get("field_state")
                    if comparison_source
                    else field_state_for(expectation.get("expected_value"))
                )
            if (
                tag.get("runtime_state") != expected_runtime_state
                or tag.get("runtime_type") != expected_runtime_type
                or tag.get("runtime_value") != expected_runtime
            ):
                errors.append(
                    f"{label}: PASS tag parameter differs from its resolved input or "
                    "documented transformed output"
                )

        _validate_destination(requirement, evidence_by_id, label, errors)
        destination = requirement.get("destination_request")
        if (
            isinstance(destination, dict)
            and destination.get("container_id")
            and str(destination.get("container_id")) not in container_ids
        ):
            errors.append(f"{label}: destination_request references unknown container_id")
        _validate_trigger_and_sequence(requirement, label, errors)

        consent = requirement.get("consent")
        consent_expected = expectation.get("expected_consent_state") not in (None, "")
        if consent_expected and status_of(verdict.get("consent")) not in VALID_STATUSES:
            errors.append(f"{label}: consent expectation requires consent verdict")
        if consent_expected and (
            not isinstance(consent, dict) or consent.get("applicable") is not True
        ):
            errors.append(f"{label}: consent expectation lacks applicable consent evidence")
        if isinstance(consent, dict) and consent.get("applicable") is True:
            if consent.get("source") not in CONSENT_SOURCES - {"not_in_scope"}:
                errors.append(f"{label}: invalid applicable consent source")
            for field in ("scenario_id", "scenario", "state_at_event", "evidence_id"):
                if field not in consent or consent.get(field) in ("", None):
                    errors.append(f"{label}: applicable consent missing '{field}'")
            if status_of(verdict.get("consent")) == "PASS":
                consent_evidence = evidence_by_id.get(str(consent.get("evidence_id", "")))
                if not consent_evidence or consent_evidence.get("kind") not in {
                    "consent_state",
                    "tag_assistant_consent",
                }:
                    errors.append(
                        f"{label}: consent PASS requires event-level consent-state evidence"
                    )
                expected_state = _parse_consent_state(expectation.get("expected_consent_state"))
                actual_state = _parse_consent_state(consent.get("state_at_event"))
                if expected_state is not None and (
                    actual_state is None
                    or any(actual_state.get(key) != value for key, value in expected_state.items())
                ):
                    errors.append(f"{label}: PASS consent state differs from expectation")
        _validate_consent_details(requirement, label, errors)
        _validate_consent_override(requirement, run, blockers, label, errors)
        _validate_business_rule_results(
            requirement,
            computed_business_by_requirement.get(requirement_id, []),
            label,
            errors,
        )
        _validate_sensitive_data(
            requirement,
            label,
            errors,
            required=(scope_status == "IN_SCOPE" and "sensitive_data_scan" in active_layers),
        )
        _validate_client_checks(requirement, run, label, errors)
        _validate_regression(
            requirement,
            acceptance_status,
            regression_context if isinstance(regression_context, dict) else None,
            label,
            errors,
        )

    sorted_ids = [item[1] for item in sorted(sortable_requirements, key=lambda item: item[0])]
    if normalized_inventory and normalized_inventory != sorted_ids:
        errors.append("run: requirement_inventory does not follow source.plan_order")

    for index, row in enumerate(unexpected, start=1):
        unexpected_id = str(row.get("unexpected_id", "")).strip() or str(index)
        event_group_id = str(row.get("event_group_id", "")).strip()
        if not event_group_id:
            errors.append(f"unexpected {unexpected_id}: missing event_group_id")
        elif event_group_id not in set(event_group_ids):
            errors.append(f"unexpected {unexpected_id}: unknown event_group_id '{event_group_id}'")
        status = status_of(row)
        if status not in VALID_STATUSES:
            errors.append(f"unexpected {unexpected_id}: invalid status '{status}'")
        if status == "REVIEW":
            if row.get("review_basis") != "semantic_ambiguity":
                errors.append(
                    f"unexpected {unexpected_id}: REVIEW requires review_basis=semantic_ambiguity"
                )
            if not _is_nonempty_string(row.get("review_question")):
                errors.append(f"unexpected {unexpected_id}: REVIEW requires review_question")
        refs = evidence_ids(row.get("evidence_ids"))
        if not refs:
            errors.append(f"unexpected {unexpected_id}: missing evidence_ids")
        unknown = sorted(set(refs) - known_evidence)
        if unknown:
            errors.append(f"unexpected {unexpected_id}: unknown evidence IDs {', '.join(unknown)}")

    return errors


def validate(data: dict[str, Any], strict: bool = True) -> list[str]:
    """Validate data; raise in strict mode and return warnings otherwise."""
    errors = semantic_errors(data)
    if errors and strict:
        raise ReportValidationError("\n".join(errors))
    return errors


def event_rollup(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Build one concise plan-ordered event result from atomic requirements."""
    requirements = as_rows(data.get("requirements"), "requirements")
    by_group: dict[str, list[dict[str, Any]]] = {}
    for requirement in requirements:
        by_group.setdefault(str(requirement.get("event_group_id", "")), []).append(requirement)
    unexpected_by_group: dict[str, list[dict[str, Any]]] = {}
    for unexpected in as_rows(data.get("unexpected"), "unexpected"):
        unexpected_by_group.setdefault(str(unexpected.get("event_group_id", "")), []).append(
            unexpected
        )

    output: list[dict[str, Any]] = []
    run = data.get("run", {})
    for event in run.get("event_inventory", []):
        group_id = str(event.get("event_group_id", ""))
        rows = by_group.get(group_id, [])
        mapped_unexpected = unexpected_by_group.get(group_id, [])
        statuses = [status_of(row.get("verdict", {}).get("overall")) for row in rows] + [
            status_of(row) for row in mapped_unexpected
        ]
        failures = []
        evidence: set[str] = set()
        for row in rows:
            verdict = row.get("verdict", {})
            mismatch = verdict.get("mismatch") or row.get("notes")
            if status_of(verdict.get("overall")) != "PASS" and mismatch:
                failures.append(str(mismatch))
            evidence.update(evidence_ids(row.get("evidence_ids")))
        for row in mapped_unexpected:
            mismatch = (
                row.get("classification_reason") or row.get("review_question") or row.get("notes")
            )
            if status_of(row) != "PASS" and mismatch:
                failures.append(str(mismatch))
            evidence.update(evidence_ids(row.get("evidence_ids")))
        output.append(
            {
                "event_group_id": group_id,
                "plan_order": event.get("plan_order"),
                "event_name": event.get("event_name"),
                "status": worst_status(statuses),
                "requirement_count": len(rows),
                "reason": "\n".join(dict.fromkeys(failures)),
                "evidence_ids": sorted(evidence),
            }
        )
    return output


def dumps_structured(value: Any) -> str:
    """Serialize structured evidence deterministically for workbook display."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ": "))
