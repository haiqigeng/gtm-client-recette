"""Small protocol decoders for supported Google browser sends."""

from __future__ import annotations

from typing import Any

from .ads import decode_ads_sends
from .ga4 import decode_ga4_sends


def decode_logical_sends(request: dict[str, Any]) -> list[dict[str, Any]]:
    sends = decode_ga4_sends(request)
    if sends:
        return sends
    sends = decode_ads_sends(request)
    if sends:
        return sends
    return [
        {
            "logical_send_id": f"{request.get('request_id')}:1",
            "protocol": "generic",
            "event_name": None,
            "destination": None,
            "parameters": {},
            "request_id": request.get("request_id"),
            "action_id": request.get("action_id"),
            "document_id": request.get("document_id"),
            "tag_ids": request.get("tag_ids", []),
            "correlation_id": request.get("correlation_id"),
            "endpoint": request.get("endpoint"),
            "outcome": request.get("outcome"),
        }
    ]
