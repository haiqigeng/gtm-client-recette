"""Immediate fixed-schema feedback rendering for the agent workflow."""

from __future__ import annotations

from typing import Any

from report import feedback_rows


def _cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def feedback_markdown(result: dict[str, Any]) -> str:
    lines = [
        "| event_name | layer_name | status | details |",
        "|---|---|---|---|",
    ]
    for row in feedback_rows(result):
        lines.append(
            f"| {_cell(row['event_name'])} | {_cell(row['layer_name'])} | "
            f"{_cell(row['status'])} | {_cell(row['details'])} |"
        )
    return "\n".join(lines)
