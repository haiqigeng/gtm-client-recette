"""Google Ads conversion request recognition and logical-send decoding."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def decode_ads_sends(request: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = str(request.get("endpoint") or "")
    parsed = urlsplit(endpoint)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.casefold()
    recognized_host = any(
        host.endswith(suffix)
        for suffix in ("googleadservices.com", "google.com", "doubleclick.net")
    )
    if not recognized_host or "conversion" not in path:
        return []
    query = request.get("query") if isinstance(request.get("query"), dict) else {}
    conversion_id = _first(query.get("google_conversion_id", query.get("conversion_id")))
    if conversion_id is None:
        fragments = [part for part in path.split("/") if part]
        conversion_id = next((part for part in fragments if part.isdigit()), None)
    label = _first(query.get("label", query.get("google_conversion_label")))
    destination = f"AW-{conversion_id}" if conversion_id else None
    return [
        {
            "logical_send_id": f"{request.get('request_id')}:1",
            "protocol": "google_ads",
            "event_name": "conversion",
            "destination": destination,
            "conversion_label": label,
            "parameters": query,
            "request_id": request.get("request_id"),
            "action_id": request.get("action_id"),
            "document_id": request.get("document_id"),
            "tag_ids": request.get("tag_ids", []),
            "correlation_id": request.get("correlation_id"),
            "endpoint": endpoint,
            "outcome": request.get("outcome"),
        }
    ]
