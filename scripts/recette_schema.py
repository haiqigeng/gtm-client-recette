#!/usr/bin/env python3
"""Schema-v2 validation and shared semantics for GTM Preview recette results."""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

SCHEMA_VERSION = 2
RUN_TYPES = {"FULL_TRACKING_PLAN_RECETTE", "SCOPED_ACCEPTANCE_RECETTE"}
VALID_STATUSES = {"PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_TESTED"}
STATUS_PRIORITY = ("FAIL", "BLOCKED", "REVIEW", "NOT_TESTED", "PASS")
STATUS_RANK = {status: len(STATUS_PRIORITY) - index for index, status in enumerate(STATUS_PRIORITY)}
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
}
OCCURRENCE_RULES = {"once", "at_least_once", "absent", "before_event", "after_event"}
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
SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE"}
RAW_SOURCES = {"tag_assistant_api_call", "browser_interception", "not_observed"}
CONSENT_SOURCES = {"natural_cmp", "session_override", "not_in_scope"}
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
FULL_LAYERS = {
    "raw_api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "consent_when_applicable",
}
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


def status_of(value: Any) -> str:
    """Normalize a row or scalar status."""
    if isinstance(value, dict):
        value = value.get("status", "")
    return str(value or "").strip().upper()


def worst_status(statuses: Iterable[str]) -> str:
    """Return the worst applicable status using the recette dependency order."""
    normalized = [status_of(status) for status in statuses if status_of(status) in VALID_STATUSES]
    if not normalized:
        return "NOT_TESTED"
    return max(normalized, key=lambda item: STATUS_RANK[item])


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
    for section_name in (
        "occurrence_evidence",
        "raw_api_call",
        "resolved_data_layer",
        "gtm_variable",
        "tag",
        "consent",
    ):
        section = requirement.get(section_name)
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if key.endswith("evidence_id") and _is_nonempty_string(value):
                ids.add(value.strip())
            elif key.endswith("evidence_ids"):
                ids.update(evidence_ids(value))
    return ids


def _occurrence_rule(expectation: dict[str, Any]) -> tuple[str, str | None]:
    configured = expectation.get("expected_occurrence")
    if isinstance(configured, str):
        return configured, None
    if isinstance(configured, dict):
        return str(configured.get("rule", "")), configured.get("anchor_event_name")
    return "", None


