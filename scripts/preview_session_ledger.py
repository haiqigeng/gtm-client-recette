#!/usr/bin/env python3
"""Maintain resumable browser surfaces, interaction cases, and action evidence."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from evidence_integrity import build_integrity_record
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
from gated_flow_contract import FLOW_KINDS
from layer_contract import (
    CANONICAL_LAYERS,
    CONDITIONAL_PREDICATES,
    TAG_CATEGORIES,
    TAG_DELIVERY_TYPES,
    TAG_RESULT_LAYERS,
    declared_tag_contracts,
    inferred_tag_category,
    layer_applicability,
    normalize_tag_scope,
    tag_scope_decision,
)
from runtime_state_contract import INTERRUPTION_REASONS, normalize_runtime_check
from scenario_coverage import SAMPLE_ROLES
from state_io import atomic_write_json, load_json_object, recover_file_pair

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
    try:
        return load_json_object(path)
    except ValueError as exc:
        raise SystemExit("Ledger must be a JSON object.") from exc


def load_results(path: Path) -> dict[str, Any]:
    try:
        return load_json_object(path)
    except ValueError as exc:
        raise SystemExit("Normalized results must be a JSON object.") from exc


def save(path: Path, value: dict[str, Any]) -> None:
    atomic_write_json(path, value)


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


def parse_condition_activations(values: list[str]) -> dict[str, str]:
    """Parse explicit conditional-layer activations with non-empty reasons."""
    output: dict[str, str] = {}
    for value in values:
        layer, separator, reason = value.partition("=")
        layer = layer.strip()
        reason = reason.strip()
        if not separator or layer not in CONDITIONAL_PREDICATES or not reason:
            raise SystemExit("--activate-condition must use CONDITIONAL_LAYER=concrete reason.")
        if layer in output:
            raise SystemExit(f"Duplicate conditional-layer activation: {layer}")
        output[layer] = reason
    return output


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("ledger", type=Path)
    init.add_argument("--profile-path", required=True)
    init.add_argument("--approved-origin", action="append", required=True)
    init.add_argument(
        "--operator-contract-version",
        choices=(1, 2),
        type=int,
        default=2,
        help="Current guided recette defaults to 2; select 1 only for old automation.",
    )
    init.add_argument(
        "--run-id",
        help="Exact normalized run.run_id; required for operator-contract-v2 sessions.",
    )
    init.add_argument("--browser-instance-id")
    init.add_argument("--browser-context-id")

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
    register.add_argument("--workspace")

    runtime_check = subparsers.add_parser("record-runtime-check")
    runtime_check.add_argument("ledger", type=Path)
    runtime_check.add_argument("snapshot", type=Path)
    runtime_check.add_argument("--results", type=Path, required=True)
    runtime_check.add_argument(
        "--phase",
        choices=("before_action", "resume", "after_action", "interrupted_action"),
        required=True,
    )
    runtime_check.add_argument("--action-id", required=True)
    runtime_check.add_argument("--case-id", required=True)

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
        "--dimension-value",
        action="append",
        default=[],
        metavar="DIMENSION_ID=JSON_VALUE",
        help="Bind this case to each material coverage dimension; repeat as needed.",
    )
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
    register_case.add_argument("--coverage-decision-id")
    register_case.add_argument("--scenario-class-id")
    register_case.add_argument("--sample-role", choices=tuple(sorted(SAMPLE_ROLES)))
    register_case.add_argument("--selection-rationale")
    register_case.add_argument("--population-member-id")
    register_case.add_argument("--acquisition-context", type=Path)
    register_case.add_argument(
        "--gated-flow-kind",
        choices=tuple(sorted(FLOW_KINDS)),
        default="NONE",
    )
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
    register_case.add_argument(
        "--activate-condition",
        action="append",
        default=[],
        metavar="LAYER=REASON",
        help="Pre-activate a conditional layer from detected site/runtime configuration.",
    )

    register_tag = subparsers.add_parser("register-tag")
    register_tag.add_argument("ledger", type=Path)
    register_tag.add_argument("--case-id", required=True)
    register_tag.add_argument("--tag-id", required=True)
    register_tag.add_argument("--tag-name", required=True)
    register_tag.add_argument("--container-id", required=True)
    register_tag.add_argument(
        "--tag-category", choices=tuple(sorted(TAG_CATEGORIES)), required=True
    )
    register_tag.add_argument(
        "--tag-delivery", choices=tuple(sorted(TAG_DELIVERY_TYPES)), required=True
    )
    register_tag.add_argument("--vendor-family")
    register_tag.add_argument("--destination-id")
    register_tag.add_argument("--template-type", required=True)
    register_tag.add_argument("--consent-required", choices=("true", "false"), required=True)
    register_tag.add_argument("--evidence-id", action="append", required=True)

    complete_inventory = subparsers.add_parser("complete-tag-inventory")
    complete_inventory.add_argument("ledger", type=Path)
    complete_inventory.add_argument("--case-id", required=True)
    complete_inventory.add_argument("--reason", required=True)
    complete_inventory.add_argument("--evidence-id", action="append", required=True)

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
    begin.add_argument("--readiness-check-id", required=True)
    begin.add_argument("--consent-state", required=True)
    begin.add_argument("--quiet-window-ms", type=int, default=2000)
    begin.add_argument("--timeout-ms", type=int, default=15000)
    begin.add_argument(
        "--retry-of-action-id",
        help="Settled immediately prior attempt retained as the reason for this retry.",
    )

    push = subparsers.add_parser("record-push")
    push.add_argument("ledger", type=Path)
    push.add_argument("--push-id", required=True)
    push.add_argument("--action-id")
    push.add_argument("--segment-id")
    push.add_argument("--event-index", type=int, required=True)
    push.add_argument("--preview-event-index", type=int)
    push.add_argument("--datalayer-call-index", type=int)
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

    void_check = subparsers.add_parser("void-runtime-check")
    void_check.add_argument("ledger", type=Path)
    void_check.add_argument("--check-id", required=True)
    void_check.add_argument("--reason", required=True)

    import_cases = subparsers.add_parser("import-cases")
    import_cases.add_argument("ledger", type=Path)
    import_cases.add_argument("manifest", type=Path)
    import_cases.add_argument("--results", type=Path, required=True)

    import_coverage = subparsers.add_parser("import-coverage")
    import_coverage.add_argument("ledger", type=Path)
    import_coverage.add_argument("coverage", type=Path)

    import_stream = subparsers.add_parser("import-stream")
    import_stream.add_argument("ledger", type=Path)
    import_stream.add_argument("stream", type=Path)

    import_semantic = subparsers.add_parser("import-semantic")
    import_semantic.add_argument("ledger", type=Path)
    import_semantic.add_argument("semantic", type=Path)

    import_handoffs = subparsers.add_parser("import-protected-handoffs")
    import_handoffs.add_argument("ledger", type=Path)
    import_handoffs.add_argument("handoffs", type=Path)

    import_flows = subparsers.add_parser("import-gated-flows")
    import_flows.add_argument("ledger", type=Path)
    import_flows.add_argument("flows", type=Path)

    verify_evidence = subparsers.add_parser("verify-evidence")
    verify_evidence.add_argument("ledger", type=Path)
    verify_evidence.add_argument("--results", type=Path, required=True)
    verify_evidence.add_argument("--base-dir", type=Path, required=True)

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
    layer.add_argument(
        "--predicate-result",
        choices=("true", "false"),
        help="Required for a conditional layer; false requires NOT_APPLICABLE.",
    )

    import_layers_parser = subparsers.add_parser("import-layers")
    import_layers_parser.add_argument("ledger", type=Path)
    import_layers_parser.add_argument("layer_results", type=Path)
    import_layers_parser.add_argument("--action-id", required=True)

    import_tag_results = subparsers.add_parser("import-tag-results")
    import_tag_results.add_argument("ledger", type=Path)
    import_tag_results.add_argument("tag_results", type=Path)
    import_tag_results.add_argument("--action-id", required=True)
    import_tag_results.add_argument(
        "--results",
        type=Path,
        help="Normalized results used to validate the staged import; required for v2.",
    )

    scaffold_tags = subparsers.add_parser("scaffold-tag-results")
    scaffold_tags.add_argument("ledger", type=Path)
    scaffold_tags.add_argument("--action-id", required=True)
    scaffold_tags.add_argument("--output", type=Path, required=True)

    revise_inventory = subparsers.add_parser("revise-tag-inventory")
    revise_inventory.add_argument("ledger", type=Path)
    revise_inventory.add_argument("--case-id", required=True)
    revise_inventory.add_argument("--tag-id", required=True)
    revise_inventory.add_argument("--tag-name", required=True)
    revise_inventory.add_argument("--container-id", required=True)
    revise_inventory.add_argument(
        "--tag-category", choices=tuple(sorted(TAG_CATEGORIES)), required=True
    )
    revise_inventory.add_argument(
        "--tag-delivery", choices=tuple(sorted(TAG_DELIVERY_TYPES)), required=True
    )
    revise_inventory.add_argument("--vendor-family")
    revise_inventory.add_argument("--destination-id")
    revise_inventory.add_argument("--template-type", required=True)
    revise_inventory.add_argument("--consent-required", choices=("true", "false"), required=True)
    revise_inventory.add_argument("--evidence-id", action="append", required=True)
    revise_inventory.add_argument("--reason", required=True)

    settle = subparsers.add_parser("settle-action")
    settle.add_argument("ledger", type=Path)
    settle.add_argument("--action-id", required=True)
    settle.add_argument("--settlement-check-id", required=True)
    settle.add_argument("--expected-seen", choices=("true", "false"), required=True)
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
    settle.add_argument(
        "--settlement-reason",
        choices=(
            "expected_and_quiet",
            "quiet_without_expected",
            "timeout",
            "interaction_failed",
        ),
        required=True,
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


def runtime_check_by_id(ledger: dict[str, Any], check_id: str) -> dict[str, Any]:
    """Return one unique directly captured runtime check."""
    return find_unique(ledger.get("runtime_checks", []), "check_id", check_id)


def void_runtime_check(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Retain but explicitly void an unconsumed check that never became an action boundary."""
    check = runtime_check_by_id(ledger, args.check_id)
    if check.get("consumed") is True:
        raise SystemExit("A consumed runtime check cannot be voided.")
    if any(
        args.check_id in {row.get("readiness_check_id"), row.get("settlement_check_id")}
        for row in ledger.get("actions", [])
        if isinstance(row, dict)
    ):
        raise SystemExit("A runtime check referenced by an action cannot be voided.")
    reason = str(args.reason).strip()
    if not reason:
        raise SystemExit("Voiding a runtime check requires an exact reason.")
    if check.get("voided") is True:
        raise SystemExit("The runtime check is already voided.")
    check.update({"voided": True, "void_reason": reason, "voided_at": now()})


