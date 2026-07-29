#!/usr/bin/env python3
"""Decode captured browser requests into stable query/body evidence paths."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

DEFAULT_HEADERS = {"content-type"}
FORBIDDEN_HEADERS = {
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON request list or {requests: [...]} file.")
    parser.add_argument("output", type=Path, help="Destination decoded JSON.")
    parser.add_argument(
        "--include-header",
        action="append",
        default=[],
        help="Additional non-secret request header to retain; may be repeated.",
    )
    parser.add_argument(
        "--retain-raw-body",
        action="store_true",
        help="Retain raw text body in the output; scan/quarantine it before reporting.",
    )
    return parser.parse_args()


def _multi_value(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for key, value in pairs:
        grouped[key].append(value)
    return {key: values[0] if len(values) == 1 else values for key, values in grouped.items()}


def _headers(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key).lower(): str(item) for key, item in value.items()}
    if isinstance(value, list):
        result: dict[str, str] = {}
        for row in value:
            if isinstance(row, dict) and row.get("name") is not None:
                result[str(row["name"]).lower()] = str(row.get("value", ""))
        return result
    return {}


def _parse_line(line: str) -> dict[str, Any]:
    stripped = line.strip()
    if not stripped:
        return {"format": "empty", "value": ""}
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        pairs = parse_qsl(stripped, keep_blank_values=True)
        if pairs and all("=" in part for part in stripped.split("&")):
            return {"format": "form", "value": _multi_value(pairs)}
        return {"format": "text", "value": stripped}
    return {"format": "json", "value": value}


def _decode_body(
    body: str | None,
    content_type: str,
    retain_raw_body: bool,
) -> dict[str, Any] | None:
    if body is None:
        return None
    encoded = body.encode("utf-8", errors="replace")
    result: dict[str, Any] = {
        "content_type": content_type or None,
        "length": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }
    lowered = content_type.lower()
    if "application/json" in lowered or lowered.endswith("+json"):
        try:
            result["decoded"] = json.loads(body)
            result["format"] = "json"
        except json.JSONDecodeError:
            result["format"] = "invalid_json"
    elif "application/x-www-form-urlencoded" in lowered:
        result["decoded"] = _multi_value(parse_qsl(body, keep_blank_values=True))
        result["format"] = "form"
    elif "multipart/form-data" in lowered:
        result["format"] = "multipart"
    else:
        lines = [line for line in body.splitlines() if line.strip()]
        if len(lines) > 1:
            result["format"] = "newline_batch"
            result["records"] = [_parse_line(line) for line in lines]
        elif lines:
            parsed = _parse_line(lines[0])
            result["format"] = parsed["format"]
            result["decoded"] = parsed["value"]
        else:
            result["format"] = "empty"
            result["decoded"] = ""
    if retain_raw_body:
        result["raw"] = body
    return result


def _post_data(row: dict[str, Any]) -> str | None:
    value = row.get("post_data")
    if value is None and row.get("post_data_base64") is not None:
        try:
            return base64.b64decode(str(row["post_data_base64"])).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return None
    if value is None:
        return None
    return str(value)


def decode_request(
    row: dict[str, Any],
    index: int,
    include_headers: set[str] | None = None,
    retain_raw_body: bool = False,
) -> dict[str, Any]:
    url = str(row.get("url", "")).strip()
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Request {index} has no absolute URL.")
    headers = _headers(row.get("headers"))
    allowed = {item.lower() for item in (include_headers or DEFAULT_HEADERS)}
    forbidden_requested = sorted(allowed & FORBIDDEN_HEADERS)
    if forbidden_requested:
        raise ValueError(
            "Secret-bearing headers cannot be retained: " + ", ".join(forbidden_requested)
        )
    retained_headers = {key: value for key, value in headers.items() if key in allowed}
    body = _decode_body(
        _post_data(row),
        headers.get("content-type", ""),
        retain_raw_body,
    )
    return {
        "request_id": str(row.get("request_id") or f"REQ-{index:04d}"),
        "action_id": row.get("action_id"),
        "timestamp": row.get("timestamp"),
        "resource_type": row.get("resource_type"),
        "method": str(row.get("method") or "GET").upper(),
        "request_url": url,
        "endpoint": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        "query": _multi_value(parse_qsl(parsed.query, keep_blank_values=True)),
        "headers": retained_headers,
        "excluded_header_names": sorted(key for key in headers if key not in retained_headers),
        "body": body,
    }


def decode_requests(
    value: Any,
    include_headers: set[str] | None = None,
    retain_raw_body: bool = False,
) -> dict[str, Any]:
    rows = value.get("requests") if isinstance(value, dict) else value
    if not isinstance(rows, list):
        raise ValueError("Input must be an array or an object with a requests array.")
    decoded = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Request {index} must be an object.")
        decoded.append(
            decode_request(
                row,
                index,
                include_headers=include_headers,
                retain_raw_body=retain_raw_body,
            )
        )
    return {
        "schema_version": 1,
        "request_count": len(decoded),
        "requests": decoded,
    }


def main() -> int:
    args = parse_args()
    value = json.loads(args.input.read_text(encoding="utf-8"))
    included_headers = DEFAULT_HEADERS | {str(item).lower() for item in args.include_header}
    try:
        output = decode_requests(
            value,
            include_headers=included_headers,
            retain_raw_body=args.retain_raw_body,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
