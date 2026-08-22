#!/usr/bin/env python3
"""Shared JSON value and timestamp semantics used by recette validators."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def json_value_type(value: Any) -> str:
    """Return the normalized JSON-compatible type name."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def is_json_number(value: Any) -> bool:
    """Return whether a value is a JSON number rather than a boolean."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's boolean/number shortcut."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if is_json_number(left) or is_json_number(right):
        return is_json_number(left) and is_json_number(right) and left == right
    return type(left) is type(right) and left == right


def field_state_for(value: Any) -> str:
    """Return the explicit field state used across raw, resolved, and semantic checks."""
    if value is None:
        return "null"
    if value == "":
        return "empty"
    return "value"


def parse_iso_timestamp(value: Any) -> datetime | None:
    """Parse one timezone-qualified ISO timestamp, returning ``None`` when invalid."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
