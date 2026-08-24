"""Canonical vocabulary for the zero-based recette runtime."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = "6.0"

STATUSES = frozenset({"PASS", "FAIL", "BLOCKED", "REVIEW", "NOT_APPLICABLE", "PENDING"})
STATUS_PRIORITY = {
    "NOT_APPLICABLE": 0,
    "PASS": 1,
    "PENDING": 2,
    "REVIEW": 3,
    "BLOCKED": 4,
    "FAIL": 5,
}

DOMAINS = (
    "reality",
    "source",
    "gtm",
    "delivery",
    "behavior",
    "safety",
)
DOMAIN_LABELS = {
    "reality": "Reality",
    "source": "Source signal",
    "gtm": "GTM decision",
    "delivery": "Destination delivery",
    "behavior": "Surrounding behavior",
    "safety": "Data safety",
}

CLAIM_ARCHETYPES = frozenset({"reality", "source", "gtm", "delivery", "sequence", "safety"})
ARCHETYPE_DOMAIN = {
    "reality": "reality",
    "source": "source",
    "gtm": "gtm",
    "delivery": "delivery",
    "sequence": "behavior",
    "safety": "safety",
}

PROVENANCES = frozenset({"machine_observed", "user_provided", "analyst_annotation", "derived"})
USER_RECORD_KINDS = frozenset({"REOPEN_AUTHORIZATION"})
ANALYST_RECORD_KINDS = frozenset(
    {
        "ACTION_BEGIN",
        "ACTION_COMMIT",
        "COVERAGE_REVIEW",
        "SEMANTIC_FINDING",
        "PROTECTED_HANDOFF",
        "ACQUISITION_CONTEXT",
    }
)
MACHINE_RECORD_KINDS = frozenset(
    {
        "CAPTURE_CAPABILITY",
        "CAPTURE_BINDING",
        "CAPTURE_HEALTH",
        "CAPTURE_PAGE",
        "CAPTURE_DATALAYER",
        "CAPTURE_SOURCE",
        "CAPTURE_PREVIEW",
        "CAPTURE_NETWORK",
        "CAPTURE_LIFECYCLE",
    }
)
DERIVED_RECORD_KINDS = frozenset(
    {
        "PREVIEW_SYNC",
        "EVENT_FEEDBACK_ISSUED",
        "RUN_FINISHED",
        "RUN_REOPENED",
    }
)

CAPTURE_KINDS = {
    "capability": "CAPTURE_CAPABILITY",
    "binding": "CAPTURE_BINDING",
    "health": "CAPTURE_HEALTH",
    "page": "CAPTURE_PAGE",
    "datalayer": "CAPTURE_DATALAYER",
    "source": "CAPTURE_SOURCE",
    "preview": "CAPTURE_PREVIEW",
    "network": "CAPTURE_NETWORK",
    "lifecycle": "CAPTURE_LIFECYCLE",
}

MATERIALITY_DEFINITION = (
    "A value, state, or behaviour is material when it can affect occurrence, value, "
    "JSON type, order, context, an in-scope tag or destination, consent/privacy, page "
    "or action validity, business coherence, scenario coverage, or the verdict."
)

OPERATION_COUNTERS = (
    "navigations",
    "resets",
    "reloads",
    "target_tab_switches",
    "preview_tab_switches",
    "full_preflights",
    "preview_summary_reads",
    "preview_deep_reads",
    "preview_retries",
    "ai_semantic_passes",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def worst_status(values: Iterable[str], *, default: str = "PENDING") -> str:
    normalized = [value for value in values if value in STATUS_PRIORITY]
    return max(normalized, key=STATUS_PRIORITY.__getitem__) if normalized else default


def status_label(status: str) -> str:
    if status == "PASS":
        return "OK"
    if status == "FAIL":
        return "KO"
    return status


def compact_reason(value: Any, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: max(0, limit - 3)] + "..."
