#!/usr/bin/env python3
"""Validate release metadata and reject sensitive or generated artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".xlsx", ".log", ".png", ".jpg", ".jpeg"}
FORBIDDEN_NAMES = {"normalized-results.json", "__pycache__"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected_tag = f"v{project['version']}"
    errors: list[str] = []
    if args.tag and args.tag != expected_tag:
        errors.append(f"tag {args.tag!r} does not match project version {expected_tag!r}")

    if (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        tracked_candidates = [ROOT / line for line in result.stdout.splitlines() if line]
    else:
        tracked_candidates = [path for path in ROOT.rglob("*") if path.is_file()]
    for path in tracked_candidates:
        relative = path.relative_to(ROOT)
        if any(part in {".git", "dist", ".venv"} for part in relative.parts):
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or FORBIDDEN_NAMES.intersection(relative.parts):
            errors.append(f"release tree contains forbidden artifact: {relative}")

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for required in ("01-orientation", "02-execution", "03-judgement"):
        if required not in skill:
            errors.append(f"SKILL.md does not route to {required}")
    if "observation mode" in skill.lower():
        errors.append("SKILL.md must not introduce observation mode")
    if not re.search(r"name:\s*gtm-preview-recette", skill):
        errors.append("SKILL.md has an invalid skill name")

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Release checks passed for {expected_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
