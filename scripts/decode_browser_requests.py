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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from client_side_rules import scan_sensitive_value
from path_safety import ensure_distinct_output
from state_io import atomic_write_json

DEFAULT_HEADERS = {"content-type"}
FORBIDDEN_HEADERS = {
    "api-key",
    "authorization",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-access-token",
    "x-amz-security-token",
    "x-api-key",
    "x-auth-token",
    "x-goog-api-key",
}
SECRET_HEADER_MARKERS = ("api-key", "apikey", "auth-token", "access-token", "secret")
MAX_REQUEST_ROWS = 100_000
MAX_BODY_BYTES = 10_000_000


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
        help="Retain raw text only in --quarantine-output; never in the normal output.",
    )
    parser.add_argument(
        "--quarantine-output",
        type=Path,
        help="Explicit separate output for raw-body evidence; required with --retain-raw-body.",
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


def _redact_scalar(value: Any, key: str | None = None) -> Any:
    target = {key: value} if key else value
    findings = scan_sensitive_value(
        target,
        root_path="$",
        policy={"scan_unkeyed_phone_values": True, "scan_unkeyed_ip_values": True},
    )
    if not findings:
        return value
    categories = sorted({str(row.get("category", "sensitive")) for row in findings})
    return f"<redacted:{'+'.join(categories)}>"


def _redact_value(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {
            str(child_key): _redact_value(child, str(child_key))
            for child_key, child in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(child, key) for child in value]
    return _redact_scalar(value, key)


def _safe_url(parsed: Any, query: dict[str, Any]) -> str:
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = f":{parsed.port}" if parsed.port is not None else ""
    netloc = f"{hostname}{port}"
    redacted_path = _redact_scalar(parsed.path)
    safe_path = (
        "/<redacted:sensitive-path>"
        if isinstance(redacted_path, str) and redacted_path.startswith("<redacted:")
        else str(redacted_path)
    )
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            safe_path,
            urlencode(query, doseq=True),
            "",
        )
    )


def _decode_body(
    body: str | None,
    raw_bytes: bytes | None,
    content_type: str,
    retain_raw_body: bool,
) -> dict[str, Any] | None:
    if body is None or raw_bytes is None:
        return None
    if len(raw_bytes) > MAX_BODY_BYTES:
        raise ValueError(f"Request body exceeds {MAX_BODY_BYTES} bytes.")
    result: dict[str, Any] = {
        "content_type": content_type or None,
        "length": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
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


def _post_data(row: dict[str, Any]) -> tuple[str | None, bytes | None]:
    value = row.get("post_data")
    if value is None and row.get("post_data_base64") is not None:
        try:
            raw = base64.b64decode(str(row["post_data_base64"]), validate=True)
            return raw.decode("utf-8", errors="replace"), raw
        except (ValueError, TypeError):
            return None, None
    if value is None:
        return None, None
    text = str(value)
    return text, text.encode("utf-8")


def _forbidden_header(name: str) -> bool:
    lowered = name.lower()
    return lowered in FORBIDDEN_HEADERS or any(
        marker in lowered for marker in SECRET_HEADER_MARKERS
    )


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
    forbidden_requested = sorted(item for item in allowed if _forbidden_header(item))
    if forbidden_requested:
        raise ValueError(
            "Secret-bearing headers cannot be retained: " + ", ".join(forbidden_requested)
        )
    retained_headers = {
        key: _redact_value(value, key) for key, value in headers.items() if key in allowed
    }
    body_text, body_bytes = _post_data(row)
    body = _decode_body(
        body_text,
        body_bytes,
        headers.get("content-type", ""),
        retain_raw_body,
    )
    if body is not None and not retain_raw_body:
        for field in ("decoded", "records"):
            if field in body:
                body[field] = _redact_value(body[field])
    query = _redact_value(_multi_value(parse_qsl(parsed.query, keep_blank_values=True)))
    return {
        "request_id": str(row.get("request_id") or f"REQ-{index:04d}"),
        "action_id": row.get("action_id"),
        "timestamp": row.get("timestamp"),
        "resource_type": row.get("resource_type"),
        "method": str(row.get("method") or "GET").upper(),
        "request_url": _safe_url(parsed, query),
        "endpoint": _safe_url(parsed, {}).split("?", 1)[0],
        "query": query,
        "headers": retained_headers,
        "excluded_header_names": sorted(key for key in headers if key not in retained_headers),
        "body": body,
    }


def decode_requests(
    value: Any,
    include_headers: set[str] | None = None,
    retain_raw_body: bool = False,
    *,
    quarantine: bool = False,
) -> dict[str, Any]:
    if retain_raw_body and not quarantine:
        raise ValueError("Raw request bodies require an explicit quarantine decode.")
    rows = value.get("requests") if isinstance(value, dict) else value
    if not isinstance(rows, list):
        raise ValueError("Input must be an array or an object with a requests array.")
    if len(rows) > MAX_REQUEST_ROWS:
        raise ValueError(f"Input exceeds {MAX_REQUEST_ROWS} request rows.")
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
    output = {
        "schema_version": 1,
        "request_count": len(decoded),
        "requests": decoded,
    }
    if quarantine:
        output["quarantine"] = {
            "contains_raw_sensitive_values": True,
            "must_not_be_attached_to_results": True,
        }
    return output


def main() -> int:
    args = parse_args()
    try:
        ensure_distinct_output(args.output, args.input, label="decoded request output")
        if args.retain_raw_body and args.quarantine_output is None:
            raise ValueError("--retain-raw-body requires a separate --quarantine-output path")
        if args.quarantine_output is not None:
            ensure_distinct_output(
                args.quarantine_output,
                args.input,
                args.output,
                label="raw-body quarantine output",
            )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    value = json.loads(args.input.read_text(encoding="utf-8"))
    included_headers = DEFAULT_HEADERS | {str(item).lower() for item in args.include_header}
    try:
        output = decode_requests(
            value,
            include_headers=included_headers,
            retain_raw_body=False,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    atomic_write_json(args.output, output)
    if args.retain_raw_body and args.quarantine_output is not None:
        quarantine = decode_requests(
            value,
            include_headers=included_headers,
            retain_raw_body=True,
            quarantine=True,
        )
        atomic_write_json(args.quarantine_output, quarantine)
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
