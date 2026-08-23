#!/usr/bin/env python3
"""Zero-based expert client-side GTM recette operator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.plan import initialize_run
from core.report import build_reports, render_event_feedback, status_view
from core.state import StateError
from core.workflow import (
    add_handoff,
    begin_action,
    commit_action,
    finish_run,
    load_json_object,
    reopen_run,
    sync_preview,
)


def _json_object(path: Path | None) -> dict[str, Any]:
    return {} if path is None else load_json_object(path)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Compile scope and typed proof obligations.")
    init.add_argument("--plan", type=Path, required=True)
    init.add_argument("--run-dir", type=Path, required=True)
    init.add_argument("--run-id")
    init.add_argument("--scope-json", type=Path)
    init.add_argument("--approved", action="store_true", help="User accepted the test boundary.")
    init.add_argument("--origin", action="append", default=[])
    init.add_argument("--environment")
    init.add_argument("--expected-container", action="append", default=[])
    init.add_argument("--destination", action="append", default=[])
    init.add_argument("--tag-scope", action="append", default=[])
    init.add_argument("--source-only", action="store_true")
    init.add_argument("--no-browser-send", action="store_true")

    begin = commands.add_parser("begin", help="Bind and begin one real browser action.")
    begin.add_argument("--run-dir", type=Path, required=True)
    begin.add_argument("--event", action="append", required=True)
    begin.add_argument("--input", type=Path, required=True, help="Before-state/handshake bundle.")
    begin.add_argument("--scenario", default="ordinary")
    begin.add_argument("--scenario-label")
    begin.add_argument("--scenario-values-json", type=Path)
    begin.add_argument("--label")
    begin.add_argument(
        "--replay-safety",
        choices=["SAFE_IDEMPOTENT", "SAFE_ONCE", "CONSEQUENTIAL", "PROTECTED"],
        default="SAFE_IDEMPOTENT",
    )
    begin.add_argument("--fresh-context-required", action="store_true")

    commit = commands.add_parser(
        "commit", help="Commit after-state and continuous collector deltas; emit a pulse."
    )
    commit.add_argument("--run-dir", type=Path, required=True)
    commit.add_argument("--input", type=Path, required=True)
    commit.add_argument("--action")
    commit.add_argument("--outcome-may-have-occurred", action="store_true")

    sync = commands.add_parser(
        "sync-preview", help="Ingest one Preview micro-batch and emit canonical feedback."
    )
    sync.add_argument("--run-dir", type=Path, required=True)
    sync.add_argument("--input", type=Path, required=True)
    sync.add_argument("--event", action="append")
    sync.add_argument("--markdown", action="store_true")

    status = commands.add_parser("status", help="Replay current status without writing.")
    status.add_argument("--run-dir", type=Path, required=True)

    handoff = commands.add_parser("handoff", help="Record or resume a protected same-session gate.")
    handoff.add_argument("--run-dir", type=Path, required=True)
    handoff.add_argument("--input", type=Path, required=True)

    finish = commands.add_parser("finish", help="Reconcile, freeze, and render final outputs once.")
    finish.add_argument("--run-dir", type=Path, required=True)

    report = commands.add_parser("report", help="Rebuild reports from canonical frozen evidence.")
    report.add_argument("--run-dir", type=Path, required=True)

    reopen = commands.add_parser("reopen", help="Authorize an explicit post-finish revision.")
    reopen.add_argument("--run-dir", type=Path, required=True)
    reopen.add_argument("--authorization", required=True)
    return root


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            scope = _json_object(args.scope_json)
            scope["approved"] = scope.get("approved") is True or args.approved
            if args.origin:
                scope["origins"] = args.origin
            if args.environment:
                scope["environment"] = args.environment
            if args.expected_container:
                scope["expected_container"] = args.expected_container
            if args.destination:
                scope["destination"] = args.destination
            if args.tag_scope:
                scope["tag_scope"] = args.tag_scope
            scope["certify_tags"] = not args.source_only
            scope["browser_send_required"] = not args.no_browser_send and not args.source_only
            plan = initialize_run(args.plan, args.run_dir, run_id=args.run_id, scope=scope)
            first = next((event for event in plan["events"] if event.get("executable")), None)
            _print(
                {
                    "run_id": plan["run_id"],
                    "events": plan["event_count"],
                    "requirements": plan["requirement_count"],
                    "claims": plan["claim_count"],
                    "first_executable_event": first.get("event_id") if first else None,
                    "normalization": plan["source"].get("normalization"),
                    "event_compile_errors": {
                        event["event_id"]: event["compile_errors"]
                        for event in plan["events"]
                        if event.get("compile_errors")
                    },
                    "future_scenario_artifacts": 0,
                }
            )
        elif args.command == "begin":
            _print(
                begin_action(
                    args.run_dir,
                    args.event,
                    load_json_object(args.input),
                    scenario_id=args.scenario,
                    scenario_label=args.scenario_label,
                    scenario_values=_json_object(args.scenario_values_json),
                    label=args.label,
                    replay_safety=args.replay_safety,
                    fresh_context_required=args.fresh_context_required,
                )
            )
        elif args.command == "commit":
            _print(
                commit_action(
                    args.run_dir,
                    load_json_object(args.input),
                    action_id=args.action,
                    outcome_may_have_occurred=(True if args.outcome_may_have_occurred else None),
                )
            )
        elif args.command == "sync-preview":
            result = sync_preview(args.run_dir, load_json_object(args.input), event_ids=args.event)
            if args.markdown:
                for event in result["events"]:
                    print(render_event_feedback(event), end="")
            else:
                _print(result)
        elif args.command == "status":
            _print(status_view(args.run_dir))
        elif args.command == "handoff":
            _print(add_handoff(args.run_dir, load_json_object(args.input)))
        elif args.command == "finish":
            result = finish_run(args.run_dir)
            _print({"status": result["status"], "outputs": build_reports(args.run_dir)})
        elif args.command == "report":
            _print(build_reports(args.run_dir))
        elif args.command == "reopen":
            _print(reopen_run(args.run_dir, args.authorization))
        else:  # pragma: no cover
            raise StateError(f"Unknown command: {args.command}")
    except StateError as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
