#!/usr/bin/env python3
"""Build a clean, deterministic release ZIP for the GTM Preview Recette skill."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INCLUDED = ("SKILL.md", "LICENSE", "agents", "references", "scripts")
EXCLUDED_NAMES = {"__pycache__", "build_skill_package.py", "check_release.py"}


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
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files():
            relative = Path("gtm-preview-recette") / path.relative_to(ROOT)
            info = ZipInfo(relative.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
