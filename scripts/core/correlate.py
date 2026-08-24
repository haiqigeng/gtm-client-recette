"""Reconstruct one deterministic occurrence/evidence model from the append-only stream."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from value_semantics import parse_iso_timestamp

from .capture import classify_datalayer_argument, contains_truncation, load_evidence
from .protocols import decode_logical_sends


def _time(value: Any) -> datetime | None:
    return parse_iso_timestamp(value)


def _time_key(value: Any) -> tuple[int, str]:
    parsed = _time(value)
    return (0, parsed.isoformat()) if parsed else (1, str(value or ""))


def _safe_int(value: Any) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value or ""))


def action_windows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return action records with commit state without creating a second authority."""
    actions: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in records:
        kind = record.get("kind")
        data = record.get("data", {})
        action_id = str(data.get("action_id") or "")
        if kind == "ACTION_BEGIN" and action_id:
            if action_id not in actions:
                order.append(action_id)
            actions[action_id] = {
                **data,
                "action_id": action_id,
                "begin_record_id": record.get("record_id"),
                "began_at": data.get("began_at", record.get("recorded_at")),
                "status": "OPEN",
            }
        elif kind == "ACTION_COMMIT" and action_id in actions:
            actions[action_id].update(
                {
                    "commit_record_id": record.get("record_id"),
                    "committed_at": data.get("committed_at", record.get("recorded_at")),
                    "outcome_may_have_occurred": data.get("outcome_may_have_occurred"),
                    "operation_deltas": data.get("operation_deltas", {}),
                    "execution_violations": data.get("execution_violations", []),
                    "status": "COMMITTED",
                }
            )
    return [actions[action_id] for action_id in order]


def capture_payload(run_dir: Any, record: dict[str, Any]) -> Any:
    reference = record.get("data", {}).get("evidence_ref")
    return load_evidence(run_dir, reference) if isinstance(reference, dict) else None


def _action_for_timestamp(actions: list[dict[str, Any]], value: Any) -> str | None:
    timestamp = _time(value)
    if timestamp is None:
        return None
    matches = []
    for action in actions:
        start = _time(action.get("began_at"))
        end = _time(action.get("committed_at"))
        if start and timestamp >= start and (end is None or timestamp <= end):
            matches.append(action["action_id"])
    return matches[0] if len(matches) == 1 else None


def _attributed_action(
    model: dict[str, Any], requested: Any, timestamp: Any, *, identity: str
) -> str | None:
    requested_id = str(requested or "")
    if not requested_id:
        return _action_for_timestamp(model["actions"], timestamp)
    known = any(action.get("action_id") == requested_id for action in model["actions"])
    if not known:
        model["ambiguous"].append(
            {"kind": "unknown_action_attribution", "identity": identity, "action_id": requested_id}
        )
        return None
    action = next(row for row in model["actions"] if row.get("action_id") == requested_id)
    observed = _time(timestamp)
    began = _time(action.get("began_at"))
    if observed is not None and began is not None and observed < began - timedelta(seconds=2):
        model["ambiguous"].append(
            {
                "kind": "stale_action_attribution",
                "identity": identity,
                "action_id": requested_id,
                "observed_at": timestamp,
                "action_began_at": action.get("began_at"),
            }
        )
        return None
    # A request can settle after commit, so only impossible pre-action timestamps
    # override an otherwise valid collector action marker.
    return requested_id


def _tag_identity(value: Any) -> str:
    if not isinstance(value, dict):
        return str(value)
    return str(
        value.get("tag_id")
        or value.get("id")
        or value.get("tag_name")
        or value.get("name")
        or value
    )


def _merge_tag_rows(left: list[Any], right: list[Any]) -> list[Any]:
    output: dict[str, Any] = {}
    for value in [*left, *right]:
        identity = _tag_identity(value)
        if identity in output and isinstance(output[identity], dict) and isinstance(value, dict):
            output[identity] = {**output[identity], **value}
        else:
            output[identity] = value
    return list(output.values())


