#!/usr/bin/env python3
"""Validate gapless dataLayer and Tag Assistant review segments."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

SEGMENT_KINDS = {"INITIAL_LOAD", "ACTION", "INTER_ACTION", "FINAL"}
SEGMENT_STATUSES = {"OPEN", "RECONCILED"}
STREAM_STATUSES = {"OPEN", "CLOSED"}
DATALAYER_DISPOSITIONS = {
    "BUSINESS_EVENT",
    "TECHNICAL_EVENT",
    "STATE_UPDATE",
    "NON_EVENT",
}
RECONNECT_STATUSES = {"RECONCILED"}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_timestamp(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _cursor(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _stream_index(push: dict[str, Any], field: str) -> int | None:
    value = push.get(field)
    return value if _cursor(value) else None


def _duplicates(values: list[str]) -> list[str]:
    return sorted(
        value for value, count in Counter(item for item in values if item).items() if count > 1
    )


def _object_rows(value: Any, label: str, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append(f"session: {label} must be an array")
        return []
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"session {label[:-1]} row {index} must be an object")
        else:
            rows.append(row)
    return rows


def _row_catalog(rows: Any, id_field: str) -> dict[str, dict[str, Any]]:
    return {
        str(row.get(id_field, "")).strip(): row
        for row in rows or []
        if isinstance(row, dict) and str(row.get(id_field, "")).strip()
    }


def _validate_contract(contract: Any, *, final: bool, errors: list[str]) -> dict[str, Any]:
    if not isinstance(contract, dict):
        errors.append("session: stream_contract must be an object")
        return {}
    for field in ("started_at", "start_preview_event_index", "start_datalayer_call_index"):
        if field not in contract:
            errors.append(f"session stream_contract missing '{field}'")
    if not _iso_timestamp(contract.get("started_at")):
        errors.append("session stream_contract.started_at must be ISO 8601 with timezone")
    for field in (
        "start_preview_event_index",
        "start_datalayer_call_index",
        "reviewed_through_preview_event_index",
        "reviewed_through_datalayer_call_index",
    ):
        if not _cursor(contract.get(field)):
            errors.append(f"session stream_contract.{field} must be a non-negative integer")
    status = str(contract.get("status", "")).strip().upper()
    if status not in STREAM_STATUSES:
        errors.append("session stream_contract.status must be OPEN or CLOSED")
    if final and status != "CLOSED":
        errors.append("session stream_contract must be CLOSED for final certification")
    if status == "CLOSED" and not _iso_timestamp(contract.get("closed_at")):
        errors.append("session closed stream requires closed_at")
    return contract


def _validate_datalayer_argument(
    argument: dict[str, Any],
    *,
    call_label: str,
    call_index: Any,
    pushes: dict[str, dict[str, Any]],
    referenced_business_pushes: list[str],
    final: bool,
    errors: list[str],
) -> None:
    argument_index = argument.get("argument_index")
    label = f"{call_label} argument {argument_index}"
    disposition = str(argument.get("disposition", "")).strip().upper()
    if disposition not in DATALAYER_DISPOSITIONS:
        errors.append(f"{label}: invalid disposition")
        return
    if not isinstance(argument.get("event_field_present"), bool):
        errors.append(f"{label}: event_field_present must be boolean")
    if not _nonempty(argument.get("reason")):
        errors.append(f"{label}: reason is required")
    event_name = str(argument.get("event_name", "")).strip()
    event_present = argument.get("event_field_present") is True
    push_id = str(argument.get("push_id", "")).strip()
    if disposition == "BUSINESS_EVENT":
        if not event_present or not event_name:
            errors.append(f"{label}: BUSINESS_EVENT requires a non-empty event field")
        if event_name.startswith("gtm."):
            errors.append(f"{label}: gtm.* lifecycle events are TECHNICAL_EVENT")
        push = pushes.get(push_id)
        if not push_id or push is None:
            errors.append(f"{label}: BUSINESS_EVENT requires a known push_id")
        else:
            referenced_business_pushes.append(push_id)
            if push.get("datalayer_call_index") != call_index:
                errors.append(f"{label}: push has a different call index")
            if push.get("event_name") != event_name:
                errors.append(f"{label}: push has a different event name")
    elif push_id:
        errors.append(f"{label}: only BUSINESS_EVENT may declare push_id")
    if disposition == "TECHNICAL_EVENT" and (
        not event_present or not event_name.startswith("gtm.")
    ):
        errors.append(f"{label}: TECHNICAL_EVENT requires a gtm.* event name")
    if disposition in {"STATE_UPDATE", "NON_EVENT"} and event_present:
        errors.append(f"{label}: an argument with an event field cannot be hidden as {disposition}")
    if final and argument.get("capture_complete") is not True:
        errors.append(f"{label}: final review requires capture_complete=true")


def _validate_datalayer_reviews(
    segment: dict[str, Any],
    *,
    label: str,
    pushes: dict[str, dict[str, Any]],
    referenced_business_pushes: list[str],
    final: bool,
    errors: list[str],
) -> None:
    """Require every recorder call and argument to be explicitly classified."""
    reviews = segment.get("datalayer_call_reviews")
    if not isinstance(reviews, list) or any(not isinstance(row, dict) for row in reviews):
        errors.append(f"{label}: datalayer_call_reviews must be an object array")
        return
    start = segment.get("start_datalayer_call_index")
    end = segment.get("end_datalayer_call_index")
    if not _cursor(start) or not _cursor(end):
        return
    if [row.get("call_index") for row in reviews] != list(range(start + 1, end + 1)):
        errors.append(f"{label}: dataLayer call reviews must cover every call index exactly once")
    for review in reviews:
        call_index = review.get("call_index")
        call_label = f"{label} dataLayer call {call_index}"
        if not _nonempty(review.get("evidence_id")):
            errors.append(f"{call_label}: evidence_id is required")
        arguments = review.get("arguments")
        if not isinstance(arguments, list) or any(not isinstance(row, dict) for row in arguments):
            errors.append(f"{call_label}: arguments must be an object array")
            continue
        if [row.get("argument_index") for row in arguments] != list(range(len(arguments))):
            errors.append(f"{call_label}: argument indexes must be contiguous from zero")
        if not arguments and not _nonempty(review.get("reason")):
            errors.append(f"{call_label}: an empty push call requires a reason")
        for argument in arguments:
            _validate_datalayer_argument(
                argument,
                call_label=call_label,
                call_index=call_index,
                pushes=pushes,
                referenced_business_pushes=referenced_business_pushes,
                final=final,
                errors=errors,
            )


def _validate_segment_cursors(segment: dict[str, Any], *, label: str, errors: list[str]) -> None:
    fields = (
        "start_preview_event_index",
        "end_preview_event_index",
        "start_datalayer_call_index",
        "end_datalayer_call_index",
    )
    for field in fields:
        if not _cursor(segment.get(field)):
            errors.append(f"{label}: {field} must be a non-negative integer")
    pairs = (
        ("start_preview_event_index", "end_preview_event_index", "Preview"),
        ("start_datalayer_call_index", "end_datalayer_call_index", "dataLayer"),
    )
    for start_field, end_field, name in pairs:
        start = segment.get(start_field)
        end = segment.get(end_field)
        if _cursor(start) and _cursor(end) and end < start:
            errors.append(f"{label}: {name} cursor moves backwards")


def _validate_segment(
    segment: dict[str, Any],
    *,
    index: int,
    actions: dict[str, dict[str, Any]],
    pushes: dict[str, dict[str, Any]],
    action_segments: dict[str, list[dict[str, Any]]],
    referenced_push_ids: list[str],
    reviewed_business_push_ids: list[str],
    final: bool,
    errors: list[str],
) -> None:
    segment_id = str(segment.get("segment_id", "")).strip() or str(index)
    label = f"session stream segment {segment_id}"
    kind = str(segment.get("kind", "")).strip().upper()
    if kind not in SEGMENT_KINDS:
        errors.append(f"{label}: invalid kind")
    status = str(segment.get("status", "")).strip().upper()
    if status not in SEGMENT_STATUSES:
        errors.append(f"{label}: invalid status")
    if final and status != "RECONCILED":
        errors.append(f"{label}: final certification requires RECONCILED")
    epoch = segment.get("connection_epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 1:
        errors.append(f"{label}: connection_epoch must be a positive integer")
    _validate_segment_cursors(segment, label=label, errors=errors)
    for field in ("started_at", "ended_at"):
        if not _iso_timestamp(segment.get(field)):
            errors.append(f"{label}: {field} must be ISO 8601 with timezone")
    refs = segment.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
        errors.append(f"{label}: evidence_ids must be a non-empty string array")
    push_ids = segment.get("observed_push_ids")
    if not isinstance(push_ids, list) or any(not _nonempty(item) for item in push_ids):
        errors.append(f"{label}: observed_push_ids must be a string array")
        push_ids = []
    if len(set(push_ids)) != len(push_ids):
        errors.append(f"{label}: observed_push_ids contains duplicates")
    referenced_push_ids.extend(map(str, push_ids))
    for push_id in push_ids:
        push = pushes.get(str(push_id))
        if push is None:
            errors.append(f"{label}: unknown push_id '{push_id}'")
        elif push.get("segment_id") != segment_id:
            errors.append(f"{label}: push {push_id} points to another segment")
    action_id = str(segment.get("action_id") or "").strip()
    if kind == "ACTION":
        if not action_id or action_id not in actions:
            errors.append(f"{label}: ACTION segment requires a known action_id")
        else:
            action_segments[action_id].append(segment)
    elif action_id:
        errors.append(f"{label}: only ACTION segments may declare action_id")
    _validate_datalayer_reviews(
        segment,
        label=label,
        pushes=pushes,
        referenced_business_pushes=reviewed_business_push_ids,
        final=final,
        errors=errors,
    )


def _validate_reconnect(
    reconnect: Any,
    *,
    previous: dict[str, Any],
    segment: dict[str, Any],
    actions: dict[str, dict[str, Any]],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(reconnect, dict):
        errors.append(f"{label}: a new connection epoch requires a reconnect contract")
        return
    if reconnect.get("status") not in RECONNECT_STATUSES:
        errors.append(f"{label}: reconnect status must be RECONCILED")
    if not _nonempty(reconnect.get("reason")):
        errors.append(f"{label}: reconnect reason is required")
    refs = reconnect.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
        errors.append(f"{label}: reconnect evidence_ids must be a non-empty string array")
    expected = {
        "previous_connection_epoch": previous.get("connection_epoch"),
        "new_connection_epoch": segment.get("connection_epoch"),
        "previous_segment_id": previous.get("segment_id"),
        "previous_preview_event_index": previous.get("end_preview_event_index"),
        "new_preview_event_index": segment.get("start_preview_event_index"),
        "datalayer_call_index": segment.get("start_datalayer_call_index"),
    }
    for field, expected_value in expected.items():
        if reconnect.get(field) != expected_value:
            errors.append(f"{label}: reconnect {field} must be {expected_value!r}")
    for side in ("before_binding", "after_binding"):
        binding = reconnect.get(side)
        if not isinstance(binding, dict):
            errors.append(f"{label}: reconnect {side} must be an object")
            continue
        for field in (
            "browser_instance_id",
            "browser_context_id",
            "tab_id",
            "preview_session_id",
        ):
            if not _nonempty(binding.get(field)):
                errors.append(f"{label}: reconnect {side}.{field} is required")
    before_binding = reconnect.get("before_binding")
    after_binding = reconnect.get("after_binding")
    if isinstance(before_binding, dict) and isinstance(after_binding, dict):
        for field in ("browser_instance_id", "browser_context_id"):
            if before_binding.get(field) != after_binding.get(field):
                errors.append(f"{label}: reconnect changed {field}")
    action_id = str(reconnect.get("action_id") or "").strip()
    case_id = str(reconnect.get("case_id") or "").strip()
    if bool(action_id) != bool(case_id):
        errors.append(f"{label}: reconnect action_id and case_id must be declared together")
    elif action_id:
        action = actions.get(action_id)
        if action is None:
            errors.append(f"{label}: reconnect references an unknown action_id")
        elif str(action.get("case_id", "")).strip() != case_id:
            errors.append(f"{label}: reconnect action belongs to another case")


def _validate_epoch_continuity(
    segments: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
    actions: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    previous: dict[str, Any] | None = None
    for segment in segments:
        segment_id = str(segment.get("segment_id", "")).strip()
        label = f"session stream segment {segment_id}"
        epoch = segment.get("connection_epoch")
        if previous is None:
            if segment.get("previous_segment_id") not in (None, ""):
                errors.append(f"{label}: initial segment cannot have a predecessor")
            if segment.get("start_preview_event_index") != contract.get(
                "start_preview_event_index"
            ):
                errors.append(f"{label}: wrong initial Preview cursor")
            if segment.get("start_datalayer_call_index") != contract.get(
                "start_datalayer_call_index"
            ):
                errors.append(f"{label}: wrong initial dataLayer cursor")
            if segment.get("reconnect") not in (None, {}):
                errors.append(f"{label}: initial segment cannot declare reconnect")
            previous = segment
            continue

        previous_id = str(previous.get("segment_id", "")).strip()
        previous_epoch = previous.get("connection_epoch")
        if segment.get("previous_segment_id") != previous_id:
            errors.append(f"{label}: previous_segment_id must be {previous_id}")
        if not isinstance(epoch, int) or not isinstance(previous_epoch, int):
            previous = segment
            continue
        if epoch == previous_epoch:
            if segment.get("reconnect") not in (None, {}):
                errors.append(f"{label}: reconnect is allowed only on a new connection epoch")
            if segment.get("start_preview_event_index") != previous.get("end_preview_event_index"):
                errors.append(f"{label}: Preview review has a gap or overlap")
        elif epoch == previous_epoch + 1:
            _validate_reconnect(
                segment.get("reconnect"),
                previous=previous,
                segment=segment,
                actions=actions,
                label=label,
                errors=errors,
            )
        else:
            errors.append(f"{label}: connection epochs must be contiguous and ordered")
        if segment.get("start_datalayer_call_index") != previous.get("end_datalayer_call_index"):
            errors.append(f"{label}: dataLayer review has a cross-segment gap or overlap")
        previous = segment


def _validate_terminal_cursors(
    segments: list[dict[str, Any]],
    *,
    contract: dict[str, Any],
    final: bool,
    errors: list[str],
) -> None:
    if not segments:
        if final:
            errors.append("session final certification requires stream segments")
        return
    last = segments[-1]
    if last.get("end_preview_event_index") != contract.get("reviewed_through_preview_event_index"):
        errors.append("session stream final Preview cursor does not match reviewed-through cursor")
    if last.get("end_datalayer_call_index") != contract.get(
        "reviewed_through_datalayer_call_index"
    ):
        errors.append(
            "session stream final dataLayer cursor does not match reviewed-through cursor"
        )


def _validate_segment_sequence(
    segments: list[dict[str, Any]], *, final: bool, errors: list[str]
) -> None:
    initial_positions = [
        index for index, segment in enumerate(segments) if segment.get("kind") == "INITIAL_LOAD"
    ]
    final_positions = [
        index for index, segment in enumerate(segments) if segment.get("kind") == "FINAL"
    ]
    if len(initial_positions) > 1:
        errors.append("session stream requires at most one INITIAL_LOAD segment")
    if len(final_positions) > 1:
        errors.append("session stream requires at most one FINAL segment")
    if initial_positions and initial_positions[0] != 0:
        errors.append("session INITIAL_LOAD must be the first stream segment")
    if final_positions and final_positions[0] != len(segments) - 1:
        errors.append("session FINAL must be the last stream segment")
    if final and initial_positions != [0]:
        errors.append("session final certification requires one leading INITIAL_LOAD segment")
    if final and final_positions != [len(segments) - 1]:
        errors.append("session final certification requires one trailing FINAL segment")


def _validate_action_segment(
    action_id: str,
    action: dict[str, Any],
    *,
    mapped: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if action.get("state") != "SETTLED":
        return
    if len(mapped) != 1:
        errors.append(f"session action {action_id}: requires exactly one ACTION stream segment")
        return
    segment = mapped[0]
    comparisons = (
        ("start_preview_event_index", "last_event_before", "starts at wrong Preview cursor"),
        ("end_preview_event_index", "settled_final_event", "ends at wrong Preview cursor"),
        (
            "start_datalayer_call_index",
            "datalayer_call_index_before",
            "starts at wrong dataLayer cursor",
        ),
        (
            "end_datalayer_call_index",
            "datalayer_call_index_after",
            "ends at wrong dataLayer cursor",
        ),
    )
    for segment_field, action_field, message in comparisons:
        if segment.get(segment_field) != action.get(action_field):
            errors.append(f"session action {action_id}: stream segment {message}")


def _validate_push_coverage(
    pushes: dict[str, dict[str, Any]],
    *,
    referenced_push_ids: list[str],
    reviewed_business_push_ids: list[str],
    errors: list[str],
) -> None:
    duplicate_refs = _duplicates(referenced_push_ids)
    if duplicate_refs:
        errors.append("session stream segments reuse pushes " + ", ".join(duplicate_refs))
    missing = sorted(set(pushes) - set(referenced_push_ids))
    if missing:
        errors.append("session business pushes missing from stream segments " + ", ".join(missing))
    duplicate_reviews = _duplicates(reviewed_business_push_ids)
    if duplicate_reviews:
        errors.append(
            "session dataLayer reviews reuse business pushes " + ", ".join(duplicate_reviews)
        )
    datalayer_pushes = {
        push_id
        for push_id, push in pushes.items()
        if _stream_index(push, "datalayer_call_index") is not None
    }
    missing_reviews = sorted(datalayer_pushes - set(reviewed_business_push_ids))
    if missing_reviews:
        errors.append(
            "session dataLayer business pushes missing from call reviews "
            + ", ".join(missing_reviews)
        )


def _validate_push_bounds(
    push_id: str,
    push: dict[str, Any],
    *,
    segment_by_id: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    segment = segment_by_id.get(str(push.get("segment_id", "")).strip())
    if segment is None:
        errors.append(f"session business push {push_id}: unknown segment_id")
        return
    preview_index = _stream_index(push, "preview_event_index")
    datalayer_index = _stream_index(push, "datalayer_call_index")
    if preview_index is None and datalayer_index is None:
        errors.append(
            f"session business push {push_id}: requires Preview or dataLayer stream index"
        )
    preview_start = segment.get("start_preview_event_index")
    preview_end = segment.get("end_preview_event_index")
    if (
        preview_index is not None
        and _cursor(preview_start)
        and _cursor(preview_end)
        and not preview_start < preview_index <= preview_end
    ):
        errors.append(f"session business push {push_id}: Preview index is outside its segment")
    dl_start = segment.get("start_datalayer_call_index")
    dl_end = segment.get("end_datalayer_call_index")
    if (
        datalayer_index is not None
        and _cursor(dl_start)
        and _cursor(dl_end)
        and not dl_start < datalayer_index <= dl_end
    ):
        errors.append(f"session business push {push_id}: dataLayer index is outside its segment")
    if preview_index is not None and push.get("event_index") != preview_index:
        errors.append(
            f"session business push {push_id}: event_index must match preview_event_index"
        )
    segment_action = str(segment.get("action_id") or "").strip()
    push_action = str(push.get("action_id") or "").strip()
    push_epoch = push.get("connection_epoch")
    segment_epoch = segment.get("connection_epoch")
    if push_epoch is None and isinstance(segment_epoch, int) and segment_epoch > 1:
        errors.append(f"session business push {push_id}: reconnect epoch is required")
    elif push_epoch is not None and push_epoch != segment_epoch:
        errors.append(f"session business push {push_id}: connection_epoch differs from its segment")
    if segment.get("kind") == "ACTION" and push_action != segment_action:
        errors.append(f"session business push {push_id}: action_id differs from its segment")
    if segment.get("kind") != "ACTION" and push_action:
        errors.append(f"session business push {push_id}: inter-action push cannot claim action_id")


def stream_errors(ledger: dict[str, Any], *, final: bool) -> list[str]:
    """Return continuity and mapping errors for an operator-contract-v2 stream."""
    errors: list[str] = []
    contract = _validate_contract(ledger.get("stream_contract"), final=final, errors=errors)
    if not contract:
        return errors
    segments = _object_rows(ledger.get("stream_segments"), "stream_segments", errors)
    if not isinstance(ledger.get("stream_segments"), list):
        return errors
    segment_ids = [str(row.get("segment_id", "")).strip() for row in segments]
    for index, segment_id in enumerate(segment_ids, start=1):
        if not segment_id:
            errors.append(f"session stream segment row {index} missing segment_id")
    duplicates = _duplicates(segment_ids)
    if duplicates:
        errors.append("session stream segments contain duplicate IDs " + ", ".join(duplicates))
    segment_by_id = _row_catalog(segments, "segment_id")
    actions = _row_catalog(ledger.get("actions"), "action_id")
    pushes = _row_catalog(ledger.get("business_pushes"), "push_id")
    action_segments: dict[str, list[dict[str, Any]]] = defaultdict(list)
    referenced_push_ids: list[str] = []
    reviewed_business_push_ids: list[str] = []
    for index, segment in enumerate(segments, start=1):
        _validate_segment(
            segment,
            index=index,
            actions=actions,
            pushes=pushes,
            action_segments=action_segments,
            referenced_push_ids=referenced_push_ids,
            reviewed_business_push_ids=reviewed_business_push_ids,
            final=final,
            errors=errors,
        )
    _validate_epoch_continuity(
        segments,
        contract=contract,
        actions=actions,
        errors=errors,
    )
    _validate_segment_sequence(segments, final=final, errors=errors)
    _validate_terminal_cursors(segments, contract=contract, final=final, errors=errors)
    for action_id, action in actions.items():
        _validate_action_segment(
            action_id,
            action,
            mapped=action_segments.get(action_id, []),
            errors=errors,
        )
    _validate_push_coverage(
        pushes,
        referenced_push_ids=referenced_push_ids,
        reviewed_business_push_ids=reviewed_business_push_ids,
        errors=errors,
    )
    for push_id, push in pushes.items():
        _validate_push_bounds(push_id, push, segment_by_id=segment_by_id, errors=errors)
    return errors


def stream_summary(ledger: dict[str, Any], event_group_id: str) -> dict[str, Any]:
    """Return event-relevant action and inter-action stream facts."""
    pushes = [
        row
        for row in ledger.get("business_pushes", [])
        if isinstance(row, dict) and str(row.get("event_group_id", "")).strip() == event_group_id
    ]
    segments = _row_catalog(ledger.get("stream_segments"), "segment_id")
    return {
        "review_status": (ledger.get("stream_contract") or {}).get("status"),
        "observed_push_count": len(pushes),
        "inter_action_push_count": sum(
            segments.get(str(row.get("segment_id", "")), {}).get("kind") != "ACTION"
            for row in pushes
        ),
        "classifications": [
            {
                "push_id": row.get("push_id"),
                "event_name": row.get("event_name"),
                "classification": row.get("classification"),
                "reason": row.get("classification_reason"),
                "segment_kind": segments.get(str(row.get("segment_id", "")), {}).get("kind"),
            }
            for row in pushes
        ],
    }
