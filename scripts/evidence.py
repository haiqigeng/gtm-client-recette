"""Deterministic normalization of raw Tag Assistant and GA4 request evidence."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from tag_assistant import _tokens, _ValueParser

GA4_ID = re.compile(r"\b(?:G|GT)-[A-Z0-9-]+\b", re.I)
GA4_TAG = re.compile(r"\b(?:GA4|Google Analytics|Google tag)\b", re.I)
TECHNICAL_EVENT = re.compile(
    r"^(?:gtm\.|message$|container loaded$|dom ready$|window loaded$|trigger group$|consent)",
    re.I,
)
ITEM_CODES = {
    "id": "item_id",
    "nm": "item_name",
    "br": "item_brand",
    "ca": "item_category",
    "c2": "item_category2",
    "c3": "item_category3",
    "c4": "item_category4",
    "c5": "item_category5",
    "va": "item_variant",
    "pr": "price",
    "qt": "quantity",
    "cp": "coupon",
    "ds": "discount",
    "ln": "item_list_name",
    "li": "item_list_id",
    "af": "affiliation",
    "lp": "index",
}


def _display_value(value: str) -> Any:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return _ValueParser(_tokens(text)).arguments()[0]
    except (ValueError, IndexError):
        return text


def _tag_technology(tag: dict[str, Any]) -> str:
    text = json.dumps(tag, ensure_ascii=False, sort_keys=True, default=str)
    return "GA4" if GA4_TAG.search(text) or GA4_ID.search(text) else "OTHER"


def build_gtm_evidence(raw_capture: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Normalize concerned tags on bounded causal rows at or after the source event."""
    selected = source.get("selected")
    if not isinstance(selected, dict):
        return {
            "complete": source.get("complete") is True,
            "attributable": False,
            "tags": [],
            "reason": "No exactly selected API Call exists for tag attribution.",
        }
    cursor = selected.get("cursor")
    rows = [
        item
        for item in raw_capture.get("rows", [])
        if isinstance(item, dict)
        and isinstance(item.get("cursor"), int)
        and item["cursor"] >= cursor
    ]
    if not rows or not any(item.get("cursor") == cursor for item in rows):
        return {
            "complete": False,
            "attributable": False,
            "tags": [],
            "reason": "Selected Tag Assistant row is absent from raw capture.",
        }
    tags = []
    for row in rows:
        for raw_tag in row.get("tags", []):
            if not isinstance(raw_tag, dict):
                continue
            technology = _tag_technology(raw_tag)
            names = {
                str(key): _display_value(value) for key, value in raw_tag.get("names", {}).items()
            }
            values = {
                str(key): _display_value(value) for key, value in raw_tag.get("values", {}).items()
            }
            count_match = re.search(
                r"fired\s+(\d+)\s+times?",
                f"{raw_tag.get('detail_text', '')}\n{row.get('panel_text', '')}",
                re.I,
            )
            fired = raw_tag.get("fired") is True
            tags.append(
                {
                    "name": str(raw_tag.get("name") or ""),
                    "technology": technology,
                    "concerned": technology == "GA4",
                    "fired": fired,
                    "firing_count": int(count_match.group(1)) if count_match else int(fired),
                    "mappings": names,
                    "runtime": values,
                    "complete": bool(names) and bool(values),
                    "event_cursor": row["cursor"],
                }
            )
    concerned = [tag for tag in tags if tag["concerned"]]
    complete = bool(concerned) and all(tag["complete"] for tag in concerned)
    return {
        "complete": complete,
        "attributable": True,
        "tags": tags,
        "reason": None if complete else "Concerned GA4 Names/Values evidence is incomplete.",
    }


def _number(value: str) -> int | float | str:
    try:
        parsed = float(value)
    except ValueError:
        return value
    return int(parsed) if parsed.is_integer() else parsed


def _item(value: str) -> dict[str, Any]:
    item: dict[str, Any] = {}
    for part in value.split("~"):
        code = part[:2]
        raw = part[2:]
        if code in ITEM_CODES:
            item[ITEM_CODES[code]] = _number(raw) if code in {"pr", "qt", "ds", "lp"} else raw
    return item


