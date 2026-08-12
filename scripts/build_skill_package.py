#!/usr/bin/env python3
"""Build a clean, deterministic release ZIP for the GTM Preview Recette skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INCLUDED = (
    "SKILL.md",
    "LICENSE",
    "pyproject.toml",
    "agents",
    "references",
    "scripts",
    "tests",
)
EXCLUDED_NAMES = {"__pycache__", "check_release.py"}
MANIFEST_NAME = "RELEASE-MANIFEST.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def release_files() -> list[Path]:
    files: list[Path] = []
    for name in INCLUDED:
        source = ROOT / name
        if source.is_file():
            files.append(source)
        elif source.is_dir():
            files.extend(path for path in source.rglob("*") if path.is_file())
    return sorted(
        (path for path in files if not EXCLUDED_NAMES.intersection(path.parts)),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def main() -> int:
    args = parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    expected_name = f"{project['name']}-v{project['version']}.zip"
    if args.output.name != expected_name:
        raise SystemExit(
            f"release archive must be named {expected_name!r}; got {args.output.name!r}"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    files = release_files()
    hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    tree_digest = hashlib.sha256(
        "".join(f"{name}\0{digest}\n" for name, digest in hashes.items()).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest_version": 1,
        "package": project["name"],
        "release": f"v{project['version']}",
        "source_tree_sha256": tree_digest,
        "files": hashes,
    }
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = Path("gtm-preview-recette") / path.relative_to(ROOT)
            info = ZipInfo(relative.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        manifest_info = ZipInfo(
            (Path("gtm-preview-recette") / MANIFEST_NAME).as_posix(),
            date_time=(2026, 1, 1, 0, 0, 0),
        )
        manifest_info.compress_type = ZIP_DEFLATED
        manifest_info.external_attr = 0o644 << 16
        archive.writestr(
            manifest_info,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
            + b"\n",
        )
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
