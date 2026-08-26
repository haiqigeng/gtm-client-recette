#!/usr/bin/env python3
"""Atomic forward-only lifecycle for one scenario per canonical event."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RunError(ValueError):
    """Raised when the sole run lifecycle is violated."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _paths(root: Path | str) -> dict[str, Path]:
    value = Path(root).resolve()
    return {
        "root": value,
        "plan": value / "inspection-plan.json",
        "stream": value / "events.ndjson",
        "workbook": value / "gtm-client-recette-results.xlsx",
    }


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _append(root: Path | str, kind: str, data: dict[str, Any]) -> None:
    run = _paths(root)
    if run["stream"].stat().st_size == 0:
        if kind != "RUN_STARTED":
            raise RunError("The first event-log record must be RUN_STARTED.")
        records = []
    else:
        records = read_records(root)
    record = {"sequence": len(records) + 1, "timestamp": _now(), "kind": kind, "data": data}
    with run["stream"].open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def resolve_workbook_input(reference: Path | str) -> dict[str, str]:
    """Resolve one workbook from an exact path, filename, or bounded location hint."""
    if not isinstance(reference, (str, Path)) or not str(reference).strip():
        raise RunError("Workbook input must name an XLSX or describe where it is located.")
    text = str(reference).strip().strip('"')
    workspace = _workspace_root()
    downloads = Path.home() / "Downloads"
    direct = Path(text).expanduser()
    direct_candidates = [direct] if direct.is_absolute() else [workspace / direct]
    candidates = {path.resolve() for path in direct_candidates if path.is_file()}
    exact = [path for path in candidates if path.suffix.casefold() == ".xlsx"]
    if len(exact) == 1:
        return preflight_run(exact[0])
    names = {
        Path(match.group(0).strip('"')).name
        for match in re.finditer(r"[^\r\n<>|?*]+?\.xlsx\b", text, re.I)
    }
    roots = [workspace]
    if direct.is_dir() and direct.resolve() not in roots:
        roots.append(direct.resolve())
    if downloads.is_dir() and downloads.resolve() != workspace:
        roots.append(downloads.resolve())
    for root in roots:
        for name in names:
            candidates.update(
                path.resolve()
                for path in root.rglob(name)
                if path.is_file() and not path.name.startswith("~$")
            )
    if not names:
        hinted_roots = [
            root for root in roots if root.name.casefold() in text.casefold() or root == workspace
        ]
        for root in hinted_roots:
            candidates.update(
                path.resolve()
                for path in root.glob("*.xlsx")
                if path.is_file() and not path.name.startswith("~$")
            )
    candidates = {path for path in candidates if path.suffix.casefold() == ".xlsx"}
    if not candidates:
        raise RunError("No readable XLSX matches the supplied name or location.")
    if len(candidates) != 1:
        listed = ", ".join(str(path) for path in sorted(candidates))
        raise RunError(f"Workbook input is ambiguous; choose one exact XLSX: {listed}")
    source = next(iter(candidates))
    return preflight_run(source)


