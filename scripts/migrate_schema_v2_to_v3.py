#!/usr/bin/env python3
"""Migrate v2 discovery context to schema v3 without inheriting proof or verdicts."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from init_coverage_ledger import event_inventory, initialize_requirement
from layer_contract import CANONICAL_LAYERS, applicable_layers, normalize_tag_scope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy_results", type=Path)
    parser.add_argument("output_results", type=Path)
    parser.add_argument("--legacy-session", type=Path)
    parser.add_argument("--case-manifest", type=Path)
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def migrate_results(legacy: dict[str, Any]) -> dict[str, Any]:
    """Preserve accepted discovery/order and reset every runtime proof surface."""
    if legacy.get("schema_version") != 2:
        raise ValueError("Only normalized schema-v2 results can use this migration.")
    run = deepcopy(legacy.get("run"))
    if not isinstance(run, dict):
        raise ValueError("Legacy run must be an object.")
    source_requirements = legacy.get("requirements")
    if not isinstance(source_requirements, list) or any(
        not isinstance(row, dict) for row in source_requirements
    ):
        raise ValueError("Legacy requirements must be an array of objects.")
    requirements: list[dict[str, Any]] = []
    for source in source_requirements:
        reset = initialize_requirement(deepcopy(source))
        reset.pop("blocker_id", None)
        scenario = reset.get("scenario")
        if isinstance(scenario, dict):
            scenario.pop("evidence_id", None)
            scenario.pop("condition_met", None)
        reset["notes"] = "Pending fresh schema-v3 capture; no prior proof was inherited."
        requirements.append(reset)
    containers = [row for row in run.get("containers", []) if isinstance(row, dict)]
    included = applicable_layers(requirements, container_count=len(containers) or 1)
    included.sort(key=CANONICAL_LAYERS.index)
    run.update(
        {
            "tag_scope": normalize_tag_scope(run.get("tag_scope")),
            "included_layers": included,
            "requirement_inventory": [row.get("requirement_id") for row in requirements],
            "event_inventory": event_inventory(requirements),
            "executed_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "schema_migration": {
                "from_schema": 2,
                "to_schema": 3,
                "verdicts_inherited": False,
                "evidence_inherited": False,
                "discovery_context_preserved": True,
            },
        }
    )
    run.pop("regression_context", None)
    return {
        "schema_version": 3,
        "run": run,
        "requirements": requirements,
        "unexpected": [],
        "blockers": [],
        "evidence": [],
    }


def migration_case_manifest(legacy_session: dict[str, Any]) -> dict[str, Any]:
    """Return importable prior-case discovery only; actions and proof stay excluded."""
    cases = []
    limitations = []
    for index, case in enumerate(legacy_session.get("cases", []), start=1):
        if not isinstance(case, dict):
            continue
        required = ("case_id", "event_group_id", "url", "element", "placement", "action")
        missing = [field for field in required if case.get(field) in (None, "")]
        if missing:
            limitations.append(
                {
                    "case_index": index,
                    "event_group_id": case.get("event_group_id"),
                    "missing_fields": missing,
                }
            )
            continue
        cases.append(
            {
                "case_id": case.get("case_id"),
                "event_group_id": case.get("event_group_id"),
                "url": case.get("url"),
                "element": case.get("element"),
                "placement": case.get("placement"),
                "action": case.get("action"),
                "material_variant": deepcopy(case.get("material_variant", {})),
                "execution_status": "PENDING",
                "authorization_ids": [],
            }
        )
    return {
        "artifact_type": "gtm_recette_retest_manifest",
        "source_schema_version": legacy_session.get("schema_version"),
        "verdicts_inherited": False,
        "evidence_inherited": False,
        "cases": cases,
        "limitations": limitations,
    }


def main() -> int:
    args = parse_args()
    migrated = migrate_results(load_object(args.legacy_results))
    args.output_results.parent.mkdir(parents=True, exist_ok=True)
    args.output_results.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if bool(args.legacy_session) != bool(args.case_manifest):
        raise ValueError("Use --legacy-session and --case-manifest together.")
    if args.legacy_session and args.case_manifest:
        manifest = migration_case_manifest(load_object(args.legacy_session))
        args.case_manifest.parent.mkdir(parents=True, exist_ok=True)
        args.case_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Created {args.output_results.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
