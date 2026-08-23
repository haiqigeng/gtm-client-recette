"""Deterministic event feedback and final reports from one canonical result model."""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Font, PatternFill

from value_semantics import parse_iso_timestamp

from .constants import DOMAIN_LABELS, DOMAINS, OPERATION_COUNTERS, status_label
from .correlate import action_windows
from .judge import judge_run
from .state import RunPaths, StateError, load_plan, read_stream


def formula_safe_text(value: Any) -> str:
    text = str(value if value is not None else "")
    return "'" + text if text.startswith(("=", "+", "-", "@")) else text


def set_safe_cell(cell: Cell, value: Any) -> Cell:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, str):
        value = formula_safe_text(value)
    cell.value = value
    return cell


def markdown_safe(value: Any) -> str:
    text = (
        json.dumps(value, ensure_ascii=False, sort_keys=True)
        if isinstance(value, (dict, list))
        else str(value if value is not None else "")
    )
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _append_row(sheet: Any, values: Iterable[Any]) -> None:
    row_values = list(values)
    sheet.append([None] * len(row_values))
    row_index = sheet.max_row
    for column, value in enumerate(row_values, start=1):
        set_safe_cell(sheet.cell(row=row_index, column=column), value)


def _style_sheet(sheet: Any) -> None:
    if sheet.max_row:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        values = [len(str(cell.value or "")) for cell in column[:200]]
        sheet.column_dimensions[column[0].column_letter].width = min(max(values or [8]) + 2, 60)
        for cell in column:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _status_text(status: str) -> str:
    return f"{status_label(status)} ({status})" if status in {"PASS", "FAIL"} else status


def render_action_pulse(value: dict[str, Any]) -> str:
    defects = value.get("immediate_defects", {})
    lines = [
        f"Action: {value.get('action_id')}",
        "Observed: " + (", ".join(value.get("observed_events", [])) or "no named event yet"),
        "Immediate defects: "
        + (
            "; ".join(
                f"{key}={', '.join(map(str, items))}" for key, items in defects.items() if items
            )
            or "none from current deltas"
        ),
        "Awaiting: " + ", ".join(value.get("awaiting", [])),
    ]
    return "\n".join(lines) + "\n"