def record_runtime_check(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Record one direct browser/Preview/network state capture."""
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read runtime snapshot: {exc}") from exc
    if not isinstance(snapshot, dict):
        raise SystemExit("Runtime snapshot must be a JSON object.")
    check_id = str(snapshot.get("check_id", "")).strip()
    if any(
        row.get("check_id") == check_id
        for row in ledger.get("runtime_checks", [])
        if isinstance(row, dict)
    ):
        raise SystemExit(f"Duplicate runtime check ID: {check_id}")
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    action_matches = [
        row
        for row in ledger.get("actions", [])
        if isinstance(row, dict) and row.get("action_id") == args.action_id
    ]
    if args.phase == "before_action" and action_matches:
        raise SystemExit("A before-action runtime check must precede action registration.")
    if args.phase in {"resume", "after_action", "interrupted_action"}:
        if len(action_matches) != 1 or action_matches[0].get("state") != "OPEN":
            raise SystemExit(f"A {args.phase} runtime check requires the matching open action.")
        if action_matches[0].get("case_id") != args.case_id:
            raise SystemExit("Runtime check action and case identities differ.")
    try:
        normalized = normalize_runtime_check(
            snapshot,
            phase=args.phase,
            action_id=args.action_id,
            case=case,
            ledger=ledger,
            results=load_results(args.results),
            recorded_at=now(),
            action_timestamp=(
                action_matches[0].get("action_timestamp") if action_matches else None
            ),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    ledger.setdefault("runtime_checks", []).append(normalized)


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
    contract_v2 = ledger.get("operator_contract_version") == 2
    v2_fields = {
        "coverage_decision_id": getattr(args, "coverage_decision_id", None),
        "scenario_class_id": getattr(args, "scenario_class_id", None),
        "sample_role": getattr(args, "sample_role", None),
        "selection_rationale": getattr(args, "selection_rationale", None),
        "population_member_id": getattr(args, "population_member_id", None),
    }
    if contract_v2:
        missing_v2 = [field for field, value in v2_fields.items() if not str(value or "").strip()]
        if missing_v2:
            raise SystemExit("Operator-contract-v2 cases require " + ", ".join(missing_v2) + ".")
        dimension_values = parse_variant(getattr(args, "dimension_value", []))
        if not dimension_values:
            raise SystemExit("Operator-contract-v2 cases require --dimension-value bindings.")
        acquisition_path = getattr(args, "acquisition_context", None)
        if isinstance(acquisition_path, dict):
            acquisition_context = deepcopy(acquisition_path)
        elif isinstance(acquisition_path, Path):
            try:
                acquisition_context = load_json_object(acquisition_path)
            except (OSError, ValueError) as exc:
                raise SystemExit(f"Cannot read acquisition context: {exc}") from exc
        else:
            raise SystemExit("Operator-contract-v2 cases require --acquisition-context JSON.")
    else:
        acquisition_context = None
    unknown_authorizations = sorted(
        value
        for value in args.authorization_id
        if not any(row.get("authorization_id") == value for row in ledger.get("authorizations", []))
    )
    if unknown_authorizations:
        raise SystemExit("Unknown authorization IDs: " + ", ".join(unknown_authorizations))
    if args.include_layer or args.exclude_layer:
        raise SystemExit(
            "Manual layer inclusion/exclusion is obsolete. Core layers are mandatory; "
            "use --activate-condition LAYER=REASON only for detected conditional predicates."
        )
    containers = [
        row for row in results.get("run", {}).get("containers", []) if isinstance(row, dict)
    ]
    activated_conditions = parse_condition_activations(getattr(args, "activate_condition", []))
    applicability = layer_applicability(
        group_requirements,
        container_count=len(containers) or 1,
        activated_conditions=activated_conditions,
    )
    layers = [row["layer"] for row in applicability if row["mode"] == "MANDATORY"]
    run = results.get("run", {}) if isinstance(results.get("run"), dict) else {}
    container_ids = sorted(
        {
            str(row.get("container_id", "")).strip()
            for row in run.get("containers", [])
            if isinstance(row, dict) and str(row.get("container_id", "")).strip()
        }
        or (
            {str(run.get("container_id", "")).strip()}
            if str(run.get("container_id", "")).strip()
            else set()
        )
    )
    case_record = {
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
        "execution_status": ("NOT_TESTED" if args.scope_status == "OUT_OF_SCOPE" else "PENDING"),
        "reason": str(args.reason or "").strip() or None,
        "authorization_ids": list(dict.fromkeys(args.authorization_id)),
        "tag_scope": normalize_tag_scope(results.get("run", {}).get("tag_scope")),
        "declared_tag_contracts": declared_tag_contracts(group_requirements),
        "source_expectations": [dict(row.get("expectation", {})) for row in group_requirements],
        "tag_inventory_status": "PENDING",
        "inventory_revision": 1,
        "applicability_history": [],
        "tag_inventory_reason": None,
        "tag_inventory_evidence_ids": [],
        "tag_inventory": [],
        "conditional_activations": activated_conditions,
        "applicability_status": "DRAFT",
        "layer_applicability": applicability,
        "applicable_layers": layers,
        "container_ids": container_ids,
        "registered_at": now(),
        "final_action_id": None,
    }
    if contract_v2:
        case_record.update(
            {
                **v2_fields,
                "sample_role": str(v2_fields["sample_role"]).strip().upper(),
                "dimension_values": dimension_values,
                "acquisition_context": acquisition_context,
                "gated_flow_kind": getattr(args, "gated_flow_kind", "NONE"),
            }
        )
    ledger.setdefault("cases", []).append(case_record)


def register_tag(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Register one detected concerned tag before the case action begins."""
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if case.get("applicability_status") != "DRAFT":
        raise SystemExit("Tag inventory is frozen for this case.")
    if any(
        row.get("tag_id") == args.tag_id
        for row in case.get("tag_inventory", [])
        if isinstance(row, dict)
    ):
        raise SystemExit(f"Duplicate tag_id in case {args.case_id}: {args.tag_id}")
    if args.container_id not in case.get("container_ids", []):
        raise SystemExit("Detected tag container is outside the case container set.")
    tag = {
        "tag_id": args.tag_id,
        "tag_name": args.tag_name,
        "container_id": args.container_id,
        "tag_category": args.tag_category,
        "tag_delivery": args.tag_delivery,
        "vendor_family": str(args.vendor_family or "").strip() or None,
        "destination_id": str(args.destination_id or "").strip() or None,
        "template_type": args.template_type,
        "consent_required": args.consent_required == "true",
        "evidence_ids": list(dict.fromkeys(args.evidence_id)),
    }
    inferred_category = inferred_tag_category(tag)
    if inferred_category is not None and args.tag_category != inferred_category:
        raise SystemExit(
            f"Tag metadata identifies category {inferred_category}; received {args.tag_category}."
        )
    scope_status, scope_reason = tag_scope_decision(
        tag,
        case.get("tag_scope"),
        case.get("declared_tag_contracts", []),
    )
    tag["scope_status"] = scope_status
    tag["scope_reason"] = scope_reason
    case.setdefault("tag_inventory", []).append(tag)


def revise_tag_inventory(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Version a frozen inventory after a material late tag discovery and force retest."""
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if case.get("applicability_status") != "FROZEN":
        raise SystemExit("Late discovery requires an already frozen applicability card.")
    case_actions = sorted(
        [row for row in ledger.get("actions", []) if row.get("case_id") == args.case_id],
        key=lambda row: row.get("attempt_number", 0),
    )
    if not case_actions or case_actions[-1].get("state") != "SETTLED":
        raise SystemExit("Settle the current action before revising a frozen tag inventory.")
    if any(
        row.get("tag_id") == args.tag_id
        for row in case.get("tag_inventory", [])
        if isinstance(row, dict)
    ):
        raise SystemExit(f"Duplicate tag_id in case {args.case_id}: {args.tag_id}")
    if args.container_id not in case.get("container_ids", []):
        raise SystemExit("Detected tag container is outside the case container set.")
    reason = str(args.reason).strip()
    if not reason:
        raise SystemExit("Late discovery requires an exact reason.")
    prior_revision = int(case.get("inventory_revision", 1))
    case.setdefault("applicability_history", []).append(
        {
            "inventory_revision": prior_revision,
            "tag_inventory": deepcopy(case.get("tag_inventory", [])),
            "layer_applicability": deepcopy(case.get("layer_applicability", [])),
            "applicable_layers": deepcopy(case.get("applicable_layers", [])),
            "frozen_at": case.get("applicability_frozen_at"),
            "superseded_by_action_id": case_actions[-1].get("action_id"),
            "superseded_reason": reason,
        }
    )
    tag = {
        "tag_id": args.tag_id,
        "tag_name": args.tag_name,
        "container_id": args.container_id,
        "tag_category": args.tag_category,
        "tag_delivery": args.tag_delivery,
        "vendor_family": str(args.vendor_family or "").strip() or None,
        "destination_id": str(args.destination_id or "").strip() or None,
        "template_type": args.template_type,
        "consent_required": args.consent_required == "true",
        "evidence_ids": list(dict.fromkeys(args.evidence_id)),
    }
    inferred_category = inferred_tag_category(tag)
    if inferred_category is not None and args.tag_category != inferred_category:
        raise SystemExit(
            f"Tag metadata identifies category {inferred_category}; received {args.tag_category}."
        )
    tag["scope_status"], tag["scope_reason"] = tag_scope_decision(
        tag,
        case.get("tag_scope"),
        case.get("declared_tag_contracts", []),
    )
    inventory = [
        *[row for row in case.get("tag_inventory", []) if isinstance(row, dict)],
        tag,
    ]
    applicability = layer_applicability(
        [
            {"scope_status": "IN_SCOPE", "expectation": expectation}
            for expectation in case.get("source_expectations", [])
        ],
        container_count=max(1, len(case.get("container_ids", []))),
        tag_inventory=inventory,
        activated_conditions=case.get("conditional_activations", {}),
    )
    prior_action_id = str(case_actions[-1].get("action_id"))
    case.update(
        {
            "inventory_revision": prior_revision + 1,
            "tag_inventory": inventory,
            "tag_inventory_status": "COMPLETE",
            "tag_inventory_reason": reason,
            "tag_inventory_evidence_ids": list(
                dict.fromkeys([*case.get("tag_inventory_evidence_ids", []), *args.evidence_id])
            ),
            "layer_applicability": applicability,
            "applicable_layers": [
                row["layer"] for row in applicability if row.get("mode") == "MANDATORY"
            ],
            "applicability_frozen_at": now(),
            "execution_status": "PENDING",
            "final_action_id": None,
            "required_retest_of_action_id": prior_action_id,
        }
    )
    event_group_id = str(case.get("event_group_id", ""))
    _invalidate_closures_from(ledger, event_group_id, reason)
    ledger["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": event_group_id,
    }


def complete_tag_inventory(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Freeze the per-case tag inventory and immutable applicability card."""
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if case.get("applicability_status") != "DRAFT":
        raise SystemExit("Case applicability is already frozen.")
    reason = str(args.reason).strip()
    if not reason:
        raise SystemExit("Tag inventory completion requires an exact reason.")
    inventory = [row for row in case.get("tag_inventory", []) if isinstance(row, dict)]
    applicability = layer_applicability(
        [
            {"scope_status": "IN_SCOPE", "expectation": expectation}
            for expectation in case.get("source_expectations", [])
        ],
        container_count=max(1, len(case.get("container_ids", []))),
        tag_inventory=inventory,
        activated_conditions=case.get("conditional_activations", {}),
    )
    # Backward-compatible fallback for a draft created before source expectations were stored.
    if not case.get("source_expectations"):
        applicability = list(case.get("layer_applicability", []))
        mandatory = {row["layer"] for row in applicability if row.get("mode") == "MANDATORY"}
        in_scope = [row for row in inventory if row.get("scope_status") == "IN_SCOPE"]
        if any(row.get("consent_required") is True for row in in_scope):
            mandatory.add("consent_when_applicable")
        if in_scope and all(row.get("tag_delivery") == "local_only" for row in in_scope):
            mandatory.discard("destination_request_when_applicable")
        applicability = [
            {
                **row,
                "mode": "MANDATORY" if row.get("layer") in mandatory else row.get("mode"),
                "reason": (
                    "A concerned tag declares consent requirements."
                    if row.get("layer") == "consent_when_applicable"
                    and row.get("layer") in mandatory
                    else row.get("reason")
                ),
            }
            for row in applicability
        ]
    case.update(
        {
            "tag_inventory_status": "COMPLETE",
            "tag_inventory_reason": reason,
            "tag_inventory_evidence_ids": list(dict.fromkeys(args.evidence_id)),
            "applicability_status": "FROZEN",
            "layer_applicability": applicability,
            "applicable_layers": [
                row["layer"] for row in applicability if row.get("mode") == "MANDATORY"
            ],
            "applicability_frozen_at": now(),
        }
    )


def _tag_batch_matrix_errors(
    ledger: dict[str, Any],
    action: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[str]:
    """Require the exact frozen in-scope tag x canonical tag-layer matrix."""
    case = find_unique(ledger.get("cases", []), "case_id", str(action.get("case_id", "")))
    inventory_ids = {
        str(row.get("tag_id", "")).strip()
        for row in case.get("tag_inventory", [])
        if isinstance(row, dict)
        and row.get("scope_status") == "IN_SCOPE"
        and str(row.get("tag_id", "")).strip()
    }
    expected = {(tag_id, layer) for tag_id in inventory_ids for layer in TAG_RESULT_LAYERS}
    actual = [
        (str(row.get("tag_id", "")).strip(), str(row.get("layer", "")).strip()) for row in rows
    ]
    errors: list[str] = []
    duplicates = sorted({key for key in actual if actual.count(key) > 1})
    if duplicates:
        errors.append(
            "duplicate tag/layer rows: "
            + ", ".join(f"{tag_id}:{layer}" for tag_id, layer in duplicates)
        )
    actual_keys = set(actual)
    missing = sorted(expected - actual_keys)
    extra = sorted(actual_keys - expected)
    if missing:
        errors.append(
            "missing tag/layer rows: " + ", ".join(f"{tag_id}:{layer}" for tag_id, layer in missing)
        )
    if extra:
        errors.append(
            "unknown or out-of-scope tag/layer rows: "
            + ", ".join(f"{tag_id}:{layer}" for tag_id, layer in extra)
        )
    return errors


def import_tag_results(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Atomically replace one complete, validated tag x layer batch on an open action."""
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if action.get("state") != "OPEN":
        raise SystemExit("Tag results can be imported only for an open action.")
    value = _read_json(args.tag_results, "tag results JSON")
    contract_v2 = ledger.get("operator_contract_version") == 2
    if contract_v2:
        _require_artifact_run_id(ledger, value, "Tag results")
        if value.get("action_id") != args.action_id:
            raise SystemExit("Tag results action_id differs from the requested open action.")
        if value.get("inventory_revision") != action.get("inventory_revision", 1):
            raise SystemExit("Tag results inventory_revision differs from the open action.")
    elif isinstance(value, dict) and value.get("action_id") not in (None, args.action_id):
        raise SystemExit("Tag results action_id differs from the requested open action.")

    rows_value = value.get("tag_layer_results") if isinstance(value, dict) else value
    rows = _object_array(rows_value, "tag_layer_results")
    recorded_at = now()
    for index, row in enumerate(rows, start=1):
        if row.get("layer") not in TAG_RESULT_LAYERS:
            raise SystemExit(f"Tag result row {index} has an unsupported layer.")
        supplied_action_id = str(row.get("action_id", "")).strip()
        if contract_v2 and supplied_action_id != args.action_id:
            raise SystemExit(f"Tag result row {index} has the wrong action_id.")
        if supplied_action_id not in ("", args.action_id):
            raise SystemExit(f"Tag result row {index} has the wrong action_id.")
        row["action_id"] = args.action_id
        row.setdefault("recorded_at", recorded_at)

    matrix_errors = _tag_batch_matrix_errors(ledger, action, rows)
    if matrix_errors:
        raise SystemExit(
            "Tag result batch is incomplete or inconsistent:\n" + "\n".join(matrix_errors)
        )

    results_path = getattr(args, "results", None)
    if contract_v2 and not isinstance(results_path, Path):
        raise SystemExit("Operator-contract-v2 tag imports require --results.")
    results = load_results(results_path) if isinstance(results_path, Path) else None
    if contract_v2:
        _require_results_run_id(ledger, results, "Tag results")

    staged = deepcopy(ledger)
    staged_action = find_unique(staged.get("actions", []), "action_id", args.action_id)
    staged_action["tag_layer_results"] = rows
    errors = validate_session(staged, results=results, final=False)
    if errors:
        raise SystemExit("Tag result batch failed staged session validation:\n" + "\n".join(errors))
    ledger.clear()
    ledger.update(staged)


def _comparison_template(
    requirement_id: str,
    source: str,
    path: str,
    *,
    transform: str = "identity",
) -> dict[str, Any]:
    anchor = {"source": source, "requirement_id": requirement_id, "path": path}
    if transform != "identity":
        anchor["transform"] = transform
    return {
        "name": "replace-with-exact-field-name",
        "expected_anchor": anchor,
        "expected_value": None,
        "expected_type": "null",
        "actual_value": None,
        "actual_type": "null",
        "status": "BLOCKED",
    }


def build_tag_result_scaffold(ledger: dict[str, Any], action_id: str) -> dict[str, Any]:
    """Return the exact in-scope tag x layer matrix without writing run-specific code."""
    action = find_unique(ledger.get("actions", []), "action_id", action_id)
    case = find_unique(ledger.get("cases", []), "case_id", str(action.get("case_id")))
    requirement_ids = [str(value) for value in action.get("requirement_ids", []) if str(value)]
    if not requirement_ids:
        raise SystemExit("The action has no accepted requirement IDs.")
    requirement_id = requirement_ids[0]
    output: list[dict[str, Any]] = []
    for tag in case.get("tag_inventory", []):
        if not isinstance(tag, dict) or tag.get("scope_status") != "IN_SCOPE":
            continue
        details_by_layer = {
            "gtm_variable": {
                "variables": [
                    _comparison_template(
                        requirement_id,
                        "raw_data_layer_mapping",
                        "resolved_data_layer.field_value",
                    )
                ]
            },
            "tag_configuration": {
                "configuration": [
                    _comparison_template(
                        requirement_id,
                        "tracking_plan",
                        "expectation.expected_tag_configuration",
                    )
                ]
            },
            "tag_firing": {
                "expected_firing": None,
                "expected_firing_anchor": {
                    "source": "tracking_plan",
                    "requirement_id": requirement_id,
                    "path": "expectation.expected_firing",
                },
                "actual_firing": None,
                "fire_count": 0,
            },
            "tag_parameter": {
                "parameters": [
                    _comparison_template(
                        requirement_id,
                        "resolved_gtm_variable_contract",
                        "gtm_variable.field_value",
                    )
                ]
            },
            "destination_request_when_applicable": {
                "request_count": 0,
                "request_ids": [],
                "expected_request_behavior": None,
                "expected_request_behavior_anchor": {
                    "source": "tracking_plan",
                    "requirement_id": requirement_id,
                    "path": "expectation.expected_request_behavior",
                },
                "parameters": [
                    _comparison_template(
                        requirement_id,
                        "explicit_acceptance_rule",
                        "expectation.expected_request_behavior",
                        transform="request_expected",
                    )
                ],
            },
            "consent_when_applicable": {"predicate_reason": "replace-with-direct-proof"},
            "trigger_logic_when_applicable": {"predicate_reason": "replace-with-direct-proof"},
            "tag_sequence_when_applicable": {"predicate_reason": "replace-with-direct-proof"},
        }
        for layer in TAG_RESULT_LAYERS:
            output.append(
                {
                    "action_id": action_id,
                    "tag_id": tag.get("tag_id"),
                    "tag_name": tag.get("tag_name"),
                    "container_id": tag.get("container_id"),
                    "tag_category": tag.get("tag_category"),
                    "tag_delivery": tag.get("tag_delivery"),
                    "layer": layer,
                    "status": "PENDING",
                    "reason": "Pending direct evidence.",
                    "details": details_by_layer[layer],
                    "evidence_ids": [],
                    "semantic_ambiguity": None,
                    "blocker_id": None,
                }
            )
    artifact: dict[str, Any] = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "action_id": action_id,
        "inventory_revision": case.get("inventory_revision", 1),
        "tag_layer_results": output,
    }
    if ledger.get("operator_contract_version") == 2:
        artifact["run_id"] = _session_run_id(ledger)
    return artifact


def scaffold_tag_results(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Write the exact in-scope tag x layer matrix as a fillable import template."""
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if action.get("state") != "OPEN":
        raise SystemExit("Tag result scaffolding requires an open action.")
    artifact = build_tag_result_scaffold(ledger, args.action_id)
    save(args.output, artifact)
    print(f"Created {args.output.resolve()}")


def begin_action(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    require_surfaces(ledger)
    if any(row.get("action_id") == args.action_id for row in ledger.get("actions", [])):
        raise SystemExit(f"Duplicate action_id: {args.action_id}")
    case = find_unique(ledger.get("cases", []), "case_id", args.case_id)
    if case.get("scope_status") != "IN_SCOPE":
        raise SystemExit("Actions can start only for an applicable case.")
    if (
        case.get("tag_inventory_status") != "COMPLETE"
        or case.get("applicability_status") != "FROZEN"
    ):
        raise SystemExit(
            "Complete the concerned-tag inventory and freeze the applicability card "
            "before beginning the action."
        )
    if ledger.get("operator_contract_version") == 2:
        decision = next(
            (
                row
                for row in ledger.get("coverage_decisions", [])
                if isinstance(row, dict)
                and row.get("coverage_decision_id") == case.get("coverage_decision_id")
            ),
            None,
        )
        if not isinstance(decision, dict) or decision.get("status") != "FROZEN":
            raise SystemExit(
                "Freeze the event scenario-coverage decision before beginning an action."
            )
    if args.quiet_window_ms <= 0 or args.timeout_ms <= 0:
        raise SystemExit("Quiet window and timeout must be positive.")
    readiness = runtime_check_by_id(ledger, args.readiness_check_id)
    if readiness.get("voided") is True:
        raise SystemExit("A voided runtime check cannot begin an action.")
    if readiness.get("phase") != "before_action":
        raise SystemExit("begin-action requires a before_action runtime check.")
    if readiness.get("action_id") != args.action_id or readiness.get("case_id") != args.case_id:
        raise SystemExit("The readiness check is bound to another action or case.")
    if readiness.get("consumed") is True:
        raise SystemExit("The readiness check has already been consumed.")
    if readiness.get("connection_epoch") != ledger.get("connection_epoch", 1):
        raise SystemExit("The readiness check belongs to a stale Preview connection epoch.")
    invalid_page_capture = (
        ledger.get("operator_contract_version") == 2
        and isinstance(readiness.get("page_health"), dict)
        and readiness["page_health"].get("status") == "FAIL"
    )
    readiness_fields = (
        (
            "preview_connected",
            "lifecycle_observed",
            "stream_quiet",
            "network_capture_active",
        )
        if invalid_page_capture
        else (
            "preview_connected",
            "target_interactive",
            "target_uncovered",
            "lifecycle_observed",
            "stream_quiet",
            "network_capture_active",
        )
    )
    if not all(readiness.get(field_name) is True for field_name in readiness_fields):
        raise SystemExit("The readiness check is not fully ready for a business action.")
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
    retrying_interruption = case.get("execution_status") == "BLOCKED"
    if retrying_interruption:
        prior = previous[-1] if previous else None
        if not (
            isinstance(prior, dict)
            and prior.get("state") == "SETTLED"
            and prior.get("settlement_reason") in INTERRUPTION_REASONS
            and prior.get("interaction_outcome") == "uncertain"
            and str(prior.get("interruption_blocker_id", "")).strip()
            and str(prior.get("interruption_reason", "")).strip()
            and args.retry_of_action_id == prior.get("action_id")
        ):
            raise SystemExit(
                "A blocked case can restart only as a linked retry of its immediately prior "
                "retained runtime interruption."
            )
    required_retest = case.get("required_retest_of_action_id")
    if required_retest and args.retry_of_action_id != required_retest:
        raise SystemExit(
            "Late tag discovery requires a retry of the retained pre-discovery action."
        )
    container_ids = [
        str(row.get("container_id", ""))
        for row in readiness.get("containers", [])
        if isinstance(row, dict) and str(row.get("container_id", "")).strip()
    ]
    if not container_ids:
        raise SystemExit("The action requires at least one client-side container ID.")
    if len(container_ids) > 1:
        raise SystemExit(
            "The guided action has one Preview and network cursor. Use one container-scoped "
            "certified run per applicable client container."
        )
    if retrying_interruption:
        case.update(
            {
                "execution_status": "PENDING",
                "final_action_id": None,
                "blocker_id": None,
                "reason": None,
            }
        )
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
        "inventory_revision": case.get("inventory_revision", 1),
        "connection_epoch": ledger.get("connection_epoch", 1),
        "retry_of_action_id": args.retry_of_action_id,
        "readiness_check_id": readiness.get("check_id"),
        "readiness_evidence_ids": list(readiness.get("evidence_ids", [])),
        "preview_connected_before": readiness.get("preview_connected"),
        "target_ready_before": all(
            readiness.get(field_name) is True
            for field_name in (
                "target_interactive",
                "target_uncovered",
                "lifecycle_observed",
                "stream_quiet",
            )
        ),
        "last_event_before": readiness.get("preview_event_cursor"),
        "network_request_cursor_before": readiness.get("network_request_cursor"),
        "consent_state_before": args.consent_state,
        "browser_context_id": readiness.get("browser_context_id"),
        "container_ids": list(dict.fromkeys(container_ids)),
        "observed_url_before": readiness.get("website_url"),
        "selected_page_url_before": readiness.get("selected_page_url"),
        "action_timestamp": now(),
        "quiet_window_ms": args.quiet_window_ms,
        "timeout_ms": args.timeout_ms,
        "layer_results": [],
        "tag_layer_results": [],
        "state": "OPEN",
    }
    if ledger.get("operator_contract_version") == 2:
        action.update(
            {
                "datalayer_call_index_before": readiness.get("datalayer_call_cursor"),
                "page_health_before": deepcopy(readiness.get("page_health")),
            }
        )
    readiness["consumed"] = True
    readiness["consumed_by_action_id"] = args.action_id
    ledger.setdefault("actions", []).append(action)


def record_push(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    if any(row.get("push_id") == args.push_id for row in ledger.get("business_pushes", [])):
        raise SystemExit(f"Duplicate push_id: {args.push_id}")
    contract_v2 = ledger.get("operator_contract_version") == 2
    action_id = str(getattr(args, "action_id", None) or "").strip()
    action = find_unique(ledger.get("actions", []), "action_id", action_id) if action_id else None
    if action is None and not contract_v2:
        raise SystemExit("Legacy business pushes require --action-id.")
    if action is not None and action.get("state") != "OPEN":
        raise SystemExit("Action-bound business pushes require an open action.")
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
    if action is not None and args.event_index <= action.get("last_event_before", -1):
        raise SystemExit("Business push event_index must follow last_event_before.")
    connection_epoch = args.connection_epoch
    if connection_epoch is None:
        connection_epoch = (
            action.get("connection_epoch", ledger.get("connection_epoch", 1))
            if action is not None
            else ledger.get("connection_epoch", 1)
        )
    if connection_epoch < 1:
        raise SystemExit("connection_epoch must be a positive integer.")
    if action is not None and connection_epoch != action.get("connection_epoch", 1):
        raise SystemExit("connection_epoch must match the open action connection epoch.")
    segment_id = str(getattr(args, "segment_id", None) or "").strip()
    preview_event_index = getattr(args, "preview_event_index", None)
    datalayer_call_index = getattr(args, "datalayer_call_index", None)
    if contract_v2:
        if not segment_id:
            raise SystemExit("Operator-contract-v2 pushes require --segment-id.")
        if preview_event_index is None:
            preview_event_index = args.event_index
        if datalayer_call_index is None and preview_event_index is None:
            raise SystemExit("Operator-contract-v2 pushes require a Preview or dataLayer index.")
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
    if group_id is None and action is not None:
        group_id = action.get("event_group_id")
    if contract_v2 and not str(group_id or "").strip():
        raise SystemExit(
            "Operator-contract-v2 pushes require --event-group-id so anomalies affect "
            "an explicit event verdict."
        )
    push_record = {
        "push_id": args.push_id,
        "stream_id": args.stream_id,
        "connection_epoch": connection_epoch,
        "action_id": action_id or None,
        "case_id": action.get("case_id") if action is not None else None,
        "event_group_id": group_id,
        "event_name": args.event_name,
        "event_index": args.event_index,
        "captured_at": captured_at or now(),
        "url": args.url or (action.get("url") if action is not None else None),
        "page_state": args.page_state,
        "classification": args.classification,
        "classification_reason": args.classification_reason,
        "evidence_id": args.evidence_id,
        "container_id": args.container_id,
    }
    if contract_v2:
        push_record.update(
            {
                "segment_id": segment_id,
                "preview_event_index": preview_event_index,
                "datalayer_call_index": datalayer_call_index,
            }
        )
    ledger.setdefault("business_pushes", []).append(push_record)


def import_pushes(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    value = json.loads(args.push_file.read_text(encoding="utf-8"))
    pushes = value.get("pushes") if isinstance(value, dict) else value
    if not isinstance(pushes, list) or any(not isinstance(row, dict) for row in pushes):
        raise SystemExit("Push import must be a JSON array or an object with a pushes array.")
    required = {
        "push_id",
        "event_index",
        "event_name",
        "classification",
        "classification_reason",
        "page_state",
        "evidence_id",
        "container_id",
    }
    if ledger.get("operator_contract_version") != 2:
        required.add("action_id")
    for index, row in enumerate(pushes, start=1):
        missing = sorted(key for key in required if row.get(key) in (None, ""))
        if missing:
            raise SystemExit(f"Push import row {index} is missing: " + ", ".join(missing))
        record_push(
            ledger,
            argparse.Namespace(
                push_id=row["push_id"],
                action_id=row.get("action_id"),
                segment_id=row.get("segment_id"),
                event_index=row["event_index"],
                preview_event_index=row.get("preview_event_index"),
                datalayer_call_index=row.get("datalayer_call_index"),
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


def _require_contract_v2(ledger: dict[str, Any], operation: str) -> None:
    if ledger.get("operator_contract_version") != 2:
        raise SystemExit(f"{operation} requires operator_contract_version=2.")


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read {label}: {exc}") from exc


def _session_run_id(ledger: dict[str, Any]) -> str:
    run_id = str(ledger.get("run_id", "")).strip()
    if not run_id:
        raise SystemExit(
            "Operator-contract-v2 session is not bound to a normalized run_id; recreate it."
        )
    return run_id


def _require_artifact_run_id(
    ledger: dict[str, Any],
    value: Any,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} import must be an object containing run_id.")
    expected = _session_run_id(ledger)
    actual = str(value.get("run_id", "")).strip()
    if not actual:
        raise SystemExit(f"{label} import requires run_id={expected}.")
    if actual != expected:
        raise SystemExit(
            f"{label} run_id '{actual}' differs from session run_id '{expected}'; "
            "previous-run artifacts cannot be imported."
        )
    return value


def _require_results_run_id(
    ledger: dict[str, Any],
    results: dict[str, Any] | None,
    label: str,
) -> None:
    if not isinstance(results, dict) or not isinstance(results.get("run"), dict):
        raise SystemExit(f"{label} requires normalized results with run.run_id.")
    expected = _session_run_id(ledger)
    actual = str(results["run"].get("run_id", "")).strip()
    if actual != expected:
        raise SystemExit(
            f"{label} normalized run_id '{actual or 'missing'}' differs from "
            f"session run_id '{expected}'."
        )


def _object_array(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise SystemExit(f"{label} must be an array of objects.")
    return deepcopy(value)


def _invalidate_closures_from(
    ledger: dict[str, Any],
    event_group_id: str,
    reason: str,
) -> None:
    closures = [row for row in ledger.get("event_closures", []) if isinstance(row, dict)]
    closure_index = next(
        (
            index
            for index, row in enumerate(closures)
            if str(row.get("event_group_id", "")) == event_group_id
        ),
        None,
    )
    if closure_index is None:
        return
    invalidated = deepcopy(closures[closure_index:])
    ledger["event_closures"] = deepcopy(closures[:closure_index])
    ledger.setdefault("closure_history", []).append(
        {
            "reopened_event_group_id": event_group_id,
            "reopened_at": now(),
            "reason": reason,
            "invalidated_closures": invalidated,
        }
    )
    ledger["operator_state"] = {
        "status": "ACTIVE",
        "current_event_group_id": event_group_id,
    }


def import_coverage(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Replace the explainable scenario-coverage ledger and reopen stale closures."""
    _require_contract_v2(ledger, "Scenario coverage")
    value = _require_artifact_run_id(
        ledger,
        _read_json(args.coverage, "coverage JSON"),
        "Scenario coverage",
    )
    decisions_value = value.get("coverage_decisions")
    decisions = _object_array(decisions_value, "coverage_decisions")
    prior = {
        str(row.get("event_group_id", "")): row
        for row in ledger.get("coverage_decisions", [])
        if isinstance(row, dict)
    }
    ledger["coverage_decisions"] = decisions
    closed_groups = {
        str(row.get("event_group_id", ""))
        for row in ledger.get("event_closures", [])
        if isinstance(row, dict)
    }
    changed = [
        str(row.get("event_group_id", ""))
        for row in decisions
        if str(row.get("event_group_id", "")) in closed_groups
        and prior.get(str(row.get("event_group_id", ""))) != row
    ]
    if changed:
        closure_order = [
            str(row.get("event_group_id", ""))
            for row in ledger.get("event_closures", [])
            if isinstance(row, dict)
        ]
        first_changed = min(changed, key=closure_order.index)
        _invalidate_closures_from(
            ledger,
            first_changed,
            "Scenario coverage changed after event closure; affected events require retest.",
        )


def import_stream(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    _require_contract_v2(ledger, "Continuous stream import")
    value = _require_artifact_run_id(
        ledger,
        _read_json(args.stream, "stream JSON"),
        "Continuous stream",
    )
    if not isinstance(value.get("stream_contract"), dict):
        raise SystemExit("Stream import requires stream_contract and stream_segments.")
    ledger["stream_contract"] = deepcopy(value["stream_contract"])
    ledger["stream_segments"] = _object_array(value.get("stream_segments"), "stream_segments")


def import_semantic(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    _require_contract_v2(ledger, "Semantic evidence import")
    value = _require_artifact_run_id(
        ledger,
        _read_json(args.semantic, "semantic JSON"),
        "Semantic evidence",
    )
    ledger["journey_states"] = _object_array(value.get("journey_states"), "journey_states")
    ledger["semantic_checks"] = _object_array(value.get("semantic_checks"), "semantic_checks")


def import_protected_handoffs(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    _require_contract_v2(ledger, "Protected handoff import")
    value = _require_artifact_run_id(
        ledger,
        _read_json(args.handoffs, "protected handoff JSON"),
        "Protected handoff",
    )
    rows = value.get("protected_handoffs")
    ledger["protected_handoffs"] = _object_array(rows, "protected_handoffs")


def import_gated_flows(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    _require_contract_v2(ledger, "Gated-flow import")
    value = _require_artifact_run_id(
        ledger,
        _read_json(args.flows, "gated-flow JSON"),
        "Gated flow",
    )
    rows = value.get("gated_flows")
    ledger["gated_flows"] = _object_array(rows, "gated_flows")


def verify_evidence(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    _require_contract_v2(ledger, "Evidence verification")
    if not args.base_dir.is_dir():
        raise SystemExit(f"Evidence base directory does not exist: {args.base_dir}")
    try:
        ledger["evidence_integrity"] = build_integrity_record(
            load_results(args.results), args.base_dir
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot verify evidence: {exc}") from exc


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
                activate_condition=[],
                coverage_decision_id=row.get("coverage_decision_id"),
                scenario_class_id=row.get("scenario_class_id"),
                sample_role=row.get("sample_role"),
                selection_rationale=row.get("selection_rationale"),
                population_member_id=row.get("population_member_id"),
                acquisition_context=row.get("acquisition_context"),
                gated_flow_kind=row.get("gated_flow_kind", "NONE"),
            ),
        )


def record_layer(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if not isinstance(args.layer, str) or args.layer not in CANONICAL_LAYERS:
        raise SystemExit(f"Unsupported canonical layer: {args.layer}")
    if not isinstance(args.status, str) or args.status not in LAYER_RESULT_STATUSES:
        raise SystemExit(f"Unsupported layer status: {args.status}")
    reason = str(args.reason).strip()
    if not reason:
        raise SystemExit("Layer evidence requires a non-empty reason.")
    if (
        not isinstance(args.evidence_id, list)
        or not args.evidence_id
        or any(not isinstance(value, str) or not value.strip() for value in args.evidence_id)
    ):
        raise SystemExit("Layer evidence_ids must be a non-empty string array.")
    if len(set(args.evidence_id)) != len(args.evidence_id):
        raise SystemExit("Layer evidence_ids contain duplicates.")
    if args.predicate_result not in (None, "true", "false"):
        raise SystemExit("predicate_result must be true, false, or omitted.")
    case = find_unique(
        ledger.get("cases", []),
        "case_id",
        str(action.get("case_id")),
    )
    decisions = {
        row.get("layer"): row
        for row in case.get("layer_applicability", [])
        if isinstance(row, dict)
    }
    decision = decisions.get(args.layer)
    if decision is None:
        raise SystemExit(f"Layer is absent from the frozen applicability card: {args.layer}")
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
    predicate_result = (
        args.predicate_result == "true" if args.predicate_result is not None else None
    )
    if decision.get("mode") == "MANDATORY":
        if args.status == "NOT_APPLICABLE":
            raise SystemExit("A mandatory layer cannot be NOT_APPLICABLE.")
        if predicate_result is False:
            raise SystemExit("A mandatory layer cannot have predicate_result=false.")
    else:
        if predicate_result is None:
            raise SystemExit("Conditional layers require --predicate-result true or false.")
        if predicate_result is False and args.status != "NOT_APPLICABLE":
            raise SystemExit("A false conditional predicate requires NOT_APPLICABLE.")
        if predicate_result is True and args.status == "NOT_APPLICABLE":
            raise SystemExit("An activated conditional layer cannot be NOT_APPLICABLE.")
    action.setdefault("layer_results", []).append(
        {
            "layer": args.layer,
            "status": args.status,
            "reason": reason,
            "evidence_ids": list(args.evidence_id),
            "semantic_ambiguity": (
                str(args.semantic_ambiguity).strip() if args.semantic_ambiguity else None
            ),
            "blocker_id": str(args.blocker_id).strip() if args.blocker_id else None,
            "predicate_result": predicate_result,
            "recorded_at": now(),
        }
    )


def import_layers(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    """Import all event-layer results for one open action as one transaction."""
    try:
        value = json.loads(args.layer_results.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read layer results: {exc}") from exc
    rows = value.get("layer_results") if isinstance(value, dict) else value
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise SystemExit("Layer results must be an array or an object with a layer_results array.")
    required = {"layer", "status", "reason", "evidence_ids"}
    seen_layers: set[str] = set()
    for index, row in enumerate(rows, start=1):
        missing = sorted(key for key in required if row.get(key) in (None, "", []))
        if missing:
            raise SystemExit(f"Layer result row {index} is missing: " + ", ".join(missing))
        layer = row.get("layer")
        status = row.get("status")
        if not isinstance(layer, str) or layer not in CANONICAL_LAYERS:
            raise SystemExit(f"Layer result row {index} has an unsupported layer.")
        if layer in seen_layers:
            raise SystemExit(f"Layer result row {index} duplicates layer {layer}.")
        seen_layers.add(layer)
        if not isinstance(status, str) or status not in LAYER_RESULT_STATUSES:
            raise SystemExit(f"Layer result row {index} has an unsupported status.")
        if not isinstance(row.get("reason"), str) or not row["reason"].strip():
            raise SystemExit(f"Layer result row {index} reason must be a non-empty string.")
        evidence_ids = row.get("evidence_ids")
        if not isinstance(evidence_ids, list) or any(
            not isinstance(value, str) or not value.strip() for value in evidence_ids
        ):
            raise SystemExit(f"Layer result row {index} evidence_ids must be a string array.")
        if len(set(evidence_ids)) != len(evidence_ids):
            raise SystemExit(f"Layer result row {index} evidence_ids contain duplicates.")
        predicate_result = row.get("predicate_result")
        if predicate_result not in (None, True, False, "true", "false"):
            raise SystemExit(
                f"Layer result row {index} predicate_result must be boolean or omitted."
            )
    staged = deepcopy(ledger)
    for row in rows:
        evidence_ids = row["evidence_ids"]
        predicate_result = row.get("predicate_result")
        if isinstance(predicate_result, bool):
            predicate_result = "true" if predicate_result else "false"
        record_layer(
            staged,
            argparse.Namespace(
                action_id=args.action_id,
                layer=row["layer"],
                status=row["status"],
                reason=row["reason"],
                evidence_id=evidence_ids,
                semantic_ambiguity=row.get("semantic_ambiguity"),
                blocker_id=row.get("blocker_id"),
                predicate_result=predicate_result,
            ),
        )
    ledger.clear()
    ledger.update(staged)


def settle_action(ledger: dict[str, Any], args: argparse.Namespace) -> None:
    action = find_unique(ledger.get("actions", []), "action_id", args.action_id)
    if action.get("state") != "OPEN":
        raise SystemExit(f"Action is already settled: {args.action_id}")
    settlement = runtime_check_by_id(ledger, args.settlement_check_id)
    if settlement.get("voided") is True:
        raise SystemExit("A voided runtime check cannot settle an action.")
    if settlement.get("phase") not in {"after_action", "interrupted_action"}:
        raise SystemExit("settle-action requires an after_action or interrupted_action check.")
    if settlement.get("action_id") != args.action_id or settlement.get("case_id") != action.get(
        "case_id"
    ):
        raise SystemExit("The settlement check is bound to another action or case.")
    if settlement.get("consumed") is True:
        raise SystemExit("The settlement check has already been consumed.")
    if settlement.get("connection_epoch") != action.get("connection_epoch"):
        raise SystemExit("The settlement check belongs to another connection epoch.")
    completion_signal = str(args.completion_signal).strip()
    if not completion_signal:
        raise SystemExit("A safe independent --completion-signal is required.")
    preview_connected_after = settlement.get("preview_connected") is True
    stream_settled = settlement.get("stream_quiet") is True
    interrupted = settlement.get("phase") == "interrupted_action"
    if interrupted and args.settlement_reason != settlement.get("failure_reason"):
        raise SystemExit("Interrupted settlement reason must equal the captured failure_reason.")
    if interrupted and args.interaction_outcome != "uncertain":
        raise SystemExit("An interrupted action must settle with interaction_outcome=uncertain.")
    if not interrupted and args.settlement_reason in INTERRUPTION_REASONS:
        raise SystemExit(
            "Runtime interruption reasons require an interrupted_action capture and "
            "interrupt-action."
        )
    if not stream_settled and args.settlement_reason in {
        "expected_and_quiet",
        "quiet_without_expected",
    }:
        raise SystemExit("An unsettled stream cannot use a quiet settlement reason.")
    if not interrupted and not preview_connected_after:
        raise SystemExit("A disconnected Preview session requires an interrupted_action capture.")
    if (
        ledger.get("operator_contract_version") == 2
        and args.interaction_outcome == "failed"
        and args.settlement_reason != "interaction_failed"
    ):
        raise SystemExit(
            "A failed website interaction requires settlement_reason=interaction_failed."
        )
    recorded_pushes = sum(
        row.get("action_id") == args.action_id
        for row in ledger.get("business_pushes", [])
        if isinstance(row, dict)
    )
    observed_business_push_count = settlement.get("observed_business_push_count")
    if recorded_pushes != observed_business_push_count:
        raise SystemExit(
            "Record and classify every observed business push before settlement; "
            f"ledger has {recorded_pushes}, action window has "
            f"{observed_business_push_count}."
        )
    first_event_after = settlement.get("first_event_after")
    settled_final_event = settlement.get("preview_event_cursor")
    network_request_cursor_after = settlement.get("network_request_cursor")
    datalayer_call_index_after = settlement.get("datalayer_call_cursor")
    if first_event_after is not None and first_event_after <= action.get("last_event_before", -1):
        raise SystemExit("first_event_after must follow last_event_before.")
    if settled_final_event < action.get("last_event_before", -1):
        raise SystemExit("settled_final_event cannot precede last_event_before.")
    if network_request_cursor_after < action.get("network_request_cursor_before", -1):
        raise SystemExit("Network request cursor cannot move backwards within an action.")
    if ledger.get("operator_contract_version") == 2 and datalayer_call_index_after < action.get(
        "datalayer_call_index_before", -1
    ):
        raise SystemExit("dataLayer cursor cannot move backwards within an action.")
    action.update(
        {
            "settlement_check_id": settlement.get("check_id"),
            "settlement_evidence_ids": list(settlement.get("evidence_ids", [])),
            "first_event_after": first_event_after,
            "settled_final_event": settled_final_event,
            "network_request_cursor_after": network_request_cursor_after,
            "expected_seen": args.expected_seen == "true",
            "preview_connected_after": preview_connected_after,
            "interaction_outcome": args.interaction_outcome,
            "completion_signal": completion_signal,
            "stream_settled": stream_settled,
            "settlement_reason": args.settlement_reason,
            "observed_business_push_count": observed_business_push_count,
            "settled_at": now(),
            "state": "SETTLED",
        }
    )
    if ledger.get("operator_contract_version") == 2:
        action.update(
            {
                "datalayer_call_index_after": datalayer_call_index_after,
                "page_health_after": deepcopy(settlement.get("page_health")),
            }
        )
    settlement["consumed"] = True
    settlement["consumed_by_action_id"] = args.action_id
    accepted_outcomes = (
        {"completed", "failed"} if ledger.get("operator_contract_version") == 2 else {"completed"}
    )
    if args.interaction_outcome in accepted_outcomes and preview_connected_after and stream_settled:
        case = find_unique(
            ledger.get("cases", []),
            "case_id",
            str(action.get("case_id")),
        )
        case["execution_status"] = "EXECUTED"
        case["final_action_id"] = args.action_id
        case.pop("required_retest_of_action_id", None)
    if interrupted and args.settlement_reason == "preview_disconnected":
        ledger["connection_epoch"] = (
            action.get("connection_epoch", ledger.get("connection_epoch", 1)) + 1
        )


def init_command(args: argparse.Namespace) -> None:
    timestamp = now()
    contract_version = int(getattr(args, "operator_contract_version", 2))
    run_id = str(getattr(args, "run_id", "") or "").strip()
    browser_instance_id = str(getattr(args, "browser_instance_id", "") or "").strip()
    browser_context_id = str(getattr(args, "browser_context_id", "") or "").strip()
    if contract_version == 2 and not run_id:
        raise SystemExit(
            "Operator-contract-v2 init requires --run-id copied from normalized run.run_id."
        )
    if contract_version == 2 and (not browser_instance_id or not browser_context_id):
        raise SystemExit(
            "Operator-contract-v2 init requires --browser-instance-id and "
            "--browser-context-id for the already approved browser session."
        )
    ledger = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "operator_contract_version": contract_version,
        "created_at": timestamp,
        "updated_at": timestamp,
        "profile_path": args.profile_path,
        "connection_epoch": 1,
        "approved_origins": sorted({origin(item) for item in args.approved_origin}),
        "surfaces": {},
        "runtime_checks": [],
        "event_closures": [],
        "closure_history": [],
        "operator_state": {
            "status": "ACTIVE",
            "current_event_group_id": None,
        },
        "authorizations": [],
        "cases": [],
        "actions": [],
        "business_pushes": [],
        "checkpoints": [],
    }
    if run_id:
        ledger["run_id"] = run_id
    if contract_version == 2:
        ledger.update(
            {
                "browser_binding": {
                    "browser_instance_id": browser_instance_id,
                    "browser_context_id": browser_context_id,
                    "profile_path": args.profile_path,
                    "approved_existing_session": True,
                    "registered_at": timestamp,
                },
                "coverage_decisions": [],
                "stream_contract": {
                    "status": "OPEN",
                    "started_at": timestamp,
                    "start_preview_event_index": 0,
                    "start_datalayer_call_index": 0,
                    "reviewed_through_preview_event_index": 0,
                    "reviewed_through_datalayer_call_index": 0,
                },
                "stream_segments": [],
                "journey_states": [],
                "semantic_checks": [],
                "protected_handoffs": [],
                "gated_flows": [],
                "evidence_integrity": {"version": 2, "status": "PENDING"},
            }
        )
    save(
        args.ledger,
        ledger,
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
    if args.workspace:
        surface["workspace"] = args.workspace
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
    "record-runtime-check": record_runtime_check,
    "void-runtime-check": void_runtime_check,
    "authorize": authorize,
    "register-case": register_case,
    "register-tag": register_tag,
    "complete-tag-inventory": complete_tag_inventory,
    "close-case": close_case,
    "begin-action": begin_action,
    "record-push": record_push,
    "import-pushes": import_pushes,
    "import-cases": import_cases,
    "import-coverage": import_coverage,
    "import-stream": import_stream,
    "import-semantic": import_semantic,
    "import-protected-handoffs": import_protected_handoffs,
    "import-gated-flows": import_gated_flows,
    "verify-evidence": verify_evidence,
    "record-layer": record_layer,
    "import-layers": import_layers,
    "import-tag-results": import_tag_results,
    "revise-tag-inventory": revise_tag_inventory,
    "settle-action": settle_action,
    "checkpoint": checkpoint,
}


def main() -> int:
    args = parse_args()
    if args.command == "init":
        init_command(args)
        print(f"Created {args.ledger.resolve()}")
        return 0

    if args.command == "validate" and args.results is not None:
        recover_file_pair(args.results, args.ledger)
    ledger = load(args.ledger)
    if ledger.get("schema_version") != SESSION_SCHEMA_VERSION:
        raise SystemExit("Unsupported session ledger. Recreate it with the current init command.")
    if args.command == "validate":
        validate_command(ledger, args)
        return 0
    if args.command == "status":
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
        return 0
    if args.command == "scaffold-tag-results":
        scaffold_tag_results(ledger, args)
        return 0

    MUTATING_COMMANDS[args.command](ledger, args)
    ledger["updated_at"] = now()
    save(args.ledger, ledger)
    print(f"Updated {args.ledger.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
