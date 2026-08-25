#!/usr/bin/env python3
"""Compile the single supported XLSX tracking-plan contract."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

SCHEMA_VERSION = "8.0"

EVENT_HEADERS = {
    "name_of_the_event",
    "nom_de_l_evenement",
    "nom_evenement",
    "nature",
}
FIELD_HEADERS = {"variable", "variables", "parameter", "parameters", "parametre", "parametres"}
TYPE_HEADERS = {"type", "data_type", "json_type"}
STATUS_HEADERS = {"status", "statut", "required", "requiredness", "obligatoire"}
VALUE_HEADERS = {"value", "values", "valeur", "valeurs", "allowed_values"}
SUMMARY_HEADERS = {"summary", "description", "resume", "meaning"}
INDEX_HEADERS = {"event", "events", "evenement", "evenements"}
STOP_MARKERS = {
    "code",
    "develop",
    "development",
    "example",
    "images",
    "implementation",
    "javascript",
}
ECOMMERCE_EVENTS = {
    "view_item_list",
    "select_item",
    "view_item",
    "add_to_cart",
    "remove_from_cart",
    "view_cart",
    "begin_checkout",
    "add_shipping_info",
    "add_payment_info",
    "purchase",
    "refund",
}
ITEM_FIELDS = {
    "affiliation",
    "coupon",
    "discount",
    "index",
    "item_brand",
    "item_category",
    "item_category2",
    "item_category3",
    "item_category4",
    "item_category5",
    "item_id",
    "item_list_id",
    "item_list_name",
    "item_name",
    "item_variant",
    "location_id",
    "price",
    "quantity",
}
EXACT_SINGLETON_FIELDS = {
    "action",
    "checkout_step",
    "currency",
    "event",
    "event_name",
    "item_list_name",
    "payment_type",
}
TYPE_ALIASES = {
    "str": "string",
    "text": "string",
    "texte": "string",
    "numeric": "number",
    "numer": "number",
    "float": "number",
    "double": "number",
    "int": "integer",
    "bool": "boolean",
}
SUPPORTED_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}


class PlanError(ValueError):
    """Raised when the fixed XLSX contract cannot be compiled without guessing."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _identity(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _key(value))


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _slug(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", _text(value)).strip("-") or "event"


def _event_name(value: Any) -> str:
    text = _text(value)
    if re.fullmatch(r"[A-Za-z0-9_.-]+", text):
        return text
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _field_name(value: Any) -> str:
    original = _text(value)
    if re.fullmatch(
        r"[A-Za-z_$][A-Za-z0-9_$]*(?:\[\])?(?:\.[A-Za-z_$][A-Za-z0-9_$]*(?:\[\])?)*", original
    ):
        return original
    normalized = unicodedata.normalize("NFKD", original)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9_]+", "_", normalized).strip("_").casefold()


def _field_path(event_name: str, field_name: str) -> str:
    if "." in field_name or "[" in field_name:
        return field_name
    if event_name in ECOMMERCE_EVENTS and field_name != "event":
        return (
            f"ecommerce.items[].{field_name}"
            if field_name.casefold() in ITEM_FIELDS
            else f"ecommerce.{field_name}"
        )
    return field_name


def _finite_values(value: Any) -> list[Any]:
    if not isinstance(value, str):
        return []
    if "|" in value:
        parts = value.split("|")
    elif re.fullmatch(r"\s*[A-Za-z0-9_-]{1,20}\s*/\s*[A-Za-z0-9_-]{1,20}\s*", value):
        parts = value.split("/")
    else:
        return []
    values = [re.sub(r"^[^\w-]+|[^\w-]+$", "", part.strip()) for part in parts]
    values = [part for part in values if part]
    if not 2 <= len(values) <= 20:
        return []
    rejected = re.compile(
        r"(?:\.\.\.|…|\b(?:xxx|example|sample|dynamic|variable|etc)\b|\{\{|<[^>]+>)", re.I
    )
    if any(len(item) > 80 or rejected.search(item) for item in values):
        return []
    return values


def _declared_rule(value: Any, expected_type: str | None, field: str, event: str) -> dict[str, Any]:
    allowed = _finite_values(value)
    if allowed:
        return {"rule": "one_of", "allowed_values": allowed}
    if field == "event" and event:
        return {"rule": "equals", "expected": event}
    if not _present(value):
        return {"rule": "present"}
    text = _text(value)
    if re.search(
        r"(?:\.\.\.|…|\b(?:xxx|example|sample|dynamic|variable|n/?a|etc)\b|\{\{|<[^>]+>)",
        text,
        re.I,
    ):
        return {"rule": "present"}
    if "|" in text or re.search(r"\s(?:-|/)\s", text) or "," in text:
        return {"rule": "present"}
    if field.casefold() not in EXACT_SINGLETON_FIELDS and expected_type not in {
        "boolean",
        "null",
    }:
        return {"rule": "present"}
    if expected_type == "boolean":
        lowered = text.casefold()
        if lowered in {"true", "1", "yes", "oui"}:
            return {"rule": "equals", "expected": True}
        if lowered in {"false", "0", "no", "non"}:
            return {"rule": "equals", "expected": False}
    return {"rule": "equals", "expected": value}


