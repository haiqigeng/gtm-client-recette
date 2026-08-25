#!/usr/bin/env python3
"""Render the single final XLSX from deterministic completed-event records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

LAYER_ORDER = (
    "Page/action reality",
    "Data Layer API Call",
    "GTM Tags",
    "Browser request",
    "Surrounding behavior",
)
PRIORITY = {
    "NOT_APPLICABLE": 0,
    "PASS": 1,
    "PENDING": 2,
    "REVIEW": 3,
    "BLOCKED": 4,
    "FAIL": 5,
}
STATUS_FILL = {
    "PASS": "C6EFCE",
    "FAIL": "FFC7CE",
    "BLOCKED": "F4B183",
    "REVIEW": "FFEB9C",
    "PENDING": "D9EAF7",
    "NOT_APPLICABLE": "E7E6E6",
}


def _worst(statuses: list[str]) -> str:
    valid = [status for status in statuses if status in PRIORITY]
    return max(valid, key=PRIORITY.__getitem__) if valid else "BLOCKED"


def _reason(layer: dict[str, Any]) -> str:
    non_pass = next(
        (
            check
            for check in layer.get("checks", [])
            if check.get("status") in {"FAIL", "BLOCKED", "REVIEW", "PENDING"}
        ),
        None,
    )
    return str(non_pass.get("reason")) if non_pass else "All checks passed."


def _target(layer: dict[str, Any]) -> str:
    targets = [
        str(check["check_next"])
        for check in layer.get("checks", [])
        if check.get("check_next")
        and check.get("status") in {"FAIL", "BLOCKED", "REVIEW", "PENDING"}
    ]
    return "; ".join(dict.fromkeys(targets))


def _style_sheet(sheet: Any) -> None:
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith(("=", "+", "-", "@")):
                cell.value = "'" + cell.value
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if isinstance(cell.value, str) and cell.value in STATUS_FILL:
                cell.fill = PatternFill("solid", fgColor=STATUS_FILL[cell.value])
    for column in range(1, sheet.max_column + 1):
        values = [str(sheet.cell(row, column).value or "") for row in range(1, sheet.max_row + 1)]
        width = min(max(max(map(len, values), default=8) + 2, 10), 52)
        sheet.column_dimensions[get_column_letter(column)].width = width


def _latest_layers(event_results: list[dict[str, Any]]) -> dict[str, str]:
    output = {}
    for name in LAYER_ORDER:
        statuses = [
            layer["status"]
            for result in event_results
            for layer in result.get("layers", [])
            if layer.get("layer") == name
        ]
        output[name] = _worst(statuses)
    return output


def render_report(
    plan: dict[str, Any],
    results: list[dict[str, Any]],
    output: Path | str,
) -> None:
    """Write and reopen-validate the only supported final workbook."""
    target = Path(output).resolve()
    if target.exists():
        raise ValueError(f"Final workbook already exists: {target}")
    if not results:
        raise ValueError("Cannot render a report without completed event evidence.")

    workbook = Workbook()
    workbook.properties.title = "GTM Client Recette v8"
    workbook.properties.subject = "Five-layer client-side GTM acceptance results"
    conclusion = workbook.active
    conclusion.title = "Conclusion"
    conclusion.append(
        [
            "Order",
            "Event",
            "Technical event",
            "Scenarios",
            *LAYER_ORDER,
            "Overall",
            "Why",
        ]
    )
    by_event: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_event.setdefault(str(result["event_id"]), []).append(result)
    for event in plan["events"]:
        event_results = by_event.get(event["event_id"], [])
        if not event_results:
            raise ValueError(f"Missing final results for {event['label']}.")
        layers = _latest_layers(event_results)
        overall = _worst(list(layers.values()))
        reasons = [
            _reason(layer)
            for result in event_results
            for layer in result["layers"]
            if layer["status"] != "PASS"
        ]
        conclusion.append(
            [
                event["plan_order"],
                event["label"],
                event["event_name"],
                len(event_results),
                *[layers[name] for name in LAYER_ORDER],
                overall,
                "; ".join(dict.fromkeys(reasons)) or "All scenarios and layers passed.",
            ]
        )

    feedback = workbook.create_sheet("Event feedback")
    feedback.append(
        [
            "Order",
            "Event",
            "Scenario",
            "Material signature",
            "Coverage final",
            "Layer",
            "Status",
            "Why",
            "Passed checks",
            "Total checks",
            "Check next",
        ]
    )
    order = {event["event_id"]: event["plan_order"] for event in plan["events"]}
    ordered_results = sorted(
        results, key=lambda result: (order[result["event_id"]], result["action_id"])
    )
    for result in ordered_results:
        for layer in result["layers"]:
            feedback.append(
                [
                    order[result["event_id"]],
                    result["label"],
                    result["scenario"]["id"],
                    result["scenario"]["signature"],
                    result["coverage"]["complete"],
                    layer["layer"],
                    layer["status"],
                    _reason(layer),
                    layer["passed"],
                    layer["total"],
                    _target(layer),
                ]
            )

    checks = workbook.create_sheet("Checks")
    checks.append(
        [
            "Order",
            "Event",
            "Scenario",
            "Layer",
            "Status",
            "Check",
            "Field path",
            "Expected",
            "Observed",
            "Why",
            "Check next",
        ]
    )
    for result in ordered_results:
        for layer in result["layers"]:
            for check in layer["checks"]:
                checks.append(
                    [
                        order[result["event_id"]],
                        result["label"],
                        result["scenario"]["id"],
                        layer["layer"],
                        check["status"],
                        check["check"],
                        check.get("path"),
                        check.get("expected"),
                        check.get("observed"),
                        check["reason"],
                        check.get("check_next"),
                    ]
                )

    for sheet in workbook.worksheets:
        _style_sheet(sheet)
    target.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(target)
    workbook.close()

    validation = load_workbook(target, read_only=True, data_only=False)
    try:
        if validation.sheetnames != ["Conclusion", "Event feedback", "Checks"]:
            raise ValueError("Final workbook sheet contract is invalid.")
        expected_feedback_rows = 1 + len(results) * len(LAYER_ORDER)
        if validation["Event feedback"].max_row != expected_feedback_rows:
            raise ValueError("Final workbook does not contain five feedback rows per scenario.")
        if validation["Conclusion"].max_row != 1 + len(plan["events"]):
            raise ValueError("Final workbook conclusion is not plan-complete.")
    finally:
        validation.close()
