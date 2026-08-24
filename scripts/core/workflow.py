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
from .constants import OPERATION_COUNTERS, utc_now
from .correlate import action_windows, build_model
from .coverage import event_by_id
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

_COLLECTOR_PATH = Path(__file__).resolve().parents[1] / "tag_assistant_collector.js"


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


_CONSENT_CONTEXTS = {"ORDINARY_GRANTED", "EXPLICIT_VARIANT", "NOT_APPLICABLE"}


def _normalize_setup_boundary(
    value: Any, *, required: bool, preview_required: bool = True
) -> dict[str, Any] | None:
    """Validate the prepared browser/Preview boundary without treating it as evidence."""
    if value is None:
        if required:
            raise StateError(
                "The first or fresh-context next call needs setup_boundary after the user "
                "has prepared the site, GTM Preview, and ordinary consent."
            )
        return None
    if not isinstance(value, dict):
        raise StateError("setup_boundary must be a JSON object.")
    cursor = value.get("preview_cursor")
    if not isinstance(cursor, dict):
        raise StateError("setup_boundary.preview_cursor is required.")
    epoch = str(cursor.get("epoch") or "").strip()
    if not epoch and preview_required:
        raise StateError("setup_boundary.preview_cursor.epoch is required.")
    try:
        index = int(cursor.get("index"))
    except (TypeError, ValueError) as error:
        raise StateError(
            "setup_boundary.preview_cursor.index must be a non-negative integer."
        ) from error
    if index < 0:
        raise StateError("setup_boundary.preview_cursor.index must be a non-negative integer.")
    consent_context = str(value.get("consent_context") or "").upper()
    if consent_context not in _CONSENT_CONTEXTS:
        raise StateError(
            "setup_boundary.consent_context must be ORDINARY_GRANTED, "
            "EXPLICIT_VARIANT, or NOT_APPLICABLE."
        )
    binding = value.get("binding")
    if binding is not None and not isinstance(binding, dict):
        raise StateError("setup_boundary.binding must be an object when supplied.")
    safe_binding = (
        {
            key: binding[key]
            for key in (
                "browser_family",
                "browser_context_id",
                "tab_id",
                "document_id",
                "frame_id",
                "origin",
                "preview_session_id",
                "preview_epoch",
                "natural_container_ids",
                "active_container_ids",
                "override_container_ids",
                "workspace_version",
            )
            if key in binding
        }
        if isinstance(binding, dict)
        else None
    )
    return {
        "preview_cursor": {
            "epoch": epoch or None,
            "index": index,
            **(
                {"preview_session_id": str(cursor.get("preview_session_id"))}
                if cursor.get("preview_session_id")
                else {}
            ),
        },
        "consent_context": consent_context,
        **({"binding": safe_binding} if isinstance(safe_binding, dict) else {}),
    }


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


def _latest_capture_summary(records: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    return next(
        (
            record.get("data", {}).get("summary")
            for record in reversed(records)
            if record.get("kind") == kind
            and isinstance(record.get("data", {}).get("summary"), dict)
        ),
        None,
    )


def _validate_runtime_contract(
    plan: dict[str, Any], capability: dict[str, Any] | None, *, fresh_context: bool
) -> None:
    if not isinstance(capability, dict):
        raise StateError("No verified browser runtime capability is available.")
    runtime = capability.get("runtime")
    if not isinstance(runtime, dict):
        raise StateError("Browser capability has no verified runtime self-check.")
    scope = plan.get("scope", {})
    expected_provider = str(scope.get("browser_runtime") or "playwright_mcp")
    observed_provider = str(runtime.get("provider") or "")
    if observed_provider != expected_provider:
        raise StateError(
            f"Run requires {expected_provider}, but the verified runtime is {observed_provider or 'unknown'}."
        )
    expected_channel = str(scope.get("browser_channel") or "")
    observed_channel = str(runtime.get("browser_channel") or "")
    if expected_channel and observed_channel.casefold() != expected_channel.casefold():
        raise StateError(
            f"Run requires browser channel {expected_channel}, not {observed_channel or 'unknown'}."
        )
    expected_profile = str(scope.get("browser_profile_mode") or "persistent").casefold()
    observed_profile = str(runtime.get("profile_mode") or "").casefold()
    if fresh_context and observed_profile != "isolated":
        raise StateError("A fresh-context action requires a verified isolated profile.")
    if not fresh_context and observed_profile != expected_profile:
        raise StateError(
            f"Run requires profile mode {expected_profile}; observed {observed_profile or 'unknown'}."
        )
    if bool(runtime.get("headed")) != bool(scope.get("browser_headed", True)):
        raise StateError("Browser headed/headless mode differs from the approved run scope.")


def _operations(value: dict[str, Any] | None) -> dict[str, int] | None:
    if not isinstance(value, dict) or not isinstance(value.get("operations"), dict):
        return None
    observed = value["operations"]
    if not {"navigations", "reloads"}.issubset(observed):
        return None
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in observed.values()):
        return None
    return {key: int(observed.get(key, 0)) for key in OPERATION_COUNTERS}


def _latest_operations(records: list[dict[str, Any]]) -> dict[str, int] | None:
    return _operations(_latest_capture_summary(records, "CAPTURE_HEALTH"))


