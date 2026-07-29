#!/usr/bin/env python3
"""Scan normalized client-side evidence for redacted sensitive-data findings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from client_side_rules import (
    DEFAULT_FORBIDDEN_CATEGORIES,
    scan_requirement_sensitive_data,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Normalized schema-v2 recette JSON.")
    parser.add_argument("--policy", type=Path, help="Optional sensitive-data policy JSON.")
    parser.add_argument("--output", type=Path, help="Optional redacted result JSON.")
    return parser.parse_args()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def main() -> int:
    args = parse_args()
    try:
        data = load_object(args.input)
        policy_override = load_object(args.policy) if args.policy else None
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    requirements = data.get("requirements")
    if not isinstance(requirements, list):
        print("ERROR: input must contain a requirements array.", file=sys.stderr)
        return 2
    findings: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        expectation = requirement.get("expectation")
        declared_policy = (
            expectation.get("sensitive_data_policy") if isinstance(expectation, dict) else None
        )
        policy = policy_override or (
            declared_policy
            if isinstance(declared_policy, dict)
            else {"forbidden_categories": DEFAULT_FORBIDDEN_CATEGORIES}
        )
        for finding in scan_requirement_sensitive_data(requirement, policy):
            finding["requirement_id"] = requirement.get("requirement_id")
            findings.append(finding)
    status = (
        "FAIL"
        if any(item["status"] == "FAIL" for item in findings)
        else "REVIEW"
        if any(item["status"] == "REVIEW" for item in findings)
        else "PASS"
    )
    output = {
        "status": status,
        "policy_source": str(args.policy) if args.policy else "per_requirement_or_default",
        "finding_count": len(findings),
        "findings": findings,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Created {args.output.resolve()}")
    else:
        print(rendered, end="")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
