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
SEMVER_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
CALVER_PATTERN = re.compile(
    r"(?:19|20)\d{2}\.(?:0?[1-9]|1[0-2])\.(?:0?[1-9]|[12]\d|3[01])"
)
NORTH_STAR = (
    "Execute an expert, tracking-plan-led GTM recette on the actual test website, "
    "covering every planned event in its original order. Use supplied URLs, screenshots, "
    "and journeys when available; otherwise identify and execute the relevant website "
    "interactions. For every event, use GTM Preview to compare the tracking-plan "
    "expectation with the exact live dataLayer.push payload, its variables, values and "
    "types, the resolved GTM variables, the expected tag firing or non-firing behaviour, "
    "and every required runtime tag parameter and value. Complete ordinary and "
    "authentication-gated journeys with safe synthetic data whenever possible, requesting "
    "analyst intervention only at protected, consequential, or genuinely ambiguous "
    "boundaries. Return an immediate, evidence-backed verdict and precise reason for each "
    "event, omit nothing silently, and finish with a complete plan-ordered status summary "
    "and validated detailed workbook."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = str(project["version"])
    expected_tag = f"v{version}"
    errors: list[str] = []
    if not SEMVER_PATTERN.fullmatch(version):
        errors.append(
            "project version must use MAJOR.MINOR.PATCH metadata; "
            "release tags and archives add the leading v"
        )
    if CALVER_PATTERN.fullmatch(version):
        errors.append("calendar-date versions are forbidden; use semantic v-versioning")
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
    normalized_skill = " ".join(skill.split())
    if NORTH_STAR not in normalized_skill:
        errors.append("SKILL.md does not contain the exact approved north star")
    for required_file in (
        "scripts/recette_schema.py",
        "scripts/inspect_tracking_plan.py",
        "scripts/init_coverage_ledger.py",
        "scripts/preview_session_ledger.py",
        "references/03-judgement/schema-v2.md",
        "references/02-execution/journey-inference-and-coverage.md",
    ):
        if not (ROOT / required_file).is_file():
            errors.append(f"skill is missing required execution resource: {required_file}")

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Release checks passed for {expected_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
