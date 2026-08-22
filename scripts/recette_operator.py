#!/usr/bin/env python3
"""Guide one recette run through fresh actions, event closure, and final output."""

from __future__ import annotations

import argparse
import json
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from event_feedback import event_feedback, feedback_for_event, final_conclusion
from execution_contract import validate_session
from incremental_recette import apply_event, load_object, save_atomic, validate_event
from preview_session_ledger import (
    begin_action,
    checkpoint,
    now,
    record_runtime_check,
    settle_action,
)
from recette_schema import ACTION_BOUNDARY_CONTRACT_VERSION, validate
from state_io import (
    atomic_write_file_pair,
    atomic_write_json_pair,
    recover_file_pair,
    serialized_json,
)


def _ordered_inventory(results: dict[str, Any]) -> list[dict[str, Any]]:
    run = results.get("run", {})
    inventory = [row for row in run.get("event_inventory", []) if isinstance(row, dict)]
    return [
        row
        for _, row in sorted(
            enumerate(inventory),
            key=lambda item: (
                item[1].get("plan_order") if isinstance(item[1].get("plan_order"), int) else 10**9,
                item[0],
            ),
        )
    ]


def _next_event(results: dict[str, Any], session: dict[str, Any]) -> dict[str, Any] | None:
    closed = {
        str(row.get("event_group_id", ""))
        for row in session.get("event_closures", [])
        if isinstance(row, dict)
    }
    return next(
        (
            row
            for row in _ordered_inventory(results)
            if str(row.get("event_group_id", "")) not in closed
        ),
        None,
    )


def _require_next_event(
    results: dict[str, Any],
    session: dict[str, Any],
    event_group_id: str,
) -> dict[str, Any]:
    expected = _next_event(results, session)
    if expected is None:
        raise ValueError("Every tracking-plan event is already closed.")
    if str(expected.get("event_group_id", "")) != event_group_id:
        raise ValueError(
            "Event execution must follow tracking-plan order; next event is "
            f"{expected.get('event_group_id')} ({expected.get('event_name')})."
        )
    return expected


def _reopened_target_closure(
    session: dict[str, Any],
    event_group_id: str,
) -> dict[str, Any] | None:
    for history in reversed(session.get("closure_history", [])):
        if (
            not isinstance(history, dict)
            or str(history.get("reopened_event_group_id", "")) != event_group_id
        ):
            continue
        invalidated = history.get("invalidated_closures", [])
        if isinstance(invalidated, list) and invalidated and isinstance(invalidated[0], dict):
            return invalidated[0]
    return None


def _require_active(session: dict[str, Any]) -> None:
    state = session.get("operator_state", {})
    if isinstance(state, dict) and state.get("status") == "PAUSED":
        raise ValueError("The run is paused; capture a fresh resume runtime check first.")
    if isinstance(state, dict) and state.get("status") == "FINISHED":
        raise ValueError("The run is already finished.")


def _require_guided_contract(
    results: dict[str, Any],
    session: dict[str, Any],
) -> None:
    run = results.get("run", {})
    if (
        not isinstance(run, dict)
        or run.get("action_boundary_contract_version") != ACTION_BOUNDARY_CONTRACT_VERSION
    ):
        raise ValueError(
            "The guided operator requires action_boundary_contract_version=1. "
            "Legacy schema-v3 results remain readable, but guided execution requires "
            "fresh normalization and runtime proof; missing historical fields are never fabricated."
        )
    required_operator_version = run.get("operator_contract_version_required", 1)
    if required_operator_version not in {1, 2}:
        raise ValueError("The normalized run declares an unsupported operator contract.")
    if session.get("operator_contract_version") != required_operator_version:
        raise ValueError(
            "The guided operator requires operator_contract_version="
            f"{required_operator_version} for this normalized run."
        )
    if required_operator_version == 2:
        normalized_run_id = str(run.get("run_id", "")).strip()
        session_run_id = str(session.get("run_id", "")).strip()
        if not session_run_id:
            raise ValueError(
                "The operator-v2 session is not bound to normalized run.run_id; recreate it."
            )
        if session_run_id != normalized_run_id:
            raise ValueError(
                "The operator-v2 session run_id differs from normalized run.run_id; "
                "previous-run state cannot be reused."
            )


