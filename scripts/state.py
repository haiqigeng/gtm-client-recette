#!/usr/bin/env python3
"""Minimal strict run state for the fixed recette path."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from xlsx_plan import compile_xlsx


class RunError(ValueError):
    """Raised when a run violates the fixed lifecycle contract."""


@dataclass(frozen=True)
class RunPaths:
    root: Path
    plan: Path
    stream: Path
    workbook: Path


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def paths(root: Path | str) -> RunPaths:
    value = Path(root).resolve()
    return RunPaths(
        root=value,
        plan=value / "plan.json",
        stream=value / "events.ndjson",
        workbook=value / "gtm-client-recette-results.xlsx",
    )


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def start_run(plan_path: Path | str, root: Path | str) -> dict[str, Any]:
    run = paths(root)
    if run.root.exists() and any(run.root.iterdir()):
        raise RunError(f"Run directory must be absent or empty: {run.root}")
    run.root.mkdir(parents=True, exist_ok=True)
    try:
        plan = compile_xlsx(plan_path)
    except Exception:
        if not any(run.root.iterdir()):
            run.root.rmdir()
        raise
    plan["run_id"] = "gtm-recette-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    _write_json(run.plan, plan)
    run.stream.touch(exist_ok=False)
    append_record(run.root, "RUN_STARTED", {"run_id": plan["run_id"]}, [])
    return plan


def load_plan(root: Path | str) -> dict[str, Any]:
    path = paths(root).plan
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunError(f"Run plan is missing or corrupted: {error}") from error
    if not isinstance(value, dict) or value.get("schema_version") != "8.0":
        raise RunError("Run plan schema is missing or unsupported.")
    return value


def read_records(root: Path | str) -> list[dict[str, Any]]:
    path = paths(root).stream
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RunError(f"Run event log is unavailable: {error}") from error
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            raise RunError(f"Run event log contains a blank record at line {line_number}.")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RunError(f"Run event log is corrupted at line {line_number}: {error}") from error
        if not isinstance(record, dict) or record.get("sequence") != line_number:
            raise RunError(f"Run event log sequence is invalid at line {line_number}.")
        records.append(record)
    if not records or records[0].get("kind") != "RUN_STARTED":
        raise RunError("Run event log has no valid RUN_STARTED record.")
    return records


def append_record(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    run = paths(root)
    record = {
        "sequence": len(records) + 1,
        "timestamp": now(),
        "kind": kind,
        "data": data,
    }
    with run.stream.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return record


def completed(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record["data"] for record in records if record.get("kind") == "EVENT_COMPLETED"]


def open_action(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    closed = {item.get("action_id") for item in completed(records)}
    for record in reversed(records):
        if record.get("kind") == "ACTION_STARTED":
            action = record["data"]
            if action.get("action_id") not in closed:
                return action
    return None


def is_stopped(records: list[dict[str, Any]]) -> bool:
    return any(record.get("kind") == "RUN_STOPPED" for record in records)


def is_finished(records: list[dict[str, Any]]) -> bool:
    return any(record.get("kind") == "RUN_FINISHED" for record in records)


def consecutive_zero_evidence_events(records: list[dict[str, Any]]) -> int:
    outcomes: list[bool] = []
    active_event: str | None = None
    active_zero_evidence = True
    for result in completed(records):
        event_id = str(result.get("event_id") or "")
        if event_id != active_event:
            active_event = event_id
            active_zero_evidence = True
        active_zero_evidence = active_zero_evidence and result.get("zero_evidence") is True
        if result.get("coverage", {}).get("complete") is True:
            outcomes.append(active_zero_evidence)
            active_event = None

    count = 0
    for zero_evidence in reversed(outcomes):
        if zero_evidence:
            count += 1
        else:
            break
    return count


def next_event(plan: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any] | None:
    by_event: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_event.setdefault(str(result.get("event_id")), []).append(result)
    for event in plan.get("events", []):
        attempts = by_event.get(event["event_id"], [])
        if not attempts or attempts[-1].get("coverage", {}).get("complete") is not True:
            return event
    return None


def start_action(root: Path | str, preview_cursor: int) -> dict[str, Any]:
    plan = load_plan(root)
    records = read_records(root)
    if is_finished(records):
        raise RunError("Run is already finished and cannot be reopened.")
    if is_stopped(records):
        raise RunError("Run stopped after two consecutive zero-evidence events; start a new run.")
    if open_action(records) is not None:
        raise RunError("An action is already open; invalid runs cannot be repaired or skipped.")
    if consecutive_zero_evidence_events(records) >= 2:
        raise RunError("Run reached the two-event zero-evidence stopping condition.")
    results = completed(records)
    if not isinstance(preview_cursor, int) or preview_cursor < 0:
        raise RunError("Next requires a non-negative Preview cursor from the v8 observer.")
    if results and preview_cursor != results[-1].get("preview_cursor"):
        raise RunError("Next Preview cursor must equal the preceding completed action cursor.")
    event = next_event(plan, results)
    if event is None:
        raise RunError(
            "All event coverage is final; run finish instead of starting another action."
        )
    action_number = len(results) + 1
    action = {
        "action_id": f"A-{action_number:04d}",
        "event_id": event["event_id"],
        "event_name": event["event_name"],
        "label": event["label"],
        "is_core": event["is_core"],
        "action": event.get("action"),
        "fields": event["fields"],
        "dimensions": event["dimensions"],
        "selector": event["selector"],
        "preview_cursor": preview_cursor,
    }
    append_record(root, "ACTION_STARTED", action, records)
    return action


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def _covered_values(
    event_id: str,
    results: list[dict[str, Any]],
    current_scenario: dict[str, Any],
) -> dict[str, list[Any]]:
    scenarios = [
        result.get("scenario", {}) for result in results if result.get("event_id") == event_id
    ]
    scenarios.append(current_scenario)
    covered: dict[str, list[Any]] = {}
    for scenario in scenarios:
        values = scenario.get("values", {}) if isinstance(scenario, dict) else {}
        for path, value in values.items():
            candidates = value if isinstance(value, list) else [value]
            bucket = covered.setdefault(str(path), [])
            for candidate in candidates:
                if not any(_same(candidate, existing) for existing in bucket):
                    bucket.append(candidate)
    return covered


def _validate_coverage(
    event: dict[str, Any],
    results: list[dict[str, Any]],
    scenario: dict[str, Any],
    coverage: dict[str, Any],
) -> None:
    previous_ids = {
        result.get("scenario", {}).get("id")
        for result in results
        if result.get("event_id") == event["event_id"]
    }
    if scenario["id"] in previous_ids:
        raise RunError(
            f"Scenario id {scenario['id']!r} was already completed for {event['label']}."
        )
    unreachable = coverage.get("unreachable")
    if not isinstance(unreachable, list):
        raise RunError("Coverage requires an unreachable array, even when it is empty.")
    exclusions: list[tuple[str, Any]] = []
    for item in unreachable:
        if (
            not isinstance(item, dict)
            or not str(item.get("path") or "").strip()
            or "value" not in item
            or not str(item.get("reason") or "").strip()
        ):
            raise RunError("Every unreachable value requires path, value, and reason.")
        exclusions.append((str(item["path"]), item["value"]))
    if not coverage["complete"]:
        return
    observed = _covered_values(event["event_id"], results, scenario)
    missing: list[str] = []
    for dimension in event.get("dimensions", []):
        path = dimension["path"]
        for value in dimension["values"]:
            seen = any(_same(value, item) for item in observed.get(path, []))
            excluded = any(
                path == excluded_path and _same(value, excluded_value)
                for excluded_path, excluded_value in exclusions
            )
            if not seen and not excluded:
                missing.append(f"{path}={value!r}")
    if missing:
        raise RunError(
            "Coverage cannot be complete before planned finite values are tested or "
            "explicitly unreachable: " + ", ".join(missing)
        )


def complete_action(root: Path | str, evidence_path: Path | str) -> dict[str, Any]:
    from judge import event_by_id, judge_event, prepare_bundle

    plan = load_plan(root)
    records = read_records(root)
    if is_finished(records) or is_stopped(records):
        raise RunError("A finished or stopped run cannot accept more evidence.")
    action = open_action(records)
    if action is None:
        raise RunError("No action is open; run next before complete.")
    source = Path(evidence_path).resolve()
    expected_source = paths(root).root / f"evidence-{action['action_id']}.json"
    if source != expected_source or not source.is_file():
        raise RunError(f"Complete requires the exact evidence file {expected_source}.")
    try:
        raw = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunError(f"Evidence bundle is unreadable: {error}") from error
    if not isinstance(raw, dict):
        raise RunError("Evidence bundle root must be an object.")
    safe, digest = prepare_bundle(raw)
    _write_json(source, safe)
    event = event_by_id(plan, action["event_id"])
    result = judge_event(event, action, safe)
    _validate_coverage(
        event,
        completed(records),
        result["scenario"],
        result["coverage"],
    )
    result["evidence_sha256"] = digest
    result["evidence_file"] = source.name
    completion = append_record(root, "EVENT_COMPLETED", result, records)
    records.append(completion)
    stopped = consecutive_zero_evidence_events(records) >= 2
    if stopped:
        append_record(
            root,
            "RUN_STOPPED",
            {
                "reason": "Two consecutive events had all five layers BLOCKED and no attributable evidence.",
                "after_action_id": result["action_id"],
            },
            records,
        )
    return {"result": result, "stopped": stopped}


def finish_run(root: Path | str) -> Path:
    from report import render_report

    plan = load_plan(root)
    records = read_records(root)
    if is_finished(records):
        raise RunError("Run is already finished and cannot be rendered again.")
    if is_stopped(records):
        raise RunError("A zero-evidence-stopped run cannot produce a final workbook.")
    if open_action(records) is not None:
        raise RunError("The open action must be completed before finish.")
    if next_event(plan, completed(records)) is not None:
        raise RunError(
            "Every event needs a final material-scenario coverage decision before finish."
        )
    output = paths(root).workbook
    render_report(plan, completed(records), output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    append_record(
        root,
        "RUN_FINISHED",
        {"workbook": output.name, "sha256": digest},
        records,
    )
    return output
