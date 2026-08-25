#!/usr/bin/env python3
"""Fixed four-command runtime for personal GTM client recette."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from state import RunError, complete_action, finish_run, start_action, start_run
from xlsx_plan import PlanError


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def _layer_detail(layer: dict[str, Any]) -> tuple[str, str]:
    problems = [
        check
        for check in layer["checks"]
        if check["status"] in {"FAIL", "BLOCKED", "REVIEW", "PENDING"}
    ]
    if not problems:
        return f"{layer['passed']}/{layer['total']} checks passed.", ""
    paths = list(dict.fromkeys(str(check["path"]) for check in problems if check.get("path")))
    reasons = list(dict.fromkeys(str(check["reason"]) for check in problems))
    details = "; ".join(reasons)
    if paths:
        details += " Affected: " + ", ".join(paths)
    comparisons = list(
        dict.fromkeys(
            f"{check.get('path') or check['check']}: {check.get('expected')} -> {check.get('observed')}"
            for check in problems
            if check.get("expected") is not None or check.get("observed") is not None
        )
    )
    if comparisons:
        details += " Expected -> observed: " + "; ".join(comparisons)
    targets = list(
        dict.fromkeys(str(check["check_next"]) for check in problems if check.get("check_next"))
    )
    return details, "; ".join(targets)


def feedback_markdown(result: dict[str, Any], stopped: bool) -> str:
    lines = [
        f"### {result['label']} — {result['scenario']['id']} — {result['status']}",
        "",
        "| Layer | Status | Details | Check next |",
        "|---|---|---|---|",
    ]
    for layer in result["layers"]:
        details, target = _layer_detail(layer)
        lines.append(
            f"| {_cell(layer['layer'])} | {_cell(layer['status'])} | "
            f"{_cell(details)} | {_cell(target)} |"
        )
    coverage = result["coverage"]
    lines.extend(
        [
            "",
            f"Coverage: {'FINAL' if coverage['complete'] else 'PENDING'} — {coverage['rationale']}",
        ]
    )
    if stopped:
        lines.append(
            "Run stopped after this feedback: two consecutive events had all five layers "
            "BLOCKED with no attributable evidence."
        )
    return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("tracking_plan", type=Path)
    start.add_argument("run_directory", type=Path)
    next_command = commands.add_parser("next")
    next_command.add_argument("run_directory", type=Path)
    next_command.add_argument("preview_cursor", type=int)
    complete = commands.add_parser("complete")
    complete.add_argument("run_directory", type=Path)
    complete.add_argument("evidence_bundle", type=Path)
    finish = commands.add_parser("finish")
    finish.add_argument("run_directory", type=Path)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "start":
            plan = start_run(args.tracking_plan, args.run_directory)
            _json(
                {
                    "run_id": plan["run_id"],
                    "event_count": plan["event_count"],
                    "field_count": plan["field_count"],
                    "next": "Prepare Preview, bootstrap the observer once, then run next with its current-document cursor for Core or current cursor otherwise.",
                }
            )
        elif args.command == "next":
            _json(start_action(args.run_directory, args.preview_cursor))
        elif args.command == "complete":
            completed = complete_action(args.run_directory, args.evidence_bundle)
            result = completed["result"]
            print(feedback_markdown(result, completed["stopped"]))
            print()
            _json(
                {
                    "action_id": result["action_id"],
                    "event_id": result["event_id"],
                    "preview_cursor": result["preview_cursor"],
                    "status": result["status"],
                    "stopped": completed["stopped"],
                }
            )
        else:
            output = finish_run(args.run_directory)
            _json({"finished": True, "workbook": str(output)})
    except (OSError, PlanError, RunError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
