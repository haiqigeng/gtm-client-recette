"""GA4 request recognition and logical-hit decoding."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

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
    "lp": "index",
    "ln": "item_list_name",
    "li": "item_list_id",
}
NUMERIC_ITEM_FIELDS = {"price", "quantity", "discount", "index"}


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _rows(request: dict[str, Any]) -> list[dict[str, Any]]:
    query = request.get("query") if isinstance(request.get("query"), dict) else {}
    body = request.get("body") if isinstance(request.get("body"), dict) else {}
    records = body.get("records")
    if isinstance(records, list) and records:
        output = []
        for record in records:
            if not isinstance(record, dict):
                continue
            value = record.get("value")
            if isinstance(value, dict):
                output.append({**query, **value})
            else:
                output.append({**query, **record})
        return output
    decoded = body.get("decoded")
    if isinstance(decoded, dict):
        return [{**query, **decoded}]
    return [query]


def _number(value: Any) -> Any:
    try:
        number = float(str(value))
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def _item(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {"raw": value}
    output: dict[str, Any] = {}
    for segment in value.split("~"):
        if len(segment) < 3:
            continue
        field = ITEM_CODES.get(segment[:2])
        if field:
            item = segment[2:]
            output[field] = _number(item) if field in NUMERIC_ITEM_FIELDS else item
    return output


def _canonical_parameters(row: dict[str, Any]) -> dict[str, Any]:
    canonical: dict[str, Any] = {"event": _first(row.get("en"))}
    for key, value in row.items():
        actual = _first(value)
        if key.startswith("ep."):
            canonical[key[3:]] = actual
        elif key.startswith("epn."):
            canonical[key[4:]] = _number(actual)
    if row.get("cu") is not None:
        canonical["currency"] = _first(row.get("cu"))
    items = [
        _item(value)
        for key, value in sorted(
            row.items(),
            key=lambda item: (
                int(item[0][2:]) if item[0].startswith("pr") and item[0][2:].isdigit() else 10**9
            ),
        )
        if key.startswith("pr") and key[2:].isdigit()
    ]
    ecommerce_keys = {
        "affiliation",
        "coupon",
        "currency",
        "shipping",
        "shipping_tier",
        "tax",
        "transaction_id",
        "value",
    }
    ecommerce = {key: value for key, value in canonical.items() if key in ecommerce_keys}
    if items:
        canonical["items"] = items
        ecommerce["items"] = items
    if ecommerce:
        canonical["ecommerce"] = ecommerce
    return canonical


def decode_ga4_sends(request: dict[str, Any]) -> list[dict[str, Any]]:
    endpoint = str(request.get("endpoint") or "")
    parsed = urlsplit(endpoint)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.casefold()
    if not (
        (host.endswith("google-analytics.com") or host.endswith("analytics.google.com"))
        and path.endswith("/g/collect")
    ):
        return []
    output = []
    for index, row in enumerate(_rows(request), start=1):
        parameters = {
            **row,
            **_canonical_parameters(row),
        }
        output.append(
            {
                "logical_send_id": f"{request.get('request_id')}:{index}",
                "protocol": "ga4",
                "event_name": _first(row.get("en")),
                "destination": _first(row.get("tid")),
                "parameters": parameters,
                "request_id": request.get("request_id"),
                "action_id": request.get("action_id"),
                "document_id": request.get("document_id"),
                "tag_ids": request.get("tag_ids", []),
                "correlation_id": request.get("correlation_id"),
                "endpoint": endpoint,
                "outcome": request.get("outcome"),
                "collection_complete": request.get("collection_complete") is True,
            }
        )
    return output
