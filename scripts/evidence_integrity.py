#!/usr/bin/env python3
"""Verify every final evidence artifact and bind all catalog metadata by digest."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _catalog_rows(results: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in results.get("evidence", []) if isinstance(row, dict)]


def catalog_digest(results: dict[str, Any]) -> str:
    """Return a stable digest of every evidence identity, binding, and location field."""
    normalized = _catalog_rows(results)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _safe_local_path(base_dir: Path, value: str) -> Path:
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()
    base = base_dir.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"evidence path escapes the run evidence directory: {value}") from exc
    return resolved


def build_integrity_record(results: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """Inspect evidence paths and return a metadata-only integrity record."""
    files: list[dict[str, Any]] = []
    failures = 0
    for row in _catalog_rows(results):
        evidence_id = str(row.get("evidence_id", "")).strip()
        kind = str(row.get("kind", "")).strip()
        location = str(row.get("path_or_url", "")).strip()
        record: dict[str, Any] = {
            "evidence_id": evidence_id,
            "kind": kind,
            "critical": True,
            "required_for_final": True,
            "path_or_url": location,
        }
        if not location:
            record.update({"status": "MISSING_LOCATION", "exists": False})
            failures += 1
        elif _is_web_url(location):
            record.update(
                {
                    "status": "EXTERNAL_UNVERIFIED",
                    "exists": None,
                    "limitation": "External URLs are not local immutable evidence.",
                }
            )
            failures += 1
        else:
            try:
                path = _safe_local_path(base_dir, location)
            except ValueError as exc:
                record.update({"status": "UNSAFE_PATH", "exists": False, "limitation": str(exc)})
                failures += 1
            else:
                exists = path.is_file()
                record.update(
                    {
                        "status": "VERIFIED" if exists else "MISSING_FILE",
                        "exists": exists,
                        "size": path.stat().st_size if exists else None,
                    }
                )
                if exists:
                    record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                if not exists:
                    failures += 1
        files.append(record)
    return {
        "version": 2,
        "status": "VERIFIED" if failures == 0 else "FAILED",
        "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_dir": str(base_dir.resolve()),
        "catalog_sha256": catalog_digest(results),
        "file_count": len(files),
        "critical_file_count": sum(bool(row.get("critical")) for row in files),
        "files": files,
    }


def integrity_errors(
    ledger: dict[str, Any],
    *,
    results: dict[str, Any],
    verify_files: bool,
) -> list[str]:
    """Validate a stored integrity record and optionally recheck the files live."""
    value = ledger.get("evidence_integrity")
    if not isinstance(value, dict):
        return ["session evidence_integrity must be an object"]
    errors: list[str] = []
    if value.get("version") != 2:
        errors.append("session evidence_integrity.version must be 2")
    if value.get("status") != "VERIFIED":
        errors.append("session evidence_integrity.status must be VERIFIED")
    expected_catalog = catalog_digest(results)
    if value.get("catalog_sha256") != expected_catalog:
        errors.append("session evidence integrity is stale for the current evidence catalog")
    files = value.get("files")
    if not isinstance(files, list) or any(not isinstance(row, dict) for row in files):
        return errors + ["session evidence_integrity.files must be an object array"]
    expected_ids = [str(row.get("evidence_id", "")).strip() for row in _catalog_rows(results)]
    actual_ids = [str(row.get("evidence_id", "")).strip() for row in files]
    if actual_ids != expected_ids:
        errors.append("session evidence integrity file inventory differs from evidence catalog")
    for row in files:
        evidence_id = str(row.get("evidence_id", "")).strip()
        if row.get("required_for_final") is not True or row.get("critical") is not True:
            errors.append(f"session evidence {evidence_id}: every final artifact is required")
        if row.get("status") != "VERIFIED" or row.get("exists") is not True:
            errors.append(f"session evidence {evidence_id}: local file was not verified")
        if not _nonempty(row.get("sha256")):
            errors.append(f"session evidence {evidence_id}: file requires sha256")
    if verify_files and _nonempty(value.get("base_dir")):
        try:
            current = build_integrity_record(results, Path(str(value["base_dir"])))
        except OSError as exc:
            errors.append(f"session evidence integrity live check failed: {exc}")
        else:
            if current.get("status") != "VERIFIED":
                errors.append("session evidence files no longer pass live verification")
            current_by_id = {
                str(row.get("evidence_id", "")): row for row in current.get("files", [])
            }
            for stored in files:
                evidence_id = str(stored.get("evidence_id", ""))
                live = current_by_id.get(evidence_id, {})
                if stored.get("sha256") != live.get("sha256"):
                    errors.append(f"session evidence {evidence_id}: file digest changed")
    elif verify_files:
        errors.append("session evidence_integrity.base_dir is required for live verification")
    return errors
