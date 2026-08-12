#!/usr/bin/env python3
"""Apply, validate, resume, and summarize plan-ordered recette event results."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from acceptance_contract import STATUS_PRIORITY, status_of
from event_feedback import event_feedback, feedback_for_event
from execution_contract import validate_session
from init_coverage_ledger import initialize_requirement
from recette_schema import validate
from state_io import atomic_write_json, load_json_object


def load_object(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def save_atomic(path: Path, value: dict[str, Any]) -> None:
    atomic_write_json(path, value)


def rows(value: Any, field: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{field} must be an array of objects.")
    return value


def event_requirements(data: dict[str, Any], event_group_id: str) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows(data.get("requirements"), "requirements")
        if str(row.get("event_group_id")) == event_group_id
    ]
    if not selected:
        raise ValueError(f"Unknown event_group_id: {event_group_id}")
    return selected


def _row_applies(
    row: dict[str, Any],
    event_group_id: str,
    requirement_ids: set[str],
) -> bool:
    if str(row.get("event_group_id", "")) == event_group_id:
        return True
    if str(row.get("requirement_id", "")) in requirement_ids:
        return True
    for field in ("affected_requirement_ids", "requirement_ids"):
        affected = row.get(field)
        if isinstance(affected, list) and requirement_ids & {str(item) for item in affected}:
            return True
    return False


def _blocker_applies(
    row: dict[str, Any],
    event_group_id: str,
    requirement_ids: set[str],
) -> bool:
    has_explicit_scope = any(
        row.get(field) not in (None, "", [])
        for field in (
            "event_group_id",
            "requirement_id",
            "affected_requirement_ids",
            "requirement_ids",
        )
    )
    return not has_explicit_scope or _row_applies(row, event_group_id, requirement_ids)


def _referenced_evidence_ids(value: Any) -> set[str]:
    """Collect evidence references without retaining unrelated run evidence rows."""
    references: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized.endswith("evidence_id") and isinstance(item, str) and item.strip():
                references.add(item.strip())
            elif normalized.endswith("evidence_ids") and isinstance(item, list):
                references.update(str(row).strip() for row in item if str(row).strip())
            elif key != "evidence":
                references.update(_referenced_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            references.update(_referenced_evidence_ids(item))
    return references


def event_view(data: dict[str, Any], event_group_id: str) -> dict[str, Any]:
    view = deepcopy(data)
    selected = event_requirements(view, event_group_id)
    requirement_ids = {str(row.get("requirement_id")) for row in selected}
    view["requirements"] = selected
    run = view.get("run")
    if not isinstance(run, dict):
        raise ValueError("run must be an object.")
    run["requirement_inventory"] = [
        item for item in run.get("requirement_inventory", []) if str(item) in requirement_ids
    ]
    run["event_inventory"] = [
        row
        for row in rows(run.get("event_inventory"), "run.event_inventory")
        if str(row.get("event_group_id")) == event_group_id
    ]
    view["unexpected"] = [
        row
        for row in rows(view.get("unexpected"), "unexpected")
        if _row_applies(row, event_group_id, requirement_ids)
    ]
    view["blockers"] = [
        row
        for row in rows(view.get("blockers"), "blockers")
        if _blocker_applies(row, event_group_id, requirement_ids)
    ]
    referenced_evidence = _referenced_evidence_ids(view)
    view["evidence"] = [
        row
        for row in rows(view.get("evidence"), "evidence")
        if str(row.get("evidence_id", "")).strip() in referenced_evidence
    ]
    return view


def _status(requirements: list[dict[str, Any]]) -> str:
    if any(row.get("journey", {}).get("execution_status") == "PENDING" for row in requirements):
        return "PENDING"
    statuses = [
        str(row.get("verdict", {}).get("overall"))
        for row in requirements
        if str(row.get("verdict", {}).get("overall")) in STATUS_PRIORITY
    ]
    if not statuses:
        return "PENDING"
    return min(statuses, key=STATUS_PRIORITY.index)


def _session_event_view(
    session: dict[str, Any],
    event_group_id: str,
) -> dict[str, Any]:
    view = deepcopy(session)
    cases = [
        row
        for row in session.get("cases", [])
        if isinstance(row, dict) and str(row.get("event_group_id")) == event_group_id
    ]
    case_ids = {str(row.get("case_id")) for row in cases}
    actions = [
        row
        for row in session.get("actions", [])
        if isinstance(row, dict) and str(row.get("case_id")) in case_ids
    ]
    action_ids = {str(row.get("action_id")) for row in actions}
    view["cases"] = cases
    view["actions"] = actions
    view["business_pushes"] = [
        row
        for row in session.get("business_pushes", [])
        if isinstance(row, dict) and str(row.get("action_id")) in action_ids
    ]
    view["runtime_checks"] = [
        row
        for row in session.get("runtime_checks", [])
        if isinstance(row, dict) and str(row.get("action_id")) in action_ids
    ]
    view["event_closures"] = [
        row
        for row in session.get("event_closures", [])
        if isinstance(row, dict) and str(row.get("event_group_id")) == event_group_id
    ]
    view["closure_history"] = []
    for history in session.get("closure_history", []):
        if (
            not isinstance(history, dict)
            or str(history.get("reopened_event_group_id", "")) != event_group_id
        ):
            continue
        selected_history = deepcopy(history)
        selected_history["invalidated_closures"] = [
            row
            for row in history.get("invalidated_closures", [])
            if isinstance(row, dict) and str(row.get("event_group_id", "")) == event_group_id
        ]
        view["closure_history"].append(selected_history)
    return view


def validate_event(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    view = event_view(data, event_group_id)
    errors = validate(view, strict=True)
    if errors:
        raise ValueError("\n".join(errors))
    if session is not None:
        session_view = _session_event_view(session, event_group_id)
        session_evidence_ids = _referenced_evidence_ids(session_view)
        visible_evidence_ids = {
            str(row.get("evidence_id", "")).strip() for row in view.get("evidence", [])
        }
        view["evidence"].extend(
            deepcopy(row)
            for row in rows(data.get("evidence"), "evidence")
            if str(row.get("evidence_id", "")).strip() in session_evidence_ids
            and str(row.get("evidence_id", "")).strip() not in visible_evidence_ids
        )
        execution_errors = validate_session(
            session_view,
            results=view,
            final=True,
        )
        if execution_errors:
            raise ValueError("\n".join(execution_errors))
    selected = event_requirements(view, event_group_id)
    event_name = next(
        (
            row.get("event_name")
            for row in view["run"].get("event_inventory", [])
            if row.get("event_group_id") == event_group_id
        ),
        selected[0].get("expectation", {}).get("event_name"),
    )
    output = {
        "event_group_id": event_group_id,
        "event_name": event_name,
        "status": _status(selected),
        "requirement_count": len(selected),
        "validated": True,
    }
    if session is not None:
        output["feedback"] = feedback_for_event(view, event_group_id, session)
        output["status"] = output["feedback"]["status"]
    return output


def _merge_event_rows(
    current: list[dict[str, Any]],
    patch: list[dict[str, Any]],
    event_group_id: str,
    requirement_ids: set[str],
) -> list[dict[str, Any]]:
    return [
        row for row in current if not _row_applies(row, event_group_id, requirement_ids)
    ] + deepcopy(patch)


def apply_event(
    data: dict[str, Any],
    patch: dict[str, Any],
    *,
    validate_result: bool = True,
) -> tuple[dict[str, Any], str]:
    event_group_id = str(patch.get("event_group_id", "")).strip()
    if not event_group_id:
        raise ValueError("Event patch requires event_group_id.")
    current_rows = event_requirements(data, event_group_id)
    current_ids = {str(row.get("requirement_id")) for row in current_rows}
    patch_rows = rows(patch.get("requirements"), "patch.requirements")
    patch_ids = {str(row.get("requirement_id")) for row in patch_rows}
    if patch_ids != current_ids or len(patch_rows) != len(current_rows):
        raise ValueError("Event patch requirement IDs must exactly match the ledger event group.")
    if any(str(row.get("event_group_id")) != event_group_id for row in patch_rows):
        raise ValueError("Every patched requirement must use the patch event_group_id.")

    updated = deepcopy(data)
    replacements = {str(row["requirement_id"]): deepcopy(row) for row in patch_rows}
    updated["requirements"] = [
        replacements.get(str(row.get("requirement_id")), row)
        for row in rows(updated.get("requirements"), "requirements")
    ]

    patch_evidence = rows(patch.get("evidence"), "patch.evidence")
    patch_evidence_ids = [str(row.get("evidence_id", "")).strip() for row in patch_evidence]
    if any(not item for item in patch_evidence_ids):
        raise ValueError("Every patch evidence row requires evidence_id.")
    if len(patch_evidence_ids) != len(set(patch_evidence_ids)):
        raise ValueError("Event patch contains duplicate evidence IDs.")
    current_evidence = rows(updated.get("evidence"), "evidence")
    existing_ids = {
        str(row.get("evidence_id", "")).strip()
        for row in current_evidence
        if str(row.get("evidence_id", "")).strip()
    }
    conflicts = sorted(existing_ids & set(patch_evidence_ids))
    if conflicts:
        raise ValueError("Event patch evidence IDs already exist: " + ", ".join(conflicts))
    updated["evidence"] = current_evidence + deepcopy(patch_evidence)

    for collection in ("unexpected", "blockers"):
        if collection in patch:
            updated[collection] = _merge_event_rows(
                rows(updated.get(collection), collection),
                rows(patch.get(collection), f"patch.{collection}"),
                event_group_id,
                current_ids,
            )

    if validate_result:
        validate_event(updated, event_group_id)
    return updated, event_group_id


def status_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    run = data.get("run")
    if not isinstance(run, dict):
        raise ValueError("run must be an object.")
    output = []
    for inventory in rows(run.get("event_inventory"), "run.event_inventory"):
        event_group_id = str(inventory.get("event_group_id"))
        selected = event_requirements(data, event_group_id)
        output.append(
            {
                "plan_order": inventory.get("plan_order"),
                "event_group_id": event_group_id,
                "event_name": inventory.get("event_name"),
                "status": _status(selected),
                "requirements": len(selected),
            }
        )
    return output


def scaffold_event_patch(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a PENDING event patch with discovery context but no inherited proof."""
    selected = event_requirements(data, event_group_id)
    reset_requirements: list[dict[str, Any]] = []
    for row in selected:
        reset = initialize_requirement(deepcopy(row))
        reset.pop("blocker_id", None)
        scenario = reset.get("scenario")
        if isinstance(scenario, dict):
            scenario.pop("evidence_id", None)
            scenario.pop("condition_met", None)
        reset["notes"] = "Pending fresh capture; prior verdict and evidence were not inherited."
        reset_requirements.append(reset)
    session_view = _session_event_view(session, event_group_id) if session is not None else None
    return {
        "event_group_id": event_group_id,
        "requirements": reset_requirements,
        "evidence": [],
        "unexpected": [],
        "blockers": [],
        "capture_context": {
            "supporting_only": True,
            "verdicts_inherited": False,
            "evidence_inherited": False,
            "prior_cases": (session_view or {}).get("cases", []),
            "prior_actions": (session_view or {}).get("actions", []),
            "prior_business_pushes": (session_view or {}).get("business_pushes", []),
            "instruction": (
                "Use this context to locate the interaction. Replace it with new direct "
                "evidence from the current action window before applying the patch."
            ),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_event_parser = subparsers.add_parser("validate-event")
    validate_event_parser.add_argument("ledger", type=Path)
    validate_event_parser.add_argument("--event-group-id", required=True)
    validate_event_parser.add_argument("--session-ledger", type=Path)

    apply_parser = subparsers.add_parser("apply-event")
    apply_parser.add_argument("ledger", type=Path)
    apply_parser.add_argument("event_patch", type=Path)
    apply_parser.add_argument("--output", type=Path)
    apply_parser.add_argument("--session-ledger", type=Path)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("ledger", type=Path)
    status_parser.add_argument("--session-ledger", type=Path)

    scaffold_parser = subparsers.add_parser("scaffold-event")
    scaffold_parser.add_argument("ledger", type=Path)
    scaffold_parser.add_argument("--event-group-id", required=True)
    scaffold_parser.add_argument("--session-ledger", type=Path)
    scaffold_parser.add_argument("--output", type=Path, required=True)

    final_parser = subparsers.add_parser("final-validate")
    final_parser.add_argument("ledger", type=Path)
    final_parser.add_argument("--session-ledger", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_object(args.ledger)
        session = (
            load_object(args.session_ledger) if getattr(args, "session_ledger", None) else None
        )
        if args.command == "validate-event":
            output = validate_event(data, args.event_group_id, session)
        elif args.command == "apply-event":
            patch = load_object(args.event_patch)
            updated, event_group_id = apply_event(data, patch, validate_result=False)
            destination = args.output or args.ledger
            output = validate_event(updated, event_group_id, session)
            save_atomic(destination, updated)
            output["output"] = str(destination.resolve())
        elif args.command == "status":
            output = {
                "events": (
                    event_feedback(data, session) if session is not None else status_rows(data)
                )
            }
        elif args.command == "scaffold-event":
            patch = scaffold_event_patch(data, args.event_group_id, session)
            save_atomic(args.output, patch)
            output = {
                "event_group_id": args.event_group_id,
                "requirements": len(patch["requirements"]),
                "verdicts_inherited": False,
                "evidence_inherited": False,
                "output": str(args.output.resolve()),
            }
        else:
            errors = validate(data, strict=True)
            if errors:
                raise ValueError("\n".join(errors))
            execution_errors = validate_session(session or {}, results=data, final=True)
            if execution_errors:
                raise ValueError("\n".join(execution_errors))
            feedback = event_feedback(data, session)
            output = {
                "validated": True,
                "event_count": len(feedback),
                "validation_status": "PASS",
                "overall_status": min(
                    (
                        [row["status"] for row in feedback]
                        + [
                            status_of(row)
                            for row in rows(data.get("unexpected"), "unexpected")
                            if status_of(row) in STATUS_PRIORITY
                        ]
                    ),
                    key=STATUS_PRIORITY.index,
                ),
                "events": feedback,
            }
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
