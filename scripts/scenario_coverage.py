#!/usr/bin/env python3
"""Validate explainable scenario discovery, partitioning, and sampling decisions."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from typing import Any

COVERAGE_STATUSES = {"DRAFT", "FROZEN"}
DIMENSION_TREATMENTS = {"ENUMERATE", "SAMPLE", "PARTITION", "EXCLUDE", "BLOCKED"}
SELECTION_MODES = {"EXHAUSTIVE", "SAMPLED", "PARTITIONED", "SINGLETON", "BLOCKED"}
SAMPLE_ROLES = {
    "EXHAUSTIVE",
    "ORDINARY",
    "CONTRAST",
    "BOUNDARY",
    "EXCEPTION",
    "SINGLETON",
}
DISCOVERY_SOURCES = {
    "tracking_plan",
    "analyst_instruction",
    "supplied_url",
    "supplied_screenshot",
    "supplied_journey",
    "website_census",
    "visible_website_state",
    "runtime_discovery",
    "tag_assistant",
    "prior_run",
    "platform_semantics",
}
EXPANSION_TRIGGERS = {
    "NEW_BEHAVIOR_SIGNATURE",
    "ANOMALY_OR_FAILURE",
    "UNSEEN_MATERIAL_DIMENSION_VALUE",
    "CONDITIONAL_RUNTIME_BRANCH",
}
EXPANSION_OUTCOMES = {"NOT_TRIGGERED", "EXPANDED", "EXHAUSTED", "BLOCKED"}
CONDITIONAL_SAMPLE_ROLES = {"BOUNDARY", "EXCEPTION"}
ANOMALOUS_PUSH_CLASSIFICATIONS = {
    "duplicate",
    "premature",
    "delayed",
    "wrong_order",
    "wrong_context",
    "unplanned_relevant",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_timestamp(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _value_key(value: Any) -> str:
    """Return a stable comparison key for JSON-compatible dimension values."""
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return repr(value)


def _declared_values(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _object_rows(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    output: list[dict[str, Any]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"{label} row {index} must be an object")
        else:
            output.append(row)
    return output


def _unique(
    rows: list[dict[str, Any]], field: str, label: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    values = [str(row.get(field, "")).strip() for row in rows]
    for index, value in enumerate(values, start=1):
        if not value:
            errors.append(f"{label} row {index} missing {field}")
    duplicates = sorted(
        value for value, count in Counter(item for item in values if item).items() if count > 1
    )
    if duplicates:
        errors.append(f"duplicate {label} IDs " + ", ".join(duplicates))
    return {str(row.get(field, "")).strip(): row for row in rows if str(row.get(field, "")).strip()}


def _validate_dimension(
    decision_id: str,
    dimension: dict[str, Any],
    index: int,
    errors: list[str],
) -> None:
    label = f"coverage {decision_id} dimension {dimension.get('dimension_id') or index}"
    for field in ("dimension_id", "name", "source", "reason"):
        if not _nonempty(dimension.get(field)):
            errors.append(f"{label}: {field} is required")
    if dimension.get("source") not in DISCOVERY_SOURCES:
        errors.append(f"{label}: unsupported discovery source")
    treatment = str(dimension.get("treatment", "")).strip().upper()
    if treatment not in DIMENSION_TREATMENTS:
        errors.append(f"{label}: invalid treatment")
    values = dimension.get("values")
    if not isinstance(values, list) or not values:
        errors.append(f"{label}: values must be a non-empty array")
    elif any(item in (None, "") for item in values):
        errors.append(f"{label}: values cannot contain empty entries")
    elif len({repr(item) for item in values}) != len(values):
        errors.append(f"{label}: values contain duplicates")
    material = dimension.get("material")
    if not isinstance(material, bool):
        errors.append(f"{label}: material must be boolean")
    elif treatment == "EXCLUDE" and material:
        errors.append(f"{label}: an excluded dimension cannot be material")
    elif treatment != "EXCLUDE" and not material:
        errors.append(f"{label}: a non-excluded dimension must be material")
    if treatment == "BLOCKED" and not _nonempty(dimension.get("blocker_id")):
        errors.append(f"{label}: BLOCKED treatment requires blocker_id")


def _validate_signature(label: str, value: Any, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label}: behavior_signature must be an object")
        return
    required = (
        "action_path",
        "page_or_component",
        "data_source",
        "payload_contract",
        "tag_contract",
        "consent_context",
        "acquisition_context",
        "journey_precondition",
    )
    for field in required:
        if field not in value or value.get(field) in (None, ""):
            errors.append(f"{label}: behavior_signature.{field} is required")


def _required_sampling_roles(
    scenario: dict[str, Any],
    *,
    label: str,
    sampled: bool,
    errors: list[str],
) -> set[str]:
    """Derive sample roles from explicit boundary/exception applicability."""
    if not sampled:
        return set()
    required = {"ORDINARY", "CONTRAST"}
    applicability = scenario.get("sample_role_applicability")
    if not isinstance(applicability, dict):
        errors.append(
            f"{label}: sampled coverage requires sample_role_applicability for "
            "BOUNDARY and EXCEPTION"
        )
        return required
    if set(applicability) != CONDITIONAL_SAMPLE_ROLES:
        errors.append(
            f"{label}: sample_role_applicability must contain exactly BOUNDARY and EXCEPTION"
        )
    for role in sorted(CONDITIONAL_SAMPLE_ROLES):
        declaration = applicability.get(role)
        if not isinstance(declaration, dict):
            errors.append(f"{label}: {role} applicability must be an object")
            continue
        if not isinstance(declaration.get("applicable"), bool):
            errors.append(f"{label}: {role} applicability requires applicable boolean")
        elif declaration["applicable"]:
            required.add(role)
        if not _nonempty(declaration.get("reason")):
            errors.append(f"{label}: {role} applicability requires a reason")
    return required


def _validate_scenario_class(
    decision_id: str,
    scenario: dict[str, Any],
    index: int,
    final: bool,
    errors: list[str],
) -> None:
    label = f"coverage {decision_id} class {scenario.get('scenario_class_id') or index}"
    for field in (
        "scenario_class_id",
        "name",
        "population_source",
        "selection_method",
    ):
        if not _nonempty(scenario.get(field)):
            errors.append(f"{label}: {field} is required")
    mode = str(scenario.get("selection_mode", "")).strip().upper()
    if mode not in SELECTION_MODES:
        errors.append(f"{label}: invalid selection_mode")
    _validate_signature(label, scenario.get("behavior_signature"), errors)
    dimension_values = scenario.get("dimension_values")
    if not isinstance(dimension_values, dict) or not dimension_values:
        errors.append(f"{label}: dimension_values must be a non-empty object")
    population = scenario.get("population_estimate")
    if population is not None and (
        not isinstance(population, int) or isinstance(population, bool) or population < 1
    ):
        errors.append(f"{label}: population_estimate must be null or a positive integer")
    limitations = scenario.get("limitations")
    if not isinstance(limitations, list) or any(not _nonempty(item) for item in limitations):
        errors.append(f"{label}: limitations must be a string array")
    if population is None and mode != "BLOCKED" and not limitations:
        errors.append(f"{label}: unknown population requires a stated limitation")
    roles = scenario.get("required_sample_roles")
    if not isinstance(roles, list) or any(role not in SAMPLE_ROLES for role in roles):
        errors.append(f"{label}: required_sample_roles contains an invalid role")
        roles = []
    if len(set(roles)) != len(roles):
        errors.append(f"{label}: required_sample_roles contains duplicates")
    case_ids = scenario.get("case_ids")
    sampled = mode == "SAMPLED" or (
        mode == "PARTITIONED"
        and isinstance(case_ids, list)
        and (population is None or population > len(case_ids))
    )
    computed_roles = _required_sampling_roles(
        scenario,
        label=label,
        sampled=sampled,
        errors=errors,
    )
    if sampled and set(roles) != computed_roles:
        missing = sorted(computed_roles - set(roles))
        extra = sorted(set(roles) - computed_roles)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("inapplicable " + ", ".join(extra))
        errors.append(
            f"{label}: required_sample_roles must match applicability ({'; '.join(details)})"
        )
    if mode == "SAMPLED" and population == 1:
        errors.append(f"{label}: a one-member population must use SINGLETON")
    if mode == "SINGLETON" and roles != ["SINGLETON"]:
        errors.append(f"{label}: singleton selection requires only SINGLETON")
    if not isinstance(case_ids, list) or any(not _nonempty(item) for item in case_ids):
        errors.append(f"{label}: case_ids must be a string array")
    elif len(set(case_ids)) != len(case_ids):
        errors.append(f"{label}: case_ids contains duplicates")
    if mode != "BLOCKED" and not case_ids:
        errors.append(f"{label}: a testable scenario requires at least one case")
    if mode == "SINGLETON" and population != 1:
        errors.append(f"{label}: singleton selection requires population_estimate=1")
    if mode == "EXHAUSTIVE":
        if population is None:
            errors.append(f"{label}: exhaustive selection requires a known finite population")
        elif isinstance(case_ids, list) and len(case_ids) != population:
            errors.append(f"{label}: exhaustive selection must execute every population member")
        if roles != ["EXHAUSTIVE"]:
            errors.append(f"{label}: exhaustive selection requires only EXHAUSTIVE sample role")
    if mode == "BLOCKED" and not _nonempty(scenario.get("blocker_id")):
        errors.append(f"{label}: BLOCKED scenario requires blocker_id")
    expansion = scenario.get("expansion_review")
    if final:
        if not isinstance(expansion, dict):
            errors.append(f"{label}: final coverage requires expansion_review")
        else:
            if expansion.get("status") not in EXPANSION_OUTCOMES:
                errors.append(f"{label}: expansion_review has an invalid status")
            if not _nonempty(expansion.get("reason")):
                errors.append(f"{label}: expansion_review.reason is required")
            additional = expansion.get("additional_case_ids")
            if not isinstance(additional, list) or any(not _nonempty(item) for item in additional):
                errors.append(
                    f"{label}: expansion_review.additional_case_ids must be a string array"
                )
            elif expansion.get("status") == "EXPANDED" and not additional:
                errors.append(f"{label}: EXPANDED requires additional_case_ids")
            elif expansion.get("status") != "EXPANDED" and additional:
                errors.append(f"{label}: only EXPANDED may declare additional_case_ids")
            if expansion.get("status") == "BLOCKED" and not _nonempty(expansion.get("blocker_id")):
                errors.append(f"{label}: BLOCKED expansion requires blocker_id")


def coverage_by_group(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return one coverage decision per event group, ignoring malformed rows."""
    return {
        str(row.get("event_group_id", "")).strip(): row
        for row in ledger.get("coverage_decisions", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip()
    }


def _catalog(value: Any, field: str) -> dict[str, dict[str, Any]]:
    return {
        str(row.get(field, "")).strip(): row
        for row in value or []
        if isinstance(row, dict) and str(row.get(field, "")).strip()
    }


def _validate_group_inventory(
    group_values: list[str],
    *,
    expected_groups: set[str],
    final: bool,
    errors: list[str],
) -> None:
    duplicate_groups = sorted(
        value
        for value, count in Counter(item for item in group_values if item).items()
        if count > 1
    )
    if duplicate_groups:
        errors.append(
            "coverage_decisions contain duplicate event groups " + ", ".join(duplicate_groups)
        )
    if not final or expected_groups == set(group_values):
        return
    missing = sorted(expected_groups - set(group_values))
    extra = sorted(set(group_values) - expected_groups)
    if missing:
        errors.append("coverage decisions missing event groups " + ", ".join(missing))
    if extra:
        errors.append("coverage decisions contain unknown event groups " + ", ".join(extra))


def _validate_decision_metadata(
    decision_id: str,
    decision: dict[str, Any],
    *,
    expected_groups: set[str],
    errors: list[str],
) -> tuple[str, Any, str]:
    label = f"coverage {decision_id}"
    group_id = str(decision.get("event_group_id", "")).strip()
    if not group_id:
        errors.append(f"{label}: event_group_id is required")
    elif expected_groups and group_id not in expected_groups:
        errors.append(f"{label}: unknown event_group_id '{group_id}'")
    revision = decision.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        errors.append(f"{label}: revision must be a positive integer")
    status = str(decision.get("status", "")).strip().upper()
    if status not in COVERAGE_STATUSES:
        errors.append(f"{label}: invalid status")
    if not _iso_timestamp(decision.get("recorded_at")):
        errors.append(f"{label}: recorded_at must be ISO 8601 with timezone")
    if status == "FROZEN" and not _iso_timestamp(decision.get("frozen_at")):
        errors.append(f"{label}: frozen coverage requires frozen_at")
    discovery = decision.get("discovery_sources")
    if not isinstance(discovery, list) or not discovery:
        errors.append(f"{label}: discovery_sources must be a non-empty array")
    elif any(item not in DISCOVERY_SOURCES for item in discovery):
        errors.append(f"{label}: discovery_sources contains an unsupported value")
    if not _nonempty(decision.get("population_scope")):
        errors.append(f"{label}: population_scope is required")
    if not isinstance(decision.get("population_complete"), bool):
        errors.append(f"{label}: population_complete must be boolean")
    limitations = decision.get("limitations")
    if not isinstance(limitations, list) or any(not _nonempty(item) for item in limitations):
        errors.append(f"{label}: limitations must be a string array")
    if decision.get("population_complete") is False and not limitations:
        errors.append(f"{label}: incomplete population requires a stated limitation")
    expansion_triggers = decision.get("expansion_triggers")
    if not isinstance(expansion_triggers, list) or set(expansion_triggers) != EXPANSION_TRIGGERS:
        errors.append(f"{label}: expansion_triggers must contain every mandatory adaptive trigger")
    return group_id, revision, status


def _decision_components(
    decision_id: str,
    decision: dict[str, Any],
    *,
    status: str,
    final: bool,
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    label = f"coverage {decision_id}"
    dimensions = _object_rows(decision.get("dimensions"), f"{label}.dimensions", errors)
    dimension_by_id = _unique(dimensions, "dimension_id", f"{label} dimension", errors)
    for index, dimension in enumerate(dimensions, start=1):
        _validate_dimension(decision_id, dimension, index, errors)
    scenarios = _object_rows(decision.get("scenario_classes"), f"{label}.scenario_classes", errors)
    scenario_by_id = _unique(scenarios, "scenario_class_id", f"{label} scenario class", errors)
    for index, scenario in enumerate(scenarios, start=1):
        _validate_scenario_class(decision_id, scenario, index, final, errors)
    if status == "FROZEN" and not scenarios:
        errors.append(f"{label}: frozen coverage requires scenario classes")
    return dimension_by_id, scenario_by_id


def _scenario_dimension_contract(
    label: str,
    scenario_id: str,
    scenario: dict[str, Any],
    *,
    dimension_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, set[str]]:
    material_ids = {
        dimension_id
        for dimension_id, dimension in dimension_by_id.items()
        if dimension.get("material") is True
        and str(dimension.get("treatment", "")).strip().upper() != "EXCLUDE"
    }
    dimension_values = scenario.get("dimension_values", {})
    if not isinstance(dimension_values, dict):
        return {}
    unknown = sorted(set(map(str, dimension_values)) - set(dimension_by_id))
    if unknown:
        errors.append(f"{label} class {scenario_id}: unknown dimensions " + ", ".join(unknown))
    missing = sorted(material_ids - set(dimension_values))
    if missing:
        errors.append(
            f"{label} class {scenario_id}: missing material dimensions " + ", ".join(missing)
        )
    allowed_by_dimension: dict[str, set[str]] = {}
    for dimension_id, value in dimension_values.items():
        if dimension_id not in dimension_by_id:
            continue
        values = _declared_values(value)
        if not values or any(item in (None, "") for item in values):
            errors.append(f"{label} class {scenario_id}: dimension {dimension_id} requires values")
            continue
        keys = {_value_key(item) for item in values}
        declared = {_value_key(item) for item in dimension_by_id[dimension_id].get("values", [])}
        outside = sorted(keys - declared)
        if outside:
            errors.append(
                f"{label} class {scenario_id}: dimension {dimension_id} has undeclared values "
                + ", ".join(outside)
            )
        allowed_by_dimension[str(dimension_id)] = keys
    return allowed_by_dimension


def _validate_case_sample(
    case_id: Any,
    *,
    label: str,
    scenario_id: str,
    decision_id: str,
    group_id: str,
    cases: dict[str, dict[str, Any]],
    scenario_dimensions: dict[str, set[str]],
    represented: dict[str, set[str]],
    referenced_cases: list[str],
    errors: list[str],
) -> str | None:
    key = str(case_id)
    referenced_cases.append(key)
    case = cases.get(key)
    if case is None:
        errors.append(f"{label} class {scenario_id}: unknown case_id '{case_id}'")
        return None
    if str(case.get("event_group_id", "")).strip() != group_id:
        errors.append(f"{label} class {scenario_id}: case belongs to another event")
    if case.get("coverage_decision_id") != decision_id:
        errors.append(f"{label} class {scenario_id}: case coverage_decision_id mismatch")
    if case.get("scenario_class_id") != scenario_id:
        errors.append(f"{label} class {scenario_id}: case scenario_class_id mismatch")
    role = str(case.get("sample_role", "")).strip().upper()
    if role not in SAMPLE_ROLES:
        errors.append(f"{label} class {scenario_id}: case has invalid sample_role")
        role = None
    if not _nonempty(case.get("selection_rationale")):
        errors.append(f"{label} class {scenario_id}: case selection_rationale required")
    if not _nonempty(case.get("population_member_id")):
        errors.append(f"{label} class {scenario_id}: population_member_id required")
    case_dimensions = case.get("dimension_values")
    if not isinstance(case_dimensions, dict):
        errors.append(f"{label} class {scenario_id}: case {key} requires explicit dimension_values")
        return role
    unknown_dimensions = sorted(set(map(str, case_dimensions)) - set(scenario_dimensions))
    if unknown_dimensions:
        errors.append(
            f"{label} class {scenario_id}: case {key} has unknown material dimensions "
            + ", ".join(unknown_dimensions)
        )
    missing_dimensions = sorted(set(scenario_dimensions) - set(case_dimensions))
    if missing_dimensions:
        errors.append(
            f"{label} class {scenario_id}: case {key} is missing material dimensions "
            + ", ".join(missing_dimensions)
        )
    for dimension_id, allowed in scenario_dimensions.items():
        if dimension_id not in case_dimensions:
            continue
        value_key = _value_key(case_dimensions[dimension_id])
        if value_key not in allowed:
            errors.append(
                f"{label} class {scenario_id}: case {key} value for {dimension_id} "
                "is outside the scenario class"
            )
        else:
            represented.setdefault(dimension_id, set()).add(value_key)
    return role


def _detected_expansion_triggers(
    ledger: dict[str, Any],
    *,
    group_id: str,
    scenario: dict[str, Any],
    scenario_case_ids: set[str],
    cases: dict[str, dict[str, Any]],
    dimension_by_id: dict[str, dict[str, Any]],
    scenario_dimensions: dict[str, set[str]],
) -> set[str]:
    detected: set[str] = set()
    if any(
        isinstance(row, dict)
        and str(row.get("case_id", "")) in scenario_case_ids
        and str(row.get("status", "")).strip().upper() in {"FAIL", "REVIEW", "BLOCKED"}
        for row in ledger.get("semantic_checks", [])
    ) or any(
        isinstance(row, dict)
        and str(row.get("case_id", "")) in scenario_case_ids
        and any(
            isinstance(layer, dict)
            and str(layer.get("status", "")).strip().upper() in {"FAIL", "REVIEW", "BLOCKED"}
            for layer in row.get("layer_results", [])
        )
        for row in ledger.get("actions", [])
    ):
        detected.add("ANOMALY_OR_FAILURE")

    group_pushes = [
        row
        for row in ledger.get("business_pushes", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip() == group_id
    ]
    if any(row.get("classification") in ANOMALOUS_PUSH_CLASSIFICATIONS for row in group_pushes):
        detected.add("ANOMALY_OR_FAILURE")
    if any(row.get("classification") == "unplanned_relevant" for row in group_pushes):
        detected.add("NEW_BEHAVIOR_SIGNATURE")

    expected_signature = scenario.get("behavior_signature")
    for case_id in scenario_case_ids:
        case = cases.get(case_id, {})
        observed_signature = case.get("observed_behavior_signature")
        if isinstance(observed_signature, dict) and _value_key(observed_signature) != _value_key(
            expected_signature
        ):
            detected.add("NEW_BEHAVIOR_SIGNATURE")
        observed_dimensions = case.get("observed_dimension_values")
        if isinstance(observed_dimensions, dict):
            case_dimensions = case.get("dimension_values")
            case_dimensions = case_dimensions if isinstance(case_dimensions, dict) else {}
            for dimension_id, value in observed_dimensions.items():
                dimension = dimension_by_id.get(str(dimension_id))
                declared = {_value_key(item) for item in (dimension or {}).get("values", [])}
                key = _value_key(value)
                if (
                    dimension is None
                    or key not in declared
                    or key not in scenario_dimensions.get(str(dimension_id), set())
                    or (
                        dimension_id in case_dimensions
                        and key != _value_key(case_dimensions[dimension_id])
                    )
                ):
                    detected.add("UNSEEN_MATERIAL_DIMENSION_VALUE")

    if any(
        isinstance(row, dict)
        and str(row.get("case_id", "")) in scenario_case_ids
        and row.get("conditional_branch_observed") is True
        for row in ledger.get("actions", [])
    ):
        detected.add("CONDITIONAL_RUNTIME_BRANCH")
    return detected


def _validate_expansion_review(
    *,
    label: str,
    scenario_id: str,
    scenario: dict[str, Any],
    detected: set[str],
    cases: dict[str, dict[str, Any]],
    final: bool,
    errors: list[str],
) -> None:
    if not final:
        return
    expansion = scenario.get("expansion_review")
    if not isinstance(expansion, dict):
        return
    scenario_case_ids = {str(value) for value in scenario.get("case_ids", [])}
    additional = expansion.get("additional_case_ids")
    additional_ids = {str(value) for value in additional} if isinstance(additional, list) else set()
    unknown = sorted(additional_ids - set(cases))
    outside = sorted(additional_ids - scenario_case_ids)
    if unknown:
        errors.append(
            f"{label} class {scenario_id}: expansion cases are not registered " + ", ".join(unknown)
        )
    if outside:
        errors.append(
            f"{label} class {scenario_id}: expansion cases are outside the scenario "
            + ", ".join(outside)
        )

    trigger_reviews = expansion.get("trigger_reviews")
    if not isinstance(trigger_reviews, dict):
        errors.append(
            f"{label} class {scenario_id}: final coverage requires trigger_reviews "
            "for every mandatory adaptive trigger"
        )
        return
    if set(trigger_reviews) != EXPANSION_TRIGGERS:
        errors.append(
            f"{label} class {scenario_id}: trigger_reviews must contain every mandatory trigger"
        )
    reviewed_additional: set[str] = set()
    outcomes: list[str] = []
    for trigger in sorted(EXPANSION_TRIGGERS):
        review = trigger_reviews.get(trigger)
        trigger_label = f"{label} class {scenario_id} trigger {trigger}"
        if not isinstance(review, dict):
            errors.append(f"{trigger_label}: review must be an object")
            continue
        declared_detected = review.get("detected")
        if not isinstance(declared_detected, bool):
            errors.append(f"{trigger_label}: detected must be boolean")
        if trigger in detected and declared_detected is not True:
            errors.append(f"{trigger_label}: ledger evidence requires detected=true")
        outcome = str(review.get("outcome", "")).strip().upper()
        if outcome not in EXPANSION_OUTCOMES:
            errors.append(f"{trigger_label}: invalid outcome")
        else:
            outcomes.append(outcome)
        if declared_detected is True and outcome == "NOT_TRIGGERED":
            errors.append(
                f"{trigger_label}: detected trigger requires expansion, exhaustion, or blocker"
            )
        if declared_detected is False and outcome != "NOT_TRIGGERED":
            errors.append(f"{trigger_label}: undetected trigger must be NOT_TRIGGERED")
        if not _nonempty(review.get("reason")):
            errors.append(f"{trigger_label}: reason is required")
        ids = review.get("additional_case_ids")
        if not isinstance(ids, list) or any(not _nonempty(item) for item in ids):
            errors.append(f"{trigger_label}: additional_case_ids must be a string array")
            ids = []
        ids_set = {str(value) for value in ids}
        reviewed_additional.update(ids_set)
        if outcome == "EXPANDED" and not ids_set:
            errors.append(f"{trigger_label}: EXPANDED requires additional_case_ids")
        if outcome != "EXPANDED" and ids_set:
            errors.append(f"{trigger_label}: only EXPANDED may declare additional_case_ids")
        if outcome == "BLOCKED" and not _nonempty(review.get("blocker_id")):
            errors.append(f"{trigger_label}: BLOCKED requires blocker_id")
        trigger_unknown = sorted(ids_set - set(cases))
        trigger_outside = sorted(ids_set - scenario_case_ids)
        if trigger_unknown:
            errors.append(f"{trigger_label}: unregistered cases " + ", ".join(trigger_unknown))
        if trigger_outside:
            errors.append(f"{trigger_label}: cases outside scenario " + ", ".join(trigger_outside))
    expected_overall = (
        "BLOCKED"
        if "BLOCKED" in outcomes
        else "EXPANDED"
        if "EXPANDED" in outcomes
        else "EXHAUSTED"
        if "EXHAUSTED" in outcomes
        else "NOT_TRIGGERED"
    )
    if expansion.get("status") != expected_overall:
        errors.append(
            f"{label} class {scenario_id}: expansion status must roll up to {expected_overall}"
        )
    if reviewed_additional != additional_ids:
        errors.append(
            f"{label} class {scenario_id}: overall additional_case_ids must equal trigger reviews"
        )


def _validate_scenario_mapping(
    ledger: dict[str, Any],
    *,
    decision_id: str,
    group_id: str,
    status: str,
    scenario_by_id: dict[str, dict[str, Any]],
    dimension_by_id: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    referenced_cases: list[str],
    final: bool,
    errors: list[str],
) -> dict[str, set[str]]:
    label = f"coverage {decision_id}"
    represented: dict[str, set[str]] = {key: set() for key in dimension_by_id}
    for scenario_id, scenario in scenario_by_id.items():
        scenario_dimensions = _scenario_dimension_contract(
            label,
            scenario_id,
            scenario,
            dimension_by_id=dimension_by_id,
            errors=errors,
        )
        scenario_case_ids_list = scenario.get("case_ids", [])
        scenario_represented: dict[str, set[str]] = {
            dimension_id: set() for dimension_id in scenario_dimensions
        }
        actual_roles = {
            role
            for case_id in scenario_case_ids_list
            if (
                role := _validate_case_sample(
                    case_id,
                    label=label,
                    scenario_id=scenario_id,
                    decision_id=decision_id,
                    group_id=group_id,
                    cases=cases,
                    scenario_dimensions=scenario_dimensions,
                    represented=scenario_represented,
                    referenced_cases=referenced_cases,
                    errors=errors,
                )
            )
        }
        member_ids = [
            str(cases[str(case_id)].get("population_member_id", "")).strip()
            for case_id in scenario.get("case_ids", [])
            if str(case_id) in cases
        ]
        duplicate_members = sorted(
            value
            for value, count in Counter(item for item in member_ids if item).items()
            if count > 1
        )
        if duplicate_members:
            errors.append(
                f"{label} class {scenario_id}: duplicate sampled population members "
                + ", ".join(duplicate_members)
            )
        missing_roles = sorted(set(scenario.get("required_sample_roles", [])) - actual_roles)
        if status == "FROZEN" and missing_roles:
            errors.append(
                f"{label} class {scenario_id}: missing required samples " + ", ".join(missing_roles)
            )
        for dimension_id, values in scenario_represented.items():
            represented.setdefault(dimension_id, set()).update(values)
        if status == "FROZEN" and str(scenario.get("selection_mode", "")).upper() == "EXHAUSTIVE":
            for dimension_id, allowed in scenario_dimensions.items():
                missing_values = sorted(allowed - scenario_represented.get(dimension_id, set()))
                if missing_values:
                    errors.append(
                        f"{label} class {scenario_id}: exhaustive cases do not represent "
                        f"{dimension_id} values " + ", ".join(missing_values)
                    )
        scenario_case_ids = {str(value) for value in scenario_case_ids_list}
        detected = _detected_expansion_triggers(
            ledger,
            group_id=group_id,
            scenario=scenario,
            scenario_case_ids=scenario_case_ids,
            cases=cases,
            dimension_by_id=dimension_by_id,
            scenario_dimensions=scenario_dimensions,
        )
        expansion = scenario.get("expansion_review")
        expansion_status = expansion.get("status") if isinstance(expansion, dict) else None
        if final and detected and expansion_status == "NOT_TRIGGERED":
            errors.append(
                f"{label} class {scenario_id}: detected triggers "
                + ", ".join(sorted(detected))
                + " require expansion, exhaustion, or blocker"
            )
        _validate_expansion_review(
            label=label,
            scenario_id=scenario_id,
            scenario=scenario,
            detected=detected,
            cases=cases,
            final=final,
            errors=errors,
        )
    return represented


def _validate_dimension_coverage(
    dimension_by_id: dict[str, dict[str, Any]],
    represented: dict[str, set[str]],
    *,
    label: str,
    status: str,
    errors: list[str],
) -> None:
    for dimension_id, dimension in dimension_by_id.items():
        if str(dimension.get("treatment", "")).strip().upper() not in {"ENUMERATE", "PARTITION"}:
            continue
        declared = {_value_key(value) for value in dimension.get("values", [])}
        missing = sorted(declared - represented.get(dimension_id, set()))
        if status == "FROZEN" and missing:
            errors.append(
                f"{label} dimension {dimension_id}: unrepresented values " + ", ".join(missing)
            )


def _validate_closure_binding(
    closure: dict[str, Any] | None,
    *,
    label: str,
    status: str,
    revision: Any,
    errors: list[str],
) -> None:
    if closure is None:
        return
    if status != "FROZEN":
        errors.append(f"{label}: a closed event requires frozen coverage")
    if closure.get("coverage_revision") != revision:
        errors.append(f"{label}: event closure coverage_revision is stale")


def coverage_errors(
    ledger: dict[str, Any],
    *,
    results: dict[str, Any] | None,
    final: bool,
) -> list[str]:
    """Validate coverage decisions and their exact case mapping for contract-v2 runs."""
    errors: list[str] = []
    decisions = _object_rows(ledger.get("coverage_decisions"), "coverage_decisions", errors)
    by_id = _unique(decisions, "coverage_decision_id", "coverage decision", errors)
    group_values = [str(row.get("event_group_id", "")).strip() for row in decisions]
    cases = _catalog(ledger.get("cases"), "case_id")
    closures = _catalog(ledger.get("event_closures"), "event_group_id")
    expected_groups = {
        str(row.get("event_group_id", "")).strip()
        for row in (results or {}).get("run", {}).get("event_inventory", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip()
    }
    _validate_group_inventory(
        group_values,
        expected_groups=expected_groups,
        final=final,
        errors=errors,
    )
    referenced_cases: list[str] = []
    for decision_id, decision in by_id.items():
        label = f"coverage {decision_id}"
        group_id, revision, status = _validate_decision_metadata(
            decision_id,
            decision,
            expected_groups=expected_groups,
            errors=errors,
        )
        dimension_by_id, scenario_by_id = _decision_components(
            decision_id,
            decision,
            status=status,
            final=final,
            errors=errors,
        )
        represented = _validate_scenario_mapping(
            ledger,
            decision_id=decision_id,
            group_id=group_id,
            status=status,
            scenario_by_id=scenario_by_id,
            dimension_by_id=dimension_by_id,
            cases=cases,
            referenced_cases=referenced_cases,
            final=final,
            errors=errors,
        )
        _validate_dimension_coverage(
            dimension_by_id,
            represented,
            label=label,
            status=status,
            errors=errors,
        )
        _validate_closure_binding(
            closures.get(group_id),
            label=label,
            status=status,
            revision=revision,
            errors=errors,
        )
    duplicates = sorted(
        case_id for case_id, count in Counter(referenced_cases).items() if case_id and count > 1
    )
    if duplicates:
        errors.append("coverage scenario classes reuse cases " + ", ".join(duplicates))
    in_scope_case_ids = {
        case_id for case_id, case in cases.items() if case.get("scope_status") == "IN_SCOPE"
    }
    missing_cases = sorted(in_scope_case_ids - set(referenced_cases))
    if final and missing_cases:
        errors.append("in-scope cases missing from coverage classes " + ", ".join(missing_cases))
    return errors


def coverage_summary(ledger: dict[str, Any], event_group_id: str) -> dict[str, Any]:
    """Return a compact explainable coverage summary for feedback and reports."""
    decision = coverage_by_group(ledger).get(event_group_id)
    if decision is None:
        return {
            "status": "LEGACY_UNRECORDED",
            "scenario_class_count": 0,
            "case_count": 0,
            "population_complete": None,
            "limitations": [],
        }
    scenarios = [row for row in decision.get("scenario_classes", []) if isinstance(row, dict)]
    case_ids = {
        str(case_id)
        for scenario in scenarios
        for case_id in scenario.get("case_ids", [])
        if str(case_id)
    }
    return {
        "coverage_decision_id": decision.get("coverage_decision_id"),
        "revision": decision.get("revision"),
        "status": decision.get("status"),
        "scenario_class_count": len(scenarios),
        "case_count": len(case_ids),
        "population_scope": decision.get("population_scope"),
        "population_complete": decision.get("population_complete"),
        "limitations": list(decision.get("limitations", [])),
        "dimensions": [
            {
                "name": row.get("name"),
                "values": row.get("values"),
                "treatment": row.get("treatment"),
                "reason": row.get("reason"),
            }
            for row in decision.get("dimensions", [])
            if isinstance(row, dict)
        ],
        "scenario_classes": [
            {
                "scenario_class_id": row.get("scenario_class_id"),
                "name": row.get("name"),
                "selection_mode": row.get("selection_mode"),
                "population_estimate": row.get("population_estimate"),
                "case_ids": list(row.get("case_ids", [])),
                "limitations": list(row.get("limitations", [])),
            }
            for row in scenarios
        ],
    }