def _merge_preview(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = {**left, **right}
    for key in ("fired_tags", "not_fired_tags", "tags"):
        merged[key] = _merge_tag_rows(
            left.get(key, []) if isinstance(left.get(key), list) else [],
            right.get(key, []) if isinstance(right.get(key), list) else [],
        )
    for key in ("resolved_state", "consent", "completeness"):
        if isinstance(left.get(key), dict) or isinstance(right.get(key), dict):
            merged[key] = {
                **(left.get(key, {}) if isinstance(left.get(key), dict) else {}),
                **(right.get(key, {}) if isinstance(right.get(key), dict) else {}),
            }
    return merged


def _merge_request(left: dict[str, Any], right: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Merge normal request lifecycle updates; flag only incompatible reuse of an ID."""
    incompatible = any(
        left.get(key) not in (None, "")
        and right.get(key) not in (None, "")
        and left.get(key) != right.get(key)
        for key in ("endpoint", "request_url", "action_id", "document_id")
    )
    merged = {
        **left,
        **{key: value for key, value in right.items() if value not in (None, "", [], {})},
    }
    merged["tag_ids"] = list(dict.fromkeys([*left.get("tag_ids", []), *right.get("tag_ids", [])]))
    merged["evidence_refs"] = list(
        dict.fromkeys(
            [
                *left.get("evidence_refs", [left.get("evidence_ref")]),
                *right.get("evidence_refs", [right.get("evidence_ref")]),
            ]
        )
    )
    merged["evidence_refs"] = [value for value in merged["evidence_refs"] if value]
    return merged, incompatible


def _empty_model(plan: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "run_id": plan.get("run_id"),
        "actions": actions,
        "capability": None,
        "binding": None,
        "bindings": [],
        "health": [],
        "pages": [],
        "source_calls": [],
        "source_windows": [],
        "direct_signals": [],
        "preview_events": [],
        "preview_windows": [],
        "requests": [],
        "network_windows": [],
        "logical_sends": [],
        "lifecycle_events": [],
        "runtime_errors": [],
        "consent_transitions": [],
        "acquisition_contexts": [],
        "privacy_findings": [],
        "collections": {},
        "ambiguous": [],
    }


def _record_collection(
    model: dict[str, Any], adapter: str, data: dict[str, Any], evidence_ref: Any
) -> None:
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    prior = model["collections"].get(adapter, {})
    captures = [*prior.get("captures", []), {**summary, "record_id": evidence_ref}]
    model["collections"][adapter] = {
        **prior,
        **summary,
        "complete": prior.get("complete") is True or summary.get("complete") is True,
        "authoritative_complete": prior.get("authoritative_complete") is True
        or summary.get("authoritative_complete") is True,
        "capture_modes": sorted(
            {
                str(row.get("capture_mode"))
                for row in captures
                if row.get("capture_mode") not in (None, "")
            }
        ),
        "captures": captures,
        "record_id": evidence_ref,
    }
    for finding in data.get("privacy_findings", []):
        if isinstance(finding, dict):
            model["privacy_findings"].append(
                {**finding, "adapter": adapter, "evidence_ref": evidence_ref}
            )


def _ingest_capability(
    model: dict[str, Any], payload: dict[str, Any], evidence_ref: Any, _record: dict[str, Any]
) -> None:
    model["capability"] = {**payload, "evidence_ref": evidence_ref}


def _ingest_binding(
    model: dict[str, Any], payload: dict[str, Any], evidence_ref: Any, record: dict[str, Any]
) -> None:
    binding = {**payload, "evidence_ref": evidence_ref, "record_seq": record.get("seq")}
    model["binding"] = binding
    model["bindings"].append(binding)


def _ingest_health(
    model: dict[str, Any], payload: dict[str, Any], evidence_ref: Any, _record: dict[str, Any]
) -> None:
    model["health"].append({**payload, "evidence_ref": evidence_ref})


def _ingest_page(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
) -> None:
    for position, state in enumerate(payload.get("states", []), start=1):
        action_id = state.get("action_id") or _action_for_timestamp(
            model["actions"], state.get("timestamp", state.get("observed_at"))
        )
        model["pages"].append(
            {
                **state,
                "action_id": action_id,
                "occurrence_id": (
                    f"PAGE:{state.get('document_id') or 'unknown'}:"
                    f"{action_id or 'unbound'}:{state.get('phase') or position}"
                ),
                "evidence_ref": evidence_ref,
            }
        )


def _datalayer_value(
    payload: dict[str, Any], row: dict[str, Any], evidence_ref: Any
) -> tuple[str, dict[str, Any]]:
    mode = str(payload.get("captureMode", payload.get("capture_mode", "unknown")))
    document_start = (
        payload.get("installedAtDocumentStart", payload.get("installed_at_document_start")) is True
    )
    call_index = row.get("callIndex", row.get("call_index"))
    document_id = row.get("documentId", row.get("document_id")) or payload.get("document_id")
    identity = (
        f"DL:{document_id or 'unknown'}:"
        f"{row.get('layerName', row.get('layer_name', 'dataLayer'))}:{call_index}"
    )
    arguments = row.get("arguments", [])
    action_id = row.get("actionId", row.get("action_id"))
    value = {
        **row,
        "occurrence_id": identity,
        "call_index": call_index,
        "document_id": document_id,
        "action_id": action_id,
        "capture_mode": mode,
        "document_start": document_start,
        "collection_complete": payload.get("complete") is True,
        "arguments": arguments,
        "truncated": contains_truncation(arguments),
        "classifications": [classify_datalayer_argument(item) for item in arguments],
        "events": [
            str(item.get("event"))
            for item in arguments
            if isinstance(item, dict) and item.get("event")
        ],
        "evidence_ref": evidence_ref,
        "evidence_refs": [evidence_ref],
    }
    return identity, value


def _ingest_datalayer(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    for row in payload.get("records", []):
        identity, value = _datalayer_value(payload, row, evidence_ref)
        value["action_id"] = _attributed_action(
            model,
            value.get("action_id"),
            row.get("timestamp"),
            identity=identity,
        )
        prior = source_by_id.get(identity)
        if prior is None:
            source_by_id[identity] = value
        elif prior.get("arguments") != value.get("arguments") or prior.get(
            "document_id"
        ) != value.get("document_id"):
            model["ambiguous"].append(
                {
                    "kind": "source_identity_conflict",
                    "identity": identity,
                    "action_id": value.get("action_id") or prior.get("action_id"),
                }
            )
        else:
            prior["collection_complete"] = (
                prior.get("collection_complete") is True or value.get("collection_complete") is True
            )
            prior["document_start"] = (
                prior.get("document_start") is True or value.get("document_start") is True
            )
            prior["evidence_refs"] = list(
                dict.fromkeys([*prior.get("evidence_refs", []), evidence_ref])
            )


def _ingest_source(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
) -> None:
    for position, signal in enumerate(payload.get("signals", []), start=1):
        identity = str(signal.get("signal_id") or f"SOURCE:{evidence_ref}:{position}")
        action_id = _attributed_action(
            model,
            signal.get("action_id"),
            signal.get("timestamp", signal.get("observed_at")),
            identity=identity,
        )
        value = {
            **signal,
            "occurrence_id": identity,
            "action_id": action_id,
            "capture_mode": signal.get("capture_mode"),
            "direct_signal": True,
            "authoritative": signal.get("authoritative") is True,
            "collection_complete": payload.get("complete") is True,
            "evidence_ref": evidence_ref,
            "evidence_refs": [evidence_ref],
        }
        prior = source_by_id.get(identity)
        if prior is None:
            source_by_id[identity] = value
        elif any(
            prior.get(key) != value.get(key)
            for key in ("payload", "value", "event_name", "capture_mode", "action_id")
        ):
            model["ambiguous"].append(
                {
                    "kind": "direct_source_identity_conflict",
                    "identity": identity,
                    "action_id": action_id or prior.get("action_id"),
                }
            )
        else:
            prior["collection_complete"] = (
                prior.get("collection_complete") is True or value.get("collection_complete") is True
            )
            prior["evidence_refs"] = list(
                dict.fromkeys([*prior.get("evidence_refs", []), evidence_ref])
            )


def _ingest_preview(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
    preview_by_id: dict[str, dict[str, Any]],
) -> None:
    default_epoch = payload.get("epoch")
    for event in payload.get("events", []):
        epoch = str(event.get("epoch", default_epoch))
        index = event.get("index", event.get("event_index"))
        identity = f"PV:{epoch}:{index}"
        action_id = _attributed_action(
            model,
            event.get("action_id"),
            event.get("timestamp"),
            identity=identity,
        )
        value = {
            **event,
            "occurrence_id": identity,
            "epoch": epoch,
            "index": index,
            "action_id": action_id,
            "preview_session_id": payload.get("preview_session_id"),
            "container_ids": event.get("container_ids", payload.get("container_ids", [])),
            "workspace_version": event.get("workspace_version", payload.get("workspace_version")),
            "evidence_refs": [evidence_ref],
        }
        if identity in preview_by_id:
            prior = preview_by_id[identity]
            incompatible = any(
                prior.get(key) not in (None, "", [], {})
                and value.get(key) not in (None, "", [], {})
                and prior.get(key) != value.get(key)
                for key in (
                    "event_name",
                    "gtm_unique_event_id",
                    "action_id",
                    "preview_session_id",
                    "container_ids",
                )
            )
            if incompatible:
                model["ambiguous"].append(
                    {
                        "kind": "preview_identity_conflict",
                        "identity": identity,
                        "action_id": value.get("action_id") or prior.get("action_id"),
                    }
                )
                prior["evidence_refs"] = list(
                    dict.fromkeys([*prior.get("evidence_refs", []), evidence_ref])
                )
                continue
            value = _merge_preview(prior, value)
            value["evidence_refs"] = list(
                dict.fromkeys([*prior.get("evidence_refs", []), evidence_ref])
            )
        preview_by_id[identity] = value
    action_ids = {
        value.get("action_id")
        for value in preview_by_id.values()
        if value.get("evidence_ref") == evidence_ref
        or evidence_ref in value.get("evidence_refs", [])
        if value.get("action_id")
    }
    model["preview_windows"].append(
        {
            "action_id": (
                next(iter(action_ids)) if len(action_ids) == 1 else payload.get("action_id")
            ),
            "complete": payload.get("complete") is True,
            "event_list_complete": all(
                event.get("history_stable") is True
                or event.get("completeness", {}).get("event_list") is True
                for event in payload.get("events", [])
            ),
            "evidence_ref": evidence_ref,
        }
    )


def _ingest_network(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
    request_by_id: dict[str, dict[str, Any]],
) -> None:
    complete = payload.get("complete") is True
    attributed_actions: set[str] = set()
    for position, request in enumerate(payload.get("requests", []), start=1):
        identity = str(request.get("request_id") or f"REQ:{evidence_ref}:{position}")
        action_id = _attributed_action(
            model,
            request.get("action_id"),
            request.get("timestamp"),
            identity=identity,
        )
        if action_id:
            attributed_actions.add(action_id)
        value = {
            **request,
            "request_id": identity,
            "action_id": action_id,
            "collection_complete": complete,
            "evidence_ref": evidence_ref,
            "evidence_refs": [evidence_ref],
        }
        if identity not in request_by_id:
            request_by_id[identity] = value
            continue
        merged, incompatible = _merge_request(request_by_id[identity], value)
        request_by_id[identity] = merged
        if incompatible:
            model["ambiguous"].append(
                {
                    "kind": "request_identity_conflict",
                    "identity": identity,
                    "action_id": value.get("action_id") or merged.get("action_id"),
                }
            )
    window_action = payload.get("action_id")
    if not window_action and len(attributed_actions) == 1:
        window_action = next(iter(attributed_actions))
    model["network_windows"].append(
        {
            "action_id": window_action,
            "complete": complete,
            "parameter_capture_complete": payload.get("parameter_capture_complete") is True,
            "body_capture_complete": payload.get("body_capture_complete") is True,
            "evidence_ref": evidence_ref,
        }
    )


def _ingest_lifecycle(
    model: dict[str, Any], payload: dict[str, Any], evidence_ref: Any, _record: dict[str, Any]
) -> None:
    groups = (
        ("events", "lifecycle_events", "LIFE"),
        ("errors", "runtime_errors", "ERR"),
        ("consent_transitions", "consent_transitions", "CONSENT"),
    )
    for source_key, target_key, prefix in groups:
        for position, value in enumerate(payload.get(source_key, []), start=1):
            identity = f"{prefix}:{evidence_ref}:{position}"
            attributed = _attributed_action(
                model,
                value.get("action_id"),
                value.get("timestamp", value.get("observed_at")),
                identity=identity,
            )
            model[target_key].append(
                {
                    **value,
                    "action_id": attributed,
                    "evidence_ref": evidence_ref,
                    "occurrence_id": identity,
                }
            )


def _finalize_occurrences(
    model: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
    preview_by_id: dict[str, dict[str, Any]],
    request_by_id: dict[str, dict[str, Any]],
) -> None:
    model["source_calls"] = sorted(
        [value for value in source_by_id.values() if value.get("direct_signal") is not True],
        key=lambda value: (
            _time_key(value.get("timestamp")),
            _safe_int(value.get("call_index")),
            value.get("occurrence_id"),
        ),
    )
    model["direct_signals"] = sorted(
        [value for value in source_by_id.values() if value.get("direct_signal") is True],
        key=lambda value: (_time_key(value.get("timestamp")), value.get("occurrence_id")),
    )
    model["preview_events"] = sorted(
        preview_by_id.values(),
        key=lambda value: (str(value.get("epoch")), _safe_int(value.get("index"))),
    )
    direct_actions = {
        row.get("action_id")
        for row in [*model["source_calls"], *model["direct_signals"]]
        if row.get("action_id")
        and (
            (row.get("capture_mode") == "call_time" and row.get("document_start") is True)
            or row.get("authoritative") is True
        )
    }
    for row in model["preview_events"]:
        api_call = row.get("api_call")
        action_id = row.get("action_id")
        if (
            action_id in direct_actions
            or not isinstance(api_call, dict)
            or api_call.get("complete") is not True
        ):
            continue
        arguments = api_call.get("arguments", [])
        if not isinstance(arguments, list):
            continue
        model["source_calls"].append(
            {
                "occurrence_id": f"PVAPI:{row.get('epoch')}:{row.get('index')}",
                "call_index": row.get("index"),
                "timestamp": row.get("timestamp"),
                "action_id": action_id,
                "document_id": row.get("document_id"),
                "capture_mode": "preview_api_call",
                "authoritative": True,
                "collection_complete": row.get("history_stable") is True
                or row.get("completeness", {}).get("event_list") is True,
                "arguments": arguments,
                "truncated": contains_truncation(arguments),
                "classifications": [
                    classify_datalayer_argument(argument) for argument in arguments
                ],
                "events": [
                    str(argument.get("event"))
                    for argument in arguments
                    if isinstance(argument, dict) and argument.get("event")
                ],
                "evidence_ref": row.get("evidence_refs", [None])[-1],
                "evidence_refs": row.get("evidence_refs", []),
                "preview_epoch": row.get("epoch"),
                "preview_event_index": row.get("index"),
            }
        )
    model["source_calls"].sort(
        key=lambda value: (
            _time_key(value.get("timestamp")),
            _safe_int(value.get("call_index")),
            value.get("occurrence_id"),
        )
    )
    model["requests"] = sorted(
        request_by_id.values(),
        key=lambda value: (_time_key(value.get("timestamp")), value.get("request_id")),
    )
    for request in model["requests"]:
        for send in decode_logical_sends(request):
            model["logical_sends"].append(
                {
                    **send,
                    "response_status": request.get("response_status"),
                    "failure_reason": request.get("failure_reason"),
                    "evidence_ref": request.get("evidence_ref"),
                    "evidence_refs": request.get("evidence_refs", []),
                }
            )


def build_model(
    run_dir: Any, plan: dict[str, Any], records: list[dict[str, Any]]
) -> dict[str, Any]:
    model = _empty_model(plan, action_windows(records))
    preview_by_id: dict[str, dict[str, Any]] = {}
    source_by_id: dict[str, dict[str, Any]] = {}
    request_by_id: dict[str, dict[str, Any]] = {}
    simple_handlers = {
        "capability": _ingest_capability,
        "binding": _ingest_binding,
        "health": _ingest_health,
        "page": _ingest_page,
        "lifecycle": _ingest_lifecycle,
    }

    for record in records:
        kind = str(record.get("kind") or "")
        if kind == "ACQUISITION_CONTEXT":
            model["acquisition_contexts"].append(
                {**record.get("data", {}), "record_id": record.get("record_id")}
            )
            continue
        if not kind.startswith("CAPTURE_"):
            continue
        data = record.get("data", {})
        adapter = str(data.get("adapter") or kind.removeprefix("CAPTURE_").casefold())
        payload = capture_payload(run_dir, record)
        if payload is None:
            continue
        evidence_ref = record.get("record_id")
        _record_collection(model, adapter, data, evidence_ref)
        if adapter == "datalayer":
            _ingest_datalayer(model, payload, evidence_ref, record, source_by_id)
            model["source_windows"].append(
                {
                    "action_id": payload.get("action_id"),
                    "capture_mode": payload.get("captureMode", payload.get("capture_mode")),
                    "document_start": payload.get(
                        "installedAtDocumentStart",
                        payload.get("installed_at_document_start"),
                    )
                    is True,
                    "complete": payload.get("complete") is True,
                    "truncated": contains_truncation(payload.get("records", [])),
                    "evidence_ref": evidence_ref,
                }
            )
        elif adapter == "source":
            _ingest_source(model, payload, evidence_ref, record, source_by_id)
            signal_modes = {signal.get("capture_mode") for signal in payload.get("signals", [])}
            model["source_windows"].append(
                {
                    "action_id": payload.get("action_id"),
                    "capture_modes": sorted(str(mode) for mode in signal_modes if mode),
                    "authoritative": all(
                        signal.get("authoritative") is True for signal in payload.get("signals", [])
                    ),
                    "complete": payload.get("complete") is True,
                    "event_list_complete": payload.get("event_list_complete") is True,
                    "authoritative_complete": payload.get("complete") is True
                    and (
                        signal_modes == {"call_time"} or payload.get("event_list_complete") is True
                    ),
                    "evidence_ref": evidence_ref,
                }
            )
        elif adapter == "preview":
            _ingest_preview(model, payload, evidence_ref, record, preview_by_id)
        elif adapter == "network":
            _ingest_network(model, payload, evidence_ref, record, request_by_id)
        elif handler := simple_handlers.get(adapter):
            handler(model, payload, evidence_ref, record)

    _finalize_occurrences(model, source_by_id, preview_by_id, request_by_id)
    return model


def action_evidence(model: dict[str, Any], action_id: str) -> dict[str, list[dict[str, Any]]]:
    attributable = (
        "pages",
        "health",
        "source_calls",
        "source_windows",
        "direct_signals",
        "preview_events",
        "preview_windows",
        "requests",
        "network_windows",
        "logical_sends",
        "lifecycle_events",
        "runtime_errors",
        "consent_transitions",
        "acquisition_contexts",
    )
    return {
        key: [row for row in model[key] if row.get("action_id") == action_id]
        for key in attributable
    }


def source_event_names(
    model: dict[str, Any], action_id: str | None = None, *, authoritative_only: bool = False
) -> list[str]:
    names = []
    for row in model["source_calls"]:
        if action_id is not None and row.get("action_id") != action_id:
            continue
        if authoritative_only and not (
            (row.get("capture_mode") == "call_time" and row.get("document_start") is True)
            or (row.get("capture_mode") == "preview_api_call" and row.get("authoritative") is True)
        ):
            continue
        names.extend(row.get("events", []))
    for signal in model["direct_signals"]:
        if authoritative_only and signal.get("authoritative") is not True:
            continue
        if (action_id is None or signal.get("action_id") == action_id) and signal.get("event_name"):
            names.append(str(signal["event_name"]))
    return names
