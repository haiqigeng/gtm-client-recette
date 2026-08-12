#!/usr/bin/env python3
"""Build a discovery-only retest manifest from current non-PASS event results."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from event_feedback import event_feedback
from state_io import recover_file_pair

RETEST_STATUSES = {"FAIL", "BLOCKED", "REVIEW"}


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def build_manifest(data: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    feedback = {
        str(row.get("event_group_id")): row
        for row in event_feedback(data, session)
        if row.get("status") in RETEST_STATUSES
    }
    requirements_by_group: dict[str, list[dict[str, Any]]] = {}
    for requirement in data.get("requirements", []):
        if isinstance(requirement, dict):
            requirements_by_group.setdefault(str(requirement.get("event_group_id", "")), []).append(
                requirement
            )
    cases: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    for source_case in session.get("cases", []):
        if not isinstance(source_case, dict):
            continue
        group_id = str(source_case.get("event_group_id", ""))
        if group_id not in feedback or source_case.get("scope_status") != "IN_SCOPE":
            continue
        cases.append(
            {
                "case_id": f"RETEST-{source_case.get('case_id')}",
                "source_case_id": source_case.get("case_id"),
                "event_group_id": group_id,
                "url": source_case.get("url"),
                "element": source_case.get("element"),
                "placement": source_case.get("placement"),
                "action": source_case.get("action"),
                "material_variant": source_case.get("material_variant") or {},
                "discovered_from": "prior_run",
                "previous_status": feedback[group_id]["status"],
                "retest_reason": feedback[group_id].get("reason"),
                "execution_status": "PENDING",
                "authorization_ids": [],
            }
        )
    groups_with_cases = {str(row["event_group_id"]) for row in cases}
    for group_id, row in feedback.items():
        if group_id in groups_with_cases:
            continue
        requirements = requirements_by_group.get(group_id, [])
        if not requirements:
            continue
        journey = requirements[0].get("journey") or {}
        element = journey.get("selector_or_element") or journey.get("action")
        missing = [
            field
            for field, value in (
                ("url", journey.get("url")),
                ("element", element),
                ("action", journey.get("action")),
            )
            if value in (None, "")
        ]
        if missing:
            limitations.append(
                {
                    "event_group_id": group_id,
                    "previous_status": row["status"],
                    "reason": "Retest discovery is incomplete: " + ", ".join(missing),
                }
            )
            continue
        cases.append(
            {
                "case_id": f"RETEST-{group_id}",
                "source_case_id": None,
                "event_group_id": group_id,
                "url": journey.get("url"),
                "element": element,
                "placement": "tracking-plan journey",
                "action": journey.get("action"),
                "material_variant": {},
                "discovered_from": "prior_run",
                "previous_status": row["status"],
                "retest_reason": row.get("reason"),
                "execution_status": "PENDING",
                "authorization_ids": [],
            }
        )
    run = data.get("run", {})
    return {
        "contract_version": 1,
        "artifact_type": "gtm_recette_retest_manifest",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_run_id": run.get("run_id"),
        "tracking_plan_source": run.get("tracking_plan_source"),
        "container_id": run.get("container_id"),
        "verdicts_inherited": False,
        "evidence_inherited": False,
        "instruction": (
            "Reuse discovery and journey instructions only. Execute every case again and "
            "produce new direct evidence before assigning any verdict."
        ),
        "cases": cases,
        "limitations": limitations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("session", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        recover_file_pair(args.results, args.session)
        manifest = build_manifest(load_object(args.results), load_object(args.session))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        f"Created {args.output.resolve()} with {len(manifest['cases'])} retest case(s) "
        f"and {len(manifest['limitations'])} explicit limitation(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