def _save_pair_atomic(
    results_path: Path,
    results: dict[str, Any],
    session_path: Path,
    session: dict[str, Any],
) -> None:
    """Replace the result/session pair as one crash-recoverable transaction."""
    atomic_write_json_pair(results_path, results, session_path, session)


def _recover_input_pair(args: argparse.Namespace) -> None:
    """Recover an interrupted result/session transaction before any paired read."""
    results = getattr(args, "results", None)
    session = getattr(args, "session", None)
    if isinstance(results, Path) and isinstance(session, Path):
        recover_file_pair(results, session)


def _start_event(args: argparse.Namespace) -> dict[str, Any]:
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    _require_active(session)
    event = _require_next_event(results, session, args.event_group_id)
    if any(row.get("state") == "OPEN" for row in session.get("actions", [])):
        raise ValueError("Settle the open action before starting another action.")
    case = next(
        (
            row
            for row in session.get("cases", [])
            if isinstance(row, dict) and row.get("case_id") == args.case_id
        ),
        None,
    )
    if case is None or str(case.get("event_group_id", "")) != args.event_group_id:
        raise ValueError("The selected interaction case does not belong to this event.")
    staged = deepcopy(session)
    record_runtime_check(
        staged,
        Namespace(
            snapshot=args.runtime_snapshot,
            results=args.results,
            phase="before_action",
            action_id=args.action_id,
            case_id=args.case_id,
        ),
    )
    snapshot = json.loads(args.runtime_snapshot.read_text(encoding="utf-8"))
    begin_action(
        staged,
        Namespace(
            action_id=args.action_id,
            case_id=args.case_id,
            readiness_check_id=snapshot.get("check_id"),
            consent_state=args.consent_state,
            quiet_window_ms=args.quiet_window_ms,
            timeout_ms=args.timeout_ms,
            retry_of_action_id=args.retry_of_action_id,
        ),
    )
    staged["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": args.event_group_id,
    }
    staged["updated_at"] = now()
    errors = validate_session(staged, final=False)
    if errors:
        raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "started": True,
        "plan_order": event.get("plan_order"),
        "event_group_id": args.event_group_id,
        "event_name": event.get("event_name"),
        "case_id": args.case_id,
        "action_id": args.action_id,
        "next_required": [
            "record every business dataLayer push in the action window",
            "record every mandatory event layer and in-scope tag layer",
            "capture an after_action runtime snapshot and settle the action",
            "close the event to emit immediate feedback",
        ],
    }


def _settle_operator_action(args: argparse.Namespace) -> dict[str, Any]:
    session = load_object(args.session)
    results = load_object(args.results)
    _require_guided_contract(results, session)
    _require_active(session)
    action = next(
        (
            row
            for row in session.get("actions", [])
            if isinstance(row, dict) and row.get("action_id") == args.action_id
        ),
        None,
    )
    if action is None or action.get("state") != "OPEN":
        raise ValueError("settle-action requires the matching open action.")
    staged = deepcopy(session)
    record_runtime_check(
        staged,
        Namespace(
            snapshot=args.runtime_snapshot,
            results=args.results,
            phase="after_action",
            action_id=args.action_id,
            case_id=action.get("case_id"),
        ),
    )
    snapshot = json.loads(args.runtime_snapshot.read_text(encoding="utf-8"))
    settle_action(
        staged,
        Namespace(
            action_id=args.action_id,
            settlement_check_id=snapshot.get("check_id"),
            expected_seen=args.expected_seen,
            interaction_outcome=args.interaction_outcome,
            completion_signal=args.completion_signal,
            settlement_reason=args.settlement_reason,
        ),
    )
    staged["updated_at"] = now()
    errors = validate_session(staged, final=False)
    if errors:
        raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "settled": True,
        "action_id": args.action_id,
        "event_group_id": action.get("event_group_id"),
        "next_required": "finish remaining event cases, then close-event",
    }


