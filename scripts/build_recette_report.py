#!/usr/bin/env python3
"""Build an evidence-backed GTM Preview recette workbook from normalized JSON."""

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

VALID_STATUSES = {"PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_TESTED"}
STATUS_PRIORITY = ("FAIL", "BLOCKED", "REVIEW", "NOT_TESTED", "PASS")
STATUS_FILLS = {
    "PASS": "C6EFCE",
    "FAIL": "FFC7CE",
    "BLOCKED": "F4B183",
    "REVIEW": "FFF2CC",
    "NOT_TESTED": "D9E1F2",
}
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)
SUBHEADER_FILL = PatternFill("solid", fgColor="D9EAF7")
THIN_BORDER = Border(bottom=Side(style="thin", color="B7C9D6"))
WRAP_ALIGNMENT = Alignment(vertical="top", wrap_text=True)

MATRIX_HEADERS = [
    "comparison_id",
    "journey_id",
    "event_order",
    "data_layer_event",
    "data_layer_field",
    "tag_name",
    "tag_configuration_field",
    "tracking_plan_value",
    "data_layer_value",
    "tag_configuration_value",
    "resolved_tag_value",
    "status",
    "mismatch_or_reason",
    "evidence_ids",
    "notes",
]

SHEETS: dict[str, list[str]] = {
    "Event Evidence": [
        "event_id",
        "journey_id",
        "step_id",
        "event_order",
        "event_name",
        "occurred_at",
        "expected",
        "api_call",
        "data_layer_snapshot",
        "status",
        "evidence_ids",
        "notes",
    ],
    "Evidence": [
        "evidence_id",
        "kind",
        "source",
        "path_or_url",
        "captured_at",
        "description",
    ],
}

DATA_KEYS = {
    "Event Evidence": "events",
    "Evidence": "evidence",
}
COLLECTION_KEYS = (
    "journeys",
    "checks",
    "events",
    "tags",
    "consent_checks",
    "unexpected",
    "evidence",
    "comparisons",
)


