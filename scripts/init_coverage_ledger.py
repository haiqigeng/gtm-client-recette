#!/usr/bin/env python3
"""Create a plan-ordered schema-v2 coverage ledger from interpreted requirements."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from layer_contract import CANONICAL_LAYERS, applicable_layers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", type=Path, help="Interpreted requirement JSON.")
    parser.add_argument("output", type=Path, help="Destination working ledger JSON.")
    parser.add_argument("--run-id", required=True)
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
    parser.add_argument(
        "--additional-container",
        action="append",
        default=[],
        metavar="ID|WORKSPACE|ROLE",
        help="Additional client-side container; ROLE is analytics, marketing, or shared.",
    )
    parser.add_argument("--browser-context-id", default="desktop-default")
    parser.add_argument(
        "--device-class",
        choices=("desktop", "mobile", "tablet", "responsive"),
        default="desktop",
    )
    parser.add_argument("--viewport-width", type=int, default=1440)
    parser.add_argument("--viewport-height", type=int, default=900)
    parser.add_argument("--tracking-plan-source", required=True)
    parser.add_argument("--acceptance-scope", required=True)
    parser.add_argument(
        "--included-layer",
        action="append",
        default=[],
        choices=tuple(CANONICAL_LAYERS),
        help=(
            "Additional accepted evidence layer. Applicable layers are inferred "
            "from the requirements; this option may be repeated."
        ),
    )
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
    journey.setdefault("action_value", None)
    journey.setdefault("action_value_type", "null")
    journey.setdefault("action_value_source", "not_applicable")
    journey.setdefault("inferred", False)
    journey.setdefault("inference_source", None)
    journey.setdefault("confidence", "confirmed")
    journey.setdefault("attempted_routes", [])
    journey["execution_status"] = "PENDING"
    requirement["journey"] = journey
    expectation = dict(requirement["expectation"])
    expectation.setdefault(
        "sensitive_data_policy",
        {
            "forbidden_categories": [
                "email",
                "phone",
                "postal_address",
                "person_name",
                "ip_address",
                "sensitive_query_parameter",
            ],
            "allowlisted_paths": [],
        },
    )
    expectation.setdefault("source_mechanism", "data_layer_push")
    requirement["expectation"] = expectation
    has_destination = "destination_request_when_applicable" in applicable_layers([requirement])
    requirement.update(
        {
            "browser_context_id": requirement.get("browser_context_id", "desktop-default"),
            "event_observed": False,
            "occurrence_evidence": None,
            "action_boundary": None,
            "raw_api_call": None,
            "source_signal": None,
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
            "destination_request": None,
            "trigger_evaluation": None,
            "tag_sequence": None,
            "consent": {
                "applicable": (
                    expectation.get("expected_consent_state") not in (None, "")
                    or expectation.get("consent_contract") is not None
                ),
                "source": "not_in_scope",
            },
            "business_rule_results": [],
            "sensitive_data_scan": (
                {
                    "applicable": True,
                    "scanned_targets": [],
                    "findings": [],
                    "status": "PENDING",
                    "evidence_id": None,
                }
                if expectation.get("sensitive_data_policy")
                else None
            ),
            "client_checks": [],
            "regression": None,
            "verdict": {
                "event_occurrence": "PENDING",
                "source_signal": (
                    "PENDING" if expectation.get("source_mechanism") != "data_layer_push" else None
                ),
                "raw_payload": "PENDING",
                "resolved_data_layer": "PENDING",
                "gtm_variable": "PENDING" if expectation.get("variable_name") else None,
                "tag_configuration": ("PENDING" if expectation.get("tag_name") else None),
                "tag_firing": "PENDING" if expectation.get("tag_name") else None,
                "tag_parameter": (
                    "PENDING" if expectation.get("tag_configuration_field") else None
                ),
                "destination_request": "PENDING" if has_destination else None,
                "destination_parameter": (
                    "PENDING" if expectation.get("destination_parameter_path") else None
                ),
                "trigger_logic": ("PENDING" if expectation.get("trigger_contract") else None),
                "tag_sequence": ("PENDING" if expectation.get("sequence_contract") else None),
                "consent": (
                    "PENDING"
                    if (
                        expectation.get("expected_consent_state") not in (None, "")
                        or expectation.get("consent_contract") is not None
                    )
                    else None
                ),
                "business_rule": ("PENDING" if expectation.get("business_rules") else None),
                "sensitive_data": ("PENDING" if expectation.get("sensitive_data_policy") else None),
                "client_checks": None,
                "regression": None,
                "overall": "PENDING",
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
    containers = [
        {
            "container_id": args.container_id,
            "workspace": args.workspace,
            "role": "primary",
            "container_type": "web",
        }
    ]
    for value in args.additional_container:
        parts = [part.strip() for part in value.split("|")]
        if len(parts) != 3 or parts[2] not in {"analytics", "marketing", "shared"}:
            raise ValueError(
                "--additional-container must use ID|WORKSPACE|ROLE with a supported role"
            )
        containers.append(
            {
                "container_id": parts[0],
                "workspace": parts[1],
                "role": parts[2],
                "container_type": "web",
            }
        )
    if args.viewport_width <= 0 or args.viewport_height <= 0:
        raise ValueError("Viewport dimensions must be positive integers.")
    included_layers = applicable_layers(
        requirements,
        container_count=len(containers),
    )
    for layer in args.included_layer:
        if layer not in included_layers:
            included_layers.append(layer)
    included_layers.sort(key=CANONICAL_LAYERS.index)
    result = {
        "schema_version": 2,
        "run": {
            "run_id": args.run_id,
            "report_title": args.title,
            "client": args.client,
            "site_url": args.site_url,
            "environment": args.environment,
            "environment_class": args.environment_class,
            "container_id": args.container_id,
            "workspace": args.workspace,
            "containers": containers,
            "browser_contexts": [
                {
                    "context_id": args.browser_context_id,
                    "device_class": args.device_class,
                    "viewport": {
                        "width": args.viewport_width,
                        "height": args.viewport_height,
                    },
                    "user_state": "anonymous",
                    "variant": "default",
                }
            ],
            "tracking_plan_source": args.tracking_plan_source,
            "acceptance_scope": args.acceptance_scope,
            "executed_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "included_layers": included_layers,
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