def _interrupt_action(args: argparse.Namespace) -> dict[str, Any]:
    """Settle an interrupted action without deleting it or fabricating downstream proof."""
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    _require_active(session)
    action = next(
        (
            row
            for row in session.get("actions", [])
            if isinstance(row, dict)
            and row.get("action_id") == args.action_id
            and row.get("state") == "OPEN"
        ),
        None,
    )
    if action is None:
        raise ValueError("interrupt-action requires the matching open action.")
    reason = str(args.reason).strip()
    blocker_id = str(args.blocker_id).strip()
    if not reason or not blocker_id:
        raise ValueError("interrupt-action requires a blocker ID and exact reason.")
    staged = deepcopy(session)
    record_runtime_check(
        staged,
        Namespace(
            snapshot=args.runtime_snapshot,
            results=args.results,
            phase="interrupted_action",
            action_id=args.action_id,
            case_id=action.get("case_id"),
        ),
    )
    snapshot = json.loads(args.runtime_snapshot.read_text(encoding="utf-8"))
    expected_seen = any(
        isinstance(row, dict)
        and row.get("action_id") == args.action_id
        and row.get("classification") == "expected"
        for row in staged.get("business_pushes", [])
    )
    settle_action(
        staged,
        Namespace(
            action_id=args.action_id,
            settlement_check_id=snapshot.get("check_id"),
            expected_seen="true" if expected_seen else "false",
            interaction_outcome="uncertain",
            completion_signal=f"Runtime interruption captured: {reason}",
            settlement_reason=snapshot.get("failure_reason"),
        ),
    )
    interrupted_action = next(
        row
        for row in staged.get("actions", [])
        if isinstance(row, dict) and row.get("action_id") == args.action_id
    )
    interrupted_action.update(
        {
            "interruption_blocker_id": blocker_id,
            "interruption_reason": reason,
        }
    )
    case = next(
        row
        for row in staged.get("cases", [])
        if isinstance(row, dict) and row.get("case_id") == action.get("case_id")
    )
    case.update(
        {
            "execution_status": "BLOCKED",
            "blocker_id": blocker_id,
            "reason": reason,
            "final_action_id": None,
        }
    )
    staged["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": action.get("event_group_id"),
    }
    staged["updated_at"] = now()
    errors = validate_session(staged, results=results, final=False)
    if errors:
        raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "interrupted": True,
        "action_id": args.action_id,
        "case_id": action.get("case_id"),
        "event_group_id": action.get("event_group_id"),
        "status": "BLOCKED",
        "blocker_id": blocker_id,
        "reason": reason,
        "observed_expected_push": expected_seen,
        "next_required": (
            "Restore a controlled boundary and start one fresh action linked with "
            "--retry-of-action-id, or close the event with the retained blocker."
        ),
    }


def _pause_contract(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "pause_contract_version": 1,
        "operator_contract_version": 2,
        "run_id": session.get("run_id"),
        "connection_epoch": session.get("connection_epoch"),
        "browser_binding": deepcopy(session.get("browser_binding")),
        "stream_contract": deepcopy(session.get("stream_contract")),
        "open_action_ids": sorted(
            str(row.get("action_id", ""))
            for row in session.get("actions", [])
            if isinstance(row, dict) and row.get("state") == "OPEN"
        ),
    }


def _require_v2_pause_continuity(session: dict[str, Any]) -> dict[str, Any]:
    checkpoint_row = next(
        (
            row
            for row in reversed(session.get("checkpoints", []))
            if isinstance(row, dict) and row.get("pause_contract_version") == 1
        ),
        None,
    )
    if checkpoint_row is None:
        raise ValueError("Operator-v2 resume requires its recorded pause continuity checkpoint.")
    current = _pause_contract(session)
    for field in (
        "operator_contract_version",
        "run_id",
        "connection_epoch",
        "browser_binding",
        "stream_contract",
        "open_action_ids",
    ):
        if checkpoint_row.get(field) != current.get(field):
            raise ValueError(
                f"Operator-v2 pause continuity changed for {field}; capture cannot resume safely."
            )
    return checkpoint_row


