#!/usr/bin/env python3
"""Validate directly captured browser, Preview, and network runtime state."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from value_semantics import parse_iso_timestamp

RUNTIME_CHECK_PHASES = {"before_action", "resume", "after_action", "interrupted_action"}
RUNTIME_CAPTURE_SOURCES = {
    "browser_connector_runtime_probe",
    "playwright_runtime_probe",
}
MAX_CAPTURE_AGE_SECONDS = 300
MAX_CLOCK_SKEW_SECONDS = 5
MAX_EVIDENCE_SKEW_SECONDS = 5
READINESS_TRUE_FIELDS = (
    "preview_connected",
    "target_interactive",
    "target_uncovered",
    "lifecycle_observed",
    "stream_quiet",
    "network_capture_active",
)
BOOLEAN_FIELDS = set(READINESS_TRUE_FIELDS)
PAGE_MATCH_MODES = {"exact", "same_origin_spa"}
INTERRUPTION_REASONS = {
    "browser_crashed",
    "network_capture_lost",
    "preview_disconnected",
    "surface_unavailable",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_timestamp(value: Any) -> bool:
    return parse_iso_timestamp(value) is not None


def _origin(url: Any) -> str | None:
    if not _nonempty(url):
        return None
    parsed = urlparse(str(url))
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _comparable_url(url: str) -> tuple[str, str, str, str]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    return parsed.scheme, parsed.netloc, path.rstrip("/") or "/", parsed.query


def expected_container_contract(
    results: dict[str, Any],
    case: dict[str, Any],
) -> list[dict[str, str]]:
    """Return the exact case container/workspace contract in stable order."""
    run = results.get("run", {}) if isinstance(results.get("run"), dict) else {}
    configured = [row for row in run.get("containers", []) if isinstance(row, dict)]
    if not configured and _nonempty(run.get("container_id")):
        configured = [
            {
                "container_id": run.get("container_id"),
                "workspace": run.get("workspace"),
            }
        ]
    case_ids = {str(value).strip() for value in case.get("container_ids", []) if str(value).strip()}
    selected = [
        {
            "container_id": str(row.get("container_id", "")).strip(),
            "workspace": str(row.get("workspace", "")).strip(),
        }
        for row in configured
        if str(row.get("container_id", "")).strip() in case_ids
    ]
    return sorted(selected, key=lambda row: (row["container_id"], row["workspace"]))


def _snapshot_containers(value: Any, errors: list[str]) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        errors.append("runtime snapshot containers must be a non-empty array")
        return []
    output: list[dict[str, str]] = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"runtime snapshot container {index} must be an object")
            continue
        container_id = str(row.get("container_id", "")).strip()
        workspace = str(row.get("workspace", "")).strip()
        if not container_id or not workspace:
            errors.append(f"runtime snapshot container {index} requires container_id and workspace")
            continue
        output.append({"container_id": container_id, "workspace": workspace})
    normalized = sorted(output, key=lambda row: (row["container_id"], row["workspace"]))
    if len({(row["container_id"], row["workspace"]) for row in normalized}) != len(normalized):
        errors.append("runtime snapshot containers contain duplicates")
    return normalized


def runtime_snapshot_errors(
    snapshot: dict[str, Any],
    *,
    phase: str,
    action_id: str,
    case: dict[str, Any],
    ledger: dict[str, Any],
    results: dict[str, Any],
    expected_connection_epoch: int | None = None,
    recorded_at: str | None = None,
    action_timestamp: str | None = None,
) -> list[str]:
    """Return deterministic errors for one direct runtime-state capture."""
    errors: list[str] = []
    if phase not in RUNTIME_CHECK_PHASES:
        return [f"unsupported runtime-check phase: {phase}"]
    for field_name in (
        "check_id",
        "captured_at",
        "capture_source",
        "browser_context_id",
        "gtm_workspace_surface_id",
        "tag_assistant_surface_id",
        "website_surface_id",
        "website_url",
        "selected_page_url",
    ):
        if not _nonempty(snapshot.get(field_name)):
            errors.append(f"runtime snapshot requires non-empty {field_name}")
    if not _iso_timestamp(snapshot.get("captured_at")):
        errors.append("runtime snapshot captured_at must be ISO 8601 with timezone")
    capture_source = str(snapshot.get("capture_source", "")).strip()
    if capture_source and capture_source not in RUNTIME_CAPTURE_SOURCES:
        errors.append(
            "runtime snapshot capture_source must identify a supported browser runtime probe"
        )
    captured_at = parse_iso_timestamp(snapshot.get("captured_at"))
    recorded_time = parse_iso_timestamp(recorded_at or snapshot.get("recorded_at"))
    if recorded_at is not None and recorded_time is None:
        errors.append("runtime check recorded_at must be ISO 8601 with timezone")
    if captured_at is not None and recorded_time is not None:
        age_seconds = (recorded_time - captured_at).total_seconds()
        if age_seconds < -MAX_CLOCK_SKEW_SECONDS:
            errors.append("runtime snapshot captured_at cannot be later than recorded_at")
        elif age_seconds > MAX_CAPTURE_AGE_SECONDS:
            errors.append(
                "runtime snapshot is stale; capture it immediately before recording the check"
            )
    action_time = parse_iso_timestamp(action_timestamp)
    if action_timestamp is not None and action_time is None:
        errors.append("runtime action_timestamp must be ISO 8601 with timezone")
    if captured_at is not None and action_time is not None:
        delta_seconds = (captured_at - action_time).total_seconds()
        if phase == "before_action" and delta_seconds > MAX_CLOCK_SKEW_SECONDS:
            errors.append("before-action runtime capture must not follow the action timestamp")
        if (
            phase in {"resume", "after_action", "interrupted_action"}
            and delta_seconds < -MAX_CLOCK_SKEW_SECONDS
        ):
            errors.append(f"{phase} runtime capture must not precede the action timestamp")
    for field_name in BOOLEAN_FIELDS:
        if not isinstance(snapshot.get(field_name), bool):
            errors.append(f"runtime snapshot {field_name} must be boolean")
    for field_name in ("preview_event_cursor", "network_request_cursor"):
        value = snapshot.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"runtime snapshot {field_name} must be a non-negative integer")
    connection_epoch = snapshot.get("connection_epoch")
    if (
        not isinstance(connection_epoch, int)
        or isinstance(connection_epoch, bool)
        or connection_epoch < 1
    ):
        errors.append("runtime snapshot connection_epoch must be a positive integer")
    elif connection_epoch != (
        ledger.get("connection_epoch", 1)
        if expected_connection_epoch is None
        else expected_connection_epoch
    ):
        errors.append("runtime snapshot connection_epoch differs from the action epoch")

    refs = snapshot.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(row) for row in refs):
        errors.append("runtime snapshot evidence_ids must be a non-empty string array")
    elif len(set(refs)) != len(refs):
        errors.append("runtime snapshot evidence_ids contain duplicates")

    surfaces = ledger.get("surfaces", {})
    if not isinstance(surfaces, dict):
        errors.append("runtime snapshot cannot resolve an invalid surface registry")
        surfaces = {}
    surface_contract = {
        "gtm_workspace_surface_id": "gtm_workspace",
        "tag_assistant_surface_id": "tag_assistant",
        "website_surface_id": "website",
    }
    for field_name, role in surface_contract.items():
        surface_id = str(snapshot.get(field_name, ""))
        surface = surfaces.get(surface_id)
        if not isinstance(surface, dict) or surface.get("role") != role:
            errors.append(f"runtime snapshot {field_name} does not resolve a {role} surface")
    assistant = surfaces.get(str(snapshot.get("tag_assistant_surface_id", "")), {})
    if (
        phase != "interrupted_action"
        and isinstance(assistant, dict)
        and assistant.get("connected") is not True
    ):
        errors.append("runtime snapshot Tag Assistant surface is not recorded as connected")

    approved_origins = set(ledger.get("approved_origins", []))
    website_origin = _origin(snapshot.get("website_url"))
    selected_origin = _origin(snapshot.get("selected_page_url"))
    case_origin = _origin(case.get("url"))
    if website_origin is None or website_origin not in approved_origins:
        errors.append("runtime snapshot website_url is outside the approved origins")
    if selected_origin != website_origin:
        errors.append("runtime snapshot selected Tag Assistant page has the wrong origin")
    if case_origin != website_origin:
        errors.append("runtime snapshot website origin differs from the interaction case")
    page_match_mode = str(snapshot.get("page_match_mode", "exact")).strip()
    if page_match_mode not in PAGE_MATCH_MODES:
        errors.append("runtime snapshot page_match_mode must be exact or same_origin_spa")
    urls_differ = (
        website_origin
        and selected_origin
        and _nonempty(snapshot.get("website_url"))
        and _nonempty(snapshot.get("selected_page_url"))
        and _comparable_url(str(snapshot["website_url"]))
        != _comparable_url(str(snapshot["selected_page_url"]))
    )
    if urls_differ and page_match_mode != "same_origin_spa":
        errors.append("runtime snapshot selected Tag Assistant page differs from the website")
    if urls_differ and page_match_mode == "same_origin_spa":
        route_evidence_id = str(snapshot.get("route_transition_evidence_id", "")).strip()
        if not route_evidence_id or route_evidence_id not in set(snapshot.get("evidence_ids", [])):
            errors.append(
                "same_origin_spa page matching requires route_transition_evidence_id in evidence_ids"
            )

    actual_containers = _snapshot_containers(snapshot.get("containers"), errors)
    expected_containers = expected_container_contract(results, case)
    if not expected_containers:
        errors.append("runtime snapshot cannot resolve the case container/workspace contract")
    elif actual_containers != expected_containers:
        errors.append("runtime snapshot container/workspace differs from the accepted run")
    workspace_surface = surfaces.get(
        str(snapshot.get("gtm_workspace_surface_id", "")),
        {},
    )
    if isinstance(workspace_surface, dict) and actual_containers:
        workspace_identity = (
            str(workspace_surface.get("container_id", "")).strip(),
            str(workspace_surface.get("workspace", "")).strip(),
        )
        if workspace_identity not in {
            (row["container_id"], row["workspace"]) for row in actual_containers
        }:
            errors.append(
                "runtime snapshot GTM surface does not identify a captured container/workspace"
            )
    registered_workspace_identities = {
        (
            str(surface.get("container_id", "")).strip(),
            str(surface.get("workspace", "")).strip(),
        )
        for surface in surfaces.values()
        if isinstance(surface, dict) and surface.get("role") == "gtm_workspace"
    }
    missing_workspace_surfaces = sorted(
        (row["container_id"], row["workspace"])
        for row in actual_containers
        if (row["container_id"], row["workspace"]) not in registered_workspace_identities
    )
    if missing_workspace_surfaces:
        errors.append(
            "runtime snapshot containers lack registered GTM workspace surfaces: "
            + ", ".join(
                f"{container}/{workspace}" for container, workspace in missing_workspace_surfaces
            )
        )

    expected_overlay_active = snapshot.get("expected_overlay_active", False)
    if not isinstance(expected_overlay_active, bool):
        errors.append("runtime snapshot expected_overlay_active must be boolean")
    if phase == "before_action":
        for field_name in READINESS_TRUE_FIELDS:
            if snapshot.get(field_name) is not True:
                errors.append(f"runtime readiness requires {field_name}=true")
    elif phase == "resume":
        for field_name in (
            "preview_connected",
            "target_interactive",
            "lifecycle_observed",
            "stream_quiet",
            "network_capture_active",
        ):
            if snapshot.get(field_name) is not True:
                errors.append(f"runtime readiness requires {field_name}=true")
        if snapshot.get("target_uncovered") is not True and expected_overlay_active is not True:
            errors.append(
                "resume readiness requires target_uncovered=true or an expected active overlay"
            )
    elif phase == "after_action":
        if snapshot.get("network_capture_active") is not True:
            errors.append("after-action settlement requires network_capture_active=true")
        count = snapshot.get("observed_business_push_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append("after-action snapshot observed_business_push_count must be non-negative")
        first_event = snapshot.get("first_event_after")
        if first_event is not None and (
            not isinstance(first_event, int) or isinstance(first_event, bool) or first_event < 0
        ):
            errors.append("after-action snapshot first_event_after must be non-negative or null")
    else:
        failure_reason = str(snapshot.get("failure_reason", "")).strip()
        if failure_reason not in INTERRUPTION_REASONS:
            errors.append("interrupted-action snapshot requires a supported failure_reason")
        failed_condition = {
            "browser_crashed": "target_interactive",
            "network_capture_lost": "network_capture_active",
            "preview_disconnected": "preview_connected",
            "surface_unavailable": "target_interactive",
        }.get(failure_reason)
        if failed_condition and snapshot.get(failed_condition) is not False:
            errors.append(
                f"interrupted-action failure_reason {failure_reason} requires "
                f"{failed_condition}=false"
            )
        if all(
            snapshot.get(field_name) is True
            for field_name in ("preview_connected", "target_interactive", "network_capture_active")
        ):
            errors.append("interrupted-action snapshot must expose a failed runtime condition")
        count = snapshot.get("observed_business_push_count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            errors.append(
                "interrupted-action snapshot observed_business_push_count must be non-negative"
            )
        first_event = snapshot.get("first_event_after")
        if first_event is not None and (
            not isinstance(first_event, int) or isinstance(first_event, bool) or first_event < 0
        ):
            errors.append(
                "interrupted-action snapshot first_event_after must be non-negative or null"
            )

    if not _nonempty(action_id):
        errors.append("runtime check requires a non-empty action_id")
    return errors


def normalize_runtime_check(
    snapshot: dict[str, Any],
    *,
    phase: str,
    action_id: str,
    case: dict[str, Any],
    ledger: dict[str, Any],
    results: dict[str, Any],
    recorded_at: str,
    action_timestamp: str | None = None,
) -> dict[str, Any]:
    """Return a closed runtime check or raise ValueError for unsafe evidence."""
    if not isinstance(snapshot, dict):
        raise ValueError("Runtime snapshot must be a JSON object.")
    errors = runtime_snapshot_errors(
        snapshot,
        phase=phase,
        action_id=action_id,
        case=case,
        ledger=ledger,
        results=results,
        recorded_at=recorded_at,
        action_timestamp=action_timestamp,
    )
    if errors:
        raise ValueError("\n".join(errors))
    normalized = {
        "check_id": str(snapshot["check_id"]).strip(),
        "phase": phase,
        "action_id": action_id,
        "case_id": str(case.get("case_id", "")).strip(),
        "event_group_id": str(case.get("event_group_id", "")).strip(),
        "captured_at": str(snapshot["captured_at"]).strip(),
        "recorded_at": recorded_at,
        "capture_source": str(snapshot["capture_source"]).strip(),
        "browser_context_id": str(snapshot["browser_context_id"]).strip(),
        "connection_epoch": snapshot["connection_epoch"],
        "gtm_workspace_surface_id": str(snapshot["gtm_workspace_surface_id"]).strip(),
        "tag_assistant_surface_id": str(snapshot["tag_assistant_surface_id"]).strip(),
        "website_surface_id": str(snapshot["website_surface_id"]).strip(),
        "containers": _snapshot_containers(snapshot["containers"], []),
        "website_url": str(snapshot["website_url"]).strip(),
        "selected_page_url": str(snapshot["selected_page_url"]).strip(),
        "page_match_mode": str(snapshot.get("page_match_mode", "exact")).strip(),
        "route_transition_evidence_id": (
            str(snapshot.get("route_transition_evidence_id", "")).strip() or None
        ),
        "preview_connected": snapshot["preview_connected"],
        "target_interactive": snapshot["target_interactive"],
        "target_uncovered": snapshot["target_uncovered"],
        "lifecycle_observed": snapshot["lifecycle_observed"],
        "stream_quiet": snapshot["stream_quiet"],
        "network_capture_active": snapshot["network_capture_active"],
        "expected_overlay_active": snapshot.get("expected_overlay_active", False),
        "preview_event_cursor": snapshot["preview_event_cursor"],
        "network_request_cursor": snapshot["network_request_cursor"],
        "evidence_ids": list(snapshot["evidence_ids"]),
        "consumed": False,
    }
    if phase in {"after_action", "interrupted_action"}:
        normalized["first_event_after"] = snapshot.get("first_event_after")
        normalized["observed_business_push_count"] = snapshot["observed_business_push_count"]
    if phase == "interrupted_action":
        normalized["failure_reason"] = str(snapshot["failure_reason"]).strip()
    return normalized


def validate_runtime_evidence(
    check: dict[str, Any],
    evidence: dict[str, dict[str, Any]],
) -> list[str]:
    """Validate that a runtime check has direct boundary and network proof."""
    label = f"session runtime check {check.get('check_id', '')}"
    errors: list[str] = []
    kinds: set[str] = set()
    action_id = str(check.get("action_id", ""))
    check_id = str(check.get("check_id", ""))
    phase = str(check.get("phase", ""))
    check_captured_at = parse_iso_timestamp(check.get("captured_at"))
    container_ids = {
        str(row.get("container_id", ""))
        for row in check.get("containers", [])
        if isinstance(row, dict)
    }
    for ref_value in check.get("evidence_ids", []):
        ref = str(ref_value).strip()
        row = evidence.get(ref)
        if row is None:
            errors.append(f"{label}: unknown evidence ID '{ref}'")
            continue
        if row.get("capture_mode") != "direct":
            errors.append(f"{label}: evidence '{ref}' is not a direct capture")
        if row.get("action_id") != action_id:
            errors.append(f"{label}: evidence '{ref}' is bound to another action")
        if row.get("runtime_check_id") != check_id:
            errors.append(f"{label}: evidence '{ref}' is bound to another runtime check")
        if row.get("runtime_phase") != phase:
            errors.append(f"{label}: evidence '{ref}' has the wrong runtime phase")
        evidence_captured_at = parse_iso_timestamp(row.get("captured_at"))
        if evidence_captured_at is None:
            errors.append(f"{label}: evidence '{ref}' requires a timezone-aware captured_at")
        elif (
            check_captured_at is not None
            and abs((evidence_captured_at - check_captured_at).total_seconds())
            > MAX_EVIDENCE_SKEW_SECONDS
        ):
            errors.append(f"{label}: evidence '{ref}' falls outside the runtime capture window")
        kind = str(row.get("kind", ""))
        kinds.add(kind)
        if kind == "browser_network_capture" and str(row.get("container_id", "")) not in (
            container_ids
        ):
            errors.append(f"{label}: network evidence '{ref}' has the wrong container")
    if "action_boundary" not in kinds:
        errors.append(f"{label}: direct action_boundary evidence is required")
    if check.get("network_capture_active") is True and "browser_network_capture" not in kinds:
        errors.append(f"{label}: direct browser_network_capture evidence is required")
    return errors
