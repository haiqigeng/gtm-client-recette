"""Typed capture adapters and the single privacy-aware evidence write gate."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from client_side_rules import (
    QUERY_KEY_CATEGORIES,
    SENSITIVE_KEY_CATEGORIES,
    scan_sensitive_value,
)
from decode_browser_requests import decode_requests
from value_semantics import json_value_type, parse_iso_timestamp

from .constants import CAPTURE_KINDS, MACHINE_RECORD_KINDS, OPERATION_COUNTERS
from .state import (
    RunPaths,
    StateError,
    _append_machine,
    content_digest,
    file_digest,
    initialize_paths,
    load_plan,
)

TECHNICAL_EVENTS = {
    "gtm.js",
    "gtm.dom",
    "gtm.load",
    "gtm.init",
    "gtm.init_consent",
    "gtm.consentUpdate",
    "gtm.historyChange-v2",
    "gtm.triggerGroup",
}


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").casefold()).strip("_")


def _query_category(key: str) -> str | None:
    normalized = _normalized_key(key)
    for prefix in ("ep_", "up_"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    return QUERY_KEY_CATEGORIES.get(normalized)


def _key_category(key: str) -> str | None:
    return _query_category(key) or SENSITIVE_KEY_CATEGORIES.get(_normalized_key(key))


def _redaction(category: str, value: Any) -> dict[str, Any]:
    return {
        "__redacted__": category,
        "value_type": json_value_type(value),
        "present": value not in (None, "", [], {}),
    }


def _redact_url(value: str, findings: list[dict[str, Any]], path: str) -> Any:
    parsed = urlsplit(value)
    if not (parsed.scheme or parsed.query):
        return value
    pairs = []
    changed = False
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        category = _query_category(key)
        if category and item:
            pairs.append((key, f"<redacted:{category}>"))
            findings.append(
                {
                    "path": f"{path}?{key}",
                    "category": category,
                    "confidence": "confirmed",
                    "basis": "sensitive_query_key",
                    "status": "FAIL",
                    "redacted_value": f"<redacted:{category}>",
                    "value_fingerprint": "not-retained",
                }
            )
            changed = True
        else:
            pairs.append((key, item))
    if not changed:
        return value
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(pairs), parsed.fragment)
    )


def redact_for_persistence(
    value: Any,
    *,
    path: str = "$",
    key: str | None = None,
) -> tuple[Any, list[dict[str, Any]]]:
    """Return a safe copy and useful findings without retaining value fingerprints."""
    category = _key_category(key or "") if key else None
    if category and value not in (None, "", [], {}):
        finding = scan_sensitive_value({key: value}, root_path=path)
        if not finding:
            finding = [
                {
                    "path": path,
                    "category": category,
                    "confidence": "confirmed",
                    "basis": "sensitive_field_name",
                    "status": "FAIL",
                    "redacted_value": f"<redacted:{category}>",
                    "value_fingerprint": "not-retained",
                }
            ]
        for item in finding:
            item["value_fingerprint"] = "not-retained"
        return _redaction(category, value), finding

    if isinstance(value, dict):
        output: dict[str, Any] = {}
        findings: list[dict[str, Any]] = []
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}"
            safe, found = redact_for_persistence(child, path=child_path, key=str(child_key))
            output[str(child_key)] = safe
            findings.extend(found)
        return output, findings
    if isinstance(value, list):
        output = []
        findings = []
        for index, child in enumerate(value):
            safe, found = redact_for_persistence(child, path=f"{path}[{index}]", key=key)
            output.append(safe)
            findings.extend(found)
        return output, findings
    if not isinstance(value, str) or not value:
        return value, []

    url_safe = _redact_url(value, [], path)
    scanner_findings = scan_sensitive_value(value, root_path=path)
    confirmed = [
        finding
        for finding in scanner_findings
        if finding.get("confidence") == "confirmed"
        and finding.get("category") != "hashed_user_data"
    ]
    if confirmed:
        categories = sorted({str(finding["category"]) for finding in confirmed})
        for finding in confirmed:
            finding["value_fingerprint"] = "not-retained"
        return _redaction("+".join(categories), value), confirmed
    if url_safe != value:
        findings = scan_sensitive_value(value, root_path=path)
        for finding in findings:
            finding["value_fingerprint"] = "not-retained"
        return url_safe, findings
    return value, []


def _safe_artifact_name(adapter: str, digest: str, suffix: str = ".json") -> str:
    return f"{adapter}-{digest[:16]}{suffix}"


def _write_json_evidence(
    run_dir: Path | str,
    adapter: str,
    value: Any,
    *,
    quarantine: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
    paths = initialize_paths(run_dir)
    if quarantine:
        paths.quarantine.mkdir(exist_ok=True)
        digest = content_digest(value)
        target = paths.quarantine / _safe_artifact_name(adapter, digest)
        if not target.exists():
            target.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        return (
            {
                "path": str(target.relative_to(paths.root)).replace("\\", "/"),
                "sha256": file_digest(target),
                "quarantined": True,
            },
            [],
            None,
        )

    safe, findings = redact_for_persistence(value)
    digest = content_digest(safe)
    target = paths.evidence / _safe_artifact_name(adapter, digest)
    if not target.exists():
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(
            json.dumps(safe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, target)
    reference = {
        "path": str(target.relative_to(paths.root)).replace("\\", "/"),
        "sha256": file_digest(target),
        "quarantined": False,
    }
    return reference, findings, safe


def load_evidence(run_dir: Path | str, reference: dict[str, Any]) -> Any:
    paths = RunPaths.at(run_dir)
    relative = str(reference.get("path") or "")
    path = (paths.root / relative).resolve()
    allowed_root = paths.quarantine if reference.get("quarantined") else paths.evidence
    try:
        path.relative_to(allowed_root.resolve())
    except ValueError as error:
        raise StateError("Evidence reference escapes its allowed directory.") from error
    if not path.is_file() or file_digest(path) != reference.get("sha256"):
        raise StateError(f"Evidence is missing or digest-mismatched: {relative}")
    if reference.get("quarantined"):
        raise StateError("Quarantined raw evidence cannot be loaded into results.")
    if path.suffix.lower() in {".json", ".ndjson"}:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return path


def contains_truncation(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("__gtm_recette_type") in {"snapshot_truncated", "snapshot_failed"}:
            return True
        return any(contains_truncation(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_truncation(child) for child in value)
    return False


def classify_datalayer_argument(value: Any) -> str:
    if not isinstance(value, dict):
        return "NON_EVENT"
    event = value.get("event")
    if isinstance(event, str) and event:
        return (
            "TECHNICAL_EVENT"
            if event in TECHNICAL_EVENTS or event.startswith("gtm.")
            else "BUSINESS_EVENT"
        )
    return "STATE_UPDATE"


def _normalize_datalayer(value: Any, run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise StateError("DataLayer capture must be a recorder snapshot object.")
    captured_run = value.get("runId", value.get("run_id"))
    if captured_run not in (None, run_id):
        raise StateError("Recorder snapshot belongs to another run.")
    rows = value.get("records")
    if not isinstance(rows, list):
        raise StateError("Recorder snapshot has no records array.")
    capture_mode = str(value.get("captureMode", value.get("capture_mode", "unknown")))
    if capture_mode not in {"call_time", "late_snapshot", "preview_processed"}:
        raise StateError(
            "DataLayer capture_mode must be call_time, late_snapshot, or preview_processed."
        )
    seen: set[int] = set()
    summary = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise StateError(f"DataLayer record {index} is not an object.")
        call_index = row.get("callIndex", row.get("call_index"))
        if not isinstance(call_index, int) or call_index < 1 or call_index in seen:
            raise StateError("DataLayer call indexes must be unique positive integers.")
        seen.add(call_index)
        arguments = row.get("arguments")
        if not isinstance(arguments, list):
            raise StateError(f"DataLayer call {call_index} has no arguments array.")
        classifications = [classify_datalayer_argument(argument) for argument in arguments]
        events = [
            str(argument.get("event"))
            for argument in arguments
            if isinstance(argument, dict) and argument.get("event")
        ]
        summary.append(
            {
                "call_index": call_index,
                "timestamp": row.get("timestamp"),
                "action_id": row.get("actionId", row.get("action_id")),
                "document_id": row.get("documentId", row.get("document_id")),
                "frame_id": row.get("frameId", row.get("frame_id")),
                "layer_name": row.get("layerName", row.get("layer_name", "dataLayer")),
                "classifications": classifications,
                "events": events,
                "truncated": contains_truncation(arguments),
                "gtm_unique_event_ids": row.get(
                    "gtmUniqueEventIds", row.get("gtm_unique_event_ids", [])
                ),
            }
        )
    normalized = {**value, "runId": run_id, "records": rows}
    return normalized, {
        "call_count": len(rows),
        "calls": summary,
        "earliest_call_index": min(seen) if seen else None,
        "latest_call_index": max(seen) if seen else None,
        "recorder_integrity": value.get("integrity", []),
        "capture_mode": capture_mode,
        "action_id": value.get("action_id"),
        "document_start": value.get(
            "installedAtDocumentStart", value.get("installed_at_document_start")
        )
        is True,
        "complete": value.get("complete") is True,
    }


def _normalize_network(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        decoded = decode_requests(value)
    except ValueError as error:
        raise StateError(str(error)) from error
    rows = decoded["requests"]
    metadata = {
        key: value[key]
        for key in (
            "complete",
            "cursor_start",
            "cursor_end",
            "browser_context_id",
            "tab_id",
            "document_id",
            "frame_id",
            "action_id",
            "collection_mode",
            "parameter_capture_complete",
            "body_capture_complete",
        )
        if isinstance(value, dict) and key in value
    }
    return {**decoded, **metadata}, {
        "request_count": len(rows),
        "request_ids": [row.get("request_id") for row in rows],
        "endpoints": sorted({str(row.get("endpoint")) for row in rows}),
        **metadata,
    }


def _normalize_source(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("signals"), list):
        raise StateError("Direct-source capture must contain a signals array.")
    identities: set[str] = set()
    summary = []
    normalized_signals = []
    top_mode = str(value.get("capture_mode") or "").strip().casefold()
    forbidden_mechanisms = {
        "tag_assistant_message",
        "tag_assistant_data_layer",
        "preview_data_layer",
        "data_layer_state",
        "post_processed_state",
    }
    known_call_time = {
        "data_layer_push",
        "data_layer_api_call",
        "gtag_call",
        "direct_api_call",
        "vendor_queue_call",
    }
    for position, signal in enumerate(value["signals"], start=1):
        if not isinstance(signal, dict):
            raise StateError(f"Direct-source signal {position} is not an object.")
        identity = str(signal.get("signal_id") or f"signal-{position}")
        if identity in identities:
            raise StateError("Direct-source signal IDs must be unique within a capture.")
        identities.add(identity)
        mechanism = str(signal.get("mechanism") or "").strip().casefold()
        event_name = str(signal.get("event_name") or signal.get("name") or "").strip()
        if not mechanism:
            raise StateError("Every direct-source signal needs a mechanism.")
        if mechanism in forbidden_mechanisms:
            raise StateError(
                "Accumulated Tag Assistant/Data Layer state is not direct-source evidence; "
                "capture it as preview.data_layer_state."
            )
        mode = str(signal.get("capture_mode") or top_mode).strip().casefold()
        if not mode:
            mode = "call_time" if mechanism in known_call_time else ""
        if mode not in {"call_time", "preview_api_call"}:
            raise StateError("Direct-source capture_mode must be call_time or preview_api_call.")
        if (
            mode == "call_time"
            and mechanism not in known_call_time
            and signal.get("call_time_proven") is not True
        ):
            raise StateError(
                f"Direct-source mechanism {mechanism!r} needs explicit call_time_proven=true."
            )
        if mode == "preview_api_call":
            if mechanism != "tag_assistant_api_call":
                raise StateError(
                    "preview_api_call source evidence must use mechanism=tag_assistant_api_call."
                )
            if signal.get("api_call_complete") is not True:
                raise StateError(
                    "Tag Assistant API Call evidence must be fully expanded and complete."
                )
            if signal.get("preview_event_index") is None or not signal.get("preview_epoch"):
                raise StateError(
                    "Tag Assistant API Call evidence needs Preview event index and epoch identity."
                )
        if not event_name and signal.get("state_only") is not True:
            raise StateError(
                "A direct-source signal needs event_name unless it is explicitly state_only."
            )
        timestamp = signal.get("timestamp", signal.get("observed_at"))
        if timestamp is not None and parse_iso_timestamp(timestamp) is None:
            raise StateError(f"Direct-source signal {identity} has an invalid timestamp.")
        if "payload" not in signal and "value" not in signal:
            raise StateError(f"Direct-source signal {identity} needs payload or value evidence.")
        normalized_signal = {
            **signal,
            "signal_id": identity,
            "mechanism": mechanism,
            "event_name": event_name or None,
            "capture_mode": mode,
            "authoritative": True,
        }
        normalized_signals.append(normalized_signal)
        summary.append(
            {
                "signal_id": identity,
                "mechanism": mechanism,
                "event_name": event_name or None,
                "capture_mode": mode,
                "authoritative": True,
                "timestamp": timestamp,
                "action_id": signal.get("action_id"),
            }
        )
    window_complete = value.get("complete") is True and (
        all(signal.get("capture_mode") == "call_time" for signal in normalized_signals)
        or value.get("event_list_complete") is True
    )
    normalized = {**value, "signals": normalized_signals}
    return normalized, {
        "signal_count": len(summary),
        "signals": summary,
        "complete": value.get("complete") is True,
        "authoritative_complete": window_complete,
        "action_id": value.get("action_id"),
    }


def _normalize_preview(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict) or not isinstance(value.get("events"), list):
        raise StateError("Preview capture must contain an events array.")
    default_epoch = value.get("epoch")
    summary = []
    identities = set()
    for position, event in enumerate(value["events"], start=1):
        if not isinstance(event, dict):
            raise StateError(f"Preview event {position} is not an object.")
        index = event.get("index", event.get("event_index"))
        epoch = event.get("epoch", default_epoch)
        if index is None or not epoch:
            raise StateError("Every Preview event needs an index and connection epoch.")
        identity = (str(epoch), str(index))
        if identity in identities:
            raise StateError("Preview indexes must be unique within a connection epoch.")
        identities.add(identity)
        fired = event.get("fired_tags", [])
        not_fired = event.get("not_fired_tags", [])
        if not isinstance(fired, list) or not isinstance(not_fired, list):
            raise StateError("Preview tag summaries must be arrays.")
        api_call = event.get("api_call")
        if api_call is not None:
            if not isinstance(api_call, dict) or not isinstance(api_call.get("arguments"), list):
                raise StateError(
                    "Preview api_call must contain the fully expanded API Call arguments array."
                )
            if api_call.get("complete") is not True:
                raise StateError("Preview api_call evidence must be explicitly complete.")
        data_layer_state = event.get("data_layer_state")
        if data_layer_state is not None and not isinstance(data_layer_state, dict):
            raise StateError("Preview data_layer_state must be the accumulated state object.")
        summary.append(
            {
                "epoch": str(epoch),
                "index": index,
                "timestamp": event.get("timestamp"),
                "event_name": event.get("event_name", event.get("name")),
                "page_url": event.get("page_url"),
                "action_id": event.get("action_id"),
                "gtm_unique_event_id": event.get("gtm_unique_event_id"),
                "fired_tag_count": len(fired),
                "not_fired_tag_count": len(not_fired),
                "full_tag_summary": event.get("full_tag_summary") is True,
                "has_resolved_state": isinstance(event.get("resolved_state"), dict),
                "has_data_layer_state": isinstance(data_layer_state, dict),
                "has_api_call": isinstance(api_call, dict),
                "has_runtime_extract": isinstance(event.get("tags"), list),
                "history_stable": event.get("history_stable") is True,
                "bookmarked": event.get("bookmarked") is True,
                "completeness": event.get("completeness", {}),
            }
        )
    return value, {
        "event_count": len(summary),
        "events": summary,
        "complete": value.get("complete") is True,
        "action_id": value.get("action_id"),
        "preview_session_id": value.get("preview_session_id"),
        "container_ids": value.get("container_ids", []),
        "workspace_version": value.get("workspace_version"),
    }


def _normalize_page(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = value.get("states") if isinstance(value, dict) else None
    if rows is None and isinstance(value, dict):
        rows = [value]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise StateError("Page capture must be an object or contain a states array.")
    return {"states": rows}, {
        "state_count": len(rows),
        "states": [
            {
                "timestamp": row.get("timestamp", row.get("observed_at")),
                "action_id": row.get("action_id"),
                "phase": row.get("phase"),
                "url": row.get("url"),
                "status_code": row.get("status_code"),
                "page_kind": row.get("page_kind"),
                "completion": row.get("completion"),
                "container_ids": row.get("container_ids", []),
                "document_id": row.get("document_id"),
                "frame_id": row.get("frame_id"),
                "business_keys": sorted(row.get("business", {}))
                if isinstance(row.get("business"), dict)
                else [],
            }
            for row in rows
        ],
    }


def _normalize_object(value: Any, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise StateError(f"{label} capture must be an object.")
    observed = value.get("observed_at", value.get("timestamp"))
    if observed is not None and parse_iso_timestamp(observed) is None:
        raise StateError(f"{label} observed_at/timestamp is invalid.")
    summary_keys = (
        "action_id",
        "status",
        "settled",
        "settlement_reason",
        "recorder_attached",
        "network_active",
        "data_layer_cursor",
        "preview_epoch",
        "preview_event_index",
        "preview_reconnected",
        "previous_preview_epoch",
        "container_ids",
        "natural_container_ids",
        "tab_id",
        "browser_context_id",
        "browser_rebound",
        "profile_id",
        "preview_session_id",
        "document_id",
        "frame_id",
        "origin",
    )
    return value, {
        "observed_at": observed,
        **{key: value[key] for key in summary_keys if key in value},
    }


def _normalize_health(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized, summary = _normalize_object(value, "Health")
    operations = normalized.get("operations", {})
    if not isinstance(operations, dict):
        raise StateError("Health operations must be an object of non-negative counters.")
    unknown = sorted(set(operations) - set(OPERATION_COUNTERS))
    invalid = sorted(
        key
        for key, item in operations.items()
        if not isinstance(item, int) or isinstance(item, bool) or item < 0
    )
    if unknown or invalid:
        details = []
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        if invalid:
            details.append("invalid " + ", ".join(invalid))
        raise StateError("Health operation counters are invalid: " + "; ".join(details))
    return normalized, {**summary, "operations": operations}


def _normalize_capability(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise StateError("Capability capture must be an object.")
    surfaces = value.get("surfaces")
    if not isinstance(surfaces, dict):
        raise StateError("Capability capture needs a surfaces object.")
    allowed = {True, False, "unknown"}
    known_surfaces = {
        "stable_target_identity",
        "document_start_injection",
        "network_deltas",
        "network_post_data",
        "lifecycle_errors",
        "preview_events",
        "preview_tag_inventory",
        "preview_variables",
        "preview_consent",
    }
    required = {"stable_target_identity", "network_deltas", "preview_events"}
    missing = sorted(required - set(surfaces))
    unknown = sorted(set(surfaces) - known_surfaces)
    invalid = sorted(key for key, item in surfaces.items() if item not in allowed)
    if missing or unknown or invalid:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        if invalid:
            details.append("invalid " + ", ".join(invalid))
        raise StateError("Capability profile is incomplete: " + "; ".join(details))
    runtime = value.get("runtime")
    if not isinstance(runtime, dict):
        raise StateError("Capability capture needs a runtime self-check object.")
    provider = str(runtime.get("provider") or "").strip().casefold()
    if provider not in {"playwright_mcp", "existing_chromium"}:
        raise StateError("Capability runtime provider is unsupported.")
    if str(runtime.get("self_check") or "").upper() != "PASS":
        raise StateError("Browser runtime self-check did not pass; fail before opening an action.")
    if not str(runtime.get("browser_channel") or "").strip():
        raise StateError("Capability runtime needs a browser_channel.")
    if str(runtime.get("profile_mode") or "").casefold() not in {"persistent", "isolated"}:
        raise StateError("Capability runtime profile_mode must be persistent or isolated.")
    if not isinstance(runtime.get("headed"), bool):
        raise StateError("Capability runtime needs an explicit headed boolean.")
    if provider == "playwright_mcp" and not str(runtime.get("mcp_version") or "").strip():
        raise StateError("Playwright MCP runtime needs the verified MCP version.")
    normalized_surfaces = {key: surfaces.get(key, "unknown") for key in sorted(known_surfaces)}
    milestones = value.get("milestones", {})
    if not isinstance(milestones, dict):
        raise StateError("Capability milestones must be an object when supplied.")
    normalized = {
        **value,
        "browser_family": str(value.get("browser_family") or "chromium"),
        "runtime": {**runtime, "provider": provider},
        "surfaces": normalized_surfaces,
        "milestones": milestones,
    }
    return normalized, {
        "browser_family": normalized["browser_family"],
        "runtime": normalized["runtime"],
        "surfaces": normalized["surfaces"],
        "milestones": milestones,
        "observed_at": value.get("observed_at"),
    }


def _normalize_binding(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise StateError("Binding capture must be an object.")
    required = ("browser_context_id", "tab_id", "document_id", "origin")
    missing = [key for key in required if not str(value.get(key) or "").strip()]
    if missing:
        raise StateError("Binding capture is missing: " + ", ".join(missing))
    return value, {
        key: value.get(key)
        for key in (
            "browser_family",
            "browser_context_id",
            "tab_id",
            "document_id",
            "frame_id",
            "origin",
            "preview_session_id",
            "preview_epoch",
            "natural_container_ids",
            "active_container_ids",
            "override_container_ids",
            "workspace_version",
        )
        if key in value
    }


def _normalize_lifecycle(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise StateError("Lifecycle capture must be an object.")
    events = value.get("events", [])
    errors = value.get("errors", [])
    consent = value.get("consent_transitions", [])
    if not all(isinstance(rows, list) for rows in (events, errors, consent)):
        raise StateError("Lifecycle events, errors, and consent_transitions must be arrays.")
    return value, {
        "event_count": len(events),
        "error_count": len(errors),
        "consent_transition_count": len(consent),
        "complete": value.get("complete") is True,
        "action_id": value.get("action_id"),
        "document_id": value.get("document_id"),
    }


def _normalizer(adapter: str, value: Any, run_id: str) -> tuple[Any, dict[str, Any]]:
    if adapter == "capability":
        return _normalize_capability(value)
    if adapter == "binding":
        return _normalize_binding(value)
    if adapter == "datalayer":
        return _normalize_datalayer(value, run_id)
    if adapter == "network":
        return _normalize_network(value)
    if adapter == "source":
        return _normalize_source(value)
    if adapter == "preview":
        return _normalize_preview(value)
    if adapter == "page":
        return _normalize_page(value)
    if adapter == "lifecycle":
        return _normalize_lifecycle(value)
    if adapter == "health":
        return _normalize_health(value)
    raise StateError(f"Unsupported capture adapter: {adapter}")


def _annotate_network_findings(findings: list[dict[str, Any]], safe: Any) -> list[dict[str, Any]]:
    """Attach stable request identity without retaining any sensitive value."""
    requests = safe.get("requests", []) if isinstance(safe, dict) else []
    output = []
    for finding in findings:
        row = dict(finding)
        match = re.match(r"^\$\.requests\[(\d+)\]", str(row.get("path") or ""))
        if match:
            index = int(match.group(1))
            if index < len(requests) and isinstance(requests[index], dict):
                row["request_id"] = requests[index].get("request_id")
        output.append(row)
    return output


def capture_value(
    run_dir: Path | str,
    adapter: str,
    value: Any,
    *,
    source_id: str | None = None,
    quarantine: bool = False,
) -> dict[str, Any]:
    if adapter not in CAPTURE_KINDS:
        raise StateError(f"Unsupported JSON capture adapter: {adapter}")
    plan = load_plan(run_dir)
    if isinstance(value, dict) and value.get("run_id") not in (None, plan["run_id"]):
        raise StateError("Capture payload belongs to another run.")
    normalized, summary = _normalizer(adapter, value, str(plan["run_id"]))
    if isinstance(normalized, dict):
        normalized = {**normalized, "run_id": plan["run_id"]}
    reference, findings, safe = _write_json_evidence(
        run_dir, adapter, normalized, quarantine=quarantine
    )
    if adapter == "network" and safe is not None:
        findings = _annotate_network_findings(findings, safe)
    safe_digest = reference["sha256"]
    record_data = {
        "adapter": adapter,
        "evidence_ref": reference,
        "summary": summary if safe is not None else {"quarantined": True},
        "privacy_findings": findings,
    }
    key = source_id or safe_digest
    return _append_machine(
        run_dir,
        CAPTURE_KINDS[adapter],
        record_data,
        idempotency_key=f"capture:{adapter}:{key}",
    )


def validate_bundle_value(
    run_dir: Path | str,
    value: Any,
    *,
    required_adapters: set[str] | None = None,
) -> tuple[str, ...]:
    """Validate a coherent adapter bundle without writing evidence or stream state."""
    if not isinstance(value, dict):
        raise StateError("Capture bundle must be an object keyed by adapter name.")
    supported = (
        "capability",
        "binding",
        "health",
        "page",
        "datalayer",
        "source",
        "preview",
        "network",
        "lifecycle",
    )
    supplied = {str(name) for name in value}
    unexpected = supplied - set(supported)
    if unexpected:
        raise StateError(
            "Capture bundle contains unsupported adapters: " + ", ".join(sorted(unexpected))
        )
    missing = set(required_adapters or set()) - supplied
    if missing:
        raise StateError(
            "Capture bundle is missing required adapters: " + ", ".join(sorted(missing))
        )
    if not supplied:
        raise StateError("Capture bundle contains no supported adapter payload.")

    plan = load_plan(run_dir)
    for name in supported:
        if name not in value:
            continue
        payload = value[name]
        if isinstance(payload, dict) and payload.get("run_id") not in (None, plan["run_id"]):
            raise StateError(f"{name.capitalize()} capture belongs to another run.")
        _normalizer(name, payload, str(plan["run_id"]))

    return tuple(name for name in supported if name in value)


def capture_bundle_value(
    run_dir: Path | str,
    value: Any,
    *,
    source_id: str | None = None,
    required_adapters: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Validate a coherent adapter bundle before writing any stream record."""
    supported = validate_bundle_value(run_dir, value, required_adapters=required_adapters)
    bundle_identity = source_id or content_digest(value)
    return [
        capture_value(
            run_dir,
            name,
            value[name],
            source_id=f"{bundle_identity}:{name}",
        )
        for name in supported
        if name in value
    ]


def verify_evidence_references(run_dir: Path | str, records: list[dict[str, Any]]) -> list[str]:
    errors = []
    for record in records:
        if record.get("kind") not in MACHINE_RECORD_KINDS:
            continue
        reference = record.get("data", {}).get("evidence_ref")
        if not isinstance(reference, dict):
            errors.append(f"{record.get('record_id')}: missing evidence reference")
            continue
        if reference.get("quarantined"):
            errors.append(f"{record.get('record_id')}: unresolved quarantined evidence")
            continue
        try:
            load_evidence(run_dir, reference)
        except StateError as error:
            errors.append(f"{record.get('record_id')}: {error}")
    return errors
