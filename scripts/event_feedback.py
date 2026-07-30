#!/usr/bin/env python3
"""Build concise, evidence-backed per-event recette feedback."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from acceptance_contract import worst_status
from execution_contract import case_action_rows

VERDICT_TO_LAYER = {
    "event_occurrence": "event_occurrence",
    "source_signal": "source_signal",
    "raw_payload": "raw_api_call",
    "resolved_data_layer": "resolved_data_layer",
    "gtm_variable": "gtm_variable",
    "tag_configuration": "tag_configuration",
    "tag_firing": "tag_firing",
    "tag_parameter": "tag_parameter",
    "destination_request": "destination_request",
    "destination_parameter": "destination_parameter",
    "trigger_logic": "trigger_logic",
    "tag_sequence": "tag_sequence",
    "consent": "consent",
    "business_rule": "business_rule",
    "sensitive_data": "sensitive_data",
    "client_checks": "client_checks",
    "regression": "regression",
}

EXECUTION_TO_FEEDBACK_LAYER = {
    "raw_api_call": "raw_api_call",
    "resolved_data_layer": "resolved_data_layer",
    "gtm_variable": "gtm_variable",
    "tag_configuration": "tag_configuration",
    "tag_firing": "tag_firing",
    "tag_parameter": "tag_parameter",
    "consent_when_applicable": "consent",
    "source_signal_when_no_data_layer_push": "source_signal",
    "destination_request_when_applicable": "destination_request",
    "trigger_logic_when_applicable": "trigger_logic",
    "tag_sequence_when_applicable": "tag_sequence",
    "business_rules_when_declared": "business_rule",
    "sensitive_data_scan": "sensitive_data",
    "client_checks_when_applicable": "client_checks",
    "regression_when_baseline_provided": "regression",
    "container_context_when_applicable": "container_context",
    "conditional_scenarios_when_applicable": "conditional_scenarios",
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
        if layer_result_status:
            layer_statuses[feedback_layer].append(layer_result_status)
        if layer_result_status != "PASS":
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


def _case_counts(cases: Iterable[dict[str, Any]]) -> dict[str, int]:
    cases = list(cases)
    return {
        "applicable": sum(case.get("scope_status") == "IN_SCOPE" for case in cases),
        "executed": sum(case.get("execution_status") == "EXECUTED" for case in cases),
        "blocked": sum(case.get("execution_status") == "BLOCKED" for case in cases),
        "not_tested": sum(case.get("execution_status") == "NOT_TESTED" for case in cases),
        "pending": sum(case.get("execution_status") == "PENDING" for case in cases),
    }


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
        normalized_status = worst_status(
            [
                requirement.get("verdict", {}).get("overall")
                for requirement in requirements
                if isinstance(requirement.get("verdict"), dict)
            ]
            + [unexpected.get("status") for unexpected in mapped_unexpected]
        )
        retest_cases = [
            case
            for case_id, case in unique_cases.items()
            if (
                normalized_status != "PASS"
                and (not affected_case_ids or case_id in affected_case_ids)
            )
        ]
        output.append(
            {
                "plan_order": inventory.get("plan_order"),
                "event_group_id": group_id,
                "event_name": inventory.get("event_name"),
                "status": normalized_status,
                "requirement_count": len(requirements),
                "case_counts": _case_counts(unique_cases.values()),
                "verified_layers": {
                    layer: worst_status(values) for layer, values in sorted(layer_statuses.items())
                },
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