def _payload(parameters: list[tuple[str, str]]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    items: list[tuple[int, dict[str, Any]]] = []
    for key, value in parameters:
        if key == "en":
            payload["event"] = value
        elif key == "tid":
            payload["destination_id"] = value
        elif key.startswith("ep."):
            payload[key[3:]] = value
        elif key.startswith("epn."):
            payload[key[4:]] = _number(value)
        elif re.fullmatch(r"pr\d+", key):
            items.append((int(key[2:]), _item(value)))
        elif key not in {"v"}:
            payload[key] = value
    if items:
        payload["items"] = [value for _, value in sorted(items)]
    return payload


def _protocol_hits(record: dict[str, Any]) -> list[dict[str, Any]]:
    split = urlsplit(str(record.get("url") or ""))
    query = parse_qsl(split.query, keep_blank_values=True)
    body = str(record.get("post_data") or "")
    bodies = body.splitlines() if "\n" in body else [body]
    hits = []
    for line in bodies:
        parameters = [*query, *parse_qsl(line, keep_blank_values=True)]
        values = dict(parameters)
        if values.get("v") != "2" or not values.get("tid") or not values.get("en"):
            continue
        payload = _payload(parameters)
        identity = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        hits.append(
            {
                "url": record.get("url"),
                "method": record.get("method"),
                "status": record.get("status"),
                "failed": record.get("failed") is True,
                "failure": record.get("failure"),
                "sent": True,
                "logical_hit_id": identity,
                "parameters": payload,
            }
        )
    return hits


def decode_ga4_requests(raw_records: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    """Decode direct, POST, batch, and first-party GA4 protocol hits."""
    all_hits = [hit for record in raw_records for hit in _protocol_hits(record)]
    requests = [hit for hit in all_hits if hit["parameters"].get("event") == event_name]
    counts = Counter(hit["logical_hit_id"] for hit in requests)
    for hit in requests:
        hit["duplicate"] = counts[hit["logical_hit_id"]] > 1
    incomplete = any(hit["status"] is None and hit["failed"] is not True for hit in requests)
    return {
        "complete": not incomplete,
        "attributable": True,
        "requests": requests,
        "all_ga4_requests": all_hits,
        "reason": None if not incomplete else "A GA4 request has no response or failure result.",
    }


def build_behavior_evidence(source: dict[str, Any]) -> dict[str, Any]:
    """Preserve the complete parsed Preview chronology for anomaly judgment."""
    parsed_by_cursor = {
        call.get("cursor"): call for call in source.get("calls", []) if isinstance(call, dict)
    }
    messages = []
    for row in source.get("overview_rows", []):
        if not isinstance(row, dict):
            continue
        call = parsed_by_cursor.get(row.get("cursor"), {})
        payload = call.get("payload") if isinstance(call.get("payload"), dict) else {}
        wrapper = str(payload.get("event") or row.get("row_name") or "")
        semantic = str(payload.get("event_name") or wrapper)
        business = bool(semantic) and (semantic != wrapper or not TECHNICAL_EVENT.search(semantic))
        messages.append(
            {
                "cursor": row.get("cursor"),
                "event_name": semantic,
                "wrapper_event": wrapper,
                "payload": payload,
                "business": business,
                "complete": call.get("complete") is True if call else True,
            }
        )
    if messages:
        return {
            "complete": source.get("complete") is True,
            "attributable": source.get("attributable") is True,
            "messages": messages,
            "reason": source.get("reason"),
            "findings": [],
        }
    for call in source.get("calls", []):
        payload = call.get("payload") if isinstance(call.get("payload"), dict) else {}
        wrapper = str(payload.get("event") or call.get("row_name") or "")
        semantic = str(payload.get("event_name") or wrapper)
        business = bool(semantic) and (semantic != wrapper or not TECHNICAL_EVENT.search(semantic))
        messages.append(
            {
                "cursor": call.get("cursor"),
                "event_name": semantic,
                "wrapper_event": wrapper,
                "payload": payload,
                "business": business,
                "complete": call.get("complete") is True,
            }
        )
    return {
        "complete": source.get("complete") is True,
        "attributable": source.get("attributable") is True,
        "messages": messages,
        "reason": source.get("reason"),
        "findings": [],
    }
