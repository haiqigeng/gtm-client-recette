#!/usr/bin/env python3
"""Compare normalized recette runs and identify requirement-level regressions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from recette_schema import VALID_STATUSES, status_of


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path, help="Previously validated normalized JSON.")
    parser.add_argument("current", type=Path, help="Current validated normalized JSON.")
    parser.add_argument("--output", type=Path, help="Optional regression JSON path.")
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("requirements"), list):
        raise ValueError(f"{path} is not a normalized recette report.")
    return value


def comparison_key(requirement: dict[str, Any]) -> str:
    requirement_id = str(requirement.get("requirement_id", "")).strip()
    if requirement_id:
        return requirement_id
    source = requirement.get("source")
    if isinstance(source, dict):
        return str(source.get("reference", "")).strip()
    return ""


def status(requirement: dict[str, Any] | None) -> str | None:
    if requirement is None:
        return None
    value = status_of(requirement.get("verdict", {}).get("overall"))
    return value if value in VALID_STATUSES else None


def compare(baseline: dict[str, Any], current: dict[str, Any]) -> list[dict[str, Any]]:
    baseline_rows = {
        comparison_key(row): row
        for row in baseline["requirements"]
        if isinstance(row, dict) and comparison_key(row)
    }
    current_rows = {
        comparison_key(row): row
        for row in current["requirements"]
        if isinstance(row, dict) and comparison_key(row)
    }
    keys = list(current_rows)
    keys.extend(key for key in baseline_rows if key not in current_rows)
    results: list[dict[str, Any]] = []
    for key in keys:
        previous = status(baseline_rows.get(key))
        now = status(current_rows.get(key))
        if previous is None:
            change = "NEW"
        elif now is None:
            change = "REMOVED"
        elif previous == now:
            change = "UNCHANGED"
        elif previous == "PASS" and now == "FAIL":
            change = "REGRESSED"
        elif previous == "PASS" and now in {"BLOCKED", "REVIEW", "NOT_TESTED"}:
            change = "UNVERIFIED"
        elif previous != "PASS" and now == "PASS":
            change = "IMPROVED"
        else:
            change = "CHANGED"
        results.append(
            {
                "requirement_id": key,
                "baseline_status": previous,
                "current_status": now,
                "change": change,
                "regression": change == "REGRESSED",
            }
        )
    return results


def main() -> int:
    args = parse_args()
    try:
        baseline = load_report(args.baseline)
        current = load_report(args.current)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    results = compare(baseline, current)
    output = {
        "baseline_run_id": baseline.get("run", {}).get("run_id"),
        "current_run_id": current.get("run", {}).get("run_id"),
        "regression_count": sum(item["regression"] for item in results),
        "results": results,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Created {args.output.resolve()}")
    else:
        print(rendered, end="")
    return 1 if output["regression_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
