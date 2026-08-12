#!/usr/bin/env python3
"""Build concise, evidence-backed per-event recette feedback."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from acceptance_contract import expects_absence, worst_status
from execution_contract import case_action_rows
from layer_contract import TAG_RESULT_LAYERS

VERDICT_TO_LAYER = {
    "event_occurrence": "event_occurrence",
    "source_signal": "source_signal_when_no_data_layer_push",
    "raw_payload": "raw_api_call",
    "resolved_data_layer": "resolved_data_layer",
    "gtm_variable": "gtm_variable",
    "tag_configuration": "tag_configuration",
    "tag_firing": "tag_firing",
    "tag_parameter": "tag_parameter",
    "destination_request": "destination_request_when_applicable",
    "destination_parameter": "destination_request_when_applicable",
    "trigger_logic": "trigger_logic_when_applicable",
    "tag_sequence": "tag_sequence_when_applicable",
    "consent": "consent_when_applicable",
    "business_rule": "business_rules_when_declared",
    "sensitive_data": "sensitive_data_scan",
    "client_checks": "client_checks_when_applicable",
    "regression": "regression_when_baseline_provided",
}

EXECUTION_TO_FEEDBACK_LAYER = {layer: layer for layer in VERDICT_TO_LAYER.values()}
EXECUTION_TO_FEEDBACK_LAYER.update(
    {
        "action_boundary": "action_boundary",
        "concerned_tag_inventory": "concerned_tag_inventory",
        "container_context_when_applicable": "container_context_when_applicable",
        "conditional_scenarios_when_applicable": "conditional_scenarios_when_applicable",
    }
)

ANOMALY_FLAGS = {
    "duplicate": "DUPLICATE_OCCURRENCE",
    "premature": "PREMATURE_OCCURRENCE",
    "delayed": "DELAYED_OCCURRENCE",
    "wrong_order": "WRONG_ORDER_OCCURRENCE",
    "wrong_context": "WRONG_CONTEXT_OCCURRENCE",
    "unplanned_relevant": "UNPLANNED_EVENT_OBSERVED",
}


def status(value: Any) -> str:
    return str(value or "").strip().upper()


def _variant_text(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return "default variant"
    return ", ".join(
        f"{key}={json.dumps(item, ensure_ascii=False)}" for key, item in sorted(value.items())
    )


def _retest_instruction(case: dict[str, Any]) -> str:
    return (
        f'At {case.get("url")}, {case.get("action")} "{case.get("element")}" '
        f"in {case.get('placement')} ({_variant_text(case.get('material_variant'))})."
    )


def _group_rows(
    rows: Iterable[Any],
    field: str,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if isinstance(row, dict):
            grouped[str(row.get(field, ""))].append(row)
    return dict(grouped)


def _collect_requirement_feedback(
    requirements: list[dict[str, Any]],
    layer_statuses: dict[str, list[str]],
    reasons: list[str],
    evidence_ids: set[str],
) -> None:
    for requirement in requirements:
        verdict = requirement.get("verdict", {})
        if isinstance(verdict, dict):
            for component, layer in VERDICT_TO_LAYER.items():
                component_status = status(verdict.get(component))
                if component_status:
                    layer_statuses[layer].append(component_status)
            mismatch = str(verdict.get("mismatch") or "").strip()
            if status(verdict.get("overall")) != "PASS" and mismatch:
                reasons.append(mismatch)
        evidence_ids.update(
            str(evidence_id).strip()
            for evidence_id in requirement.get("evidence_ids", [])
            if str(evidence_id).strip()
        )


def _collect_case_execution(
    case: dict[str, Any],
    layer_statuses: dict[str, list[str]],
    reasons: list[str],
    affected_case_ids: set[str],
) -> None:
    case_id = str(case.get("case_id", ""))
    execution_status = case.get("execution_status")
    if execution_status == "BLOCKED":
        layer_statuses["case_execution"].append("BLOCKED")
        affected_case_ids.add(case_id)
        reason = str(case.get("case_reason") or "").strip()
        if reason:
            reasons.append(reason)
    elif execution_status == "NOT_TESTED":
        layer_statuses["case_execution"].append("NOT_TESTED")
    elif execution_status == "PENDING":
        layer_statuses["case_execution"].append("BLOCKED")
        affected_case_ids.add(case_id)
        reasons.append(f"Interaction case {case_id} is still pending.")


def _collect_final_action_layers(
    case: dict[str, Any],
    layer_statuses: dict[str, list[str]],
    reasons: list[str],
    affected_case_ids: set[str],
    evidence_ids: set[str],
) -> None:
    if case.get("execution_status") == "EXECUTED" and case.get("action_id") != case.get(
        "final_action_id"
    ):
        return
    case_id = str(case.get("case_id", ""))
    for layer_result in case.get("layer_results") or []:
        if not isinstance(layer_result, dict):
            continue
        layer_name = str(layer_result.get("layer", ""))
        feedback_layer = EXECUTION_TO_FEEDBACK_LAYER.get(layer_name, layer_name)
        layer_result_status = status(layer_result.get("status"))
        if layer_result_status and layer_result_status != "NOT_APPLICABLE":
            layer_statuses[feedback_layer].append(layer_result_status)
        if layer_result_status not in {"PASS", "NOT_APPLICABLE"}:
            affected_case_ids.add(case_id)
            reason = str(layer_result.get("reason") or "").strip()
            if reason:
                reasons.append(reason)
        evidence_ids.update(
            str(evidence_id).strip()
            for evidence_id in layer_result.get("evidence_ids", [])
            if str(evidence_id).strip()
        )


def _collect_case_feedback(
    cases: list[dict[str, Any]],
    layer_statuses: dict[str, list[str]],
    reasons: list[str],
    evidence_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    unique_cases: dict[str, dict[str, Any]] = {}
    affected_case_ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("case_id", ""))
        if case_id not in unique_cases:
            unique_cases[case_id] = case
            _collect_case_execution(
                case,
                layer_statuses,
                reasons,
                affected_case_ids,
            )
        _collect_final_action_layers(
            case,
            layer_statuses,
            reasons,
            affected_case_ids,
            evidence_ids,
        )
    return unique_cases, affected_case_ids


def _layer_feedback_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for case in cases:
        if case.get("execution_status") == "EXECUTED" and case.get("action_id") != case.get(
            "final_action_id"
        ):
            continue
        for row in case.get("layer_results") or []:
            if not isinstance(row, dict):
                continue
            output.append(
                {
                    "case_id": case.get("case_id"),
                    "action_id": case.get("action_id"),
                    "layer": str(row.get("layer", "")),
                    "status": status(row.get("status")),
                    "reason": str(row.get("reason") or "").strip(),
                    "predicate_result": row.get("predicate_result"),
                    "evidence_ids": sorted(
                        str(value).strip()
                        for value in row.get("evidence_ids", [])
                        if str(value).strip()
                    ),
                }
            )
    return output


def _tag_feedback_rows(
    session: dict[str, Any] | None,
    group_id: str,
) -> list[dict[str, Any]]:
    if not isinstance(session, dict):
        return []
    cases = [
        row
        for row in session.get("cases", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")) == group_id
    ]
    actions = {
        str(row.get("action_id", "")): row
        for row in session.get("actions", [])
        if isinstance(row, dict)
    }
    output: list[dict[str, Any]] = []
    for case in cases:
        action = actions.get(str(case.get("final_action_id", "")), {})
        results_by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for result in action.get("tag_layer_results", []) or []:
            if isinstance(result, dict):
                results_by_tag[str(result.get("tag_id", ""))].append(result)
        for tag in case.get("tag_inventory", []) or []:
            if not isinstance(tag, dict):
                continue
            tag_id = str(tag.get("tag_id", ""))
            layers = [
                {
                    "layer": row.get("layer"),
                    "status": status(row.get("status")),
                    "reason": str(row.get("reason") or "").strip(),
                    "evidence_ids": sorted(
                        str(value).strip()
                        for value in row.get("evidence_ids", [])
                        if str(value).strip()
                    ),
                    "details": row.get("details") or {},
                }
                for row in sorted(
                    results_by_tag.get(tag_id, []),
                    key=lambda result: (
                        TAG_RESULT_LAYERS.index(str(result.get("layer")))
                        if str(result.get("layer")) in TAG_RESULT_LAYERS
                        else len(TAG_RESULT_LAYERS)
                    ),
                )
            ]
            output.append(
                {
                    "case_id": case.get("case_id"),
                    "action_id": action.get("action_id"),
                    "tag_id": tag_id,
                    "tag_name": tag.get("tag_name"),
                    "tag_category": tag.get("tag_category"),
                    "tag_delivery": tag.get("tag_delivery"),
                    "scope_status": tag.get("scope_status"),
                    "scope_reason": tag.get("scope_reason"),
                    "evidence_ids": sorted(
                        str(value).strip()
                        for value in tag.get("evidence_ids", [])
                        if str(value).strip()
                    ),
                    "status": (
                        worst_status(row.get("status") for row in results_by_tag.get(tag_id, []))
                        if tag.get("scope_status") == "IN_SCOPE"
                        else "NOT_APPLICABLE"
                    ),
                    "layers": layers,
                }
            )
    return output


def _case_counts(cases: Iterable[dict[str, Any]]) -> dict[str, int]:
    cases = list(cases)
    return {
        "applicable": sum(case.get("scope_status") == "IN_SCOPE" for case in cases),
        "executed": sum(case.get("execution_status") == "EXECUTED" for case in cases),
        "blocked": sum(case.get("execution_status") == "BLOCKED" for case in cases),
        "not_tested": sum(case.get("execution_status") == "NOT_TESTED" for case in cases),
        "pending": sum(case.get("execution_status") == "PENDING" for case in cases),
    }


def _anomaly_flags(
    requirements: list[dict[str, Any]],
    unexpected: list[dict[str, Any]],
    session: dict[str, Any] | None,
    group_id: str,
) -> list[str]:
    flags: set[str] = set()
    for requirement in requirements:
        expectation = requirement.get("expectation", {})
        if (
            isinstance(expectation, dict)
            and expectation.get("source_mechanism", "data_layer_push") == "data_layer_push"
            and not expects_absence(expectation)
            and requirement.get("event_observed") is False
        ):
            flags.add("MISSING_EXPECTED_OCCURRENCE")
    rows = list(unexpected)
    if isinstance(session, dict):
        rows.extend(
            row
            for row in session.get("business_pushes", [])
            if isinstance(row, dict) and str(row.get("event_group_id", "")) == group_id
        )
    for row in rows:
        classification = str(row.get("classification", "")).strip()
        if classification in ANOMALY_FLAGS:
            flags.add(ANOMALY_FLAGS[classification])
    return sorted(flags)


def _tag_layer_details(
    tag_feedback: list[dict[str, Any]],
    layer: str,
) -> list[dict[str, Any]]:
    return [
        row.get("details") or {}
        for tag in tag_feedback
        for row in tag.get("layers", [])
        if isinstance(tag, dict)
        and isinstance(row, dict)
        and row.get("layer") == layer
        and status(row.get("status")) == "FAIL"
    ]


def _primary_outcome(
    overall_status: str,
    requirements: list[dict[str, Any]],
    counts: dict[str, int],
    verified_layers: dict[str, str],
    tag_feedback: list[dict[str, Any]],
    anomaly_flags: list[str],
) -> str:
    """Return the first actionable broken link without replacing the verdict."""
    if overall_status == "PASS":
        return "PASS"
    if counts["not_tested"] and not counts["executed"] and not counts["blocked"]:
        return "NOT_TESTED"
    if counts["blocked"] and not counts["executed"]:
        return "JOURNEY_BLOCKED"
    if counts["pending"] or (counts["applicable"] and counts["executed"] < counts["applicable"]):
        return "PARTIAL_VARIANT_COVERAGE"

    expected_push_missing = any(
        isinstance(requirement.get("expectation"), dict)
        and requirement["expectation"].get("source_mechanism", "data_layer_push")
        == "data_layer_push"
        and not expects_absence(requirement["expectation"])
        and requirement.get("event_observed") is False
        for requirement in requirements
    )
    if expected_push_missing:
        return "DATALAYER_EVENT_ABSENT"

    failure_order = (
        ("action_boundary", "ACTION_WINDOW_INVALID"),
        ("raw_api_call", "DATALAYER_PAYLOAD_INVALID"),
        ("resolved_data_layer", "RESOLVED_DATA_LAYER_INVALID"),
        ("concerned_tag_inventory", "CONCERNED_TAG_NOT_FOUND"),
        ("gtm_variable", "GTM_VARIABLE_INVALID"),
        ("tag_configuration", "TAG_CONFIGURATION_INVALID"),
        ("tag_firing", "TAG_FIRING_INVALID"),
        ("tag_parameter", "TAG_RUNTIME_PARAMETER_INVALID"),
        ("destination_request_when_applicable", "REQUEST_PARAMETER_INVALID"),
        ("consent_when_applicable", "CONSENT_INVALID"),
        ("trigger_logic_when_applicable", "TRIGGER_LOGIC_INVALID"),
    )
    for layer, outcome in failure_order:
        if status(verified_layers.get(layer)) != "FAIL":
            continue
        if layer == "tag_firing":
            details = _tag_layer_details(tag_feedback, layer)
            if details and all(row.get("fire_count", 0) == 0 for row in details):
                return "TAG_NOT_FIRED"
        if layer == "destination_request_when_applicable":
            details = _tag_layer_details(tag_feedback, layer)
            if details and all(row.get("request_count", 0) == 0 for row in details):
                return "TAG_FIRED_REQUEST_ABSENT"
        return outcome
    if anomaly_flags:
        return "OCCURRENCE_ANOMALY"
    if overall_status == "REVIEW":
        return "SEMANTIC_REVIEW"
    if overall_status == "BLOCKED":
        return "EVIDENCE_UNAVAILABLE"
    return "OTHER_CONFIRMED_MISMATCH"


def event_feedback(
    data: dict[str, Any],
    session: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return one detailed feedback object per event in original plan order."""
    requirements_by_group = _group_rows(
        data.get("requirements", []),
        "event_group_id",
    )
    cases_by_group = (
        _group_rows(case_action_rows(session), "event_group_id")
        if isinstance(session, dict)
        else {}
    )
    unexpected_by_group = _group_rows(data.get("unexpected", []), "event_group_id")

    output: list[dict[str, Any]] = []
    for inventory in data.get("run", {}).get("event_inventory", []):
        if not isinstance(inventory, dict):
            continue
        group_id = str(inventory.get("event_group_id", ""))
        requirements = requirements_by_group.get(group_id, [])
        cases = cases_by_group.get(group_id, [])
        layer_statuses: dict[str, list[str]] = defaultdict(list)
        reasons: list[str] = []
        evidence_ids: set[str] = set()

        _collect_requirement_feedback(
            requirements,
            layer_statuses,
            reasons,
            evidence_ids,
        )
        unique_cases, affected_case_ids = _collect_case_feedback(
            cases,
            layer_statuses,
            reasons,
            evidence_ids,
        )
        layer_feedback = _layer_feedback_rows(cases)
        tag_feedback = _tag_feedback_rows(session, group_id)
        mapped_unexpected = unexpected_by_group.get(group_id, [])
        for unexpected in mapped_unexpected:
            unexpected_status = status(unexpected.get("status"))
            if unexpected_status:
                layer_statuses["unexpected_business_push"].append(unexpected_status)
            if unexpected_status != "PASS":
                reason = str(
                    unexpected.get("classification_reason")
                    or unexpected.get("review_question")
                    or unexpected.get("notes")
                    or ""
                ).strip()
                if reason:
                    reasons.append(reason)
                case_id = str(unexpected.get("case_id", "")).strip()
                if case_id:
                    affected_case_ids.add(case_id)
            unexpected_evidence = unexpected.get("evidence_ids", [])
            if not isinstance(unexpected_evidence, list):
                unexpected_evidence = [unexpected_evidence]
            evidence_ids.update(
                str(evidence_id).strip()
                for evidence_id in unexpected_evidence
                if str(evidence_id).strip()
            )
        session_statuses = [
            row.get("status") for row in layer_feedback if row.get("status") != "NOT_APPLICABLE"
        ]
        normalized_status = worst_status(
            [
                requirement.get("verdict", {}).get("overall")
                for requirement in requirements
                if isinstance(requirement.get("verdict"), dict)
            ]
            + [unexpected.get("status") for unexpected in mapped_unexpected]
            + session_statuses
        )
        retest_cases = [
            case
            for case_id, case in unique_cases.items()
            if (
                normalized_status != "PASS"
                and (not affected_case_ids or case_id in affected_case_ids)
            )
        ]
        visible_layers: dict[str, list[str]] = defaultdict(list)
        for row in layer_feedback:
            visible_layers[str(row.get("layer", ""))].append(str(row.get("status", "")))
        verified_layers = {
            layer: (
                worst_status(value for value in values if value != "NOT_APPLICABLE")
                if any(value != "NOT_APPLICABLE" for value in values)
                else "NOT_APPLICABLE"
            )
            for layer, values in sorted(visible_layers.items())
        }
        for layer, values in layer_statuses.items():
            verified_layers.setdefault(layer, worst_status(values))
        counts = _case_counts(unique_cases.values())
        anomaly_flags = _anomaly_flags(
            requirements,
            mapped_unexpected,
            session,
            group_id,
        )
        output.append(
            {
                "plan_order": inventory.get("plan_order"),
                "event_group_id": group_id,
                "event_name": inventory.get("event_name"),
                "status": normalized_status,
                "primary_outcome": _primary_outcome(
                    normalized_status,
                    requirements,
                    counts,
                    verified_layers,
                    tag_feedback,
                    anomaly_flags,
                ),
                "anomaly_flags": anomaly_flags,
                "requirement_count": len(requirements),
                "case_counts": counts,
                "verified_layers": verified_layers,
                "layer_feedback": layer_feedback,
                "tag_feedback": tag_feedback,
                "reason": " | ".join(dict.fromkeys(reasons)),
                "retest": " ".join(_retest_instruction(case) for case in retest_cases),
                "evidence_ids": sorted(evidence_ids),
            }
        )
    return output


def feedback_for_event(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one event feedback object or raise for an unknown event group."""
    for row in event_feedback(data, session):
        if row.get("event_group_id") == event_group_id:
            return row
    raise ValueError(f"Unknown event_group_id: {event_group_id}")
