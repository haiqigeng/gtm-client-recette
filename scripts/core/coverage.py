"""Just-in-time material-scenario coverage without future-event registration."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .constants import MATERIALITY_DEFINITION
from .correlate import action_windows
from .state import StateError, stream_record_by_id

COVERAGE_MODES = {"EXHAUSTIVE", "PARTITIONED", "SAMPLED", "SINGLETON", "BLOCKED"}
DIMENSION_KINDS = {
    "manageable_finite",
    "high_cardinality",
    "conditional",
    "dependent",
    "unknown",
    "unreachable",
}
SAMPLE_ROLES = {"ORDINARY", "CONTRAST", "BOUNDARY", "EXCEPTION", "NEGATIVE"}


def event_by_id(plan: dict[str, Any], event_id: str) -> dict[str, Any]:
    for event in plan.get("events", []):
        if str(event.get("event_id")) == str(event_id):
            return event
    raise StateError(f"Unknown event_id: {event_id}")


def coverage_reviews(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("kind") != "COVERAGE_REVIEW":
            continue
        event_id = str(record.get("data", {}).get("event_id") or "")
        if event_id:
            latest[event_id] = record
    return latest


def _validate_scenarios(
    event_id: str,
    scenarios: list[Any],
    mode: str,
    records: list[dict[str, Any]],
) -> tuple[list[str], set[str], dict[str, set[str]], set[str]]:
    errors: list[str] = []
    record_ids = stream_record_by_id(records)
    actions = {action["action_id"]: action for action in action_windows(records)}
    seen: set[str] = set()
    values_by_dimension: dict[str, set[str]] = defaultdict(set)
    roles: set[str] = set()
    covered_actions: set[str] = set()
    if not scenarios:
        errors.append("Coverage needs at least one executed scenario.")
    for index, scenario in enumerate(scenarios, start=1):
        if not isinstance(scenario, dict):
            errors.append(f"Scenario {index} is not an object.")
            continue
        scenario_id = str(scenario.get("scenario_id") or "")
        label = scenario_id or index
        if not scenario_id or scenario_id in seen:
            errors.append(f"Scenario {index} needs a unique scenario_id.")
        seen.add(scenario_id)
        role = str(scenario.get("role") or "ORDINARY").upper()
        if role not in SAMPLE_ROLES:
            errors.append(f"Scenario {label} has an invalid sample role.")
        roles.add(role)
        values = scenario.get("values", {})
        if not isinstance(values, dict):
            errors.append(f"Scenario {label} values must be an object.")
            values = {}
        for name, value in values.items():
            values_by_dimension[str(name)].add(_value_key(value))
        action_ids = scenario.get("action_ids", [])
        if not isinstance(action_ids, list) or not action_ids:
            errors.append(f"Scenario {label} has no executed action.")
        for action_id in action_ids if isinstance(action_ids, list) else []:
            covered_actions.add(str(action_id))
            action = actions.get(str(action_id))
            if action is None:
                errors.append(f"Scenario {label} references unknown action {action_id}.")
            elif action.get("status") == "SUPERSEDED":
                errors.append(f"Scenario {label} references superseded action {action_id}.")
            elif event_id not in {str(value) for value in action.get("event_ids", [])}:
                errors.append(f"Action {action_id} is not bound to event {event_id}.")
        for reference in scenario.get("evidence_refs", []):
            if str(reference) not in record_ids:
                errors.append(f"Scenario {label} has unknown evidence ref {reference}.")
        if (
            mode == "SAMPLED"
            and role in {"ORDINARY", "CONTRAST", "BOUNDARY", "EXCEPTION"}
            and not str(scenario.get("behavior_signature") or "").strip()
        ):
            errors.append(f"Sampled scenario {label} needs an explainable behavior signature.")
    committed_for_event = {
        action_id
        for action_id, action in actions.items()
        if action.get("status") == "COMMITTED"
        and event_id in {str(value) for value in action.get("event_ids", [])}
    }
    unreviewed = sorted(committed_for_event - covered_actions)
    if unreviewed:
        errors.append(
            "Executed event actions are absent from scenario coverage: " + ", ".join(unreviewed)
        )
    return errors, seen, values_by_dimension, roles


def _live_value_errors(
    name: str, values: list[Any], record_ids: dict[str, dict[str, Any]]
) -> tuple[list[str], list[Any]]:
    errors: list[str] = []
    reachable: list[Any] = []
    for value in values:
        row = value if isinstance(value, dict) else {"value": value}
        if row.get("reachable", True) is not False:
            reachable.append(row.get("value"))
        source = str(row.get("source") or "")
        if source in {"", "plan", "user"}:
            continue
        if not row.get("evidence_ref"):
            errors.append(
                f"Live/config/runtime value {name}={row.get('value')} needs a capture evidence ref."
            )
        elif str(row["evidence_ref"]) not in record_ids:
            errors.append(f"Dimension {name} has unknown evidence ref {row['evidence_ref']}.")
    return errors, reachable


def _validate_dimensions(
    dimensions: list[Any],
    scenarios: list[Any],
    scenario_values: dict[str, set[str]],
    roles: set[str],
    records: list[dict[str, Any]],
) -> tuple[list[str], bool, bool, bool]:
    errors: list[str] = []
    record_ids = stream_record_by_id(records)
    high_cardinality = False
    blocked_dimension = False
    singleton_possible = True
    for index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            errors.append(f"Dimension {index} is not an object.")
            continue
        name = str(dimension.get("name") or "")
        kind = str(dimension.get("kind") or "")
        if not name or kind not in DIMENSION_KINDS:
            errors.append(f"Dimension {index} needs a name and recognized kind.")
            continue
        if dimension.get("material") is False:
            continue
        values = dimension.get("values", [])
        if not isinstance(values, list):
            errors.append(f"Dimension {name} values must be an array.")
            continue
        live_errors, reachable = _live_value_errors(name, values, record_ids)
        errors.extend(live_errors)
        if len({_value_key(value) for value in reachable}) > 1:
            singleton_possible = False
        if kind == "manageable_finite":
            missing = [
                value for value in reachable if _value_key(value) not in scenario_values[name]
            ]
            if missing:
                errors.append(
                    f"Manageable finite dimension {name} has untested values: "
                    + ", ".join(map(str, missing))
                )
        elif kind == "high_cardinality":
            high_cardinality = True
            if dimension.get("population_size") != 1:
                singleton_possible = False
            declared_signatures = {
                str(value)
                for value in dimension.get("behavior_signatures", [])
                if str(value).strip()
            }
            observed_signatures = {
                str(scenario.get("behavior_signature"))
                for scenario in scenarios
                if isinstance(scenario, dict) and scenario.get("behavior_signature")
            }
            if len(declared_signatures | observed_signatures) > 1 and not {
                "ORDINARY",
                "CONTRAST",
            }.issubset(roles):
                errors.append(
                    f"High-cardinality dimension {name} has distinct behavior signatures and "
                    "needs ordinary and contrast representatives."
                )
            for special, role in (
                ("boundary_applicable", "BOUNDARY"),
                ("exception_applicable", "EXCEPTION"),
            ):
                if dimension.get(special) is True and role not in roles:
                    errors.append(f"Dimension {name} requires a {role.lower()} representative.")
        elif kind in {"unknown", "unreachable"}:
            blocked_dimension = True
            singleton_possible = False
        elif kind == "dependent":
            combinations = dimension.get("required_combinations", [])
            for combination in combinations if isinstance(combinations, list) else []:
                if not _combination_covered(combination, scenarios):
                    errors.append(
                        f"Dependent combination is untested for dimension {name}: {combination}"
                    )
    return errors, high_cardinality, blocked_dimension, singleton_possible


def _coverage_closure_errors(
    data: dict[str, Any],
    mode: str,
    high_cardinality: bool,
    blocked_dimension: bool,
    singleton_possible: bool,
) -> list[str]:
    errors: list[str] = []
    if mode == "EXHAUSTIVE" and (high_cardinality or blocked_dimension):
        errors.append(
            "Coverage cannot be EXHAUSTIVE with sampled, unknown, or unreachable material dimensions."
        )
    if mode == "SAMPLED" and not high_cardinality:
        errors.append("SAMPLED coverage needs a high-cardinality material class.")
    if mode == "SINGLETON" and (not singleton_possible or len(data.get("scenarios", [])) != 1):
        errors.append("SINGLETON coverage needs exactly one scenario and no known second member.")
    if blocked_dimension and mode != "BLOCKED":
        errors.append("Unknown or unreachable material dimensions require BLOCKED coverage.")
    unresolved = data.get("unresolved_material", [])
    if data.get("complete") is True and isinstance(unresolved, list) and unresolved:
        errors.append("Coverage cannot be complete with unresolved material discoveries/anomalies.")
    return errors


def _merged_dimensions(event: dict[str, Any], supplied: list[Any]) -> list[dict[str, Any]]:
    """Keep compiler-known constraints while adding live-discovered coverage evidence."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for raw in [*event.get("known_dimensions", []), *supplied]:
        if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
            continue
        name = str(raw["name"])
        raw_values = raw.get("values", []) if isinstance(raw.get("values", []), list) else []
        if name not in merged:
            merged[name] = {**raw, "values": list(raw_values)}
            order.append(name)
            continue
        prior = merged[name]
        values = []
        seen = set()
        for value in [*prior.get("values", []), *raw_values]:
            key = _value_key(value)
            if key not in seen:
                seen.add(key)
                values.append(value)
        combined = {**raw, **prior, "values": values}
        for key in ("behavior_signatures", "required_combinations"):
            rows = []
            row_keys = set()
            for item in [*prior.get(key, []), *raw.get(key, [])]:
                item_key = _value_key(item)
                if item_key not in row_keys:
                    row_keys.add(item_key)
                    rows.append(item)
            if rows:
                combined[key] = rows
        merged[name] = combined
    return [merged[name] for name in order]


