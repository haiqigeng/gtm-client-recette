#!/usr/bin/env python3
"""Inspect XLSX or delimited tracking plans while preserving source coordinates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Tracking-plan .xlsx, .csv, or .tsv file.")
    parser.add_argument("output", type=Path, help="Destination inspection JSON.")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional per-sheet row limit; 0 reads all populated rows.",
    )
    return parser.parse_args()


def value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "formula" if value.startswith("=") else "string"
    return type(value).__name__


def inspect_xlsx(path: Path, max_rows: int) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    sheets = []
    try:
        for worksheet in workbook.worksheets:
            rows = []
            populated = 0
            for row_number, row in enumerate(worksheet.iter_rows(), start=1):
                cells = []
                for column_number, cell in enumerate(row, start=1):
                    if cell.value is None:
                        continue
                    cells.append(
                        {
                            "cell": f"{get_column_letter(column_number)}{row_number}",
                            "column": get_column_letter(column_number),
                            "value": cell.value,
                            "value_type": value_type(cell.value),
                        }
                    )
                if not cells:
                    continue
                rows.append({"row": row_number, "cells": cells})
                populated += 1
                if max_rows and populated >= max_rows:
                    break
            sheets.append(
                {
                    "sheet": worksheet.title,
                    "max_row": worksheet.max_row,
                    "max_column": worksheet.max_column,
                    "populated_rows": rows,
                    "truncated": bool(max_rows and populated >= max_rows),
                }
            )
    finally:
        workbook.close()
    return {"source": str(path.resolve()), "format": "xlsx", "sheets": sheets}


def inspect_delimited(path: Path, max_rows: int) -> dict[str, Any]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row_number, row in enumerate(reader, start=1):
            cells = [
                {
                    "cell": f"{get_column_letter(column_number)}{row_number}",
                    "column": get_column_letter(column_number),
                    "value": value,
                    "value_type": "string",
                }
                for column_number, value in enumerate(row, start=1)
                if value != ""
            ]
            if not cells:
                continue
            rows.append({"row": row_number, "cells": cells})
            if max_rows and len(rows) >= max_rows:
                break
    max_column = max((len(row["cells"]) for row in rows), default=0)
    return {
        "source": str(path.resolve()),
        "format": path.suffix.lower().lstrip("."),
        "sheets": [
            {
                "sheet": path.stem,
                "max_row": len(rows),
                "max_column": max_column,
                "populated_rows": rows,
                "truncated": bool(max_rows and len(rows) >= max_rows),
            }
        ],
    }


def main() -> int:
    args = parse_args()
    if args.max_rows < 0:
        raise SystemExit("--max-rows must be zero or positive")
    suffix = args.input.suffix.lower()
    if suffix == ".xlsx":
        result = inspect_xlsx(args.input, args.max_rows)
    elif suffix in {".csv", ".tsv"}:
        result = inspect_delimited(args.input, args.max_rows)
    else:
        raise SystemExit("Unsupported input format; use .xlsx, .csv, or .tsv")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"Created {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