def _normalize_retest_basis(
    records: list[dict[str, Any]], value: dict[str, Any] | None
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise StateError("Retest basis must be a structured object.")
    kind = str(value.get("type") or "").upper()
    if kind not in {"EVIDENCE_DEFECT", "USER_REQUEST"}:
        raise StateError("Retest basis type must be EVIDENCE_DEFECT or USER_REQUEST.")
    reason = " ".join(str(value.get("reason") or "").split())
    if not reason:
        raise StateError("Retest basis needs a concise reason.")
    normalized = {**value, "type": kind, "reason": reason}
    if kind == "EVIDENCE_DEFECT":
        record_id = str(value.get("record_id") or "")
        known = stream_record_by_id(records)
        if record_id not in known:
            raise StateError("Evidence-defect retest basis references an unknown stream record.")
        referenced = known[record_id]
        referenced_kind = str(referenced.get("kind") or "")
        action_id = str(referenced.get("data", {}).get("action_id") or "")
        if not action_id and referenced_kind.startswith("CAPTURE_"):
            action_id = next(
                (
                    str(record.get("data", {}).get("action_id") or "")
                    for record in records
                    if record.get("kind") == "ACTION_COMMIT"
                    and record_id in record.get("data", {}).get("capture_record_ids", [])
                ),
                "",
            )
        if referenced_kind not in {
            "ACTION_BEGIN",
            "ACTION_COMMIT",
        } and not referenced_kind.startswith("CAPTURE_"):
            raise StateError(
                "Evidence-defect retests must reference the affected action or machine capture, "
                "not a feedback/report record."
            )
        if not action_id:
            raise StateError("The evidence-defect record is not attributable to an action.")
        normalized.update(
            {
                "record_id": record_id,
                "supersedes_action_id": action_id,
                "scope": "action",
            }
        )
    elif not str(value.get("authorization") or "").strip():
        raise StateError("User-request retest basis needs the explicit authorization text.")
    return normalized


def _normalize_action_contract(
    events: list[dict[str, Any]],
    *,
    mode: str | None,
    document_policy: str | None,
    retest_basis: dict[str, Any] | None,
) -> tuple[str, str]:
    normalized_mode = str(mode or "").upper()
    if not normalized_mode:
        page_load = all(
            event.get("mode") == "state_only"
            or str(event.get("event_name") or "") in {"", "page_view"}
            for event in events
        )
        normalized_mode = "NAVIGATE_ONCE" if page_load else "INTERACT_ONCE"
    if normalized_mode not in {"OBSERVE_CURRENT", "NAVIGATE_ONCE", "INTERACT_ONCE"}:
        raise StateError("Action mode must be OBSERVE_CURRENT, NAVIGATE_ONCE, or INTERACT_ONCE.")
    normalized_policy = str(document_policy or "").upper()
    if not normalized_policy:
        normalized_policy = (
            "FORBIDDEN" if normalized_mode == "OBSERVE_CURRENT" else "NATURAL_ALLOWED"
        )
    if normalized_policy not in {"FORBIDDEN", "NATURAL_ALLOWED", "ONE_RELOAD_AUTHORIZED"}:
        raise StateError(
            "Document policy must be FORBIDDEN, NATURAL_ALLOWED, or ONE_RELOAD_AUTHORIZED."
        )
    if normalized_policy == "ONE_RELOAD_AUTHORIZED" and retest_basis is None:
        raise StateError("One explicit reload requires a validated retest basis.")
    return normalized_mode, normalized_policy


def _capture_spec(events: list[dict[str, Any]], preview_boundary: dict[str, Any]) -> dict[str, Any]:
    source_names = list(
        dict.fromkeys(
            str(event.get("source_event_name"))
            for event in events
            if event.get("source_event_name")
        )
    )
    delivery_names = list(
        dict.fromkeys(
            str(event.get("delivery_event_name"))
            for event in events
            if event.get("delivery_event_name")
        )
    )
    field_rows: dict[str, dict[str, Any]] = {}
    preview_checks: list[str] = []
    tag_ids: list[str] = []
    tag_scope: list[str] = []
    destinations: list[str] = []
    protocols: list[str] = []
    source_paths: list[str] = []
    requires_api_call = False
    for event in events:
        for tag in event.get("tags", []):
            if not isinstance(tag, dict):
                continue
            if tag.get("tag_id"):
                tag_ids.append(str(tag["tag_id"]))
            if tag.get("category"):
                tag_scope.append(str(tag["category"]))
            if tag.get("destination"):
                destinations.append(str(tag["destination"]))
        for claim in event.get("claims", []):
            if not isinstance(claim, dict):
                continue
            target = claim.get("target", {}) if isinstance(claim.get("target"), dict) else {}
            check = str(target.get("check") or "")
            path = str(target.get("path") or "")
            if check:
                preview_checks.append(check)
            for value in target.get("tag_scope", []):
                if value:
                    tag_scope.append(str(value))
            if target.get("tag_id"):
                tag_ids.append(str(target["tag_id"]))
            if target.get("destination"):
                destinations.append(str(target["destination"]))
            for value in target.get("destination_allowlist", []):
                if value:
                    destinations.append(str(value))
            if target.get("protocol"):
                protocols.append(str(target["protocol"]))
            if path:
                if claim.get("archetype") == "source":
                    requires_api_call = True
                    source_paths.append(path)
                row = field_rows.setdefault(
                    path,
                    {
                        "path": path,
                        "predicate": claim.get("predicate", {}),
                        "checks": [],
                    },
                )
                row["checks"].append(check or str(claim.get("archetype") or ""))
    for row in field_rows.values():
        row["checks"] = list(dict.fromkeys(value for value in row["checks"] if value))
    preview_panels = []
    if requires_api_call or any(
        value in preview_checks for value in ("event_occurrence", "event_match")
    ):
        preview_panels.append("API Call")
    if "data_layer_state" in preview_checks:
        preview_panels.append("Data Layer")
    if "resolved_variable" in preview_checks:
        preview_panels.append("Variables")
    if any(
        value in preview_checks
        for value in (
            "tag_inventory",
            "in_scope_tag_discovery",
            "tag_configuration",
            "effective_mapping",
            "tag_firing",
            "tag_consent",
            "runtime_parameter",
        )
    ):
        preview_panels.append("Tags")
    return {
        "source_anchor": {
            "mode": "event" if source_names else "state_fields",
            "event_names": source_names,
            "field_paths": list(dict.fromkeys(source_paths)),
        },
        "delivery_event_names": delivery_names,
        "planned_fields": list(field_rows.values()),
        "tag_ids": list(dict.fromkeys(tag_ids)),
        "tag_scope": list(dict.fromkeys(tag_scope)),
        "destinations": list(dict.fromkeys(destinations)),
        "protocols": list(dict.fromkeys(protocols)),
        "preview_panels": preview_panels,
        "preview_cursor": preview_boundary,
        "timeout_ms": 5000,
        "collection": {
            "bounded_passes": 1,
            "semantic_fallbacks": 1,
            "navigation_for_evidence": "FORBIDDEN",
            "reuse_static_tag_configuration": True,
            "partial_result_policy": "RETURN_BLOCKED_FEEDBACK",
        },
    }


def _action_card(
    events: list[dict[str, Any]],
    mode: str,
    document_policy: str,
    preview_boundary: dict[str, Any] | None,
) -> dict[str, Any]:
    journeys = [event.get("journey", {}) for event in events]
    normalized_boundary = preview_boundary or {
        "epoch": None,
        "index": 0,
        "instruction": "Use the new Preview connection from its first index.",
    }
    capture_spec = _capture_spec(events, normalized_boundary)
    return {
        "mode": mode,
        "document_policy": document_policy,
        "event_ids": [event["event_id"] for event in events],
        "target_urls": list(
            dict.fromkeys(
                str(journey.get("url"))
                for journey in journeys
                if isinstance(journey, dict) and journey.get("url")
            )
        ),
        "interaction": next(
            (
                str(journey.get("action"))
                for journey in journeys
                if isinstance(journey, dict) and journey.get("action")
            ),
            "Inspect the planned event once",
        ),
        "preview_cursor": normalized_boundary,
        "capture_spec": capture_spec,
        "evidence_targets": [
            "page/action reality",
            "fully expanded API Call",
            "concerned tag mapping, firing, and runtime",
            "browser request",
            "every intervening event and surrounding behavior",
        ],
        "conditional_diagnostics": [
            panel
            for panel in ("Data Layer", "Variables", "Consent")
            if panel in capture_spec["preview_panels"]
        ],
        "current_coverage": [
            {
                "event_id": event["event_id"],
                "explicit_scenarios": event.get("explicit_scenarios", []),
                "known_dimensions": event.get("known_dimensions", []),
            }
            for event in events
        ],
        "forbidden": [
            "extra reload",
            "replacement browser or tab",
            "coordinate-based interaction",
            "whole-container or historical-domain scan",
        ],
        "completion": "Capture one bounded action delta and submit it once with Preview detail.",
    }


def _playwright_completion_code(
    action_id: str,
    began_at: str,
    capture_spec: dict[str, Any],
) -> str:
    """Return one paste-ready Playwright MCP callback; no imports or local-file reads needed."""
    collector = _COLLECTOR_PATH.read_text(encoding="utf-8").strip()
    spec_json = json.dumps(capture_spec, ensure_ascii=False, separators=(",", ":"))
    action_json = json.dumps(action_id)
    began_json = json.dumps(began_at)
    return f"""async (page) => {{
  const spec = {spec_json};
  const actionId = {action_json};
  const beganAt = {began_json};
  spec.action_id = actionId;
  const collectPreview = {collector};
  const context = page.context();
  context.__gtmRecetteContextId ||= `CTX-${{Date.now().toString(36)}}-${{Math.random().toString(36).slice(2, 8)}}`;
  const pages = context.pages();
  const isPreview = (candidate) => {{
    try {{ return /(^|\\.)tagassistant\\.google\\.com$/i.test(new URL(candidate.url()).hostname); }}
    catch {{ return false; }}
  }};
  const previewPage = pages.find(isPreview);
  const targetPage = [...pages].reverse().find((candidate) => !isPreview(candidate) && !/^about:blank$/i.test(candidate.url())) || (isPreview(page) ? null : page);
  const now = new Date().toISOString();
  const priorCursor = Number(spec.preview_cursor?.index || 0);
  let preview;
  if (previewPage) {{
    preview = await previewPage.evaluate(collectPreview, spec).catch((error) => ({{
      epoch: String(spec.preview_cursor?.epoch || "preview-unavailable"),
      cursor_start: priorCursor,
      cursor_end: priorCursor,
      events: [],
      complete: false,
      event_list_complete: false,
      reason: `Tag Assistant collector failed: ${{String(error?.message || error)}}`,
      completeness: {{ event_list: false, api_call: false, fired_list: false, not_fired_set: false, tag_details: false, runtime_parameters: false }},
    }}));
  }} else {{
    preview = {{
      epoch: String(spec.preview_cursor?.epoch || "preview-unavailable"),
      cursor_start: priorCursor,
      cursor_end: priorCursor,
      events: [],
      complete: false,
      event_list_complete: false,
      reason: "Tag Assistant page was not found in this Playwright context.",
      completeness: {{ event_list: false, api_call: false, fired_list: false, not_fired_set: false, tag_details: false, runtime_parameters: false }},
    }};
  }}
  preview.action_id = actionId;
  preview.observed_at = now;

  let pageState = {{
    action_id: actionId,
    phase: "after",
    timestamp: now,
    url: targetPage?.url() || "about:blank",
    target_present: Boolean(targetPage),
    page_valid: false,
    document_id: "target-unavailable",
  }};
  let resourceRows = [];
  if (targetPage) {{
    targetPage.__gtmRecetteTabId ||= `TAB-${{Date.now().toString(36)}}-${{Math.random().toString(36).slice(2, 8)}}`;
    const observed = await targetPage.evaluate((input) => {{
      if (!globalThis.__gtmRecetteDocumentId) {{
        Object.defineProperty(globalThis, "__gtmRecetteDocumentId", {{
          value: `DOC-${{Date.now().toString(36)}}-${{Math.random().toString(36).slice(2, 8)}}`,
          configurable: false,
        }});
      }}
      const navigation = performance.getEntriesByType("navigation")[0];
      const beganMs = Date.parse(input.beganAt);
      const resources = performance.getEntriesByType("resource")
        .filter((entry) => !Number.isFinite(beganMs) || performance.timeOrigin + entry.startTime >= beganMs - 2000)
        .slice(-500)
        .map((entry, index) => ({{
          request_id: `${{input.actionId}}-PERF-${{index + 1}}`,
          action_id: input.actionId,
          timestamp: new Date(performance.timeOrigin + entry.startTime).toISOString(),
          url: entry.name,
          method: "GET",
          resource_type: entry.initiatorType || "resource",
          outcome: "observed_in_resource_timing",
          document_id: globalThis.__gtmRecetteDocumentId,
        }}));
      const bodyText = String(document.body?.innerText || "").replace(/\\s+/g, " ").slice(0, 2000);
      const soft404 = /(?:page|product|content).{{0,30}}(?:not found|introuvable)|\\b404\\b/i.test(`${{document.title}} ${{bodyText}}`);
      const activeContainerIds = [...new Set([
        ...Object.keys(globalThis.google_tag_manager || {{}}).filter((key) => /^GTM-[A-Z0-9]+$/i.test(key)),
        ...[...document.scripts].flatMap((script) => [...String(script.src || script.textContent || "").matchAll(/GTM-[A-Z0-9]+/gi)].map((match) => match[0].toUpperCase())),
      ])];
      return {{
        state: {{
          action_id: input.actionId,
          phase: "after",
          timestamp: new Date().toISOString(),
          url: location.href,
          title: document.title,
          origin: location.origin,
          ready_state: document.readyState,
          status_code: Number(navigation?.responseStatus) || null,
          soft_404: soft404,
          target_present: true,
          page_valid: !soft404 && document.readyState !== "loading",
          document_id: globalThis.__gtmRecetteDocumentId,
          container_ids: activeContainerIds,
        }},
        resources,
      }};
    }}, {{ actionId, beganAt }});
    pageState = observed.state;
    resourceRows = observed.resources;
  }}
  const targetOrigin = (() => {{ try {{ return new URL(pageState.url).origin; }} catch {{ return "unknown"; }} }})();
  const binding = {{
    action_id: actionId,
    observed_at: now,
    browser_family: "chromium",
    browser_context_id: context.__gtmRecetteContextId,
    tab_id: targetPage?.__gtmRecetteTabId || "target-unavailable",
    document_id: pageState.document_id,
    origin: targetOrigin,
    preview_session_id: preview.preview_session_id || null,
    preview_epoch: preview.epoch,
    natural_container_ids: pageState.container_ids || [],
    active_container_ids: pageState.container_ids || [],
    override_container_ids: [],
  }};
  const needsNetwork = (spec.protocols || []).length > 0 || (spec.destinations || []).length > 0;
  return {{
    binding,
    page: pageState,
    preview,
    ...(needsNetwork ? {{ network: {{
      action_id: actionId,
      complete: false,
      cursor_start: beganAt,
      cursor_end: now,
      collection_mode: "resource_timing_fallback",
      parameter_capture_complete: false,
      body_capture_complete: false,
      browser_context_id: binding.browser_context_id,
      tab_id: binding.tab_id,
      document_id: binding.document_id,
      requests: resourceRows,
    }} }} : {{}}),
  }};
}}"""


def _latest_preview_boundary(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    summary = _latest_capture_summary(records, "CAPTURE_PREVIEW")
    if not isinstance(summary, dict) or summary.get("cursor_end") is None:
        return None
    return {
        "epoch": summary.get("epoch"),
        "index": summary.get("cursor_end"),
        "preview_session_id": summary.get("preview_session_id"),
    }


def _validate_preview_delta(
    action: dict[str, Any], preview: dict[str, Any], machine: dict[str, Any]
) -> None:
    card = action.get("action_card", {})
    boundary = card.get("preview_cursor", {}) if isinstance(card, dict) else {}
    previous_epoch = str(boundary.get("epoch") or "")
    current_epoch = str(preview.get("epoch") or "")
    try:
        expected_index = int(boundary.get("index") or 0)
        observed_start = int(preview.get("cursor_start"))
    except (TypeError, ValueError) as error:
        raise StateError("Preview completion has an invalid cursor boundary.") from error
    if previous_epoch and current_epoch == previous_epoch and observed_start != expected_index:
        raise StateError(
            f"Preview delta must start after index {expected_index}, not {observed_start}."
        )
    if not previous_epoch and observed_start != 0:
        raise StateError("The first Preview connection delta must start at index 0.")
    if previous_epoch and current_epoch != previous_epoch:
        binding = machine.get("binding")
        if observed_start != 0 or not isinstance(binding, dict):
            raise StateError(
                "A new Preview epoch must start at index 0 and include the rebound identity."
            )
        if str(binding.get("preview_epoch") or "") != current_epoch:
            raise StateError("The rebound identity does not match the new Preview epoch.")
    supplied_action = str(preview.get("action_id") or "")
    if supplied_action and supplied_action != str(action.get("action_id") or ""):
        raise StateError("Preview delta belongs to another action.")


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


def _validate_after_freshness(
    bundle: dict[str, Any], action: dict[str, Any], *, continuous_since: Any = None
) -> None:
    began = parse_iso_timestamp(action.get("began_at"))
    if began is None:
        raise StateError("The action has no valid begin timestamp.")
    action_earliest = began - timedelta(seconds=2)
    continuous_boundary = parse_iso_timestamp(continuous_since) or began
    continuous_earliest = continuous_boundary - timedelta(seconds=2)
    observations = _after_observation_times(bundle)
    required_labels: set[str] = set()
    observed_labels = {label for label, value in observations if value is not None}
    missing = sorted(required_labels - observed_labels)
    if missing:
        raise StateError("After-state evidence needs current timestamps for: " + ", ".join(missing))
    for label, value in observations:
        parsed = parse_iso_timestamp(value)
        if parsed is None:
            raise StateError(f"After-state evidence has an invalid timestamp at {label}.")
        earliest = (
            action_earliest
            if label == "health" or label.startswith("page[")
            else continuous_earliest
        )
        if parsed < earliest:
            raise StateError(
                f"After-state evidence at {label} predates the action or previous "
                "continuous boundary and cannot be ingested."
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
    retest_basis: dict[str, Any] | None = None,
    mode: str | None = None,
    document_policy: str | None = None,
    deferred_binding: bool = False,
    setup_boundary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    normalized_ids = list(dict.fromkeys(str(value) for value in event_ids if str(value)))
    if not normalized_ids:
        raise StateError("begin requires at least one event_id.")
    selected_events = _event_slice(plan, normalized_ids)
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
    normalized_retest = _normalize_retest_basis(records, retest_basis)
    if normalized_retest and normalized_retest.get("type") == "EVIDENCE_DEFECT":
        superseded_id = str(normalized_retest.get("supersedes_action_id") or "")
        superseded = next(
            (action for action in prior_actions if action.get("action_id") == superseded_id),
            None,
        )
        if not isinstance(superseded, dict) or superseded.get("status") != "COMMITTED":
            raise StateError("Evidence-defect retest must reference one committed action.")
        same_events = set(map(str, superseded.get("event_ids", []))) == set(normalized_ids)
        same_scenario = str(superseded.get("scenario_id") or "ordinary") == str(
            scenario_id or "ordinary"
        )
        if not same_events or not same_scenario:
            raise StateError(
                "Evidence-defect retest must keep the superseded action's exact event slice "
                "and scenario."
            )
    if repeated and normalized_retest is None:
        raise StateError(
            "This event/scenario already has a committed action. Supply a structured "
            "retest basis or use a distinct material scenario; free text cannot authorize "
            "a clean repeat."
        )
    replay = replay_safety.upper()
    if replay not in {"SAFE_IDEMPOTENT", "SAFE_ONCE", "CONSEQUENTIAL", "PROTECTED"}:
        raise StateError("Unsupported replay-safety class.")
    normalized_mode, normalized_policy = _normalize_action_contract(
        selected_events,
        mode=mode,
        document_policy=document_policy,
        retest_basis=normalized_retest,
    )
    action_id = f"A-{uuid4().hex[:12].upper()}"
    prepared = _inject_action(bundle, action_id, "before")
    first = _first_action(records)
    begin_adapters = {"page", "datalayer", "source", "network", "lifecycle"}
    if first or normalized_retest is not None or fresh_context_required:
        begin_adapters.update({"capability", "binding", "health"})
    _validate_phase_adapters(prepared, phase="begin", allowed=begin_adapters)
    required = set() if deferred_binding else {"page"}
    if first or fresh_context_required:
        required.add("capability")
        if not deferred_binding:
            required.add("binding")
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
    capability = (
        prepared.get("capability")
        if isinstance(prepared.get("capability"), dict)
        else _latest_capture_summary(records, "CAPTURE_CAPABILITY")
    )
    _validate_runtime_contract(plan, capability, fresh_context=fresh_context_required)
    latest_binding = _latest_binding_summary(records)
    if (
        not first
        and isinstance(prepared.get("binding"), dict)
        and isinstance(latest_binding, dict)
        and _same_binding(prepared["binding"], latest_binding)
    ):
        raise StateError("The begin bundle repeats the current binding without an identity change.")
    if prepared:
        validate_bundle_value(run_dir, prepared, required_adapters=required)
    elif required:
        raise StateError("Begin bundle is missing required runtime/before-state adapters.")

    baseline_operations = _operations(prepared.get("health")) or _latest_operations(records)
    setup_binding = setup_boundary.get("binding") if isinstance(setup_boundary, dict) else None
    baseline_binding = (
        prepared.get("binding")
        if isinstance(prepared.get("binding"), dict)
        else setup_binding
        if isinstance(setup_binding, dict)
        else latest_binding
    )
    preview_boundary = (
        setup_boundary.get("preview_cursor")
        if isinstance(setup_boundary, dict)
        and isinstance(setup_boundary.get("preview_cursor"), dict)
        else _latest_preview_boundary(records)
    )
    card = _action_card(
        selected_events,
        normalized_mode,
        normalized_policy,
        preview_boundary,
    )
    began_at = utc_now()

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
            "retest_basis": normalized_retest,
            "mode": normalized_mode,
            "document_policy": normalized_policy,
            "operation_baseline": baseline_operations,
            "baseline_document_id": (
                baseline_binding.get("document_id") if isinstance(baseline_binding, dict) else None
            ),
            "setup_boundary": setup_boundary,
            "action_card": card,
            "began_at": began_at,
        },
        idempotency_key=f"action-begin:{action_id}",
    )
    captures = (
        capture_bundle_value(run_dir, prepared, source_id=f"begin:{action_id}") if prepared else []
    )
    return {
        "action": record,
        "captures": [capture["record_id"] for capture in captures],
        "action_card": card,
        "playwright_completion": {
            "tool": "browser_run_code",
            "code": _playwright_completion_code(
                action_id,
                began_at,
                card["capture_spec"],
            ),
            "instruction": (
                "After the single planned interaction, run this callback once and pass its "
                "returned object directly to complete. Do not normalize panels manually."
            ),
        },
        "instruction": (
            "Perform only the action card once. Do not reload for evidence cleanup; "
            "submit one bounded completion bundle."
        ),
    }


def next_action(
    run_dir: Path | str,
    bundle: dict[str, Any] | None = None,
    *,
    event_ids: list[str] | None = None,
    scenario_id: str = "ordinary",
    scenario_label: str | None = None,
    scenario_values: dict[str, Any] | None = None,
    label: str | None = None,
    replay_safety: str = "SAFE_IDEMPOTENT",
    fresh_context_required: bool = False,
    retest_basis: dict[str, Any] | None = None,
    mode: str | None = None,
    document_policy: str | None = None,
) -> dict[str, Any]:
    """Open the next action with only the runtime evidence needed before interaction."""
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    incoming = dict(bundle or {})
    runtime_refresh = _first_action(records) or fresh_context_required
    incoming_capability = incoming.get("capability", {})
    incoming_surfaces = (
        incoming_capability.get("surfaces", {})
        if isinstance(incoming_capability, dict)
        and isinstance(incoming_capability.get("surfaces", {}), dict)
        else {}
    )
    preview_required = not (
        isinstance(incoming_capability, dict) and incoming_surfaces.get("preview_events") is False
    )
    setup_boundary = _normalize_setup_boundary(
        incoming.pop("setup_boundary", None),
        required=runtime_refresh,
        preview_required=preview_required,
    )
    allowed = {"capability", "health"} if runtime_refresh else set()
    unexpected = sorted(set(incoming) - allowed)
    if unexpected:
        expectation = (
            "only the capability probe and optional health telemetry before the target load"
            if runtime_refresh
            else "no evidence; reuse the prior completion baseline"
        )
        raise StateError(
            "next accepts " + expectation + ". Unexpected adapters: " + ", ".join(unexpected)
        )
    selected = list(event_ids or [])
    if not selected:
        committed = {
            str(event_id)
            for action in action_windows(records)
            if action.get("status") == "COMMITTED"
            and str(action.get("scenario_id") or "ordinary") == str(scenario_id or "ordinary")
            for event_id in action.get("event_ids", [])
        }
        selected = [
            str(event["event_id"])
            for event in plan.get("events", [])
            if event.get("executable") is True and str(event["event_id"]) not in committed
        ][:1]
        if not selected and str(scenario_id or "ordinary") == "ordinary":
            committed_pairs = {
                (str(event_id), str(action.get("scenario_id") or "ordinary"))
                for action in action_windows(records)
                if action.get("status") == "COMMITTED"
                for event_id in action.get("event_ids", [])
            }
            pending_explicit = next(
                (
                    (event, scenario)
                    for event in plan.get("events", [])
                    if event.get("executable") is True
                    for scenario in event.get("explicit_scenarios", [])
                    if (
                        str(event["event_id"]),
                        str(scenario.get("scenario_id") or "ordinary"),
                    )
                    not in committed_pairs
                ),
                None,
            )
            if pending_explicit is not None:
                event, scenario = pending_explicit
                selected = [str(event["event_id"])]
                scenario_id = str(scenario.get("scenario_id") or "ordinary")
                scenario_label = str(scenario.get("label") or scenario_id)
                scenario_values = (
                    scenario.get("values", {}) if isinstance(scenario.get("values"), dict) else {}
                )
    if not selected:
        raise StateError(
            "No untested executable event remains for this scenario; select a distinct "
            "material scenario or provide a structured retest basis."
        )
    return begin_action(
        run_dir,
        selected,
        incoming,
        scenario_id=scenario_id,
        scenario_label=scenario_label,
        scenario_values=scenario_values,
        label=label,
        replay_safety=replay_safety,
        fresh_context_required=fresh_context_required,
        retest_basis=retest_basis,
        mode=mode,
        document_policy=document_policy,
        deferred_binding=True,
        setup_boundary=setup_boundary,
    )


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
    event_id = str(value.get("event_id") or "")
    event_by_id(plan, event_id)
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
    coverage = _coverage_rows(control.get("coverage"))
    for row in coverage:
        event_by_id(plan, str(row.get("event_id") or ""))
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


def _execution_violations(
    action: dict[str, Any], prepared: dict[str, Any]
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    baseline = action.get("operation_baseline")
    after = _operations(prepared.get("health"))
    deltas = (
        {key: after[key] - int(baseline.get(key, 0)) for key in OPERATION_COUNTERS}
        if isinstance(baseline, dict) and after is not None
        else {}
    )
    violations: list[dict[str, Any]] = []
    regressed = {key: value for key, value in deltas.items() if value < 0}
    if regressed:
        violations.append(
            {
                "code": "execution.counter_regression",
                "reason": "One or more cumulative browser counters moved backwards.",
                "observed": regressed,
                "expected": "Monotonic counters",
            }
        )
    mode = str(action.get("mode") or "INTERACT_ONCE")
    policy = str(action.get("document_policy") or "NATURAL_ALLOWED")
    navigation_limit = 0 if mode == "OBSERVE_CURRENT" else 1
    reload_limit = 1 if policy == "ONE_RELOAD_AUTHORIZED" else 0
    reset_limit = 1 if action.get("fresh_context_required") is True else 0
    limits = {
        "navigations": navigation_limit,
        "reloads": reload_limit,
        "resets": reset_limit,
        "full_preflights": 0,
        "preview_summary_reads": 1,
        "preview_retries": 1,
    }
    for key, limit in limits.items():
        if key in deltas and deltas[key] > limit:
            violations.append(
                {
                    "code": f"execution.{key}_exceeded",
                    "reason": f"The action used {deltas[key]} {key}; its action card allows {limit}.",
                    "observed": deltas[key],
                    "expected": {"maximum": limit},
                }
            )

    page = prepared.get("page")
    states = page.get("states", []) if isinstance(page, dict) else []
    after_documents = {
        str(row.get("document_id"))
        for row in states
        if isinstance(row, dict) and row.get("phase", "after") == "after" and row.get("document_id")
    }
    baseline_document = str(action.get("baseline_document_id") or "")
    if (
        policy == "FORBIDDEN"
        and baseline_document
        and any(document != baseline_document for document in after_documents)
    ):
        violations.append(
            {
                "code": "execution.document_change_forbidden",
                "reason": "The document changed during an observe-current action.",
                "observed": sorted(after_documents),
                "expected": baseline_document,
            }
        )
    changed_documents = {
        document
        for document in after_documents
        if baseline_document and document != baseline_document
    }
    if changed_documents:
        binding = prepared.get("binding")
        rebound_document = (
            str(binding.get("document_id") or "") if isinstance(binding, dict) else ""
        )
        if len(changed_documents) != 1 or rebound_document not in changed_documents:
            violations.append(
                {
                    "code": "execution.document_rebind_missing",
                    "reason": "A new post-action document was not rebound exactly once.",
                    "observed": sorted(changed_documents),
                    "expected": "One matching after-action binding",
                }
            )
    return deltas, violations


def commit_action(
    run_dir: Path | str,
    bundle: dict[str, Any],
    *,
    action_id: str | None = None,
    outcome_may_have_occurred: bool | None = None,
) -> dict[str, Any]:
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
    existing_commit = (
        next(
            record
            for record in reversed(records)
            if record.get("kind") == "ACTION_COMMIT"
            and record.get("data", {}).get("action_id") == action["action_id"]
        )
        if resuming
        else None
    )
    original_capture_ids = set(
        existing_commit.get("data", {}).get("capture_record_ids", [])
        if existing_commit is not None
        else []
    )
    original_binding_captured = any(
        record.get("record_id") in original_capture_ids and record.get("kind") == "CAPTURE_BINDING"
        for record in records
    )
    machine_bundle, control = _split_bundle(bundle)
    prepared = _inject_action(machine_bundle, action["action_id"], "after")
    _validate_phase_adapters(
        prepared,
        phase="commit",
        allowed={"binding", "health", "page", "datalayer", "source", "network", "lifecycle"},
    )
    latest_binding = _latest_binding_summary(records)
    if prepared:
        validate_bundle_value(run_dir, prepared)
    began = parse_iso_timestamp(action.get("began_at"))
    prior_boundaries = [
        candidate.get("committed_at")
        for candidate in actions
        if candidate.get("action_id") != action.get("action_id")
        and candidate.get("status") == "COMMITTED"
        and parse_iso_timestamp(candidate.get("committed_at")) is not None
        and began is not None
        and parse_iso_timestamp(candidate.get("committed_at")) <= began
    ]
    continuous_since = max(
        prior_boundaries,
        key=lambda value: parse_iso_timestamp(value),
        default=action.get("began_at"),
    )
    _validate_after_freshness(prepared, action, continuous_since=continuous_since)
    if (
        (not resuming or not original_binding_captured)
        and isinstance(prepared.get("binding"), dict)
        and isinstance(latest_binding, dict)
        and _same_binding(prepared["binding"], latest_binding)
    ):
        prepared.pop("binding")
    operation_deltas, execution_violations = _execution_violations(action, prepared)
    control = _normalized_controls(run_dir, control, action["action_id"])
    outcome = (
        control.get("outcome_may_have_occurred")
        if outcome_may_have_occurred is None
        else outcome_may_have_occurred
    )
    bundle_digest = content_digest(
        {"machine": prepared, "control": control, "outcome_may_have_occurred": outcome}
    )
    if (
        resuming
        and existing_commit is not None
        and existing_commit.get("data", {}).get("bundle_digest") not in {None, bundle_digest}
    ):
        raise StateError("The committed action can only be resumed with its exact original bundle.")
    captures = (
        capture_bundle_value(run_dir, prepared, source_id=f"commit:{action['action_id']}")
        if prepared
        else []
    )
    capture_ids = [record["record_id"] for record in captures]
    if resuming:
        assert existing_commit is not None
        commit = existing_commit
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
                "operation_deltas": operation_deltas,
                "execution_violations": execution_violations,
                "bundle_digest": bundle_digest,
            },
            idempotency_key=f"action-commit:{action['action_id']}:{bundle_digest}",
        )
    annotation_ids = _add_control_annotations(run_dir, control, action_id=action["action_id"])
    return {
        "commit": commit,
        "captures": capture_ids,
        "annotations": annotation_ids,
        "operation_deltas": operation_deltas,
        "execution_violations": execution_violations,
    }


