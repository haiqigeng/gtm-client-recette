#!/usr/bin/env python3
"""Create an exhaustive per-call review from a dataLayer recorder snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from evidence_contract import capture_limitation_markers
from path_safety import ensure_distinct_paths
from state_io import atomic_write_json, load_json_object


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("snapshot", type=Path)
    root.add_argument("output", type=Path)
    root.add_argument("--segment-id", required=True)
    root.add_argument("--start-exclusive", type=int, required=True)
    root.add_argument("--end-inclusive", type=int, required=True)
    root.add_argument("--evidence-id", required=True)
    root.add_argument("--expected-run-id", required=True)
    return root


def _event_name(value: Any) -> str:
    return value if isinstance(value, str) else ""


def classify_argument(value: Any, argument_index: int) -> dict[str, Any]:
    """Return a conservative draft classification for one push argument."""
    limitations = capture_limitation_markers(value)
    event_present = isinstance(value, dict) and "event" in value
    event_name = _event_name(value.get("event")) if isinstance(value, dict) else ""
    if event_present:
        disposition = "TECHNICAL_EVENT" if event_name.startswith("gtm.") else "BUSINESS_EVENT"
        reason = (
            "GTM lifecycle event identified directly from the recorder payload."
            if disposition == "TECHNICAL_EVENT"
            else "Custom event field requires mapping to a classified business push."
        )
    elif isinstance(value, dict):
        disposition = "STATE_UPDATE"
        reason = "Object updates dataLayer state without a top-level event field."
    else:
        disposition = "NON_EVENT"
        reason = "Non-object push argument has no top-level event field."
    return {
        "argument_index": argument_index,
        "event_field_present": event_present,
        "event_name": event_name or None,
        "disposition": disposition,
        "push_id": None,
        "capture_complete": not limitations,
        "capture_limitations": limitations,
        "reason": reason,
    }


def build_review(
    snapshot: dict[str, Any],
    *,
    segment_id: str,
    start_exclusive: int,
    end_inclusive: int,
    evidence_id: str,
    expected_run_id: str,
) -> dict[str, Any]:
    if snapshot.get("runId") != expected_run_id:
        raise ValueError(
            "Recorder snapshot runId differs from the current run; dispose or beginRun "
            "before collecting evidence."
        )
    if start_exclusive < 0 or end_inclusive < start_exclusive:
        raise ValueError("Invalid call-index interval.")
    records = snapshot.get("records")
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise ValueError("Recorder snapshot records must be an object array.")
    by_index = {row.get("callIndex"): row for row in records}
    expected = list(range(start_exclusive + 1, end_inclusive + 1))
    missing = [index for index in expected if index not in by_index]
    if missing:
        raise ValueError(
            "Recorder snapshot omits required call indexes: " + ", ".join(map(str, missing[:20]))
        )
    reviews: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for call_index in expected:
        record = by_index[call_index]
        arguments = record.get("arguments")
        if not isinstance(arguments, list):
            raise ValueError(f"Recorder call {call_index} arguments are unreadable.")
        classified = [
            classify_argument(argument, argument_index)
            for argument_index, argument in enumerate(arguments)
        ]
        for argument in classified:
            if argument["disposition"] == "BUSINESS_EVENT":
                unresolved.append(
                    {
                        "call_index": call_index,
                        "argument_index": argument["argument_index"],
                        "event_name": argument["event_name"],
                        "required_action": "Create/classify a business_push and set its push_id here.",
                    }
                )
        reviews.append(
            {
                "call_index": call_index,
                "evidence_id": evidence_id,
                "timestamp": record.get("timestamp"),
                "url": record.get("url"),
                "action_id_at_call": record.get("actionId"),
                "arguments": classified,
                "reason": (
                    "No arguments were passed to dataLayer.push."
                    if not classified
                    else "Every push argument was classified from the direct recorder snapshot."
                ),
            }
        )
    return {
        "artifact_type": "gtm_recette_datalayer_call_review",
        "version": 2,
        "run_id": expected_run_id,
        "segment_id": segment_id,
        "start_datalayer_call_index": start_exclusive,
        "end_datalayer_call_index": end_inclusive,
        "datalayer_call_reviews": reviews,
        "unresolved_business_events": unresolved,
        "ready_for_final": not unresolved
        and all(
            argument.get("capture_complete") is True
            for review in reviews
            for argument in review["arguments"]
        ),
    }


def main() -> int:
    args = parser().parse_args()
    ensure_distinct_paths(args.snapshot, args.output)
    snapshot = load_json_object(args.snapshot)
    output = build_review(
        snapshot,
        segment_id=args.segment_id,
        start_exclusive=args.start_exclusive,
        end_inclusive=args.end_inclusive,
        evidence_id=args.evidence_id,
        expected_run_id=args.expected_run_id,
    )
    atomic_write_json(args.output, output)
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
