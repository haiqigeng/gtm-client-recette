#!/usr/bin/env python3
"""Validate the exact v8 personal skill tree before release."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = {
    "judge.py",
    "playwright_collector.js",
    "recette.py",
    "report.py",
    "state.py",
    "xlsx_plan.py",
}
PACKAGING = {"build_skill_package.py", "check_release.py", "verify_release_artifact.py"}
COMMANDS = {"start", "next", "complete", "finish"}
LAYERS = (
    "Page/action reality",
    "Data Layer API Call",
    "GTM Tags",
    "Browser request",
    "Surrounding behavior",
)
VERSIONED = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
)
TEXT_SUFFIXES = {".md", ".py", ".js", ".toml", ".yaml", ".yml", ".json"}
ABSOLUTE_USER_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+", re.I)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    return parser.parse_args()


def error_if(condition: bool, message: str, errors: list[str]) -> None:
    if condition:
        errors.append(message)


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = str(project["version"])
    release = f"v{version}"
    error_if(version != "8.0.0", "pyproject version must be 8.0.0", errors)
    error_if(
        project.get("dependencies") != ["openpyxl>=3.1.2"],
        "runtime dependency set must contain only openpyxl",
        errors,
    )
    if args.tag:
        error_if(args.tag != release, f"tag must be {release}", errors)

    for relative in VERSIONED:
        text = (ROOT / relative).read_text(encoding="utf-8")
        error_if(release not in text, f"{relative} does not identify {release}", errors)
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    error_if(
        f"## [{release}]" not in changelog,
        f"CHANGELOG.md has no {release} section",
        errors,
    )

    scripts = {
        path.name
        for path in (ROOT / "scripts").iterdir()
        if path.is_file() and path.suffix in {".py", ".js"}
    }
    error_if(scripts != RUNTIME | PACKAGING, "scripts tree has missing or extra files", errors)
    error_if((ROOT / "references").exists(), "obsolete references directory remains", errors)
    error_if((ROOT / "scripts" / "core").exists(), "obsolete scripts/core remains", errors)
    docs = {path.name for path in (ROOT / "docs").glob("*.md")}
    error_if(
        docs != {"v8-design-and-verification.md"},
        "docs must contain only the consolidated v8 review",
        errors,
    )

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    error_if(len(skill.splitlines()) > 180, "SKILL.md exceeds the lean 180-line bound", errors)
    for phrase in (
        "exactly one `.xlsx`",
        "headed standalone Playwright MCP",
        "After two consecutive zero-evidence events",
        "Do not inspect the accumulated Data Layer tab",
    ):
        error_if(phrase not in skill, f"SKILL.md is missing {phrase!r}", errors)
    for layer in LAYERS:
        error_if(layer not in skill, f"SKILL.md is missing layer {layer!r}", errors)
    for forbidden in ("Firefox", "in-app browser", "YAML", "CSV", "reopen command"):
        error_if(
            forbidden.casefold() in skill.casefold(), f"SKILL.md contains {forbidden!r}", errors
        )

    cli = (ROOT / "scripts" / "recette.py").read_text(encoding="utf-8")
    commands = set(re.findall(r'add_parser\("([^"]+)"', cli))
    error_if(commands != COMMANDS, "runtime CLI differs from the exact four commands", errors)
    collector = (ROOT / "scripts" / "playwright_collector.js").read_text(encoding="utf-8")
    for required in ('const CONTRACT = "playwright-mcp-v8"', "const MAX_MS = 5000"):
        error_if(required not in collector, f"collector is missing {required!r}", errors)
    for forbidden in (
        'readPanel("Data Layer")',
        'readPanel("Variables")',
        "timeout_ms",
        "fallback",
    ):
        error_if(
            forbidden.casefold() in collector.casefold(),
            f"collector contains {forbidden!r}",
            errors,
        )

    agent = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
    for required in ("$gtm-client-recette", 'value: "playwright"'):
        error_if(required not in agent, f"agent metadata is missing {required!r}", errors)
    error_if("standalone" not in agent.casefold(), "agent metadata is missing 'standalone'", errors)

    runtime_lines = sum(
        len((ROOT / "scripts" / name).read_text(encoding="utf-8").splitlines()) for name in RUNTIME
    )
    ignored = {".git", ".ruff_cache", ".pytest_cache", "__pycache__", "dist", ".venv"}
    forbidden_directories = {"runs", "evidence", "backups", "screenshots", "quarantine"}
    forbidden_files = {"plan.json", "events.ndjson", "handoff-log.md"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in ignored for part in relative.parts):
            continue
        if path.is_dir():
            error_if(
                path.name.casefold() in forbidden_directories,
                f"run residue directory remains: {relative}",
                errors,
            )
            continue
        error_if(path.name in forbidden_files, f"run state remains: {relative}", errors)
        error_if(
            path.suffix.casefold() in {".xlsx", ".xls", ".zip", ".log", ".png", ".jpg"},
            f"run/output artifact remains: {relative}",
            errors,
        )
        if path.suffix.casefold() in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="ignore")
            error_if(
                ABSOLUTE_USER_PATH.search(text) is not None,
                f"user-bound absolute path remains: {relative}",
                errors,
            )

    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Fixed personal release checks passed for {release} ({runtime_lines} runtime lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