def _persist_event_feedback(
    run_dir: Path | str,
    event_id: str,
    result: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    from .report import compact_status_view

    output_kinds = {"EVENT_FEEDBACK_ISSUED", "PREVIEW_SYNC"}
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
        "feedback": compact_status_view(result),
    }
    record = append_derived(
        run_dir,
        "EVENT_FEEDBACK_ISSUED",
        feedback_data,
        idempotency_key=f"feedback:{event_id}:{content_digest(feedback_data)}",
    )
    return {**result, "feedback_record_id": record["record_id"]}


def issue_event_feedback(run_dir: Path | str, event_id: str) -> dict[str, Any]:
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    result = judge_event(run_dir, plan, records, event_id)
    return _persist_event_feedback(run_dir, event_id, result, records)


def sync_preview(
    run_dir: Path | str,
    bundle: dict[str, Any],
    *,
    event_ids: list[str] | None = None,
    revisit_event_ids: list[str] | None = None,
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
    normalized_revisit_ids = [
        event_id
        for event_id in dict.fromkeys(map(str, revisit_event_ids or []))
        if event_id not in normalized_ids
    ]
    feedback_ids = [*normalized_ids, *normalized_revisit_ids]
    _event_slice(plan, feedback_ids)
    output_kinds = {"EVENT_FEEDBACK_ISSUED", "PREVIEW_SYNC"}
    through_seq = max(
        (int(record.get("seq", 0)) for record in records if record.get("kind") not in output_kinds),
        default=0,
    )
    sync_data = {
        "event_ids": normalized_ids,
        "revisited_event_ids": normalized_revisit_ids,
        "through_seq": through_seq,
        "capture_record_ids": [record["record_id"] for record in captures],
    }
    sync = append_derived(
        run_dir,
        "PREVIEW_SYNC",
        sync_data,
        idempotency_key=f"preview-sync:{content_digest(sync_data)}",
    )
    model = build_model(run_dir, plan, records)
    feedback_by_id = {
        event_id: _persist_event_feedback(
            run_dir,
            event_id,
            judge_event(run_dir, plan, records, event_id, model=model),
            records,
        )
        for event_id in feedback_ids
    }
    return {
        "sync_record_id": sync["record_id"],
        "captures": [record["record_id"] for record in captures],
        "annotations": annotation_ids,
        "events": [feedback_by_id[event_id] for event_id in normalized_ids],
        "revised_events": [feedback_by_id[event_id] for event_id in normalized_revisit_ids],
    }


def _prior_events_changed_by_continuous_delta(
    actions: list[dict[str, Any]], action: dict[str, Any], bundle: dict[str, Any]
) -> list[str]:
    began = parse_iso_timestamp(action.get("began_at"))
    if began is None or not any(
        parse_iso_timestamp(value) < began
        for label, value in _after_observation_times(bundle)
        if label != "health"
        and not label.startswith("page[")
        and parse_iso_timestamp(value) is not None
    ):
        return []
    position = next(
        (index for index, row in enumerate(actions) if row.get("action_id") == action["action_id"]),
        0,
    )
    prior = next(
        (row for row in reversed(actions[:position]) if row.get("status") == "COMMITTED"),
        None,
    )
    return list(map(str, prior.get("event_ids", []))) if isinstance(prior, dict) else []


def complete_action(
    run_dir: Path | str,
    bundle: dict[str, Any],
    *,
    action_id: str | None = None,
    event_ids: list[str] | None = None,
    outcome_may_have_occurred: bool | None = None,
) -> dict[str, Any]:
    """Commit one action and synchronize its bounded Preview delta in one pass."""
    plan = load_plan(run_dir)
    records, _ = read_stream(run_dir)
    actions = action_windows(records)
    candidates = [row for row in actions if row.get("status") == "OPEN"]
    if action_id:
        candidates = [row for row in candidates if row.get("action_id") == action_id]
    if len(candidates) != 1:
        committed = [
            row
            for row in actions
            if action_id and row.get("action_id") == action_id and row.get("status") == "COMMITTED"
        ]
        if len(committed) != 1:
            raise StateError("complete requires exactly one matching open or resumable action.")
        action = committed[0]
    else:
        action = candidates[0]
    frozen_ids = list(dict.fromkeys(map(str, action.get("event_ids", []))))
    normalized_ids = list(dict.fromkeys(map(str, event_ids or frozen_ids)))
    if normalized_ids != frozen_ids:
        raise StateError(
            "complete event_ids must exactly match the frozen action card; start a distinct "
            "action for another event or scenario."
        )
    _event_slice(plan, normalized_ids)
    machine, control = _split_bundle(bundle)
    preview = machine.pop("preview", None)
    requires_preview = any(
        "preview" in claim.get("evidence", [])
        for event_id in normalized_ids
        for claim in event_by_id(plan, event_id).get("claims", [])
    )
    capability = _latest_capture_summary(records, "CAPTURE_CAPABILITY") or {}
    preview_available = capability.get("surfaces", {}).get("preview_events") is not False
    preview_missing = requires_preview and preview_available and not isinstance(preview, dict)
    preview_bundle: dict[str, Any] = {}
    if isinstance(preview, dict):
        preview_value = json.loads(json.dumps(preview))
        preview_value.setdefault("action_id", action["action_id"])
        _validate_preview_delta(action, preview_value, machine)
        preview_bundle["preview"] = preview_value
        validate_bundle_value(run_dir, preview_bundle, required_adapters={"preview"})
    revisit_ids = _prior_events_changed_by_continuous_delta(actions, action, machine)
    commit_bundle = {**machine, **control}
    committed = commit_action(
        run_dir,
        commit_bundle,
        action_id=action["action_id"],
        outcome_may_have_occurred=outcome_may_have_occurred,
    )
    synchronized = sync_preview(
        run_dir,
        preview_bundle,
        event_ids=normalized_ids,
        revisit_event_ids=revisit_ids,
    )
    return {
        "action_id": action["action_id"],
        "commit_record_id": committed["commit"]["record_id"],
        "sync_record_id": synchronized["sync_record_id"],
        "operation_deltas": committed["operation_deltas"],
        "execution_violations": committed["execution_violations"],
        "events": synchronized["events"],
        "revised_events": synchronized["revised_events"],
        "capture_warning": (
            "Preview evidence was omitted; dependent layers were reported BLOCKED."
            if preview_missing
            else None
        ),
        "instruction": (
            "Issue the returned per-event layer feedback to the user now, before "
            "opening or executing another action."
        ),
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
