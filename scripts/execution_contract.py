#!/usr/bin/env python3
"""Validate interaction coverage, action windows, and observed business pushes."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from acceptance_contract import ACTION_BOUNDARY_FIELDS, expects_absence, worst_status
from evidence_contract import (
    ACTION_BOUND_EVIDENCE_KINDS,
    CONTAINER_BOUND_EVIDENCE_KINDS,
    DIRECT_CAPTURE_KINDS,
    EVENT_INDEX_EVIDENCE_KINDS,
)
from layer_contract import (
    CANONICAL_LAYERS,
    LAYER_APPLICABILITY_MODES,
    TAG_CATEGORIES,
    TAG_DELIVERY_TYPES,
    TAG_RESULT_LAYERS,
    TAG_SCOPE_STATUSES,
    inferred_tag_category,
    layer_applicability,
    normalize_tag_scope,
    tag_scope_decision,
)
from runtime_state_contract import (
    INTERRUPTION_REASONS,
    runtime_snapshot_errors,
    validate_runtime_evidence,
)
from tag_evidence_contract import (
    evidence_matches_tag,
    has_network_capture,
    request_evidence_ids,
    session_sensitive_findings,
    validate_comparisons,
    validate_expected_field,
)

SESSION_SCHEMA_VERSION = 3
CASE_SCOPE_STATUSES = {"IN_SCOPE", "OUT_OF_SCOPE"}
CASE_EXECUTION_STATUSES = {"PENDING", "EXECUTED", "BLOCKED", "NOT_TESTED"}
LAYER_RESULT_STATUSES = {"PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_APPLICABLE"}
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
    "prior_run",
}
AUTHORIZATION_SCOPES = {
    "complete_ordinary_journeys",
    "safe_synthetic_identity",
    "ordinary_form_submission",
    "nonproduction_lead_submission",
    "production_reversible_submission",
    "cmp_session_override",
    "production_cmp_session_override",
}
PROTECTED_AUTHORIZATION_EXCLUSIONS = (
    "CREDENTIALS",
    "GOOGLE_SIGN_IN",
    "MFA",
    "CAPTCHA",
    "EMAIL_VERIFICATION",
    "SMS_VERIFICATION",
    "MAGIC_LINK",
    "REAL_PAYMENT",
    "EXTERNAL_APPROVAL",
    "IRREVERSIBLE_ACTION",
)
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
    "action_boundary": {"action_boundary"},
    "raw_api_call": {"api_call", "action_boundary"},
    "resolved_data_layer": {"resolved_data_layer"},
    "concerned_tag_inventory": {"tag_inventory", "tag_configuration"},
    "gtm_variable": {"gtm_variable"},
    "tag_configuration": {"tag_configuration", "tag_inventory"},
    "tag_firing": {"tag_runtime", "tag_inventory"},
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
    "destination_request_when_applicable": {
        "browser_network_request",
        "browser_network_capture",
        "tag_configuration",
    },
    "trigger_logic_when_applicable": {"trigger_evaluation"},
    "tag_sequence_when_applicable": {"tag_sequence"},
    "business_rules_when_declared": {
        "business_rule_evaluation",
        "api_call",
        "resolved_data_layer",
        "tag_runtime",
        "browser_network_request",
    },
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


def _normalized_event_status(
    requirements: list[dict[str, Any]],
    unexpected: list[dict[str, Any]] | None = None,
) -> str:
    return worst_status(
        [
            row.get("verdict", {}).get("overall")
            for row in requirements
            if isinstance(row.get("verdict"), dict)
        ]
        + [row.get("status") for row in (unexpected or []) if isinstance(row, dict)]
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
    result_status = str(layer_result.get("status", "")).strip().upper()
    requires_allowed_kind = result_status not in {"BLOCKED", "NOT_APPLICABLE"} or (
        layer == "consent_when_applicable" and result_status == "NOT_APPLICABLE"
    )
    if requires_allowed_kind and not seen_allowed:
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
        for field_name in ACTION_BOUNDARY_FIELDS
        if boundary.get(field_name) != action.get(field_name)
    )


@dataclass
class _ValidationContext:
    ledger: dict[str, Any]
    operator_contract_version: int | None
    final: bool
    results_provided: bool
    errors: list[str]
    cases: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    runtime_checks: list[dict[str, Any]]
    event_closures: list[dict[str, Any]]
    closure_history: list[dict[str, Any]]
    case_by_id: dict[str, dict[str, Any]]
    action_by_id: dict[str, dict[str, Any]]
    runtime_by_id: dict[str, dict[str, Any]]
    push_by_id: dict[str, dict[str, Any]]
    authorization_by_id: dict[str, dict[str, Any]]
    by_requirement: dict[str, dict[str, Any]]
    requirements_by_group: dict[str, list[dict[str, Any]]]
    event_by_group: dict[str, dict[str, Any]]
    evidence: dict[str, dict[str, Any]]
    unexpected_rows: list[dict[str, Any]]
    unexpected_by_push: dict[str, dict[str, Any]]
    container_count: int
    run: dict[str, Any]
    actions_by_case: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    pushes_by_action: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    anomalous_by_group: dict[str, list[dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )
    push_indexes: set[tuple[str, int, int]] = field(default_factory=set)


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
    action_rows = [row for row in ledger.get("actions", []) if isinstance(row, dict)]
    disconnected_accounted_for = bool(
        action_rows
        and action_rows[-1].get("state") == "SETTLED"
        and action_rows[-1].get("settlement_reason") == "preview_disconnected"
    )
    if (
        tag_assistants
        and not all(row.get("connected") is True for row in tag_assistants)
        and not disconnected_accounted_for
    ):
        errors.append("session: Tag Assistant is not recorded as connected")
    connection_epoch = ledger.get("connection_epoch", 1)
    if (
        not isinstance(connection_epoch, int)
        or isinstance(connection_epoch, bool)
        or connection_epoch < 1
    ):
        errors.append("session: connection_epoch must be a positive integer")


def _validate_layer_result(
    context: _ValidationContext,
    action: dict[str, Any],
    layer_result: Any,
    case_contract: dict[str, Any] | None = None,
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
    case = case_contract or context.case_by_id.get(str(action.get("case_id", "")), {})
    decisions = {
        str(row.get("layer", "")): row
        for row in case.get("layer_applicability", [])
        if isinstance(row, dict)
    }
    decision = decisions.get(layer)
    if decision is None:
        context.errors.append(
            f"session action {action_id} layer {layer}: absent from applicability card"
        )
    else:
        predicate_result = layer_result.get("predicate_result")
        if decision.get("mode") == "MANDATORY":
            if result_status == "NOT_APPLICABLE":
                context.errors.append(
                    f"session action {action_id} layer {layer}: mandatory layer cannot be "
                    "NOT_APPLICABLE"
                )
            if predicate_result is False:
                context.errors.append(
                    f"session action {action_id} layer {layer}: mandatory predicate cannot be false"
                )
        elif decision.get("mode") == "CONDITIONAL":
            if not isinstance(predicate_result, bool):
                context.errors.append(
                    f"session action {action_id} layer {layer}: conditional layer requires "
                    "boolean predicate_result"
                )
            elif predicate_result is False and result_status != "NOT_APPLICABLE":
                context.errors.append(
                    f"session action {action_id} layer {layer}: false predicate requires "
                    "NOT_APPLICABLE"
                )
            elif predicate_result is True and result_status == "NOT_APPLICABLE":
                context.errors.append(
                    f"session action {action_id} layer {layer}: true predicate cannot be "
                    "NOT_APPLICABLE"
                )
    if context.results_provided:
        _validate_direct_evidence(
            layer=layer,
            layer_result=layer_result,
            action=action,
            evidence=context.evidence,
            errors=context.errors,
        )


def _tag_result_status(rows: list[dict[str, Any]]) -> str:
    statuses = [
        str(row.get("status", "")).strip().upper()
        for row in rows
        if str(row.get("status", "")).strip().upper() != "NOT_APPLICABLE"
    ]
    return worst_status(statuses) if statuses else "NOT_APPLICABLE"


def _validate_tag_layer_result_evidence(
    context: _ValidationContext,
    action: dict[str, Any],
    row: dict[str, Any],
) -> None:
    action_id = str(action.get("action_id", "")).strip()
    tag_id = str(row.get("tag_id", "")).strip()
    layer = str(row.get("layer", "")).strip()
    status = str(row.get("status", "")).strip().upper()
    refs = row.get("evidence_ids")
    if not isinstance(refs, list) or not refs:
        context.errors.append(
            f"session action {action_id} tag {row.get('tag_id')} layer {layer}: "
            "evidence_ids are required"
        )
        return
    allowed = LAYER_EVIDENCE_KINDS.get(layer, set())
    allowed_seen = False
    for ref_value in refs:
        ref = str(ref_value).strip()
        evidence = context.evidence.get(ref)
        if evidence is None:
            context.errors.append(
                f"session action {action_id} tag {row.get('tag_id')} layer {layer}: "
                f"unknown evidence ID '{ref}'"
            )
            continue
        kind = str(evidence.get("kind", "")).strip()
        tag_matches = evidence_matches_tag(evidence, tag_id)
        if not tag_matches:
            context.errors.append(
                f"session action {action_id} tag {tag_id} layer {layer}: "
                f"evidence '{ref}' is not bound to this exact tag"
            )
        allowed_seen = allowed_seen or (kind in allowed and tag_matches)
        _validate_direct_evidence_row(
            ref,
            evidence,
            action_id,
            {str(value).strip() for value in action.get("container_ids", []) if str(value).strip()},
            context.errors,
        )
    if status not in {"BLOCKED", "NOT_APPLICABLE"} and not allowed_seen:
        context.errors.append(
            f"session action {action_id} tag {row.get('tag_id')} layer {layer}: "
            "no direct evidence of the required kind"
        )


def _validate_tag_comparisons(
    *,
    context: _ValidationContext,
    action: dict[str, Any],
    items: Any,
    label: str,
    parent_status: str,
) -> None:
    validate_comparisons(
        items=items,
        label=label,
        parent_status=parent_status,
        requirements=context.by_requirement,
        allowed_requirement_ids=action.get("requirement_ids", []),
        errors=context.errors,
    )


def _validate_tag_value_layer(
    context: _ValidationContext,
    action: dict[str, Any],
    *,
    layer: str,
    result_status: str,
    details: dict[str, Any],
    label: str,
) -> None:
    """Validate variable, configuration, and runtime-parameter comparison layers."""
    if layer == "gtm_variable" and result_status == "NOT_APPLICABLE":
        if details.get("no_gtm_variable_reference") is not True:
            context.errors.append(
                f"{label}: NOT_APPLICABLE requires positive no_gtm_variable_reference proof"
            )
        return
    if layer in {"tag_configuration", "tag_firing", "tag_parameter"} and (
        result_status == "NOT_APPLICABLE"
    ):
        context.errors.append(f"{label}: core tag layer cannot be NOT_APPLICABLE")
        return
    comparison_field = {
        "gtm_variable": "variables",
        "tag_configuration": "configuration",
        "tag_parameter": "parameters",
    }.get(layer)
    if comparison_field and result_status not in {"BLOCKED", "NOT_APPLICABLE"}:
        _validate_tag_comparisons(
            context=context,
            action=action,
            items=details.get(comparison_field),
            label=f"{label}.{comparison_field}",
            parent_status=result_status,
        )


def _validate_tag_firing_layer(
    context: _ValidationContext,
    action: dict[str, Any],
    *,
    result_status: str,
    details: dict[str, Any],
    label: str,
) -> None:
    """Validate firing expectation provenance, state, and exact count."""
    for field_name in ("expected_firing", "actual_firing", "fire_count"):
        if field_name not in details:
            context.errors.append(f"{label}: details.{field_name} is required")
    fire_count = details.get("fire_count")
    if not isinstance(fire_count, int) or isinstance(fire_count, bool) or fire_count < 0:
        context.errors.append(f"{label}: fire_count must be a non-negative integer")
    expected_firing = details.get("expected_firing")
    validate_expected_field(
        actual_expected=expected_firing,
        anchor=details.get("expected_firing_anchor"),
        requirements=context.by_requirement,
        allowed_requirement_ids=action.get("requirement_ids", []),
        label=f"{label}.expected_firing",
        errors=context.errors,
    )
    actual_firing = details.get("actual_firing")
    firing_matches = (
        (
            expected_firing == "fired_once"
            and actual_firing in {"fired", "fired_once"}
            and fire_count == 1
        )
        or (
            expected_firing == "fired"
            and actual_firing in {"fired", "fired_once"}
            and isinstance(fire_count, int)
            and fire_count >= 1
        )
        or (expected_firing in {"not_fired", "blocked"} and fire_count == 0)
    )
    if result_status == "PASS" and not firing_matches:
        context.errors.append(f"{label}: PASS contradicts expected firing/count")
    if result_status == "FAIL" and firing_matches:
        context.errors.append(f"{label}: FAIL contradicts matching firing/count")


def _validate_tag_destination_layer(
    context: _ValidationContext,
    action: dict[str, Any],
    inventory: dict[str, Any],
    row: dict[str, Any],
    *,
    result_status: str,
    details: dict[str, Any],
    label: str,
) -> None:
    """Validate tag delivery applicability and direct browser-request reconciliation."""
    delivery = inventory.get("tag_delivery")
    if delivery == "local_only":
        if result_status != "NOT_APPLICABLE":
            context.errors.append(f"{label}: local_only tag must be NOT_APPLICABLE")
        if details.get("local_only_configuration_proved") is not True:
            context.errors.append(
                f"{label}: local_only classification requires positive configuration proof"
            )
        return
    if result_status == "NOT_APPLICABLE":
        context.errors.append(f"{label}: browser-sending tag cannot be NOT_APPLICABLE")
    request_count = details.get("request_count")
    if not isinstance(request_count, int) or isinstance(request_count, bool) or request_count < 0:
        context.errors.append(f"{label}: request_count must be a non-negative integer")
    expected_request = details.get("expected_request_behavior")
    validate_expected_field(
        actual_expected=expected_request,
        anchor=details.get("expected_request_behavior_anchor"),
        requirements=context.by_requirement,
        allowed_requirement_ids=action.get("requirement_ids", []),
        label=f"{label}.expected_request_behavior",
        errors=context.errors,
    )
    expects_no_request = expected_request in {"absent", "blocked"}
    if result_status == "PASS" and expects_no_request and request_count != 0:
        context.errors.append(f"{label}: PASS expected absence requires request_count=0")
    if (
        result_status == "PASS"
        and not expects_no_request
        and (
            not isinstance(request_count, int)
            or request_count < 1
            or not isinstance(details.get("request_ids"), list)
            or not details.get("request_ids")
        )
    ):
        context.errors.append(f"{label}: PASS requires matching browser request IDs")
    if result_status not in {"BLOCKED", "NOT_APPLICABLE"}:
        _validate_tag_comparisons(
            context=context,
            action=action,
            items=details.get("parameters"),
            label=f"{label}.parameters",
            parent_status=result_status,
        )
    refs = row.get("evidence_ids") if isinstance(row.get("evidence_ids"), list) else []
    tag_id = str(row.get("tag_id", "")).strip()
    proved_ids = request_evidence_ids(refs, context.evidence, tag_id)
    declared_ids = (
        {str(value).strip() for value in details.get("request_ids", []) if str(value).strip()}
        if isinstance(details.get("request_ids"), list)
        else set()
    )
    if isinstance(request_count, int) and not isinstance(request_count, bool):
        if request_count != len(declared_ids):
            context.errors.append(
                f"{label}: request_count differs from the unique declared request IDs"
            )
        if declared_ids != proved_ids:
            context.errors.append(
                f"{label}: request_ids do not reconcile with referenced network evidence"
            )
    if (
        expects_no_request
        and result_status not in {"BLOCKED", "NOT_APPLICABLE"}
        and not has_network_capture(refs, context.evidence)
    ):
        context.errors.append(
            f"{label}: expected request absence requires complete network-capture evidence"
        )
    if result_status == "BLOCKED" and not (
        details.get("capture_unavailable") is True or details.get("upstream_source_absent") is True
    ):
        context.errors.append(
            f"{label}: BLOCKED is reserved for genuinely unavailable network capture; "
            "or an explicitly absent upstream source; an available capture with no "
            "match is FAIL after tag execution"
        )


def _validate_tag_conditional_layer(
    context: _ValidationContext,
    action: dict[str, Any],
    aggregate_by_layer: dict[str, dict[str, Any]],
    *,
    tag_id: str,
    layer: str,
    result_status: str,
    label: str,
) -> None:
    """Validate tag-level conditional predicates and automatic trigger diagnosis."""
    if layer not in {
        "consent_when_applicable",
        "trigger_logic_when_applicable",
        "tag_sequence_when_applicable",
    }:
        return
    predicate_result = aggregate_by_layer.get(layer, {}).get("predicate_result")
    if result_status == "NOT_APPLICABLE" and predicate_result is not False:
        context.errors.append(
            f"{label}: NOT_APPLICABLE requires the event-level predicate to be false"
        )
    if result_status != "NOT_APPLICABLE" and predicate_result is False:
        context.errors.append(f"{label}: false event-level predicate requires NOT_APPLICABLE")
    if layer != "trigger_logic_when_applicable":
        return
    firing_row = next(
        (
            candidate
            for candidate in action.get("tag_layer_results", [])
            if isinstance(candidate, dict)
            and candidate.get("tag_id") == tag_id
            and candidate.get("layer") == "tag_firing"
        ),
        {},
    )
    if (
        str(firing_row.get("status", "")).strip().upper() in {"FAIL", "BLOCKED", "REVIEW"}
        and predicate_result is not True
    ):
        context.errors.append(
            f"{label}: firing anomaly automatically activates trigger/exception diagnosis"
        )


def _validate_one_tag_layer_result(
    context: _ValidationContext,
    action: dict[str, Any],
    inventory: dict[str, Any],
    row: dict[str, Any],
    aggregate_by_layer: dict[str, dict[str, Any]],
) -> None:
    action_id = str(action.get("action_id", "")).strip()
    tag_id = str(row.get("tag_id", "")).strip()
    layer = str(row.get("layer", "")).strip()
    result_status = str(row.get("status", "")).strip().upper()
    label = f"session action {action_id} tag {tag_id} layer {layer}"
    if layer not in TAG_RESULT_LAYERS:
        context.errors.append(f"{label}: unsupported per-tag layer")
    if result_status not in LAYER_RESULT_STATUSES:
        context.errors.append(f"{label}: invalid status '{result_status}'")
    if row.get("action_id") != action_id:
        context.errors.append(f"{label}: action_id differs from its action")
    for tag_field in ("tag_name", "container_id", "tag_category", "tag_delivery"):
        if row.get(tag_field) != inventory.get(tag_field):
            context.errors.append(f"{label}: {tag_field} differs from frozen tag inventory")
    if not nonempty(row.get("reason")):
        context.errors.append(f"{label}: concise reason is required")
    details = row.get("details")
    if not isinstance(details, dict):
        context.errors.append(f"{label}: details must be an object")
        details = {}
    if result_status == "REVIEW" and not nonempty(row.get("semantic_ambiguity")):
        context.errors.append(f"{label}: REVIEW requires semantic_ambiguity")
    if result_status == "BLOCKED" and not nonempty(row.get("blocker_id")):
        context.errors.append(f"{label}: BLOCKED requires blocker_id")

    _validate_tag_value_layer(
        context,
        action,
        layer=layer,
        result_status=result_status,
        details=details,
        label=label,
    )
    if layer == "tag_firing":
        _validate_tag_firing_layer(
            context,
            action,
            result_status=result_status,
            details=details,
            label=label,
        )
    if layer == "destination_request_when_applicable":
        _validate_tag_destination_layer(
            context,
            action,
            inventory,
            row,
            result_status=result_status,
            details=details,
            label=label,
        )
    _validate_tag_conditional_layer(
        context,
        action,
        aggregate_by_layer,
        tag_id=tag_id,
        layer=layer,
        result_status=result_status,
        label=label,
    )
    if context.results_provided:
        _validate_tag_layer_result_evidence(context, action, row)


def _validate_action_tag_results(
    context: _ValidationContext,
    action: dict[str, Any],
    case: dict[str, Any],
) -> None:
    action_id = str(action.get("action_id", "")).strip()
    rows_value = action.get("tag_layer_results")
    if not isinstance(rows_value, list):
        context.errors.append(f"session action {action_id}: tag_layer_results must be an array")
        rows_value = []
    rows = [row for row in rows_value if isinstance(row, dict)]
    if len(rows) != len(rows_value):
        context.errors.append(f"session action {action_id}: tag layer result must be an object")
    inventory_by_id = {
        str(row.get("tag_id", "")).strip(): row
        for row in case.get("tag_inventory", [])
        if isinstance(row, dict) and row.get("scope_status") == "IN_SCOPE"
    }
    keys = [(str(row.get("tag_id", "")).strip(), str(row.get("layer", "")).strip()) for row in rows]
    duplicates = sorted(key for key, count in Counter(keys).items() if count > 1)
    if duplicates:
        context.errors.append(
            f"session action {action_id}: duplicate per-tag layer results "
            + ", ".join(f"{tag}:{layer}" for tag, layer in duplicates)
        )
    expected_keys = {(tag_id, layer) for tag_id in inventory_by_id for layer in TAG_RESULT_LAYERS}
    actual_keys = set(keys)
    interrupted = (
        action.get("state") == "SETTLED"
        and action.get("settlement_reason") in INTERRUPTION_REASONS
        and action.get("interaction_outcome") == "uncertain"
    )
    require_complete = (action.get("state") == "SETTLED" or context.final) and not interrupted
    if require_complete and actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        if missing:
            context.errors.append(
                f"session action {action_id}: omitted per-tag layers "
                + ", ".join(f"{tag}:{layer}" for tag, layer in missing)
            )
        if extra:
            context.errors.append(
                f"session action {action_id}: tag results reference excluded/unknown tags "
                + ", ".join(f"{tag}:{layer}" for tag, layer in extra)
            )
    aggregate_by_layer = {
        str(row.get("layer", "")): row
        for row in action.get("layer_results", [])
        if isinstance(row, dict)
    }
    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        tag_id = str(row.get("tag_id", "")).strip()
        inventory = inventory_by_id.get(tag_id)
        if inventory is None:
            continue
        _validate_one_tag_layer_result(context, action, inventory, row, aggregate_by_layer)
        by_layer[str(row.get("layer", ""))].append(row)

    if not require_complete:
        return
    inventory_result = aggregate_by_layer.get("concerned_tag_inventory", {})
    if inventory_by_id:
        if str(inventory_result.get("status", "")).strip().upper() != "PASS":
            context.errors.append(
                f"session action {action_id}: complete inventory with in-scope tags requires "
                "concerned_tag_inventory=PASS"
            )
        for layer in TAG_RESULT_LAYERS:
            aggregate_status = str(aggregate_by_layer.get(layer, {}).get("status", "")).upper()
            expected_status = _tag_result_status(by_layer.get(layer, []))
            if aggregate_status != expected_status:
                context.errors.append(
                    f"session action {action_id}: aggregate {layer}={aggregate_status or 'blank'} "
                    f"differs from per-tag result {expected_status}"
                )
    else:
        group_requirements = context.requirements_by_group.get(
            str(case.get("event_group_id", "")), []
        )
        has_data_layer = any(
            isinstance(row.get("expectation"), dict)
            and row["expectation"].get("source_mechanism", "data_layer_push") == "data_layer_push"
            for row in group_requirements
        )
        if not has_data_layer:
            return
        expected_without_tag = {
            "concerned_tag_inventory": "FAIL",
            "tag_configuration": "FAIL",
            "tag_firing": "FAIL",
            "gtm_variable": "BLOCKED",
            "tag_parameter": "BLOCKED",
            "destination_request_when_applicable": "BLOCKED",
        }
        for layer, expected_status in expected_without_tag.items():
            actual = str(aggregate_by_layer.get(layer, {}).get("status", "")).upper()
            if actual != expected_status:
                context.errors.append(
                    f"session action {action_id}: no in-scope analytics tag requires "
                    f"{layer}={expected_status}, got {actual or 'blank'}"
                )


def _case_contract_for_action(case: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    """Return the immutable inventory/applicability revision used by one action."""
    revision = action.get("inventory_revision", 1)
    current_revision = case.get("inventory_revision", 1)
    if revision == current_revision:
        return case
    snapshot = next(
        (
            row
            for row in case.get("applicability_history", [])
            if isinstance(row, dict) and row.get("inventory_revision") == revision
        ),
        None,
    )
    if snapshot is None:
        return case
    return {
        **case,
        "inventory_revision": revision,
        "tag_inventory": snapshot.get("tag_inventory", []),
        "layer_applicability": snapshot.get("layer_applicability", []),
        "applicable_layers": snapshot.get("applicable_layers", []),
    }


def _validate_operator_action_boundary(
    context: _ValidationContext,
    action: dict[str, Any],
) -> None:
    """Bind action cursors and readiness claims to captured runtime checks."""
    if context.operator_contract_version != 1:
        return
    action_id = str(action.get("action_id", "")).strip()
    case_id = str(action.get("case_id", "")).strip()
    readiness_id = str(action.get("readiness_check_id", "")).strip()
    readiness = context.runtime_by_id.get(readiness_id)
    if not readiness_id:
        context.errors.append(f"session action {action_id}: readiness_check_id is required")
    elif readiness is None:
        context.errors.append(
            f"session action {action_id}: readiness_check_id is absent from runtime checks"
        )
    else:
        if (
            readiness.get("phase") != "before_action"
            or readiness.get("action_id") != action_id
            or readiness.get("case_id") != case_id
        ):
            context.errors.append(
                f"session action {action_id}: readiness check has the wrong phase or identity"
            )
        if (
            readiness.get("consumed") is not True
            or readiness.get("consumed_by_action_id") != action_id
        ):
            context.errors.append(
                f"session action {action_id}: readiness check was not consumed by this action"
            )
        expected_pairs = {
            "last_event_before": "preview_event_cursor",
            "network_request_cursor_before": "network_request_cursor",
            "browser_context_id": "browser_context_id",
            "observed_url_before": "website_url",
            "selected_page_url_before": "selected_page_url",
        }
        for action_field, check_field in expected_pairs.items():
            if action.get(action_field) != readiness.get(check_field):
                context.errors.append(
                    f"session action {action_id}: {action_field} differs from readiness capture"
                )
        if (
            action.get("preview_connected_before") is not True
            or action.get("target_ready_before") is not True
        ):
            context.errors.append(
                f"session action {action_id}: captured readiness is not fully satisfied"
            )

    before_network = action.get("network_request_cursor_before")
    if (
        not isinstance(before_network, int)
        or isinstance(before_network, bool)
        or before_network < 0
    ):
        context.errors.append(
            f"session action {action_id}: network_request_cursor_before must be non-negative"
        )
    if action.get("state") != "SETTLED":
        return
    settlement_id = str(action.get("settlement_check_id", "")).strip()
    settlement = context.runtime_by_id.get(settlement_id)
    if not settlement_id:
        context.errors.append(f"session action {action_id}: settlement_check_id is required")
        return
    if settlement is None:
        context.errors.append(
            f"session action {action_id}: settlement_check_id is absent from runtime checks"
        )
        return
    if (
        settlement.get("phase") not in {"after_action", "interrupted_action"}
        or settlement.get("action_id") != action_id
        or settlement.get("case_id") != case_id
    ):
        context.errors.append(
            f"session action {action_id}: settlement check has the wrong phase or identity"
        )
    if (
        settlement.get("consumed") is not True
        or settlement.get("consumed_by_action_id") != action_id
    ):
        context.errors.append(
            f"session action {action_id}: settlement check was not consumed by this action"
        )
    expected_pairs = {
        "first_event_after": "first_event_after",
        "settled_final_event": "preview_event_cursor",
        "network_request_cursor_after": "network_request_cursor",
        "observed_business_push_count": "observed_business_push_count",
        "preview_connected_after": "preview_connected",
        "stream_settled": "stream_quiet",
    }
    for action_field, check_field in expected_pairs.items():
        if action.get(action_field) != settlement.get(check_field):
            context.errors.append(
                f"session action {action_id}: {action_field} differs from settlement capture"
            )
    if settlement.get("phase") == "interrupted_action":
        if action.get("interaction_outcome") != "uncertain":
            context.errors.append(
                f"session action {action_id}: interrupted settlement must be uncertain"
            )
        if action.get("settlement_reason") != settlement.get("failure_reason"):
            context.errors.append(
                f"session action {action_id}: interruption reason differs from its capture"
            )
        if not nonempty(action.get("interruption_blocker_id")) or not nonempty(
            action.get("interruption_reason")
        ):
            context.errors.append(
                f"session action {action_id}: retained interruption requires blocker ID and reason"
            )
    elif action.get("settlement_reason") in INTERRUPTION_REASONS:
        context.errors.append(
            f"session action {action_id}: a normal after_action capture cannot use an "
            "interruption settlement reason"
        )
    after_network = action.get("network_request_cursor_after")
    if not isinstance(after_network, int) or isinstance(after_network, bool) or after_network < 0:
        context.errors.append(
            f"session action {action_id}: network_request_cursor_after must be non-negative"
        )
    elif isinstance(before_network, int) and after_network < before_network:
        context.errors.append(f"session action {action_id}: network request cursor moved backwards")


def _validate_action(context: _ValidationContext, action: dict[str, Any]) -> None:
    action_id = str(action.get("action_id", "")).strip()
    case_id = str(action.get("case_id", "")).strip()
    case = context.case_by_id.get(case_id)
    if case is None:
        context.errors.append(f"session action {action_id}: unknown case_id '{case_id}'")
        return
    action_revision = action.get("inventory_revision", 1)
    if not isinstance(action_revision, int) or isinstance(action_revision, bool):
        context.errors.append(f"session action {action_id}: inventory_revision must be an integer")
    case_contract = _case_contract_for_action(case, action)
    if action_revision != case_contract.get("inventory_revision", 1):
        context.errors.append(
            f"session action {action_id}: inventory revision has no retained applicability card"
        )
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
    connection_epoch = action.get("connection_epoch", 1)
    if (
        not isinstance(connection_epoch, int)
        or isinstance(connection_epoch, bool)
        or connection_epoch < 1
    ):
        context.errors.append(
            f"session action {action_id}: connection_epoch must be a positive integer"
        )
    _validate_operator_action_boundary(context, action)
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
        _validate_layer_result(context, action, layer_result, case_contract)
    if (
        action.get("state") == "SETTLED"
        and action.get("interaction_outcome") == "completed"
        and action.get("stream_settled") is True
        and action.get("preview_connected_after") is True
        and action.get("expected_seen") is False
    ):
        group_requirements = context.requirements_by_group.get(
            str(case.get("event_group_id", "")), []
        )
        expected_data_layer_source = any(
            isinstance(row.get("expectation"), dict)
            and row["expectation"].get("source_mechanism", "data_layer_push") == "data_layer_push"
            and not expects_absence(row["expectation"])
            for row in group_requirements
        )
        if expected_data_layer_source:
            by_layer = {
                str(row.get("layer", "")): row for row in layer_results if isinstance(row, dict)
            }
            required_statuses = {
                "raw_api_call": "FAIL",
                "resolved_data_layer": "BLOCKED",
                "gtm_variable": "BLOCKED",
                "tag_configuration": "BLOCKED",
                "tag_firing": "BLOCKED",
                "tag_parameter": "BLOCKED",
                "destination_request_when_applicable": "BLOCKED",
            }
            for layer, expected_status in required_statuses.items():
                actual_status = str(by_layer.get(layer, {}).get("status", "")).upper()
                if actual_status != expected_status:
                    context.errors.append(
                        f"session action {action_id}: absent expected dataLayer source requires "
                        f"{layer}={expected_status}, got {actual_status or 'blank'}"
                    )
            for row in action.get("tag_layer_results", []):
                if not isinstance(row, dict):
                    continue
                layer = str(row.get("layer", ""))
                if layer not in {
                    "gtm_variable",
                    "tag_configuration",
                    "tag_firing",
                    "tag_parameter",
                    "destination_request_when_applicable",
                }:
                    continue
                actual_status = str(row.get("status", "")).upper()
                if actual_status != "BLOCKED":
                    context.errors.append(
                        f"session action {action_id} tag {row.get('tag_id')} layer {layer}: "
                        "absent upstream dataLayer source requires BLOCKED"
                    )
    _validate_action_tag_results(context, action, case_contract)


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
        if index > 0 and ordered[index - 1].get("state") != "SETTLED":
            errors.append(f"session case {case_id}: retry cannot follow an open attempt")


def _validate_actions(context: _ValidationContext) -> None:
    for action in context.actions:
        _validate_action(context, action)
    for case_id, case_actions in context.actions_by_case.items():
        _validate_attempt_chain(case_id, case_actions, context.errors)


def _validate_case_applicability_card(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
) -> list[str]:
    card = case.get("layer_applicability")
    if not isinstance(card, list) or any(not isinstance(row, dict) for row in card):
        context.errors.append(f"session case {case_id}: layer_applicability must be an array")
        return []
    layers = [str(row.get("layer", "")).strip() for row in card]
    if layers != list(CANONICAL_LAYERS):
        context.errors.append(
            f"session case {case_id}: applicability card must contain every canonical "
            "layer exactly once in canonical order"
        )
    for row in card:
        layer = str(row.get("layer", "")).strip()
        if row.get("mode") not in LAYER_APPLICABILITY_MODES:
            context.errors.append(
                f"session case {case_id} layer {layer}: invalid applicability mode"
            )
        for field_name in ("predicate", "reason"):
            if not nonempty(row.get(field_name)):
                context.errors.append(
                    f"session case {case_id} layer {layer}: applicability {field_name} is required"
                )
    has_action = any(row.get("case_id") == case_id for row in context.actions)
    if (
        case.get("scope_status") == "IN_SCOPE"
        and (context.final or has_action)
        and case.get("applicability_status") != "FROZEN"
    ):
        context.errors.append(f"session case {case_id}: applicability card is not frozen")
    return layers


def _validate_case_tag_inventory(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
) -> list[dict[str, Any]]:
    inventory = case.get("tag_inventory")
    if not isinstance(inventory, list) or any(not isinstance(row, dict) for row in inventory):
        context.errors.append(f"session case {case_id}: tag_inventory must be an array")
        return []
    has_action = any(row.get("case_id") == case_id for row in context.actions)
    if case.get("scope_status") == "IN_SCOPE" and (context.final or has_action):
        if case.get("tag_inventory_status") != "COMPLETE":
            context.errors.append(f"session case {case_id}: tag inventory is not COMPLETE")
        if not nonempty(case.get("tag_inventory_reason")):
            context.errors.append(f"session case {case_id}: tag inventory reason is required")
        refs = case.get("tag_inventory_evidence_ids")
        if not isinstance(refs, list) or not refs:
            context.errors.append(
                f"session case {case_id}: tag inventory requires direct evidence IDs"
            )
        else:
            inventory_kinds: set[str] = set()
            for ref_value in refs:
                ref = str(ref_value).strip()
                row = context.evidence.get(ref)
                if row is None:
                    context.errors.append(
                        f"session case {case_id}: unknown tag inventory evidence ID '{ref}'"
                    )
                elif row.get("kind") not in {"tag_inventory", "tag_configuration"}:
                    context.errors.append(
                        f"session case {case_id}: tag inventory evidence kind must be "
                        "tag_inventory or tag_configuration"
                    )
                else:
                    inventory_kinds.add(str(row.get("kind")))
            if not inventory and "tag_inventory" not in inventory_kinds:
                context.errors.append(
                    f"session case {case_id}: an empty inventory requires direct tag_inventory "
                    "evidence proving that no in-scope tag was found"
                )
    tag_ids = [str(row.get("tag_id", "")).strip() for row in inventory]
    duplicates = sorted(
        tag_id for tag_id, count in Counter(tag_ids).items() if tag_id and count > 1
    )
    if duplicates:
        context.errors.append(
            f"session case {case_id}: duplicate detected tag IDs " + ", ".join(duplicates)
        )
    tag_scope = normalize_tag_scope(case.get("tag_scope"))
    contracts = case.get("declared_tag_contracts", [])
    for index, tag in enumerate(inventory, start=1):
        label = f"session case {case_id} tag inventory row {index}"
        for field_name in (
            "tag_id",
            "tag_name",
            "container_id",
            "tag_category",
            "tag_delivery",
            "template_type",
            "scope_status",
            "scope_reason",
        ):
            if not nonempty(tag.get(field_name)):
                context.errors.append(f"{label}: missing '{field_name}'")
        if tag.get("tag_category") not in TAG_CATEGORIES:
            context.errors.append(f"{label}: invalid tag_category")
        inferred_category = inferred_tag_category(tag)
        if inferred_category is not None and tag.get("tag_category") != inferred_category:
            context.errors.append(
                f"{label}: tag_category contradicts direct vendor/template metadata "
                f"({inferred_category})"
            )
        if tag.get("tag_delivery") not in TAG_DELIVERY_TYPES:
            context.errors.append(f"{label}: invalid tag_delivery")
        if tag.get("scope_status") not in TAG_SCOPE_STATUSES:
            context.errors.append(f"{label}: invalid scope_status")
        if not isinstance(tag.get("consent_required"), bool):
            context.errors.append(f"{label}: consent_required must be boolean")
        if str(tag.get("container_id", "")) not in {
            str(value) for value in case.get("container_ids", [])
        }:
            context.errors.append(f"{label}: container_id is outside the case container set")
        expected_scope, expected_reason = tag_scope_decision(tag, tag_scope, contracts)
        if tag.get("scope_status") != expected_scope or tag.get("scope_reason") != expected_reason:
            context.errors.append(f"{label}: tag-scope decision differs from deterministic policy")
        refs = tag.get("evidence_ids")
        if not isinstance(refs, list) or not refs:
            context.errors.append(f"{label}: evidence_ids are required")
        else:
            for ref_value in refs:
                ref = str(ref_value).strip()
                evidence = context.evidence.get(ref)
                if evidence is None:
                    context.errors.append(f"{label}: unknown evidence ID '{ref}'")
                elif evidence.get("kind") not in {"tag_inventory", "tag_configuration"}:
                    context.errors.append(f"{label}: unsupported inventory evidence kind")
                elif evidence.get("kind") == "tag_configuration" and evidence.get(
                    "tag_id"
                ) != tag.get("tag_id"):
                    context.errors.append(
                        f"{label}: tag configuration evidence is not bound to this exact tag"
                    )
    return inventory


def _validate_case_applicability_history(
    context: _ValidationContext,
    case_id: str,
    case: dict[str, Any],
) -> None:
    """Validate immutable snapshots retained after controlled late tag discovery."""
    revision = case.get("inventory_revision", 1)
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        context.errors.append(f"session case {case_id}: inventory_revision must be positive")
        return
    history = case.get("applicability_history", [])
    if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
        context.errors.append(f"session case {case_id}: applicability_history must be an array")
        return
    if len(history) != revision - 1:
        context.errors.append(
            f"session case {case_id}: applicability history does not reconcile with revision"
        )
    expected_revisions = list(range(1, revision))
    actual_revisions = [row.get("inventory_revision") for row in history]
    if actual_revisions != expected_revisions:
        context.errors.append(
            f"session case {case_id}: applicability history revisions are not contiguous"
        )
    for snapshot in history:
        card = snapshot.get("layer_applicability")
        if not isinstance(card, list) or [
            str(row.get("layer", "")) for row in card if isinstance(row, dict)
        ] != list(CANONICAL_LAYERS):
            context.errors.append(
                f"session case {case_id}: historical applicability card is incomplete"
            )
        if not isinstance(snapshot.get("tag_inventory"), list):
            context.errors.append(
                f"session case {case_id}: historical tag inventory must be retained"
            )
        for field_name in ("frozen_at", "superseded_by_action_id", "superseded_reason"):
            if not nonempty(snapshot.get(field_name)):
                context.errors.append(
                    f"session case {case_id}: historical snapshot requires {field_name}"
                )
    required_retest = case.get("required_retest_of_action_id")
    if required_retest not in (None, ""):
        actions = context.actions_by_case.get(case_id, [])
        if not actions or required_retest not in {
            actions[-1].get("action_id"),
            actions[-1].get("retry_of_action_id"),
        }:
            context.errors.append(
                f"session case {case_id}: required late-discovery retest does not reference "
                "the retained latest action"
            )
        if case.get("execution_status") != "PENDING" or case.get("final_action_id") is not None:
            context.errors.append(
                f"session case {case_id}: late discovery must reset execution to PENDING"
            )


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
    _validate_case_applicability_card(context, case_id, case)
    _validate_case_tag_inventory(context, case_id, case)
    _validate_case_applicability_history(context, case_id, case)
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
    if normalize_tag_scope(case.get("tag_scope")) != normalize_tag_scope(
        context.run.get("tag_scope")
    ):
        context.errors.append(f"session case {case_id}: tag scope differs from the run contract")
    expected_card = layer_applicability(
        group_requirements,
        container_count=context.container_count,
        tag_inventory=[row for row in case.get("tag_inventory", []) if isinstance(row, dict)],
        activated_conditions=(
            case.get("conditional_activations")
            if isinstance(case.get("conditional_activations"), dict)
            else {}
        ),
    )
    if case.get("layer_applicability") != expected_card:
        context.errors.append(
            f"session case {case_id}: frozen applicability card differs from deterministic policy"
        )
    required_layers = [row["layer"] for row in expected_card if row.get("mode") == "MANDATORY"]
    if declared_layers != required_layers:
        context.errors.append(
            f"session case {case_id}: applicable_layers do not exactly match mandatory policy"
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
            missing = [layer for layer in CANONICAL_LAYERS if layer not in recorded_layers]
            if missing:
                context.errors.append(
                    f"session case {case_id}: final action omits explicit layer results "
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
    connection_epoch = push.get("connection_epoch", 1)
    if not isinstance(event_index, int) or isinstance(event_index, bool):
        context.errors.append(f"session business push {push_id}: event_index must be an integer")
        return
    if (
        not isinstance(connection_epoch, int)
        or isinstance(connection_epoch, bool)
        or connection_epoch < 1
    ):
        context.errors.append(
            f"session business push {push_id}: connection_epoch must be a positive integer"
        )
        return
    if connection_epoch != action.get("connection_epoch", 1):
        context.errors.append(
            f"session business push {push_id}: connection_epoch differs from its action"
        )
    key = (stream_id, connection_epoch, event_index)
    if key in context.push_indexes:
        context.errors.append(
            f"session business push {push_id}: duplicate stream/connection-epoch/event index"
        )
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
    if not nonempty(push.get("captured_at")):
        context.errors.append(f"session business push {push_id}: missing 'captured_at'")
    elif not iso_timestamp(push.get("captured_at")):
        context.errors.append(
            f"session business push {push_id}: captured_at must be ISO 8601 with timezone"
        )
    _validate_push_index(context, push_id, push, action)
    group_value = push.get("event_group_id")
    group_id = group_value.strip() if isinstance(group_value, str) else ""
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
        if case.get("scope_status") == "OUT_OF_SCOPE":
            continue
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
    for push in context.anomalous_by_group.get(group_id, []):
        unexpected = context.unexpected_by_push.get(str(push.get("push_id", "")).strip())
        if isinstance(unexpected, dict):
            statuses.append(unexpected.get("status"))
        else:
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
        normalized_status = _normalized_event_status(
            group_requirements,
            [
                row
                for row in context.unexpected_rows
                if str(row.get("event_group_id", "")).strip() == group_id
            ],
        )
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


def _validate_runtime_checks(context: _ValidationContext) -> None:
    """Validate captured readiness/settlement records and their direct proof."""
    if context.operator_contract_version != 1:
        return
    for check in context.runtime_checks:
        check_id = str(check.get("check_id", "")).strip()
        action_id = str(check.get("action_id", "")).strip()
        case_id = str(check.get("case_id", "")).strip()
        action = context.action_by_id.get(action_id)
        case = context.case_by_id.get(case_id)
        if check.get("voided") is True:
            if action is not None:
                context.errors.append(
                    f"session runtime check {check_id}: a voided check cannot resolve an action"
                )
            if check.get("consumed") is True or check.get("consumed_by_action_id") not in (
                None,
                "",
            ):
                context.errors.append(
                    f"session runtime check {check_id}: a voided check cannot be consumed"
                )
            if not nonempty(check.get("void_reason")):
                context.errors.append(f"session runtime check {check_id}: void_reason is required")
            if not iso_timestamp(check.get("voided_at")):
                context.errors.append(
                    f"session runtime check {check_id}: voided_at must be ISO 8601"
                )
            continue
        if action is None:
            context.errors.append(
                f"session runtime check {check_id}: action_id is absent from actions"
            )
            continue
        if case is None:
            context.errors.append(f"session runtime check {check_id}: case_id is absent from cases")
            continue
        if action.get("case_id") != case_id or check.get("event_group_id") != case.get(
            "event_group_id"
        ):
            context.errors.append(
                f"session runtime check {check_id}: action, case, and event identities differ"
            )
        if check.get("phase") not in {
            "before_action",
            "resume",
            "after_action",
            "interrupted_action",
        }:
            context.errors.append(
                f"session runtime check {check_id}: unsupported runtime-check phase"
            )
            continue
        if context.results_provided:
            for error in runtime_snapshot_errors(
                check,
                phase=str(check.get("phase")),
                action_id=action_id,
                case=case,
                ledger=context.ledger,
                results={"run": context.run},
                expected_connection_epoch=action.get("connection_epoch", 1),
                recorded_at=check.get("recorded_at"),
                action_timestamp=action.get("action_timestamp"),
            ):
                context.errors.append(f"session runtime check {check_id}: {error}")
            context.errors.extend(validate_runtime_evidence(check, context.evidence))
        if (
            check.get("phase") == "resume"
            and context.final
            and (
                check.get("consumed") is not True or check.get("consumed_by_action_id") != action_id
            )
        ):
            context.errors.append(
                f"session runtime check {check_id}: resume check was not consumed"
            )
    for action in context.actions:
        action_id = str(action.get("action_id", "")).strip()
        readiness = context.runtime_by_id.get(str(action.get("readiness_check_id", "")))
        settlement = context.runtime_by_id.get(str(action.get("settlement_check_id", "")))
        if readiness is None or settlement is None:
            continue
        overlap = sorted(
            set(readiness.get("evidence_ids", [])) & set(settlement.get("evidence_ids", []))
        )
        if overlap:
            context.errors.append(
                f"session action {action_id}: before/after runtime checks must use distinct "
                "action-window evidence IDs"
            )


def _ordered_event_inventory(context: _ValidationContext) -> list[dict[str, Any]]:
    inventory = [row for row in context.run.get("event_inventory", []) if isinstance(row, dict)]
    return [
        row
        for _, row in sorted(
            enumerate(inventory),
            key=lambda item: (
                item[1].get("plan_order") if isinstance(item[1].get("plan_order"), int) else 10**9,
                item[0],
            ),
        )
    ]


def _validate_event_closures(context: _ValidationContext) -> None:
    """Require plan-ordered event closure and immediate feedback acknowledgement."""
    if context.operator_contract_version != 1:
        return
    ordered_inventory = _ordered_event_inventory(context)
    expected_groups = [str(row.get("event_group_id", "")) for row in ordered_inventory]
    actual_groups = [str(row.get("event_group_id", "")).strip() for row in context.event_closures]
    if len(set(actual_groups)) != len(actual_groups):
        context.errors.append("session: event_closures contain duplicate event groups")
    if context.results_provided and actual_groups != expected_groups[: len(actual_groups)]:
        context.errors.append(
            "session: event_closures must follow the original tracking-plan order"
        )
    if context.final and context.results_provided and actual_groups != expected_groups:
        context.errors.append("session: final validation requires one closure for every plan event")
    inventory_by_group = {str(row.get("event_group_id", "")): row for row in ordered_inventory}
    for closure in context.event_closures:
        group_id = str(closure.get("event_group_id", "")).strip()
        label = f"session event closure {group_id}"
        inventory = inventory_by_group.get(group_id)
        if not group_id or (context.results_provided and inventory is None):
            context.errors.append(f"{label}: event_group_id is absent from event inventory")
            continue
        if inventory is not None and closure.get("plan_order") != inventory.get("plan_order"):
            context.errors.append(f"{label}: plan_order differs from event inventory")
        for field_name in ("closed_at", "feedback_emitted_at"):
            if not iso_timestamp(closure.get(field_name)):
                context.errors.append(f"{label}: {field_name} must be ISO 8601 with timezone")
        group_cases = [
            case
            for case in context.cases
            if str(case.get("event_group_id", "")).strip() == group_id
        ]
        expected_case_ids = [str(case.get("case_id", "")).strip() for case in group_cases]
        closure_case_ids = closure.get("case_ids")
        valid_case_ids = (
            isinstance(closure_case_ids, list)
            and all(nonempty(value) for value in closure_case_ids)
            and len(closure_case_ids) == len(set(closure_case_ids))
        )
        if not valid_case_ids or set(closure_case_ids) != set(expected_case_ids):
            context.errors.append(
                f"{label}: case_ids must exactly match the event's interaction cases"
            )
        expected_actions = [
            str(case.get("final_action_id", "")).strip()
            for case in group_cases
            if case.get("execution_status") == "EXECUTED"
        ]
        final_action_ids = closure.get("final_action_ids")
        valid_action_ids = (
            isinstance(final_action_ids, list)
            and all(nonempty(value) for value in final_action_ids)
            and len(final_action_ids) == len(set(final_action_ids))
        )
        if not valid_action_ids or set(final_action_ids) != set(expected_actions):
            context.errors.append(
                f"{label}: final_action_ids must exactly match executed final attempts"
            )
        if any(case.get("execution_status") == "PENDING" for case in group_cases):
            context.errors.append(f"{label}: cannot close an event with pending cases")
        if any(
            action.get("state") != "SETTLED"
            for action_id in expected_actions
            if (action := context.action_by_id.get(action_id)) is not None
        ):
            context.errors.append(f"{label}: a final action is not settled")


def _validate_closure_history(context: _ValidationContext) -> None:
    """Keep every explicit reopening auditable without treating old proof as current."""
    if context.operator_contract_version != 1:
        return
    inventory_order = {
        str(row.get("event_group_id", "")): index
        for index, row in enumerate(_ordered_event_inventory(context))
    }
    current_closures = {str(row.get("event_group_id", "")): row for row in context.event_closures}
    for index, history in enumerate(context.closure_history, start=1):
        label = f"session closure history {index}"
        reopened_group = str(history.get("reopened_event_group_id", "")).strip()
        if not reopened_group or (
            context.results_provided and reopened_group not in inventory_order
        ):
            context.errors.append(f"{label}: invalid reopened_event_group_id")
        if not iso_timestamp(history.get("reopened_at")):
            context.errors.append(f"{label}: reopened_at must be ISO 8601 with timezone")
        if not nonempty(history.get("reason")):
            context.errors.append(f"{label}: reason is required")
        invalidated = history.get("invalidated_closures")
        if (
            not isinstance(invalidated, list)
            or not invalidated
            or any(not isinstance(row, dict) for row in invalidated)
        ):
            context.errors.append(f"{label}: invalidated_closures must be a non-empty array")
            continue
        invalidated_groups = [str(row.get("event_group_id", "")).strip() for row in invalidated]
        for closure in invalidated:
            group_id = str(closure.get("event_group_id", "")).strip()
            if context.results_provided and group_id not in inventory_order:
                context.errors.append(f"{label}: invalidated closure has an unknown event")
            if not isinstance(closure.get("plan_order"), int) or isinstance(
                closure.get("plan_order"), bool
            ):
                context.errors.append(f"{label}: invalidated closure requires plan_order")
            for field_name in ("closed_at", "feedback_emitted_at"):
                if not iso_timestamp(closure.get(field_name)):
                    context.errors.append(
                        f"{label}: invalidated closure {field_name} must be ISO 8601"
                    )
        if invalidated_groups[0] != reopened_group:
            context.errors.append(f"{label}: invalidated suffix must start with reopened event")
        if len(set(invalidated_groups)) != len(invalidated_groups):
            context.errors.append(f"{label}: invalidated closures contain duplicate events")
        if context.results_provided and reopened_group in inventory_order:
            positions = [inventory_order.get(group) for group in invalidated_groups]
            expected = list(
                range(
                    inventory_order[reopened_group],
                    inventory_order[reopened_group] + len(invalidated_groups),
                )
            )
            if positions != expected:
                context.errors.append(
                    f"{label}: invalidated closures must preserve the plan-ordered suffix"
                )
        current = current_closures.get(reopened_group)
        prior = invalidated[0]
        if context.final and current is not None:
            current_cases = {
                value for value in current.get("case_ids", []) if isinstance(value, str)
            }
            prior_cases = {value for value in prior.get("case_ids", []) if isinstance(value, str)}
            current_actions = {
                value for value in current.get("final_action_ids", []) if isinstance(value, str)
            }
            prior_actions = {
                value for value in prior.get("final_action_ids", []) if isinstance(value, str)
            }
            if current_cases == prior_cases and current_actions == prior_actions:
                context.errors.append(
                    f"{label}: reopened target requires a new case or final action"
                )


def validate_session(
    ledger: dict[str, Any],
    *,
    results: dict[str, Any] | None = None,
    final: bool = False,
) -> list[str]:
    """Return structural and final-certification errors for a session ledger."""
    if ledger.get("schema_version") != SESSION_SCHEMA_VERSION:
        return [
            "session: schema_version must be 3; migrate or recreate the session ledger "
            "with the current preview_session_ledger.py"
        ]
    errors: list[str] = []
    operator_contract_version = ledger.get("operator_contract_version")
    if operator_contract_version not in (None, 1):
        errors.append("session: operator_contract_version must be 1 when supplied")
    if final and operator_contract_version == 1 and results is None:
        errors.append("session: operator-contract final validation requires normalized results")
    _validate_session_metadata(ledger, errors)
    cases = rows(ledger.get("cases"), "cases", errors)
    actions = rows(ledger.get("actions"), "actions", errors)
    pushes = rows(ledger.get("business_pushes"), "business_pushes", errors)
    authorizations = rows(ledger.get("authorizations"), "authorizations", errors)
    runtime_checks = (
        rows(ledger.get("runtime_checks"), "runtime_checks", errors)
        if operator_contract_version == 1
        else []
    )
    event_closures = (
        rows(ledger.get("event_closures"), "event_closures", errors)
        if operator_contract_version == 1
        else []
    )
    closure_history = (
        rows(ledger.get("closure_history", []), "closure_history", errors)
        if operator_contract_version == 1
        else []
    )
    if "connection_epoch" in ledger:
        expected_epoch = 1
        for action in actions:
            if action.get("connection_epoch") != expected_epoch:
                errors.append(
                    f"session action {action.get('action_id', '')}: connection_epoch must "
                    f"equal the explicit current epoch {expected_epoch}"
                )
            if (
                action.get("state") == "SETTLED"
                and action.get("settlement_reason") == "preview_disconnected"
            ):
                expected_epoch += 1
        if ledger.get("connection_epoch") != expected_epoch:
            errors.append(
                "session: connection_epoch does not reconcile with Preview disconnect boundaries"
            )
    by_requirement, requirements_by_group, event_by_group, evidence = _result_catalogs(results)
    unexpected_rows = [
        row for row in (results or {}).get("unexpected", []) if isinstance(row, dict)
    ]
    context = _ValidationContext(
        ledger=ledger,
        operator_contract_version=operator_contract_version,
        final=final,
        results_provided=results is not None,
        errors=errors,
        cases=cases,
        actions=actions,
        runtime_checks=runtime_checks,
        event_closures=event_closures,
        closure_history=closure_history,
        case_by_id=_unique_ids(cases, "case_id", "case", errors),
        action_by_id=_unique_ids(actions, "action_id", "action", errors),
        runtime_by_id=_unique_ids(
            runtime_checks,
            "check_id",
            "runtime check",
            errors,
        ),
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
        run=(results or {}).get("run", {})
        if isinstance((results or {}).get("run", {}), dict)
        else {},
    )
    _validate_actions(context)
    _validate_cases(context)
    _validate_pushes(context)
    _validate_runtime_checks(context)
    _validate_event_closures(context)
    _validate_closure_history(context)
    _validate_result_alignment(context)
    unsafe_session_findings = [
        finding
        for finding in session_sensitive_findings(ledger)
        if str(finding.get("status", "")).strip().upper() in {"FAIL", "REVIEW"}
    ]
    if unsafe_session_findings:
        paths = sorted({str(finding.get("path", "")) for finding in unsafe_session_findings})
        errors.append(
            "session contains unredacted sensitive content in exportable evidence at "
            + ", ".join(paths[:12])
            + (" and additional paths" if len(paths) > 12 else "")
        )
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
                "tag_scope": case.get("tag_scope"),
                "tag_inventory_status": case.get("tag_inventory_status"),
                "tag_inventory": case.get("tag_inventory"),
                "applicability_status": case.get("applicability_status"),
                "layer_applicability": case.get("layer_applicability"),
                "applicable_layers": case.get("applicable_layers"),
                "blocker_id": case.get("blocker_id"),
                "case_reason": case.get("reason"),
                "final_action_id": case.get("final_action_id"),
                "action_id": action.get("action_id"),
                "attempt_number": action.get("attempt_number"),
                "retry_of_action_id": action.get("retry_of_action_id"),
                "readiness_check_id": action.get("readiness_check_id"),
                "settlement_check_id": action.get("settlement_check_id"),
                "last_event_before": action.get("last_event_before"),
                "first_event_after": action.get("first_event_after"),
                "settled_final_event": action.get("settled_final_event"),
                "network_request_cursor_before": action.get("network_request_cursor_before"),
                "network_request_cursor_after": action.get("network_request_cursor_after"),
                "interaction_outcome": action.get("interaction_outcome"),
                "completion_signal": action.get("completion_signal"),
                "stream_settled": action.get("stream_settled"),
                "settlement_reason": action.get("settlement_reason"),
                "observed_business_push_count": action.get("observed_business_push_count"),
                "layer_results": action.get("layer_results"),
                "tag_layer_results": action.get("tag_layer_results"),
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
            row.get("connection_epoch", 1),
            row.get("event_index", -1),
            str(row.get("captured_at", "")),
        ),
    )