def _require_v2_resume_check_continuity(
    session: dict[str, Any],
    action: dict[str, Any],
    check: dict[str, Any],
    pause_checkpoint: dict[str, Any],
) -> None:
    readiness = next(
        (
            row
            for row in session.get("runtime_checks", [])
            if isinstance(row, dict) and row.get("check_id") == action.get("readiness_check_id")
        ),
        None,
    )
    if readiness is None:
        raise ValueError("Operator-v2 resume cannot resolve the action readiness capture.")
    for field in (
        "browser_instance_id",
        "browser_context_id",
        "tab_id",
        "preview_session_id",
    ):
        if check.get(field) != readiness.get(field):
            raise ValueError(f"Operator-v2 resume {field} differs from the opened action boundary.")
    if sorted(check.get("loaded_client_container_ids", [])) != sorted(
        readiness.get("loaded_client_container_ids", [])
    ):
        raise ValueError(
            "Operator-v2 resume loaded containers differ from the opened action boundary."
        )
    for field in (
        "preview_event_cursor",
        "network_request_cursor",
        "datalayer_call_cursor",
    ):
        if check.get(field, -1) < readiness.get(field, -1):
            raise ValueError(f"Operator-v2 resume {field} moved backwards while paused.")
    paused_stream = pause_checkpoint.get("stream_contract", {})
    if isinstance(paused_stream, dict):
        cursor_pairs = {
            "preview_event_cursor": "reviewed_through_preview_event_index",
            "datalayer_call_cursor": "reviewed_through_datalayer_call_index",
        }
        for check_field, stream_field in cursor_pairs.items():
            paused_cursor = paused_stream.get(stream_field)
            if isinstance(paused_cursor, int) and check.get(check_field, -1) < paused_cursor:
                raise ValueError(
                    f"Operator-v2 resume {check_field} precedes the reviewed stream checkpoint."
                )


def _pause_run(args: argparse.Namespace) -> dict[str, Any]:
    session = load_object(args.session)
    state = session.get("operator_state", {})
    contract_version = session.get("operator_contract_version")
    if contract_version not in {1, 2}:
        raise ValueError("pause-run requires operator_contract_version=1 or 2.")
    results = load_object(args.results) if args.results is not None else None
    if contract_version == 2 and results is None:
        raise ValueError("Operator-v2 pause-run requires --results for run compatibility.")
    if results is not None:
        _require_guided_contract(results, session)
    if isinstance(state, dict) and state.get("status") == "FINISHED":
        raise ValueError("A finished run cannot be paused; reopen an event first.")
    if isinstance(state, dict) and state.get("status") == "PAUSED":
        raise ValueError("The run is already paused.")
    staged = deepcopy(session)
    checkpoint(staged, Namespace(label=args.label))
    if contract_version == 2:
        staged["checkpoints"][-1].update(_pause_contract(staged))
    staged["operator_state"] = {
        "status": "PAUSED",
        "current_event_group_id": (
            state.get("current_event_group_id") if isinstance(state, dict) else None
        ),
    }
    staged["updated_at"] = now()
    if contract_version == 2 or results is not None:
        errors = validate_session(staged, results=results, final=False)
        if errors:
            raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "paused": True,
        "label": args.label,
        "operator_contract_version": contract_version,
    }


