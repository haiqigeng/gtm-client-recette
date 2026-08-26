from __future__ import annotations

from copy import deepcopy
from typing import Any


def event_fixture() -> dict[str, Any]:
    return {
        "event_id": "View-Item",
        "event_name": "view_item",
        "expected_destination_id": "G-TEST",
        "selector": {"event": "view_item"},
        "fields": [
            {
                "path": "ecommerce.items[].item_name",
                "type": "string",
                "required": True,
                "rule": "present",
            },
            {
                "path": "ecommerce.items[].quantity",
                "type": "number",
                "required": True,
                "rule": "present",
            },
            {
                "path": "ecommerce.currency",
                "type": "string",
                "required": True,
                "rule": "equals",
                "expected": "EUR",
            },
        ],
    }


def payload(quantity: int = 1, currency: str = "EUR") -> dict[str, Any]:
    return {
        "event": "view_item",
        "destination_id": "G-TEST",
        "ecommerce": {
            "items": [{"item_name": "Synthetic product", "quantity": quantity}],
            "currency": currency,
        },
    }


def action_fixture() -> dict[str, Any]:
    return {
        "action_id": "A-0001",
        "event_id": "View-Item",
        "event_name": "view_item",
        "preview_cursor": 0,
    }


def bundle_fixture(quantity: int = 1) -> dict[str, Any]:
    value = payload(quantity)
    return {
        "observer_contract": "playwright-mcp-v1",
        "action_id": "A-0001",
        "event_id": "View-Item",
        "preview_cursor": 1,
        "scenario_id": "view_item",
        "reality": {
            "complete": True,
            "attributable": True,
            "page": {"url": "https://example.test/product", "status_code": 200, "soft_404": False},
            "outcome": True,
            "expected": {
                "ecommerce.items[].item_name": ["Synthetic product"],
                "ecommerce.items[].quantity": [quantity],
                "ecommerce.currency": "EUR",
            },
            "findings": [],
        },
        "source": {
            "complete": True,
            "attributable": True,
            "occurrence_count": 1,
            "selected": {"cursor": 1, "payload": deepcopy(value)},
            "calls": [
                {
                    "cursor": 1,
                    "event_name": "view_item",
                    "payload": deepcopy(value),
                    "business": True,
                }
            ],
        },
        "gtm": {
            "complete": True,
            "attributable": True,
            "tags": [
                {
                    "name": "GA4 - view_item",
                    "concerned": True,
                    "fired": True,
                    "firing_count": 1,
                    "mapped_paths": ["event", "ecommerce"],
                    "mappings": {"event": "view_item", "ecommerce": "Data Layer"},
                    "runtime": deepcopy(value),
                }
            ],
            "findings": [],
        },
        "network": {
            "complete": True,
            "attributable": True,
            "requests": [
                {
                    "url": "https://analytics.example.test/collect",
                    "status": 204,
                    "failed": False,
                    "duplicate": False,
                    "logical_hit_id": "hit-1",
                    "parameters": deepcopy(value),
                }
            ],
            "findings": [],
        },
        "behavior": {
            "complete": True,
            "attributable": True,
            "messages": [
                {
                    "cursor": 1,
                    "event_name": "view_item",
                    "payload": deepcopy(value),
                    "business": True,
                }
            ],
            "findings": [],
        },
    }
