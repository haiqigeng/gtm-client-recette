#!/usr/bin/env python3
"""Create a plan-ordered schema-v2 coverage ledger from interpreted requirements."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANONICAL_LAYERS = [
    "raw_api_call",
    "resolved_data_layer",
    "gtm_variable",
    "tag_configuration",
    "tag_firing",
    "tag_parameter",
    "consent_when_applicable",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", type=Path, help="Interpreted requirement JSON.")
    parser.add_argument("output", type=Path, help="Destination working ledger JSON.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-type", default="FULL_TRACKING_PLAN_RECETTE")
    parser.add_argument("--title", required=True)
    parser.add_argument("--site-url", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument(
        "--environment-class",
        required=True,
        choices=("test", "preprod", "staging", "production"),
    )
    parser.add_argument("--container-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--tracking-plan-source", required=True)
    parser.add_argument("--acceptance-scope", required=True)
    parser.add_argument("--client", default="")
    return parser.parse_args()


def load_requirements(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("requirements")
    if not isinstance(value, list) or not value:
        raise ValueError("Interpreted input must contain a non-empty requirements array.")
    requirements = []
    for index, row in enumerate(value, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Requirement row {index} must be an object.")
        for field in ("requirement_id", "event_group_id", "source", "expectation", "journey"):
            if field not in row:
                raise ValueError(f"Requirement row {index} is missing '{field}'.")
        requirements.append(row)
    return requirements


def initialize_requirement(row: dict[str, Any]) -> dict[str, Any]:
    requirement = dict(row)
    requirement.setdefault("scope_status", "IN_SCOPE")
    journey = dict(requirement["journey"])
    journey.setdefault("selector_or_element", "")
    journey.setdefault("inferred", False)
    journey.setdefault("inference_source", None)
    journey.setdefault("confidence", "confirmed")
    journey.setdefault("attempted_routes", [])
    journey["execution_status"] = "PENDING"
    requirement["journey"] = journey
    expectation = requirement["expectation"]
    requirement.update(
        {
            "event_observed": False,
            "occurrence_evidence": None,
            "action_boundary": None,
            "raw_api_call": None,
            "resolved_data_layer": None,
            "gtm_variable": {
                "applicable": bool(expectation.get("variable_name")),
                "name": expectation.get("variable_name"),
            },
            "tag": {
                "applicable": bool(expectation.get("tag_name")),
                "name": expectation.get("tag_name"),
                "relevance": (
                    "expected_fire"
                    if expectation.get("expected_firing") in {"fired", "fired_once"}
                    else "expected_block"
                ),
            },
            "consent": {
                "applicable": expectation.get("expected_consent_state") not in (None, ""),
                "source": "not_in_scope",
            },
            "verdict": {
                "event_occurrence": "REVIEW",
                "raw_payload": "REVIEW",
                "resolved_data_layer": "REVIEW",
                "gtm_variable": "REVIEW" if expectation.get("variable_name") else None,
                "tag_firing": "REVIEW" if expectation.get("tag_name") else None,
                "tag_parameter": (
                    "REVIEW" if expectation.get("tag_configuration_field") else None
                ),
                "consent": (
                    "REVIEW"
                    if expectation.get("expected_consent_state") not in (None, "")
                    else None
                ),
                "overall": "REVIEW",
                "failure_layer": None,
                "mismatch": "Pending execution",
                "reason_source": None,
            },
            "evidence_ids": [],
            "notes": "Pending execution",
        }
    )
    return requirement


def event_inventory(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        group_id = str(requirement["event_group_id"])
        source = requirement["source"]
        expectation = requirement["expectation"]
        if group_id not in events:
            events[group_id] = {
                "event_group_id": group_id,
                "event_name": expectation["event_name"],
                "plan_order": source["plan_order"],
            }
    return sorted(events.values(), key=lambda item: item["plan_order"])


def main() -> int:
    args = parse_args()
    requirements = [
        initialize_requirement(row)
        for row in sorted(
            load_requirements(args.requirements),
            key=lambda item: item["source"]["plan_order"],
        )
    ]
    result = {
        "schema_version": 2,
        "run": {
            "run_id": args.run_id,
            "run_type": args.run_type,
            "report_title": args.title,
            "client": args.client,
            "site_url": args.site_url,
            "environment": args.environment,
            "environment_class": args.environment_class,
            "container_id": args.container_id,
            "workspace": args.workspace,
            "tracking_plan_source": args.tracking_plan_source,
            "acceptance_scope": args.acceptance_scope,
            "executed_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "included_layers": CANONICAL_LAYERS,
            "requirement_inventory": [row["requirement_id"] for row in requirements],
            "event_inventory": event_inventory(requirements),
        },
        "requirements": requirements,
        "unexpected": [],
        "blockers": [],
        "evidence": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
