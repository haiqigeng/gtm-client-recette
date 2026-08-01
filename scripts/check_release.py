#!/usr/bin/env python3
"""Validate release metadata and reject sensitive or generated artifacts."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".xlsx", ".log", ".png", ".jpg", ".jpeg"}
FORBIDDEN_NAMES = {"normalized-results.json"}
SEMVER_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
CALVER_PATTERN = re.compile(r"(?:19|20)\d{2}\.(?:0?[1-9]|1[0-2])\.(?:0?[1-9]|[12]\d|3[01])")
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
SAFETY_CONTRACTS = {
    "references/02-execution/browser-session-and-readiness.md": ("## Adaptive settlement"),
    "references/02-execution/interaction-and-capture-playbook.md": (
        "## Verify completion and retry safely"
    ),
    "references/02-execution/tag-assistant-operations.md": (
        "## Reconcile a recorder and Preview gap"
    ),
    "references/03-judgement/execution-contract.md": ("## Verdict-safety invariants"),
}
REQUIRED_EXECUTION_FILES = (
    "scripts/recette_schema.py",
    "scripts/acceptance_contract.py",
    "scripts/layer_contract.py",
    "scripts/evidence_contract.py",
    "scripts/execution_contract.py",
    "scripts/event_feedback.py",
    "scripts/build_recette_report.py",
    "scripts/inspect_tracking_plan.py",
    "scripts/init_coverage_ledger.py",
    "scripts/preview_session_ledger.py",
    "scripts/datalayer_recorder.js",
    "scripts/dom_interaction_census.js",
    "scripts/decode_browser_requests.py",
    "scripts/incremental_recette.py",
    "scripts/build_retest_manifest.py",
    "scripts/register_supporting_artifact.py",
    "scripts/supporting_artifacts.py",
    "scripts/client_side_rules.py",
    "scripts/validate_business_rules.py",
    "scripts/scan_sensitive_data.py",
    "scripts/diff_recette_runs.py",
    "references/03-judgement/schema-v2.md",
    "references/01-orientation/cross-skill-handoff.md",
    "references/02-execution/journey-inference-and-coverage.md",
    "references/02-execution/tag-assistant-operations.md",
    "references/02-execution/interaction-and-capture-playbook.md",
    "references/02-execution/incremental-evidence-workflow.md",
    "references/02-execution/client-side-destinations-and-containers.md",
    "references/02-execution/client-side-runtime-contexts.md",
    "references/03-judgement/conditional-business-and-privacy-rules.md",
    "references/03-judgement/regression-comparison.md",
    "references/gold-mini-recette.md",
    "tests/fixtures/browser_helpers_smoke.html",
    "tests/run_browser_helpers.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    return parser.parse_args()


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)",
        text,
        flags=re.MULTILINE,
    )
    return match.group(1) if match else ""


def _release_identifiers(
    requested_tag: str | None,
    errors: list[str],
) -> tuple[str, str, str, str]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = str(project["version"])
    expected_tag = f"v{version}"
    if not SEMVER_PATTERN.fullmatch(version):
        errors.append(
            "project version must use MAJOR.MINOR.PATCH metadata; "
            "release tags and archives add the leading v"
        )
    if CALVER_PATTERN.fullmatch(version):
        errors.append("calendar-date versions are forbidden; use semantic v-versioning")
    if requested_tag and requested_tag != expected_tag:
        errors.append(f"tag {requested_tag!r} does not match project version {expected_tag!r}")
    repository_url = "https://github.com/haiqigeng/gtm-preview-recette"
    archive_name = f"gtm-preview-recette-{expected_tag}.zip"
    release_url = f"{repository_url}/releases/tag/{expected_tag}"
    archive_url = f"{repository_url}/releases/download/{expected_tag}/{archive_name}"
    return expected_tag, archive_name, release_url, archive_url


def _check_release_documents(
    expected_tag: str,
    archive_name: str,
    release_url: str,
    archive_url: str,
    errors: list[str],
) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    current_release = markdown_section(readme, "Current release")
    errors.extend(
        (
            f"README.md current-release section is not aligned to {expected_tag}: "
            f"missing {required!r}"
        )
        for required in (expected_tag, release_url, archive_name, archive_url)
        if required not in current_release
    )

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    newest_changelog = re.search(r"^## \[(v\d+\.\d+\.\d+)\]", changelog, flags=re.MULTILINE)
    if not newest_changelog or newest_changelog.group(1) != expected_tag:
        errors.append(f"CHANGELOG.md newest release must be {expected_tag}")
    if release_url not in changelog:
        errors.append(f"CHANGELOG.md does not link the {expected_tag} release")

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    version = expected_tag.removeprefix("v")
    errors.extend(
        (f"CONTRIBUTING.md is not aligned to {expected_tag}: missing {required!r}")
        for required in (
            f"`{version}`",
            f"`{expected_tag}`",
            f"`{archive_name}`",
            f"--tag {expected_tag}",
        )
        if required not in contributing
    )

    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    errors.extend(
        f"SECURITY.md is not aligned to {expected_tag}: missing {required!r}"
        for required in (expected_tag, release_url)
        if required not in security
    )

    bug_template = (ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8")
    if bug_template.count(expected_tag) < 2:
        errors.append(f"bug-report release example and placeholder must both use {expected_tag}")


def _check_release_tree(errors: list[str]) -> None:
    for path in (path for path in ROOT.rglob("*") if path.is_file()):
        relative = path.relative_to(ROOT)
        if any(part in {".git", "dist", ".venv", "__pycache__"} for part in relative.parts):
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES or FORBIDDEN_NAMES.intersection(
            relative.parts
        ):
            errors.append(f"release tree contains forbidden artifact: {relative}")


def _check_skill_contract(errors: list[str]) -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    errors.extend(
        f"SKILL.md does not route to {required}"
        for required in ("01-orientation", "02-execution", "03-judgement")
        if required not in skill
    )
    if "observation mode" in skill.lower():
        errors.append("SKILL.md must not introduce observation mode")
    errors.extend(
        (
            f"SKILL.md contains obsolete workflow label {obsolete}; "
            "applicability must derive from the acceptance requirements"
        )
        for obsolete in ("FULL_TRACKING_PLAN_RECETTE", "SCOPED_ACCEPTANCE_RECETTE")
        if obsolete in skill
    )
    if not re.search(r"name:\s*gtm-preview-recette", skill):
        errors.append("SKILL.md has an invalid skill name")
    if NORTH_STAR not in " ".join(skill.split()):
        errors.append("SKILL.md does not contain the exact approved north star")
    if "Do not preload the complete reference library." not in skill:
        errors.append("SKILL.md does not enforce progressive reference loading")
    if "core execution contract" not in skill:
        errors.append("SKILL.md does not route to the compact execution contract")


def _check_required_resources(errors: list[str]) -> None:
    for relative, required in SAFETY_CONTRACTS.items():
        content = (ROOT / relative).read_text(encoding="utf-8")
        if required not in content:
            errors.append(f"{relative} is missing required contract {required!r}")
    agent_metadata = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$gtm-preview-recette" not in agent_metadata:
        errors.append("agents/openai.yaml default prompt must invoke $gtm-preview-recette")
    errors.extend(
        f"skill is missing required execution resource: {relative}"
        for relative in REQUIRED_EXECUTION_FILES
        if not (ROOT / relative).is_file()
    )


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    expected_tag, archive_name, release_url, archive_url = _release_identifiers(
        args.tag,
        errors,
    )
    _check_release_documents(
        expected_tag,
        archive_name,
        release_url,
        archive_url,
        errors,
    )
    _check_release_tree(errors)
    _check_skill_contract(errors)
    _check_required_resources(errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Release checks passed for {expected_tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
