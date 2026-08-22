#!/usr/bin/env python3
"""Check the lean runtime skill contract before packaging."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)")
REFERENCE_LINK = re.compile(r"\((references/[^)]+\.md)\)")

REQUIRED_REFERENCES = {
    "references/01-orientation/scope-and-inputs.md",
    "references/02-execution/scenario-coverage-and-sampling.md",
    "references/02-execution/browser-preview-runtime.md",
    "references/02-execution/forms-consent-acquisition.md",
    "references/02-execution/continuous-stream.md",
    "references/03-judgement/evidence-and-layers.md",
    "references/03-judgement/semantic-verdict.md",
    "references/03-judgement/operator-and-output.md",
}
REQUIRED_RUNTIME_SCRIPTS = {
    "acceptance_contract.py",
    "build_recette_report.py",
    "build_retest_manifest.py",
    "classify_datalayer_snapshot.py",
    "client_side_rules.py",
    "datalayer_recorder.js",
    "decode_browser_requests.py",
    "diff_recette_runs.py",
    "dom_interaction_census.js",
    "event_feedback.py",
    "evidence_contract.py",
    "evidence_integrity.py",
    "execution_contract.py",
    "gated_flow_contract.py",
    "generate_synthetic_profile.py",
    "import_ga4_tracking_plan_handoff.py",
    "incremental_recette.py",
    "init_coverage_ledger.py",
    "inspect_tracking_plan.py",
    "layer_contract.py",
    "migrate_schema_v2_to_v3.py",
    "page_context_contract.py",
    "path_safety.py",
    "preview_session_ledger.py",
    "recette_operator.py",
    "recette_schema.py",
    "register_supporting_artifact.py",
    "runtime_state_contract.py",
    "safe_regex.py",
    "scan_sensitive_data.py",
    "scenario_coverage.py",
    "semantic_contract.py",
    "state_io.py",
    "stream_contract.py",
    "supporting_artifacts.py",
    "tag_evidence_contract.py",
    "validate_business_rules.py",
    "value_semantics.py",
}
PACKAGING_SCRIPTS = {
    "build_skill_package.py",
    "check_release.py",
    "verify_release_artifact.py",
}
FORBIDDEN_RUNTIME_SUFFIXES = {".xlsx", ".log", ".png", ".jpg", ".jpeg", ".zip"}
FORBIDDEN_RUNTIME_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".playwright-mcp",
    "evidence",
    "screenshots",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    return parser.parse_args()


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
    for relative in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md"):
        if tag not in (ROOT / relative).read_text(encoding="utf-8"):
            errors.append(f"{relative} is not aligned to {tag}")
    return tag


def check_skill(errors: list[str]) -> None:
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: gtm-client-recette\n"):
        errors.append("SKILL.md frontmatter name is invalid")
    if len(skill.splitlines()) > 350:
        errors.append("SKILL.md exceeds the 350-line progressive-disclosure budget")
    for required in (
        "technical_delivery",
        "operator_contract_version_required: 2",
        "INTER_ACTION",
        "PAGE_ACTION_VALIDITY",
        "ORDINARY",
        "CONTRAST",
        "404",
        "existing authenticated GTM",
        "overall event verdict",
    ):
        if required not in skill:
            errors.append(f"SKILL.md is missing required contract {required!r}")
    linked = set(REFERENCE_LINK.findall(skill))
    if linked != REQUIRED_REFERENCES:
        errors.append(
            "SKILL.md reference routing differs from the exact consolidated reference set"
        )
    for relative in linked:
        if not (ROOT / relative).is_file():
            errors.append(f"SKILL.md links missing reference: {relative}")


def check_runtime_tree(errors: list[str]) -> None:
    references = {path.relative_to(ROOT).as_posix() for path in (ROOT / "references").rglob("*.md")}
    if references != REQUIRED_REFERENCES:
        errors.append("references tree contains missing, stale, or duplicate guides")
    scripts = {path.name for path in (ROOT / "scripts").iterdir() if path.is_file()}
    missing = REQUIRED_RUNTIME_SCRIPTS - scripts
    if missing:
        errors.append("missing runtime scripts: " + ", ".join(sorted(missing)))
    unexpected = scripts - REQUIRED_RUNTIME_SCRIPTS - PACKAGING_SCRIPTS
    if unexpected:
        errors.append("unclassified scripts: " + ", ".join(sorted(unexpected)))
    for relative in ("agents/openai.yaml", "LICENSE"):
        if not (ROOT / relative).is_file():
            errors.append(f"missing runtime resource: {relative}")
    agent = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$gtm-client-recette" not in agent:
        errors.append("agent default prompt does not invoke the skill")


def check_source_residue(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(
            part in {".git", "dist", ".venv", *FORBIDDEN_RUNTIME_PARTS} for part in relative.parts
        ):
            continue
        if path.suffix.lower() in FORBIDDEN_RUNTIME_SUFFIXES:
            errors.append(f"source tree contains run/output residue: {relative}")
        if path.name in {"normalized-results.json"}:
            errors.append(f"source tree contains run-bound result: {relative}")


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    tag = check_metadata(args.tag, errors)
    check_skill(errors)
    check_runtime_tree(errors)
    check_source_residue(errors)
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Lean runtime release checks passed for {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
