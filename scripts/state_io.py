#!/usr/bin/env python3
"""Crash-aware JSON persistence for normalized results and session ledgers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4


def serialized_json(value: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 JSON bytes for a top-level object."""
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object with a path-specific error."""
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return value


def _sync_directory(path: Path) -> None:
    """Best-effort directory sync on platforms that expose directory handles."""
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _write_synced(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _replace(source: Path, target: Path) -> None:
    """Replace a target atomically; kept separate for deterministic fault injection."""
    source.replace(target)
    _sync_directory(target.parent)


def atomic_write_bytes(path: Path, content: bytes) -> None:
    """Publish bytes through a unique, synchronized temporary file."""
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        _write_synced(temporary, content)
        _replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    """Atomically persist one JSON object."""
    atomic_write_bytes(path, serialized_json(value))


def _pair_journal_path(first: Path, second: Path) -> Path:
    identity = hashlib.sha256(f"{first.resolve()}\0{second.resolve()}".encode()).hexdigest()[:16]
    return first.parent / f".{first.name}.{identity}.pair-transaction.json"


def _restore(path: Path, backup: Path | None, existed: bool) -> None:
    if not existed:
        path.unlink(missing_ok=True)
        _sync_directory(path.parent)
        return
    if backup is None or not backup.is_file():
        raise OSError(f"Missing rollback backup for {path}")
    atomic_write_bytes(path, backup.read_bytes())


def _cleanup(paths: list[Path]) -> None:
    for path in paths:
        path.unlink(missing_ok=True)


def recover_file_pair(first: Path, second: Path) -> bool:
    """Recover an interrupted pair transaction; return whether a journal existed."""
    journal_path = _pair_journal_path(first, second)
    if not journal_path.is_file():
        return False
    journal = load_json_object(journal_path)
    expected = [str(first.resolve()), str(second.resolve())]
    if journal.get("targets") != expected:
        raise OSError(f"Pair transaction journal does not match {first} and {second}")
    backups = [Path(value) if value else None for value in journal.get("backups", [])]
    if len(backups) != 2:
        raise OSError("Pair transaction journal has an invalid backup inventory")
    artifacts = [path for path in backups if path is not None]
    if journal.get("state") == "PREPARED":
        existed = journal.get("target_existed")
        if not isinstance(existed, list) or len(existed) != 2:
            raise OSError("Pair transaction journal has invalid target history")
        _restore(first, backups[0], bool(existed[0]))
        _restore(second, backups[1], bool(existed[1]))
    elif journal.get("state") != "COMMITTED":
        raise OSError("Pair transaction journal has an unsupported state")
    _cleanup([*artifacts, journal_path])
    return True


def atomic_write_file_pair(
    first: Path,
    first_content: bytes,
    second: Path,
    second_content: bytes,
) -> None:
    """Publish two files as one crash-recoverable local transaction."""
    if first.resolve() == second.resolve():
        raise ValueError("Paired paths must be different files.")
    first.parent.mkdir(parents=True, exist_ok=True)
    second.parent.mkdir(parents=True, exist_ok=True)
    recover_file_pair(first, second)

    transaction_id = uuid4().hex
    first_temp = first.with_name(f".{first.name}.{transaction_id}.tmp")
    second_temp = second.with_name(f".{second.name}.{transaction_id}.tmp")
    first_backup = first.with_name(f".{first.name}.{transaction_id}.bak")
    second_backup = second.with_name(f".{second.name}.{transaction_id}.bak")
    journal_path = _pair_journal_path(first, second)
    first_existed = first.is_file()
    second_existed = second.is_file()
    replaced = [False, False]
    rollback_errors: list[str] = []
    artifacts = [first_temp, second_temp, first_backup, second_backup, journal_path]
    try:
        if first_existed:
            _write_synced(first_backup, first.read_bytes())
        if second_existed:
            _write_synced(second_backup, second.read_bytes())
        _write_synced(first_temp, first_content)
        _write_synced(second_temp, second_content)
        atomic_write_json(
            journal_path,
            {
                "transaction_id": transaction_id,
                "state": "PREPARED",
                "targets": [str(first.resolve()), str(second.resolve())],
                "target_existed": [first_existed, second_existed],
                "backups": [
                    str(first_backup.resolve()) if first_existed else None,
                    str(second_backup.resolve()) if second_existed else None,
                ],
            },
        )
        _replace(first_temp, first)
        replaced[0] = True
        _replace(second_temp, second)
        replaced[1] = True
        atomic_write_json(
            journal_path,
            {
                "transaction_id": transaction_id,
                "state": "COMMITTED",
                "targets": [str(first.resolve()), str(second.resolve())],
                "target_existed": [first_existed, second_existed],
                "backups": [
                    str(first_backup.resolve()) if first_existed else None,
                    str(second_backup.resolve()) if second_existed else None,
                ],
            },
        )
    except BaseException as exc:
        for path, backup, existed, was_replaced in (
            (first, first_backup if first_existed else None, first_existed, replaced[0]),
            (second, second_backup if second_existed else None, second_existed, replaced[1]),
        ):
            if not was_replaced:
                continue
            try:
                _restore(path, backup, existed)
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        if rollback_errors:
            raise OSError(
                f"Paired write failed ({exc}); rollback also failed for "
                + "; ".join(rollback_errors)
            ) from exc
        raise
    finally:
        if not rollback_errors:
            _cleanup(artifacts)


def atomic_write_json_pair(
    first: Path,
    first_value: dict[str, Any],
    second: Path,
    second_value: dict[str, Any],
) -> None:
    """Publish two JSON objects as one crash-recoverable local transaction."""
    atomic_write_file_pair(
        first,
        serialized_json(first_value),
        second,
        serialized_json(second_value),
    )


# Backward-compatible public name for callers that explicitly recover JSON pairs.
recover_json_pair = recover_file_pair
