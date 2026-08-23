#!/usr/bin/env python3
"""Shared path-alias checks for command-line inputs and outputs."""

from __future__ import annotations

from pathlib import Path


def resolved(path: Path) -> Path:
    """Resolve a path without requiring the target to exist."""
    return path.expanduser().resolve(strict=False)


def ensure_distinct_output(output: Path, *inputs: Path, label: str = "output") -> None:
    """Reject an output path that aliases any protected input path."""
    target = resolved(output)
    for source in inputs:
        if target == resolved(source):
            raise ValueError(f"{label} must not overwrite input file {source}")