def _index_events(rows: list[tuple[Any, ...]]) -> list[str]:
    for row_index, row in enumerate(rows[:60]):
        columns = [index for index, value in enumerate(row) if _key(value) in INDEX_HEADERS]
        if not columns:
            continue
        if any(_key(value) in FIELD_HEADERS for value in row):
            return []
        column = columns[0]
        output: list[str] = []
        for candidate in rows[row_index + 1 :]:
            value = candidate[column] if column < len(candidate) else None
            if _present(value):
                item = _text(value)
                if item not in output:
                    output.append(item)
        return output
    return []


def _event_metadata(
    rows: list[tuple[Any, ...]], sheet: str
) -> tuple[int, int, str, bool, str] | None:
    event_header: tuple[int, int] | None = None
    for row_index, row in enumerate(rows[:40]):
        for column, value in enumerate(row):
            if _key(value) in EVENT_HEADERS:
                event_header = (row_index, column)
                break
        if event_header:
            break
    if event_header is None:
        return None
    header_row, event_column = event_header
    event_row = next(
        (
            index
            for index in range(header_row + 1, min(len(rows), header_row + 8))
            if event_column < len(rows[index]) and _present(rows[index][event_column])
        ),
        None,
    )
    if event_row is None:
        raise PlanError(f"{sheet}: event metadata has no event value below its header.")
    label = _text(rows[event_row][event_column])
    core = _identity(label) in {"coredatalayer", "corestate"} or _identity(sheet) in {
        "coredatalayer",
        "corestate",
    }
    return event_row, event_column, label, core, "page_view" if core else _event_name(label)


def _variable_table(
    rows: list[tuple[Any, ...]], event_row: int, sheet: str
) -> tuple[int, dict[str, int]]:
    columns: dict[str, int] = {}
    for row_index in range(event_row + 1, min(len(rows), event_row + 30)):
        normalized = [_key(value) for value in rows[row_index]]
        field_columns = [index for index, value in enumerate(normalized) if value in FIELD_HEADERS]
        type_columns = [index for index, value in enumerate(normalized) if value in TYPE_HEADERS]
        if not field_columns or not type_columns:
            continue
        columns["field"] = field_columns[0]
        columns["type"] = type_columns[0]
        for index, value in enumerate(normalized):
            if value in STATUS_HEADERS:
                columns.setdefault("status", index)
            elif value in VALUE_HEADERS:
                columns.setdefault("values", index)
            elif value in SUMMARY_HEADERS:
                columns.setdefault("summary", index)
        return row_index, columns
    raise PlanError(f"{sheet}: event sheet has no variables/type table.")


def _column(row: tuple[Any, ...], columns: dict[str, int], name: str) -> Any:
    index = columns.get(name)
    return row[index] if index is not None and index < len(row) else None


def _portable_value(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (date, time)) else value


def _is_code_row(row: tuple[Any, ...]) -> bool:
    pattern = re.compile(
        r"(?:data\s*layer\s*\.\s*push|window\s*\.\s*data\s*layer|<script|```)", re.I
    )
    return any(pattern.search(str(value)) for value in row if _present(value))


