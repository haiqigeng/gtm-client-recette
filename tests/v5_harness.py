from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.constants import OPERATION_COUNTERS, utc_now
from core.plan import initialize_run
from core.state import load_plan, read_stream
from core.workflow import (
    add_coverage_review,
    begin_action,
    commit_action,
    issue_event_feedback,
    sync_preview,
)


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def default_event(
    event_id: str = "E-view_item",
    event_name: str = "view_item",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_name": event_name,
        "url": "https://shop.example.test/product",
        "requirements": [
            {
                "requirement_id": f"{event_id}-event",
                "field_path": "event",
                "match_rule": "equals",
                "expected_value": event_name,
                "expected_type": "string",
            }
        ],
        "tags": [
            {
                "tag_id": "GA4-event",
                "tag_name": "GA4 event",
                "category": "GA4",
                "expected": "fire",
                "destination": "G-TEST123",
                "configuration": {"measurement_id": "G-TEST123"},
            }
        ],
    }


class V5Harness:
    def __init__(
        self,
        root: Path,
        *,
        events: list[dict[str, Any]] | None = None,
        scope: dict[str, Any] | None = None,
        run_id: str = "RUN-V5-TEST",
    ) -> None:
        self.root = root
        self.run = root / "run"
        self.run_id = run_id
        self.source = write_json(
            root / "tracking-plan.json", {"events": events or [default_event()]}
        )
        self.plan = initialize_run(
            self.source,
            self.run,
            run_id=run_id,
            scope={
                "approved": True,
                "origins": ["https://shop.example.test"],
                "environment": "preprod",
                "expected_container": ["GTM-EXPECTED"],
                "destination": ["G-TEST123"],
                "tag_scope": ["GA4"],
                "certify_tags": True,
                "browser_send_required": True,
                **(scope or {}),
            },
        )
        self.call_index = 1
        self.preview_index = 1
        self.request_index = 1
        self.operations = {key: 0 for key in OPERATION_COUNTERS}
        self.last_begin_result: dict[str, Any] | None = None

    def capability(self, **surface_updates: Any) -> dict[str, Any]:
        surfaces = {
            "stable_target_identity": True,
            "document_start_injection": True,
            "network_deltas": True,
            "network_post_data": True,
            "lifecycle_errors": True,
            "preview_events": True,
            "preview_tag_inventory": True,
            "preview_variables": True,
            "preview_consent": True,
            **surface_updates,
        }
        return {
            "browser_family": "chromium",
            "observed_at": utc_now(),
            "runtime": {
                "provider": "playwright_mcp",
                "mcp_version": "0.0.79",
                "browser_channel": "msedge",
                "profile_mode": "persistent",
                "headed": True,
                "self_check": "PASS",
            },
            "milestones": {
                "browser_ready_at": utc_now(),
                "preview_ready_at": utc_now(),
            },
            "surfaces": surfaces,
        }

    def binding(self, **updates: Any) -> dict[str, Any]:
        return {
            "browser_family": "chromium",
            "browser_context_id": "CTX-1",
            "tab_id": "TAB-SITE",
            "document_id": "DOC-1",
            "frame_id": "FRAME-1",
            "origin": "https://shop.example.test",
            "preview_session_id": "PREVIEW-1",
            "preview_epoch": "EPOCH-1",
            "natural_container_ids": ["GTM-EXPECTED"],
            "active_container_ids": ["GTM-EXPECTED"],
            "workspace_version": "42",
            **updates,
        }

    def _health(self, phase: str) -> dict[str, Any]:
        return {
            "observed_at": utc_now(),
            "phase": phase,
            "status": "PASS",
            "settled": True,
            "settlement_reason": "bounded_quiet_window",
            "recorder_attached": True,
            "network_active": True,
            "data_layer_cursor": self.call_index - 1,
            "preview_epoch": "EPOCH-1",
            "preview_event_index": self.preview_index - 1,
            "document_id": "DOC-1",
            "operations": dict(self.operations),
        }

    def bump_operations(self, **updates: int) -> None:
        for key, amount in updates.items():
            if key not in self.operations:
                raise KeyError(key)
            self.operations[key] += amount

    def _page(self, phase: str, **updates: Any) -> dict[str, Any]:
        return {
            "timestamp": utc_now(),
            "phase": phase,
            "url": "https://shop.example.test/product",
            "status_code": 200,
            "page_kind": "product",
            "page_valid": True,
            "soft_404": False,
            "target_present": True,
            "document_id": "DOC-1",
            "frame_id": "FRAME-1",
            "business": {"item_id": "SKU-1"},
            "completion": {"succeeded": True, "signal": "visible outcome"},
            **updates,
        }

    def begin(
        self,
        event_ids: list[str] | None = None,
        *,
        scenario_id: str = "ordinary",
        scenario_values: dict[str, Any] | None = None,
        first_bundle_updates: dict[str, Any] | None = None,
        fresh_context_required: bool = False,
        replay_safety: str = "SAFE_IDEMPOTENT",
        retest_basis: dict[str, Any] | None = None,
        mode: str | None = None,
        document_policy: str | None = None,
    ) -> str:
        records, _ = read_stream(self.run)
        bundle: dict[str, Any] = {"page": {"states": [self._page("before")]}}
        if not any(row.get("kind") == "ACTION_BEGIN" for row in records):
            bundle.update(
                {
                    "capability": self.capability(),
                    "binding": self.binding(),
                    "health": self._health("before"),
                }
            )
        bundle.update(first_bundle_updates or {})
        result = begin_action(
            self.run,
            event_ids or [self.plan["events"][0]["event_id"]],
            bundle,
            scenario_id=scenario_id,
            scenario_values=scenario_values,
            label="Test browser interaction",
            fresh_context_required=fresh_context_required,
            replay_safety=replay_safety,
            retest_basis=retest_basis,
            mode=mode,
            document_policy=document_policy,
        )
        self.last_begin_result = result
        return str(result["action"]["data"]["action_id"])

    def datalayer(
        self,
        payloads: list[Any],
        *,
        action_id: str | None,
        complete: bool = True,
        capture_mode: str = "call_time",
        document_start: bool = True,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        rows = []
        for payload in payloads:
            rows.append(
                {
                    "callIndex": self.call_index,
                    "timestamp": timestamp or utc_now(),
                    "actionId": action_id,
                    "documentId": "DOC-1",
                    "frameId": "FRAME-1",
                    "layerName": "dataLayer",
                    "arguments": [payload],
                    "gtmUniqueEventIds": [self.call_index],
                }
            )
            self.call_index += 1
        return {
            "version": 3,
            "runId": self.run_id,
            "captureMode": capture_mode,
            "installedAtDocumentStart": document_start,
            "complete": complete,
            "document_id": "DOC-1",
            "records": rows,
        }

    def network(
        self,
        event_names: list[str],
        *,
        action_id: str | None,
        payloads: list[dict[str, Any]] | None = None,
        destination: str = "G-TEST123",
        complete: bool = True,
        outcome: str = "initiated",
        duplicate_count: int = 1,
    ) -> dict[str, Any]:
        rows = []
        for event_position, event_name in enumerate(event_names):
            payload = (
                payloads[event_position]
                if payloads is not None and event_position < len(payloads)
                else {}
            )
            query: list[tuple[str, Any]] = [
                ("v", "2"),
                ("tid", destination),
                ("en", event_name),
            ]
            for key, value in payload.items():
                if key in {"event", "ecommerce"} or isinstance(value, (dict, list)):
                    continue
                if key == "currency":
                    query.append(("cu", value))
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    query.append((f"epn.{key}", value))
                else:
                    query.append((f"ep.{key}", value))
            ecommerce = payload.get("ecommerce")
            if isinstance(ecommerce, dict):
                if ecommerce.get("currency") is not None:
                    query.append(("cu", ecommerce["currency"]))
                for key, value in ecommerce.items():
                    if key in {"items", "currency"} or isinstance(value, (dict, list)):
                        continue
                    prefix = (
                        "epn"
                        if isinstance(value, (int, float)) and not isinstance(value, bool)
                        else "ep"
                    )
                    query.append((f"{prefix}.{key}", value))
                for item_index, item in enumerate(ecommerce.get("items", []), start=1):
                    if not isinstance(item, dict):
                        continue
                    segments = []
                    for source_key, wire_key in (
                        ("item_id", "id"),
                        ("item_name", "nm"),
                        ("price", "pr"),
                        ("quantity", "qt"),
                    ):
                        if item.get(source_key) is not None:
                            segments.append(f"{wire_key}{item[source_key]}")
                    query.append((f"pr{item_index}", "~".join(segments)))
            for _ in range(duplicate_count):
                rows.append(
                    {
                        "request_id": f"REQ-{self.request_index}",
                        "action_id": action_id,
                        "timestamp": utc_now(),
                        "document_id": "DOC-1",
                        "tag_ids": ["GA4-event"],
                        "method": "POST",
                        "resource_type": "beacon",
                        "url": "https://www.google-analytics.com/g/collect?" + urlencode(query),
                        "outcome": outcome,
                    }
                )
                self.request_index += 1
        return {
            "complete": complete,
            "cursor_start": self.request_index - len(rows) - 1,
            "cursor_end": self.request_index - 1,
            "browser_context_id": "CTX-1",
            "tab_id": "TAB-SITE",
            "document_id": "DOC-1",
            "parameter_capture_complete": True,
            "body_capture_complete": True,
            "requests": rows,
        }

    def preview(
        self,
        payloads: list[dict[str, Any]],
        *,
        action_id: str | None,
        complete: bool = True,
        fire_tags: bool = True,
        full_details: bool = True,
        consent: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        plan = load_plan(self.run)
        by_name = {event.get("event_name"): event for event in plan["events"]}
        events = []
        for payload in payloads:
            name = str(payload.get("event") or "")
            planned = by_name.get(name, {})
            tags = planned.get("tags", [])
            fired_tags = []
            not_fired_tags = []
            details = []
            for tag in tags:
                expected = tag.get("expected")
                fired = fire_tags and expected == "fire"
                target = fired_tags if fired else not_fired_tags
                target.append(tag["tag_id"])
                details.append(
                    {
                        "tag_id": tag["tag_id"],
                        "tag_name": tag.get("tag_name"),
                        "category": tag.get("category"),
                        "fired": fired,
                        "firing_count": 1 if fired else 0,
                        "configuration": tag.get("configuration"),
                        "runtime_parameters": payload,
                    }
                )
            events.append(
                {
                    "index": self.preview_index,
                    "epoch": "EPOCH-1",
                    "timestamp": utc_now(),
                    "action_id": action_id,
                    "event_name": name,
                    "page_url": "https://shop.example.test/product",
                    "gtm_unique_event_id": self.preview_index,
                    "bookmarked": True,
                    "history_stable": complete,
                    "full_tag_summary": full_details,
                    "completeness": {
                        "event_list": complete,
                        "api_call": full_details,
                        "data_layer_state": full_details,
                        "fired_list": full_details,
                        "not_fired_set": full_details,
                        "tag_details": full_details,
                        "variables": full_details,
                        "runtime_parameters": full_details,
                    },
                    "api_call": {
                        "arguments": [payload],
                        "complete": full_details,
                    }
                    if full_details
                    else None,
                    "data_layer_state": payload if full_details else None,
                    "resolved_state": payload if full_details else None,
                    "consent": consent,
                    "fired_tags": fired_tags,
                    "not_fired_tags": not_fired_tags,
                    "tags": details if full_details else [],
                }
            )
            self.preview_index += 1
        return {
            "complete": complete,
            "action_id": action_id,
            "epoch": "EPOCH-1",
            "preview_session_id": "PREVIEW-1",
            "container_ids": ["GTM-EXPECTED"],
            "workspace_version": "42",
            "events": events,
        }

    def commit(
        self,
        action_id: str,
        payloads: list[dict[str, Any]],
        *,
        page_updates: dict[str, Any] | None = None,
        include_source: bool = True,
        include_network: bool = True,
        network_updates: dict[str, Any] | None = None,
        lifecycle: dict[str, Any] | None = None,
        acquisition_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        bundle: dict[str, Any] = {
            "health": self._health("after"),
            "page": {"states": [self._page("after", **(page_updates or {}))]},
        }
        if include_source:
            bundle["datalayer"] = self.datalayer(payloads, action_id=action_id)
        if include_network:
            names = [str(payload.get("event")) for payload in payloads if payload.get("event")]
            network_options = dict(network_updates or {})
            bundle["network"] = self.network(
                names,
                action_id=action_id,
                payloads=payloads,
                **network_options,
            )
        if lifecycle is not None:
            bundle["lifecycle"] = lifecycle
        if acquisition_context is not None:
            bundle["acquisition_context"] = acquisition_context
        return commit_action(self.run, bundle, action_id=action_id)

    def coverage(
        self,
        event_id: str,
        action_ids: list[str],
        *,
        scenario_id: str = "ordinary",
        scenario_values: dict[str, Any] | None = None,
        dimensions: list[dict[str, Any]] | None = None,
        scenarios: list[dict[str, Any]] | None = None,
        mode: str = "EXHAUSTIVE",
        complete: bool = True,
    ) -> dict[str, Any]:
        return {
            "event_id": event_id,
            "mode": mode,
            "complete": complete,
            "rationale": "All currently known material behavior classes were inspected.",
            "stop_reason": "No unresolved material branch or anomaly remains.",
            "unresolved_material": [],
            "dimensions": dimensions or [],
            "scenarios": scenarios
            or [
                {
                    "scenario_id": scenario_id,
                    "label": scenario_id,
                    "role": "ORDINARY",
                    "values": scenario_values or {},
                    "action_ids": action_ids,
                }
            ],
        }

    def sync(
        self,
        event_ids: list[str],
        payloads: list[dict[str, Any]],
        *,
        action_id: str | None,
        coverage: dict[str, Any] | list[dict[str, Any]] | None = None,
        include_preview: bool = True,
        preview_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        bundle: dict[str, Any] = {}
        if include_preview:
            options = dict(preview_updates or {})
            bundle["preview"] = self.preview(payloads, action_id=action_id, **options)
        if coverage is not None:
            bundle["coverage"] = coverage
        return sync_preview(self.run, bundle, event_ids=event_ids)

    def execute_pass(
        self,
        *,
        event_id: str = "E-view_item",
        payload: dict[str, Any] | None = None,
        scenario_id: str = "ordinary",
        scenario_values: dict[str, Any] | None = None,
        page_updates: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        value = payload or {
            "event": "view_item",
            "ecommerce": {"items": [{"item_id": "SKU-1", "price": 29.9}]},
        }
        action_id = self.begin([event_id], scenario_id=scenario_id, scenario_values=scenario_values)
        self.commit(action_id, [value], page_updates=page_updates)
        coverage = self.coverage(
            event_id,
            [action_id],
            scenario_id=scenario_id,
            scenario_values=scenario_values,
        )
        result = self.sync([event_id], [value], action_id=action_id, coverage=coverage)
        return action_id, result["events"][0]

    def add_coverage(self, value: dict[str, Any]) -> dict[str, Any]:
        return add_coverage_review(self.run, value)

    def feedback(self, event_id: str) -> dict[str, Any]:
        return issue_event_feedback(self.run, event_id)
