#!/usr/bin/env python3
"""Pure validation helpers for per-tag evidence, comparisons, and privacy."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from acceptance_contract import worst_status
from client_side_rules import MISSING, path_value, scan_sensitive_value, valid_path

EXPECTED_ANCHOR_SOURCES = {
    "tracking_plan",
    "explicit_acceptance_rule",
    "raw_data_layer_mapping",
    "resolved_gtm_variable_contract",
    "tag_template_semantics",
}

EXPECTED_ANCHOR_TRANSFORMS = {
    "identity",
    "request_expected",
    "gtm_variable_reference",
    "absence_null",
}

TAG_IDENTIFIED_EVIDENCE_KINDS = {
    "gtm_variable",
    "tag_configuration",
    "tag_runtime",
    "browser_network_request",
    "trigger_evaluation",
    "tag_sequence",
    "tag_assistant_consent",
}


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def value_type(value: Any) -> str:
    """Return the normalized JSON type name used by the recette contract."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/number equality shortcut."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    left_number = isinstance(left, (int, float)) and not isinstance(left, bool)
    right_number = isinstance(right, (int, float)) and not isinstance(right, bool)
    if left_number or right_number:
        return left_number and right_number and left == right
    return type(left) is type(right) and left == right


def _transform_anchor(value: Any, transform: str) -> Any:
    if transform == "identity":
        return value
    if transform == "request_expected":
        return value not in {"absent", "blocked"}
    if transform == "gtm_variable_reference":
        return f"{{{{{value}}}}}" if isinstance(value, str) and value else MISSING
    if transform == "absence_null":
        return None if value in {"not_fired", "blocked"} else MISSING
    return MISSING


def resolve_expected_anchor(
    anchor: Any,
    *,
    requirements: dict[str, dict[str, Any]],
    allowed_requirement_ids: Iterable[str],
    label: str,
    errors: list[str],
) -> Any:
    """Resolve an expected value from an accepted, event-bound requirement source."""
    if not isinstance(anchor, dict):
        errors.append(f"{label}: expected_anchor is required")
        return MISSING
    source = str(anchor.get("source", "")).strip()
    if source not in EXPECTED_ANCHOR_SOURCES:
        errors.append(f"{label}: unsupported expected_anchor.source '{source}'")
    requirement_id = str(anchor.get("requirement_id", "")).strip()
    allowed = {str(value).strip() for value in allowed_requirement_ids if str(value).strip()}
    if not requirement_id:
        errors.append(f"{label}: expected_anchor.requirement_id is required")
        return MISSING
    if requirement_id not in allowed:
        errors.append(f"{label}: expected anchor is outside the action requirement set")
        return MISSING
    requirement = requirements.get(requirement_id)
    if requirement is None:
        errors.append(f"{label}: expected anchor references an unknown requirement")
        return MISSING
    path = anchor.get("path")
    if not valid_path(path):
        errors.append(f"{label}: expected_anchor.path is invalid")
        return MISSING
    anchored = path_value(requirement, str(path))
    if anchored is MISSING:
        errors.append(f"{label}: expected anchor path is absent or ambiguous")
        return MISSING
    transform = str(anchor.get("transform", "identity")).strip() or "identity"
    if transform not in EXPECTED_ANCHOR_TRANSFORMS:
        errors.append(f"{label}: unsupported expected_anchor.transform '{transform}'")
        return MISSING
    transformed = _transform_anchor(anchored, transform)
    if transformed is MISSING:
        errors.append(f"{label}: expected anchor transform could not be applied")
    return transformed


def validate_expected_field(
    *,
    actual_expected: Any,
    anchor: Any,
    requirements: dict[str, dict[str, Any]],
    allowed_requirement_ids: Iterable[str],
    label: str,
    errors: list[str],
) -> None:
    """Require one expected control field to equal its accepted source anchor."""
    anchored = resolve_expected_anchor(
        anchor,
        requirements=requirements,
        allowed_requirement_ids=allowed_requirement_ids,
        label=label,
        errors=errors,
    )
    if anchored is not MISSING and not strict_equal(actual_expected, anchored):
        errors.append(f"{label}: expected value differs from its accepted source anchor")


