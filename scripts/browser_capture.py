"""Deterministic parsers for native Playwright MCP page and network evidence."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class CaptureError(ValueError):
    """Raised when one fixed MCP capture contract is invalid."""


NETWORK_ROW = re.compile(
    r"^[ \t]*(?P<index>\d+)\.[ \t]+\[(?P<method>[A-Z]+)\][ \t]+"
    r"(?P<url>\S+)[ \t]+=>[ \t]+\[(?P<status>\d+|FAILED)\]"
    r"(?:[ \t]+(?P<note>.*))?$",
    re.MULTILINE,
)
NETWORK_DETAIL = re.compile(
    r"^#(?P<index>\d+)\s+\[(?P<method>[A-Z]+)\]\s+(?P<url>\S+)", re.MULTILINE
)
GA4_ENDPOINT = re.compile(r"(?:google-analytics\.com|/g/collect(?:\?|$)|[?&]v=2(?:&|$))", re.I)
TAB_ROW = re.compile(
    r"^-\s+(?P<index>\d+):(?:\s+\(current\))?\s+\[(?P<label>.*)\]\((?P<url>[^)]+)\)\s*$",
    re.MULTILINE,
)
REQUIRED_MCP_TOOLS = {
    "mcp__playwright__browser_tabs",
    "mcp__playwright__browser_snapshot",
    "mcp__playwright__browser_take_screenshot",
    "mcp__playwright__browser_click",
    "mcp__playwright__browser_navigate",
    "mcp__playwright__browser_fill_form",
    "mcp__playwright__browser_select_option",
    "mcp__playwright__browser_press_key",
    "mcp__playwright__browser_wait_for",
    "mcp__playwright__browser_network_requests",
    "mcp__playwright__browser_network_request",
    "mcp__playwright__browser_run_code_unsafe",
    "mcp__playwright__browser_close",
}


def validate_mcp_preflight(
    available_tools: list[str], tabs_text: str, target_url: str
) -> dict[str, Any]:
    """Validate the sole production browser interface before a run starts."""
    if not isinstance(available_tools, list) or not all(
        isinstance(name, str) for name in available_tools
    ):
        raise CaptureError("MCP preflight tool inventory must be a string list.")
    missing = sorted(REQUIRED_MCP_TOOLS - set(available_tools))
    if missing:
        raise CaptureError(f"Required Playwright MCP tool is unavailable: {missing[0]}.")
    tabs = [
        {
            "index": int(match.group("index")),
            "label": match.group("label"),
            "url": match.group("url"),
        }
        for match in TAB_ROW.finditer(tabs_text if isinstance(tabs_text, str) else "")
    ]
    prepared = [tab for tab in tabs if urlparse(tab["url"]).scheme in {"http", "https"}]
    preview = [
        tab
        for tab in prepared
        if (urlparse(tab["url"]).hostname or "").casefold()
        in {"tagassistant.google.com", "tagassistant.googleusercontent.com"}
    ]
    parsed_target = urlparse(target_url if isinstance(target_url, str) else "")
    if parsed_target.scheme not in {"http", "https"} or not parsed_target.hostname:
        raise CaptureError("MCP preflight target_url must be one exact HTTP(S) tab URL.")
    target = [tab for tab in prepared if tab["url"] == target_url and tab not in preview]
    connected = (
        len(preview) == 1 and re.search(r"\bconnected\b", preview[0]["label"], re.I) is not None
    )
    if not connected or len(target) != 1:
        raise CaptureError(
            "Prepared browser must identify the exact target website tab and one connected Tag Assistant tab."
        )
    return {
        "contract": "playwright-mcp-preflight-v1",
        "target_tab": target[0],
        "tag_assistant_tab": preview[0],
        "ignored_tabs": [tab for tab in tabs if tab != target[0] and tab != preview[0]],
    }


def validate_page_capture(
    snapshot_text: str, screenshot_path: Path | str, *, expected_url: str
) -> dict[str, Any]:
    """Validate one native MCP accessibility snapshot and its screenshot artifact."""
    if not isinstance(snapshot_text, str) or not snapshot_text.strip():
        raise CaptureError("MCP accessibility snapshot is empty.")
    image = Path(screenshot_path).resolve()
    if not image.is_file() or image.stat().st_size == 0:
        raise CaptureError("MCP screenshot artifact is missing or empty.")
    if not isinstance(expected_url, str) or not expected_url.startswith(("http://", "https://")):
        raise CaptureError("Page capture requires one exact HTTP(S) URL.")
    return {
        "observer_contract": "playwright-mcp-page-v1",
        "url": expected_url,
        "snapshot_text": snapshot_text,
        "screenshot_path": str(image),
    }


def parse_network_list(text: str) -> list[dict[str, Any]]:
    """Parse the numbered list returned by browser_network_requests."""
    if not isinstance(text, str):
        raise CaptureError("Network-list evidence must be text.")
    rows = []
    for match in NETWORK_ROW.finditer(text):
        status_text = match.group("status")
        rows.append(
            {
                "index": int(match.group("index")),
                "method": match.group("method"),
                "url": match.group("url"),
                "status": int(status_text) if status_text.isdigit() else None,
                "failed": status_text == "FAILED",
                "failure": match.group("note") if status_text == "FAILED" else None,
            }
        )
    indexes = [row["index"] for row in rows]
    if len(indexes) != len(set(indexes)):
        raise CaptureError("Network-list request indexes are duplicated.")
    return rows


def network_delta(
    before_text: str, after_text: str, *, navigation_occurred: bool
) -> list[dict[str, Any]]:
    """Return requests attributable to the measured action from two MCP lists."""
    before = parse_network_list(before_text)
    after = parse_network_list(after_text)
    if navigation_occurred:
        return after
    baseline = {
        (row["index"], row["method"], row["url"], row["status"], row["failed"]) for row in before
    }
    return [
        row
        for row in after
        if (row["index"], row["method"], row["url"], row["status"], row["failed"]) not in baseline
    ]


def ga4_candidate_indices(rows: list[dict[str, Any]]) -> list[int]:
    """Select only new requests whose URL can carry a GA4 protocol hit."""
    return [
        int(row["index"])
        for row in rows
        if isinstance(row, dict) and GA4_ENDPOINT.search(str(row.get("url") or ""))
    ]


def _section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^\s{{2}}{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^\s{{2}}[A-Z][^\n]*$|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return None
    body = match.group("body").strip("\n")
    return "\n".join(line[4:] if line.startswith("    ") else line for line in body.splitlines())


def parse_network_detail(text: str) -> dict[str, Any]:
    """Parse one full browser_network_request result into the request decoder schema."""
    if not isinstance(text, str):
        raise CaptureError("Network-detail evidence must be text.")
    match = NETWORK_DETAIL.search(text)
    if not match:
        raise CaptureError("Network-detail header is missing.")
    status_match = re.search(r"^\s*status:\s*\[(\d+)\]", text, re.MULTILINE)
    failure_match = re.search(r"^\s*failure:\s*(.+)$", text, re.MULTILINE)
    return {
        "index": int(match.group("index")),
        "url": match.group("url"),
        "method": match.group("method"),
        "post_data": _section(text, "Request body"),
        "status": int(status_match.group(1)) if status_match else None,
        "failed": failure_match is not None,
        "failure": failure_match.group(1).strip() if failure_match else None,
    }