def validate_coverage_annotation(
    plan: dict[str, Any],
    records: list[dict[str, Any]],
    data: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    event_id = str(data.get("event_id") or "")
    try:
        event = event_by_id(plan, event_id)
    except StateError as error:
        return [str(error)]

    mode = str(data.get("mode") or "").upper()
    if mode not in COVERAGE_MODES:
        errors.append(
            "Coverage mode must be EXHAUSTIVE, PARTITIONED, SAMPLED, SINGLETON, or BLOCKED."
        )
    if not str(data.get("rationale") or "").strip():
        errors.append("Coverage needs a concise rationale.")
    if not str(data.get("stop_reason") or "").strip():
        errors.append("Coverage needs an explicit stop reason.")

    dimensions = data.get("dimensions", [])
    scenarios = data.get("scenarios", [])
    if not isinstance(dimensions, list) or not isinstance(scenarios, list):
        return [*errors, "Coverage dimensions and scenarios must be arrays."]

    scenario_errors, seen, scenario_values, roles = _validate_scenarios(
        event_id, scenarios, mode, records
    )
    errors.extend(scenario_errors)
    explicit_ids = {
        str(scenario.get("scenario_id")) for scenario in event.get("explicit_scenarios", [])
    }
    missing_explicit = sorted(explicit_ids - seen)
    if missing_explicit:
        errors.append("Explicit plan scenarios are untested: " + ", ".join(missing_explicit))

    dimensions = _merged_dimensions(event, dimensions)
    dimension_errors, high_cardinality, blocked_dimension, singleton_possible = (
        _validate_dimensions(dimensions, scenarios, scenario_values, roles, records)
    )
    errors.extend(dimension_errors)
    errors.extend(
        _coverage_closure_errors(
            {**data, "dimensions": dimensions},
            mode,
            high_cardinality,
            blocked_dimension,
            singleton_possible,
        )
    )
    if data.get("complete") is True and errors:
        errors.append("Coverage cannot be marked complete while material gaps remain.")
    return errors


def _value_key(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _combination_covered(combination: Any, scenarios: list[Any]) -> bool:
    if not isinstance(combination, dict):
        return False
    for scenario in scenarios:
        values = scenario.get("values", {}) if isinstance(scenario, dict) else {}
        if all(
            _value_key(values.get(key)) == _value_key(value) for key, value in combination.items()
        ):
            return True
    return False


def coverage_result(
    plan: dict[str, Any],
    records: list[dict[str, Any]],
    event_id: str,
) -> dict[str, Any]:
    event_by_id(plan, event_id)
    review = coverage_reviews(records).get(event_id)
    relevant_actions = [
        action
        for action in action_windows(records)
        if action.get("status") != "SUPERSEDED"
        if event_id in {str(value) for value in action.get("event_ids", [])}
    ]
    if review is None:
        return {
            "status": "PENDING",
            "mode": None,
            "complete": False,
            "rationale": "Current-event scenario discovery has not been concluded.",
            "stop_reason": None,
            "scenarios": [],
            "dimensions": [],
            "errors": [],
            "actions_seen": len(relevant_actions),
            "plan_gaps": [],
            "materiality": MATERIALITY_DEFINITION,
        }
    data = review.get("data", {})
    errors = validate_coverage_annotation(plan, records, data)
    complete = data.get("complete") is True and not errors
    mode = str(data.get("mode") or "").upper()
    status = (
        "PASS"
        if complete and mode != "BLOCKED"
        else "BLOCKED"
        if mode == "BLOCKED" or (data.get("complete") is True and errors)
        else "PENDING"
    )
    plan_gaps = []
    dimensions = _merged_dimensions(event_by_id(plan, event_id), data.get("dimensions", []))
    for dimension in dimensions:
        if not isinstance(dimension, dict):
            continue
        for value in dimension.get("values", []):
            row = value if isinstance(value, dict) else {"value": value}
            if row.get("source") not in {None, "plan", "user"}:
                plan_gaps.append(
                    {
                        "dimension": dimension.get("name"),
                        "value": row.get("value"),
                        "source": row.get("source"),
                    }
                )
    return {
        "status": status,
        "mode": mode or None,
        "complete": complete,
        "rationale": data.get("rationale"),
        "stop_reason": data.get("stop_reason"),
        "scenarios": data.get("scenarios", []),
        "dimensions": dimensions,
        "errors": errors,
        "actions_seen": len(relevant_actions),
        "plan_gaps": plan_gaps,
        "materiality": MATERIALITY_DEFINITION,
        "record_id": review.get("record_id"),
    }
