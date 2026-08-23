"""Reconstruct one deterministic occurrence/evidence model from the append-only stream."""

from __future__ import annotations

from datetime import datetime
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
        "direct_signals": [],
        "preview_events": [],
        "requests": [],
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
    model["collections"][adapter] = {
        **prior,
        **summary,
        "complete": prior.get("complete") is True or summary.get("complete") is True,
        "record_id": evidence_ref,
    }
    for finding in data.get("privacy_findings", []):
        if isinstance(finding, dict):
            model["privacy_findings"].append({**finding, "evidence_ref": evidence_ref})


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
        if value.get("action_id") in (None, ""):
            value["action_id"] = _action_for_timestamp(model["actions"], row.get("timestamp"))
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
        action_id = signal.get("action_id") or _action_for_timestamp(
            model["actions"], signal.get("timestamp", signal.get("observed_at"))
        )
        source_by_id.setdefault(
            identity,
            {
                **signal,
                "occurrence_id": identity,
                "action_id": action_id,
                "capture_mode": "direct_source",
                "collection_complete": payload.get("complete") is True,
                "evidence_ref": evidence_ref,
                "evidence_refs": [evidence_ref],
            },
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
        action_id = event.get("action_id") or _action_for_timestamp(
            model["actions"], event.get("timestamp")
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
            value = _merge_preview(prior, value)
            value["evidence_refs"] = list(
                dict.fromkeys([*prior.get("evidence_refs", []), evidence_ref])
            )
        preview_by_id[identity] = value


def _ingest_network(
    model: dict[str, Any],
    payload: dict[str, Any],
    evidence_ref: Any,
    _record: dict[str, Any],
    request_by_id: dict[str, dict[str, Any]],
) -> None:
    complete = payload.get("complete") is True
    for position, request in enumerate(payload.get("requests", []), start=1):
        identity = str(request.get("request_id") or f"REQ:{evidence_ref}:{position}")
        action_id = request.get("action_id") or _action_for_timestamp(
            model["actions"], request.get("timestamp")
        )
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


def _ingest_lifecycle(
    model: dict[str, Any], payload: dict[str, Any], evidence_ref: Any, _record: dict[str, Any]
) -> None:
    action_id = payload.get("action_id")
    groups = (
        ("events", "lifecycle_events", "LIFE"),
        ("errors", "runtime_errors", "ERR"),
        ("consent_transitions", "consent_transitions", "CONSENT"),
    )
    for source_key, target_key, prefix in groups:
        for position, value in enumerate(payload.get(source_key, []), start=1):
            model[target_key].append(
                {
                    **value,
                    "action_id": value.get("action_id", action_id),
                    "evidence_ref": evidence_ref,
                    "occurrence_id": f"{prefix}:{evidence_ref}:{position}",
                }
            )


def _finalize_occurrences(
    model: dict[str, Any],
    source_by_id: dict[str, dict[str, Any]],
    preview_by_id: dict[str, dict[str, Any]],
    request_by_id: dict[str, dict[str, Any]],
) -> None:
    model["source_calls"] = sorted(
        [value for value in source_by_id.values() if value.get("capture_mode") != "direct_source"],
        key=lambda value: (
            _time_key(value.get("timestamp")),
            _safe_int(value.get("call_index")),
            value.get("occurrence_id"),
        ),
    )
    model["direct_signals"] = sorted(
        [value for value in source_by_id.values() if value.get("capture_mode") == "direct_source"],
        key=lambda value: (_time_key(value.get("timestamp")), value.get("occurrence_id")),
    )
    model["preview_events"] = sorted(
        preview_by_id.values(),
        key=lambda value: (str(value.get("epoch")), _safe_int(value.get("index"))),
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
        elif adapter == "source":
            _ingest_source(model, payload, evidence_ref, record, source_by_id)
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
        "direct_signals",
        "preview_events",
        "requests",
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


def source_event_names(model: dict[str, Any], action_id: str | None = None) -> list[str]:
    names = []
    for row in model["source_calls"]:
        if action_id is not None and row.get("action_id") != action_id:
            continue
        names.extend(row.get("events", []))
    for signal in model["direct_signals"]:
        if (action_id is None or signal.get("action_id") == action_id) and signal.get("event_name"):
            names.append(str(signal["event_name"]))
    return names
