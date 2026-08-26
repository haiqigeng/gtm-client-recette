#!/usr/bin/env python3
"""Validate and execute the sole native Playwright action contract."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

ACTIONS = {"navigate", "click", "fill", "select", "press", "submit"}
LOCATOR_FIELDS = {"role", "name", "exact"}
DECISION_FIELDS = {
    "event_id",
    "scenario_id",
    "operation",
    "semantic_locator",
    "value",
    "reason",
    "evidence_refs",
}
SCENARIO_FIELDS = {
    "event_id",
    "scenario_id",
    "target_url",
    "target_source",
    "setup_actions",
    "measured_action",
    "reason",
    "evidence_refs",
}
TARGET_SOURCES = {"PLAN", "LIVE"}
SNAPSHOT_NODE = re.compile(
    r"^\s*-\s+(?P<role>[A-Za-z][A-Za-z0-9_-]*)"
    r'(?:\s+"(?P<quoted>(?:[^"\\]|\\.)*)")?'
    r"\s+\[ref=(?P<ref>[^\]]+)\]",
    re.MULTILINE,
)


class ActionError(ValueError):
    """Raised when an adaptive action decision violates the fixed contract."""


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ActionError(f"{field} must be a non-empty string.")
    return value.strip()


def validate_decision(decision: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized decision or reject it before browser execution."""
    if not isinstance(decision, dict):
        raise ActionError("InteractionDecision must be an object.")
    unknown = sorted(set(decision) - DECISION_FIELDS)
    missing = sorted(DECISION_FIELDS - set(decision))
    if unknown or missing:
        raise ActionError(
            f"InteractionDecision fields invalid; missing={missing}, unknown={unknown}."
        )
    event_id = _text(decision["event_id"], "event_id")
    if event_id != event.get("event_id"):
        raise ActionError("InteractionDecision changed event identity.")
    scenario_id = _text(decision["scenario_id"], "scenario_id")
    if scenario_id != event.get("event_name"):
        raise ActionError("scenario_id must equal the canonical event_name.")
    operation = decision["operation"]
    if operation not in ACTIONS:
        raise ActionError(f"Unsupported operation {operation!r}.")
    reason = _text(decision["reason"], "reason")
    evidence_refs = decision["evidence_refs"]
    if (
        not isinstance(evidence_refs, list)
        or not evidence_refs
        or not all(isinstance(item, str) and item for item in evidence_refs)
    ):
        raise ActionError("evidence_refs must be a non-empty string list.")

    locator = decision["semantic_locator"]
    value = decision["value"]
    if operation == "navigate":
        if locator is not None or value is not None:
            raise ActionError("navigate requires null semantic_locator and value.")
        normalized_locator = None
    else:
        if not isinstance(locator, dict) or set(locator) != LOCATOR_FIELDS:
            raise ActionError("semantic_locator must contain exactly role, name, and exact.")
        role = _text(locator["role"], "semantic_locator.role")
        name = _text(locator["name"], "semantic_locator.name")
        if locator["exact"] is not True:
            raise ActionError("semantic_locator.exact must be true.")
        normalized_locator = {"role": role, "name": name, "exact": True}
        if operation in {"fill", "select", "press"}:
            value = _text(value, "value")
        elif value is not None:
            raise ActionError(f"{operation} requires null value.")
    return {
        "event_id": event_id,
        "scenario_id": scenario_id,
        "operation": operation,
        "semantic_locator": normalized_locator,
        "value": value,
        "reason": reason,
        "evidence_refs": list(dict.fromkeys(evidence_refs)),
    }


def _origin(url: str, field: str) -> tuple[str, str, int | None]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ActionError(f"{field} must be one exact HTTP(S) URL.")
    return parsed.scheme.casefold(), parsed.hostname.casefold(), parsed.port


def validate_scenario_decision(
    decision: dict[str, Any], event: dict[str, Any], prepared_url: str
) -> dict[str, Any]:
    """Validate one adaptive target, fixed setup sequence, and measured action."""
    if not isinstance(decision, dict) or set(decision) != SCENARIO_FIELDS:
        actual = set(decision) if isinstance(decision, dict) else set()
        raise ActionError(
            f"ScenarioDecision fields invalid; missing={sorted(SCENARIO_FIELDS - actual)}, "
            f"unknown={sorted(actual - SCENARIO_FIELDS)}."
        )
    if decision["event_id"] != event.get("event_id"):
        raise ActionError("ScenarioDecision changed event identity.")
    if decision["scenario_id"] != event.get("event_name"):
        raise ActionError("scenario_id must equal the canonical event_name.")
    target_url = _text(decision["target_url"], "target_url")
    target_origin = _origin(target_url, "target_url")
    source = decision["target_source"]
    if source not in TARGET_SOURCES:
        raise ActionError("target_source must be PLAN or LIVE.")
    planned_url = event.get("entry_url")
    if planned_url:
        if source != "PLAN" or target_url != planned_url:
            raise ActionError("A supplied plan URL must be used exactly as the target.")
    else:
        if source != "LIVE":
            raise ActionError("A missing plan URL requires LIVE target resolution.")
        if target_origin != _origin(_text(prepared_url, "prepared_url"), "prepared_url"):
            raise ActionError("A live-resolved target must stay on the prepared site origin.")
    setup = decision["setup_actions"]
    if not isinstance(setup, list):
        raise ActionError("setup_actions must be a finite JSON list.")
    accepted_setup = [validate_decision(action, event) for action in setup]
    if any(action["operation"] == "navigate" for action in accepted_setup):
        raise ActionError("setup_actions cannot contain navigation; target_url owns navigation.")
    measured = validate_decision(decision["measured_action"], event)
    if measured["operation"] == "navigate" and accepted_setup:
        raise ActionError("A measured navigation cannot follow setup actions.")
    refs = decision["evidence_refs"]
    if (
        not isinstance(refs, list)
        or not refs
        or not all(isinstance(ref, str) and ref for ref in refs)
    ):
        raise ActionError("ScenarioDecision evidence_refs must be a non-empty string list.")
    return {
        "event_id": event["event_id"],
        "scenario_id": event["event_name"],
        "target_url": target_url,
        "target_source": source,
        "setup_actions": accepted_setup,
        "measured_action": measured,
        "reason": _text(decision["reason"], "reason"),
        "evidence_refs": list(dict.fromkeys(refs)),
    }