def _parse_fields(
    rows: list[tuple[Any, ...]],
    sheet: str,
    variable_header: int,
    columns: dict[str, int],
    canonical_event: str,
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []
    errors: list[str] = []
    for row_index in range(variable_header + 1, len(rows)):
        row = rows[row_index]
        raw_field = _column(row, columns, "field")
        if not _present(raw_field):
            continue
        if _key(raw_field) in STOP_MARKERS:
            break
        source = f"{sheet}!{row_index + 1}"
        if _is_code_row(row):
            continue
        field = _field_name(raw_field)
        raw_type = _key(_column(row, columns, "type"))
        expected_type = TYPE_ALIASES.get(raw_type, raw_type) or None
        if not field:
            errors.append(f"{source}: variable name cannot be normalized.")
        elif expected_type and expected_type not in SUPPORTED_TYPES:
            errors.append(f"{source}: unsupported JSON type {expected_type!r}.")
        else:
            path = _field_path(canonical_event, field)
            if any(existing["path"].casefold() == path.casefold() for existing in fields):
                errors.append(f"{source}: duplicate variable path {path!r}.")
                continue
            status = _key(_column(row, columns, "status"))
            values = _portable_value(_column(row, columns, "values"))
            fields.append(
                {
                    "path": path,
                    "type": expected_type,
                    "required": status
                    not in {"optional", "facultative", "not_required", "non_obligatoire"},
                    **_declared_rule(values, expected_type, field, canonical_event),
                    "summary": _text(_column(row, columns, "summary")) or None,
                    "declared_values": values,
                    "source": source,
                }
            )
    if errors:
        raise PlanError("\n".join(errors))
    if not fields:
        raise PlanError(f"{sheet}: variable table contains no requirements.")
    return fields


def _selector(core: bool, canonical_event: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    if core:
        return {"anchor_fields": [field["path"] for field in fields]}
    selector: dict[str, Any] = {"event": canonical_event}
    if canonical_event != "gtm.custom_event":
        return selector
    discriminator = next((field for field in fields if field["path"] == "event_name"), None)
    if discriminator is not None and discriminator["rule"] in {"equals", "one_of"}:
        selector["event_name"] = (
            discriminator.get("expected")
            if discriminator["rule"] == "equals"
            else discriminator.get("allowed_values")
        )
    return selector


def _sheet_event(rows: list[tuple[Any, ...]], sheet: str) -> dict[str, Any] | None:
    metadata = _event_metadata(rows, sheet)
    if metadata is None:
        return None
    event_row, event_column, label, core, canonical_event = metadata
    variable_header, columns = _variable_table(rows, event_row, sheet)
    fields = _parse_fields(rows, sheet, variable_header, columns, canonical_event)

    action = rows[event_row][event_column + 2] if event_column + 2 < len(rows[event_row]) else None
    return {
        "event_id": _slug(sheet),
        "event_name": canonical_event,
        "label": (
            "Core DataLayer" if core else sheet if canonical_event == "gtm.custom_event" else label
        ),
        "is_core": core,
        "action": _text(action) or None,
        "source_sheet": sheet,
        "fields": fields,
        "dimensions": [
            {"path": field["path"], "values": field["allowed_values"]}
            for field in fields
            if field.get("rule") == "one_of"
        ],
        "selector": _selector(core, canonical_event, fields),
    }


def compile_xlsx(path: Path | str) -> dict[str, Any]:
    """Compile one XLSX without alternate adapters or silent recovery."""
    source = Path(path).resolve()
    if source.suffix.casefold() != ".xlsx":
        raise PlanError("Tracking plan must be exactly one .xlsx file.")
    if not source.is_file():
        raise PlanError(f"Tracking plan does not exist: {source}")
    try:
        workbook = load_workbook(source, read_only=True, data_only=False, keep_links=False)
    except (OSError, ValueError, BadZipFile, InvalidFileException) as error:
        raise PlanError(f"Cannot open XLSX tracking plan: {error}") from error

    details: dict[str, dict[str, Any]] = {}
    manifest: list[dict[str, Any]] = []
    try:
        for worksheet in workbook.worksheets:
            rows = [tuple(row) for row in worksheet.iter_rows(values_only=True)]
            if not any(any(_present(value) for value in row) for row in rows):
                manifest.append({"sheet": worksheet.title, "classification": "empty"})
                continue
            parsed = _sheet_event(rows, worksheet.title)
            if parsed is not None:
                event = parsed
                if event["event_id"] in details:
                    raise PlanError(f"Duplicate event sheet identity: {event['event_id']}")
                details[event["event_id"]] = event
                manifest.append(
                    {
                        "sheet": worksheet.title,
                        "classification": "event",
                        "event_id": event["event_id"],
                        "fields": len(event["fields"]),
                    }
                )
                continue
            indexed = _index_events(rows)
            if indexed:
                manifest.append(
                    {"sheet": worksheet.title, "classification": "index", "events": indexed}
                )
            else:
                manifest.append({"sheet": worksheet.title, "classification": "ignored"})
    finally:
        workbook.close()
    if not details:
        raise PlanError("No event sheet with event metadata and a variables/type table was found.")

    # Event-detail tabs are the only requirement source. Navigation/index tabs are often
    # incomplete and may contain display-only labels or typos; they never create, delete,
    # or rename requirements. Workbook tab order is therefore the deterministic plan order.
    events = [{**event, "plan_order": index} for index, event in enumerate(details.values(), 1)]
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now(),
        "source": {
            "filename": source.name,
            "sha256": _digest(source),
            "manifest": manifest,
        },
        "event_count": len(events),
        "field_count": sum(len(event["fields"]) for event in events),
        "events": events,
    }
