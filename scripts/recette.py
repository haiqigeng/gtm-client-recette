#!/usr/bin/env python3
"""Zero-based expert client-side GTM recette operator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.plan import initialize_run
from core.report import build_reports, compact_status_view, render_event_feedback, status_view
from core.state import StateError
from core.workflow import (
    add_handoff,
    complete_action,
    finish_run,
    load_json_object,
    next_action,
    reopen_run,
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
    init.add_argument(
        "--browser-runtime",
        choices=["playwright_mcp", "existing_chromium"],
    )
    init.add_argument("--browser-channel")

    next_command = commands.add_parser(
        "next", help="Open one frozen Playwright action card for the next event/scenario."
    )
    next_command.add_argument("--run-dir", type=Path, required=True)
    next_command.add_argument("--event", action="append")
    next_command.add_argument("--input", type=Path, help="First runtime self-check bundle.")
    next_command.add_argument("--scenario", default="ordinary")
    next_command.add_argument("--scenario-label")
    next_command.add_argument("--scenario-values-json", type=Path)
    next_command.add_argument("--label")
    next_command.add_argument(
        "--replay-safety",
        choices=["SAFE_IDEMPOTENT", "SAFE_ONCE", "CONSEQUENTIAL", "PROTECTED"],
        default="SAFE_IDEMPOTENT",
    )
    next_command.add_argument("--fresh-context-required", action="store_true")
    next_command.add_argument("--retest-basis-json", type=Path)
    next_command.add_argument(
        "--mode", choices=["OBSERVE_CURRENT", "NAVIGATE_ONCE", "INTERACT_ONCE"]
    )
    next_command.add_argument(
        "--document-policy",
        choices=["FORBIDDEN", "NATURAL_ALLOWED", "ONE_RELOAD_AUTHORIZED"],
    )

    complete = commands.add_parser(
        "complete", help="Commit action deltas and Preview evidence in one bounded pass."
    )
    complete.add_argument("--run-dir", type=Path, required=True)
    complete.add_argument("--input", type=Path, required=True)
    complete.add_argument(
        "--action", required=True, help="Exact action_id returned by next; also enables safe retry."
    )
    complete.add_argument("--outcome-may-have-occurred", action="store_true")
    complete.add_argument("--markdown", action="store_true")
    complete.add_argument("--full", action="store_true")

    status = commands.add_parser("status", help="Replay current status without writing.")
    status.add_argument("--run-dir", type=Path, required=True)
    status.add_argument("--full", action="store_true")

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
            if args.browser_runtime:
                scope["browser_runtime"] = args.browser_runtime
            if args.browser_channel:
                scope["browser_channel"] = args.browser_channel
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
        elif args.command == "next":
            _print(
                next_action(
                    args.run_dir,
                    _json_object(args.input),
                    event_ids=args.event,
                    scenario_id=args.scenario,
                    scenario_label=args.scenario_label,
                    scenario_values=_json_object(args.scenario_values_json),
                    label=args.label,
                    replay_safety=args.replay_safety,
                    fresh_context_required=args.fresh_context_required,
                    retest_basis=_json_object(args.retest_basis_json) or None,
                    mode=args.mode,
                    document_policy=args.document_policy,
                )
            )
        elif args.command == "complete":
            result = complete_action(
                args.run_dir,
                load_json_object(args.input),
                action_id=args.action,
                outcome_may_have_occurred=(True if args.outcome_may_have_occurred else None),
            )
            if args.markdown:
                for event in [*result["events"], *result.get("revised_events", [])]:
                    print(render_event_feedback(event), end="")
            elif args.full:
                _print(result)
            else:
                _print(
                    {
                        "action_id": result["action_id"],
                        "commit_record_id": result["commit_record_id"],
                        "sync_record_id": result["sync_record_id"],
                        "events": [compact_status_view(event) for event in result["events"]],
                        "revised_events": [
                            compact_status_view(event) for event in result.get("revised_events", [])
                        ],
                    }
                )
        elif args.command == "status":
            _print(
                status_view(args.run_dir)
                if args.full
                else compact_status_view(status_view(args.run_dir))
            )
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