def _resume_run(args: argparse.Namespace) -> dict[str, Any]:
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    state = session.get("operator_state", {})
    if not isinstance(state, dict) or state.get("status") != "PAUSED":
        raise ValueError("resume-run requires a paused run.")
    pause_checkpoint = (
        _require_v2_pause_continuity(session)
        if session.get("operator_contract_version") == 2
        else {}
    )
    action = next(
        (
            row
            for row in session.get("actions", [])
            if isinstance(row, dict) and row.get("state") == "OPEN"
        ),
        None,
    )
    staged = deepcopy(session)
    if action is None:
        if args.runtime_snapshot is not None:
            raise ValueError(
                "Do not supply a resume snapshot between events; the next start-event "
                "captures a fresh before_action boundary."
            )
        staged["operator_state"] = {
            "status": "ACTIVE",
            "current_event_group_id": state.get("current_event_group_id"),
        }
        staged["updated_at"] = now()
        errors = validate_session(staged, results=results, final=False)
        if errors:
            raise ValueError("\n".join(errors))
        save_atomic(args.session, staged)
        return {
            "resumed": True,
            "action_id": None,
            "fresh_runtime_check_id": None,
            "next_required": "start-event with a fresh before_action runtime snapshot",
        }
    if args.runtime_snapshot is None:
        raise ValueError("Resuming an open action requires a fresh runtime snapshot.")
    record_runtime_check(
        staged,
        Namespace(
            snapshot=args.runtime_snapshot,
            results=args.results,
            phase="resume",
            action_id=action.get("action_id"),
            case_id=action.get("case_id"),
        ),
    )
    check = staged["runtime_checks"][-1]
    if session.get("operator_contract_version") == 2:
        _require_v2_resume_check_continuity(staged, action, check, pause_checkpoint)
    check["consumed"] = True
    check["consumed_by_action_id"] = action.get("action_id")
    staged["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": action.get("event_group_id"),
    }
    staged["updated_at"] = now()
    errors = validate_session(staged, final=False)
    if errors:
        raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "resumed": True,
        "action_id": action.get("action_id"),
        "fresh_runtime_check_id": check.get("check_id"),
    }


def _close_event(args: argparse.Namespace) -> dict[str, Any]:
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    _require_active(session)
    event = _require_next_event(results, session, args.event_group_id)
    group_cases = [
        row
        for row in session.get("cases", [])
        if isinstance(row, dict) and row.get("event_group_id") == args.event_group_id
    ]
    if not group_cases:
        raise ValueError("The event has no registered interaction cases.")
    if any(row.get("execution_status") == "PENDING" for row in group_cases):
        raise ValueError("Close or execute every applicable interaction case first.")
    coverage_revision = None
    if session.get("operator_contract_version") == 2:
        coverage = next(
            (
                row
                for row in session.get("coverage_decisions", [])
                if isinstance(row, dict) and row.get("event_group_id") == args.event_group_id
            ),
            None,
        )
        if not isinstance(coverage, dict) or coverage.get("status") != "FROZEN":
            raise ValueError("Freeze the event scenario coverage before closure.")
        coverage_revision = coverage.get("revision")
    group_action_ids = {
        str(row.get("action_id", ""))
        for row in session.get("actions", [])
        if isinstance(row, dict) and row.get("event_group_id") == args.event_group_id
    }
    if any(
        row.get("state") == "OPEN" and str(row.get("action_id", "")) in group_action_ids
        for row in session.get("actions", [])
        if isinstance(row, dict)
    ):
        raise ValueError("Settle every action for the event before closure.")
    prior_target_closure = _reopened_target_closure(session, args.event_group_id)
    if prior_target_closure is not None:
        current_case_ids = {str(row.get("case_id", "")) for row in group_cases}
        current_final_actions = {
            str(row.get("final_action_id", ""))
            for row in group_cases
            if row.get("execution_status") == "EXECUTED"
        }
        prior_case_ids = {
            str(value)
            for value in prior_target_closure.get("case_ids", [])
            if isinstance(value, str)
        }
        prior_final_actions = {
            str(value)
            for value in prior_target_closure.get("final_action_ids", [])
            if isinstance(value, str)
        }
        if current_case_ids == prior_case_ids and current_final_actions == prior_final_actions:
            raise ValueError(
                "A reopened target event requires a new material case or a new final action; "
                "the prior closure cannot be acknowledged unchanged."
            )
    patch = load_object(args.event_patch)
    updated_results, patched_group = apply_event(results, patch, validate_result=False)
    if patched_group != args.event_group_id:
        raise ValueError("Event patch and requested event group differ.")
    updated_session = deepcopy(session)
    timestamp = now()
    closure = {
        "event_group_id": args.event_group_id,
        "plan_order": event.get("plan_order"),
        "case_ids": [str(row.get("case_id", "")) for row in group_cases],
        "final_action_ids": [
            str(row.get("final_action_id", ""))
            for row in group_cases
            if row.get("execution_status") == "EXECUTED"
        ],
        "closed_at": timestamp,
        "feedback_emitted_at": timestamp,
    }
    if session.get("operator_contract_version") == 2:
        closure["coverage_revision"] = coverage_revision
    updated_session.setdefault("event_closures", []).append(closure)
    updated_session["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": None,
    }
    updated_session["updated_at"] = timestamp
    validate_event(
        updated_results,
        args.event_group_id,
        updated_session,
    )
    _save_pair_atomic(args.results, updated_results, args.session, updated_session)
    return feedback_for_event(updated_results, args.event_group_id, updated_session)


