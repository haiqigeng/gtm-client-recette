#!/usr/bin/env python3
"""Apply, validate, resume, and summarize plan-ordered recette event results."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from acceptance_contract import ACTION_BOUNDARY_FIELDS, STATUS_PRIORITY, status_of
from event_feedback import event_feedback, feedback_for_event
from evidence_integrity import build_integrity_record, integrity_errors
from execution_contract import validate_session
from init_coverage_ledger import initialize_requirement
from layer_contract import CANONICAL_LAYERS
from preview_session_ledger import build_tag_result_scaffold
from recette_schema import validate
from state_io import atomic_write_json, load_json_object, recover_file_pair
from stream_contract import stream_errors


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


def event_patch_digest(patch: dict[str, Any]) -> str:
    """Hash only the effective event mutation so retries ignore helper context."""
    payload = {
        "event_group_id": patch.get("event_group_id"),
        "requirements": patch.get("requirements", []),
        "evidence": patch.get("evidence", []),
        "unexpected": patch.get("unexpected", []),
        "blockers": patch.get("blockers", []),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _canonical_action_boundary(action: dict[str, Any]) -> dict[str, Any]:
    boundary = {field: deepcopy(action.get(field)) for field in ACTION_BOUNDARY_FIELDS}
    timestamp = boundary.get("action_timestamp")
    if isinstance(timestamp, str):
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            pass
        else:
            if parsed.tzinfo is not None:
                boundary["action_timestamp"] = parsed.astimezone(UTC).isoformat(timespec="seconds")
    return boundary


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


def _select_rows(value: Any, predicate: Any) -> list[dict[str, Any]]:
    return [row for row in value or [] if isinstance(row, dict) and predicate(row)]


def _row_ids(selected: list[dict[str, Any]], field: str) -> set[str]:
    return {str(row.get(field, "")) for row in selected if str(row.get(field, ""))}


def _event_scope_match(
    row: dict[str, Any],
    event_group_id: str,
    case_ids: set[str],
    action_ids: set[str],
) -> bool:
    return (
        str(row.get("event_group_id", "")) == event_group_id
        or str(row.get("case_id", "")) in case_ids
        or str(row.get("action_id", "")) in action_ids
    )


def _event_stream_segments(
    session: dict[str, Any], action_ids: set[str], push_ids: set[str]
) -> list[dict[str, Any]]:
    def applies(row: dict[str, Any]) -> bool:
        observed = {str(value) for value in row.get("observed_push_ids", []) if str(value)}
        return str(row.get("action_id", "")) in action_ids or bool(observed & push_ids)

    return _select_rows(session.get("stream_segments"), applies)


def _event_closure_history(session: dict[str, Any], event_group_id: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for history in session.get("closure_history", []):
        if not isinstance(history, dict) or str(history.get("reopened_event_group_id", "")) != (
            event_group_id
        ):
            continue
        selected = deepcopy(history)
        selected["invalidated_closures"] = _select_rows(
            history.get("invalidated_closures"),
            lambda row: str(row.get("event_group_id", "")) == event_group_id,
        )
        output.append(selected)
    return output


def _session_event_view(
    session: dict[str, Any],
    event_group_id: str,
) -> dict[str, Any]:
    """Project every event-bound sidecar while retaining shared runtime identity."""
    view = deepcopy(session)
    cases = _select_rows(
        session.get("cases"), lambda row: str(row.get("event_group_id")) == event_group_id
    )
    case_ids = _row_ids(cases, "case_id")
    actions = _select_rows(session.get("actions"), lambda row: str(row.get("case_id")) in case_ids)
    action_ids = _row_ids(actions, "action_id")

    def applies(row: dict[str, Any]) -> bool:
        return _event_scope_match(row, event_group_id, case_ids, action_ids)

    view["cases"] = cases
    view["actions"] = actions
    view["business_pushes"] = _select_rows(session.get("business_pushes"), applies)
    view["stream_segments"] = _event_stream_segments(
        session, action_ids, _row_ids(view["business_pushes"], "push_id")
    )
    view["runtime_checks"] = _select_rows(
        session.get("runtime_checks"), lambda row: str(row.get("action_id")) in action_ids
    )
    for field in (
        "checkpoints",
        "journey_states",
        "semantic_checks",
        "protected_handoffs",
        "gated_flows",
    ):
        view[field] = _select_rows(session.get(field), applies)
    view["coverage_decisions"] = _select_rows(
        session.get("coverage_decisions"),
        lambda row: str(row.get("event_group_id", "")) == event_group_id,
    )
    # Current-event evidence is verified separately. Keeping this PENDING avoids
    # binding event certification to the still-growing whole-run catalog.
    if session.get("operator_contract_version") == 2:
        view["evidence_integrity"] = {"version": 2, "status": "PENDING"}
    view["event_closures"] = _select_rows(
        session.get("event_closures"),
        lambda row: str(row.get("event_group_id")) == event_group_id,
    )
    view["closure_history"] = _event_closure_history(session, event_group_id)
    return view


def _event_validation_views(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    results_view = event_view(data, event_group_id)
    session_view = _session_event_view(session, event_group_id)
    evidence_scopes = {
        key: session_view.get(key)
        for key in (
            "cases",
            "actions",
            "business_pushes",
            "runtime_checks",
            "checkpoints",
            "coverage_decisions",
            "journey_states",
            "semantic_checks",
            "protected_handoffs",
            "gated_flows",
            "stream_segments",
        )
    }
    session_evidence_ids = _referenced_evidence_ids(evidence_scopes)
    visible_evidence_ids = {
        str(row.get("evidence_id", "")).strip() for row in results_view.get("evidence", [])
    }
    results_view["evidence"].extend(
        deepcopy(row)
        for row in rows(data.get("evidence"), "evidence")
        if str(row.get("evidence_id", "")).strip() in session_evidence_ids
        and str(row.get("evidence_id", "")).strip() not in visible_evidence_ids
    )
    return results_view, session_view


def build_event_integrity(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any],
    base_dir: Path,
) -> dict[str, Any]:
    """Build and live-verify the evidence catalog needed by one event only."""
    results_view, _ = _event_validation_views(data, event_group_id, session)
    record = build_integrity_record(results_view, base_dir)
    errors = integrity_errors(
        {"evidence_integrity": record},
        results=results_view,
        verify_files=True,
    )
    if errors:
        raise ValueError("\n".join(errors))
    return record


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
        global_errors = validate_session(session, results=data, final=False)
        if global_errors:
            raise ValueError("\n".join(global_errors))
        view, session_view = _event_validation_views(data, event_group_id, session)
        execution_errors = validate_session(
            session_view,
            results=view,
            certify_event=True,
        )
        if session.get("operator_contract_version") == 2:
            execution_errors.extend(stream_errors(session, final=False, certify_prefix=True))
            closure = next(
                (
                    row
                    for row in session.get("event_closures", [])
                    if isinstance(row, dict)
                    and str(row.get("event_group_id", "")) == event_group_id
                ),
                None,
            )
            if isinstance(closure, dict) and closure.get("closure_contract_version") == 2:
                integrity_ledger = {"evidence_integrity": closure.get("evidence_integrity")}
                execution_errors.extend(
                    integrity_errors(
                        integrity_ledger,
                        results=view,
                        verify_files=True,
                    )
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


def _merge_patch_evidence(
    current: list[dict[str, Any]],
    patch: list[dict[str, Any]],
    *,
    allow_identical: bool,
) -> list[dict[str, Any]]:
    patch_ids = [str(row.get("evidence_id", "")).strip() for row in patch]
    if any(not evidence_id for evidence_id in patch_ids):
        raise ValueError("Every patch evidence row requires evidence_id.")
    if len(patch_ids) != len(set(patch_ids)):
        raise ValueError("Event patch contains duplicate evidence IDs.")
    existing = {
        str(row.get("evidence_id", "")).strip(): row
        for row in current
        if str(row.get("evidence_id", "")).strip()
    }
    conflicts = sorted(
        evidence_id
        for evidence_id, patch_row in zip(patch_ids, patch, strict=True)
        if evidence_id in existing and (not allow_identical or existing[evidence_id] != patch_row)
    )
    if conflicts:
        raise ValueError("Event patch evidence IDs already exist: " + ", ".join(conflicts))
    return current + [
        deepcopy(row)
        for evidence_id, row in zip(patch_ids, patch, strict=True)
        if evidence_id not in existing
    ]


def apply_event(
    data: dict[str, Any],
    patch: dict[str, Any],
    *,
    validate_result: bool = True,
    allow_identical_evidence: bool = False,
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

    updated["evidence"] = _merge_patch_evidence(
        rows(updated.get("evidence"), "evidence"),
        rows(patch.get("evidence"), "patch.evidence"),
        allow_identical=allow_identical_evidence,
    )

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


def _pending_requirement(row: dict[str, Any]) -> dict[str, Any]:
    reset = initialize_requirement(deepcopy(row))
    reset.pop("blocker_id", None)
    scenario = reset.get("scenario")
    if isinstance(scenario, dict):
        scenario.pop("evidence_id", None)
        scenario.pop("condition_met", None)
    reset["notes"] = "Pending fresh capture; prior verdict and evidence were not inherited."
    return reset


def _action_layer_scaffold(case: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    decisions = {
        str(row.get("layer", "")): row
        for row in case.get("layer_applicability", [])
        if isinstance(row, dict)
    }
    existing_layers = _row_ids(_select_rows(action.get("layer_results"), lambda row: True), "layer")
    return {
        "case_id": case.get("case_id"),
        "action_id": action.get("action_id"),
        "layer_results": [
            {
                "layer": layer,
                "mode": decisions.get(layer, {}).get("mode"),
                "predicate": decisions.get(layer, {}).get("predicate"),
                "status": "PENDING",
                "predicate_result": None,
                "reason": "Pending current-event direct evidence review.",
                "evidence_ids": [],
                "prior_result_present": layer in existing_layers,
            }
            for layer in CANONICAL_LAYERS
        ],
    }


def _event_capture_scaffolds(
    session: dict[str, Any], session_view: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    actions_by_id = {
        str(row.get("action_id", "")): row
        for row in session_view.get("actions", [])
        if isinstance(row, dict) and str(row.get("action_id", ""))
    }
    boundaries: list[dict[str, Any]] = []
    action_scaffolds: list[dict[str, Any]] = []
    tag_scaffolds: list[dict[str, Any]] = []
    actions_by_requirement: dict[str, list[dict[str, Any]]] = {}
    for case in session_view.get("cases", []):
        if not isinstance(case, dict):
            continue
        action_id = str(case.get("final_action_id", "")).strip()
        action = actions_by_id.get(action_id)
        if not action or action.get("state") != "SETTLED":
            continue
        boundaries.append(
            {
                "case_id": case.get("case_id"),
                "action_id": action_id,
                "requirement_ids": deepcopy(action.get("requirement_ids", [])),
                "action_boundary": _canonical_action_boundary(action),
            }
        )
        for requirement_id in action.get("requirement_ids", []):
            actions_by_requirement.setdefault(str(requirement_id), []).append(action)
        action_scaffolds.append(_action_layer_scaffold(case, action))
        tag_scaffolds.append(build_tag_result_scaffold(session, action_id))
    return boundaries, action_scaffolds, tag_scaffolds, actions_by_requirement


def scaffold_event_patch(
    data: dict[str, Any],
    event_group_id: str,
    session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a PENDING event patch with discovery context but no inherited proof."""
    selected = event_requirements(data, event_group_id)
    reset_requirements = [_pending_requirement(row) for row in selected]
    session_view = _session_event_view(session, event_group_id) if session is not None else None
    action_boundaries_by_case: list[dict[str, Any]] = []
    action_layer_scaffolds: list[dict[str, Any]] = []
    tag_layer_scaffolds: list[dict[str, Any]] = []
    final_actions_by_requirement: dict[str, Any] = {}
    if session_view is not None:
        (
            action_boundaries_by_case,
            action_layer_scaffolds,
            tag_layer_scaffolds,
            final_actions_by_requirement,
        ) = _event_capture_scaffolds(session, session_view)

    for reset in reset_requirements:
        matching_actions = final_actions_by_requirement.get(str(reset.get("requirement_id")), [])
        if len(matching_actions) == 1:
            reset["action_boundary"] = _canonical_action_boundary(matching_actions[0])
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
            "action_boundaries_by_case": action_boundaries_by_case,
            "action_layer_scaffolds": action_layer_scaffolds,
            "tag_layer_scaffolds": tag_layer_scaffolds,
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
        if getattr(args, "session_ledger", None) is not None:
            recover_file_pair(args.ledger, args.session_ledger)
        data = load_object(args.ledger)
        session = (
            load_object(args.session_ledger) if getattr(args, "session_ledger", None) else None
        )
        if args.command == "validate-event":
            output = validate_event(data, args.event_group_id, session)
        elif args.command == "apply-event":
            if isinstance(session, dict) and session.get("operator_contract_version") == 2:
                raise ValueError(
                    "Operator-contract-v2 event commits must use recette_operator.py "
                    "close-event so results, closure proof, and stream certification stay atomic."
                )
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
