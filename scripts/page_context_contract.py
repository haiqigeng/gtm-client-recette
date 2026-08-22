#!/usr/bin/env python3
"""Validate browser binding, page health, acquisition, and protected handoffs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

ACQUISITION_KINDS = {
    "DIRECT",
    "REFERRER",
    "CAMPAIGN",
    "INTERNAL",
    "RETURNING",
    "NOT_APPLICABLE",
}
ACQUISITION_METHODS = {
    "NATURAL",
    "BROWSER_SIMULATED",
    "URL_PARAMETER_SIMULATED",
    "ANALYST_PROVIDED",
    "NOT_APPLICABLE",
}
PROTECTED_GATE_TYPES = {
    "CREDENTIALS",
    "GOOGLE_SIGN_IN",
    "MFA",
    "CAPTCHA",
    "EMAIL_VERIFICATION",
    "SMS_VERIFICATION",
    "MAGIC_LINK",
    "REAL_PAYMENT",
    "EXTERNAL_APPROVAL",
    "IRREVERSIBLE_ACTION",
}
HANDOFF_STATUSES = {"REQUESTED", "RESUMED", "BLOCKED"}
PAGE_HEALTH_STATUSES = {"PASS", "FAIL"}
CONTINUITY_MODES = {"SAME_SESSION"}
ACQUISITION_EVIDENCE_KINDS = {
    "navigation",
    "source_signal",
    "screenshot",
    "browser_network_capture",
    "browser_network_request",
}
ACQUISITION_CAPTURE_FIELDS = {
    "referrer_url",
    "landing_url",
    "storage_cookie_state",
    "acquisition_parameters",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _iso_timestamp(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).tzinfo is not None
    except ValueError:
        return False


def _origin(value: Any) -> str | None:
    if not _nonempty(value):
        return None
    parsed = urlparse(str(value))
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def page_health_errors(value: Any, *, phase: str) -> list[str]:
    """Validate one direct, non-tracking page-health observation."""
    if not isinstance(value, dict):
        return ["page_health must be an object"]
    errors: list[str] = []
    for field in (
        "reachable",
        "is_error_page",
        "is_soft_404",
        "expected_content_present",
        "action_target_present",
    ):
        if not isinstance(value.get(field), bool):
            errors.append(f"page_health.{field} must be boolean")
    status_code = value.get("http_status")
    if status_code is not None and (
        not isinstance(status_code, int)
        or isinstance(status_code, bool)
        or not 100 <= status_code <= 599
    ):
        errors.append("page_health.http_status must be null or an HTTP status integer")
    if not _nonempty(value.get("reason")):
        errors.append("page_health.reason is required")
    status = str(value.get("status", "")).strip().upper()
    if status not in PAGE_HEALTH_STATUSES:
        errors.append("page_health.status must be PASS or FAIL")
    refs = value.get("evidence_ids")
    if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
        errors.append("page_health.evidence_ids must be a non-empty string array")
    healthy = (
        value.get("reachable") is True
        and (status_code is None or status_code < 400)
        and value.get("is_error_page") is False
        and value.get("is_soft_404") is False
        and value.get("expected_content_present") is True
        and (phase not in {"before_action", "resume"} or value.get("action_target_present") is True)
    )
    if status == "PASS" and not healthy:
        errors.append("page_health PASS contradicts the observed page state")
    if status == "FAIL" and healthy:
        errors.append("page_health FAIL requires a directly observed page problem")
    return errors


def page_health_passes(value: Any, *, phase: str) -> bool:
    """Return whether a structurally valid page-health observation passes."""
    return (
        isinstance(value, dict)
        and not page_health_errors(value, phase=phase)
        and str(value.get("status", "")).strip().upper() == "PASS"
    )


def _binding_matches(binding: Any, snapshot: dict[str, Any]) -> bool:
    return isinstance(binding, dict) and all(
        binding.get(field) == snapshot.get(field)
        for field in (
            "browser_instance_id",
            "browser_context_id",
            "tab_id",
            "preview_session_id",
        )
    )


def _valid_stream_reconnect(
    ledger: dict[str, Any],
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    action_id: str,
    case_id: str,
) -> bool:
    return any(
        isinstance(segment, dict)
        and isinstance(reconnect := segment.get("reconnect"), dict)
        and reconnect.get("status") == "RECONCILED"
        and str(reconnect.get("action_id", "")).strip() == action_id
        and str(reconnect.get("case_id", "")).strip() == case_id
        and _nonempty(reconnect.get("reason"))
        and isinstance(reconnect.get("evidence_ids"), list)
        and bool(reconnect["evidence_ids"])
        and _binding_matches(reconnect.get("before_binding"), before)
        and _binding_matches(reconnect.get("after_binding"), after)
        for segment in ledger.get("stream_segments", [])
    )


def _runtime_continuity_errors(snapshot: dict[str, Any], ledger: dict[str, Any]) -> list[str]:
    action_id = str(snapshot.get("action_id", "")).strip()
    if not action_id or snapshot.get("phase") not in {"after_action", "interrupted_action"}:
        return []
    action = next(
        (
            row
            for row in ledger.get("actions", [])
            if isinstance(row, dict) and str(row.get("action_id", "")).strip() == action_id
        ),
        None,
    )
    if not isinstance(action, dict) or snapshot.get("check_id") != action.get(
        "settlement_check_id"
    ):
        return []
    readiness_id = str(action.get("readiness_check_id", "")).strip()
    before = next(
        (
            row
            for row in ledger.get("runtime_checks", [])
            if isinstance(row, dict) and str(row.get("check_id", "")).strip() == readiness_id
        ),
        None,
    )
    if not isinstance(before, dict):
        return []
    changed = [
        field
        for field in ("tab_id", "preview_session_id")
        if before.get(field) != snapshot.get(field)
    ]
    if not changed:
        return []
    case_id = str(action.get("case_id", "")).strip()
    protected_handoff = any(
        isinstance(row, dict)
        and row.get("status") == "RESUMED"
        and row.get("gate_type") in PROTECTED_GATE_TYPES
        and str(row.get("action_id", "")).strip() == action_id
        and str(row.get("case_id", "")).strip() == case_id
        for row in ledger.get("protected_handoffs", [])
    )
    if protected_handoff:
        return [
            "runtime protected handoff continuity changed "
            + ", ".join(changed)
            + "; protected gates must resume in the same tab and Preview session"
        ]
    if _valid_stream_reconnect(
        ledger,
        before=before,
        after=snapshot,
        action_id=action_id,
        case_id=case_id,
    ):
        return []
    return [
        "runtime action continuity changed "
        + ", ".join(changed)
        + " without a bound reconnect contract"
    ]


def _is_first_runtime_snapshot(snapshot: dict[str, Any], ledger: dict[str, Any]) -> bool:
    first = next(
        (row for row in ledger.get("runtime_checks", []) if isinstance(row, dict)),
        None,
    )
    return isinstance(first, dict) and snapshot.get("check_id") == first.get("check_id")


def browser_runtime_errors(
    snapshot: dict[str, Any],
    *,
    ledger: dict[str, Any],
    expected_container_ids: set[str],
    evidence_catalog: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    """Validate that runtime evidence belongs to the approved existing browser and Preview."""
    errors: list[str] = []
    binding = ledger.get("browser_binding")
    if not isinstance(binding, dict):
        return ["session browser_binding must be an object"]
    for field in ("browser_instance_id", "browser_context_id", "profile_path", "registered_at"):
        if not _nonempty(binding.get(field)):
            errors.append(f"session browser_binding.{field} is required")
    if not _iso_timestamp(binding.get("registered_at")):
        errors.append("session browser_binding.registered_at must be ISO 8601 with timezone")
    if binding.get("approved_existing_session") is not True:
        errors.append("session browser binding must confirm the approved existing session")
    for field in ("browser_instance_id", "browser_context_id"):
        if snapshot.get(field) != binding.get(field):
            errors.append(f"runtime snapshot {field} differs from the approved browser binding")
    for field in ("tab_id", "preview_session_id"):
        if not _nonempty(snapshot.get(field)):
            errors.append(f"runtime snapshot {field} is required")
    loaded = snapshot.get("loaded_client_container_ids")
    if not isinstance(loaded, list) or any(not _nonempty(item) for item in loaded):
        errors.append("runtime snapshot loaded_client_container_ids must be a string array")
    else:
        normalized = {str(item).strip() for item in loaded}
        if normalized != expected_container_ids:
            errors.append(
                "runtime snapshot loaded client containers differ from the accepted container"
            )
    errors.extend(_runtime_continuity_errors(snapshot, ledger))
    if _is_first_runtime_snapshot(snapshot, ledger):
        for case in ledger.get("cases", []):
            if not isinstance(case, dict):
                continue
            context = case.get("acquisition_context")
            if isinstance(context, dict) and context.get("kind") != "NOT_APPLICABLE":
                case_id = str(case.get("case_id", "")).strip()
                errors.extend(
                    f"session case {case_id}: {error}"
                    for error in acquisition_errors(context, require_direct_evidence=True)
                )
                errors.extend(
                    f"session case {case_id}: {error}"
                    for error in _acquisition_catalog_errors(
                        context,
                        case_id=case_id,
                        evidence_catalog=evidence_catalog,
                    )
                )
    return errors


def _acquisition_catalog_errors(
    value: dict[str, Any],
    *,
    case_id: str,
    evidence_catalog: dict[str, dict[str, Any]] | None,
) -> list[str]:
    """Resolve acquisition bindings against the actual normalized evidence catalog."""
    if evidence_catalog is None:
        return ["applicable acquisition requires the normalized evidence catalog"]
    bindings = {
        str(row.get("evidence_id", "")).strip(): row
        for row in value.get("evidence_bindings", [])
        if isinstance(row, dict) and str(row.get("evidence_id", "")).strip()
    }
    errors: list[str] = []
    for evidence_id in value.get("evidence_ids", []):
        key = str(evidence_id).strip()
        actual = evidence_catalog.get(key)
        declared = bindings.get(key, {})
        if not isinstance(actual, dict):
            errors.append(f"acquisition evidence {key} is absent from the evidence catalog")
            continue
        if actual.get("capture_mode") != "direct":
            errors.append(f"acquisition evidence {key} is not a direct catalog capture")
        if actual.get("kind") not in ACQUISITION_EVIDENCE_KINDS:
            errors.append(f"acquisition evidence {key} catalog kind is inappropriate")
        if str(actual.get("case_id", "")).strip() != case_id:
            errors.append(f"acquisition evidence {key} is bound to another case")
        if actual.get("kind") != declared.get("kind") or actual.get("path_or_url") != declared.get(
            "path_or_url"
        ):
            errors.append(f"acquisition evidence {key} catalog binding differs")
        actual_fields = actual.get("captured_fields")
        declared_fields = declared.get("captured_fields")
        if (
            not isinstance(actual_fields, list)
            or set(actual_fields) != set(declared_fields or [])
            or set(actual_fields) != ACQUISITION_CAPTURE_FIELDS
        ):
            errors.append(f"acquisition evidence {key} must bind every captured acquisition field")
    return errors


def _acquisition_capture_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    observed_referrer = value.get("observed_referrer_url")
    if "observed_referrer_url" not in value or (
        observed_referrer is not None and _origin(observed_referrer) is None
    ):
        errors.append("acquisition_context.observed_referrer_url must be null or absolute")
    if _origin(value.get("landing_url")) is None:
        errors.append("acquisition_context.landing_url must be absolute")
    kind = str(value.get("kind", "")).strip().upper()
    if kind == "REFERRER" and _origin(observed_referrer) != _origin(value.get("referrer_url")):
        errors.append("referrer acquisition observed referrer differs from the intended source")

    storage = value.get("storage_cookie_state")
    if not isinstance(storage, dict):
        errors.append("acquisition_context.storage_cookie_state must be an object")
    else:
        for field in ("cookies_present", "local_storage_present", "session_storage_present"):
            if not isinstance(storage.get(field), bool):
                errors.append(f"acquisition_context.storage_cookie_state.{field} must be boolean")
        if storage.get("raw_values_retained") is not False:
            errors.append(
                "acquisition_context.storage_cookie_state.raw_values_retained must be false"
            )
        if not _nonempty(storage.get("reason")):
            errors.append("acquisition_context.storage_cookie_state.reason is required")
    parameters = value.get("acquisition_parameters")
    if not isinstance(parameters, dict):
        errors.append("acquisition_context.acquisition_parameters must be an object")
    elif kind == "CAMPAIGN" and not parameters:
        errors.append("campaign acquisition requires captured acquisition_parameters")

    refs = value.get("evidence_ids")
    ref_ids = {str(item) for item in refs} if isinstance(refs, list) else set()
    bindings = value.get("evidence_bindings")
    if not isinstance(bindings, list) or any(not isinstance(row, dict) for row in bindings):
        errors.append("acquisition_context.evidence_bindings must be an object array")
        return errors
    binding_ids = [str(row.get("evidence_id", "")).strip() for row in bindings]
    if any(not item for item in binding_ids) or len(set(binding_ids)) != len(binding_ids):
        errors.append("acquisition_context.evidence_bindings require unique evidence IDs")
    if set(binding_ids) != ref_ids:
        errors.append(
            "acquisition_context evidence_ids do not resolve exactly to evidence_bindings"
        )
    captured_fields: set[str] = set()
    for binding in bindings:
        evidence_id = str(binding.get("evidence_id", "")).strip() or "unknown"
        if binding.get("capture_mode") != "direct":
            errors.append(f"acquisition evidence {evidence_id} must use direct capture")
        if binding.get("kind") not in ACQUISITION_EVIDENCE_KINDS:
            errors.append(f"acquisition evidence {evidence_id} has an inappropriate kind")
        if not _nonempty(binding.get("path_or_url")):
            errors.append(f"acquisition evidence {evidence_id} requires path_or_url")
        fields = binding.get("captured_fields")
        if not isinstance(fields, list) or any(
            field not in ACQUISITION_CAPTURE_FIELDS for field in fields
        ):
            errors.append(f"acquisition evidence {evidence_id} has invalid captured_fields")
        else:
            captured_fields.update(fields)
    missing_fields = sorted(ACQUISITION_CAPTURE_FIELDS - captured_fields)
    if missing_fields:
        errors.append("acquisition direct evidence does not cover " + ", ".join(missing_fields))
    return errors


def acquisition_errors(value: Any, *, require_direct_evidence: bool = False) -> list[str]:
    """Validate one explicitly labelled acquisition/referrer context."""
    if not isinstance(value, dict):
        return ["acquisition_context must be an object"]
    errors: list[str] = []
    kind = str(value.get("kind", "")).strip().upper()
    method = str(value.get("method", "")).strip().upper()
    if kind not in ACQUISITION_KINDS:
        errors.append("acquisition_context.kind is invalid")
    if method not in ACQUISITION_METHODS:
        errors.append("acquisition_context.method is invalid")
    if kind == "NOT_APPLICABLE" and method != "NOT_APPLICABLE":
        errors.append("not-applicable acquisition must use a not-applicable method")
    if kind != "NOT_APPLICABLE":
        if method == "NOT_APPLICABLE":
            errors.append("applicable acquisition requires an acquisition method")
        if value.get("fresh_state") is not True:
            errors.append("applicable acquisition requires fresh_state=true")
        if kind == "REFERRER" and _origin(value.get("referrer_url")) is None:
            errors.append("referrer acquisition requires an absolute referrer_url")
        refs = value.get("evidence_ids")
        if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
            errors.append("applicable acquisition requires evidence_ids")
        if require_direct_evidence:
            errors.extend(_acquisition_capture_errors(value))
    limitations = value.get("limitations", [])
    if not isinstance(limitations, list) or any(not _nonempty(item) for item in limitations):
        errors.append("acquisition_context.limitations must be a string array")
    if method in {"BROWSER_SIMULATED", "URL_PARAMETER_SIMULATED"} and not limitations:
        errors.append("simulated acquisition requires an explicit limitation")
    return errors


def handoff_errors(
    ledger: dict[str, Any],
    *,
    final: bool,
) -> list[str]:
    """Validate protected-gate handoffs and same-session resumption."""
    value = ledger.get("protected_handoffs")
    if not isinstance(value, list):
        return ["session protected_handoffs must be an array"]
    errors: list[str] = []
    seen: set[str] = set()
    binding = (
        ledger.get("browser_binding") if isinstance(ledger.get("browser_binding"), dict) else {}
    )
    action_ids = {
        str(row.get("action_id", "")).strip()
        for row in ledger.get("actions", [])
        if isinstance(row, dict)
    }
    case_ids = {
        str(row.get("case_id", "")).strip()
        for row in ledger.get("cases", [])
        if isinstance(row, dict)
    }
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            errors.append(f"session protected handoff row {index} must be an object")
            continue
        handoff_id = str(row.get("handoff_id", "")).strip()
        label = f"session protected handoff {handoff_id or index}"
        if not handoff_id:
            errors.append(f"{label}: handoff_id is required")
        elif handoff_id in seen:
            errors.append(f"{label}: duplicate handoff_id")
        seen.add(handoff_id)
        if row.get("gate_type") not in PROTECTED_GATE_TYPES:
            errors.append(f"{label}: invalid gate_type")
        status = str(row.get("status", "")).strip().upper()
        if status not in HANDOFF_STATUSES:
            errors.append(f"{label}: invalid status")
        continuity_mode = str(row.get("continuity_mode", "SAME_SESSION")).strip().upper()
        if continuity_mode not in CONTINUITY_MODES:
            errors.append(f"{label}: invalid continuity_mode")
        if row.get("analyst_help_requested") is not True:
            errors.append(f"{label}: analyst_help_requested must be true")
        if str(row.get("case_id", "")).strip() not in case_ids:
            errors.append(f"{label}: unknown case_id")
        if str(row.get("action_id", "")).strip() not in action_ids:
            errors.append(f"{label}: unknown action_id")
        if not _iso_timestamp(row.get("requested_at")):
            errors.append(f"{label}: requested_at must be ISO 8601 with timezone")
        if not _nonempty(row.get("reason")):
            errors.append(f"{label}: reason is required")
        refs = row.get("evidence_ids")
        if not isinstance(refs, list) or not refs or any(not _nonempty(item) for item in refs):
            errors.append(f"{label}: evidence_ids must be a non-empty string array")
        before = row.get("before_binding")
        if not isinstance(before, dict):
            errors.append(f"{label}: before_binding must be an object")
            before = {}
        for field in (
            "browser_instance_id",
            "browser_context_id",
            "tab_id",
            "preview_session_id",
        ):
            if not _nonempty(before.get(field)):
                errors.append(f"{label}: before_binding.{field} is required")
            if field in {"browser_instance_id", "browser_context_id"} and before.get(
                field
            ) != binding.get(field):
                errors.append(f"{label}: before_binding.{field} differs from approved browser")
        if status == "RESUMED":
            if not _iso_timestamp(row.get("resumed_at")):
                errors.append(f"{label}: resumed handoff requires resumed_at")
            after = row.get("after_binding")
            if not isinstance(after, dict):
                errors.append(f"{label}: resumed handoff requires after_binding")
            else:
                for field in (
                    "browser_instance_id",
                    "browser_context_id",
                    "tab_id",
                    "preview_session_id",
                ):
                    if not _nonempty(after.get(field)):
                        errors.append(f"{label}: after_binding.{field} is required")
                    if field in {"browser_instance_id", "browser_context_id"} and after.get(
                        field
                    ) != binding.get(field):
                        errors.append(
                            f"{label}: after_binding.{field} differs from approved browser"
                        )
                    if after.get(field) != before.get(field):
                        errors.append(f"{label}: handoff resumed in a different {field}")
        if final and status == "REQUESTED":
            errors.append(f"{label}: final run cannot retain a merely requested handoff")
    return errors
