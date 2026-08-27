#!/usr/bin/env python3
"""Fixed in-memory JSONL bridge from native MCP text to deterministic parsers."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from browser_actions import resolve_snapshot_ref
from browser_capture import (
    ga4_candidate_indices,
    network_delta,
    parse_network_detail,
    validate_mcp_preflight,
    validate_page_capture,
)
from tag_assistant import (
    api_call_text,
    candidate_and_carrier_rows,
    compile_api_call_expand,
    concerned_tag_buttons,
    exact_button_ref,
    parse_api_call,
    parse_event_overview,
    properties_table,
)


class BridgeError(ValueError):
    """Raised when the fixed bridge protocol is violated."""


def _fields(request: dict[str, Any], expected: set[str]) -> None:
    actual = set(request)
    if actual != expected:
        raise BridgeError(
            f"Bridge fields invalid; missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}."
        )


def _target_ref(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text", "semantic_locator"})
    return {"ref": resolve_snapshot_ref(request["snapshot_text"], request["semantic_locator"])}


def _preflight(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "available_tools", "tabs_text", "target_url"})
    return validate_mcp_preflight(
        request["available_tools"], request["tabs_text"], request["target_url"]
    )


def _page_capture(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text", "screenshot_path", "expected_url"})
    capture = validate_page_capture(
        request["snapshot_text"],
        request["screenshot_path"],
        expected_url=request["expected_url"],
    )
    capture["aria_snapshot"] = capture.pop("snapshot_text")
    return capture


def _network_window(request: dict[str, Any]) -> dict[str, Any]:
    _fields(
        request,
        {"stage", "before_text", "after_text", "navigation_occurred"},
    )
    if not isinstance(request["navigation_occurred"], bool):
        raise BridgeError("navigation_occurred must be boolean.")
    rows = network_delta(
        request["before_text"],
        request["after_text"],
        navigation_occurred=request["navigation_occurred"],
    )
    return {"rows": rows, "ga4_candidate_indices": ga4_candidate_indices(rows)}


def _network_detail(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "detail_text"})
    return parse_network_detail(request["detail_text"])


def _tag_overview(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text", "preview_cursor", "selector"})
    overview = parse_event_overview(request["snapshot_text"], request["preview_cursor"])
    return {**overview, **candidate_and_carrier_rows(overview, request["selector"])}


def _tag_selected(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text", "expected_event_name"})
    return compile_api_call_expand(request["snapshot_text"], request["expected_event_name"])


def _tag_api(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text"})
    text = api_call_text(request["snapshot_text"])
    return {"api_call_text": text, "parsed": parse_api_call(text)}


def _tag_summary(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text"})
    return {"concerned_tags": concerned_tag_buttons(request["snapshot_text"])}


def _tag_tabs(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text"})
    return {"tags_button_ref": exact_button_ref(request["snapshot_text"], "Tags")}


def _tag_properties(request: dict[str, Any]) -> dict[str, Any]:
    _fields(request, {"stage", "snapshot_text", "display"})
    if request["display"] not in {"Names", "Values"}:
        raise BridgeError("display must be exactly Names or Values.")
    result = {
        "display": request["display"],
        "properties": properties_table(request["snapshot_text"]),
    }
    if request["display"] == "Names":
        result["values_button_ref"] = exact_button_ref(request["snapshot_text"], "Values")
    else:
        result["close_button_ref"] = exact_button_ref(request["snapshot_text"], "Close screen")
    return result


STAGES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "preflight": _preflight,
    "target_ref": _target_ref,
    "page_capture": _page_capture,
    "network_window": _network_window,
    "network_detail": _network_detail,
    "tag_overview": _tag_overview,
    "tag_selected": _tag_selected,
    "tag_api": _tag_api,
    "tag_tabs": _tag_tabs,
    "tag_summary": _tag_summary,
    "tag_properties": _tag_properties,
}


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")), flush=True)


def main() -> int:
    if len(sys.argv) != 1:
        print("mcp_bridge.py accepts no arguments.", file=sys.stderr)
        return 2
    for line_number, line in enumerate(sys.stdin, 1):
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(request.get("stage"), str):
                raise BridgeError("Each bridge request must be an object with one string stage.")
            if request["stage"] == "close":
                _fields(request, {"stage"})
                _emit({"status": "closed"})
                return 0
            handler = STAGES.get(request["stage"])
            if handler is None:
                raise BridgeError(f"Unsupported bridge stage {request['stage']!r}.")
            _emit({"stage": request["stage"], "result": handler(request)})
        except (TypeError, ValueError, KeyError) as error:
            _emit(
                {
                    "error": "MCP_BRIDGE_CONTRACT",
                    "line": line_number,
                    "message": str(error),
                }
            )
            return 1
    print("mcp_bridge.py requires an explicit close request.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
