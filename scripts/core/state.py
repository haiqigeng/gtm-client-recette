"""Immutable plan plus one append-only occurrence/evidence stream.

The module intentionally has no public generic machine-observation writer. Capture
adapters obtain the private writer capability and assign provenance themselves.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import (
    ANALYST_RECORD_KINDS,
    DERIVED_RECORD_KINDS,
    PROVENANCES,
    SCHEMA_VERSION,
    USER_RECORD_KINDS,
    utc_now,
)


class StateError(ValueError):
    """Raised when append-only state would become ambiguous or invalid."""


@dataclass(frozen=True)
class RunPaths:
    root: Path
    plan: Path
    stream: Path
    evidence: Path
    quarantine: Path
    reports: Path

    @classmethod
    def at(cls, root: Path | str) -> RunPaths:
        resolved = Path(root).expanduser().resolve()
        return cls(
            root=resolved,
            plan=resolved / "plan.json",
            stream=resolved / "stream.ndjson",
            evidence=resolved / "evidence",
            quarantine=resolved / "quarantine",
            reports=resolved / "reports",
        )


class _MachineWriter:
    pass


_MACHINE_WRITER = _MachineWriter()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def initialize_paths(root: Path | str) -> RunPaths:
    paths = RunPaths.at(root)
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.evidence.mkdir(exist_ok=True)
    paths.reports.mkdir(exist_ok=True)
    return paths


def write_immutable_plan(root: Path | str, plan: dict[str, Any]) -> Path:
    paths = initialize_paths(root)
    payload = json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
    if paths.plan.exists():
        current = paths.plan.read_text(encoding="utf-8")
        if current == payload:
            return paths.plan
        raise StateError("plan.json is immutable; start a new run for a different plan.")
    temporary = paths.plan.with_suffix(".json.tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    os.replace(temporary, paths.plan)
    if not paths.stream.exists():
        paths.stream.touch()
    return paths.plan


def load_plan(root: Path | str) -> dict[str, Any]:
    path = RunPaths.at(root).plan
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"Cannot read plan.json: {error}") from error
    if not isinstance(value, dict) or value.get("schema_version") != SCHEMA_VERSION:
        raise StateError("Run does not contain a current zero-based plan.json.")
    return value


def _parse_stream(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        return [], False
    raw = path.read_bytes()
    if not raw:
        return [], False
    lines = raw.splitlines(keepends=True)
    records: list[dict[str, Any]] = []
    incomplete_tail = False
    for index, line in enumerate(lines, start=1):
        complete = line.endswith((b"\n", b"\r"))
        try:
            value = json.loads(line.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            if index == len(lines) and not complete:
                incomplete_tail = True
                break
            raise StateError(f"Invalid stream record at line {index}: {error}") from error
        if not isinstance(value, dict):
            raise StateError(f"Stream record {index} is not an object.")
        if value.get("seq") != index:
            raise StateError(f"Stream sequence is not contiguous at line {index}.")
        records.append(value)
    return records, incomplete_tail


def read_stream(root: Path | str) -> tuple[list[dict[str, Any]], list[str]]:
    records, incomplete = _parse_stream(RunPaths.at(root).stream)
    warnings = ["Ignored one incomplete final stream record."] if incomplete else []
    return records, warnings


def _recover_incomplete_tail(path: Path) -> None:
    _, incomplete = _parse_stream(path)
    if not incomplete:
        return
    raw = path.read_bytes()
    newline = raw.rfind(b"\n")
    retained = raw[: newline + 1] if newline >= 0 else b""
    with path.open("r+b") as handle:
        handle.seek(0)
        handle.write(retained)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())


def _is_frozen(records: list[dict[str, Any]]) -> bool:
    frozen = False
    for record in records:
        if record.get("kind") == "RUN_FINISHED":
            frozen = True
        elif record.get("kind") == "RUN_REOPENED":
            frozen = False
    return frozen


def _append(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    provenance: str,
    *,
    idempotency_key: str | None = None,
    machine_writer: _MachineWriter | None = None,
    allow_frozen_transition: bool = False,
) -> dict[str, Any]:
    if provenance not in PROVENANCES:
        raise StateError(f"Unsupported provenance: {provenance}")
    if provenance == "machine_observed" and machine_writer is not _MACHINE_WRITER:
        raise StateError("Machine observations are writable only by typed capture adapters.")
    if not isinstance(data, dict):
        raise StateError("Record data must be an object.")

    paths = initialize_paths(root)
    load_plan(paths.root)
    _recover_incomplete_tail(paths.stream)
    records, _ = _parse_stream(paths.stream)
    if _is_frozen(records) and not allow_frozen_transition:
        raise StateError("The run is finished; explicit reopen authorization is required.")

    if idempotency_key:
        matches = [record for record in records if record.get("idempotency_key") == idempotency_key]
        if matches:
            candidate = matches[-1]
            if candidate.get("kind") == kind and candidate.get("data") == data:
                return candidate
            raise StateError(
                f"Idempotency key already identifies different content: {idempotency_key}"
            )

    seq = len(records) + 1
    record = {
        "seq": seq,
        "record_id": f"R{seq:07d}",
        "recorded_at": utc_now(),
        "kind": kind,
        "provenance": provenance,
        "data": data,
    }
    if idempotency_key:
        record["idempotency_key"] = idempotency_key
    encoded = (canonical_json(record) + "\n").encode("utf-8")
    with paths.stream.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return record


def append_user(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    *,
    idempotency_key: str | None = None,
    allow_frozen_transition: bool = False,
) -> dict[str, Any]:
    if kind not in USER_RECORD_KINDS:
        raise StateError(f"{kind} is not a user-provided record kind.")
    if allow_frozen_transition and kind != "REOPEN_AUTHORIZATION":
        raise StateError("Only explicit reopen authorization may be appended to a finished run.")
    return _append(
        root,
        kind,
        data,
        "user_provided",
        idempotency_key=idempotency_key,
        allow_frozen_transition=allow_frozen_transition,
    )


def append_annotation(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    *,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    if kind not in ANALYST_RECORD_KINDS:
        raise StateError(f"{kind} is not an analyst-annotation record kind.")
    return _append(root, kind, data, "analyst_annotation", idempotency_key=idempotency_key)


def append_derived(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    *,
    idempotency_key: str | None = None,
    allow_frozen_transition: bool = False,
) -> dict[str, Any]:
    if kind not in DERIVED_RECORD_KINDS:
        raise StateError(f"{kind} is not a derived record kind.")
    return _append(
        root,
        kind,
        data,
        "derived",
        idempotency_key=idempotency_key,
        allow_frozen_transition=allow_frozen_transition,
    )


def _append_machine(
    root: Path | str,
    kind: str,
    data: dict[str, Any],
    *,
    idempotency_key: str,
) -> dict[str, Any]:
    return _append(
        root,
        kind,
        data,
        "machine_observed",
        idempotency_key=idempotency_key,
        machine_writer=_MACHINE_WRITER,
    )


def stream_record_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record.get("record_id")): record for record in records}
