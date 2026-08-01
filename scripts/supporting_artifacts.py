#!/usr/bin/env python3
"""Supporting-only cross-skill artifact metadata for GTM recette inputs."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from client_side_rules import DEFAULT_FORBIDDEN_CATEGORIES, scan_sensitive_value

ARTIFACT_CONTRACT_VERSION = 1
SUPPORTING_ARTIFACT_TYPES = {
    "gtm_container_audit_facts",
    "gtm_configuration_change_manifest",
}
SUPPORTING_SOURCE_SKILLS = {
    "gtm-container-audit-cleanup",
    "configure-gtm",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_supporting_artifacts(value: Any) -> list[str]:
    """Validate metadata only; supporting artifacts never decide recette verdicts."""
    if value is None:
        return []
    if not isinstance(value, list):
        return ["run.supporting_artifacts must be an array"]
    errors: list[str] = []
    identifiers: set[str] = set()
    for index, row in enumerate(value, start=1):
        label = f"run.supporting_artifacts row {index}"
        if not isinstance(row, dict):
            errors.append(f"{label}: must be an object")
            continue
        artifact_id = row.get("artifact_id")
        for field in (
            "artifact_id",
            "artifact_type",
            "source_skill",
            "source_run_id",
            "source_version",
            "sha256",
            "file_name",
            "registered_at",
        ):
            if not _nonempty(row.get(field)):
                errors.append(f"{label}: missing '{field}'")
        if _nonempty(artifact_id):
            if artifact_id in identifiers:
                errors.append(f"{label}: duplicate artifact_id '{artifact_id}'")
            identifiers.add(str(artifact_id))
        if row.get("contract_version") != ARTIFACT_CONTRACT_VERSION:
            errors.append(f"{label}: contract_version must be 1")
        if row.get("artifact_type") not in SUPPORTING_ARTIFACT_TYPES:
            errors.append(f"{label}: unsupported artifact_type")
        if row.get("source_skill") not in SUPPORTING_SOURCE_SKILLS:
            errors.append(f"{label}: unsupported source_skill")
        if row.get("role") != "supporting_only" or row.get("verdict_authority") is not False:
            errors.append(
                f"{label}: role must be supporting_only and verdict_authority must be false"
            )
        digest = row.get("sha256")
        if _nonempty(digest) and not SHA256_RE.fullmatch(str(digest)):
            errors.append(f"{label}: sha256 must be 64 lowercase hexadecimal characters")
        timestamp = row.get("registered_at")
        if _nonempty(timestamp):
            try:
                parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{label}: registered_at must be ISO 8601")
            else:
                if parsed.tzinfo is None:
                    errors.append(f"{label}: registered_at must include timezone")
        findings = scan_sensitive_value(
            {
                "artifact_id": row.get("artifact_id"),
                "source_run_id": row.get("source_run_id"),
                "source_version": row.get("source_version"),
                "file_name": row.get("file_name"),
                "notes": row.get("notes"),
            },
            root_path=label,
            policy={"forbidden_categories": DEFAULT_FORBIDDEN_CATEGORIES},
        )
        if any(finding.get("status") in {"FAIL", "REVIEW"} for finding in findings):
            errors.append(f"{label}: metadata contains sensitive content; redact it first")
    return errors
