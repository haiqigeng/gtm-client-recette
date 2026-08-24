#!/usr/bin/env python3
"""Validate the lean Playwright-first skill tree before packaging or release."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
REFERENCE_LINK = re.compile(r"\((references/[^)]+\.md)\)")
ADD_PARSER = re.compile(r"add_parser\(\s*[\"']([^\"']+)[\"']")

REQUIRED_REFERENCES = {
    "references/browser-and-preview.md",
    "references/protected-journeys.md",
    "references/scenario-coverage.md",
    "references/verdict-and-output.md",
}
REQUIRED_ROOT_SCRIPTS = {
    "client_side_rules.py",
    "datalayer_recorder.js",
    "decode_browser_requests.py",
    "dom_interaction_census.js",
    "generate_synthetic_profile.py",
    "import_ga4_tracking_plan_handoff.py",
    "path_safety.py",
    "recette.py",
    "safe_regex.py",
    "state_io.py",
    "tag_assistant_collector.js",
    "value_semantics.py",
}
REQUIRED_CORE_SCRIPTS = {
    "__init__.py",
    "capture.py",
    "constants.py",
    "correlate.py",
    "coverage.py",
    "judge.py",
    "plan.py",
    "predicates.py",
    "report.py",
    "state.py",
    "workflow.py",
}
REQUIRED_PROTOCOLS = {"__init__.py", "ads.py", "ga4.py"}
PACKAGING_SCRIPTS = {
    "build_skill_package.py",
    "check_release.py",
    "verify_release_artifact.py",
}
PUBLIC_COMMANDS = {
    "init",
    "next",
    "complete",
    "status",
    "handoff",
    "finish",
    "report",
    "reopen",
}
VERSIONED_METADATA = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
)
ACTIVE_GUIDES = (
    "SKILL.md",
    "README.md",
    "CONTRIBUTING.md",
    "agents/openai.yaml",
    *sorted(REQUIRED_REFERENCES),
)
FORBIDDEN_ACTIVE_TERMS = {
    "recette_operator.py",
    "preview_session_ledger.py",
    "operator_contract_version_required",
    "normalized-results.json",
    "schema-v3 session",
    "19 canonical rows",
    "nine reporting layers",
    "## V4 operating model",
}
ABSOLUTE_USER_PATH = re.compile(r"[a-z]:[\\/]+users[\\/]+", re.IGNORECASE)
FORBIDDEN_RUNTIME_SUFFIXES = {".xlsx", ".log", ".png", ".jpg", ".jpeg", ".zip"}
IGNORED_PARTS = {".git", "dist", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    parser.add_argument(
        "--live-pilot",
        type=Path,
        help="Optional sanitized Playwright MCP live-pilot result JSON.",
    )
    return parser.parse_args()


def validate_live_pilot(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read live pilot: {error}"]
    if not isinstance(value, dict):
        return ["live pilot root must be an object"]
    runtime = value.get("runtime", {})
    expected_runtime = {
        "provider": "playwright_mcp",
        "browser_channel": "msedge",
        "profile_mode": "persistent",
        "headed": True,
    }
    for key, expected in expected_runtime.items():
        if runtime.get(key) != expected:
            errors.append(f"live pilot runtime {key} must be {expected!r}")
    if runtime.get("self_check") is not None and runtime.get("self_check") != "PASS":
        errors.append("live pilot runtime self_check must be 'PASS' when supplied")
    surfaces = value.get("capabilities", {})
    for key in ("stable_target_identity", "network_deltas", "preview_events"):
        if surfaces.get(key) is not True:
            errors.append(f"live pilot capability {key} must be true")
    latency = value.get("latency_seconds", {})
    for key, limit in (("first_action", 120), ("first_feedback", 300)):
        observed = latency.get(key)
        if not isinstance(observed, (int, float)) or isinstance(observed, bool):
            errors.append(f"live pilot latency {key} is missing")
        elif observed > limit:
            errors.append(f"live pilot latency {key} exceeds {limit} seconds")
    operations = value.get("operations", {})
    zero_counters = (
        "unsupported_method_errors",
        "coordinate_actions",
        "ad_hoc_evidence_files",
        "unauthorized_reloads",
        "scope_restarts",
    )
    for key in zero_counters:
        if operations.get(key) != 0:
            errors.append(f"live pilot operations {key} must be zero")
    if operations.get("preview_passes_first_event") != 1:
        errors.append("live pilot must complete the first event in one Preview pass")
    quality = value.get("quality", {})
    required_quality = (
        "core_event_completed",
        "ordinary_event_completed",
        "mandatory_layers_complete",
        "continuous_anomaly_stream_complete",
        "per_event_feedback_emitted",
    )
    for key in required_quality:
        if quality.get(key) is not True:
            errors.append(f"live pilot quality {key} must be true")
    return errors


def check_metadata(requested_tag: str | None, errors: list[str]) -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if project.get("name") != "gtm-client-recette":
        errors.append("project name must be gtm-client-recette")
    version = str(project.get("version", ""))
    if not SEMVER.fullmatch(version):
        errors.append("project version must be MAJOR.MINOR.PATCH")
    tag = f"v{version}"
    if requested_tag and requested_tag != tag:
        errors.append(f"requested tag {requested_tag!r} does not match {tag!r}")
    for relative in VERSIONED_METADATA:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"{relative} is missing")
        elif tag not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative} is not aligned to {tag}")
    return tag


def check_skill(errors: list[str]) -> None:
    path = ROOT / "SKILL.md"
    if not path.is_file():
        errors.append("SKILL.md is missing")
        return
    skill = path.read_text(encoding="utf-8")
    if not skill.startswith("---\nname: gtm-client-recette\n"):
        errors.append("SKILL.md frontmatter name is invalid")
    if len(skill.splitlines()) > 240:
        errors.append("SKILL.md exceeds the 240-line progressive-disclosure budget")
    required_doctrine = (
        "measurement claim",
        "material scenario",
        "Playwright MCP",
        "managed Edge",
        "five layers",
        "Page/action reality",
        "Data Layer API Call",
        "GTM Tags",
        "Browser request",
        "Surrounding behavior",
        "Evidence confidence",
        "scenario coverage",
        "call-time dataLayer",
        "state-only dataLayer",
        "fully expanded Tag Assistant",
        "normal source authority",
        "structured retest basis",
        "playwright_completion.code",
        "partial evidence",
        "every destination-applicable planned field",
        "every intervening source/API message",
        "high-cardinality",
        "setup_boundary",
        "five-second pass",
        "per tested event",
        "deterministic renderer owns every",
    )
    lower_skill = skill.lower()
    for required in required_doctrine:
        if required.lower() not in lower_skill:
            errors.append(f"SKILL.md is missing required doctrine {required!r}")
    linked = set(REFERENCE_LINK.findall(skill))
    if linked != REQUIRED_REFERENCES:
        errors.append("SKILL.md reference routing differs from the exact four-guide set")


def check_runtime_tree(errors: list[str]) -> None:
    references = {path.relative_to(ROOT).as_posix() for path in (ROOT / "references").rglob("*.md")}
    if references != REQUIRED_REFERENCES:
        errors.append("references tree contains missing or stale guides")
    root_scripts = {path.name for path in (ROOT / "scripts").iterdir() if path.is_file()}
    missing = REQUIRED_ROOT_SCRIPTS - root_scripts
    unexpected = root_scripts - REQUIRED_ROOT_SCRIPTS - PACKAGING_SCRIPTS
    if missing:
        errors.append("missing runtime scripts: " + ", ".join(sorted(missing)))
    if unexpected:
        errors.append("unclassified root scripts: " + ", ".join(sorted(unexpected)))
    core_scripts = {path.name for path in (ROOT / "scripts" / "core").glob("*.py")}
    if core_scripts != REQUIRED_CORE_SCRIPTS:
        errors.append("scripts/core contains missing or unclassified modules")
    protocols = {path.name for path in (ROOT / "scripts" / "core" / "protocols").glob("*.py")}
    if protocols != REQUIRED_PROTOCOLS:
        errors.append("scripts/core/protocols contains missing or unclassified modules")
    capture_vocabulary = "\n".join(
        (ROOT / "scripts" / "core" / name).read_text(encoding="utf-8")
        for name in ("capture.py", "constants.py")
    )
    if "CAPTURE_DOM" in capture_vocabulary:
        errors.append("unused generic DOM evidence adapter is still present")
    for relative in ("agents/openai.yaml", "LICENSE"):
        if not (ROOT / relative).is_file():
            errors.append(f"missing runtime resource: {relative}")
    agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$gtm-client-recette" not in agent:
        errors.append("agent default prompt does not invoke the skill")
    collector = (ROOT / "scripts" / "tag_assistant_collector.js").read_text(encoding="utf-8")
    if not collector.startswith("(async (spec) =>"):
        errors.append("Tag Assistant collector is not a directly evaluable page function")
    for forbidden in ("module.exports", "requires_canonical_normalization", "require("):
        if forbidden in collector:
            errors.append(f"Tag Assistant collector contains stale handoff code {forbidden!r}")
    workflow = (ROOT / "scripts" / "core" / "workflow.py").read_text(encoding="utf-8")
    if '"playwright_completion"' not in workflow:
        errors.append("next does not return a paste-ready Playwright completion callback")


def check_active_docs(errors: list[str]) -> None:
    for relative in ACTIVE_GUIDES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        lower = text.lower()
        for forbidden in FORBIDDEN_ACTIVE_TERMS:
            if forbidden.lower() in lower:
                errors.append(f"{relative} contains stale architecture term {forbidden!r}")
        if ABSOLUTE_USER_PATH.search(text):
            errors.append(f"{relative} contains a user-bound absolute path")


def check_public_cli(errors: list[str]) -> None:
    source = (ROOT / "scripts" / "recette.py").read_text(encoding="utf-8")
    actual = set(ADD_PARSER.findall(source))
    if actual != PUBLIC_COMMANDS:
        errors.append(
            "public CLI command set differs from the Playwright-first contract: "
            f"missing={sorted(PUBLIC_COMMANDS - actual)}, extra={sorted(actual - PUBLIC_COMMANDS)}"
        )
    for forbidden in (
        'add_parser("append"',
        'add_parser("set-verdict"',
        'add_parser("set-layer"',
        "_append_machine(",
    ):
        if forbidden in source:
            errors.append(f"public CLI exposes forbidden mutation path {forbidden!r}")


def check_source_residue(errors: list[str]) -> None:
    forbidden_directories = {"runs", "evidence", "quarantine", "reports", "screenshots", "backups"}
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        if path.is_dir():
            if path.name.lower() in forbidden_directories:
                errors.append(f"source tree contains run/backup directory: {relative}")
            continue
        if path.suffix.lower() in FORBIDDEN_RUNTIME_SUFFIXES:
            errors.append(f"source tree contains run/output residue: {relative}")
        if path.name in {"plan.json", "stream.ndjson", "results.json", "handoff-log.md"}:
            errors.append(f"source tree contains run-bound state: {relative}")
        if path.suffix.lower() in {".py", ".js", ".md", ".yaml", ".yml", ".toml", ".json"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if ABSOLUTE_USER_PATH.search(text):
                errors.append(f"{relative} contains a user-bound absolute path")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    tag = check_metadata(args.tag, errors)
    check_skill(errors)
    check_runtime_tree(errors)
    check_active_docs(errors)
    check_public_cli(errors)
    check_source_residue(errors)
    if args.live_pilot is not None:
        errors.extend(validate_live_pilot(args.live_pilot))
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Playwright-first release checks passed for {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
