#!/usr/bin/env python3
"""Validate safe form execution and protected-gate handoff state."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

FLOW_KINDS = {"NONE", "FORM", "REGISTRATION", "LOGIN", "LEAD", "CHECKOUT", "OTHER"}
FLOW_STATUSES = {"COMPLETED", "FAILED", "BLOCKED"}
CONSENT_OUTCOMES = {"NOT_APPLICABLE", "UNTOUCHED", "ACCEPTED", "REFUSED", "PARTIAL"}
CAPTCHA_OUTCOMES = {"NOT_PRESENT", "PRESENT_HANDOFF", "BLOCKED"}
DATA_ENTRY_FLOW_KINDS = {"FORM", "REGISTRATION", "LOGIN", "LEAD", "CHECKOUT"}
FLOW_STATES = {
    "DISCOVERED",
    "SYNTHETIC_DATA_ENTERED",
    "CONSENT_ESTABLISHED",
    "VALIDATION_COMPLETED",
    "SUBMISSION_ATTEMPTED",
    "HANDOFF_REQUESTED",
    "HANDOFF_RESUMED",
    "SUCCEEDED",
    "FAILED",
    "BLOCKED",
}
STATE_ORDER = {
    "DISCOVERED": 10,
    "SYNTHETIC_DATA_ENTERED": 20,
    "CONSENT_ESTABLISHED": 30,
    "VALIDATION_COMPLETED": 40,
    "SUBMISSION_ATTEMPTED": 50,
    "HANDOFF_REQUESTED": 60,
    "HANDOFF_RESUMED": 70,
    "SUCCEEDED": 80,
    "FAILED": 80,
    "BLOCKED": 80,
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


def _flow_rows(value: Any, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("session gated_flows must be an array")
        return []
    flows: list[dict[str, Any]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"session gated flow row {index} must be an object")
        else:
            flows.append(row)
    ids = [str(row.get("flow_id", "")).strip() for row in flows]
    for index, flow_id in enumerate(ids, start=1):
        if not flow_id:
            errors.append(f"session gated flow row {index} missing flow_id")
    duplicates = sorted(
        flow_id for flow_id, count in Counter(item for item in ids if item).items() if count > 1
    )
    if duplicates:
        errors.append("session gated flows contain duplicate IDs " + ", ".join(duplicates))
    return flows


def _validated_states(
    flow: dict[str, Any],
    *,
    label: str,
    status: str,
    errors: list[str],
) -> list[str]:
    states = flow.get("states")
    if not isinstance(states, list) or not states:
        errors.append(f"{label}: states must be a non-empty array")
        states = []
    elif any(state not in FLOW_STATES for state in states):
        errors.append(f"{label}: states contains an invalid state")
    elif len(set(states)) != len(states):
        errors.append(f"{label}: states contains duplicates")
    elif [STATE_ORDER[state] for state in states] != sorted(STATE_ORDER[state] for state in states):
        errors.append(f"{label}: states are out of order")
    if states and states[0] != "DISCOVERED":
        errors.append(f"{label}: state sequence must start with DISCOVERED")
    expected_terminal = {
        "COMPLETED": "SUCCEEDED",
        "FAILED": "FAILED",
        "BLOCKED": "BLOCKED",
    }.get(status)
    if expected_terminal and (not states or states[-1] != expected_terminal):
        errors.append(f"{label}: status and terminal state disagree")
    return states


def _validate_progression(
    flow: dict[str, Any],
    *,
    label: str,
    kind: str,
    status: str,
    states: list[str],
    errors: list[str],
) -> None:
    data_entry = kind in DATA_ENTRY_FLOW_KINDS
    synthetic = flow.get("synthetic_data_used")
    if data_entry and synthetic is not True:
        errors.append(f"{label}: data-entry flow requires synthetic_data_used=true")
    if data_entry and "SYNTHETIC_DATA_ENTERED" not in states:
        errors.append(f"{label}: data-entry flow must record SYNTHETIC_DATA_ENTERED")
    if "SYNTHETIC_DATA_ENTERED" in states and synthetic is not True:
        errors.append(f"{label}: SYNTHETIC_DATA_ENTERED contradicts synthetic_data_used")

    consent_required = flow.get("consent_required")
    if not isinstance(consent_required, bool):
        errors.append(f"{label}: consent_required must be boolean")
    elif consent_required:
        if "CONSENT_ESTABLISHED" not in states:
            errors.append(f"{label}: required consent must record CONSENT_ESTABLISHED")
        if flow.get("consent_outcome") in {"NOT_APPLICABLE", "UNTOUCHED"}:
            errors.append(f"{label}: required consent needs an explicit outcome")
    elif flow.get("consent_outcome") not in {"NOT_APPLICABLE", "UNTOUCHED"}:
        errors.append(f"{label}: non-required consent must be NOT_APPLICABLE or UNTOUCHED")

    if status in {"COMPLETED", "FAILED"}:
        for milestone in ("VALIDATION_COMPLETED", "SUBMISSION_ATTEMPTED"):
            if milestone not in states:
                errors.append(f"{label}: {status} flow must record {milestone}")
    if "HANDOFF_RESUMED" in states and "HANDOFF_REQUESTED" not in states:
        errors.append(f"{label}: HANDOFF_RESUMED requires HANDOFF_REQUESTED")


def _validate_captcha_handoff(
    flow: dict[str, Any],
    *,
    label: str,
    case_id: str,
    action_id: str,
    status: str,
    captcha: Any,
    states: list[str],
    handoffs: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    handoff_id = str(flow.get("handoff_id", "")).strip()
    if captcha not in {"PRESENT_HANDOFF", "BLOCKED"}:
        return
    handoff = handoffs.get(handoff_id)
    if not handoff_id or handoff is None:
        errors.append(f"{label}: CAPTCHA outcome requires a protected handoff")
        return
    for milestone in ("VALIDATION_COMPLETED", "SUBMISSION_ATTEMPTED"):
        if milestone not in states:
            errors.append(f"{label}: CAPTCHA flow must record {milestone} before handoff")
    if "HANDOFF_REQUESTED" not in states:
        errors.append(f"{label}: CAPTCHA outcome requires HANDOFF_REQUESTED state")
    if handoff.get("gate_type") != "CAPTCHA":
        errors.append(f"{label}: CAPTCHA flow requires a CAPTCHA handoff")
    if str(handoff.get("flow_id", "")).strip() != str(flow.get("flow_id", "")).strip():
        errors.append(f"{label}: CAPTCHA handoff is bound to another flow")
    if str(handoff.get("case_id", "")).strip() != case_id:
        errors.append(f"{label}: CAPTCHA handoff is bound to another case")
    if str(handoff.get("action_id", "")).strip() != action_id:
        errors.append(f"{label}: CAPTCHA handoff is bound to another action")
    if captcha == "PRESENT_HANDOFF" and status == "COMPLETED":
        if handoff.get("status") != "RESUMED":
            errors.append(f"{label}: completed CAPTCHA requires a RESUMED handoff")
        if "HANDOFF_RESUMED" not in states:
            errors.append(f"{label}: completed CAPTCHA handoff requires HANDOFF_RESUMED")
    if captcha == "BLOCKED" and (status != "BLOCKED" or handoff.get("status") != "BLOCKED"):
        errors.append(f"{label}: blocked CAPTCHA requires a BLOCKED flow and handoff")


def _validate_flow(
    flow: dict[str, Any],
    *,
    index: int,
    cases: dict[str, dict[str, Any]],
    actions: dict[str, dict[str, Any]],
    handoffs: dict[str, dict[str, Any]],
    flows_by_case: dict[str, list[dict[str, Any]]],
    errors: list[str],
) -> None:
    flow_id = str(flow.get("flow_id", "")).strip() or str(index)
    label = f"session gated flow {flow_id}"
    case_id = str(flow.get("case_id", "")).strip()
    action_id = str(flow.get("action_id", "")).strip()
    if case_id not in cases:
        errors.append(f"{label}: unknown case_id")
    else:
        flows_by_case[case_id].append(flow)
    if action_id not in actions:
        errors.append(f"{label}: unknown action_id")
    elif actions[action_id].get("case_id") != case_id:
        errors.append(f"{label}: action belongs to another case")
    kind = str(flow.get("kind", "")).strip().upper()
    if kind not in FLOW_KINDS - {"NONE"}:
        errors.append(f"{label}: invalid applicable flow kind")
    status = str(flow.get("status", "")).strip().upper()
    if status not in FLOW_STATUSES:
        errors.append(f"{label}: invalid status")
    if flow.get("safe_environment_confirmed") is not True:
        errors.append(f"{label}: safe_environment_confirmed must be true")
    if not isinstance(flow.get("synthetic_data_used"), bool):
        errors.append(f"{label}: synthetic_data_used must be boolean")
    if flow.get("consent_outcome") not in CONSENT_OUTCOMES:
        errors.append(f"{label}: invalid consent_outcome")
    captcha = flow.get("captcha_outcome")
    if captcha not in CAPTCHA_OUTCOMES:
        errors.append(f"{label}: invalid captcha_outcome")
    states = _validated_states(flow, label=label, status=status, errors=errors)
    _validate_progression(
        flow,
        label=label,
        kind=kind,
        status=status,
        states=states,
        errors=errors,
    )
    _validate_captcha_handoff(
        flow,
        label=label,
        case_id=case_id,
        action_id=action_id,
        status=status,
        captcha=captcha,
        states=states,
        handoffs=handoffs,
        errors=errors,
    )
    if not _iso_timestamp(flow.get("recorded_at")):
        errors.append(f"{label}: recorded_at must be ISO 8601 with timezone")
    if not _nonempty(flow.get("reason")):
        errors.append(f"{label}: reason is required")
    refs = flow.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
        errors.append(f"{label}: evidence_ids must be a non-empty string array")


def _validate_case_binding(
    case_id: str,
    case: dict[str, Any],
    *,
    flows_by_case: dict[str, list[dict[str, Any]]],
    final: bool,
    errors: list[str],
) -> None:
    kind = str(case.get("gated_flow_kind", "")).strip().upper()
    if kind not in FLOW_KINDS:
        errors.append(f"session case {case_id}: gated_flow_kind is required and must be valid")
        return
    mapped = flows_by_case.get(case_id, [])
    if kind == "NONE" and mapped:
        errors.append(f"session case {case_id}: NONE gated flow cannot have flow records")
    if kind != "NONE" and final and len(mapped) != 1:
        errors.append(f"session case {case_id}: applicable gated flow requires exactly one record")
    action_text = (
        f"{case.get('action', '')} {case.get('element', '')} {case.get('placement', '')}".lower()
    )
    if (
        any(token in action_text for token in ("submit", "form", "register", "sign up"))
        and kind == "NONE"
    ):
        errors.append(f"session case {case_id}: form-like action cannot use gated_flow_kind NONE")


def gated_flow_errors(ledger: dict[str, Any], *, final: bool) -> list[str]:
    """Return state-machine errors for forms and other safe gated journeys."""
    errors: list[str] = []
    flows = _flow_rows(ledger.get("gated_flows"), errors)
    if not isinstance(ledger.get("gated_flows"), list):
        return errors
    cases = {
        str(row.get("case_id", "")).strip(): row
        for row in ledger.get("cases", [])
        if isinstance(row, dict) and str(row.get("case_id", "")).strip()
    }
    actions = {
        str(row.get("action_id", "")).strip(): row
        for row in ledger.get("actions", [])
        if isinstance(row, dict) and str(row.get("action_id", "")).strip()
    }
    handoffs = {
        str(row.get("handoff_id", "")).strip(): row
        for row in ledger.get("protected_handoffs", [])
        if isinstance(row, dict) and str(row.get("handoff_id", "")).strip()
    }
    flows_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, flow in enumerate(flows, start=1):
        _validate_flow(
            flow,
            index=index,
            cases=cases,
            actions=actions,
            handoffs=handoffs,
            flows_by_case=flows_by_case,
            errors=errors,
        )

    for case_id, case in cases.items():
        _validate_case_binding(
            case_id,
            case,
            flows_by_case=flows_by_case,
            final=final,
            errors=errors,
        )
    return errors
