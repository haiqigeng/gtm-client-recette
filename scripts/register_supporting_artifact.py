#!/usr/bin/env python3
"""Register an Audit or Configuration artifact as supporting-only recette context."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from path_safety import ensure_distinct_output, ensure_distinct_paths
from state_io import atomic_write_json, load_json_object
from supporting_artifacts import (
    ARTIFACT_CONTRACT_VERSION,
    SUPPORTING_ARTIFACT_TYPES,
    SUPPORTING_SOURCE_SKILLS,
    validate_supporting_artifacts,
)


def load_object(path: Path) -> dict[str, Any]:
    return load_json_object(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument(
        "--artifact-type",
        choices=tuple(sorted(SUPPORTING_ARTIFACT_TYPES)),
        required=True,
    )
    parser.add_argument(
        "--source-skill",
        choices=tuple(sorted(SUPPORTING_SOURCE_SKILLS)),
        required=True,
    )
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--notes", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        destination = args.output or args.ledger
        ensure_distinct_paths(args.ledger, args.artifact)
        ensure_distinct_output(destination, args.artifact, label="artifact ledger output")
        data = load_object(args.ledger)
        raw = args.artifact.read_bytes()
        run = data.get("run")
        if not isinstance(run, dict):
            raise ValueError("Normalized ledger run must be an object.")
        artifacts = run.setdefault("supporting_artifacts", [])
        if not isinstance(artifacts, list):
            raise ValueError("run.supporting_artifacts must be an array.")
        if any(
            isinstance(row, dict) and row.get("artifact_id") == args.artifact_id
            for row in artifacts
        ):
            raise ValueError(f"Duplicate artifact_id: {args.artifact_id}")
        artifacts.append(
            {
                "contract_version": ARTIFACT_CONTRACT_VERSION,
                "artifact_id": args.artifact_id,
                "artifact_type": args.artifact_type,
                "source_skill": args.source_skill,
                "source_run_id": args.source_run_id,
                "source_version": args.source_version,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "file_name": args.artifact.name,
                "role": "supporting_only",
                "verdict_authority": False,
                "registered_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "notes": args.notes.strip() or None,
            }
        )
        errors = validate_supporting_artifacts(artifacts)
        if errors:
            raise ValueError("\n".join(errors))
        atomic_write_json(destination, data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "registered": args.artifact_id,
                "role": "supporting_only",
                "verdict_authority": False,
                "output": str(destination.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