def _reopen_event(args: argparse.Namespace) -> dict[str, Any]:
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    operator_state = session.get("operator_state")
    was_finished = isinstance(operator_state, dict) and operator_state.get("status") == "FINISHED"
    if any(
        isinstance(row, dict) and row.get("state") == "OPEN" for row in session.get("actions", [])
    ):
        raise ValueError("Settle the open action before reopening an event.")
    reason = str(args.reason).strip()
    if not reason:
        raise ValueError("reopen-event requires a precise reason.")
    closures = [row for row in session.get("event_closures", []) if isinstance(row, dict)]
    index = next(
        (
            position
            for position, row in enumerate(closures)
            if str(row.get("event_group_id", "")) == args.event_group_id
        ),
        None,
    )
    if index is None:
        raise ValueError("Only a currently closed event can be reopened.")
    invalidated = deepcopy(closures[index:])
    timestamp = now()
    staged = deepcopy(session)
    staged["event_closures"] = deepcopy(closures[:index])
    staged.setdefault("closure_history", []).append(
        {
            "reopened_event_group_id": args.event_group_id,
            "reopened_at": timestamp,
            "reason": reason,
            "invalidated_closures": invalidated,
        }
    )
    staged["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": args.event_group_id,
    }
    staged["updated_at"] = timestamp
    errors = validate_session(staged, results=results, final=False)
    if errors:
        raise ValueError("\n".join(errors))
    save_atomic(args.session, staged)
    return {
        "reopened": True,
        "event_group_id": args.event_group_id,
        "reason": reason,
        "invalidated_event_closures": [row.get("event_group_id") for row in invalidated],
        "prior_proof_retained": True,
        "previous_output_superseded": was_finished,
        "next_required": (
            "register and execute the late interaction/variant, reclose this event, then "
            "revalidate the preserved later event closures in plan order"
        ),
    }


def _finish_run(args: argparse.Namespace) -> dict[str, Any]:
    paths = [args.results.resolve(), args.session.resolve(), args.workbook.resolve()]
    if len(set(paths)) != len(paths):
        raise ValueError("Results, session, and workbook must use three different files.")
    if args.workbook.suffix.lower() != ".xlsx":
        raise ValueError("The final workbook path must use the .xlsx extension.")
    recover_file_pair(args.workbook, args.session)
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    next_event = _next_event(results, session)
    if next_event is not None:
        raise ValueError(
            "Cannot finish before every event is closed; next event is "
            f"{next_event.get('event_group_id')}."
        )
    schema_errors = validate(results, strict=True)
    session_errors = validate_session(session, results=results, final=True)
    if schema_errors or session_errors:
        raise ValueError("\n".join([*schema_errors, *session_errors]))
    from build_recette_report import build_workbook

    staged_session = deepcopy(session)
    staged_session["operator_state"] = {
        "status": "FINISHED",
        "current_event_group_id": None,
    }
    staged_session["updated_at"] = now()
    final_errors = validate_session(staged_session, results=results, final=True)
    if final_errors:
        raise ValueError("\n".join(final_errors))
    args.workbook.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.workbook.with_name(f".{args.workbook.stem}.{uuid4().hex}.validated.xlsx")
    try:
        build_workbook(results, temporary, schema_errors, staged_session)
        atomic_write_file_pair(
            args.workbook,
            temporary.read_bytes(),
            args.session,
            serialized_json(staged_session),
        )
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "finished": True,
        "workbook": str(args.workbook.resolve()),
        "events": event_feedback(results, staged_session),
        "conclusion": final_conclusion(results, staged_session),
    }


