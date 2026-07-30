#!/usr/bin/env python3
"""Small shared acceptance primitives used across recette validators."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

VALID_STATUSES = {"PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_TESTED"}
STATUS_PRIORITY = ("FAIL", "BLOCKED", "REVIEW", "NOT_TESTED", "PASS")
STATUS_RANK = {status: len(STATUS_PRIORITY) - index for index, status in enumerate(STATUS_PRIORITY)}

ACTION_BOUNDARY_FIELDS = (
    "action_id",
    "retry_of_action_id",
    "last_event_before",
    "first_event_after",
    "settled_final_event",
    "action_timestamp",
    "interaction_outcome",
    "completion_signal",
    "quiet_window_ms",
    "timeout_ms",
    "stream_settled",
    "settlement_reason",
)


def status_of(value: Any) -> str:
    """Normalize a row or scalar status."""
    if isinstance(value, dict):
        value = value.get("status", "")
    return str(value or "").strip().upper()


def worst_status(statuses: Iterable[Any]) -> str:
    """Return the worst applicable final status."""
    normalized = [status_of(status) for status in statuses if status_of(status) in VALID_STATUSES]
    return max(normalized, key=STATUS_RANK.__getitem__) if normalized else "NOT_TESTED"
