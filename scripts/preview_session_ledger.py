#!/usr/bin/env python3
"""Maintain resumable browser surfaces, interaction cases, and action evidence."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from execution_contract import (
    AUTHORIZATION_SCOPES,
    CASE_EXECUTION_STATUSES,
    DISCOVERY_SOURCES,
    LAYER_RESULT_STATUSES,
    PROTECTED_AUTHORIZATION_EXCLUSIONS,
    PUSH_CLASSIFICATIONS,
    SESSION_SCHEMA_VERSION,
    validate_session,
)
from layer_contract import CANONICAL_LAYERS, applicable_layers

ROLES = {
    "gtm_workspace",
    "tag_assistant",
    "website",
    "vendor_helper",
    "vendor_ui",
}
REQUIRED_ROLES = {"gtm_workspace", "tag_assistant", "website"}


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Ledger does not exist: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("Ledger must be a JSON object.")
    return value


def load_results(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit("Normalized results must be a JSON object.")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise SystemExit(f"URL must be absolute: {url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_variant(values: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for value in values:
        key, separator, raw = value.partition("=")
        key = key.strip()
        if not separator or not key:
            raise SystemExit("--variant must use KEY=JSON_VALUE or KEY=text.")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw
        if key in output:
            raise SystemExit(f"Duplicate material variant key: {key}")
        output[key] = parsed
    return output


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

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
    register.add_argument(
        "--surface-id",
        help="Unique key when more than one workspace, Preview session, or website is open.",
    )
    register.add_argument("--container-id")

    authorize = subparsers.add_parser("authorize")
    authorize.add_argument("ledger", type=Path)
    authorize.add_argument("--authorization-id", required=True)
    authorize.add_argument(
        "--scope",
        choices=tuple(sorted(AUTHORIZATION_SCOPES)),
        required=True,
    )
    authorize.add_argument("--description", required=True)
    authorize.add_argument(
        "--environment-class",
        choices=("test", "preprod", "staging", "production"),
        required=True,
    )
    authorize.add_argument("--exact-method")

    register_case = subparsers.add_parser("register-case")
    register_case.add_argument("ledger", type=Path)
    register_case.add_argument("--results", type=Path, required=True)
    register_case.add_argument("--case-id", required=True)
    register_case.add_argument("--event-group-id", required=True)
    register_case.add_argument("--url", required=True)
    register_case.add_argument("--element", required=True)
    register_case.add_argument("--placement", required=True)
    register_case.add_argument("--action", required=True)
    register_case.add_argument("--variant", action="append", default=[])
    register_case.add_argument(
        "--discovered-from",
        choices=tuple(sorted(DISCOVERY_SOURCES)),
        required=True,
    )
    register_case.add_argument(
        "--scope-status",
        choices=("IN_SCOPE", "OUT_OF_SCOPE"),
        default="IN_SCOPE",
    )
    register_case.add_argument("--reason")
    register_case.add_argument("--authorization-id", action="append", default=[])
    register_case.add_argument(
        "--include-layer",
        action="append",
        default=[],
        choices=CANONICAL_LAYERS,
    )
    register_case.add_argument(
        "--exclude-layer",
        action="append",
        default=[],
        choices=CANONICAL_LAYERS,
    )

    close_case = subparsers.add_parser("close-case")
    close_case.add_argument("ledger", type=Path)
    close_case.add_argument("--case-id", required=True)
    close_case.add_argument(
        "--execution-status",
        choices=("BLOCKED", "NOT_TESTED"),
        required=True,
    )
    close_case.add_argument("--reason", required=True)
    close_case.add_argument("--blocker-id")

    begin = subparsers.add_parser("begin-action")
    begin.add_argument("ledger", type=Path)
    begin.add_argument("--action-id", required=True)
    begin.add_argument("--case-id", required=True)
    begin.add_argument("--last-event-before", type=int, required=True)
    begin.add_argument("--consent-state", required=True)
    begin.add_argument("--browser-context-id")
    begin.add_argument("--container-id", action="append", default=[])
    begin.add_argument("--quiet-window-ms", type=int, default=2000)
    begin.add_argument("--timeout-ms", type=int, default=15000)
    begin.add_argument(
        "--retry-of-action-id",
        help="Settled immediately prior attempt retained as the reason for this retry.",
    )

    push = subparsers.add_parser("record-push")
    push.add_argument("ledger", type=Path)
    push.add_argument("--push-id", required=True)
    push.add_argument("--action-id", required=True)
    push.add_argument("--event-index", type=int, required=True)
    push.add_argument("--event-name", required=True)
    push.add_argument(
        "--classification",
        choices=tuple(sorted(PUSH_CLASSIFICATIONS)),
        required=True,
    )
    push.add_argument("--classification-reason", required=True)
    push.add_argument("--event-group-id")
    push.add_argument("--url")
    push.add_argument("--page-state", required=True)
    push.add_argument("--evidence-id", required=True)
    push.add_argument("--container-id", required=True)
    push.add_argument("--stream-id", default="tag_assistant")
    push.add_argument("--captured-at")
    push.add_argument(
        "--connection-epoch",
        type=int,
        help=(
            "Preview connection segment. Defaults to 1 plus the number of prior "
            "preview_disconnected actions."
        ),
    )

    import_pushes = subparsers.add_parser("import-pushes")
    import_pushes.add_argument("ledger", type=Path)
    import_pushes.add_argument(
        "push_file",
        type=Path,
        help="JSON array, or an object with a pushes array, captured for open actions.",
    )

    import_cases = subparsers.add_parser("import-cases")
    import_cases.add_argument("ledger", type=Path)
    import_cases.add_argument("manifest", type=Path)
    import_cases.add_argument("--results", type=Path, required=True)

    layer = subparsers.add_parser("record-layer")
    layer.add_argument("ledger", type=Path)
    layer.add_argument("--action-id", required=True)
    layer.add_argument("--layer", choices=CANONICAL_LAYERS, required=True)
    layer.add_argument(
        "--status",
        choices=tuple(sorted(LAYER_RESULT_STATUSES)),
        required=True,
    )
    layer.add_argument("--reason", required=True)
    layer.add_argument("--evidence-id", action="append", required=True)
    layer.add_argument("--semantic-ambiguity")
    layer.add_argument("--blocker-id")

    settle = subparsers.add_parser("settle-action")
    settle.add_argument("ledger", type=Path)
    settle.add_argument("--action-id", required=True)
    settle.add_argument("--first-event-after", type=int)
    settle.add_argument("--settled-final-event", type=int, required=True)
    settle.add_argument("--expected-seen", choices=("true", "false"), required=True)
    settle.add_argument("--preview-connected-after", choices=("true", "false"), required=True)
    settle.add_argument(
        "--interaction-outcome",
        choices=("completed", "failed", "uncertain"),
        required=True,
        help="Whether the website interaction completed independently of tracking.",
    )
    settle.add_argument(
        "--completion-signal",
        required=True,
        help="Safe non-tracking proof of the completion, failure, or uncertainty.",
    )
    settle.add_argument("--stream-settled", choices=("true", "false"), required=True)
    settle.add_argument(
        "--settlement-reason",
        choices=(
            "expected_and_quiet",
            "quiet_without_expected",
            "timeout",
            "interaction_failed",
            "preview_disconnected",
        ),
        required=True,
    )
    settle.add_argument(
        "--observed-business-push-count",
        type=int,
        required=True,
        help="Total business pushes visible in the complete action window.",
    )

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint.add_argument("ledger", type=Path)
    checkpoint.add_argument("--label", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("ledger", type=Path)
    validate.add_argument("--results", type=Path)
    validate.add_argument("--final", action="store_true")

    status = subparsers.add_parser("status")
    status.add_argument("ledger", type=Path)
    return root


def parse_args() -> argparse.Namespace:
    return parser().parse_args()


def require_surfaces(ledger: dict[str, Any]) -> None:
    surfaces = ledger.get("surfaces", {})
    roles = {str(surface.get("role")) for surface in surfaces.values() if isinstance(surface, dict)}
    missing = sorted(REQUIRED_ROLES - roles)
    if missing:
        raise SystemExit("Register all browser surfaces before an action: " + ", ".join(missing))
    assistants = [
        surface
        for surface in surfaces.values()
        if isinstance(surface, dict) and surface.get("role") == "tag_assistant"
    ]
    if not assistants or not all(surface.get("connected") is True for surface in assistants):
        raise SystemExit("Tag Assistant is not recorded as connected.")


def find_unique(rows: list[dict[str, Any]], field: str, value: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get(field) == value]
    if len(matches) != 1:
        raise SystemExit(f"Unknown or duplicate {field}: {value}")
    return matches[0]


def register_case(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    if any(row.get("case_id") == args.case_id for row in ledger.get("cases", [])):
        raise SystemExit(f"Duplicate case_id: {args.case_id}")
    if origin(args.url) not in ledger.get("approved_origins", []):
        raise SystemExit(f"Case origin is not approved: {origin(args.url)}")
    results = load_results(args.results)
    group_requirements = [
        row
        for row in results.get("requirements", [])
        if isinstance(row, dict) and row.get("event_group_id") == args.event_group_id
    ]
    if not group_requirements:
        raise SystemExit(f"Unknown event_group_id: {args.event_group_id}")
    if args.scope_status == "OUT_OF_SCOPE" and not str(args.reason or "").strip():
        raise SystemExit("OUT_OF_SCOPE cases require --reason.")
    unknown_authorizations = sorted(
        value
        for value in args.authorization_id
        if not any(row.get("authorization_id") == value for row in ledger.get("authorizations", []))
    )
    if unknown_authorizations:
        raise SystemExit("Unknown authorization IDs: " + ", ".join(unknown_authorizations))
    containers = [
        row for row in results.get("run", {}).get("containers", []) if isinstance(row, dict)
    ]
    layers = applicable_layers(
        group_requirements,
        container_count=len(containers) or 1,
    )
    layers = [
        layer
        for layer in CANONICAL_LAYERS
        if (layer in layers or layer in args.include_layer) and layer not in args.exclude_layer
    ]
    container_ids = sorted(
        {
            str(
                requirement.get("container_id") or results.get("run", {}).get("container_id", "")
            ).strip()
            for requirement in group_requirements
            if str(
                requirement.get("container_id") or results.get("run", {}).get("container_id", "")
            ).strip()
        }
    )
    ledger.setdefault("cases", []).append(
        {
            "case_id": args.case_id,
            "event_group_id": args.event_group_id,
            "requirement_ids": [str(row.get("requirement_id")) for row in group_requirements],
            "url": args.url,
            "element": args.element,
            "placement": args.placement,
            "action": args.action,
            "material_variant": parse_variant(args.variant),
            "discovered_from": args.discovered_from,
            "scope_status": args.scope_status,
            "execution_status": (
                "NOT_TESTED" if args.scope_status == "OUT_OF_SCOPE" else "PENDING"
            ),
            "reason": str(args.reason or "").strip() or None,
            "authorization_ids": list(dict.fromkeys(args.authorization_id)),
            "applicable_layers": layers,
            "container_ids": container_ids,
            "registered_at": now(),
            "final_action_id": None,
        }
    )


def begin_action(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    require_surfaces(ledger)
    if any(row.get("action_id") == args.action_id for row in ledger.get("actions", [])):
        raise SystemExit(f"Duplicate action_id: {args.action_id}")
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if case.get("scope_status") != "IN_SCOPE" or case.get("execution_status") == "BLOCKED":
        raise SystemExit("Actions can start only for an applicable, unblocked case.")
    if args.quiet_window_ms <= 0 or args.timeout_ms <= 0:
        raise SystemExit("Quiet window and timeout must be positive.")
    previous = sorted(
        [row for row in ledger.get("actions", []) if row.get("case_id") == args.case_id],
        key=lambda row: row.get("attempt_number", 0),
    )
    if previous:
        expected_retry = previous[-1]
        if expected_retry.get(
            "state"
        ) != "SETTLED" or args.retry_of_action_id != expected_retry.get("action_id"):
            raise SystemExit(
                "A repeated case must retry the retained immediately prior settled action."
            )
    elif args.retry_of_action_id:
        raise SystemExit("The first case attempt cannot use --retry-of-action-id.")
    container_ids = args.container_id or case.get("container_ids", [])
    if not container_ids:
        raise SystemExit("The action requires at least one client-side container ID.")
    action = {
        "action_id": args.action_id,
        "case_id": args.case_id,
        "event_group_id": case.get("event_group_id"),
        "requirement_ids": case.get("requirement_ids"),
        "url": case.get("url"),
        "element": case.get("element"),
        "placement": case.get("placement"),
        "material_variant": case.get("material_variant"),
        "action": case.get("action"),
        "attempt_number": len(previous) + 1,
        "connection_epoch": ledger.get("connection_epoch", 1),
        "retry_of_action_id": args.retry_of_action_id,
        "preview_connected_before": True,
        "target_ready_before": True,
        "last_event_before": args.last_event_before,
        "consent_state_before": args.consent_state,
        "browser_context_id": args.browser_context_id,
        "container_ids": list(dict.fromkeys(container_ids)),
        "action_timestamp": now(),
        "quiet_window_ms": args.quiet_window_ms,
        "timeout_ms": args.timeout_ms,
        "layer_results": [],
        "state": "OPEN",
    }
    ledger.setdefault("actions", []).append(action)


def record_push(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    if any(row.get("push_id") == args.push_id for row in ledger.get("business_pushes", [])):
        raise SystemExit(f"Duplicate push_id: {args.push_id}")
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if action.get("state") != "OPEN":
        raise SystemExit("Business pushes can be recorded only for an open action.")
    if args.classification not in PUSH_CLASSIFICATIONS:
        raise SystemExit(f"Invalid push classification: {args.classification}")
    if not isinstance(args.event_index, int) or isinstance(args.event_index, bool):
        raise SystemExit("Business push event_index must be an integer.")
    captured_at = getattr(args, "captured_at", None)
    if captured_at:
        try:
            parsed_capture = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise SystemExit("captured_at must be ISO 8601 with timezone.") from exc
        if parsed_capture.tzinfo is None:
            raise SystemExit("captured_at must be ISO 8601 with timezone.")
    if args.event_index <= action.get("last_event_before", -1):
        raise SystemExit("Business push event_index must follow last_event_before.")
    connection_epoch = args.connection_epoch
    if connection_epoch is None:
        connection_epoch = action.get("connection_epoch", ledger.get("connection_epoch", 1))
    if connection_epoch < 1:
        raise SystemExit("connection_epoch must be a positive integer.")
    if connection_epoch != action.get("connection_epoch", 1):
        raise SystemExit("connection_epoch must match the open action connection epoch.")
    if any(
        isinstance(row, dict)
        and row.get("stream_id", "tag_assistant") == args.stream_id
        and row.get("connection_epoch", 1) == connection_epoch
        and row.get("event_index") == args.event_index
        for row in ledger.get("business_pushes", [])
    ):
        raise SystemExit(
            "Duplicate stream/connection-epoch/event index; use the next "
            "--connection-epoch after a Preview reconnect."
        )
    group_id = args.event_group_id
    if group_id is None:
        group_id = action.get("event_group_id")
    ledger.setdefault("business_pushes", []).append(
        {
            "push_id": args.push_id,
            "stream_id": args.stream_id,
            "connection_epoch": connection_epoch,
            "action_id": args.action_id,
            "case_id": action.get("case_id"),
            "event_group_id": group_id,
            "event_name": args.event_name,
            "event_index": args.event_index,
            "captured_at": captured_at or now(),
            "url": args.url or action.get("url"),
            "page_state": args.page_state,
            "classification": args.classification,
            "classification_reason": args.classification_reason,
            "evidence_id": args.evidence_id,
            "container_id": args.container_id,
        }
    )


def import_pushes(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    value = json.loads(args.push_file.read_text(encoding="utf-8"))
    pushes = value.get("pushes") if isinstance(value, dict) else value
    if not isinstance(pushes, list) or any(not isinstance(row, dict) for row in pushes):
        raise SystemExit("Push import must be a JSON array or an object with a pushes array.")
    required = {
        "push_id",
        "action_id",
        "event_index",
        "event_name",
        "classification",
        "classification_reason",
        "page_state",
        "evidence_id",
        "container_id",
    }
    for index, row in enumerate(pushes, start=1):
        missing = sorted(key for key in required if row.get(key) in (None, ""))
        if missing:
            raise SystemExit(f"Push import row {index} is missing: " + ", ".join(missing))
        record_push(
            ledger,
            argparse.Namespace(
                push_id=row["push_id"],
                action_id=row["action_id"],
                event_index=row["event_index"],
                event_name=row["event_name"],
                classification=row["classification"],
                classification_reason=row["classification_reason"],
                event_group_id=row.get("event_group_id"),
                url=row.get("url"),
                page_state=row["page_state"],
                evidence_id=row["evidence_id"],
                container_id=row["container_id"],
                stream_id=row.get("stream_id", "tag_assistant"),
                connection_epoch=row.get("connection_epoch"),
                captured_at=row.get("captured_at"),
            ),
        )


def import_cases(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    value = json.loads(args.manifest.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("artifact_type") != ("gtm_recette_retest_manifest"):
        raise SystemExit("Case import requires a gtm_recette_retest_manifest object.")
    if value.get("verdicts_inherited") is not False or value.get("evidence_inherited") is not False:
        raise SystemExit(
            "Retest manifests must explicitly reject verdict and evidence inheritance."
        )
    limitations = value.get("limitations", [])
    if not isinstance(limitations, list):
        raise SystemExit("Retest manifest limitations must be an array.")
    if limitations:
        raise SystemExit(
            "Resolve every retest discovery limitation before importing cases: "
            + ", ".join(
                str(row.get("event_group_id", "unknown"))
                for row in limitations
                if isinstance(row, dict)
            )
        )
    cases = value.get("cases")
    if not isinstance(cases, list) or any(not isinstance(row, dict) for row in cases):
        raise SystemExit("Retest manifest cases must be an array of objects.")
    for index, row in enumerate(cases, start=1):
        required = (
            "case_id",
            "event_group_id",
            "url",
            "element",
            "placement",
            "action",
        )
        missing = [field for field in required if row.get(field) in (None, "")]
        if missing:
            raise SystemExit(f"Retest manifest case {index} is missing: " + ", ".join(missing))
        if row.get("execution_status") != "PENDING":
            raise SystemExit("Every imported retest case must start PENDING.")
        if row.get("authorization_ids") not in (None, []):
            raise SystemExit("Prior-run authorizations cannot be inherited by retest cases.")
        variant = row.get("material_variant", {})
        if not isinstance(variant, dict):
            raise SystemExit(f"Retest manifest case {index} material_variant must be an object.")
        register_case(
            ledger,
            argparse.Namespace(
                results=args.results,
                case_id=str(row["case_id"]),
                event_group_id=str(row["event_group_id"]),
                url=str(row["url"]),
                element=str(row["element"]),
                placement=str(row["placement"]),
                action=str(row["action"]),
                variant=[
                    f"{key}={json.dumps(item, ensure_ascii=False)}" for key, item in variant.items()
                ],
                discovered_from="prior_run",
                scope_status="IN_SCOPE",
                reason=None,
                authorization_id=[],
                include_layer=[],
                exclude_layer=[],
            ),
        )


def record_layer(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if args.layer not in find_unique(
        ledger.get("cases", []),
        "case_id",
        str(action.get("case_id")),
    ).get("applicable_layers", []):
        raise SystemExit(f"Layer is not applicable to this case: {args.layer}")
    if any(
        row.get("layer") == args.layer
        for row in action.get("layer_results", [])
        if isinstance(row, dict)
    ):
        raise SystemExit(f"Layer already recorded for action {args.action_id}: {args.layer}")
    if args.status == "REVIEW" and not str(args.semantic_ambiguity or "").strip():
        raise SystemExit("REVIEW requires --semantic-ambiguity.")
    if args.status == "BLOCKED" and not str(args.blocker_id or "").strip():
        raise SystemExit("BLOCKED layer evidence requires --blocker-id.")
    action.setdefault("layer_results", []).append(
        {
            "layer": args.layer,
            "status": args.status,
            "reason": args.reason,
            "evidence_ids": list(dict.fromkeys(args.evidence_id)),
            "semantic_ambiguity": (
                str(args.semantic_ambiguity).strip() if args.semantic_ambiguity else None
            ),
            "blocker_id": str(args.blocker_id).strip() if args.blocker_id else None,
            "recorded_at": now(),
        }
    )


def settle_action(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if action.get("state") != "OPEN":
        raise SystemExit(f"Action is already settled: {args.action_id}")
    completion_signal = str(args.completion_signal).strip()
    if not completion_signal:
        raise SystemExit("A safe independent --completion-signal is required.")
    preview_connected_after = args.preview_connected_after == "true"
    stream_settled = args.stream_settled == "true"
    if not stream_settled and args.settlement_reason in {
        "expected_and_quiet",
        "quiet_without_expected",
    }:
        raise SystemExit("An unsettled stream cannot use a quiet settlement reason.")
    if not preview_connected_after and args.settlement_reason != "preview_disconnected":
        raise SystemExit("A disconnected Preview session requires preview_disconnected.")
    recorded_pushes = sum(
        row.get("action_id") == args.action_id
        for row in ledger.get("business_pushes", [])
        if isinstance(row, dict)
    )
    if args.observed_business_push_count < 0:
        raise SystemExit("Observed business push count must be non-negative.")
    if recorded_pushes != args.observed_business_push_count:
        raise SystemExit(
            "Record and classify every observed business push before settlement; "
            f"ledger has {recorded_pushes}, action window has "
            f"{args.observed_business_push_count}."
        )
    if args.first_event_after is not None and args.first_event_after <= action.get(
        "last_event_before", -1
    ):
        raise SystemExit("first_event_after must follow last_event_before.")
    if args.settled_final_event < action.get("last_event_before", -1):
        raise SystemExit("settled_final_event cannot precede last_event_before.")
    action.update(
        {
            "first_event_after": args.first_event_after,
            "settled_final_event": args.settled_final_event,
            "expected_seen": args.expected_seen == "true",
            "preview_connected_after": preview_connected_after,
            "interaction_outcome": args.interaction_outcome,
            "completion_signal": completion_signal,
            "stream_settled": stream_settled,
            "settlement_reason": args.settlement_reason,
            "observed_business_push_count": args.observed_business_push_count,
            "settled_at": now(),
            "state": "SETTLED",
        }
    )
    if args.interaction_outcome == "completed" and preview_connected_after and stream_settled:
        case = find_unique(
            ledger.get("cases", []),
            "case_id",
            str(action.get("case_id")),
        )
        case["execution_status"] = "EXECUTED"
        case["final_action_id"] = args.action_id
    if args.settlement_reason == "preview_disconnected":
        ledger["connection_epoch"] = (
            action.get("connection_epoch", ledger.get("connection_epoch", 1)) + 1
        )


def init_command(args: argparse.Namespace) -> None:
    timestamp = now()
    save(
        args.ledger,
        {
            "schema_version": SESSION_SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "profile_path": args.profile_path,
            "connection_epoch": 1,
            "approved_origins": sorted({origin(item) for item in args.approved_origin}),
            "surfaces": {},
            "authorizations": [],
            "cases": [],
            "actions": [],
            "business_pushes": [],
            "checkpoints": [],
        },
    )


def register_surface(ledger: dict[str, Any], args: argparse.Namespace) -> None:
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
    if args.container_id:
        surface["container_id"] = args.container_id
    ledger.setdefault("surfaces", {})[args.surface_id or args.role] = surface


def authorize(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    if any(
        row.get("authorization_id") == args.authorization_id
        for row in ledger.get("authorizations", [])
    ):
        raise SystemExit(f"Duplicate authorization_id: {args.authorization_id}")
    if args.scope == "production_cmp_session_override" and args.environment_class != "production":
        raise SystemExit("Production CMP authorization requires production environment.")
    if args.scope == "production_cmp_session_override" and not str(args.exact_method or "").strip():
        raise SystemExit("Production CMP authorization requires --exact-method.")
    ledger.setdefault("authorizations", []).append(
        {
            "authorization_id": args.authorization_id,
            "scope": args.scope,
            "description": args.description,
            "environment_class": args.environment_class,
            "exact_method": str(args.exact_method or "").strip() or None,
            "session_only": True,
            "protected_exclusions": list(PROTECTED_AUTHORIZATION_EXCLUSIONS),
            "approved_at": now(),
        }
    )


def close_case(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    if args.execution_status not in CASE_EXECUTION_STATUSES:
        raise SystemExit("Invalid execution status.")
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if args.execution_status == "BLOCKED" and not str(args.blocker_id or "").strip():
        raise SystemExit("BLOCKED cases require --blocker-id.")
    if args.execution_status == "NOT_TESTED":
        case["scope_status"] = "OUT_OF_SCOPE"
    case.update(
        {
            "execution_status": args.execution_status,
            "reason": args.reason,
            "blocker_id": str(args.blocker_id or "").strip() or None,
            "closed_at": now(),
        }
    )


def checkpoint(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    ledger.setdefault("checkpoints", []).append(
        {
            "label": args.label,
            "captured_at": now(),
            "surface_roles": sorted(
                str(row.get("role"))
                for row in ledger.get("surfaces", {}).values()
                if isinstance(row, dict)
            ),
            "registered_cases": len(ledger.get("cases", [])),
            "settled_actions": sum(
                row.get("state") == "SETTLED" for row in ledger.get("actions", [])
            ),
            "classified_business_pushes": len(ledger.get("business_pushes", [])),
        }
    )


def validate_command(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    results = load_results(args.results) if args.results else None
    errors = validate_session(ledger, results=results, final=args.final)
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        json.dumps(
            {
                "validated": True,
                "final": args.final,
                "cases": len(ledger.get("cases", [])),
                "actions": len(ledger.get("actions", [])),
                "business_pushes": len(ledger.get("business_pushes", [])),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


MUTATING_COMMANDS = {
    "register-surface": register_surface,
    "authorize": authorize,
    "register-case": register_case,
    "close-case": close_case,
    "begin-action": begin_action,
    "record-push": record_push,
    "import-pushes": import_pushes,
    "import-cases": import_cases,
    "record-layer": record_layer,
    "settle-action": settle_action,
    "checkpoint": checkpoint,
}


def main() -> int:
    args = parse_args()
    if args.command == "init":
        init_command(args)
        print(f"Created {args.ledger.resolve()}")
        return 0

    ledger = load(args.ledger)
    if ledger.get("schema_version") != SESSION_SCHEMA_VERSION:
        raise SystemExit("Unsupported session ledger. Recreate it with the current init command.")
    if args.command == "validate":
        validate_command(ledger, args)
        return 0
    if args.command == "status":
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
        return 0

    MUTATING_COMMANDS[args.command](ledger, args)
    ledger["updated_at"] = now()
    save(args.ledger, ledger)
    print(f"Updated {args.ledger.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