def preflight_run(plan_path: Path | str) -> dict[str, str]:
    """Fail before extraction unless the resolved input and workspace are usable."""
    source = Path(plan_path).resolve()
    if source.suffix.casefold() != ".xlsx" or not source.is_file():
        raise RunError("Preflight requires one existing .xlsx tracking plan.")
    output = _workspace_root()
    probe = output / f".{source.stem}.gtm-client-recette-write-test-{os.getpid()}"
    try:
        with probe.open("x", encoding="utf-8") as handle:
            handle.write("preflight\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise RunError(f"Active workspace is not writable: {error}") from error
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError as error:
            raise RunError(f"Cannot remove the output preflight file: {error}") from error
    return {"plan_path": str(source), "output_directory": str(output)}


def start_run(plan_path: Path | str, plan: dict[str, Any]) -> dict[str, Any]:
    """Persist one already validated plan without reopening or remapping the XLSX."""
    source = Path(plan_path).resolve()
    if not isinstance(plan, dict) or plan.get("schema_version") != "3.0.0":
        raise RunError("start_run requires one validated canonical plan.")
    if plan.get("scope") != "GA4_ONLY" or not isinstance(plan.get("events"), list):
        raise RunError("start_run received an invalid canonical plan contract.")
    plan_source = plan.get("source") if isinstance(plan.get("source"), dict) else {}
    if Path(str(plan_source.get("path") or "")).resolve() != source:
        raise RunError("Canonical plan source path does not match plan_path.")
    try:
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError as error:
        raise RunError(f"Cannot verify tracking-plan source: {error}") from error
    if plan_source.get("sha256") != source_digest:
        raise RunError("Canonical plan source hash no longer matches the XLSX.")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    root = _workspace_root() / f"{source.stem}-gtm-client-recette-{stamp}"
    root.mkdir(exist_ok=False)
    run = _paths(root)
    persisted_plan = json.loads(json.dumps(plan))
    persisted_plan["run_id"] = root.name
    try:
        _write_json(run["plan"], persisted_plan)
        run["stream"].touch(exist_ok=False)
        _append(root, "RUN_STARTED", {"run_id": persisted_plan["run_id"]})
    except Exception:
        if not any(root.iterdir()):
            root.rmdir()
        raise
    return {"run_directory": str(root), "plan": persisted_plan}


def load_plan(root: Path | str) -> dict[str, Any]:
    try:
        plan = json.loads(_paths(root)["plan"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunError(f"Run plan is missing or corrupted: {error}") from error
    if not isinstance(plan, dict) or plan.get("schema_version") != "3.0.0":
        raise RunError("Run plan schema is missing or unsupported.")
    return plan


def read_records(root: Path | str) -> list[dict[str, Any]]:
    try:
        lines = _paths(root)["stream"].read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise RunError(f"Run event log is unavailable: {error}") from error
    records = []
    for number, line in enumerate(lines, 1):
        if not line:
            raise RunError(f"Run event log contains a blank record at line {number}.")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RunError(f"Run event log is corrupted at line {number}: {error}") from error
        if not isinstance(record, dict) or record.get("sequence") != number:
            raise RunError(f"Run event log sequence is invalid at line {number}.")
        records.append(record)
    if not records or records[0].get("kind") != "RUN_STARTED":
        raise RunError("Run event log has no RUN_STARTED record.")
    return records


def _committed(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record["data"]["result"] for record in records if record.get("kind") == "EVENT_COMMITTED"
    ]


def _open_action(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    committed = {result["event_id"] for result in _committed(records)}
    for record in reversed(records):
        if record.get("kind") == "ACTION_STARTED" and record["data"]["event_id"] not in committed:
            return record["data"]
    return None


def _terminal(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    for record in reversed(records):
        if record.get("kind") == "RUN_ABORTED":
            return record
    return None


def _temporary_images(root: Path | str, event_id: str) -> tuple[Path, Path]:
    run_root = _paths(root)["root"]
    return (
        run_root / f".image-{event_id}-before.tmp.png",
        run_root / f".image-{event_id}-after.tmp.png",
    )


def start_event(root: Path | str, preview_cursor: int) -> dict[str, Any]:
    """Freeze the next event and preceding Preview cursor exactly once."""
    if not isinstance(preview_cursor, int) or preview_cursor < 0:
        raise RunError("Preview cursor must be a non-negative integer.")
    plan = load_plan(root)
    records = read_records(root)
    if _terminal(records):
        raise RunError("A terminal run cannot start another event.")
    if _open_action(records):
        raise RunError("An event action is already open.")
    results = _committed(records)
    if results and preview_cursor != results[-1]["preview_cursor"]:
        raise RunError("Preview cursor must equal the preceding committed cursor.")
    done = {result["event_id"] for result in results}
    event = next((item for item in plan["events"] if item["event_id"] not in done), None)
    if event is None:
        raise RunError("Every tracking-plan event is already committed.")
    action = {
        "action_id": f"A-{len(results) + 1:04d}",
        "event_id": event["event_id"],
        "event_name": event["event_name"],
        "scenario_id": event["event_name"],
        "entry_url": event.get("entry_url"),
        "mapping_notices": event.get("mapping_notices", []),
        "selector": event["selector"],
        "fields": event["fields"],
        "preview_cursor": preview_cursor,
    }
    before_image, after_image = _temporary_images(root, event["event_id"])
    action["before_image_temporary"] = str(before_image)
    action["after_image_temporary"] = str(after_image)
    _append(root, "ACTION_STARTED", action)
    return action


def commit_event(
    root: Path | str,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Judge and atomically commit both images and evidence, then advance once."""
    from judge import event_by_id, judge_event

    plan = load_plan(root)
    records = read_records(root)
    if _terminal(records):
        raise RunError("A terminal run cannot commit another event.")
    action = _open_action(records)
    if action is None:
        raise RunError("No event action is open.")
    event = event_by_id(plan, action["event_id"])
    result = judge_event(event, action, bundle)
    run = _paths(root)
    before_source, after_source = _temporary_images(root, event["event_id"])
    if action.get("before_image_temporary") != str(before_source) or action.get(
        "after_image_temporary"
    ) != str(after_source):
        raise RunError("Open action temporary screenshot paths are invalid.")
    if not before_source.is_file() or not after_source.is_file():
        raise RunError("Both temporary screenshots are required before commit.")
    before_final = run["root"] / f"image-{event['event_id']}-before.png"
    after_final = run["root"] / f"image-{event['event_id']}-after.png"
    evidence_final = run["root"] / f"evidence-{event['event_id']}.json"
    if any(path.exists() for path in (before_final, after_final, evidence_final)):
        raise RunError("Event artifact target already exists.")
    result["evidence_file"] = evidence_final.name
    result["image_before"] = before_final.name
    result["image_after"] = after_final.name
    evidence = {
        "bundle": bundle,
        "result": result,
        "artifacts": {
            "image_before_sha256": hashlib.sha256(before_source.read_bytes()).hexdigest(),
            "image_after_sha256": hashlib.sha256(after_source.read_bytes()).hexdigest(),
        },
    }
    evidence_temp = evidence_final.with_name(evidence_final.name + ".tmp")
    with evidence_temp.open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    json.loads(evidence_temp.read_text(encoding="utf-8"))
    try:
        os.replace(before_source, before_final)
        os.replace(after_source, after_final)
        os.replace(evidence_temp, evidence_final)
        _append(root, "EVENT_COMMITTED", {"result": result})
    except Exception:
        for path in (
            before_source,
            after_source,
            before_final,
            after_final,
            evidence_temp,
            evidence_final,
        ):
            path.unlink(missing_ok=True)
        raise
    return result


def abandon_run(
    root: Path | str, fatal_stage: str, error_code: str, message: str
) -> dict[str, Any]:
    """Record one fatal terminal and remove only fixed uncommitted event artifacts."""
    records = read_records(root)
    if _terminal(records):
        raise RunError("Run already has a terminal record.")
    action = _open_action(records)
    if action:
        before, after = _temporary_images(root, action["event_id"])
        evidence_temp = _paths(root)["root"] / f"evidence-{action['event_id']}.json.tmp"
        for path in (before, after, evidence_temp):
            path.unlink(missing_ok=True)
    if not all(
        isinstance(value, str) and value.strip() for value in (fatal_stage, error_code, message)
    ):
        raise RunError("Fatal stage, error code, and message must be non-empty strings.")
    terminal = {
        "status": "FATAL",
        "cleanup_status": "COMPLETE",
        "fatal_stage": fatal_stage.strip(),
        "error_code": error_code.strip(),
        "message": message.strip(),
        "committed_event_ids": [result["event_id"] for result in _committed(records)],
    }
    _append(root, "RUN_ABORTED", terminal)
    return terminal


def finish_run(root: Path | str) -> dict[str, Any]:
    """Render the final workbook only after every event commit marker exists."""
    from report import render_report

    plan = load_plan(root)
    records = read_records(root)
    if _terminal(records):
        raise RunError("Run already has a terminal record.")
    if _open_action(records):
        raise RunError("The open event must be committed before finalization.")
    results = _committed(records)
    if len(results) != len(plan["events"]):
        raise RunError("Every tracking-plan event must be committed before finalization.")
    output = _paths(root)["workbook"]
    render_report(plan, results, output)
    terminal = {
        "status": "COMPLETE",
        "workbook_path": str(output),
        "workbook_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "cleanup_status": "NOT_REQUIRED",
        "fatal_stage": None,
        "error_code": None,
        "message": "Every tracking-plan event was committed.",
        "committed_event_ids": [result["event_id"] for result in results],
    }
    return terminal