class ReportValidationError(ValueError):
    """Raised when normalized report data fails validation."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        help="Normalized JSON path, or - to read JSON from standard input.",
    )
    parser.add_argument("output", help="Destination .xlsx path.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Reject missing evidence, statuses, or wanted-tag non-firing reasons.",
    )
    return parser.parse_args()


def load_data(source: str) -> dict[str, Any]:
    raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ReportValidationError("Top-level JSON value must be an object.")
    return data


def as_rows(value: Any, key: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ReportValidationError(f"'{key}' must be an array.")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ReportValidationError(f"'{key}' row {index} must be an object.")
        rows.append(item)
    return rows


def evidence_ids(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def status_of(row: dict[str, Any]) -> str:
    return str(row.get("status", "")).strip().upper()


def validate(data: dict[str, Any], strict: bool) -> list[str]:
    warnings: list[str] = []
    errors: list[str] = []
    run = data.get("run", {})
    if not isinstance(run, dict):
        raise ReportValidationError("'run' must be an object.")
    if strict:
        for field in ("site_url", "container_id", "workspace", "tracking_plan_source"):
            if not str(run.get(field, "")).strip():
                errors.append(f"run: missing required field '{field}'")

    rows = {key: as_rows(data.get(key), key) for key in COLLECTION_KEYS}
    checks = rows["checks"]
    comparisons = rows["comparisons"]
    evidence = rows["evidence"]
    if not checks:
        message = "At least one detailed check is required."
        if strict:
            raise ReportValidationError(message)
        warnings.append(message)
    if not evidence:
        message = "At least one evidence row is required."
        if strict:
            raise ReportValidationError(message)
        warnings.append(message)
    if not comparisons:
        message = "At least one canonical comparison row is required."
        if strict:
            raise ReportValidationError(message)
        warnings.append(message)

    evidence_catalog = [str(row.get("evidence_id", "")).strip() for row in evidence]
    nonempty_evidence = [item for item in evidence_catalog if item]
    duplicates = sorted(item for item, count in Counter(nonempty_evidence).items() if count > 1)
    if duplicates:
        raise ReportValidationError(
            "Duplicate evidence IDs: " + ", ".join(duplicates)
        )
    known_evidence = set(nonempty_evidence)

    status_collections = {
        "checks": checks,
        "journeys": rows["journeys"],
        "events": rows["events"],
        "tags": rows["tags"],
        "consent_checks": rows["consent_checks"],
        "unexpected": rows["unexpected"],
        "comparisons": rows["comparisons"],
    }
    for key, collection in status_collections.items():
        for index, row in enumerate(collection, start=1):
            status = status_of(row)
            if not status:
                errors.append(f"{key} row {index}: missing status")
            elif status not in VALID_STATUSES:
                errors.append(f"{key} row {index}: invalid status '{status}'")

    evidence_collections = {
        "checks": checks,
        "events": rows["events"],
        "tags": rows["tags"],
        "consent_checks": rows["consent_checks"],
        "unexpected": rows["unexpected"],
        "comparisons": rows["comparisons"],
    }
    for key, collection in evidence_collections.items():
        for index, row in enumerate(collection, start=1):
            references = evidence_ids(row.get("evidence_ids"))
            if strict and not references:
                errors.append(f"{key} row {index}: missing evidence_ids")
            unknown = sorted(set(references) - known_evidence)
            if unknown:
                errors.append(
                    f"{key} row {index}: unknown evidence IDs {', '.join(unknown)}"
                )

    for index, row in enumerate(comparisons, start=1):
        for field in (
            "comparison_id",
            "data_layer_event",
            "tag_name",
            "tracking_plan_value",
            "data_layer_value",
            "tag_configuration_value",
        ):
            if not str(row.get(field, "")).strip():
                errors.append(f"comparisons row {index}: missing '{field}'")

    for index, row in enumerate(rows["tags"], start=1):
        expected = str(row.get("expected_status", "")).strip().lower().replace(" ", "_")
        actual = str(row.get("actual_status", "")).strip().lower().replace(" ", "_")
        if expected == "fired" and actual != "fired":
            if not str(row.get("non_firing_reason", "")).strip():
                errors.append(f"tags row {index}: wanted tag lacks non_firing_reason")
            if not str(row.get("reason_source", "")).strip():
                errors.append(f"tags row {index}: wanted tag lacks reason_source")

    for index, row in enumerate(checks, start=1):
        check_type = str(row.get("check_type", "")).strip().lower()
        expected = str(row.get("expected", "")).strip().lower().replace(" ", "_")
        actual = str(row.get("actual", "")).strip().lower().replace(" ", "_")
        if check_type in {"tag_firing", "tag_non_firing_reason"} and expected == "fired" and actual != "fired":
            if not str(row.get("non_firing_reason", "")).strip():
                errors.append(f"checks row {index}: wanted tag lacks non_firing_reason")
            if not str(row.get("reason_source", "")).strip():
                errors.append(f"checks row {index}: wanted tag lacks reason_source")

    if errors:
        message = "\n".join(errors)
        if strict:
            raise ReportValidationError(message)
        warnings.extend(errors)
    return warnings


def serialize(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ": "))
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def overall_status(data: dict[str, Any]) -> str:
    statuses: list[str] = []
    for key in ("comparisons", "checks", "events", "tags", "consent_checks", "unexpected"):
        for row in as_rows(data.get(key), key):
            status = status_of(row)
            if status in VALID_STATUSES:
                statuses.append(status)
    if not statuses:
        return "NOT_TESTED"
    for candidate in STATUS_PRIORITY:
        if candidate in statuses:
            return candidate
    return "NOT_TESTED"


def apply_status_fill(cell: Cell) -> None:
    status = str(cell.value or "").strip().upper()
    colour = STATUS_FILLS.get(status)
    if colour:
        cell.fill = PatternFill("solid", fgColor=colour)
        cell.font = Font(bold=True)


def style_table(ws, status_column: int | None = None) -> None:
    ws.freeze_panes = "A2"
    if ws.max_row >= 1 and ws.max_column >= 1:
        ws.auto_filter.ref = ws.dimensions
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = WRAP_ALIGNMENT
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_ALIGNMENT
            cell.border = THIN_BORDER
        if status_column:
            apply_status_fill(row[status_column - 1])

    for column_index, column_cells in enumerate(ws.columns, start=1):
        values = [str(cell.value or "") for cell in column_cells]
        longest = max((len(value) for value in values), default=0)
        header = str(column_cells[0].value or "")
        cap = 80 if header in {
            "api_call",
            "data_layer_snapshot",
            "expected_parameters",
            "actual_parameters",
            "variable_values",
            "notes",
            "description",
            "non_firing_reason",
        } else 45
        ws.column_dimensions[get_column_letter(column_index)].width = min(max(longest + 2, 12), cap)


def add_table_sheet(wb: Workbook, title: str, headers: list[str], rows: Iterable[dict[str, Any]]) -> None:
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        ws.append([serialize(row.get(header)) for header in headers])

    status_column = headers.index("status") + 1 if "status" in headers else None
    style_table(ws, status_column)

    if title == "Evidence":
        path_column = headers.index("path_or_url") + 1
        for row_index in range(2, ws.max_row + 1):
            cell = ws.cell(row=row_index, column=path_column)
            target = str(cell.value or "").strip()
            if target and (target.startswith(("https://", "http://")) or Path(target).exists()):
                cell.hyperlink = target
                cell.style = "Hyperlink"


def build_validation_matrix(data: dict[str, Any]) -> list[dict[str, Any]]:
    comparisons = as_rows(data.get("comparisons"), "comparisons")
    if comparisons:
        return comparisons

    matrix: list[dict[str, Any]] = []
    for tag in as_rows(data.get("tags"), "tags"):
        reason = str(tag.get("non_firing_reason", "")).strip()
        matrix.append(
            {
                "comparison_id": tag.get("tag_check_id"),
                "journey_id": tag.get("journey_id"),
                "event_order": tag.get("event_order", ""),
                "data_layer_event": tag.get("event_name"),
                "data_layer_field": "_event / relevant dataLayer variables",
                "tag_name": tag.get("tag_name"),
                "tag_configuration_field": "event and configured parameters",
                "tracking_plan_value": tag.get("expected_parameters") or tag.get("expected_status"),
                "data_layer_value": tag.get("variable_values"),
                "tag_configuration_value": tag.get("actual_parameters"),
                "resolved_tag_value": tag.get("actual_status"),
                "status": tag.get("status"),
                "mismatch_or_reason": reason or tag.get("notes"),
                "evidence_ids": tag.get("evidence_ids"),
                "notes": "",
            }
        )

    for check in as_rows(data.get("checks"), "checks"):
        if str(check.get("check_type", "")) not in {"data_layer_state", "variable", "tag_parameter"}:
            continue
        matrix.append(
            {
                "comparison_id": check.get("check_id"),
                "journey_id": check.get("journey_id"),
                "event_order": check.get("event_order"),
                "data_layer_event": check.get("event_name"),
                "data_layer_field": check.get("field_path") or check.get("variable_name"),
                "tag_name": check.get("tag_name"),
                "tag_configuration_field": check.get("object_name"),
                "tracking_plan_value": check.get("expected"),
                "data_layer_value": check.get("actual") if check.get("check_type") != "tag_parameter" else "",
                "tag_configuration_value": check.get("actual") if check.get("check_type") == "tag_parameter" else "",
                "resolved_tag_value": "",
                "status": check.get("status"),
                "mismatch_or_reason": check.get("non_firing_reason") or check.get("notes"),
                "evidence_ids": check.get("evidence_ids"),
                "notes": "",
            }
        )
    return matrix


def add_summary(wb: Workbook, data: dict[str, Any], warnings: list[str]) -> None:
    ws = wb.active
    ws.title = "Summary"
    run = data.get("run", {})
    matrix = build_validation_matrix(data)
    counts = Counter(status_of(row) for row in matrix)
    report_title = str(run.get("report_title") or "GTM Preview Recette Results")
    overall = overall_status(data)

    ws["A1"] = report_title
    ws["A1"].font = Font(size=18, bold=True, color="1F4E78")
    ws["A3"] = "Overall status"
    ws["B3"] = overall
    ws["A4"] = "Generated at"
    ws["B4"] = datetime.now(UTC).isoformat(timespec="seconds")
    ws["A5"] = "Validation rows"
    ws["B5"] = len(matrix)
    ws["A6"] = "Evidence items"
    ws["B6"] = len(as_rows(data.get("evidence"), "evidence"))
    evidence_linked_rows = sum(bool(evidence_ids(row.get("evidence_ids"))) for row in matrix)
    ws["A7"] = "Evidence-linked rows"
    ws["B7"] = f"{evidence_linked_rows}/{len(matrix)}"
    ws["A8"] = "Validation warnings"
    ws["B8"] = len(warnings)
    apply_status_fill(ws["B3"])

    ws["A10"] = "Status"
    ws["B10"] = "Count"
    for cell in ws[10]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for offset, status in enumerate(STATUS_PRIORITY, start=11):
        ws.cell(row=offset, column=1, value=status)
        ws.cell(row=offset, column=2, value=counts.get(status, 0))
        apply_status_fill(ws.cell(row=offset, column=1))

    start = 19
    ws.cell(row=start, column=1, value="Run context")
    ws.cell(row=start, column=1).fill = SUBHEADER_FILL
    ws.cell(row=start, column=1).font = Font(bold=True)
    for row_offset, (key, value) in enumerate(run.items(), start=start + 1):
        ws.cell(row=row_offset, column=1, value=str(key))
        ws.cell(row=row_offset, column=2, value=serialize(value))

    warning_start = start + max(len(run), 1) + 2
    if warnings:
        ws.cell(row=warning_start, column=1, value="Validation warnings")
        ws.cell(row=warning_start, column=1).fill = SUBHEADER_FILL
        ws.cell(row=warning_start, column=1).font = Font(bold=True)
        for index, warning in enumerate(warnings, start=warning_start + 1):
            ws.cell(row=index, column=1, value=warning)

    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = WRAP_ALIGNMENT
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 80
    ws.freeze_panes = "A3"


def add_run_context(wb: Workbook, run: dict[str, Any]) -> None:
    ws = wb.create_sheet("Run Context")
    ws.append(["field", "value"])
    for key, value in run.items():
        ws.append([key, serialize(value)])
    style_table(ws)


def build_workbook(data: dict[str, Any], output: Path, warnings: list[str]) -> None:
    wb = Workbook()
    add_summary(wb, data, warnings)
    add_table_sheet(wb, "Validation Matrix", MATRIX_HEADERS, build_validation_matrix(data))
    wb.move_sheet(wb["Validation Matrix"], offset=-1)
    wb.active = 0
    for title, headers in SHEETS.items():
        add_table_sheet(wb, title, headers, as_rows(data.get(DATA_KEYS[title]), DATA_KEYS[title]))
    add_run_context(wb, data.get("run", {}))
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)

    # Re-open the generated artifact so corrupt or incomplete writes fail immediately.
    check = load_workbook(output, read_only=True, data_only=False)
    missing = [title for title in ["Summary", "Validation Matrix", *SHEETS.keys(), "Run Context"] if title not in check.sheetnames]
    check.close()
    if missing:
        raise ReportValidationError("Generated workbook is missing sheets: " + ", ".join(missing))


def main() -> int:
    args = parse_args()
    try:
        data = load_data(args.input)
        warnings = validate(data, args.strict)
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
