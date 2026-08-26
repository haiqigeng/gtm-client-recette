"""Strict contracts for the two per-event adaptive records."""

from __future__ import annotations

from typing import Any


class AdaptiveError(ValueError):
    """Raised when adaptive output exceeds its fixed contract."""


VISUAL_FIELDS = {
    "event_id",
    "scenario_id",
    "target_match",
    "outcome",
    "observed_values",
    "anomaly_codes",
    "summary",
    "evidence_refs",
}
TARGET_MATCHES = {"MATCH", "MISMATCH", "UNDETERMINED"}
OUTCOMES = {"EXPECTED", "UNEXPECTED", "UNDETERMINED"}
ANOMALY_CODES = {
    "TARGET_NOT_FOUND",
    "WRONG_TARGET",
    "NO_VISIBLE_CHANGE",
    "UNEXPECTED_VISIBLE_OUTCOME",
    "VISIBLE_ERROR",
    "VISUAL_EVIDENCE_INCOMPLETE",
}


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdaptiveError(f"{field} must be a non-empty string.")
    return value.strip()


def validate_visual_assessment(
    assessment: dict[str, Any], event: dict[str, Any], valid_evidence_refs: set[str]
) -> dict[str, Any]:
    """Validate visual interpretation without accepting a final layer status."""
    if not isinstance(assessment, dict) or set(assessment) != VISUAL_FIELDS:
        actual = set(assessment) if isinstance(assessment, dict) else set()
        raise AdaptiveError(
            f"VisualAssessment fields invalid; missing={sorted(VISUAL_FIELDS - actual)}, "
            f"unknown={sorted(actual - VISUAL_FIELDS)}."
        )
    if assessment["event_id"] != event.get("event_id"):
        raise AdaptiveError("VisualAssessment changed event identity.")
    if assessment["scenario_id"] != event.get("event_name"):
        raise AdaptiveError("scenario_id must equal the canonical event_name.")
    target_match = assessment["target_match"]
    outcome = assessment["outcome"]
    if target_match not in TARGET_MATCHES:
        raise AdaptiveError("target_match is invalid.")
    if outcome not in OUTCOMES:
        raise AdaptiveError("outcome is invalid.")
    observed = assessment["observed_values"]
    if not isinstance(observed, dict):
        raise AdaptiveError("observed_values must be an object.")
    anomalies = assessment["anomaly_codes"]
    if (
        not isinstance(anomalies, list)
        or len(anomalies) != len(set(anomalies))
        or any(code not in ANOMALY_CODES for code in anomalies)
    ):
        raise AdaptiveError("anomaly_codes contains an unsupported or duplicate code.")
    if target_match == "MATCH" and outcome == "EXPECTED" and anomalies:
        raise AdaptiveError("A fully expected visual assessment cannot contain anomalies.")
    if (target_match != "MATCH" or outcome != "EXPECTED") and not anomalies:
        raise AdaptiveError("A non-passing visual assessment requires an anomaly code.")
    refs = assessment["evidence_refs"]
    if (
        not isinstance(refs, list)
        or not refs
        or not all(isinstance(ref, str) and ref in valid_evidence_refs for ref in refs)
    ):
        raise AdaptiveError("evidence_refs must cite available per-event evidence.")
    return {
        "event_id": assessment["event_id"],
        "scenario_id": event["event_name"],
        "target_match": target_match,
        "outcome": outcome,
        "observed_values": observed,
        "anomaly_codes": anomalies,
        "summary": _text(assessment["summary"], "summary"),
        "evidence_refs": list(dict.fromkeys(refs)),
    }


def build_reality_evidence(
    before: dict[str, Any],
    after: dict[str, Any],
    action: dict[str, Any],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    """Convert validated visible evidence into deterministic reality evidence."""
    action_executed = action.get("executed") is True
    determined = (
        assessment["target_match"] != "UNDETERMINED" and assessment["outcome"] != "UNDETERMINED"
    )
    findings = []
    for notice in action.get("plan_findings", []):
        if not isinstance(notice, dict):
            continue
        findings.append(
            {
                "status": "REVIEW",
                "code": f"plan.{notice.get('code', 'notice').casefold()}",
                "reason": str(notice.get("message") or "Tracking-plan evidence is incomplete."),
                "path": notice.get("field"),
                "expected": notice.get("expected"),
                "observed": notice.get("observed"),
                "evidence_refs": notice.get("source_refs", []),
            }
        )
    if assessment["target_match"] == "MISMATCH":
        findings.append(
            {
                "status": "FAIL",
                "code": "reality.target_mismatch",
                "reason": assessment["summary"],
                "expected": "tracking-plan interaction target",
                "observed": assessment["target_match"],
            }
        )
    if assessment["outcome"] == "UNEXPECTED":
        findings.append(
            {
                "status": "FAIL",
                "code": "reality.unexpected_outcome",
                "reason": assessment["summary"],
                "expected": "expected visible outcome",
                "observed": assessment["anomaly_codes"],
            }
        )
    return {
        "complete": action_executed and determined,
        "attributable": action_executed,
        "reason": None
        if action_executed and determined
        else str(action.get("reason") or assessment["summary"]),
        "page": {
            "url": after.get("url") or action.get("target_url"),
            "target_source": action.get("target_source"),
            "setup_action_count": action.get("setup_action_count", 0),
            "reachable": bool(after.get("url")),
            "soft_404": "VISIBLE_ERROR" in assessment["anomaly_codes"],
            "before_aria_snapshot": before.get("aria_snapshot"),
            "after_aria_snapshot": after.get("aria_snapshot"),
            "before_screenshot": before.get("screenshot_path"),
            "after_screenshot": after.get("screenshot_path"),
        },
        "outcome": True
        if assessment["outcome"] == "EXPECTED"
        else False
        if assessment["outcome"] == "UNEXPECTED"
        else None,
        "expected": assessment["observed_values"],
        "findings": findings,
        "visual_assessment": assessment,
    }
