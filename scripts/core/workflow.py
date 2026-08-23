"""Minimal operating surface over the canonical zero-based stream."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from value_semantics import parse_iso_timestamp

from .capture import (
    capture_bundle_value,
    validate_bundle_value,
    verify_evidence_references,
)
from .constants import utc_now
from .correlate import action_evidence, action_windows, build_model, source_event_names
from .coverage import event_by_id, validate_coverage_annotation
from .judge import judge_event, judge_run
from .state import (
    StateError,
    append_annotation,
    append_derived,
    append_user,
    content_digest,
    load_plan,
    read_stream,
    stream_record_by_id,
)


def load_json_object(path: Path | str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        value = json.loads(source.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"Cannot read JSON object {source}: {error}") from error
    if not isinstance(value, dict):
        raise StateError(f"Expected a JSON object: {source}")
    return value


def _split_bundle(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    control_keys = {
        "coverage",
        "semantic_findings",
        "handoff",
        "acquisition_context",
        "outcome_may_have_occurred",
    }
    return (
        {key: item for key, item in value.items() if key not in control_keys},
        {key: value[key] for key in control_keys if key in value},
    )


def _inject_action(bundle: dict[str, Any], action_id: str, phase: str) -> dict[str, Any]:
    """Bind action-level snapshots without rewriting occurrence attribution.

    Source, Preview, network and lifecycle rows retain their collector timestamps and
    action IDs. Assigning the current action to an unbound row here would hide the
    exact between-interaction anomalies the workflow is intended to detect.
    """
    value = json.loads(json.dumps(bundle))
    if isinstance(value.get("health"), dict):
        value["health"].setdefault("action_id", action_id)
        value["health"].setdefault("phase", phase)
    if isinstance(value.get("binding"), dict):
        value["binding"].setdefault("action_id", action_id)
    if phase == "after":
        # An empty after-delta still proves absence only when its window belongs to
        # the action. Do not rewrite individual occurrence rows or before-deltas.
        for adapter in ("datalayer", "source", "network", "lifecycle"):
            if isinstance(value.get(adapter), dict):
                value[adapter].setdefault("action_id", action_id)
    if isinstance(value.get("page"), dict):
        states = value["page"].get("states")
        if not isinstance(states, list):
            states = [value["page"]]
            value["page"] = {"states": states}
        for state in states:
            if isinstance(state, dict):
                state.setdefault("action_id", action_id)
                state.setdefault("phase", phase)
    return value


def _validate_phase_adapters(bundle: dict[str, Any], *, phase: str, allowed: set[str]) -> None:
    unexpected = sorted(set(bundle) - allowed)
    if unexpected:
        raise StateError(
            f"{phase} bundle contains adapters that belong to another workflow phase: "
            + ", ".join(unexpected)
        )


def _latest_binding_summary(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next(
        (
            record.get("data", {}).get("summary")
            for record in reversed(records)
            if record.get("kind") == "CAPTURE_BINDING"
            and isinstance(record.get("data", {}).get("summary"), dict)
        ),
        None,
    )


def _same_binding(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = (
        "browser_context_id",
        "tab_id",
        "document_id",
        "preview_session_id",
        "preview_epoch",
        "origin",
        "workspace_version",
        "natural_container_ids",
        "active_container_ids",
        "override_container_ids",
    )
    return all(str(left.get(key) or "") == str(right.get(key) or "") for key in keys)


def _after_observation_times(bundle: dict[str, Any]) -> list[tuple[str, Any]]:
    output: list[tuple[str, Any]] = []
    health = bundle.get("health")
    if isinstance(health, dict):
        output.append(("health", health.get("observed_at", health.get("timestamp"))))
    page = bundle.get("page")
    if isinstance(page, dict):
        states = page.get("states") if isinstance(page.get("states"), list) else [page]
        output.extend(
            (f"page[{index}]", row.get("timestamp", row.get("observed_at")))
            for index, row in enumerate(states)
            if isinstance(row, dict)
        )
    datalayer = bundle.get("datalayer")
    if isinstance(datalayer, dict):
        output.extend(
            (f"datalayer[{index}]", row.get("timestamp"))
            for index, row in enumerate(datalayer.get("records", []))
            if isinstance(row, dict) and row.get("timestamp") is not None
        )
    source = bundle.get("source")
    if isinstance(source, dict):
        output.extend(
            (f"source[{index}]", row.get("timestamp", row.get("observed_at")))
            for index, row in enumerate(source.get("signals", []))
            if isinstance(row, dict) and row.get("timestamp", row.get("observed_at")) is not None
        )
    network = bundle.get("network")
    if isinstance(network, dict):
        output.extend(
            (f"network[{index}]", row.get("timestamp"))
            for index, row in enumerate(network.get("requests", []))
            if isinstance(row, dict) and row.get("timestamp") is not None
        )
    lifecycle = bundle.get("lifecycle")
    if isinstance(lifecycle, dict):
        for group in ("events", "errors", "consent_transitions"):
            output.extend(
                (f"lifecycle.{group}[{index}]", row.get("timestamp", row.get("observed_at")))
                for index, row in enumerate(lifecycle.get(group, []))
                if isinstance(row, dict)
                and row.get("timestamp", row.get("observed_at")) is not None
            )
    return output


def _validate_after_freshness(bundle: dict[str, Any], action: dict[str, Any]) -> None:
    began = parse_iso_timestamp(action.get("began_at"))
    if began is None:
        raise StateError("The action has no valid begin timestamp.")
    earliest = began - timedelta(seconds=2)
    observations = _after_observation_times(bundle)
    required_labels = {"health", "page[0]"}
    observed_labels = {label for label, value in observations if value is not None}
    missing = sorted(required_labels - observed_labels)
    if missing:
        raise StateError("After-state evidence needs current timestamps for: " + ", ".join(missing))
    for label, value in observations:
        parsed = parse_iso_timestamp(value)
        if parsed is None:
            raise StateError(f"After-state evidence has an invalid timestamp at {label}.")
        if parsed < earliest:
            raise StateError(
                f"After-state evidence at {label} predates the action and cannot be rebound to it."
            )


def _event_slice(plan: dict[str, Any], event_ids: list[str]) -> list[dict[str, Any]]:
    events = [event_by_id(plan, event_id) for event_id in event_ids]
    blocked = [event for event in events if not event.get("executable", False)]
    if blocked:
        details = [
            f"{event['event_id']}: {' | '.join(event.get('compile_errors', []))}"
            for event in blocked
        ]
        raise StateError("Selected event slice is not executable: " + " || ".join(details))
    return events


def _first_action(records: list[dict[str, Any]]) -> bool:
    return not any(record.get("kind") == "ACTION_BEGIN" for record in records)


def begin_action(
    run_dir: Path | str,
    event_ids: list[str],
    bundle: dict[str, Any],
    *,
    scenario_id: str = "ordinary",
    scenario_label: str | None = None,
    scenario_values: dict[str, Any] | None = None,
    label: str | None = None,
    replay_safety: str = "SAFE_IDEMPOTENT",
    fresh_context_required: bool = False,
    retest_reason: str | None = None,
) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    normalized_ids = list(dict.fromkeys(str(value) for value in event_ids if str(value)))
    if not normalized_ids:
        raise StateError("begin requires at least one event_id.")
    _event_slice(plan, normalized_ids)
    prior_actions = action_windows(records)
    open_actions = [
        action["action_id"] for action in action_windows(records) if action["status"] == "OPEN"
    ]
    if open_actions:
        raise StateError(
            "Commit the current action before beginning another: " + ", ".join(open_actions)
        )
    repeated = [
        action
        for action in prior_actions
        if action.get("status") == "COMMITTED"
        and str(action.get("scenario_id") or "ordinary") == str(scenario_id or "ordinary")
        and set(map(str, action.get("event_ids", []))) & set(normalized_ids)
    ]
    if repeated and not str(retest_reason or "").strip():
        raise StateError(
            "This event/scenario already has a committed action. Supply one explicit "
            "retest reason or use a distinct material scenario; do not create a clean repeat."
        )
    replay = replay_safety.upper()
    if replay not in {"SAFE_IDEMPOTENT", "SAFE_ONCE", "CONSEQUENTIAL", "PROTECTED"}:
        raise StateError("Unsupported replay-safety class.")
    action_id = f"A-{uuid4().hex[:12].upper()}"
    prepared = _inject_action(bundle, action_id, "before")
    first = _first_action(records)
    begin_adapters = {"page", "datalayer", "source", "network", "lifecycle"}
    if first or str(retest_reason or "").strip():
        begin_adapters.update({"capability", "binding", "health"})
    _validate_phase_adapters(prepared, phase="begin", allowed=begin_adapters)
    required = {"page"}
    if first:
        required.add("health")
        required.update({"capability", "binding"})
        if replay in {"CONSEQUENTIAL", "PROTECTED"}:
            datalayer = prepared.get("datalayer", {})
            direct = prepared.get("source", {})
            source_self_test = (
                isinstance(datalayer, dict)
                and datalayer.get("captureMode", datalayer.get("capture_mode")) == "call_time"
                and datalayer.get(
                    "installedAtDocumentStart",
                    datalayer.get("installed_at_document_start"),
                )
                is True
                and datalayer.get("complete") is True
            ) or (isinstance(direct, dict) and direct.get("complete") is True)
            if not source_self_test:
                raise StateError(
                    "The first consequential/protected action requires one complete cheap "
                    "source self-test."
                )
    latest_binding = _latest_binding_summary(records)
    if (
        not first
        and isinstance(prepared.get("binding"), dict)
        and isinstance(latest_binding, dict)
        and _same_binding(prepared["binding"], latest_binding)
    ):
        raise StateError("The begin bundle repeats the current binding without an identity change.")
    validate_bundle_value(run_dir, prepared, required_adapters=required)

    record = append_annotation(
        run_dir,
        "ACTION_BEGIN",
        {
            "action_id": action_id,
            "event_ids": normalized_ids,
            "scenario_id": str(scenario_id or "ordinary"),
            "scenario_label": scenario_label,
            "scenario_values": scenario_values or {},
            "label": label or "Browser interaction",
            "replay_safety": replay,
            "fresh_context_required": fresh_context_required,
            "retest_reason": str(retest_reason).strip() if retest_reason else None,
            "began_at": utc_now(),
        },
        idempotency_key=f"action-begin:{action_id}",
    )
    captures = capture_bundle_value(run_dir, prepared, source_id=f"begin:{action_id}")
    return {
        "action": record,
        "captures": [capture["record_id"] for capture in captures],
        "instruction": "Mark this action_id in the collector, perform the real interaction once, then commit its deltas.",
    }


def _coverage_rows(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    return (
        [value]
        if isinstance(value, dict)
        else [row for row in value if isinstance(row, dict)]
        if isinstance(value, list)
        else []
    )


def add_coverage_review(run_dir: Path | str, value: dict[str, Any]) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    errors = validate_coverage_annotation(plan, records, value)
    if errors:
        raise StateError("Coverage review is invalid: " + " | ".join(errors))
    event_id = str(value.get("event_id"))
    return append_annotation(
        run_dir,
        "COVERAGE_REVIEW",
        value,
        idempotency_key=f"coverage:{event_id}:{content_digest(value)}",
    )


def _normalized_semantic_finding(run_dir: Path | str, value: dict[str, Any]) -> dict[str, Any]:
    plan = load_plan(run_dir)
    event_id = str(value.get("event_id") or "")
    event_by_id(plan, event_id)
    status = str(value.get("status") or "REVIEW").upper()
    if status not in {"FAIL", "REVIEW"}:
        raise StateError("Semantic findings may only add FAIL or REVIEW.")
    if not str(value.get("reason") or "").strip():
        raise StateError("Semantic finding needs a concise reason.")
    records, _ = read_stream(run_dir)
    known = stream_record_by_id(records)
    references = value.get("evidence_refs", [])
    if not isinstance(references, list) or not references:
        raise StateError("Semantic finding needs at least one machine evidence reference.")
    unknown = [str(reference) for reference in references if str(reference) not in known]
    if unknown:
        raise StateError("Semantic finding references unknown evidence: " + ", ".join(unknown))
    return {**value, "event_id": event_id, "status": status}


def add_semantic_finding(run_dir: Path | str, value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalized_semantic_finding(run_dir, value)
    return append_annotation(
        run_dir,
        "SEMANTIC_FINDING",
        normalized,
        idempotency_key=f"semantic:{content_digest(normalized)}",
    )


def _normalized_acquisition_context(
    run_dir: Path | str, value: dict[str, Any], action_id: str | None
) -> dict[str, Any]:
    normalized = dict(value)
    normalized.setdefault("action_id", action_id)
    method = str(normalized.get("method") or "").upper()
    if method not in {"NATURAL", "CONTROLLED_NAVIGATION", "NOT_APPLICABLE"}:
        raise StateError(
            "Acquisition method must be NATURAL, CONTROLLED_NAVIGATION, or NOT_APPLICABLE."
        )
    if not isinstance(normalized.get("fresh"), bool):
        raise StateError("Acquisition context needs an explicit boolean fresh state.")
    if method != "NOT_APPLICABLE":
        references = normalized.get("evidence_refs", [])
        known = stream_record_by_id(read_stream(run_dir)[0])
        if not isinstance(references, list) or not references:
            raise StateError("Applicable acquisition context needs machine evidence references.")
        unknown = [str(reference) for reference in references if str(reference) not in known]
        if unknown:
            raise StateError(
                "Acquisition context references unknown evidence: " + ", ".join(unknown)
            )
    normalized["method"] = method
    return normalized


def _normalized_handoff(run_dir: Path | str, value: dict[str, Any]) -> dict[str, Any]:
    gate = str(value.get("gate") or "").upper()
    allowed = {
        "CAPTCHA",
        "CREDENTIALS",
        "MFA",
        "EMAIL_VERIFICATION",
        "SMS_VERIFICATION",
        "MAGIC_LINK",
        "PAYMENT",
        "EXTERNAL_APPROVAL",
    }
    if gate not in allowed:
        raise StateError("Protected handoff has an unsupported gate kind.")
    status = str(value.get("status") or "PENDING").upper()
    if status not in {"PENDING", "RESUMED", "ABANDONED"}:
        raise StateError("Handoff status must be PENDING, RESUMED, or ABANDONED.")
    records, _ = read_stream(run_dir)
    handoff_id = str(
        value.get("handoff_id")
        or f"H-{content_digest({'gate': gate, 'binding': value.get('binding')})[:10].upper()}"
    )
    binding = value.get("binding")
    if not isinstance(binding, dict) or not all(
        binding.get(key) for key in ("browser_context_id", "tab_id", "document_id", "action_id")
    ):
        raise StateError("Protected handoff must bind browser context, tab, document, and action.")
    if status == "RESUMED":
        prior = next(
            (
                record.get("data", {})
                for record in reversed(records)
                if record.get("kind") == "PROTECTED_HANDOFF"
                and record.get("data", {}).get("handoff_id") == handoff_id
                and record.get("data", {}).get("status") == "PENDING"
            ),
            None,
        )
        if prior is None or prior.get("binding") != binding:
            raise StateError(
                "Protected handoff did not resume the exact browser/tab/document/action lineage."
            )
    return {**value, "handoff_id": handoff_id, "gate": gate, "status": status}


def _normalized_controls(
    run_dir: Path | str, control: dict[str, Any], action_id: str | None
) -> dict[str, Any]:
    """Validate every analyst control before any part of a bundle is persisted."""
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    coverage = _coverage_rows(control.get("coverage"))
    for row in coverage:
        errors = validate_coverage_annotation(plan, records, row)
        if errors:
            raise StateError("Coverage review is invalid: " + " | ".join(errors))
    semantic = [
        _normalized_semantic_finding(run_dir, row)
        for row in _coverage_rows(control.get("semantic_findings"))
    ]
    normalized: dict[str, Any] = {**control, "coverage": coverage, "semantic_findings": semantic}
    if isinstance(control.get("handoff"), dict):
        normalized["handoff"] = _normalized_handoff(run_dir, control["handoff"])
    if isinstance(control.get("acquisition_context"), dict):
        normalized["acquisition_context"] = _normalized_acquisition_context(
            run_dir, control["acquisition_context"], action_id
        )
    return normalized


def _add_control_annotations(
    run_dir: Path | str,
    control: dict[str, Any],
    *,
    action_id: str | None = None,
) -> list[str]:
    record_ids = []
    for row in _coverage_rows(control.get("coverage")):
        record_ids.append(add_coverage_review(run_dir, row)["record_id"])
    for row in _coverage_rows(control.get("semantic_findings")):
        record_ids.append(add_semantic_finding(run_dir, row)["record_id"])
    if isinstance(control.get("handoff"), dict):
        normalized = control["handoff"]
        record_ids.append(
            append_annotation(
                run_dir,
                "PROTECTED_HANDOFF",
                normalized,
                idempotency_key=(f"handoff:{normalized['handoff_id']}:{normalized['status']}"),
            )["record_id"]
        )
    if isinstance(control.get("acquisition_context"), dict):
        value = control["acquisition_context"]
        record_ids.append(
            append_annotation(
                run_dir,
                "ACQUISITION_CONTEXT",
                value,
                idempotency_key=f"acquisition:{content_digest(value)}",
            )["record_id"]
        )
    return record_ids


def commit_action(
    run_dir: Path | str,
    bundle: dict[str, Any],
    *,
    action_id: str | None = None,
    outcome_may_have_occurred: bool | None = None,
) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    actions = action_windows(records)
    open_actions = [action for action in actions if action["status"] == "OPEN"]
    if action_id:
        open_actions = [action for action in open_actions if action["action_id"] == action_id]
    resuming = False
    if len(open_actions) == 1:
        action = open_actions[0]
    else:
        committed = [
            action
            for action in actions
            if action_id and action["action_id"] == action_id and action["status"] == "COMMITTED"
        ]
        if len(committed) != 1:
            raise StateError("commit requires exactly one matching open action.")
        action = committed[0]
        resuming = True
    machine_bundle, control = _split_bundle(bundle)
    prepared = _inject_action(machine_bundle, action["action_id"], "after")
    _validate_phase_adapters(
        prepared,
        phase="commit",
        allowed={"binding", "health", "page", "datalayer", "source", "network", "lifecycle"},
    )
    validate_bundle_value(run_dir, prepared, required_adapters={"health", "page"})
    _validate_after_freshness(prepared, action)
    latest_binding = _latest_binding_summary(records)
    if (
        isinstance(prepared.get("binding"), dict)
        and isinstance(latest_binding, dict)
        and _same_binding(prepared["binding"], latest_binding)
    ):
        raise StateError(
            "The commit bundle repeats the current binding without a navigation change."
        )
    control = _normalized_controls(run_dir, control, action["action_id"])
    captures = capture_bundle_value(run_dir, prepared, source_id=f"commit:{action['action_id']}")
    capture_ids = [record["record_id"] for record in captures]
    outcome = (
        control.get("outcome_may_have_occurred")
        if outcome_may_have_occurred is None
        else outcome_may_have_occurred
    )
    if resuming:
        commit = next(
            record
            for record in reversed(records)
            if record.get("kind") == "ACTION_COMMIT"
            and record.get("data", {}).get("action_id") == action["action_id"]
        )
        if (
            commit.get("data", {}).get("capture_record_ids") != capture_ids
            or commit.get("data", {}).get("outcome_may_have_occurred") != outcome
        ):
            raise StateError(
                "The committed action can only be resumed with its exact original bundle."
            )
    else:
        commit = append_annotation(
            run_dir,
            "ACTION_COMMIT",
            {
                "action_id": action["action_id"],
                "committed_at": utc_now(),
                "outcome_may_have_occurred": outcome,
                "capture_record_ids": capture_ids,
            },
            idempotency_key=f"action-commit:{action['action_id']}:{content_digest(prepared)}",
        )
    annotation_ids = _add_control_annotations(run_dir, control, action_id=action["action_id"])
    final_records, _ = read_stream(run_dir)
    model = build_model(run_dir, plan, final_records)
    observed = source_event_names(model, action["action_id"], authoritative_only=True)
    duplicates = sorted({name for name in observed if observed.count(name) > 1})
    expected_names = {
        str(event_by_id(plan, event_id).get("event_name"))
        for event_id in action.get("event_ids", [])
        if event_by_id(plan, event_id).get("event_name")
    }
    unexpected = [
        name for name in observed if name not in expected_names and not name.startswith("gtm.")
    ]
    current_evidence = action_evidence(model, action["action_id"])
    provisional = []
    for event_id in action.get("event_ids", []):
        event_result = judge_event(run_dir, plan, final_records, str(event_id), model=model)
        provisional.append(
            {
                "event_id": event_id,
                "status": event_result["status"],
                "layers": {
                    domain: {
                        "status": value.get("status"),
                        "reason": value.get("reason"),
                    }
                    for domain, value in event_result.get("domains", {}).items()
                },
                "operational_rows": [
                    {
                        "scenario_id": row.get("scenario_id"),
                        "target": row.get("inspection_target"),
                        "domain": row.get("domain"),
                        "status": row.get("status"),
                        "observed": row.get("observed"),
                        "expected": row.get("expected"),
                        "reason": row.get("reason"),
                        "check_next": row.get("check_next"),
                        "evidence": row.get("evidence", []),
                    }
                    for row in event_result.get("inspections", [])
                ],
            }
        )
    awaiting = []
    if any(
        row.get("layers", {}).get("gtm", {}).get("status") in {"BLOCKED", "PENDING"}
        for row in provisional
    ):
        awaiting.append("one targeted Preview detail pass")
    if any(row.get("status") == "PENDING" for row in provisional):
        awaiting.append("remaining material scenario coverage")
    pulse_data = {
        "action_id": action["action_id"],
        "event_ids": action.get("event_ids", []),
        "observed_events": observed,
        "immediate_defects": {
            "duplicates": duplicates,
            "unexpected_events": unexpected,
        },
        "observed_network_sends": len(current_evidence.get("logical_sends", [])),
        "observed_preview_messages": len(current_evidence.get("preview_events", [])),
        "provisional_events": provisional,
        "awaiting": awaiting,
    }
    pulse = append_derived(
        run_dir,
        "ACTION_PULSE",
        pulse_data,
        idempotency_key=f"pulse:{action['action_id']}:{content_digest(pulse_data)}",
    )
    return {
        "commit": commit,
        "captures": capture_ids,
        "annotations": annotation_ids,
        "pulse": {**pulse_data, "record_id": pulse["record_id"], "certifying": False},
    }


def issue_event_feedback(run_dir: Path | str, event_id: str) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    result = judge_event(run_dir, plan, records, event_id)
    output_kinds = {"ACTION_PULSE", "EVENT_FEEDBACK_ISSUED", "PREVIEW_SYNC"}
    reviewed_through = max(
        (int(record.get("seq", 0)) for record in records if record.get("kind") not in output_kinds),
        default=0,
    )
    feedback_data = {
        "event_id": event_id,
        "status": result["status"],
        "final": result["final"],
        "reviewed_through_seq": reviewed_through,
        "result_digest": content_digest(result),
    }
    record = append_derived(
        run_dir,
        "EVENT_FEEDBACK_ISSUED",
        feedback_data,
        idempotency_key=f"feedback:{event_id}:{content_digest(feedback_data)}",
    )
    return {**result, "feedback_record_id": record["record_id"]}


def sync_preview(
    run_dir: Path | str,
    bundle: dict[str, Any],
    *,
    event_ids: list[str] | None = None,
) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    machine_bundle, control = _split_bundle(bundle)
    control = _normalized_controls(run_dir, control, None)
    if machine_bundle:
        _validate_phase_adapters(machine_bundle, phase="sync-preview", allowed={"preview"})
        validate_bundle_value(run_dir, machine_bundle)
        captures = capture_bundle_value(
            run_dir, machine_bundle, source_id=f"sync:{content_digest(machine_bundle)}"
        )
    else:
        captures = []
    annotation_ids = _add_control_annotations(run_dir, control)
    records, _ = read_stream(run_dir)
    if event_ids is None:
        last_sync_seq = max(
            (
                int(record.get("data", {}).get("through_seq", 0))
                for record in records
                if record.get("kind") == "PREVIEW_SYNC"
            ),
            default=0,
        )
        event_ids = []
        for record in records:
            if record.get("kind") == "ACTION_COMMIT" and int(record.get("seq", 0)) > last_sync_seq:
                action_id = record.get("data", {}).get("action_id")
                action = next(
                    (row for row in action_windows(records) if row["action_id"] == action_id), None
                )
                if action:
                    event_ids.extend(map(str, action.get("event_ids", [])))
    normalized_ids = list(dict.fromkeys(event_ids or []))
    _event_slice(plan, normalized_ids)
    output_kinds = {"ACTION_PULSE", "EVENT_FEEDBACK_ISSUED", "PREVIEW_SYNC"}
    through_seq = max(
        (int(record.get("seq", 0)) for record in records if record.get("kind") not in output_kinds),
        default=0,
    )
    sync_data = {
        "event_ids": normalized_ids,
        "through_seq": through_seq,
        "capture_record_ids": [record["record_id"] for record in captures],
    }
    sync = append_derived(
        run_dir,
        "PREVIEW_SYNC",
        sync_data,
        idempotency_key=f"preview-sync:{content_digest(sync_data)}",
    )
    feedback = [issue_event_feedback(run_dir, event_id) for event_id in normalized_ids]
    return {
        "sync_record_id": sync["record_id"],
        "captures": [record["record_id"] for record in captures],
        "annotations": annotation_ids,
        "events": feedback,
    }


def add_handoff(run_dir: Path | str, value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalized_handoff(run_dir, value)
    return append_annotation(
        run_dir,
        "PROTECTED_HANDOFF",
        normalized,
        idempotency_key=f"handoff:{normalized['handoff_id']}:{normalized['status']}",
    )


def _pending_handoffs(records: list[dict[str, Any]]) -> list[str]:
    statuses: dict[str, str] = {}
    for record in records:
        if record.get("kind") == "PROTECTED_HANDOFF":
            statuses[str(record.get("data", {}).get("handoff_id"))] = str(
                record.get("data", {}).get("status")
            )
    return sorted(key for key, value in statuses.items() if value == "PENDING")


def _currently_finished(records: list[dict[str, Any]]) -> bool:
    finished = False
    for record in records:
        if record.get("kind") == "RUN_FINISHED":
            finished = True
        elif record.get("kind") == "RUN_REOPENED":
            finished = False
    return finished


def executable_residue(run_dir: Path | str) -> list[str]:
    root = Path(run_dir).expanduser().resolve()
    allowed = {"plan.json", "stream.ndjson"}
    executable = {".py", ".js", ".mjs", ".cjs", ".ps1", ".bat", ".cmd", ".exe"}
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file() and path.name not in allowed and path.suffix.lower() in executable
    )


def finish_run(run_dir: Path | str) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, warnings = read_stream(run_dir)
    if warnings:
        raise StateError("Recover the incomplete final stream record before finishing.")
    if any(action["status"] == "OPEN" for action in action_windows(records)):
        raise StateError("Cannot finish with an open browser action.")
    errors = verify_evidence_references(run_dir, records)
    if errors:
        raise StateError("Evidence integrity failed: " + " | ".join(errors))
    handoffs = _pending_handoffs(records)
    if handoffs:
        raise StateError("Protected handoffs remain unresolved: " + ", ".join(handoffs))
    residue = executable_residue(run_dir)
    if residue:
        raise StateError("Run-specific executable residue is forbidden: " + ", ".join(residue))
    result = judge_run(run_dir, plan, records)
    unfinished = [event["event_id"] for event in result["events"] if event.get("final") is not True]
    if unfinished:
        raise StateError(
            "Cannot finish before every event has a final confidence and coverage decision: "
            + ", ".join(unfinished)
        )
    if _currently_finished(records):
        return result
    result_core = {
        "status": result["status"],
        "events": result["events"],
        "counts": result["counts"],
    }
    record = append_derived(
        run_dir,
        "RUN_FINISHED",
        {
            "finished_at": utc_now(),
            "reviewed_through_seq": records[-1]["seq"] if records else 0,
            "result_digest": content_digest(result_core),
            "overall_status": result["status"],
        },
        idempotency_key=f"finish:{content_digest(result_core)}",
    )
    final_records, _ = read_stream(run_dir)
    return {**judge_run(run_dir, plan, final_records), "finish_record_id": record["record_id"]}


def reopen_run(run_dir: Path | str, authorization: str) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    if not any(record.get("kind") == "RUN_FINISHED" for record in records):
        raise StateError("Run is not finished; no reopen authorization is needed.")
    normalized = " ".join(str(authorization or "").split())
    if not normalized:
        raise StateError("Explicit user reopen authorization is required.")
    auth = append_user(
        run_dir,
        "REOPEN_AUTHORIZATION",
        {"run_id": plan["run_id"], "authorization": normalized, "authorized_at": utc_now()},
        idempotency_key=f"reopen-auth:{content_digest(normalized)}",
        allow_frozen_transition=True,
    )
    return append_derived(
        run_dir,
        "RUN_REOPENED",
        {
            "authorization_record_id": auth["record_id"],
            "reopened_at": utc_now(),
            "revision": 1 + sum(record.get("kind") == "RUN_REOPENED" for record in records),
        },
        idempotency_key=f"reopen:{auth['record_id']}",
        allow_frozen_transition=True,
    )