def validate_comparisons(
    *,
    items: Any,
    label: str,
    parent_status: str,
    requirements: dict[str, dict[str, Any]],
    allowed_requirement_ids: Iterable[str],
    errors: list[str],
) -> None:
    """Validate exact comparisons and bind every expectation to accepted evidence."""
    if not isinstance(items, list) or not items:
        errors.append(f"{label}: exact comparison rows are required")
        return
    computed: list[str] = []
    for index, item in enumerate(items, start=1):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label}: comparison must be an object")
            computed.append("FAIL")
            continue
        if not _nonempty(item.get("name")):
            errors.append(f"{item_label}: name is required")
        item_status = str(item.get("status", "")).strip().upper()
        if item_status not in {"PASS", "FAIL", "BLOCKED", "REVIEW"}:
            errors.append(f"{item_label}: invalid comparison status")
            computed.append("FAIL")
            continue
        anchored = resolve_expected_anchor(
            item.get("expected_anchor"),
            requirements=requirements,
            allowed_requirement_ids=allowed_requirement_ids,
            label=item_label,
            errors=errors,
        )
        if item.get("redacted") is True:
            if not _nonempty(item.get("comparison_basis")):
                errors.append(f"{item_label}: redacted comparison requires comparison_basis")
            if any(field in item for field in ("expected_value", "actual_value")):
                errors.append(f"{item_label}: redacted comparison must not retain values")
            computed.append(item_status)
            continue
        for field_name in (
            "expected_value",
            "expected_type",
            "actual_value",
            "actual_type",
        ):
            if field_name not in item:
                errors.append(f"{item_label}: missing '{field_name}'")
        expected_value = item.get("expected_value")
        actual_value = item.get("actual_value")
        expected_type = item.get("expected_type")
        actual_type = item.get("actual_type")
        if value_type(expected_value) != expected_type:
            errors.append(f"{item_label}: expected_type differs from expected_value")
        if value_type(actual_value) != actual_type:
            errors.append(f"{item_label}: actual_type differs from actual_value")
        if anchored is not MISSING and not strict_equal(expected_value, anchored):
            errors.append(f"{item_label}: expected value differs from its accepted source anchor")
        matches = expected_type == actual_type and strict_equal(expected_value, actual_value)
        expected_status = "PASS" if matches else "FAIL"
        if item_status in {"PASS", "FAIL"} and item_status != expected_status:
            errors.append(
                f"{item_label}: status {item_status} contradicts exact value/type comparison"
            )
        computed.append(item_status)
    computed_parent = worst_status(computed)
    if parent_status in {"PASS", "FAIL", "BLOCKED", "REVIEW"} and (
        parent_status != computed_parent
    ):
        errors.append(
            f"{label}: parent status {parent_status} differs from comparison rows {computed_parent}"
        )


def evidence_matches_tag(evidence: dict[str, Any], tag_id: str) -> bool:
    """Return whether tag-specific evidence is explicitly bound to this tag."""
    kind = str(evidence.get("kind", "")).strip()
    return kind not in TAG_IDENTIFIED_EVIDENCE_KINDS or evidence.get("tag_id") == tag_id


def request_evidence_ids(
    evidence_ids: Iterable[Any],
    evidence: dict[str, dict[str, Any]],
    tag_id: str,
) -> set[str]:
    """Return request IDs proved by referenced, tag-bound network evidence."""
    output: set[str] = set()
    for evidence_id in evidence_ids:
        row = evidence.get(str(evidence_id).strip(), {})
        if row.get("kind") != "browser_network_request" or row.get("tag_id") != tag_id:
            continue
        request_id = str(row.get("request_id", "")).strip()
        if request_id:
            output.add(request_id)
    return output


def has_network_capture(evidence_ids: Iterable[Any], evidence: dict[str, dict[str, Any]]) -> bool:
    """Return whether references prove that the action network stream was captured."""
    return any(
        evidence.get(str(evidence_id).strip(), {}).get("kind") == "browser_network_capture"
        for evidence_id in evidence_ids
    )


def session_sensitive_findings(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Scan all exportable session/per-tag values without retaining matched secrets."""
    findings = scan_sensitive_value(ledger, root_path="session")
    for action_index, action in enumerate(ledger.get("actions", [])):
        if not isinstance(action, dict):
            continue
        for row_index, row in enumerate(action.get("tag_layer_results", [])):
            if not isinstance(row, dict):
                continue
            details = row.get("details") if isinstance(row.get("details"), dict) else {}
            for comparison_field in ("variables", "configuration", "parameters"):
                for item_index, item in enumerate(details.get(comparison_field, []) or []):
                    if not isinstance(item, dict) or item.get("redacted") is True:
                        continue
                    name = str(item.get("name", "value"))
                    findings.extend(
                        scan_sensitive_value(
                            {
                                name: {
                                    "expected": item.get("expected_value"),
                                    "actual": item.get("actual_value"),
                                }
                            },
                            root_path=(
                                f"session.actions[{action_index}].tag_layer_results"
                                f"[{row_index}].details.{comparison_field}[{item_index}]"
                            ),
                        )
                    )
    deduplicated: dict[tuple[str, str, str], dict[str, Any]] = {}
    for finding in findings:
        key = (
            str(finding.get("path", "")),
            str(finding.get("category", "")),
            str(finding.get("basis", "")),
        )
        deduplicated[key] = finding
    return list(deduplicated.values())