def _validate_occurrence(
    requirement: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    expectation = requirement.get("expectation", {})
    verdict = requirement.get("verdict", {})
    rule, anchor_name = _occurrence_rule(expectation)
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
        return state == field_state_for(expected) and actual == expected and actual_type == expected_type
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
    if rule in {"changes", "stable", "documented_transform"}:
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
    for field in ("action_timestamp", "quiet_window_ms", "timeout_ms", "stream_settled"):
        if field not in boundary:
            errors.append(f"{label}: action_boundary missing '{field}'")
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
    if "last_event_before" not in boundary:
        errors.append(f"{label}: action_boundary missing 'last_event_before'")
    if "settled_final_event" not in boundary:
        errors.append(f"{label}: action_boundary missing 'settled_final_event'")
    if observed and not isinstance(boundary.get("first_event_after"), int):
        errors.append(f"{label}: observed event requires first_event_after")


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
    firing_pass = status_of(verdict.get("tag_firing")) == "PASS"
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
    expected_configuration = expectation.get("expected_tag_configuration")
    if (
        expected_configuration not in (None, "")
        and parameter_status == "PASS"
        and tag.get("configured_value") != expected_configuration
    ):
        errors.append(
            f"{label}: PASS tag configuration differs from the tracking-plan expectation"
        )


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
    if run.get("environment_class") == "production":
        errors.append(f"{label}: session consent override is forbidden in production")
    if consent.get("override_approved") is not True:
        errors.append(f"{label}: session consent override lacks explicit analyst approval")
    for field in (
        "approval_evidence_id",
        "override_method",
        "before_state",
        "state_at_event",
        "blocker_id",
    ):
        if field not in consent or consent.get(field) in ("", None):
            errors.append(f"{label}: session consent override missing '{field}'")
    blocker = blockers.get(str(consent.get("blocker_id", "")))
    if not blocker or blocker.get("type") != "CMP_TEST_ENVIRONMENT":
        errors.append(f"{label}: session consent override must reference a CMP test-environment blocker")


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
    for field in (
        "run_id",
        "run_type",
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
    run_type = str(run.get("run_type", "")).strip()
    if run_type not in RUN_TYPES:
        errors.append(f"run: invalid run_type '{run_type}'")
    if run.get("environment_class") not in {"test", "preprod", "staging", "production"}:
        errors.append("run: environment_class must be test, preprod, staging, or production")
    if "observation-only" in (
        f"{run.get('tracking_plan_source', '')} {run.get('acceptance_scope', '')}".lower()
    ):
        errors.append("run: observation-only mode is not an acceptance recette")

    included_layers = run.get("included_layers")
    if run_type == "SCOPED_ACCEPTANCE_RECETTE":
        if not isinstance(included_layers, list) or not included_layers:
            errors.append("run: scoped recette requires non-empty included_layers")
    elif run_type == "FULL_TRACKING_PLAN_RECETTE":
        if not isinstance(included_layers, list):
            errors.append("run: full recette requires included_layers")
            included_layers = []
        included = set(included_layers)
        if not FULL_LAYERS.issubset(included):
            missing = sorted(FULL_LAYERS - included)
            errors.append("run: full recette included_layers missing " + ", ".join(missing))
    active_layers = set(included_layers) if isinstance(included_layers, list) else set()

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

    evidence_catalog = [str(row.get("evidence_id", "")).strip() for row in evidence]
    empty_evidence_rows = [index for index, value in enumerate(evidence_catalog, start=1) if not value]
    for index in empty_evidence_rows:
        errors.append(f"evidence row {index}: missing evidence_id")
    duplicate_evidence = sorted(
        item for item, count in Counter(item for item in evidence_catalog if item).items() if count > 1
    )
    if duplicate_evidence:
        errors.append("evidence: duplicate IDs " + ", ".join(duplicate_evidence))
    known_evidence = {item for item in evidence_catalog if item}
    evidence_by_id = {
        str(row.get("evidence_id", "")).strip(): row
        for row in evidence
        if str(row.get("evidence_id", "")).strip()
    }

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
                errors.append(f"blocker {blocker_id}: protected checkpoint must be analyst-controlled")
            if blocker_status == "BLOCKED" and blocker.get("analyst_help_requested") is not True:
                errors.append(
                    f"blocker {blocker_id}: analyst help must be requested before final BLOCKED"
                )

    requirement_ids = [str(row.get("requirement_id", "")).strip() for row in requirements]
    duplicate_requirements = sorted(
        item for item, count in Counter(item for item in requirement_ids if item).items() if count > 1
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
        if journey.get("execution_status") not in EXECUTION_STATUSES:
            errors.append(f"{label}: invalid journey.execution_status")
        if journey.get("inferred") is True and not _is_nonempty_string(
            journey.get("inference_source")
        ):
            errors.append(f"{label}: inferred journey requires inference_source")
        if not isinstance(journey.get("attempted_routes"), list):
            errors.append(f"{label}: journey.attempted_routes must be an array")

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
            errors.append(f"{label}: unsupported expected_type '{expectation.get('expected_type')}'")
        if expectation.get("match_rule") == "documented_transform":
            transform = expectation.get("transformation")
            if not isinstance(transform, dict) or not all(
                key in transform for key in ("input_path", "rule", "expected_output")
            ):
                errors.append(f"{label}: documented_transform requires input, rule, and output")

        verdict = requirement.get("verdict")
        if not isinstance(verdict, dict):
            errors.append(f"{label}: missing verdict object")
            verdict = {}
        components = []
        for field in (
            "event_occurrence",
            "raw_payload",
            "resolved_data_layer",
            "gtm_variable",
            "tag_firing",
            "tag_parameter",
            "consent",
        ):
            value = verdict.get(field)
            if value in (None, ""):
                continue
            status = status_of(value)
            if status not in VALID_STATUSES:
                errors.append(f"{label}: verdict.{field} has invalid status '{status}'")
            else:
                components.append(status)
        overall = status_of(verdict.get("overall"))
        if overall not in VALID_STATUSES:
            errors.append(f"{label}: verdict.overall has invalid status '{overall}'")
        elif components and overall != worst_status(components):
            errors.append(
                f"{label}: overall status '{overall}' does not equal worst applicable "
                f"component '{worst_status(components)}'"
            )

        refs = evidence_ids(requirement.get("evidence_ids"))
        if not refs:
            errors.append(f"{label}: missing evidence_ids")
        unknown = sorted(set(refs) - known_evidence)
        if unknown:
            errors.append(f"{label}: unknown evidence IDs {', '.join(unknown)}")
        nested = _nested_ids(requirement)
        if not nested.issubset(set(refs)):
            missing = sorted(nested - set(refs))
            errors.append(f"{label}: nested evidence IDs absent from evidence_ids: {', '.join(missing)}")

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
        if scope_status == "IN_SCOPE" and journey.get("execution_status") in {"EXECUTED", "BLOCKED"}:
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
            _validate_occurrence(requirement, label, errors)

        if observed:
            raw_required = run_type == "FULL_TRACKING_PLAN_RECETTE" or "raw_api_call" in active_layers
            resolved_required = (
                run_type == "FULL_TRACKING_PLAN_RECETTE"
                or "resolved_data_layer" in active_layers
            )
            raw = requirement.get("raw_api_call")
            resolved = requirement.get("resolved_data_layer")
            if raw_required:
                _validate_observation(
                    raw,
                    f"{label}.raw_api_call",
                    errors,
                    require_payload=True,
                )
                if isinstance(raw, dict) and raw.get("capture_source") not in RAW_SOURCES:
                    errors.append(f"{label}: invalid raw capture_source")
                if run_type == "FULL_TRACKING_PLAN_RECETTE" and isinstance(raw, dict) and (
                    raw.get("capture_source") != "tag_assistant_api_call"
                ):
                    errors.append(
                        f"{label}: full recette requires exact Tag Assistant API Call evidence"
                    )
                if (
                    isinstance(raw, dict)
                    and status_of(verdict.get("raw_payload")) == "PASS"
                ):
                    match = _matches_expectation(expectation, raw)
                    if match is False:
                        errors.append(
                            f"{label}: PASS raw_payload contradicts expected value/type/rule"
                        )
            if resolved_required:
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
        elif overall == "PASS" and _occurrence_rule(expectation)[0] != "absent":
            errors.append(f"{label}: PASS requires an observed event or an expected absence")
        elif status_of(verdict.get("event_occurrence")) == "FAIL":
            _validate_action_boundary(
                requirement.get("action_boundary"),
                label,
                errors,
                observed=False,
                require_ready=True,
            )
            for component in (
                "raw_payload",
                "resolved_data_layer",
                "gtm_variable",
                "tag_firing",
                "tag_parameter",
            ):
                status = status_of(verdict.get(component))
                if status and status != "BLOCKED":
                    errors.append(
                        f"{label}: absent expected event requires downstream {component}=BLOCKED"
                    )

        variable = requirement.get("gtm_variable")
        variable_name = expectation.get("variable_name")
        if variable_name:
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
        if (
            isinstance(tag, dict)
            and status_of(verdict.get("tag_parameter")) == "PASS"
        ):
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
                    comparison_source.get("field_value") if comparison_source else None
                )
                expected_runtime_type = (
                    comparison_source.get("field_type") if comparison_source else None
                )
                expected_runtime_state = (
                    comparison_source.get("field_state") if comparison_source else None
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

        consent = requirement.get("consent")
        consent_expected = expectation.get("expected_consent_state") not in (None, "")
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
        _validate_consent_override(requirement, run, blockers, label, errors)

    sorted_ids = [item[1] for item in sorted(sortable_requirements, key=lambda item: item[0])]
    if normalized_inventory and normalized_inventory != sorted_ids:
        errors.append("run: requirement_inventory does not follow source.plan_order")

    for index, row in enumerate(unexpected, start=1):
        unexpected_id = str(row.get("unexpected_id", "")).strip() or str(index)
        status = status_of(row)
        if status not in VALID_STATUSES:
            errors.append(f"unexpected {unexpected_id}: invalid status '{status}'")
        refs = evidence_ids(row.get("evidence_ids"))
        if not refs:
            errors.append(f"unexpected {unexpected_id}: missing evidence_ids")
        unknown = sorted(set(refs) - known_evidence)
        if unknown:
            errors.append(
                f"unexpected {unexpected_id}: unknown evidence IDs {', '.join(unknown)}"
            )

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

    output: list[dict[str, Any]] = []
    run = data.get("run", {})
    for event in run.get("event_inventory", []):
        group_id = str(event.get("event_group_id", ""))
        rows = by_group.get(group_id, [])
        statuses = [status_of(row.get("verdict", {}).get("overall")) for row in rows]
        failures = []
        evidence: set[str] = set()
        for row in rows:
            verdict = row.get("verdict", {})
            mismatch = verdict.get("mismatch") or row.get("notes")
            if status_of(verdict.get("overall")) != "PASS" and mismatch:
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