def _snapshot_nodes(snapshot_text: str) -> list[dict[str, str]]:
    if not isinstance(snapshot_text, str) or not snapshot_text.strip():
        raise ActionError("A non-empty MCP accessibility snapshot is required.")
    nodes = []
    for match in SNAPSHOT_NODE.finditer(snapshot_text):
        quoted = match.group("quoted")
        name = json.loads(f'"{quoted}"') if quoted is not None else ""
        nodes.append(
            {
                "role": match.group("role").casefold(),
                "name": name,
                "ref": match.group("ref"),
            }
        )
    return nodes


def resolve_snapshot_ref(snapshot_text: str, semantic_locator: dict[str, Any]) -> str:
    """Resolve one exact role/name locator from one native MCP snapshot."""
    if not isinstance(semantic_locator, dict) or set(semantic_locator) != LOCATOR_FIELDS:
        raise ActionError("semantic_locator must contain exactly role, name, and exact.")
    if semantic_locator.get("exact") is not True:
        raise ActionError("semantic_locator.exact must be true.")
    role = _text(semantic_locator.get("role"), "semantic_locator.role").casefold()
    name = _text(semantic_locator.get("name"), "semantic_locator.name")
    matches = [
        node
        for node in _snapshot_nodes(snapshot_text)
        if node["role"] == role and node["name"] == name
    ]
    if len(matches) != 1:
        raise ActionError(
            f"Exact MCP locator must resolve once; role={role!r}, name={name!r}, "
            f"matches={len(matches)}."
        )
    return matches[0]["ref"]


def compile_mcp_action(
    event: dict[str, Any],
    decision: dict[str, Any],
    *,
    snapshot_text: str | None = None,
    target_url: str | None = None,
) -> dict[str, Any]:
    """Compile one validated interaction into the sole MCP tool-call sequence."""
    accepted = validate_decision(decision, event)
    operation = accepted["operation"]
    if operation == "navigate":
        destination = target_url or event.get("entry_url")
        if not destination:
            raise ActionError("navigate requires a resolved target URL.")
        _origin(destination, "target_url")
        calls = [
            {
                "tool": "mcp__playwright__browser_navigate",
                "arguments": {"url": destination},
            }
        ]
    else:
        target = resolve_snapshot_ref(snapshot_text or "", accepted["semantic_locator"])
        label = accepted["semantic_locator"]["name"]
        if operation in {"click", "submit"}:
            calls = [
                {
                    "tool": "mcp__playwright__browser_click",
                    "arguments": {"target": target, "element": label},
                }
            ]
        elif operation == "fill":
            if accepted["semantic_locator"]["role"].casefold() != "textbox":
                raise ActionError("fill requires one exact textbox locator.")
            calls = [
                {
                    "tool": "mcp__playwright__browser_fill_form",
                    "arguments": {
                        "fields": [
                            {
                                "name": label,
                                "type": "textbox",
                                "target": target,
                                "value": accepted["value"],
                            }
                        ]
                    },
                }
            ]
        elif operation == "select":
            if accepted["semantic_locator"]["role"].casefold() != "combobox":
                raise ActionError("select requires one exact combobox locator.")
            calls = [
                {
                    "tool": "mcp__playwright__browser_select_option",
                    "arguments": {
                        "target": target,
                        "element": label,
                        "values": [accepted["value"]],
                    },
                }
            ]
        else:
            calls = [
                {
                    "tool": "mcp__playwright__browser_click",
                    "arguments": {"target": target, "element": label},
                },
                {
                    "tool": "mcp__playwright__browser_press_key",
                    "arguments": {"key": accepted["value"]},
                },
            ]
    return {
        "contract": "playwright-mcp-action-v1",
        "event_id": accepted["event_id"],
        "scenario_id": accepted["scenario_id"],
        "operation": operation,
        "calls": calls,
    }
