#!/usr/bin/env python3
"""Create plan-ordered recette requirements from a GA4 tracking-plan delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from path_safety import ensure_distinct_output
from state_io import atomic_write_json


class HandoffError(ValueError):
    """Raised when the upstream delivery is invalid or not review-ready."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise HandoffError(f"Cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise HandoffError(f"Expected a JSON object: {path}")
    return value


def _safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise HandoffError(f"Artifact path escapes the delivery: {relative}") from error
    return path


def verify_delivery(
    delivery: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = delivery.resolve()
    handoff = _load(root / "handoff.json")
    if (
        handoff.get("handoff_version") != "1.0.0"
        or handoff.get("skill", {}).get("name") != "ga4-tracking-plan"
    ):
        raise HandoffError("Unsupported or non-GA4 tracking-plan handoff.")
    if handoff.get("approval", {}).get("state") not in {"reviewed", "approved"}:
        raise HandoffError("Recette requires a reviewed or approved tracking-plan handoff.")
    by_role: dict[str, Path] = {}
    for artifact in handoff.get("artifacts", []):
        if not isinstance(artifact, dict):
            raise HandoffError("Invalid artifact inventory row.")
        path = _safe_path(root, str(artifact.get("path", "")))
        if not path.is_file() or _digest(path) != artifact.get("sha256"):
            raise HandoffError(f"Missing or hash-mismatched artifact: {path.name}")
        by_role[str(artifact.get("role", ""))] = path
    plan_path = by_role.get("canonical_tracking_plan")
    expected_path = by_role.get("runtime_expected_events_contract")
    if plan_path is None or expected_path is None:
        raise HandoffError(
            "The delivery must include canonical plan and expected-events contracts."
        )
    if _digest(plan_path) != handoff.get("plan", {}).get("canonical_sha256"):
        raise HandoffError("Canonical plan hash mismatch.")
    return handoff, _load(plan_path), _load(expected_path)


def _path_value(root: Any, path: str) -> Any:
    current = root
    for raw_part in path.split("."):
        part = raw_part.removesuffix("[]")
        if isinstance(current, list):
            current = current[0] if current else None
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, list) and path.endswith("[]"):
        return current
    return current


def _expectation(
    event_name: str,
    field_path: str,
    value_type: str,
    expected_value: Any,
    allowed_values: list[Any] | None,
) -> dict[str, Any]:
    if allowed_values:
        match_rule = "one_of"
        value = allowed_values
    elif expected_value is not None:
        match_rule = "equals"
        value = expected_value
    else:
        match_rule = "present"
        value = None
    return {
        "event_name": event_name,
        "field_path": field_path,
        "match_rule": match_rule,
        "expected_value": value,
        "expected_type": value_type,
        "expected_occurrence": "once_per_qualifying_action",
        "source_mechanism": "data_layer_push",
    }


def interpreted_requirements(
    handoff: dict[str, Any], plan: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    expected_by_name = {
        str(item.get("event_name")): item
        for item in expected.get("events", [])
        if isinstance(item, dict)
    }
    requirements: list[dict[str, Any]] = []
    plan_order = 0
    for event_index, event in enumerate(plan.get("events", []), start=1):
        if not isinstance(event, dict):
            continue
        event_name = str(event.get("event_name", ""))
        runtime = expected_by_name.get(event_name)
        if runtime is None:
            raise HandoffError(f"Expected-events contract omits '{event_name}'.")
        group_id = f"GA4-EVG-{event_index:03d}-{event_name}"
        location = next(
            (item for item in event.get("locations", []) if isinstance(item, dict)),
            {},
        )
        journey_id = str((event.get("journey_ids") or ["unassigned"])[0])
        plan_order += 1
        requirements.append(
            {
                "requirement_id": f"{group_id}::event",
                "event_group_id": group_id,
                "source": {
                    "reference": f"plan.json / events[{event_index - 1}] / event_name",
                    "file": "plan.json",
                    "section": event_name,
                    "plan_order": plan_order,
                    "canonical_sha256": handoff.get("plan", {}).get("canonical_sha256"),
                },
                "journey": {
                    "journey_id": journey_id,
                    "step_id": f"{journey_id}::{event_name}",
                    "action": event.get("trigger"),
                    "url": location.get("url_pattern")
                    or handoff.get("plan", {}).get("target_sites", [""])[0],
                    "selector_or_element": location.get("component", ""),
                    "inferred": False,
                    "inference_source": "canonical tracking-plan delivery",
                    "confidence": "confirmed",
                    "attempted_routes": [],
                },
                "expectation": _expectation(event_name, "event", "string", event_name, None),
            }
        )
        push = event.get("data_layer", {}).get("push", {})
        for parameter_index, parameter in enumerate(event.get("parameters", []), start=1):
            if not isinstance(parameter, dict):
                continue
            plan_order += 1
            path = str(parameter.get("data_layer_path", ""))
            expected_value = _path_value(push, path)
            requirements.append(
                {
                    "requirement_id": (
                        f"{group_id}::{parameter_index:03d}::"
                        f"{parameter.get('scope')}::{parameter.get('name')}"
                    ),
                    "event_group_id": group_id,
                    "source": {
                        "reference": (
                            f"plan.json / events[{event_index - 1}] / "
                            f"parameters[{parameter_index - 1}]"
                        ),
                        "file": "plan.json",
                        "section": event_name,
                        "plan_order": plan_order,
                        "canonical_sha256": handoff.get("plan", {}).get("canonical_sha256"),
                    },
                    "journey": {
                        "journey_id": journey_id,
                        "step_id": f"{journey_id}::{event_name}",
                        "action": event.get("trigger"),
                        "url": location.get("url_pattern")
                        or handoff.get("plan", {}).get("target_sites", [""])[0],
                        "selector_or_element": location.get("component", ""),
                        "inferred": False,
                        "inference_source": "canonical tracking-plan delivery",
                        "confidence": "confirmed",
                        "attempted_routes": [],
                    },
                    "expectation": {
                        **_expectation(
                            event_name,
                            path,
                            str(parameter.get("type", "string")),
                            expected_value,
                            parameter.get("allowed_values"),
                        ),
                        "requirement": parameter.get("requirement"),
                        **(
                            {"condition": parameter.get("condition")}
                            if parameter.get("condition")
                            else {}
                        ),
                        "destination": parameter.get("destination"),
                        "parameter_scope": parameter.get("scope"),
                    },
                }
            )
    if set(expected_by_name) != {
        str(event.get("event_name")) for event in plan.get("events", []) if isinstance(event, dict)
    }:
        raise HandoffError("Plan and expected-events event inventories differ.")
    return {
        "source_contract": "ga4-tracking-plan-delivery@1.0.0",
        "source_plan_sha256": handoff.get("plan", {}).get("canonical_sha256"),
        "source_approval": handoff.get("approval"),
        "requirements": requirements,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True)
    args = parser.parse_args()
    try:
        handoff, plan, expected = verify_delivery(args.delivery)
        result = interpreted_requirements(handoff, plan, expected)
        ensure_distinct_output(args.output, args.delivery)
        atomic_write_json(args.output, result)
    except HandoffError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
