#!/usr/bin/env python3
"""Verify a packaged skill manifest and optionally an installed skill tree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZipFile

ROOT_PREFIX = PurePosixPath("gtm-preview-recette")
MANIFEST_PATH = (ROOT_PREFIX / "RELEASE-MANIFEST.json").as_posix()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--installed-skill", type=Path)
    return parser.parse_args()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_manifest(archive: ZipFile) -> dict[str, Any]:
    if MANIFEST_PATH not in archive.namelist():
        raise ValueError("Release archive has no RELEASE-MANIFEST.json.")
    value = json.loads(archive.read(MANIFEST_PATH))
    if not isinstance(value, dict) or value.get("manifest_version") != 1:
        raise ValueError("Release manifest is missing or unsupported.")
    return value


def verify_archive(path: Path) -> dict[str, Any]:
    with ZipFile(path) as archive:
        manifest = load_manifest(archive)
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError("Release manifest files map is empty.")
        actual_names = {
            PurePosixPath(name).relative_to(ROOT_PREFIX).as_posix()
            for name in archive.namelist()
            if name != MANIFEST_PATH and not name.endswith("/")
        }
        if actual_names != set(files):
            raise ValueError("Release archive contents differ from the manifest file set.")
        for relative, expected in files.items():
            actual = digest(archive.read((ROOT_PREFIX / relative).as_posix()))
            if actual != expected:
                raise ValueError(f"Release file hash mismatch: {relative}")
        expected_tree = hashlib.sha256(
            "".join(f"{name}\0{files[name]}\n" for name in sorted(files)).encode("utf-8")
        ).hexdigest()
        if manifest.get("source_tree_sha256") != expected_tree:
            raise ValueError("Release source-tree digest does not reconcile.")
        return manifest


def verify_install(manifest: dict[str, Any], installed_skill: Path) -> None:
    files = manifest["files"]
    missing = []
    mismatched = []
    for relative, expected in files.items():
        path = installed_skill / Path(relative)
        if not path.is_file():
            missing.append(relative)
        elif digest(path.read_bytes()) != expected:
            mismatched.append(relative)
    if missing or mismatched:
        parts = []
        if missing:
            parts.append("missing: " + ", ".join(missing[:10]))
        if mismatched:
            parts.append("hash mismatch: " + ", ".join(mismatched[:10]))
        raise ValueError(
            "Installed skill differs from the release artifact (" + "; ".join(parts) + ")"
        )


def main() -> int:
    args = parse_args()
    try:
        manifest = verify_archive(args.archive)
        if args.installed_skill:
            verify_install(manifest, args.installed_skill)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(
        json.dumps(
            {
                "verified": True,
                "release": manifest.get("release"),
                "source_tree_sha256": manifest.get("source_tree_sha256"),
                "installed_skill_verified": bool(args.installed_skill),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
