#!/usr/bin/env python3
"""Build and semantically validate a schema-v2 GTM Preview recette workbook."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from recette_schema import (
    ReportValidationError,
    as_rows,
    dumps_structured,
    event_rollup,
    status_of,
    validate,
    worst_status,
)

STATUS_FILLS = {
    "PASS": "C6EFCE",
    "FAIL": "FFC7CE",
    "BLOCKED": "F4B183",
    "REVIEW": "FFF2CC",
    "NOT_TESTED": "D9E1F2",
}
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SECTION_FILL = PatternFill("solid", fgColor="D9EAF7")
THIN_BORDER = Border(bottom=Side(style="thin", color="B7C9D6"))
WRAP_ALIGNMENT = Alignment(vertical="top", wrap_text=True)

REQUIRED_SHEETS = [
    "Client Summary",
    "Requirement Matrix",
    "Journey Coverage",
    "Event Evidence",
    "Tag Evidence",
    "Consent",
    "Unexpected Events-Tags",
    "Blockers",
    "Evidence Catalogue",
    "Run Context",
]

REQUIREMENT_HEADERS = [
    "requirement_id",
    "event_group_id",
    "plan_order",
    "source_reference",
    "source_file",
    "source_sheet",
    "source_row",
    "source_cells",
    "source_section",
    "journey_id",
    "step_id",
    "action",
    "url",
    "selector_or_element",
    "inferred",
    "inference_source",
    "event_name",
    "field_path",
    "match_rule",
    "expected_value",
    "expected_type",
    "expected_occurrence",
    "occurrence_verdict",
    "raw_state",
    "raw_value",
    "raw_type",
    "resolved_state",
    "resolved_value",
    "resolved_type",
    "gtm_variable",
    "gtm_variable_state",
    "gtm_variable_value",
    "gtm_variable_type",
    "tag_name",
    "tag_relevance",
    "expected_firing",
    "actual_firing",
    "fire_count",
    "tag_configuration_field",
    "expected_tag_configuration",
    "configured_value",
    "runtime_state",
    "runtime_value",
    "runtime_type",
    "consent_scenario",
    "consent_source",
    "consent_state",
    "raw_verdict",
    "resolved_verdict",
    "variable_verdict",
    "tag_firing_verdict",
    "tag_parameter_verdict",
    "consent_verdict",
    "overall_status",
    "failure_layer",
    "mismatch_or_reason",
    "evidence_ids",
    "notes",
]

JOURNEY_HEADERS = [
    "plan_order",
    "event_group_id",
    "event_name",
    "requirement_id",
    "journey_id",
    "step_id",
    "action",
    "url",
    "selector_or_element",
    "inferred",
    "inference_source",
    "confidence",
    "attempted_routes",
    "execution_status",
    "blocker_id",
    "overall_status",
    "evidence_ids",
    "notes",
]

EVENT_HEADERS = [
    "plan_order",
    "event_group_id",
    "requirement_id",
    "event_name",
    "event_observed",
    "actual_occurrence_count",
    "occurrence_event_indexes",
    "anchor_event_name",
    "anchor_event_index",
    "occurrence_evidence_id",
    "capture_source",
    "event_index",
    "event_timestamp",
    "raw_api_call_payload",
    "raw_field_path",
    "raw_field_state",
    "raw_field_value",
    "raw_field_type",
    "resolved_data_layer_snapshot",
    "resolved_field_state",
    "resolved_field_value",
    "resolved_field_type",
    "preview_connected_before",
    "target_ready_before",
    "last_event_before",
    "action_timestamp",
    "first_event_after",
    "settled_final_event",
    "quiet_window_ms",
    "timeout_ms",
    "stream_settled",
    "raw_evidence_id",
    "resolved_evidence_id",
    "status",
    "notes",
]

TAG_HEADERS = [
    "plan_order",
    "event_group_id",
    "requirement_id",
    "event_name",
    "tag_name",
    "relevance",
    "expected_firing",
    "actual_firing",
    "fire_count",
    "configuration_field",
    "configured_value",
    "runtime_state",
    "runtime_value",
    "runtime_type",
    "firing_status",
    "parameter_status",
    "non_firing_reason",
    "reason_source",
    "configuration_evidence_id",
    "runtime_evidence_id",
    "notes",
]

CONSENT_HEADERS = [
    "plan_order",
    "event_group_id",
    "requirement_id",
    "event_name",
    "applicable",
    "scenario_id",
    "scenario",
    "source",
    "expected_state",
    "state_at_event",
    "override_approved",
    "override_method",
    "blocker_id",
    "approval_evidence_id",
    "evidence_id",
    "status",
    "notes",
]

UNEXPECTED_HEADERS = [
    "unexpected_id",
    "event_group_id",
    "kind",
    "event_name",
    "tag_name",
    "actual",
    "status",
    "evidence_ids",
    "notes",
]

BLOCKER_HEADERS = [
    "blocker_id",
    "type",
    "checkpoint",
    "description",
    "requirement_ids",
    "analyst_intervention_required",
    "analyst_help_requested",
    "analyst_response",
    "outcome",
    "status",
    "evidence_ids",
    "notes",
]

EVIDENCE_HEADERS = [
    "evidence_id",
    "kind",
    "source",
    "path_or_url",
    "captured_at",
    "description",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Schema-v2 normalized JSON path, or - for stdin.")
    parser.add_argument("output", nargs="?", help="Destination .xlsx path.")
    parser.add_argument("--strict", action="store_true", help="Reject every semantic error.")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate normalized data without writing a workbook.",
    )
    return parser.parse_args()


def load_data(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ReportValidationError("Top-level JSON value must be an object.")
    return data


def serialize(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return dumps_structured(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def apply_status_fill(cell: Cell) -> None:
    status = status_of(cell.value)
    colour = STATUS_FILLS.get(status)
    if colour:
        cell.fill = PatternFill("solid", fgColor=colour)
        cell.font = Font(bold=True)


def _column_cap(header: str) -> int:
    if any(
        token in header
        for token in (
            "payload",
            "snapshot",
            "attempted_routes",
            "state",
            "notes",
            "reason",
            "description",
            "value",
        )
    ):
        return 80
    return 45


def style_table(
    ws,
    status_headers: tuple[str, ...] = (
        "status",
        "overall_status",
        "occurrence_verdict",
        "raw_verdict",
        "resolved_verdict",
        "variable_verdict",
        "tag_firing_verdict",
        "tag_parameter_verdict",
        "consent_verdict",
        "firing_status",
        "parameter_status",
    ),
) -> None:
    ws.freeze_panes = "A2"
    if ws.max_row >= 1 and ws.max_column >= 1:
        ws.auto_filter.ref = ws.dimensions
    header_map = {str(cell.value): cell.column for cell in ws[1]}
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP_ALIGNMENT
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_ALIGNMENT
            cell.border = THIN_BORDER
        for header in status_headers:
            column = header_map.get(header)
            if column:
                apply_status_fill(row[column - 1])
    for column_index, cells in enumerate(ws.columns, start=1):
        values = [str(cell.value or "") for cell in cells]
        longest = max((len(value) for value in values), default=0)
        header = str(cells[0].value or "")
        ws.column_dimensions[get_column_letter(column_index)].width = min(
            max(longest + 2, 12), _column_cap(header)
        )


def add_table_sheet(
    wb: Workbook,
    title: str,
    headers: list[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append([serialize(row.get(header)) for header in headers])
    style_table(ws)


def _observation_value(observation: Any, field: str) -> Any:
    if not isinstance(observation, dict):
        return ""
    if field not in observation:
        return ""
    return observation[field]


def requirement_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for req in as_rows(data.get("requirements"), "requirements"):
        source = req.get("source", {})
        journey = req.get("journey", {})
        expectation = req.get("expectation", {})
        raw = req.get("raw_api_call") or {}
        resolved = req.get("resolved_data_layer") or {}
        variable = req.get("gtm_variable") or {}
        tag = req.get("tag") or {}
        consent = req.get("consent") or {}
        verdict = req.get("verdict", {})
        output.append(
            {
                "requirement_id": req.get("requirement_id"),
                "event_group_id": req.get("event_group_id"),
                "plan_order": source.get("plan_order"),
                "source_reference": source.get("reference"),
                "source_file": source.get("file"),
                "source_sheet": source.get("sheet"),
                "source_row": source.get("row"),
                "source_cells": source.get("cells"),
                "source_section": source.get("section"),
                "journey_id": journey.get("journey_id"),
                "step_id": journey.get("step_id"),
                "action": journey.get("action"),
                "url": journey.get("url"),
                "selector_or_element": journey.get("selector_or_element"),
                "inferred": journey.get("inferred"),
                "inference_source": journey.get("inference_source"),
                "event_name": expectation.get("event_name"),
                "field_path": expectation.get("field_path"),
                "match_rule": expectation.get("match_rule"),
                "expected_value": expectation.get("expected_value"),
                "expected_type": expectation.get("expected_type"),
                "expected_occurrence": expectation.get("expected_occurrence"),
                "occurrence_verdict": verdict.get("event_occurrence"),
                "raw_state": raw.get("field_state"),
                "raw_value": _observation_value(raw, "field_value"),
                "raw_type": raw.get("field_type"),
                "resolved_state": resolved.get("field_state"),
                "resolved_value": _observation_value(resolved, "field_value"),
                "resolved_type": resolved.get("field_type"),
                "gtm_variable": variable.get("name"),
                "gtm_variable_state": variable.get("field_state"),
                "gtm_variable_value": _observation_value(variable, "field_value"),
                "gtm_variable_type": variable.get("field_type"),
                "tag_name": tag.get("name"),
                "tag_relevance": tag.get("relevance"),
                "expected_firing": tag.get("expected_firing"),
                "actual_firing": tag.get("actual_firing"),
                "fire_count": tag.get("fire_count"),
                "tag_configuration_field": tag.get("configuration_field"),
                "expected_tag_configuration": expectation.get(
                    "expected_tag_configuration"
                ),
                "configured_value": tag.get("configured_value"),
                "runtime_state": tag.get("runtime_state"),
                "runtime_value": _observation_value(tag, "runtime_value"),
                "runtime_type": tag.get("runtime_type"),
                "consent_scenario": consent.get("scenario"),
                "consent_source": consent.get("source"),
                "consent_state": consent.get("state_at_event"),
                "raw_verdict": verdict.get("raw_payload"),
                "resolved_verdict": verdict.get("resolved_data_layer"),
                "variable_verdict": verdict.get("gtm_variable"),
                "tag_firing_verdict": verdict.get("tag_firing"),
                "tag_parameter_verdict": verdict.get("tag_parameter"),
                "consent_verdict": verdict.get("consent"),
                "overall_status": verdict.get("overall"),
                "failure_layer": verdict.get("failure_layer"),
                "mismatch_or_reason": verdict.get("mismatch"),
                "evidence_ids": req.get("evidence_ids"),
                "notes": req.get("notes"),
            }
        )
    return output


def journey_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for req in as_rows(data.get("requirements"), "requirements"):
        source = req.get("source", {})
        journey = req.get("journey", {})
        expectation = req.get("expectation", {})
        output.append(
            {
                "plan_order": source.get("plan_order"),
                "event_group_id": req.get("event_group_id"),
                "event_name": expectation.get("event_name"),
                "requirement_id": req.get("requirement_id"),
                "journey_id": journey.get("journey_id"),
                "step_id": journey.get("step_id"),
                "action": journey.get("action"),
                "url": journey.get("url"),
                "selector_or_element": journey.get("selector_or_element"),
                "inferred": journey.get("inferred"),
                "inference_source": journey.get("inference_source"),
                "confidence": journey.get("confidence"),
                "attempted_routes": journey.get("attempted_routes"),
                "execution_status": journey.get("execution_status"),
                "blocker_id": req.get("blocker_id"),
                "overall_status": req.get("verdict", {}).get("overall"),
                "evidence_ids": req.get("evidence_ids"),
                "notes": req.get("notes"),
            }
        )
    return output


def event_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for req in as_rows(data.get("requirements"), "requirements"):
        source = req.get("source", {})
        expectation = req.get("expectation", {})
        raw = req.get("raw_api_call") or {}
        resolved = req.get("resolved_data_layer") or {}
        occurrence = req.get("occurrence_evidence") or {}
        boundary = req.get("action_boundary") or {}
        output.append(
            {
                "plan_order": source.get("plan_order"),
                "event_group_id": req.get("event_group_id"),
                "requirement_id": req.get("requirement_id"),
                "event_name": expectation.get("event_name"),
                "event_observed": req.get("event_observed"),
                "actual_occurrence_count": occurrence.get("actual_count"),
                "occurrence_event_indexes": occurrence.get("event_indexes"),
                "anchor_event_name": occurrence.get("anchor_event_name"),
                "anchor_event_index": occurrence.get("anchor_event_index"),
                "occurrence_evidence_id": occurrence.get("evidence_id"),
                "capture_source": raw.get("capture_source"),
                "event_index": raw.get("event_index"),
                "event_timestamp": raw.get("timestamp"),
                "raw_api_call_payload": raw.get("payload"),
                "raw_field_path": expectation.get("field_path"),
                "raw_field_state": raw.get("field_state"),
                "raw_field_value": _observation_value(raw, "field_value"),
                "raw_field_type": raw.get("field_type"),
                "resolved_data_layer_snapshot": resolved.get("snapshot"),
                "resolved_field_state": resolved.get("field_state"),
                "resolved_field_value": _observation_value(resolved, "field_value"),
                "resolved_field_type": resolved.get("field_type"),
                "preview_connected_before": boundary.get("preview_connected_before"),
                "target_ready_before": boundary.get("target_ready_before"),
                "last_event_before": boundary.get("last_event_before"),
                "action_timestamp": boundary.get("action_timestamp"),
                "first_event_after": boundary.get("first_event_after"),
                "settled_final_event": boundary.get("settled_final_event"),
                "quiet_window_ms": boundary.get("quiet_window_ms"),
                "timeout_ms": boundary.get("timeout_ms"),
                "stream_settled": boundary.get("stream_settled"),
                "raw_evidence_id": raw.get("evidence_id"),
                "resolved_evidence_id": resolved.get("evidence_id"),
                "status": req.get("verdict", {}).get("raw_payload"),
                "notes": req.get("notes"),
            }
        )
    return output


def tag_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for req in as_rows(data.get("requirements"), "requirements"):
        tag = req.get("tag")
        if not isinstance(tag, dict) or tag.get("applicable") is not True:
            continue
        source = req.get("source", {})
        expectation = req.get("expectation", {})
        verdict = req.get("verdict", {})
        output.append(
            {
                "plan_order": source.get("plan_order"),
                "event_group_id": req.get("event_group_id"),
                "requirement_id": req.get("requirement_id"),
                "event_name": expectation.get("event_name"),
                "tag_name": tag.get("name"),
                "relevance": tag.get("relevance"),
                "expected_firing": tag.get("expected_firing"),
                "actual_firing": tag.get("actual_firing"),
                "fire_count": tag.get("fire_count"),
                "configuration_field": tag.get("configuration_field"),
                "configured_value": tag.get("configured_value"),
                "runtime_state": tag.get("runtime_state"),
                "runtime_value": _observation_value(tag, "runtime_value"),
                "runtime_type": tag.get("runtime_type"),
                "firing_status": verdict.get("tag_firing"),
                "parameter_status": verdict.get("tag_parameter"),
                "non_firing_reason": tag.get("non_firing_reason"),
                "reason_source": tag.get("reason_source"),
                "configuration_evidence_id": tag.get("configuration_evidence_id"),
                "runtime_evidence_id": tag.get("runtime_evidence_id"),
                "notes": req.get("notes"),
            }
        )
    return output


def consent_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for req in as_rows(data.get("requirements"), "requirements"):
        consent = req.get("consent")
        if not isinstance(consent, dict):
            continue
        source = req.get("source", {})
        expectation = req.get("expectation", {})
        output.append(
            {
                "plan_order": source.get("plan_order"),
                "event_group_id": req.get("event_group_id"),
                "requirement_id": req.get("requirement_id"),
                "event_name": expectation.get("event_name"),
                "applicable": consent.get("applicable"),
                "scenario_id": consent.get("scenario_id"),
                "scenario": consent.get("scenario"),
                "source": consent.get("source"),
                "expected_state": expectation.get("expected_consent_state"),
                "state_at_event": consent.get("state_at_event"),
                "override_approved": consent.get("override_approved"),
                "override_method": consent.get("override_method"),
                "blocker_id": consent.get("blocker_id"),
                "approval_evidence_id": consent.get("approval_evidence_id"),
                "evidence_id": consent.get("evidence_id"),
                "status": req.get("verdict", {}).get("consent"),
                "notes": req.get("notes"),
            }
        )
    return output


def client_category(req: dict[str, Any]) -> str:
    status = status_of(req.get("verdict", {}).get("overall"))
    if status == "PASS":
        return "tested and correct"
    if status == "BLOCKED":
        return "blocked journey or unavailable element"
    if status in {"REVIEW", "NOT_TESTED"}:
        return "review or outside scope"
    if req.get("event_observed") is False:
        return "expected event not triggered"
    verdict = req.get("verdict", {})
    layer = str(verdict.get("failure_layer", "")).lower()
    raw = req.get("raw_api_call") or {}
    tag = req.get("tag") or {}
    if raw.get("field_state") == "absent":
        return "raw dataLayer field missing"
    if layer in {"raw_payload", "raw_value", "raw_type"}:
        return "wrong raw value/type"
    if layer in {"resolved_data_layer", "gtm_variable"}:
        return "resolved Data Layer or GTM variable mismatch"
    if layer in {"tag_firing", "tag_not_fired"}:
        return "tag not fired"
    if tag.get("fire_count", 0) > 1 or layer in {"duplicate_tag", "unexpected_tag"}:
        return "tag fired unexpectedly or duplicated"
    if layer in {"tag_configuration", "configuration"}:
        return "tag configuration mismatch"
    if layer in {"tag_parameter", "runtime_parameter"}:
        return "runtime tag parameter mismatch"
    if layer in {"consent", "timing"}:
        return "consent/timing issue"
    return "other confirmed mismatch"


def add_client_summary(wb: Workbook, data: dict[str, Any], warnings: list[str]) -> None:
    ws = wb.active
    ws.title = "Client Summary"
    run = data.get("run", {})
    rollup = event_rollup(data)
    overall = worst_status(item["status"] for item in rollup)
    counts = Counter(item["status"] for item in rollup)

    ws["A1"] = run.get("report_title", "GTM Preview Recette")
    ws["A1"].font = Font(size=18, bold=True, color="1F4E78")
    summary_rows = [
        ("Overall status", overall),
        ("Run type", run.get("run_type")),
        ("Client", run.get("client")),
        ("Environment", run.get("environment")),
        ("Target URL", run.get("site_url")),
        ("Container / workspace", f"{run.get('container_id')} / {run.get('workspace')}"),
        ("Tracking plan", run.get("tracking_plan_source")),
        ("Generated at", datetime.now(UTC).isoformat(timespec="seconds")),
        ("Validation warnings", len(warnings)),
    ]
    for row_index, (label, value) in enumerate(summary_rows, start=3):
        ws.cell(row=row_index, column=1, value=label)
        ws.cell(row=row_index, column=2, value=serialize(value))
    apply_status_fill(ws["B3"])

    event_start = 14
    ws.cell(row=event_start, column=1, value="Plan-ordered event status")
    ws.cell(row=event_start, column=1).fill = SECTION_FILL
    ws.cell(row=event_start, column=1).font = Font(bold=True)
    event_headers = [
        "plan_order",
        "event_name",
        "status",
        "requirement_count",
        "reason",
        "evidence_ids",
    ]
    for column, header in enumerate(event_headers, start=1):
        cell = ws.cell(row=event_start + 1, column=column, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for row_index, item in enumerate(rollup, start=event_start + 2):
        for column, header in enumerate(event_headers, start=1):
            ws.cell(row=row_index, column=column, value=serialize(item.get(header)))
        apply_status_fill(ws.cell(row=row_index, column=3))

    counts_start = event_start + len(rollup) + 4
    ws.cell(row=counts_start, column=1, value="Event status totals")
    ws.cell(row=counts_start, column=1).fill = SECTION_FILL
    ws.cell(row=counts_start, column=1).font = Font(bold=True)
    for offset, status in enumerate(("PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_TESTED"), start=1):
        ws.cell(row=counts_start + offset, column=1, value=status)
        ws.cell(row=counts_start + offset, column=2, value=counts.get(status, 0))
        apply_status_fill(ws.cell(row=counts_start + offset, column=1))

    category_start = counts_start + 7
    ws.cell(row=category_start, column=1, value="Requirement outcome categories")
    ws.cell(row=category_start, column=1).fill = SECTION_FILL
    ws.cell(row=category_start, column=1).font = Font(bold=True)
    category_counts = Counter(
        client_category(req) for req in as_rows(data.get("requirements"), "requirements")
    )
    for offset, (category, count) in enumerate(sorted(category_counts.items()), start=1):
        ws.cell(row=category_start + offset, column=1, value=category)
        ws.cell(row=category_start + offset, column=2, value=count)

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = WRAP_ALIGNMENT
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 42
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 80
    ws.column_dimensions["F"].width = 50
    ws.freeze_panes = "A3"


def add_run_context(wb: Workbook, run: dict[str, Any]) -> None:
    ws = wb.create_sheet("Run Context")
    ws.append(["field", "value"])
    for key, value in run.items():
        ws.append([key, serialize(value)])
    style_table(ws)


def _generic_rows(rows: list[dict[str, Any]], headers: list[str]) -> list[dict[str, Any]]:
    return [{header: row.get(header) for header in headers} for row in rows]


def build_workbook(
    data: dict[str, Any],
    output: Path,
    warnings: list[str] | None = None,
) -> None:
    warnings = warnings or []
    wb = Workbook()
    add_client_summary(wb, data, warnings)
    add_table_sheet(wb, "Requirement Matrix", REQUIREMENT_HEADERS, requirement_rows(data))
    add_table_sheet(wb, "Journey Coverage", JOURNEY_HEADERS, journey_rows(data))
    add_table_sheet(wb, "Event Evidence", EVENT_HEADERS, event_rows(data))
    add_table_sheet(wb, "Tag Evidence", TAG_HEADERS, tag_rows(data))
    add_table_sheet(wb, "Consent", CONSENT_HEADERS, consent_rows(data))
    add_table_sheet(
        wb,
        "Unexpected Events-Tags",
        UNEXPECTED_HEADERS,
        _generic_rows(as_rows(data.get("unexpected"), "unexpected"), UNEXPECTED_HEADERS),
    )
    add_table_sheet(
        wb,
        "Blockers",
        BLOCKER_HEADERS,
        _generic_rows(as_rows(data.get("blockers"), "blockers"), BLOCKER_HEADERS),
    )
    add_table_sheet(
        wb,
        "Evidence Catalogue",
        EVIDENCE_HEADERS,
        _generic_rows(as_rows(data.get("evidence"), "evidence"), EVIDENCE_HEADERS),
    )
    add_run_context(wb, data.get("run", {}))

    evidence_ws = wb["Evidence Catalogue"]
    path_column = EVIDENCE_HEADERS.index("path_or_url") + 1
    for row_index in range(2, evidence_ws.max_row + 1):
        cell = evidence_ws.cell(row=row_index, column=path_column)
        target = str(cell.value or "").strip()
        if target and (
            target.startswith(("https://", "http://"))
            or Path(target).is_absolute()
            or Path(target).exists()
        ):
            cell.hyperlink = target
            cell.style = "Hyperlink"

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    validate_workbook(output, data)


def validate_workbook(path: Path, data: dict[str, Any]) -> None:
    workbook = load_workbook(path, read_only=False, data_only=False)
    try:
        missing = [title for title in REQUIRED_SHEETS if title not in workbook.sheetnames]
        if missing:
            raise ReportValidationError(
                "Generated workbook is missing sheets: " + ", ".join(missing)
            )
        if workbook.sheetnames != REQUIRED_SHEETS:
            raise ReportValidationError("Generated workbook sheets are not in the required order.")
        expected_rows = {
            "Requirement Matrix": len(as_rows(data.get("requirements"), "requirements")) + 1,
            "Journey Coverage": len(as_rows(data.get("requirements"), "requirements")) + 1,
            "Event Evidence": len(as_rows(data.get("requirements"), "requirements")) + 1,
            "Tag Evidence": len(tag_rows(data)) + 1,
            "Consent": len(consent_rows(data)) + 1,
            "Unexpected Events-Tags": len(as_rows(data.get("unexpected"), "unexpected")) + 1,
            "Blockers": len(as_rows(data.get("blockers"), "blockers")) + 1,
            "Evidence Catalogue": len(as_rows(data.get("evidence"), "evidence")) + 1,
        }
        for title, count in expected_rows.items():
            sheet = workbook[title]
            if sheet.max_row != count:
                raise ReportValidationError(
                    f"Generated workbook sheet '{title}' has {sheet.max_row} rows; expected {count}."
                )
            if not sheet.auto_filter.ref:
                raise ReportValidationError(
                    f"Generated workbook sheet '{title}' is missing its filter."
                )
    finally:
        workbook.close()


def main() -> int:
    args = parse_args()
    try:
        data = load_data(args.input)
        warnings = validate(data, strict=args.strict)
        if args.validate_only:
            print("Schema-v2 recette results are valid.")
            if warnings:
                print(f"Completed with {len(warnings)} validation warning(s).")
            return 0
        if not args.output:
            raise ReportValidationError("An output .xlsx path is required unless --validate-only is used.")
        output = Path(args.output)
        if output.suffix.lower() != ".xlsx":
            raise ReportValidationError("Output path must use the .xlsx extension.")
        build_workbook(data, output, warnings)
    except (OSError, json.JSONDecodeError, ReportValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Created {output.resolve()}")
    if warnings:
        print(f"Completed with {len(warnings)} validation warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
