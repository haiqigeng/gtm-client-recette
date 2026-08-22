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


def ensure_distinct_paths(*paths: Path) -> None:
    """Reject duplicate paths in a set of independently written artifacts."""
    normalized = [resolved(path) for path in paths]
    if len(set(normalized)) != len(normalized):
        raise ValueError("artifact paths must resolve to distinct files")