def render_event_feedback(result: dict[str, Any], *, compact: bool = False) -> str:
    lines = [
        f"Event: {result.get('event_name') or result.get('event_id')} - {_status_text(result['status'])}",
        f"Final: {'yes' if result.get('final') else 'no'}",
        "Domain summary: "
        + " | ".join(
            f"{DOMAIN_LABELS[domain]} {result.get('domains', {}).get(domain, {}).get('status', 'NOT_APPLICABLE')}"
            for domain in DOMAINS
        ),
        f"Why: {result.get('reason')}",
        (
            "Coverage: "
            + str(result.get("coverage", {}).get("mode") or "pending")
            + (" - complete" if result.get("coverage", {}).get("complete") else " - incomplete")
        ),
        "",
    ]
    scenarios = result.get("scenarios", [])
    if len(scenarios) > 1:
        lines.extend(
            [
                "| Scenario | Reality | Source | GTM | Delivery | Behavior | Safety | Overall |",
                "|---|---|---|---|---|---|---|---|",
            ]
        )
        for scenario in scenarios:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_safe(scenario.get("label")),
                        *[
                            str(scenario.get("domains", {}).get(domain, {}).get("status", "N/A"))
                            for domain in DOMAINS
                        ],
                        str(scenario.get("status")),
                    ]
                )
                + " |"
            )
        lines.append("")
    if compact:
        non_pass = [row for row in result.get("inspections", []) if row.get("status") != "PASS"]
        for row in non_pass[:12]:
            lines.append(
                f"- {row.get('inspection_target')}: {row.get('status')} - {row.get('reason')}"
            )
        return "\n".join(lines).rstrip() + "\n"
    lines.extend(
        [
            "| Inspection target | Domain | Status | Observed | Expected | Check next | Evidence |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in result.get("inspections", []):
        lines.append(
            "| "
            + " | ".join(
                markdown_safe(value)
                for value in (
                    row.get("inspection_target"),
                    DOMAIN_LABELS.get(str(row.get("domain")), row.get("domain")),
                    row.get("status"),
                    row.get("observed"),
                    row.get("expected"),
                    row.get("check_next") or "-",
                    ", ".join(row.get("evidence", [])) or "-",
                )
            )
            + " |"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_conclusion(result: dict[str, Any]) -> str:
    lines = [
        "# GTM Client Recette Conclusion",
        "",
        f"Run: `{result.get('run_id')}`",
        f"Overall status: **{_status_text(result.get('status', 'PENDING'))}**",
        "",
        "| Event | Reality | Source | GTM | Delivery | Behavior | Safety | Status | Why |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for event in result.get("events", []):
        lines.append(
            "| "
            + " | ".join(
                markdown_safe(value)
                for value in (
                    event.get("event_name") or event.get("event_id"),
                    *[
                        event.get("domains", {}).get(domain, {}).get("status", "NOT_APPLICABLE")
                        for domain in DOMAINS
                    ],
                    event.get("status"),
                    event.get("reason"),
                )
            )
            + " |"
        )
    lines.extend(["", "## Event details", ""])
    for event in result.get("events", []):
        lines.append(render_event_feedback(event).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def defect_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for event in result.get("events", []):
        for inspection in event.get("inspections", []):
            if inspection.get("status") in {"PASS", "NOT_APPLICABLE"}:
                continue
            rows.append(
                {
                    "event_id": event.get("event_id"),
                    "event_name": event.get("event_name"),
                    "scenario_id": inspection.get("scenario_id"),
                    "action_id": inspection.get("action_id"),
                    "domain": inspection.get("domain"),
                    "inspection_target": inspection.get("inspection_target"),
                    "status": inspection.get("status"),
                    "reason_code": inspection.get("reason_code"),
                    "reason": inspection.get("reason"),
                    "check_next": inspection.get("check_next"),
                    "evidence": inspection.get("evidence", []),
                }
            )
    return rows


def telemetry_view(plan: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    kinds = defaultdict(int)
    for record in records:
        kinds[str(record.get("kind"))] += 1
    created = parse_iso_timestamp(plan.get("created_at"))
    first_action = next(
        (
            parse_iso_timestamp(record.get("recorded_at"))
            for record in records
            if record.get("kind") == "ACTION_BEGIN"
        ),
        None,
    )
    first_feedback = next(
        (
            parse_iso_timestamp(record.get("recorded_at"))
            for record in records
            if record.get("kind") == "EVENT_FEEDBACK_ISSUED"
        ),
        None,
    )

    def elapsed(end: Any) -> float | None:
        return round((end - created).total_seconds(), 3) if created and end else None

    operations = {key: 0 for key in OPERATION_COUNTERS}
    for record in records:
        if record.get("kind") != "CAPTURE_HEALTH":
            continue
        observed = record.get("data", {}).get("summary", {}).get("operations", {})
        if not isinstance(observed, dict):
            continue
        for key in OPERATION_COUNTERS:
            value = observed.get(key, 0)
            if isinstance(value, int) and not isinstance(value, bool):
                operations[key] += value

    return {
        "first_action_seconds": elapsed(first_action),
        "first_feedback_seconds": elapsed(first_feedback),
        "actions": kinds["ACTION_BEGIN"],
        "commits": kinds["ACTION_COMMIT"],
        "preview_syncs": kinds["PREVIEW_SYNC"],
        "preview_captures": kinds["CAPTURE_PREVIEW"],
        "network_captures": kinds["CAPTURE_NETWORK"],
        "capability_probes": kinds["CAPTURE_CAPABILITY"],
        "pulses": kinds["ACTION_PULSE"],
        "feedbacks": kinds["EVENT_FEEDBACK_ISSUED"],
        "stream_records": len(records),
        **operations,
    }


def status_view(run_dir: Path | str) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, warnings = read_stream(run_dir)
    result = judge_run(run_dir, plan, records)
    return {
        **result,
        "warnings": warnings,
        "open_actions": [
            action["action_id"] for action in action_windows(records) if action["status"] == "OPEN"
        ],
        "telemetry": telemetry_view(plan, records),
    }


def _workbook(
    plan: dict[str, Any], result: dict[str, Any], records: list[dict[str, Any]]
) -> Workbook:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    _append_row(summary, ["Metric", "Value"])
    for key, value in (
        ("Run ID", result.get("run_id")),
        ("Status", result.get("status")),
        ("Events", len(result.get("events", []))),
        ("Claims", plan.get("claim_count")),
        ("Source kind", plan.get("source", {}).get("kind")),
        ("Source SHA-256", plan.get("source", {}).get("sha256")),
    ):
        _append_row(summary, [key, value])

    events_sheet = workbook.create_sheet("Events")
    _append_row(
        events_sheet,
        [
            "Order",
            "Event ID",
            "Event",
            *[DOMAIN_LABELS[d] for d in DOMAINS],
            "Confidence",
            "Coverage",
            "Status",
            "Final",
            "Why",
        ],
    )
    order = {event["event_id"]: event.get("plan_order") for event in plan.get("events", [])}
    for event in result.get("events", []):
        _append_row(
            events_sheet,
            [
                order.get(event.get("event_id")),
                event.get("event_id"),
                event.get("event_name"),
                *[event.get("domains", {}).get(domain, {}).get("status") for domain in DOMAINS],
                event.get("gates", {}).get("evidence_confidence", {}).get("status"),
                event.get("coverage", {}).get("status"),
                event.get("status"),
                event.get("final"),
                event.get("reason"),
            ],
        )

    scenarios = workbook.create_sheet("Scenarios")
    _append_row(
        scenarios,
        [
            "Event ID",
            "Scenario ID",
            "Scenario",
            "Values",
            "Signature",
            *[DOMAIN_LABELS[d] for d in DOMAINS],
            "Status",
            "Actions",
        ],
    )
    for event in result.get("events", []):
        for scenario in event.get("scenarios", []):
            _append_row(
                scenarios,
                [
                    event.get("event_id"),
                    scenario.get("scenario_id"),
                    scenario.get("label"),
                    scenario.get("values"),
                    scenario.get("behavior_signature"),
                    *[
                        scenario.get("domains", {}).get(domain, {}).get("status")
                        for domain in DOMAINS
                    ],
                    scenario.get("status"),
                    scenario.get("action_ids"),
                ],
            )

    inspections = workbook.create_sheet("Inspections")
    _append_row(
        inspections,
        [
            "Event ID",
            "Scenario ID",
            "Action ID",
            "Domain",
            "Inspection target",
            "Status",
            "Observed",
            "Expected",
            "Reason code",
            "Reason",
            "Check next",
            "Evidence",
        ],
    )
    for event in result.get("events", []):
        for row in event.get("inspections", []):
            _append_row(
                inspections,
                [
                    event.get("event_id"),
                    row.get("scenario_id"),
                    row.get("action_id"),
                    row.get("domain"),
                    row.get("inspection_target"),
                    row.get("status"),
                    row.get("observed"),
                    row.get("expected"),
                    row.get("reason_code"),
                    row.get("reason"),
                    row.get("check_next"),
                    row.get("evidence"),
                ],
            )

    defects = workbook.create_sheet("Defects and limits")
    _append_row(
        defects,
        [
            "Event ID",
            "Scenario",
            "Action ID",
            "Domain",
            "Inspection target",
            "Status",
            "Reason code",
            "Reason",
            "Check next",
            "Evidence",
        ],
    )
    for row in defect_rows(result):
        _append_row(
            defects,
            [
                row.get("event_id"),
                row.get("scenario_id"),
                row.get("action_id"),
                row.get("domain"),
                row.get("inspection_target"),
                row.get("status"),
                row.get("reason_code"),
                row.get("reason"),
                row.get("check_next"),
                row.get("evidence"),
            ],
        )

    evidence = workbook.create_sheet("Evidence index")
    _append_row(
        evidence, ["Record ID", "Sequence", "Kind", "Provenance", "Recorded at", "Evidence path"]
    )
    for record in records:
        reference = record.get("data", {}).get("evidence_ref", {})
        _append_row(
            evidence,
            [
                record.get("record_id"),
                record.get("seq"),
                record.get("kind"),
                record.get("provenance"),
                record.get("recorded_at"),
                reference.get("path") if isinstance(reference, dict) else None,
            ],
        )

    telemetry = workbook.create_sheet("Telemetry")
    _append_row(telemetry, ["Metric", "Value"])
    for key, value in telemetry_view(plan, records).items():
        _append_row(telemetry, [key, value])
    for sheet in workbook.worksheets:
        _style_sheet(sheet)
    return workbook


def validate_workbook(path: Path, expected_event_count: int) -> list[str]:
    errors = []
    try:
        workbook = load_workbook(path, read_only=True, data_only=False)
    except Exception as error:  # pragma: no cover - openpyxl supplies detailed errors
        return [f"Workbook cannot be opened: {error}"]
    try:
        required = {
            "Summary",
            "Events",
            "Scenarios",
            "Inspections",
            "Defects and limits",
            "Evidence index",
            "Telemetry",
        }
        missing = required - set(workbook.sheetnames)
        if missing:
            errors.append("Missing sheets: " + ", ".join(sorted(missing)))
        if (
            "Events" in workbook.sheetnames
            and workbook["Events"].max_row - 1 != expected_event_count
        ):
            errors.append("Events sheet row count differs from the plan.")
    finally:
        workbook.close()
    return errors


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else ["event_id", "status"]
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: formula_safe_text(
                        json.dumps(value, ensure_ascii=False, sort_keys=True)
                        if isinstance(value, (dict, list))
                        else value
                    )
                    for key, value in row.items()
                }
            )
    os.replace(temporary, path)


def _write_text_atomic(path: Path, value: str, *, encoding: str = "utf-8") -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding=encoding, newline="\n")
    os.replace(temporary, path)


def build_reports(run_dir: Path | str) -> dict[str, str]:
    paths = RunPaths.at(run_dir)
    plan = load_plan(run_dir)
    records, warnings = read_stream(run_dir)
    if warnings:
        raise StateError("Cannot build reports from an incomplete stream tail.")
    if not any(record.get("kind") == "RUN_FINISHED" for record in records) or any(
        record.get("kind") == "RUN_REOPENED"
        for record in records[
            1
            + max(
                (
                    index
                    for index, record in enumerate(records)
                    if record.get("kind") == "RUN_FINISHED"
                ),
                default=-1,
            ) :
        ]
    ):
        raise StateError("Final reports can only be built from a currently finished run.")
    result = judge_run(run_dir, plan, records)
    paths.reports.mkdir(exist_ok=True)
    outputs = {
        "json": paths.reports / "results.json",
        "markdown": paths.reports / "conclusion.md",
        "xlsx": paths.reports / "results.xlsx",
        "defects_csv": paths.reports / "defects.csv",
    }
    _write_text_atomic(outputs["json"], json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    _write_text_atomic(outputs["markdown"], render_conclusion(result))
    _write_csv(outputs["defects_csv"], defect_rows(result))
    workbook = _workbook(plan, result, records)
    temporary = outputs["xlsx"].with_name(outputs["xlsx"].stem + ".tmp.xlsx")
    workbook.save(temporary)
    workbook.close()
    os.replace(temporary, outputs["xlsx"])
    errors = validate_workbook(outputs["xlsx"], plan.get("event_count", 0))
    if errors:
        raise StateError("Generated workbook failed validation: " + " | ".join(errors))
    return {key: str(path) for key, path in outputs.items()}
