#!/usr/bin/env python3
"""Evaluate allowlisted cross-field rules declared by normalized recette requirements."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from client_side_rules import evaluate_report_business_rules


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Normalized schema-v2 recette JSON.")
    parser.add_argument("--output", type=Path, help="Optional JSON result path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print("ERROR: input must be a JSON object.", file=sys.stderr)
        return 2
    results = evaluate_report_business_rules(data)
    output = {
        "result_count": len(results),
        "status": (
            "FAIL"
            if any(item["status"] == "FAIL" for item in results)
            else "REVIEW"
            if any(item["status"] == "REVIEW" for item in results)
            else "PASS"
        ),
        "results": results,
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Created {args.output.resolve()}")
    else:
        print(rendered, end="")
    return 1 if output["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
