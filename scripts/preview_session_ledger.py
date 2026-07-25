#!/usr/bin/env python3
"""Maintain resumable GTM, Tag Assistant, website, and action-boundary state."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROLES = {"gtm_workspace", "tag_assistant", "website"}


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Ledger does not exist: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("Ledger must be a JSON object.")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"URL must be absolute: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("ledger", type=Path)
    init.add_argument("--profile-path", required=True)
    init.add_argument("--approved-origin", action="append", required=True)

    register = subparsers.add_parser("register-surface")
    register.add_argument("ledger", type=Path)
    register.add_argument("--role", choices=tuple(sorted(ROLES)), required=True)
    register.add_argument("--url", required=True)
    register.add_argument("--title", required=True)
    register.add_argument("--connected", choices=("true", "false"))

    begin = subparsers.add_parser("begin-action")
    begin.add_argument("ledger", type=Path)
    begin.add_argument("--action-id", required=True)
    begin.add_argument("--requirement-id", action="append", required=True)
    begin.add_argument("--url", required=True)
    begin.add_argument("--element", required=True)
    begin.add_argument("--action", required=True)
    begin.add_argument("--last-event-before", type=int, required=True)
    begin.add_argument("--consent-state", required=True)
    begin.add_argument("--quiet-window-ms", type=int, default=2000)
    begin.add_argument("--timeout-ms", type=int, default=15000)

    settle = subparsers.add_parser("settle-action")
    settle.add_argument("ledger", type=Path)
    settle.add_argument("--action-id", required=True)
    settle.add_argument("--first-event-after", type=int)
    settle.add_argument("--settled-final-event", type=int, required=True)
    settle.add_argument("--expected-seen", choices=("true", "false"), required=True)
    settle.add_argument("--preview-connected-after", choices=("true", "false"), required=True)

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("ledger", type=Path)
    checkpoint.add_argument("--label", required=True)

    status = subparsers.add_parser("status")
    status.add_argument("ledger", type=Path)
    return parser.parse_args()


def require_surfaces(ledger: dict[str, Any]) -> None:
    surfaces = ledger.get("surfaces", {})
    missing = sorted(ROLES - set(surfaces))
    if missing:
        raise SystemExit("Register all browser surfaces before an action: " + ", ".join(missing))
    if surfaces["tag_assistant"].get("connected") is not True:
        raise SystemExit("Tag Assistant is not recorded as connected.")


def main() -> int:
    args = parse_args()
    if args.command == "init":
        approved = sorted({origin(item) for item in args.approved_origin})
        ledger = {
            "schema_version": 1,
            "created_at": now(),
            "updated_at": now(),
            "profile_path": args.profile_path,
            "approved_origins": approved,
            "surfaces": {},
            "actions": [],
            "checkpoints": [],
        }
        save(args.ledger, ledger)
        print(f"Created {args.ledger.resolve()}")
        return 0

    ledger = load(args.ledger)
    if args.command == "register-surface":
        surface_origin = origin(args.url)
        if args.role == "website" and surface_origin not in ledger.get("approved_origins", []):
            raise SystemExit(f"Website origin is not approved: {surface_origin}")
        surface = {
            "role": args.role,
            "url": args.url,
            "origin": surface_origin,
            "title": args.title,
            "registered_at": now(),
        }
        if args.connected is not None:
            surface["connected"] = args.connected == "true"
        ledger.setdefault("surfaces", {})[args.role] = surface
    elif args.command == "begin-action":
        require_surfaces(ledger)
        if origin(args.url) not in ledger.get("approved_origins", []):
            raise SystemExit(f"Action origin is not approved: {origin(args.url)}")
        if any(row.get("action_id") == args.action_id for row in ledger.get("actions", [])):
            raise SystemExit(f"Duplicate action_id: {args.action_id}")
        if args.quiet_window_ms <= 0 or args.timeout_ms <= 0:
            raise SystemExit("Quiet window and timeout must be positive.")
        ledger.setdefault("actions", []).append(
            {
                "action_id": args.action_id,
                "requirement_ids": args.requirement_id,
                "url": args.url,
                "element": args.element,
                "action": args.action,
                "preview_connected_before": True,
                "target_ready_before": True,
                "last_event_before": args.last_event_before,
                "consent_state_before": args.consent_state,
                "action_timestamp": now(),
                "quiet_window_ms": args.quiet_window_ms,
                "timeout_ms": args.timeout_ms,
                "state": "OPEN",
            }
        )
    elif args.command == "settle-action":
        matches = [
            row for row in ledger.get("actions", []) if row.get("action_id") == args.action_id
        ]
        if len(matches) != 1:
            raise SystemExit(f"Unknown or duplicate action_id: {args.action_id}")
        action = matches[0]
        if action.get("state") != "OPEN":
            raise SystemExit(f"Action is already settled: {args.action_id}")
        action.update(
            {
                "first_event_after": args.first_event_after,
                "settled_final_event": args.settled_final_event,
                "expected_seen": args.expected_seen == "true",
                "preview_connected_after": args.preview_connected_after == "true",
                "stream_settled": True,
                "settled_at": now(),
                "state": "SETTLED",
            }
        )
    elif args.command == "checkpoint":
        ledger.setdefault("checkpoints", []).append(
            {
                "label": args.label,
                "captured_at": now(),
                "surface_roles": sorted(ledger.get("surfaces", {})),
                "settled_actions": sum(
                    row.get("state") == "SETTLED" for row in ledger.get("actions", [])
                ),
            }
        )
    elif args.command == "status":
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
        return 0

    ledger["updated_at"] = now()
    save(args.ledger, ledger)
    print(f"Updated {args.ledger.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
