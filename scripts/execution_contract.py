#!/usr/bin/env python3
"""Validate interaction coverage, action windows, and observed business pushes."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from evidence_contract import (
    ACTION_BOUND_EVIDENCE_KINDS,
    CONTAINER_BOUND_EVIDENCE_KINDS,
    DIRECT_CAPTURE_KINDS,
    EVENT_INDEX_EVIDENCE_KINDS,
)
from layer_contract import CANONICAL_LAYERS, applicable_layers

SESSION_SCHEMA_VERSION = 2
CASE_SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE"}
CASE_EXECUTION_STATUSES = {"PENDING", "EXECUTED", "BLOCKED", "NOT_TESTED"}
LAYER_RESULT_STATUSES = {"PASS", "FAIL", "BLOCKED", "REVIEW"}
PUSH_CLASSIFICATIONS = {
    "expected",
    "companion",
    "duplicate",
    "premature",
    "delayed",
    "wrong_order",
    "wrong_context",
    "unplanned_relevant",
}
ANOMALOUS_PUSH_CLASSIFICATIONS = PUSH_CLASSIFICATIONS - {"expected", "companion"}
DISCOVERY_SOURCES = {
    "tracking_plan",
    "supplied_url",
    "supplied_screenshot",
    "supplied_journey",
    "website_census",
    "runtime_discovery",
}
AUTHORIZATION_SCOPES = {
    "safe_synthetic_identity",
    "ordinary_form_submission",
    "nonproduction_lead_submission",
    "production_reversible_submission",
    "cmp_session_override",
    "production_cmp_session_override",
}
PROTECTED_AUTHORIZATION_EXCLUSIONS = (
    "MFA",
    "CAPTCHA",
    "EMAIL_VERIFICATION",
    "SMS_VERIFICATION",
    "MAGIC_LINK",
    "REAL_PAYMENT",
    "EXTERNAL_APPROVAL",
    "IRREVERSIBLE_ACTION",
)
STATUS_RANK = {"PASS": 0, "NOT_TESTED": 1, "REVIEW": 2, "BLOCKED": 3, "FAIL": 4}
FORBIDDEN_SESSION_SECRET_KEYS = {
    "password",
    "passphrase",
    "passcode",
    "credential",
    "credentials",
    "username",
    "login",
    "email",
    "phone",
    "phone_number",
    "first_name",
    "last_name",
    "full_name",
    "postal_address",
    "card_number",
    "cvv",
    "secret",
}
LAYER_EVIDENCE_KINDS = {
    "raw_api_call": {"api_call", "action_boundary"},
    "resolved_data_layer": {"resolved_data_layer"},
    "gtm_variable": {"gtm_variable"},
    "tag_configuration": {"tag_configuration"},
    "tag_firing": {"tag_runtime"},
    "tag_parameter": {"tag_runtime"},
    "consent_when_applicable": {"consent_state", "tag_assistant_consent"},
    "source_signal_when_no_data_layer_push": {
        "source_signal",
        "gtm_native_event",
        "gtm_auto_event",
        "dom_event",
        "direct_vendor_call",
        "custom_html",
        "ga4_enhanced_measurement",
    },
    "destination_request_when_applicable": {"browser_network_request"},
    "trigger_logic_when_applicable": {"trigger_evaluation"},
    "tag_sequence_when_applicable": {"tag_sequence"},
    "business_rules_when_declared": {"business_rule_evaluation"},
    "sensitive_data_scan": {"sensitive_data_scan"},
    "client_checks_when_applicable": {"client_side_checks"},
    "regression_when_baseline_provided": {"previous_run_comparison"},
    "container_context_when_applicable": {
        "tag_configuration",
        "tag_runtime",
        "browser_network_request",
    },
    "conditional_scenarios_when_applicable": {"scenario_branch"},
}


def rows(value: Any, field_name: str, errors: list[str]) -> list[dict[str, Any]]:
    """Return object rows while recording a useful structural error."""
    if not isinstance(value, list):
        errors.append(f"session: {field_name} must be an array")
        return []
    output = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            errors.append(f"session: {field_name} row {index} must be an object")
            continue
        output.append(item)
    return output


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def iso_timestamp(value: Any) -> bool:
    if not nonempty(value):
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def worst_status(statuses: Iterable[Any]) -> str:
    normalized = [
        str(status).strip().upper()
        for status in statuses
        if str(status).strip().upper() in STATUS_RANK
    ]
    return max(normalized, key=STATUS_RANK.__getitem__) if normalized else "NOT_TESTED"


def _credential_paths(value: Any, path: str = "session") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if str(key).strip().lower() in FORBIDDEN_SESSION_SECRET_KEYS:
                findings.append(child_path)
            findings.extend(_credential_paths(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(_credential_paths(item, f"{path}[{index}]"))
    return findings


def _unique_ids(
    collection: list[dict[str, Any]],
    field_name: str,
    label: str,
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    values = [str(row.get(field_name, "")).strip() for row in collection]
    errors.extend(
        f"session: {label} row {index} missing {field_name}"
        for index, value in enumerate(values, start=1)
        if not value
    )
    duplicates = sorted(
        value for value, count in Counter(item for item in values if item).items() if count > 1
    )
    if duplicates:
        errors.append(f"session: duplicate {label} IDs " + ", ".join(duplicates))
    return {
        str(row.get(field_name)).strip(): row
        for row in collection
        if str(row.get(field_name, "")).strip()
    }


def _result_catalogs(
    results: dict[str, Any] | None,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, list[dict[str, Any]]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    if not isinstance(results, dict):
        return {}, {}, {}, {}
    requirements = [row for row in results.get("requirements", []) if isinstance(row, dict)]
    by_requirement = {
        str(row.get("requirement_id", "")).strip(): row
        for row in requirements
        if str(row.get("requirement_id", "")).strip()
    }
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for requirement in requirements:
        by_group[str(requirement.get("event_group_id", "")).strip()].append(requirement)
    events = {
        str(row.get("event_group_id", "")).strip(): row
        for row in results.get("run", {}).get("event_inventory", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip()
    }
    evidence = {
        str(row.get("evidence_id", "")).strip(): row
        for row in results.get("evidence", [])
        if isinstance(row, dict) and str(row.get("evidence_id", "")).strip()
    }
    return by_requirement, dict(by_group), events, evidence


def _normalized_event_status(requirements: list[dict[str, Any]]) -> str:
    return worst_status(
        row.get("verdict", {}).get("overall")
        for row in requirements
        if isinstance(row.get("verdict"), dict)
    )


def _validate_authorizations(
    authorizations: list[dict[str, Any]],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    catalog = _unique_ids(
        authorizations,
        "authorization_id",
        "authorization",
        errors,
    )
    for authorization_id, authorization in catalog.items():
        scope = authorization.get("scope")
        if scope not in AUTHORIZATION_SCOPES:
            errors.append(f"session authorization {authorization_id}: unsupported scope '{scope}'")
        if authorization.get("session_only") is not True:
            errors.append(f"session authorization {authorization_id}: session_only must be true")
        if not nonempty(authorization.get("description")):
            errors.append(
                f"session authorization {authorization_id}: exact description is required"
            )
        if not iso_timestamp(authorization.get("approved_at")):
            errors.append(f"session authorization {authorization_id}: approved_at must be ISO 8601")
        if authorization.get("protected_exclusions") != list(PROTECTED_AUTHORIZATION_EXCLUSIONS):
            errors.append(
                f"session authorization {authorization_id}: protected exclusions were altered"
            )
        if scope == "production_cmp_session_override":
            if authorization.get("environment_class") != "production":
                errors.append(
                    f"session authorization {authorization_id}: production CMP scope "
                    "requires environment_class=production"
                )
            if not nonempty(authorization.get("exact_method")):
                errors.append(
                    f"session authorization {authorization_id}: production CMP scope "
                    "requires the exact temporary method"
                )
    return catalog


def _validate_direct_evidence_row(
    ref: str,
    row: dict[str, Any],
    action_id: str,
    container_ids: set[str],
    errors: list[str],
) -> None:
    kind = str(row.get("kind", "")).strip()
    if kind in DIRECT_CAPTURE_KINDS and row.get("capture_mode") != "direct":
        errors.append(
            f"evidence {ref}: direct browser/Preview evidence requires capture_mode=direct"
        )
    if kind in ACTION_BOUND_EVIDENCE_KINDS and row.get("action_id") != action_id:
        errors.append(f"evidence {ref}: action_id does not match session action {action_id}")
    if kind in EVENT_INDEX_EVIDENCE_KINDS and not isinstance(row.get("event_index"), int):
        errors.append(f"evidence {ref}: direct event evidence requires event_index")
    if kind == "browser_network_request" and not nonempty(row.get("request_id")):
        errors.append(f"evidence {ref}: browser request evidence requires request_id")
    if kind in CONTAINER_BOUND_EVIDENCE_KINDS and not nonempty(row.get("container_id")):
        errors.append(f"evidence {ref}: direct GTM evidence requires container_id")
    if (
        container_ids
        and nonempty(row.get("container_id"))
        and str(row.get("container_id")).strip() not in container_ids
    ):
        errors.append(f"evidence {ref}: container_id is outside the action container set")


def _validate_direct_evidence(
    *,
    layer: str,
    layer_result: dict[str, Any],
    action: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    action_id = str(action.get("action_id", "")).strip()
    refs = layer_result.get("evidence_ids")
    if not isinstance(refs, list) or not refs:
        errors.append(f"session action {action_id} layer {layer}: evidence_ids are required")
        return
    allowed_kinds = LAYER_EVIDENCE_KINDS.get(layer, set())
    container_ids = {
        str(value).strip() for value in action.get("container_ids", []) if str(value).strip()
    }
    seen_allowed = False
    for ref_value in refs:
        ref = str(ref_value).strip()
        row = evidence.get(ref)
        if row is None:
            errors.append(f"session action {action_id} layer {layer}: unknown evidence ID '{ref}'")
            continue
        seen_allowed = seen_allowed or str(row.get("kind", "")).strip() in allowed_kinds
        _validate_direct_evidence_row(
            ref,
            row,
            action_id,
            container_ids,
            errors,
        )
    if str(layer_result.get("status", "")).strip().upper() != "BLOCKED" and not seen_allowed:
        errors.append(
            f"session action {action_id} layer {layer}: no direct evidence of the required kind"
        )


def _validate_action_boundary_link(
    requirement: dict[str, Any],
    action: dict[str, Any],
    errors: list[str],
) -> None:
    requirement_id = str(requirement.get("requirement_id", "")).strip()
    boundary = requirement.get("action_boundary")
    if not isinstance(boundary, dict):
        return
    errors.extend(
        (
            f"requirement {requirement_id}: action_boundary.{field_name} "
            "does not match the session ledger"
        )
        for field_name in (
            "action_id",
            "retry_of_action_id",
            "last_event_before",
            "first_event_after",
            "settled_final_event",
            "action_timestamp",
            "interaction_outcome",
            "completion_signal",
            "quiet_window_ms",
            "timeout_ms",
            "stream_settled",
            "settlement_reason",
        )
        if boundary.get(field_name) != action.get(field_name)
    )


@dataclass
class _ValidationContext:
    final: bool
    results_provided: bool
    errors: list[str]
    cases: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    case_by_id: dict[str, dict[str, Any]]
    action_by_id: dict[str, dict[str, Any]]
    push_by_id: dict[str, dict[str, Any]]
    authorization_by_id: dict[str, dict[str, Any]]
    by_requirement: dict[str, dict[str, Any]]
    requirements_by_group: dict[str, list[dict[str, Any]]]
    event_by_group: dict[str, dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    unexpected_rows: list[dict[str, Any]]
    unexpected_by_push: dict[str, dict[str, Any]]
    container_count: int
    actions_by_case: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    pushes_by_action: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    anomalous_by_group: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    push_indexes: set[tuple[str, int]] = field(default_factory=set)


def _validate_session_metadata(ledger: dict[str, Any], errors: list[str]) -> None:
    credential_paths = _credential_paths(ledger)
    if credential_paths:
        errors.append(
            "session: credentials or synthetic personal fields must remain ephemeral "
            "and cannot be stored at " + ", ".join(credential_paths)
        )
    errors.extend(
        f"session: missing '{field_name}'"
        for field_name in ("created_at", "updated_at", "profile_path")
        if not nonempty(ledger.get(field_name))
    )
    errors.extend(
        f"session: {field_name} must be ISO 8601 with timezone"
        for field_name in ("created_at", "updated_at")
        if nonempty(ledger.get(field_name)) and not iso_timestamp(ledger.get(field_name))
    )
    approved_origins = ledger.get("approved_origins")
    if not isinstance(approved_origins, list) or not approved_origins:
        errors.append("session: approved_origins must be a non-empty array")
    surfaces = ledger.get("surfaces")
    if not isinstance(surfaces, dict):
        errors.append("session: surfaces must be an object")
        surfaces = {}
    surface_rows = [row for row in surfaces.values() if isinstance(row, dict)]
    required_roles = {"gtm_workspace", "tag_assistant", "website"}
    missing_roles = sorted(required_roles - {str(row.get("role")) for row in surface_rows})
    if missing_roles:
        errors.append("session: missing required browser surfaces " + ", ".join(missing_roles))
    tag_assistants = [row for row in surface_rows if row.get("role") == "tag_assistant"]
    if tag_assistants and not all(row.get("connected") is True for row in tag_assistants):
        errors.append("session: Tag Assistant is not recorded as connected")


def _validate_layer_result(
    context: _ValidationContext,
    action: dict[str, Any],
    layer_result: Any,
) -> None:
    action_id = str(action.get("action_id", "")).strip()
    if not isinstance(layer_result, dict):
        context.errors.append(f"session action {action_id}: layer result must be an object")
        return
    layer = str(layer_result.get("layer", "")).strip()
    result_status = str(layer_result.get("status", "")).strip().upper()
    if layer not in CANONICAL_LAYERS:
        context.errors.append(f"session action {action_id}: unsupported layer '{layer}'")
    if result_status not in LAYER_RESULT_STATUSES:
        context.errors.append(
            f"session action {action_id} layer {layer}: invalid status '{result_status}'"
        )
    if not nonempty(layer_result.get("reason")):
        context.errors.append(
            f"session action {action_id} layer {layer}: concise reason is required"
        )
    if result_status == "REVIEW" and not nonempty(layer_result.get("semantic_ambiguity")):
        context.errors.append(
            f"session action {action_id} layer {layer}: REVIEW requires "
            "a semantic_ambiguity question"
        )
    if context.results_provided:
        _validate_direct_evidence(
            layer=layer,
            layer_result=layer_result,
            action=action,
            evidence=context.evidence,
            errors=context.errors,
        )


def _validate_action(context: _ValidationContext, action: dict[str, Any]) -> None:
    action_id = str(action.get("action_id", "")).strip()
    case_id = str(action.get("case_id", "")).strip()
    case = context.case_by_id.get(case_id)
    if case is None:
        context.errors.append(f"session action {action_id}: unknown case_id '{case_id}'")
        return
    context.actions_by_case[case_id].append(action)
    for field_name in (
        "event_group_id",
        "requirement_ids",
        "placement",
        "material_variant",
    ):
        if action.get(field_name) != case.get(field_name):
            context.errors.append(f"session action {action_id}: {field_name} differs from its case")
    if action.get("state") not in {"OPEN", "SETTLED"}:
        context.errors.append(f"session action {action_id}: invalid state")
    if context.final and action.get("state") != "SETTLED":
        context.errors.append(f"session action {action_id}: final validation rejects open actions")
    attempt_number = action.get("attempt_number")
    if not isinstance(attempt_number, int) or attempt_number < 1:
        context.errors.append(f"session action {action_id}: invalid attempt_number")
    layer_results = action.get("layer_results")
    if not isinstance(layer_results, list):
        context.errors.append(f"session action {action_id}: layer_results must be an array")
        layer_results = []
    layer_names = [
        str(row.get("layer", "")).strip() for row in layer_results if isinstance(row, dict)
    ]
    duplicates = sorted(
        layer for layer, count in Counter(layer_names).items() if layer and count > 1
    )
    if duplicates:
        context.errors.append(
            f"session action {action_id}: duplicate layer results " + ", ".join(duplicates)
        )
    for layer_result in layer_results:
        _validate_layer_result(context, action, layer_result)


def _validate_attempt_chain(
    case_id: str,
    case_actions: list[dict[str, Any]],
    errors: list[str],
) -> None:
    ordered = sorted(
        case_actions,
        key=lambda row: (
            int(row.get("attempt_number", 0)) if isinstance(row.get("attempt_number"), int) else 0
        ),
    )
    expected_attempts = list(range(1, len(ordered) + 1))
    if [row.get("attempt_number") for row in ordered] != expected_attempts:
        errors.append(f"session case {case_id}: attempt numbers are not contiguous")
    for index, action in enumerate(ordered):
        retry_id = action.get("retry_of_action_id")
        if index == 0 and retry_id not in (None, ""):
            errors.append(f"session case {case_id}: first attempt cannot be a retry")
        if index > 0 and retry_id != ordered[index - 1].get("action_id"):
            errors.append(
                f"session case {case_id}: retry must reference the retained prior attempt"
            )


def _validate_actions(context: _ValidationContext) -> None:
    for action in context.actions:
        _validate_action(context, action)
    for case_id, case_actions in context.actions_by_case.items():
        _validate_attempt_chain(case_id, case_actions, context.errors)


def _validate_case_shape(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
) -> list[str]:
    group_id = str(case.get("event_group_id", "")).strip()
    scope_status = case.get("scope_status")
    execution_status = case.get("execution_status")
    if not group_id:
        context.errors.append(f"session case {case_id}: event_group_id is required")
    if scope_status not in CASE_SCOPE_STATUSES:
        context.errors.append(f"session case {case_id}: invalid scope_status")
    if execution_status not in CASE_EXECUTION_STATUSES:
        context.errors.append(f"session case {case_id}: invalid execution_status")
    context.errors.extend(
        f"session case {case_id}: missing '{field_name}'"
        for field_name in ("url", "element", "placement", "action")
        if not nonempty(case.get(field_name))
    )
    if case.get("discovered_from") not in DISCOVERY_SOURCES:
        context.errors.append(f"session case {case_id}: invalid discovered_from")
    if not isinstance(case.get("material_variant"), dict):
        context.errors.append(f"session case {case_id}: material_variant must be an object")
    declared_layers = case.get("applicable_layers")
    if not isinstance(declared_layers, list) or any(
        layer not in CANONICAL_LAYERS for layer in declared_layers
    ):
        context.errors.append(f"session case {case_id}: invalid applicable_layers")
        declared_layers = []
    if len(set(declared_layers)) != len(declared_layers):
        context.errors.append(f"session case {case_id}: duplicate applicable_layers")
    authorization_ids = case.get("authorization_ids", [])
    if not isinstance(authorization_ids, list):
        context.errors.append(f"session case {case_id}: authorization_ids must be an array")
    else:
        unknown = sorted(
            str(reference)
            for reference in authorization_ids
            if str(reference) not in context.authorization_by_id
        )
        if unknown:
            context.errors.append(
                f"session case {case_id}: unknown authorization IDs " + ", ".join(unknown)
            )
    return declared_layers


def _validate_case_result_mapping(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
    declared_layers: list[str],
) -> None:
    if not context.results_provided:
        return
    group_id = str(case.get("event_group_id", "")).strip()
    group_requirements = context.requirements_by_group.get(group_id, [])
    if group_id not in context.event_by_group:
        context.errors.append(f"session case {case_id}: unknown event_group_id '{group_id}'")
    expected_ids = sorted(str(row.get("requirement_id", "")).strip() for row in group_requirements)
    actual_ids = sorted(str(value).strip() for value in case.get("requirement_ids", []))
    if expected_ids != actual_ids:
        context.errors.append(
            f"session case {case_id}: requirement_ids do not exactly match "
            "the normalized event group"
        )
    required_layers = set(
        applicable_layers(
            group_requirements,
            container_count=context.container_count,
        )
    )
    missing_layers = sorted(required_layers - set(declared_layers))
    if missing_layers:
        context.errors.append(
            f"session case {case_id}: applicable_layers omit " + ", ".join(missing_layers)
        )


def _completed_case_actions(
    context: _ValidationContext,
    case_id: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in context.actions_by_case.get(case_id, [])
        if row.get("state") == "SETTLED"
        and row.get("interaction_outcome") == "completed"
        and row.get("stream_settled") is True
        and row.get("preview_connected_after") is True
    ]


def _validate_case_execution(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
    declared_layers: list[str],
) -> None:
    scope_status = case.get("scope_status")
    execution_status = case.get("execution_status")
    completed = _completed_case_actions(context, case_id)
    final_action_id = case.get("final_action_id")
    if execution_status == "EXECUTED":
        if not completed:
            context.errors.append(
                f"session case {case_id}: EXECUTED requires a completed settled action"
            )
        elif final_action_id != completed[-1].get("action_id"):
            context.errors.append(
                f"session case {case_id}: final_action_id is not the latest "
                "completed settled action"
            )
        else:
            recorded_layers = {
                str(row.get("layer", "")).strip()
                for row in completed[-1].get("layer_results", [])
                if isinstance(row, dict)
            }
            missing = sorted(set(declared_layers) - recorded_layers)
            if missing:
                context.errors.append(
                    f"session case {case_id}: final action omits layer results "
                    + ", ".join(missing)
                )
    if execution_status == "BLOCKED" and (
        not nonempty(case.get("blocker_id")) or not nonempty(case.get("reason"))
    ):
        context.errors.append(f"session case {case_id}: BLOCKED requires blocker_id and reason")
    if scope_status == "OUT_OF_SCOPE":
        if execution_status != "NOT_TESTED" or not nonempty(case.get("reason")):
            context.errors.append(
                f"session case {case_id}: OUT_OF_SCOPE requires NOT_TESTED and reason"
            )
    elif execution_status == "NOT_TESTED":
        context.errors.append(f"session case {case_id}: NOT_TESTED is only valid for OUT_OF_SCOPE")
    if context.final and scope_status == "IN_SCOPE" and execution_status == "PENDING":
        context.errors.append(f"session case {case_id}: applicable case remains PENDING")


def _validate_cases(context: _ValidationContext) -> None:
    for case_id, case in context.case_by_id.items():
        declared_layers = _validate_case_shape(context, case_id, case)
        _validate_case_result_mapping(context, case_id, case, declared_layers)
        _validate_case_execution(context, case_id, case, declared_layers)


def _validate_push_index(
    context: _ValidationContext,
    push_id: str,
    push: dict[str, Any],
    action: dict[str, Any],
) -> None:
    event_index = push.get("event_index")
    stream_id = str(push.get("stream_id", "tag_assistant")).strip()
    if not isinstance(event_index, int) or isinstance(event_index, bool):
        context.errors.append(f"session business push {push_id}: event_index must be an integer")
        return
    key = (stream_id, event_index)
    if key in context.push_indexes:
        context.errors.append(f"session business push {push_id}: duplicate stream/event index")
    context.push_indexes.add(key)
    last_event = action.get("last_event_before")
    settled_event = action.get("settled_final_event")
    if isinstance(last_event, int) and event_index <= last_event:
        context.errors.append(
            f"session business push {push_id}: event_index is outside action window"
        )
    if isinstance(settled_event, int) and event_index > settled_event:
        context.errors.append(
            f"session business push {push_id}: event_index exceeds settled action window"
        )


def _validate_push_evidence(
    context: _ValidationContext,
    push_id: str,
    push: dict[str, Any],
    action_id: str,
) -> None:
    if not context.results_provided:
        return
    evidence_row = context.evidence.get(str(push.get("evidence_id", "")).strip())
    if evidence_row is None or evidence_row.get("kind") != "api_call":
        context.errors.append(
            f"session business push {push_id}: exact API Call evidence is required"
        )
        return
    if evidence_row.get("capture_mode") != "direct":
        context.errors.append(f"session business push {push_id}: evidence is not a direct capture")
    if evidence_row.get("action_id") != action_id:
        context.errors.append(f"session business push {push_id}: evidence action_id mismatch")
    if evidence_row.get("event_index") != push.get("event_index"):
        context.errors.append(f"session business push {push_id}: evidence event_index mismatch")


def _unexpected_by_push(
    unexpected_rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("observed_push_id", "")).strip(): row
        for row in unexpected_rows
        if str(row.get("observed_push_id", "")).strip()
    }


def _validate_push_anomaly(
    context: _ValidationContext,
    push_id: str,
    push: dict[str, Any],
    action_id: str,
    group_id: str,
) -> None:
    classification = push.get("classification")
    if classification not in ANOMALOUS_PUSH_CLASSIFICATIONS:
        return
    context.anomalous_by_group[group_id].append(push)
    unexpected = context.unexpected_by_push.get(push_id)
    if context.results_provided and unexpected is None:
        context.errors.append(
            f"session business push {push_id}: anomalous push is absent from unexpected"
        )
        return
    if unexpected is None:
        return
    if unexpected.get("action_id") != action_id:
        context.errors.append(f"session business push {push_id}: unexpected action_id mismatch")
    if str(unexpected.get("event_group_id", "")).strip() != group_id:
        context.errors.append(
            f"session business push {push_id}: unexpected event_group_id mismatch"
        )
    unexpected_status = str(unexpected.get("status", "")).strip().upper()
    confirmed_contradictions = {
        "duplicate",
        "premature",
        "delayed",
        "wrong_order",
        "wrong_context",
    }
    if classification in confirmed_contradictions and unexpected_status != "FAIL":
        context.errors.append(
            f"session business push {push_id}: confirmed occurrence "
            "contradiction requires unexpected status FAIL"
        )
    if classification == "unplanned_relevant" and unexpected_status not in {"FAIL", "REVIEW"}:
        context.errors.append(
            f"session business push {push_id}: unplanned relevant push "
            "requires unexpected status FAIL or REVIEW"
        )


def _validate_push(
    context: _ValidationContext,
    push_id: str,
    push: dict[str, Any],
) -> None:
    action_id = str(push.get("action_id", "")).strip()
    action = context.action_by_id.get(action_id)
    if action is None:
        context.errors.append(f"session business push {push_id}: unknown action_id '{action_id}'")
        return
    context.pushes_by_action[action_id].append(push)
    if push.get("case_id") != action.get("case_id"):
        context.errors.append(f"session business push {push_id}: case_id differs from its action")
    classification = push.get("classification")
    if classification not in PUSH_CLASSIFICATIONS:
        context.errors.append(f"session business push {push_id}: invalid classification")
    if not nonempty(push.get("classification_reason")):
        context.errors.append(f"session business push {push_id}: classification_reason is required")
    context.errors.extend(
        f"session business push {push_id}: missing '{field_name}'"
        for field_name in (
            "event_name",
            "url",
            "page_state",
            "evidence_id",
            "container_id",
        )
        if not nonempty(push.get(field_name))
    )
    _validate_push_index(context, push_id, push, action)
    group_id = str(push.get("event_group_id", "")).strip()
    if classification != "unplanned_relevant" and not group_id:
        context.errors.append(
            f"session business push {push_id}: classification requires event_group_id"
        )
    if group_id and context.results_provided and group_id not in context.event_by_group:
        context.errors.append(
            f"session business push {push_id}: unknown event_group_id '{group_id}'"
        )
    _validate_push_evidence(context, push_id, push, action_id)
    _validate_push_anomaly(context, push_id, push, action_id, group_id)
    if (
        classification not in {"companion", "unplanned_relevant"}
        and group_id in context.event_by_group
        and push.get("event_name") != context.event_by_group[group_id].get("event_name")
    ):
        context.errors.append(
            f"session business push {push_id}: event_name differs from mapped plan event"
        )


def _validate_push_counts(context: _ValidationContext) -> None:
    for action_id, action in context.action_by_id.items():
        if action.get("state") != "SETTLED":
            continue
        declared_count = action.get("observed_business_push_count")
        if not isinstance(declared_count, int) or declared_count < 0:
            context.errors.append(
                f"session action {action_id}: observed_business_push_count is required"
            )
        elif declared_count != len(context.pushes_by_action.get(action_id, [])):
            context.errors.append(
                f"session action {action_id}: observed business push count does not "
                "match classified stream rows"
            )


def _validate_pushes(context: _ValidationContext) -> None:
    for push_id, push in context.push_by_id.items():
        _validate_push(context, push_id, push)
    if context.results_provided:
        context.errors.extend(
            (
                f"unexpected {unexpected.get('unexpected_id')}: observed_push_id "
                "is absent from the session stream"
            )
            for unexpected in context.unexpected_rows
            if (observed_push_id := str(unexpected.get("observed_push_id", "")).strip())
            and observed_push_id not in context.push_by_id
        )
    _validate_push_counts(context)


def _validate_requirement_action_links(context: _ValidationContext) -> None:
    for requirement_id, requirement in context.by_requirement.items():
        boundary = requirement.get("action_boundary")
        if not isinstance(boundary, dict):
            continue
        action_id = str(boundary.get("action_id", "")).strip()
        action = context.action_by_id.get(action_id)
        if action is None:
            context.errors.append(
                f"requirement {requirement_id}: action_boundary action_id is absent "
                "from the session ledger"
            )
        elif requirement_id not in action.get("requirement_ids", []):
            context.errors.append(
                f"requirement {requirement_id}: session action does not cover requirement"
            )
        else:
            _validate_action_boundary_link(requirement, action, context.errors)


def _session_event_status(
    context: _ValidationContext,
    group_id: str,
    group_cases: list[dict[str, Any]],
) -> str:
    statuses: list[str] = []
    for case in group_cases:
        execution_status = case.get("execution_status")
        if execution_status == "BLOCKED":
            statuses.append("BLOCKED")
        elif execution_status == "NOT_TESTED":
            statuses.append("NOT_TESTED")
        elif execution_status == "EXECUTED":
            action = context.action_by_id.get(
                str(case.get("final_action_id", "")).strip(),
                {},
            )
            statuses.extend(
                str(row.get("status", "")).strip().upper()
                for row in action.get("layer_results", [])
                if isinstance(row, dict)
            )
    if context.anomalous_by_group.get(group_id):
        statuses.append("FAIL")
    return worst_status(statuses)


def _validate_event_statuses(context: _ValidationContext) -> None:
    for group_id, group_requirements in context.requirements_by_group.items():
        group_cases = [
            case
            for case in context.cases
            if str(case.get("event_group_id", "")).strip() == group_id
        ]
        if not group_cases:
            context.errors.append(
                f"session: event_group_id {group_id} has no registered interaction case"
            )
            continue
        session_status = _session_event_status(context, group_id, group_cases)
        normalized_status = _normalized_event_status(group_requirements)
        if context.final and session_status != normalized_status:
            context.errors.append(
                f"session event {group_id}: execution status {session_status} "
                f"does not match normalized status {normalized_status}"
            )


def _validate_result_alignment(context: _ValidationContext) -> None:
    if not context.results_provided:
        return
    _validate_requirement_action_links(context)
    _validate_event_statuses(context)


def validate_session(
    ledger: dict[str, Any],
    *,
    results: dict[str, Any] | None = None,
    final: bool = False,
) -> list[str]:
    """Return structural and final-certification errors for a session ledger."""
    if ledger.get("schema_version") != SESSION_SCHEMA_VERSION:
        return [
            "session: schema_version must be 2; recreate the session ledger with "
            "the current preview_session_ledger.py"
        ]
    errors: list[str] = []
    _validate_session_metadata(ledger, errors)
    cases = rows(ledger.get("cases"), "cases", errors)
    actions = rows(ledger.get("actions"), "actions", errors)
    pushes = rows(ledger.get("business_pushes"), "business_pushes", errors)
    authorizations = rows(ledger.get("authorizations"), "authorizations", errors)
    by_requirement, requirements_by_group, event_by_group, evidence = _result_catalogs(results)
    unexpected_rows = [
        row for row in (results or {}).get("unexpected", []) if isinstance(row, dict)
    ]
    context = _ValidationContext(
        final=final,
        results_provided=results is not None,
        errors=errors,
        cases=cases,
        actions=actions,
        case_by_id=_unique_ids(cases, "case_id", "case", errors),
        action_by_id=_unique_ids(actions, "action_id", "action", errors),
        push_by_id=_unique_ids(pushes, "push_id", "business push", errors),
        authorization_by_id=_validate_authorizations(authorizations, errors),
        by_requirement=by_requirement,
        requirements_by_group=requirements_by_group,
        event_by_group=event_by_group,
        evidence=evidence,
        unexpected_rows=unexpected_rows,
        unexpected_by_push=_unexpected_by_push(unexpected_rows),
        container_count=(
            len(
                [
                    row
                    for row in (results or {}).get("run", {}).get("containers", [])
                    if isinstance(row, dict)
                ]
            )
            or 1
        ),
    )
    _validate_actions(context)
    _validate_cases(context)
    _validate_pushes(context)
    _validate_result_alignment(context)
    return errors


def case_action_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return concise case/action rows for feedback and workbook output."""
    actions_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for action in ledger.get("actions", []):
        if isinstance(action, dict):
            actions_by_case[str(action.get("case_id", ""))].append(action)
    output = []
    for case in ledger.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_actions = sorted(
            actions_by_case.get(str(case.get("case_id", "")), []),
            key=lambda row: row.get("attempt_number", 0),
        )
        if not case_actions:
            case_actions = [{}]
        output.extend(
            {
                "event_group_id": case.get("event_group_id"),
                "case_id": case.get("case_id"),
                "scope_status": case.get("scope_status"),
                "execution_status": case.get("execution_status"),
                "url": case.get("url"),
                "element": case.get("element"),
                "placement": case.get("placement"),
                "action": case.get("action"),
                "material_variant": case.get("material_variant"),
                "discovered_from": case.get("discovered_from"),
                "applicable_layers": case.get("applicable_layers"),
                "blocker_id": case.get("blocker_id"),
                "case_reason": case.get("reason"),
                "final_action_id": case.get("final_action_id"),
                "action_id": action.get("action_id"),
                "attempt_number": action.get("attempt_number"),
                "retry_of_action_id": action.get("retry_of_action_id"),
                "interaction_outcome": action.get("interaction_outcome"),
                "completion_signal": action.get("completion_signal"),
                "stream_settled": action.get("stream_settled"),
                "settlement_reason": action.get("settlement_reason"),
                "observed_business_push_count": action.get("observed_business_push_count"),
                "layer_results": action.get("layer_results"),
            }
            for action in case_actions
        )
    return output


def business_push_rows(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the compact chronological business-push stream."""
    return sorted(
        [dict(row) for row in ledger.get("business_pushes", []) if isinstance(row, dict)],
        key=lambda row: (
            str(row.get("stream_id", "")),
            row.get("event_index", -1),
            str(row.get("captured_at", "")),
        ),
    )
