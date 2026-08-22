#!/usr/bin/env python3
"""Validate semantic truth, positive anchors, and cross-event journey state."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from acceptance_contract import expects_absence, worst_status
from value_semantics import field_state_for, strict_equal

SEMANTIC_KINDS = {
    "PAGE_ACTION_VALIDITY",
    "POSITIVE_ANCHOR",
    "BUSINESS_STATE",
    "JOURNEY_CONTINUITY",
    "PLATFORM_SEMANTICS",
}
SEMANTIC_AUTHORITIES = {
    "VISIBLE_PAGE",
    "JOURNEY_STATE",
    "TRACKING_PLAN",
    "ANALYST_SPEC",
    "PLATFORM_DOCUMENTATION",
    "DIRECT_INTERACTION",
}
SEMANTIC_STATUSES = {"PASS", "FAIL", "REVIEW", "BLOCKED", "NOT_APPLICABLE"}
COMPARISONS = {"EQUAL", "PRESENT", "ABSENT", "PLAUSIBLE", "TRANSITION"}
ANCHOR_STATES = {"PRESENT", "EXPECTED_ABSENT", "NOT_APPLICABLE"}
JOURNEY_PHASES = {"BEFORE", "AFTER"}
POSITIVE_SEMANTIC_KINDS = {"POSITIVE_ANCHOR", "BUSINESS_STATE"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_timestamp(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _empty_business_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _page_health_invalid(value: Any, *, phase: str) -> bool:
    """Return whether a captured page-health row makes the action invalid."""
    if not isinstance(value, dict):
        return True
    status = str(value.get("status", "")).strip().upper()
    status_code = value.get("http_status")
    return (
        status != "PASS"
        or value.get("reachable") is not True
        or (
            isinstance(status_code, int)
            and not isinstance(status_code, bool)
            and status_code >= 400
        )
        or value.get("is_error_page") is not False
        or value.get("is_soft_404") is not False
        or value.get("expected_content_present") is not True
        or (phase == "before_action" and value.get("action_target_present") is not True)
    )


def _action_page_invalid(
    action: dict[str, Any],
    runtime_checks: dict[str, dict[str, Any]],
) -> bool:
    """Use both action boundaries; a bad departure or landing page invalidates the action."""
    boundaries = (
        ("readiness_check_id", "before_action", "page_health_before"),
        ("settlement_check_id", "after_action", "page_health_after"),
    )
    for check_field, phase, action_field in boundaries:
        runtime = runtime_checks.get(str(action.get(check_field, "")).strip())
        if runtime is None or _page_health_invalid(runtime.get("page_health"), phase=phase):
            return True
        action_health = action.get(action_field)
        if (
            isinstance(action_health, dict)
            and str(action_health.get("status", "")).upper() == "FAIL"
        ):
            return True
    return False


def _rows(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"session: {label} must be an array")
        return []
    output: list[dict[str, Any]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"session: {label} row {index} must be an object")
        else:
            output.append(row)
    return output


def _ids(
    rows: list[dict[str, Any]], field: str, label: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    values = [str(row.get(field, "")).strip() for row in rows]
    for index, value in enumerate(values, start=1):
        if not value:
            errors.append(f"session {label} row {index} missing {field}")
    duplicates = sorted(
        value for value, count in Counter(item for item in values if item).items() if count > 1
    )
    if duplicates:
        errors.append(f"session duplicate {label} IDs " + ", ".join(duplicates))
    return {str(row.get(field, "")).strip(): row for row in rows if str(row.get(field, "")).strip()}


def _validate_journey_states(
    ledger: dict[str, Any],
    *,
    final: bool,
    errors: list[str],
) -> dict[str, list[dict[str, Any]]]:
    states = _rows(ledger.get("journey_states"), "journey_states", errors)
    _ids(states, "state_id", "journey state", errors)
    actions = {
        str(row.get("action_id", "")).strip(): row
        for row in ledger.get("actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    cases = {
        str(row.get("case_id", "")).strip(): row
        for row in ledger.get("cases", [])
        if isinstance(row, dict) and str(row.get("case_id", "")).strip()
    }
    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for state in states:
        state_id = str(state.get("state_id", "")).strip()
        label = f"session journey state {state_id}"
        action_id = str(state.get("action_id", "")).strip()
        case_id = str(state.get("case_id", "")).strip()
        if action_id not in actions:
            errors.append(f"{label}: unknown action_id")
        if case_id not in cases:
            errors.append(f"{label}: unknown case_id")
        if action_id in actions and actions[action_id].get("case_id") != case_id:
            errors.append(f"{label}: case_id differs from action")
        if state.get("phase") not in JOURNEY_PHASES:
            errors.append(f"{label}: phase must be BEFORE or AFTER")
        if not _iso_timestamp(state.get("captured_at")):
            errors.append(f"{label}: captured_at must be ISO 8601 with timezone")
        values = state.get("values")
        if not isinstance(values, dict) or not values:
            errors.append(f"{label}: values must be a non-empty object")
        if not _nonempty(state.get("summary")):
            errors.append(f"{label}: summary is required")
        refs = state.get("evidence_ids")
        if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
            errors.append(f"{label}: evidence_ids must be a non-empty string array")
        if state.get("sensitive_scan_status") != "PASS":
            errors.append(f"{label}: sensitive_scan_status must be PASS")
        by_action[action_id].append(state)
    if final:
        for action in ledger.get("actions", []):
            if not isinstance(action, dict) or action.get("state") != "SETTLED":
                continue
            action_id = str(action.get("action_id", "")).strip()
            phases = [row.get("phase") for row in by_action.get(action_id, [])]
            if Counter(phases) != Counter({"BEFORE": 1, "AFTER": 1}):
                errors.append(
                    f"session action {action_id}: requires exactly one BEFORE and one AFTER journey state"
                )
    return dict(by_action)


def _validate_semantic_check(
    check: dict[str, Any],
    *,
    action_ids: set[str],
    case_ids: set[str],
    group_ids: set[str],
    requirement_ids: set[str],
    errors: list[str],
) -> None:
    check_id = str(check.get("check_id", "")).strip()
    label = f"session semantic check {check_id}"
    action_id = str(check.get("action_id", "")).strip()
    case_id = str(check.get("case_id", "")).strip()
    group_id = str(check.get("event_group_id", "")).strip()
    requirement_id = str(check.get("requirement_id") or "").strip()
    if action_id not in action_ids:
        errors.append(f"{label}: unknown action_id")
    if case_id not in case_ids:
        errors.append(f"{label}: unknown case_id")
    if group_id not in group_ids:
        errors.append(f"{label}: unknown event_group_id")
    if requirement_id and requirement_id not in requirement_ids:
        errors.append(f"{label}: unknown requirement_id")
    if check.get("kind") not in SEMANTIC_KINDS:
        errors.append(f"{label}: invalid kind")
    if check.get("authority") not in SEMANTIC_AUTHORITIES:
        errors.append(f"{label}: invalid authority")
    if check.get("comparison") not in COMPARISONS:
        errors.append(f"{label}: invalid comparison")
    if check.get("anchor_state") not in ANCHOR_STATES:
        errors.append(f"{label}: invalid anchor_state")
    status = str(check.get("status", "")).strip().upper()
    if status not in SEMANTIC_STATUSES:
        errors.append(f"{label}: invalid status")
    for field in ("subject", "reason"):
        if not _nonempty(check.get(field)):
            errors.append(f"{label}: {field} is required")
    if not _iso_timestamp(check.get("recorded_at")):
        errors.append(f"{label}: recorded_at must be ISO 8601 with timezone")
    refs = check.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
        errors.append(f"{label}: evidence_ids must be a non-empty string array")
    if status == "REVIEW" and not _nonempty(check.get("review_question")):
        errors.append(f"{label}: REVIEW requires review_question")
    if status == "BLOCKED" and not _nonempty(check.get("blocker_id")):
        errors.append(f"{label}: BLOCKED requires blocker_id")
    comparison = check.get("comparison")
    anchor_state = check.get("anchor_state")
    anchor_value = check.get("anchor_value")
    observed_value = check.get("observed_value")
    positive_kind = check.get("kind") in POSITIVE_SEMANTIC_KINDS
    if positive_kind and anchor_state == "PRESENT":
        if status == "NOT_APPLICABLE":
            errors.append(f"{label}: a PRESENT positive business anchor cannot be NOT_APPLICABLE")
        if _empty_business_value(anchor_value):
            errors.append(f"{label}: a PRESENT positive business anchor must be non-empty")
    if anchor_state == "PRESENT":
        if check.get("anchor_field_state") != field_state_for(anchor_value):
            errors.append(f"{label}: anchor_field_state is inconsistent")
        if check.get("observed_field_state") != field_state_for(observed_value):
            errors.append(f"{label}: observed_field_state is inconsistent")
    if status == "PASS":
        if comparison == "EQUAL" and not strict_equal(anchor_value, observed_value):
            errors.append(f"{label}: PASS contradicts unequal anchor and observed values")
        if comparison == "PRESENT" and (
            anchor_state != "PRESENT" or _empty_business_value(observed_value)
        ):
            errors.append(f"{label}: PASS PRESENT requires a non-empty observed value")
        if comparison == "ABSENT" and (
            anchor_state != "EXPECTED_ABSENT" or not _empty_business_value(observed_value)
        ):
            errors.append(f"{label}: PASS ABSENT contradicts the observed value")
        if positive_kind and (
            anchor_state != "PRESENT"
            or _empty_business_value(anchor_value)
            or _empty_business_value(observed_value)
        ):
            errors.append(f"{label}: matching emptiness cannot satisfy a positive business anchor")


def _validate_check_bindings(
    check: dict[str, Any],
    *,
    actions: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    evidence: dict[str, dict[str, Any]],
    runtime_checks: dict[str, dict[str, Any]],
    journey_by_evidence: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    check_id = check.get("check_id")
    action_id = str(check.get("action_id", "")).strip()
    case_id = str(check.get("case_id", "")).strip()
    action = actions.get(action_id)
    case = cases.get(case_id)
    if action is not None and check.get("case_id") != action.get("case_id"):
        errors.append(f"session semantic check {check_id}: case_id differs from action")
    if case is not None and check.get("event_group_id") != case.get("event_group_id"):
        errors.append(f"session semantic check {check_id}: event_group_id differs from case")
    matched_journey_phases: set[str] = set()
    matched_runtime_phases: set[str] = set()
    for evidence_id in check.get("evidence_ids", []):
        evidence_key = str(evidence_id)
        evidence_row = evidence.get(evidence_key)
        if evidence_row is None:
            errors.append(f"session semantic check {check_id}: unknown evidence ID '{evidence_id}'")
            continue
        if evidence_row.get("capture_mode") != "direct":
            errors.append(
                f"session semantic check {check_id}: evidence '{evidence_id}' "
                "is not a direct capture"
            )
        if str(evidence_row.get("action_id", "")).strip() != action_id:
            errors.append(
                f"session semantic check {check_id}: evidence '{evidence_id}' "
                "does not belong to the same action"
            )
        evidence_case_id = str(evidence_row.get("case_id", "")).strip()
        if evidence_case_id and evidence_case_id != case_id:
            errors.append(
                f"session semantic check {check_id}: evidence '{evidence_id}' "
                "does not belong to the same case"
            )
        evidence_action = actions.get(str(evidence_row.get("action_id", "")).strip())
        if evidence_action is not None and evidence_action.get("case_id") != case_id:
            errors.append(
                f"session semantic check {check_id}: evidence '{evidence_id}' "
                "resolves to an action from another case"
            )

        runtime_check_id = str(evidence_row.get("runtime_check_id", "")).strip()
        runtime_phase = str(evidence_row.get("runtime_phase", "")).strip()
        if evidence_row.get("kind") == "page_health" and not (runtime_check_id and runtime_phase):
            errors.append(
                f"session semantic check {check_id}: page-health evidence '{evidence_id}' "
                "requires an explicit before/after runtime binding"
            )
        if runtime_check_id or runtime_phase:
            if not runtime_check_id or not runtime_phase:
                errors.append(
                    f"session semantic check {check_id}: evidence '{evidence_id}' "
                    "must bind both runtime_check_id and runtime_phase"
                )
            runtime = runtime_checks.get(runtime_check_id)
            if runtime is None:
                errors.append(
                    f"session semantic check {check_id}: evidence '{evidence_id}' "
                    "references an unknown runtime check"
                )
            else:
                if runtime.get("action_id") != action_id or runtime.get("case_id") != case_id:
                    errors.append(
                        f"session semantic check {check_id}: evidence '{evidence_id}' "
                        "runtime binding belongs to another action or case"
                    )
                if runtime.get("phase") != runtime_phase:
                    errors.append(
                        f"session semantic check {check_id}: evidence '{evidence_id}' "
                        "runtime_phase differs from the bound runtime check"
                    )
                expected_runtime_id = {
                    "before_action": str((action or {}).get("readiness_check_id", "")).strip(),
                    "after_action": str((action or {}).get("settlement_check_id", "")).strip(),
                }.get(runtime_phase)
                if not expected_runtime_id or runtime_check_id != expected_runtime_id:
                    errors.append(
                        f"session semantic check {check_id}: evidence '{evidence_id}' "
                        "is bound to the wrong before/after action phase"
                    )
                if evidence_key not in runtime.get("evidence_ids", []):
                    errors.append(
                        f"session semantic check {check_id}: evidence '{evidence_id}' "
                        "is absent from its bound runtime check"
                    )
                if evidence_row.get("kind") == "page_health" and evidence_key not in (
                    runtime.get("page_health") or {}
                ).get("evidence_ids", []):
                    errors.append(
                        f"session semantic check {check_id}: page-health evidence "
                        f"'{evidence_id}' is absent from the bound page-health capture"
                    )
                matched_runtime_phases.add(runtime_phase)

        if evidence_row.get("kind") == "journey_state":
            matches = [
                row
                for row in journey_by_evidence.get(evidence_key, [])
                if row.get("action_id") == action_id and row.get("case_id") == case_id
            ]
            if not matches:
                errors.append(
                    f"session semantic check {check_id}: journey evidence '{evidence_id}' "
                    "is not bound to this action and case"
                )
            matched_journey_phases.update(
                str(row.get("phase", "")).strip().upper() for row in matches
            )
    evidence_kinds = {
        evidence[str(evidence_id)].get("kind")
        for evidence_id in check.get("evidence_ids", [])
        if str(evidence_id) in evidence
    }
    if check.get("kind") == "PAGE_ACTION_VALIDITY" and "page_health" not in evidence_kinds:
        errors.append(f"session semantic check {check_id}: page_health evidence is required")
    if check.get("kind") == "PAGE_ACTION_VALIDITY" and matched_runtime_phases != {
        "before_action",
        "after_action",
    }:
        errors.append(
            f"session semantic check {check_id}: PAGE_ACTION_VALIDITY requires before and "
            "after page-health evidence"
        )
    if check.get("kind") in {"BUSINESS_STATE", "JOURNEY_CONTINUITY"} and (
        "journey_state" not in evidence_kinds
    ):
        errors.append(f"session semantic check {check_id}: journey_state evidence is required")
    if check.get("kind") == "BUSINESS_STATE" and "AFTER" not in matched_journey_phases:
        errors.append(
            f"session semantic check {check_id}: BUSINESS_STATE requires AFTER journey evidence"
        )
    if check.get("kind") == "JOURNEY_CONTINUITY" and matched_journey_phases != {"BEFORE", "AFTER"}:
        errors.append(
            f"session semantic check {check_id}: JOURNEY_CONTINUITY requires BEFORE and AFTER "
            "journey evidence"
        )


def _check_indexes(
    checks: list[dict[str, Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[tuple[str, str], list[dict[str, Any]]],
]:
    by_action: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_action_requirement: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        action_id = str(check.get("action_id", "")).strip()
        by_action[action_id].append(check)
        requirement_id = str(check.get("requirement_id", "")).strip()
        if requirement_id:
            by_action_requirement[(action_id, requirement_id)].append(check)
    return dict(by_action), dict(by_action_requirement)


def _validate_page_semantics(
    action_id: str,
    action: dict[str, Any],
    *,
    action_checks: list[dict[str, Any]],
    runtime_checks: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    page_checks = [row for row in action_checks if row.get("kind") == "PAGE_ACTION_VALIDITY"]
    if len(page_checks) != 1:
        errors.append(f"session action {action_id}: missing PAGE_ACTION_VALIDITY semantic check")
        return
    expected_status = "FAIL" if _action_page_invalid(action, runtime_checks) else "PASS"
    if page_checks[0].get("status") != expected_status:
        errors.append(
            f"session action {action_id}: PAGE_ACTION_VALIDITY must be "
            f"{expected_status} for the captured page health"
        )


def _validate_requirement_semantics(
    action_id: str,
    case: dict[str, Any],
    *,
    requirements: dict[str, dict[str, Any]],
    checks_by_action_requirement: dict[tuple[str, str], list[dict[str, Any]]],
    errors: list[str],
) -> None:
    for requirement_id in case.get("requirement_ids", []):
        requirement_key = str(requirement_id)
        requirement = requirements.get(requirement_key)
        if requirement is None or requirement.get("scope_status") != "IN_SCOPE":
            continue
        matched = checks_by_action_requirement.get((action_id, requirement_key), [])
        if not matched:
            errors.append(
                f"session action {action_id}: requirement {requirement_id} lacks semantic acceptance"
            )
            continue
        expectation = requirement.get("expectation", {})
        if not isinstance(expectation, dict) or expects_absence(expectation):
            continue
        positive_checks = [
            row
            for row in matched
            if row.get("kind") in POSITIVE_SEMANTIC_KINDS
            and row.get("anchor_state") == "PRESENT"
            and not _empty_business_value(row.get("anchor_value"))
        ]
        passing_anchors = [
            row
            for row in positive_checks
            if str(row.get("status", "")).strip().upper() == "PASS"
            and not _empty_business_value(row.get("observed_value"))
        ]
        explicit_nonpass = [
            row
            for row in positive_checks
            if str(row.get("status", "")).strip().upper() in {"FAIL", "REVIEW", "BLOCKED"}
        ]
        if not passing_anchors and not explicit_nonpass:
            errors.append(
                f"session action {action_id}: requirement {requirement_id} lacks a positive anchor"
            )


def _validate_business_state_semantics(
    action_id: str,
    action: dict[str, Any],
    *,
    action_checks: list[dict[str, Any]],
    runtime_checks: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    business_checks = [row for row in action_checks if row.get("kind") == "BUSINESS_STATE"]
    if not business_checks:
        errors.append(f"session action {action_id}: missing BUSINESS_STATE semantic check")
        return
    page_invalid = _action_page_invalid(action, runtime_checks)
    action_failed = action.get("interaction_outcome") != "completed"
    if (page_invalid or action_failed) and any(
        row.get("status") == "PASS" for row in business_checks
    ):
        errors.append(
            f"session action {action_id}: BUSINESS_STATE cannot PASS for an invalid page or failed action"
        )


def _validate_final_actions(
    ledger: dict[str, Any],
    *,
    actions: dict[str, dict[str, Any]],
    cases: dict[str, dict[str, Any]],
    requirements: dict[str, dict[str, Any]],
    checks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    checks_by_action, checks_by_action_requirement = _check_indexes(checks)
    runtime_checks = {
        str(row.get("check_id", "")).strip(): row
        for row in ledger.get("runtime_checks", [])
        if isinstance(row, dict) and str(row.get("check_id", "")).strip()
    }
    for action_id, action in actions.items():
        if action.get("state") != "SETTLED":
            continue
        action_checks = checks_by_action.get(action_id, [])
        _validate_page_semantics(
            action_id,
            action,
            action_checks=action_checks,
            runtime_checks=runtime_checks,
            errors=errors,
        )
        _validate_business_state_semantics(
            action_id,
            action,
            action_checks=action_checks,
            runtime_checks=runtime_checks,
            errors=errors,
        )
        case = cases.get(str(action.get("case_id", "")).strip(), {})
        _validate_requirement_semantics(
            action_id,
            case,
            requirements=requirements,
            checks_by_action_requirement=checks_by_action_requirement,
            errors=errors,
        )


def semantic_contract_errors(
    ledger: dict[str, Any],
    *,
    results: dict[str, Any] | None,
    final: bool,
) -> list[str]:
    """Validate mandatory semantic acceptance and journey continuity for contract v2."""
    errors: list[str] = []
    journey_states_by_action = _validate_journey_states(ledger, final=final, errors=errors)
    checks = _rows(ledger.get("semantic_checks"), "semantic_checks", errors)
    check_by_id = _ids(checks, "check_id", "semantic check", errors)
    actions = {
        str(row.get("action_id", "")).strip(): row
        for row in ledger.get("actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    cases = {
        str(row.get("case_id", "")).strip(): row
        for row in ledger.get("cases", [])
        if isinstance(row, dict) and str(row.get("case_id", "")).strip()
    }
    requirements = {
        str(row.get("requirement_id", "")).strip(): row
        for row in (results or {}).get("requirements", [])
        if isinstance(row, dict) and str(row.get("requirement_id", "")).strip()
    }
    group_ids = {
        str(row.get("event_group_id", "")).strip()
        for row in (results or {}).get("run", {}).get("event_inventory", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip()
    }
    evidence = {
        str(row.get("evidence_id", "")).strip(): row
        for row in (results or {}).get("evidence", [])
        if isinstance(row, dict) and str(row.get("evidence_id", "")).strip()
    }
    runtime_checks = {
        str(row.get("check_id", "")).strip(): row
        for row in ledger.get("runtime_checks", [])
        if isinstance(row, dict) and str(row.get("check_id", "")).strip()
    }
    journey_by_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for journey_states in journey_states_by_action.values():
        for state in journey_states:
            for evidence_id in state.get("evidence_ids", []):
                journey_by_evidence[str(evidence_id)].append(state)
    for check in check_by_id.values():
        _validate_semantic_check(
            check,
            action_ids=set(actions),
            case_ids=set(cases),
            group_ids=group_ids,
            requirement_ids=set(requirements),
            errors=errors,
        )
        _validate_check_bindings(
            check,
            actions=actions,
            cases=cases,
            evidence=evidence,
            runtime_checks=runtime_checks,
            journey_by_evidence=dict(journey_by_evidence),
            errors=errors,
        )
    if not final:
        return errors
    _validate_final_actions(
        ledger,
        actions=actions,
        cases=cases,
        requirements=requirements,
        checks=checks,
        errors=errors,
    )
    return errors


def semantic_statuses_by_group(ledger: dict[str, Any]) -> dict[str, str]:
    """Return worst semantic status for each event group."""
    groups = {
        str(row.get("event_group_id", "")).strip()
        for row in ledger.get("semantic_checks", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip()
    }
    return {group: str(semantic_summary(ledger, group)["status"]) for group in groups}


def _effective_check_result(
    row: dict[str, Any],
    *,
    actions: dict[str, dict[str, Any]],
    runtime_checks: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    recorded_status = str(row.get("status", "")).strip().upper()
    derived_statuses = [recorded_status]
    derived_reason = str(row.get("reason") or "").strip()
    action = actions.get(str(row.get("action_id", "")).strip())
    if (
        action is not None
        and row.get("kind") in {"PAGE_ACTION_VALIDITY", "BUSINESS_STATE"}
        and (
            _action_page_invalid(action, runtime_checks)
            or action.get("interaction_outcome") != "completed"
        )
    ):
        derived_statuses.append("FAIL")
        derived_reason = (
            "Captured before/after page health or the interaction outcome invalidates "
            "this business action."
        )
    if (
        row.get("kind") in POSITIVE_SEMANTIC_KINDS
        and row.get("anchor_state") == "PRESENT"
        and (
            recorded_status == "NOT_APPLICABLE"
            or _empty_business_value(row.get("anchor_value"))
            or (recorded_status == "PASS" and _empty_business_value(row.get("observed_value")))
        )
    ):
        derived_statuses.append("FAIL")
        derived_reason = "The required positive business anchor is not a non-empty accepted value."
    return worst_status(derived_statuses), derived_reason


def semantic_summary(ledger: dict[str, Any], event_group_id: str) -> dict[str, Any]:
    """Return concise semantic checks for event feedback and reporting."""
    checks = [
        row
        for row in ledger.get("semantic_checks", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip() == event_group_id
    ]
    actions = {
        str(row.get("action_id", "")).strip(): row
        for row in ledger.get("actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    runtime_checks = {
        str(row.get("check_id", "")).strip(): row
        for row in ledger.get("runtime_checks", [])
        if isinstance(row, dict) and str(row.get("check_id", "")).strip()
    }
    effective = [
        _effective_check_result(row, actions=actions, runtime_checks=runtime_checks)
        for row in checks
    ]
    return {
        "status": worst_status(result[0] for result in effective),
        "checks": [
            {
                "check_id": row.get("check_id"),
                "case_id": row.get("case_id"),
                "kind": row.get("kind"),
                "subject": row.get("subject"),
                "status": effective[index][0],
                "reason": effective[index][1],
                "authority": row.get("authority"),
                "evidence_ids": list(row.get("evidence_ids", [])),
            }
            for index, row in enumerate(checks)
        ],
    }