def _status(args: argparse.Namespace) -> dict[str, Any]:
    results = load_object(args.results)
    session = load_object(args.session)
    _require_guided_contract(results, session)
    return {
        "guided_contract": {
            "compatible": True,
            "operator_contract_version": session.get("operator_contract_version"),
            "run_id": session.get("run_id"),
        },
        "operator_state": session.get("operator_state"),
        "next_event": _next_event(results, session),
        "closed_events": event_feedback(results, session)[: len(session.get("event_closures", []))],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start-event")
    start.add_argument("results", type=Path)
    start.add_argument("session", type=Path)
    start.add_argument("runtime_snapshot", type=Path)
    start.add_argument("--event-group-id", required=True)
    start.add_argument("--case-id", required=True)
    start.add_argument("--action-id", required=True)
    start.add_argument("--consent-state", required=True)
    start.add_argument("--quiet-window-ms", type=int, default=2000)
    start.add_argument("--timeout-ms", type=int, default=15000)
    start.add_argument("--retry-of-action-id")

    settle = commands.add_parser("settle-action")
    settle.add_argument("results", type=Path)
    settle.add_argument("session", type=Path)
    settle.add_argument("runtime_snapshot", type=Path)
    settle.add_argument("--action-id", required=True)
    settle.add_argument("--expected-seen", choices=("true", "false"), required=True)
    settle.add_argument(
        "--interaction-outcome",
        choices=("completed", "failed", "uncertain"),
        required=True,
    )
    settle.add_argument("--completion-signal", required=True)
    settle.add_argument(
        "--settlement-reason",
        choices=(
            "expected_and_quiet",
            "quiet_without_expected",
            "timeout",
            "interaction_failed",
        ),
        required=True,
    )

    interrupt = commands.add_parser("interrupt-action")
    interrupt.add_argument("results", type=Path)
    interrupt.add_argument("session", type=Path)
    interrupt.add_argument("runtime_snapshot", type=Path)
    interrupt.add_argument("--action-id", required=True)
    interrupt.add_argument("--blocker-id", required=True)
    interrupt.add_argument("--reason", required=True)

    pause = commands.add_parser("pause-run")
    pause.add_argument("session", type=Path)
    pause.add_argument("--results", type=Path)
    pause.add_argument("--label", required=True)

    resume = commands.add_parser("resume-run")
    resume.add_argument("results", type=Path)
    resume.add_argument("session", type=Path)
    resume.add_argument("runtime_snapshot", type=Path, nargs="?")

    close = commands.add_parser("close-event")
    close.add_argument("results", type=Path)
    close.add_argument("session", type=Path)
    close.add_argument("event_patch", type=Path)
    close.add_argument("--event-group-id", required=True)

    reopen = commands.add_parser("reopen-event")
    reopen.add_argument("results", type=Path)
    reopen.add_argument("session", type=Path)
    reopen.add_argument("--event-group-id", required=True)
    reopen.add_argument("--reason", required=True)

    finish = commands.add_parser("finish-run")
    finish.add_argument("results", type=Path)
    finish.add_argument("session", type=Path)
    finish.add_argument("workbook", type=Path)

    status_parser = commands.add_parser("status")
    status_parser.add_argument("results", type=Path)
    status_parser.add_argument("session", type=Path)
    return root


COMMANDS = {
    "start-event": _start_event,
    "settle-action": _settle_operator_action,
    "interrupt-action": _interrupt_action,
    "pause-run": _pause_run,
    "resume-run": _resume_run,
    "close-event": _close_event,
    "reopen-event": _reopen_event,
    "finish-run": _finish_run,
    "status": _status,
}


def main() -> int:
    args = parser().parse_args()
    try:
        _recover_input_pair(args)
        output = COMMANDS[args.command](args)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
