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
from scenario_coverage import coverage_errors, coverage_summary
from semantic_contract import semantic_summary
from stream_contract import stream_errors, stream_summary

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

HUMAN_STATUSES = {
    "PASS": "OK",
    "FAIL": "KO",
    "BLOCKED": "BLOCKED",
    "REVIEW": "REVIEW",
    "NOT_TESTED": "NOT_TESTED",
}
TECHNICAL_DELIVERY_LAYERS = {
    "raw_api_call",
    "resolved_data_layer",
    "concerned_tag_inventory",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "destination_request_when_applicable",
    "consent_when_applicable",
    "source_signal_when_no_data_layer_push",
    "trigger_logic_when_applicable",
    "tag_sequence_when_applicable",
    "container_context_when_applicable",
}


def status(value: Any) -> str:
    return str(value or "").strip().upper()


def _contract_component_status(value: Any, *, passing_state: str) -> str:
    """Map a workflow state to a verdict without allowing unfinished work to pass."""
    normalized = status(value)
    if normalized == passing_state:
        return "PASS"
    if normalized in {"FAIL", "BLOCKED", "REVIEW"}:
        return normalized
    return "BLOCKED"


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


def _case_feedback_rows(
    session: dict[str, Any] | None,
    group_id: str,
) -> list[dict[str, Any]]:
    """Return one concise, fully layered feedback object per tested case."""
    if not isinstance(session, dict):
        return []
    actions = [row for row in session.get("actions", []) if isinstance(row, dict)]
    semantic_checks = [row for row in session.get("semantic_checks", []) if isinstance(row, dict)]
    output: list[dict[str, Any]] = []
    for case in session.get("cases", []):
        if not isinstance(case, dict) or str(case.get("event_group_id", "")) != group_id:
            continue
        case_actions = sorted(
            [row for row in actions if row.get("case_id") == case.get("case_id")],
            key=lambda row: row.get("attempt_number", 0),
        )
        action = next(
            (row for row in case_actions if row.get("action_id") == case.get("final_action_id")),
            case_actions[-1] if case_actions else {},
        )
        layers = [row for row in action.get("layer_results", []) if isinstance(row, dict)]
        technical_status = worst_status(
            row.get("status")
            for row in layers
            if row.get("layer") in TECHNICAL_DELIVERY_LAYERS
            if status(row.get("status")) != "NOT_APPLICABLE"
        )
        checks = [
            row
            for row in semantic_checks
            if row.get("case_id") == case.get("case_id")
            and (not action.get("action_id") or row.get("action_id") == action.get("action_id"))
        ]
        semantic_status = (
            worst_status(row.get("status") for row in checks)
            if session.get("operator_contract_version") == 2
            else "NOT_TESTED"
        )
        execution_status = case.get("execution_status")
        execution_component = {
            "EXECUTED": "PASS",
            "BLOCKED": "BLOCKED",
            "PENDING": "BLOCKED",
            "NOT_TESTED": "NOT_TESTED",
        }.get(str(execution_status), "REVIEW")
        overall_components = [technical_status, execution_component]
        if session.get("operator_contract_version") == 2:
            overall_components.append(semantic_status)
        overall_status = worst_status(overall_components)
        reasons = [
            str(case.get("reason") or "").strip(),
            *[
                str(row.get("reason") or "").strip()
                for row in layers
                if status(row.get("status")) not in {"PASS", "NOT_APPLICABLE"}
            ],
            *[
                str(row.get("reason") or "").strip()
                for row in checks
                if status(row.get("status")) not in {"PASS", "NOT_APPLICABLE"}
            ],
        ]
        output.append(
            {
                "case_id": case.get("case_id"),
                "action_id": action.get("action_id"),
                "url": case.get("url"),
                "interaction": f"{case.get('action')} {case.get('element')}",
                "placement": case.get("placement"),
                "material_variant": case.get("material_variant"),
                "scenario_class_id": case.get("scenario_class_id"),
                "sample_role": case.get("sample_role"),
                "selection_rationale": case.get("selection_rationale"),
                "acquisition_context": case.get("acquisition_context"),
                "gated_flow_kind": case.get("gated_flow_kind"),
                "execution_status": execution_status,
                "technical_status": technical_status,
                "semantic_status": semantic_status,
                "status": overall_status,
                "status_label": HUMAN_STATUSES.get(overall_status, overall_status),
                "reason": " | ".join(item for item in dict.fromkeys(reasons) if item),
                "layers": [
                    {
                        "layer": row.get("layer"),
                        "status": status(row.get("status")),
                        "reason": str(row.get("reason") or "").strip(),
                        "evidence_ids": list(row.get("evidence_ids", [])),
                    }
                    for row in layers
                ],
                "semantic_checks": [
                    {
                        "kind": row.get("kind"),
                        "subject": row.get("subject"),
                        "status": status(row.get("status")),
                        "reason": row.get("reason"),
                    }
                    for row in checks
                ],
            }
        )
    return output


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
        ("page_and_journey", "PAGE_OR_JOURNEY_INVALID"),
        ("business_semantics", "BUSINESS_STATE_INVALID"),
        ("continuous_stream", "INTERACTION_STREAM_INVALID"),
        ("scenario_coverage", "SCENARIO_COVERAGE_INVALID"),
        ("event_occurrence", "EVENT_OCCURRENCE_INVALID"),
        ("action_boundary", "ACTION_WINDOW_INVALID"),
        ("source_signal_when_no_data_layer_push", "SOURCE_SIGNAL_INVALID"),
        ("raw_api_call", "DATALAYER_PAYLOAD_INVALID"),
        ("resolved_data_layer", "RESOLVED_DATA_LAYER_INVALID"),
        ("concerned_tag_inventory", "CONCERNED_TAG_NOT_FOUND"),
        ("gtm_variable", "GTM_VARIABLE_INVALID"),
        ("tag_configuration", "TAG_CONFIGURATION_INVALID"),
        ("tag_firing", "TAG_FIRING_INVALID"),
        ("tag_parameter", "TAG_RUNTIME_PARAMETER_INVALID"),
        ("destination_request_when_applicable", "REQUEST_PARAMETER_INVALID"),
        ("sensitive_data_scan", "SENSITIVE_DATA_INVALID"),
        ("consent_when_applicable", "CONSENT_INVALID"),
        ("trigger_logic_when_applicable", "TRIGGER_LOGIC_INVALID"),
        ("tag_sequence_when_applicable", "TAG_SEQUENCE_INVALID"),
        ("business_rules_when_declared", "BUSINESS_RULE_INVALID"),
        ("client_checks_when_applicable", "CLIENT_CHECK_INVALID"),
        ("regression_when_baseline_provided", "REGRESSION_INVALID"),
        ("container_context_when_applicable", "CONTAINER_CONTEXT_INVALID"),
        ("conditional_scenarios_when_applicable", "CONDITIONAL_SCENARIO_INVALID"),
        ("unexpected_business_push", "OCCURRENCE_ANOMALY"),
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
    contract_v2 = isinstance(session, dict) and session.get("operator_contract_version") == 2
    closed_stream_errors: list[str] = []
    frozen_coverage_errors: list[str] = []
    if contract_v2:
        if status((session.get("stream_contract") or {}).get("status")) == "CLOSED":
            closed_stream_errors = stream_errors(session, final=True)
        if any(
            status(row.get("status")) == "FROZEN"
            for row in session.get("coverage_decisions", [])
            if isinstance(row, dict)
        ):
            frozen_coverage_errors = coverage_errors(session, results=data, final=True)

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
        coverage_info = coverage_summary(session, group_id) if contract_v2 else None
        semantic_info = semantic_summary(session, group_id) if contract_v2 else None
        stream_info = stream_summary(session, group_id) if contract_v2 else None
        if isinstance(stream_info, dict) and closed_stream_errors:
            stream_info["validation_errors"] = list(closed_stream_errors)
        if isinstance(coverage_info, dict) and frozen_coverage_errors:
            coverage_info["validation_errors"] = list(frozen_coverage_errors)
        case_feedback = _case_feedback_rows(session, group_id)
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
        evidence_status = worst_status(
            [
                requirement.get("verdict", {}).get("overall")
                for requirement in requirements
                if isinstance(requirement.get("verdict"), dict)
            ]
            + [unexpected.get("status") for unexpected in mapped_unexpected]
            + session_statuses
            + layer_statuses.get("case_execution", [])
        )
        counts = _case_counts(unique_cases.values())
        anomaly_flags = _anomaly_flags(
            requirements,
            mapped_unexpected,
            session,
            group_id,
        )
        semantic_checks = semantic_info.get("checks", []) if semantic_info else []
        semantic_status = status(semantic_info.get("status")) if semantic_info else "NOT_TESTED"
        page_and_journey_status = (
            worst_status(
                row.get("status")
                for row in semantic_checks
                if row.get("kind") in {"PAGE_ACTION_VALIDITY", "JOURNEY_CONTINUITY"}
            )
            if contract_v2
            else "NOT_TESTED"
        )
        business_semantic_status = (
            worst_status(
                row.get("status")
                for row in semantic_checks
                if row.get("kind") in {"POSITIVE_ANCHOR", "BUSINESS_STATE", "PLATFORM_SEMANTICS"}
            )
            if contract_v2
            else "NOT_TESTED"
        )
        chronology_status = "NOT_TESTED"
        coverage_status = "NOT_TESTED"
        if contract_v2:
            chronology_status = (
                "FAIL"
                if anomaly_flags or closed_stream_errors
                else _contract_component_status(
                    (stream_info or {}).get("review_status"),
                    passing_state="CLOSED",
                )
            )
            coverage_status = (
                "FAIL"
                if status((coverage_info or {}).get("status")) == "FROZEN"
                and frozen_coverage_errors
                else _contract_component_status(
                    (coverage_info or {}).get("status"),
                    passing_state="FROZEN",
                )
            )

        normalized_components = [evidence_status]
        if contract_v2:
            normalized_components.extend([semantic_status, chronology_status, coverage_status])
        normalized_status = worst_status(normalized_components)
        if contract_v2 and isinstance(semantic_info, dict):
            for check in semantic_info.get("checks", []):
                if status(check.get("status")) not in {"PASS", "NOT_APPLICABLE"}:
                    reason = str(check.get("reason") or "").strip()
                    if reason:
                        reasons.append(reason)
        if contract_v2 and chronology_status != "PASS":
            reasons.append(
                "Continuous interaction-stream review is "
                f"{chronology_status.lower()} ({(stream_info or {}).get('review_status') or 'missing'})."
            )
        if contract_v2 and coverage_status != "PASS":
            reasons.append(
                "Scenario coverage is "
                f"{coverage_status.lower()} ({(coverage_info or {}).get('status') or 'missing'})."
            )
        if normalized_status == "NOT_TESTED" and any(
            case.get("execution_status") == "PENDING" for case in unique_cases.values()
        ):
            normalized_status = "BLOCKED"
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
        if contract_v2:
            verified_layers["page_and_journey"] = page_and_journey_status
            verified_layers["business_semantics"] = business_semantic_status
            verified_layers["continuous_stream"] = chronology_status
            verified_layers["scenario_coverage"] = coverage_status
        technical_status = worst_status(
            layer_status
            for layer, layer_status in verified_layers.items()
            if layer in TECHNICAL_DELIVERY_LAYERS and status(layer_status) != "NOT_APPLICABLE"
        )
        output.append(
            {
                "plan_order": inventory.get("plan_order"),
                "event_group_id": group_id,
                "event_name": inventory.get("event_name"),
                "status": normalized_status,
                "status_label": HUMAN_STATUSES.get(normalized_status, normalized_status),
                "technical_status": technical_status,
                "semantic_status": semantic_status,
                "component_statuses": {
                    "technical_delivery": technical_status,
                    "page_and_journey": page_and_journey_status,
                    "business_semantics": business_semantic_status,
                    "continuous_stream": chronology_status,
                    "scenario_coverage": coverage_status,
                },
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
                "case_feedback": case_feedback,
                "coverage": coverage_info,
                "semantic": semantic_info,
                "stream": stream_info,
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


def final_conclusion(
    data: dict[str, Any],
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the concise end-of-run event/layer/status/why conclusion."""
    events = event_feedback(data, session)
    overall = worst_status(row.get("status") for row in events)
    return {
        "status": overall,
        "status_label": HUMAN_STATUSES.get(overall, overall),
        "event_counts": {
            state: sum(status(row.get("status")) == state for row in events)
            for state in ("PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_TESTED")
        },
        "events": [
            {
                "plan_order": row.get("plan_order"),
                "event_group_id": row.get("event_group_id"),
                "event_name": row.get("event_name"),
                "status": row.get("status"),
                "status_label": row.get("status_label"),
                "technical_status": row.get("technical_status"),
                "semantic_status": row.get("semantic_status"),
                "stream_status": row.get("component_statuses", {}).get("continuous_stream"),
                "coverage_status": row.get("component_statuses", {}).get("scenario_coverage"),
                "layers_inspected": [
                    {
                        "layer": layer,
                        "status": layer_status,
                    }
                    for layer, layer_status in row.get("verified_layers", {}).items()
                ],
                "why": row.get("reason") or row.get("primary_outcome"),
            }
            for row in events
        ],
    }
