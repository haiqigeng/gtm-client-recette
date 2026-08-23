"""Staged, source-preserving tracking-plan compiler.

The compiler emits typed proof obligations and records event-local errors instead of
building run-wide cases or allowing later malformed rows to block the first valid event.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from openpyxl import load_workbook

from client_side_rules import valid_path

from .constants import ARCHETYPE_DOMAIN, CLAIM_ARCHETYPES, SCHEMA_VERSION, utc_now
from .predicates import PredicateError, compile_predicate
from .state import StateError, canonical_json, write_immutable_plan

HEADER_ALIASES = {
    "event_name": {"event", "event_name", "nom_evenement", "nom_événement"},
    "event_id": {"event_id", "event_group_id", "groupe_evenement", "groupe_événement"},
    "event_label": {"event_label", "label", "description"},
    "requirement_id": {"requirement_id", "id", "requirement", "exigence"},
    "claim_type": {"claim_type", "archetype", "type_requete", "type_exigence"},
    "field_path": {
        "field_path",
        "data_layer_path",
        "datalayer_path",
        "parameter",
        "parametre",
        "paramètre",
    },
    "expected_value": {"expected_value", "value", "valeur_attendue"},
    "allowed_values": {"allowed_values", "enum", "valeurs_autorisees", "valeurs_autorisées"},
    "expected_type": {"expected_type", "json_type", "type_json"},
    "match_rule": {"match_rule", "operator", "rule", "regle", "règle"},
    "occurrence": {"occurrence", "expected_occurrence", "count", "nombre"},
    "action": {"action", "trigger", "interaction", "declencheur", "déclencheur"},
    "url": {"url", "page", "route"},
    "locale": {"locale", "language", "langue"},
    "scenario": {"scenario", "case", "cas"},
    "tag": {"tag", "tag_name", "balise"},
    "destination": {"destination", "measurement_id", "pixel_id"},
    "source_mechanism": {"source_mechanism", "source", "mecanisme_source"},
    "resolved_path": {"resolved_path", "gtm_variable", "variable_gtm"},
    "runtime_path": {"runtime_path", "tag_parameter", "parametre_balise"},
    "request_path": {"request_path", "request_parameter", "parametre_requete"},
    "configuration_path": {"configuration_path", "tag_configuration_path"},
    "negative": {"negative", "expected_absence", "absence_attendue"},
    "condition": {"condition", "applicability", "applicabilite", "applicabilité"},
    "notes": {"notes", "comment", "commentaire", "example", "exemple"},
}

TABULAR_REQUIREMENT_FIELDS = frozenset(HEADER_ALIASES) - {
    "event_name",
    "event_id",
    "event_label",
    "notes",
}

ARCHETYPE_ALIASES = {
    "page": "reality",
    "business": "reality",
    "business_state": "reality",
    "source_state": "source",
    "source_event": "source",
    "tag": "gtm",
    "gtm_tag": "gtm",
    "request": "delivery",
    "destination": "delivery",
    "anomaly": "sequence",
    "behavior": "sequence",
    "behaviour": "sequence",
    "privacy": "safety",
}


def _slug(value: Any, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return text[:80] or fallback


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _list_value(value: Any) -> list[Any]:
    parsed = _json_value(value)
    if isinstance(parsed, list):
        return parsed
    if parsed in (None, ""):
        return []
    if isinstance(parsed, str):
        separator = "|" if "|" in parsed else ","
        return [item.strip() for item in parsed.split(separator) if item.strip()]
    return [parsed]


def _header_key(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.casefold()).strip("_")


def _headers(row: list[Any]) -> dict[int, str]:
    aliases = {
        _header_key(alias): target for target, values in HEADER_ALIASES.items() for alias in values
    }
    return {
        index: aliases[key]
        for index, value in enumerate(row)
        if (key := _header_key(value)) in aliases
    }


def _header_row(rows: list[tuple[Any, ...]]) -> tuple[int, dict[int, str]] | None:
    for index, row in enumerate(rows[:60]):
        mapping = _headers(list(row))
        if "event_name" in mapping.values() and (
            "field_path" in mapping.values()
            or "claim_type" in mapping.values()
            or "requirement_id" in mapping.values()
        ):
            return index, mapping
    return None


def _has_cell_value(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _tabular_rows(
    rows: list[tuple[Any, ...]],
    header_index: int,
    mapping: dict[int, str],
    reference_for_row: Callable[[int], str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read one recognized table without silently dropping continuation rows.

    Tracking workbooks commonly merge or visually fill down event identity cells. A
    non-empty requirement row may inherit the immediately preceding event identity,
    but never across a blank separator. Ambiguous orphan rows fail at intake instead of
    producing an incomplete plan that could later pass falsely.
    """

    output: list[dict[str, Any]] = []
    ignored: list[dict[str, str]] = []
    current_event_name: str | None = None
    current_event_id: str | None = None
    carried_event_rows = 0
    rows_seen = 0

    for source_row, raw in enumerate(rows[header_index + 1 :], start=header_index + 2):
        row = {name: raw[index] for index, name in mapping.items() if index < len(raw)}
        if not any(_has_cell_value(value) for value in row.values()):
            current_event_name = None
            current_event_id = None
            continue

        rows_seen += 1
        reference = reference_for_row(source_row)
        event_name = str(row.get("event_name") or "").strip()
        event_id = str(row.get("event_id") or "").strip()
        has_requirement = any(
            _has_cell_value(row.get(field)) for field in TABULAR_REQUIREMENT_FIELDS
        )

        if event_name:
            current_event_name = event_name
            current_event_id = event_id or None
        elif has_requirement:
            if current_event_name is None:
                raise StateError(
                    f"{reference} contains requirement data before an event name; "
                    "the row cannot be assigned safely."
                )
            if event_id and event_id != current_event_id:
                raise StateError(
                    f"{reference} introduces event group {event_id!r} without an event name; "
                    "the row cannot be assigned safely."
                )
            row["event_name"] = current_event_name
            if current_event_id:
                row["event_id"] = current_event_id
            carried_event_rows += 1
        elif _has_cell_value(row.get("notes")):
            ignored.append({"source": reference, "reason": "notes_only"})
            continue
        else:
            raise StateError(
                f"{reference} contains tabular data but no event name or requirement fields."
            )

        row["_source"] = reference
        output.append(row)

    return output, {
        "rows_seen": rows_seen,
        "requirements_compiled": len(output),
        "carried_event_rows": carried_event_rows,
        "rows_ignored": len(ignored),
        "ignored": ignored,
    }


def _rows_from_xlsx(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    output: list[dict[str, Any]] = []
    tables: list[str] = []
    ignored_sheets: list[str] = []
    diagnostics = {
        "rows_seen": 0,
        "requirements_compiled": 0,
        "carried_event_rows": 0,
        "rows_ignored": 0,
        "ignored": [],
    }
    try:
        for sheet in workbook.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            header = _header_row(rows)
            if header is None:
                ignored_sheets.append(sheet.title)
                continue
            header_index, mapping = header
            tables.append(sheet.title)
            table_rows, table_diagnostics = _tabular_rows(
                rows,
                header_index,
                mapping,
                lambda excel_row, title=sheet.title: f"{title}!{excel_row}",
            )
            output.extend(table_rows)
            for key in (
                "rows_seen",
                "requirements_compiled",
                "carried_event_rows",
                "rows_ignored",
            ):
                diagnostics[key] += table_diagnostics[key]
            diagnostics["ignored"].extend(table_diagnostics["ignored"])
    finally:
        workbook.close()
    if not output:
        raise StateError(
            "No worksheet contained an event column plus a requirement, field, or claim column."
        )
    return output, {
        "format": "xlsx",
        "tables": tables,
        "ignored_sheets": ignored_sheets,
        **diagnostics,
    }


def _rows_from_delimited(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    sample = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(sample[:8192], delimiters=",;\t")
    except csv.Error as error:
        raise StateError(f"Cannot detect the tracking-plan delimiter: {error}") from error
    values = list(csv.reader(sample.splitlines(), dialect))
    header = _header_row([tuple(row) for row in values])
    if header is None:
        raise StateError("No event column plus a requirement, field, or claim column was found.")
    header_index, mapping = header
    output, diagnostics = _tabular_rows(
        [tuple(row) for row in values],
        header_index,
        mapping,
        lambda line: f"line {line}",
    )
    if not output:
        raise StateError("The tracking-plan table contains no compilable requirement rows.")
    return output, {"format": "delimited", "tables": ["file"], **diagnostics}


def _requirements_from_rows(
    rows: list[dict[str, Any]], diagnostics: dict[str, Any]
) -> dict[str, Any]:
    requirements = []
    for index, row in enumerate(rows, start=1):
        event_name = str(row.get("event_name") or "").strip()
        expected = _json_value(row.get("expected_value"))
        rule = str(row.get("match_rule") or ("equals" if expected not in (None, "") else "present"))
        expectation = {
            "event_name": event_name,
            "field_path": str(row.get("field_path") or "event").strip(),
            "match_rule": rule,
            "expected_value": expected,
            "expected_type": row.get("expected_type"),
            "expected_occurrence": row.get("occurrence") or "once_per_action",
            "source_mechanism": row.get("source_mechanism") or "data_layer_push",
        }
        for key in (
            "claim_type",
            "resolved_path",
            "runtime_path",
            "request_path",
            "configuration_path",
            "condition",
        ):
            if row.get(key) not in (None, ""):
                expectation[key] = row[key]
        allowed = _list_value(row.get("allowed_values"))
        if allowed:
            expectation["allowed_values"] = allowed
        requirements.append(
            {
                "requirement_id": str(row.get("requirement_id") or f"REQ-{index:04d}"),
                "event_group_id": str(row.get("event_id") or event_name),
                "source": {"reference": row.get("_source"), "plan_order": index},
                "journey": {
                    "action": row.get("action"),
                    "url": row.get("url"),
                    "locale": row.get("locale"),
                },
                "expectation": expectation,
                "scenario": row.get("scenario"),
                "tag": row.get("tag"),
                "destination": row.get("destination"),
                "negative": str(row.get("negative") or "").casefold()
                in {"1", "true", "yes", "oui"},
            }
        )
    return {"requirements": requirements, "_normalization": diagnostics}


def _load_source(source: Path) -> tuple[dict[str, Any], str, str]:
    if source.is_dir():
        from import_ga4_tracking_plan_handoff import interpreted_requirements, verify_delivery

        handoff, plan, expected = verify_delivery(source)
        value = interpreted_requirements(handoff, plan, expected)
        return value, "ga4_tracking_plan_handoff", str(value.get("source_plan_sha256"))
    suffix = source.suffix.lower()
    if suffix == ".json":
        try:
            value = json.loads(source.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            raise StateError(f"Cannot read tracking plan: {error}") from error
        kind = "json"
    elif suffix in {".yaml", ".yml"}:
        try:
            value = yaml.safe_load(source.read_text(encoding="utf-8-sig"))
        except (OSError, yaml.YAMLError) as error:
            raise StateError(f"Cannot read tracking plan: {error}") from error
        kind = "yaml"
    elif suffix in {".xlsx", ".xlsm"}:
        rows, diagnostics = _rows_from_xlsx(source)
        return _requirements_from_rows(rows, diagnostics), "xlsx", _sha256(source)
    elif suffix in {".csv", ".tsv"}:
        rows, diagnostics = _rows_from_delimited(source)
        return _requirements_from_rows(rows, diagnostics), "delimited", _sha256(source)
    else:
        raise StateError("Tracking plan must be JSON, YAML, XLSX, CSV, TSV, or a handoff folder.")
    if not isinstance(value, dict):
        raise StateError("Tracking-plan root must be an object.")
    return value, kind, _sha256(source)


def _normalize_scope(scope: dict[str, Any] | None) -> dict[str, Any]:
    value = dict(scope or {})
    if value.get("approved") is not True:
        raise StateError(
            "Scope must contain approved=true after the user accepts the test boundary."
        )
    origins = value.get("origins", [])
    if isinstance(origins, str):
        origins = [origins]
    if not isinstance(origins, list) or not all(str(item).strip() for item in origins):
        raise StateError("Approved scope needs at least one non-empty origin.")
    value["origins"] = [str(item).strip() for item in origins]
    for key in ("expected_container", "destination", "tag_scope"):
        item = value.get(key, [])
        if isinstance(item, str):
            item = [item]
        value[key] = [str(entry) for entry in item if str(entry).strip()]
    bad_containers = [item for item in value["expected_container"] if not item.startswith("GTM-")]
    bad_destinations = [item for item in value["destination"] if item.startswith("GTM-")]
    if bad_containers:
        raise StateError("Expected container IDs must use the GTM- identity type.")
    if bad_destinations:
        raise StateError("Destination IDs cannot use the GTM container identity type.")
    value.setdefault("certify_tags", True)
    value.setdefault("browser_send_required", bool(value["certify_tags"]))
    value.setdefault("delivery_mode", "gtm_browser" if value["certify_tags"] else "source_only")
    return value


def _normalize_tag(value: Any, index: int) -> dict[str, Any]:
    row = value if isinstance(value, dict) else {"tag_name": str(value)}
    identity = str(row.get("tag_id") or row.get("tag_name") or row.get("name") or "").strip()
    if not identity:
        identity = f"tag-{index}"
    expected = str(row.get("expected") or row.get("expectation") or "fire").casefold()
    if expected not in {"fire", "not_fire", "optional"}:
        expected = "fire"
    return {
        "tag_id": identity,
        "tag_name": str(row.get("tag_name") or row.get("name") or identity),
        "category": str(row.get("category") or "").strip() or None,
        "expected": expected,
        "destination": row.get("destination"),
        "configuration": row.get("configuration", row.get("expected_configuration")),
        "consent_requirements": row.get("consent_requirements", []),
        "browser_send_required": row.get("browser_send_required"),
    }


def _tag_in_scope(tag: dict[str, Any], scope: dict[str, Any]) -> bool:
    """Apply an explicit tag-category scope without guessing unknown vendors."""
    requested = {
        re.sub(r"[^a-z0-9]+", "", str(value).casefold())
        for value in scope.get("tag_scope", [])
        if str(value).strip()
    }
    if not requested:
        return True
    searchable = re.sub(
        r"[^a-z0-9]+",
        "",
        " ".join(
            str(value or "")
            for value in (tag.get("category"), tag.get("tag_name"), tag.get("tag_id"))
        ).casefold(),
    )
    aliases = {
        "ga4": {"ga4", "googleanalytics4", "googleanalyticsevent", "googletag"},
        "googleads": {"googleads", "ads", "adwords"},
    }
    for item in requested:
        candidates = aliases.get(item, {item})
        if any(candidate and candidate in searchable for candidate in candidates):
            return True
    return False


def _tag_protocol(tag: dict[str, Any]) -> str | None:
    searchable = " ".join(
        str(value or "") for value in (tag.get("category"), tag.get("tag_name"), tag.get("tag_id"))
    ).casefold()
    if "ga4" in searchable or "analytics" in searchable:
        return "ga4"
    if "google ads" in searchable or "adwords" in searchable:
        return "google_ads"
    return None


def _scenario(value: Any, event_id: str, index: int, *, negative: bool = False) -> dict[str, Any]:
    row = value if isinstance(value, dict) else {"label": str(value)}
    is_negative = negative or row.get("negative") is True
    return {
        "scenario_id": str(row.get("scenario_id") or f"{_slug(event_id, 'event')}-S{index:02d}"),
        "label": str(row.get("label") or row.get("name") or f"Scenario {index}"),
        "values": row.get("values", {}),
        "explicit": True,
        "negative": is_negative,
        "role": "NEGATIVE" if is_negative else row.get("role"),
    }


class _ClaimBuilder:
    def __init__(self, event_id: str) -> None:
        self.event_id = event_id
        self.claims: list[dict[str, Any]] = []
        self._keys: dict[str, str] = {}
        self.warnings: list[str] = []

    def add(
        self,
        archetype: str,
        target: dict[str, Any],
        predicate: dict[str, Any],
        evidence: list[str],
        source: dict[str, Any],
        *,
        applicability: dict[str, Any] | None = None,
        label: str | None = None,
    ) -> None:
        if archetype not in CLAIM_ARCHETYPES:
            raise PredicateError(f"Unsupported claim archetype '{archetype}'.")
        core = {
            "archetype": archetype,
            "domain": ARCHETYPE_DOMAIN[archetype],
            "target": target,
            "predicate": predicate,
            "evidence": evidence,
            "applicability": applicability or {},
        }
        key = canonical_json(core)
        if key in self._keys:
            self.warnings.append(
                f"Duplicate claim at {source.get('reference') or 'unknown source'} matches {self._keys[key]}."
            )
            return
        claim_id = f"{_slug(self.event_id, 'event')}::C{len(self.claims) + 1:03d}"
        self._keys[key] = claim_id
        self.claims.append(
            {"claim_id": claim_id, **core, "source": source, "label": label or target.get("label")}
        )


def _occurrence_predicate(value: Any, *, negative: bool = False) -> dict[str, Any]:
    if negative:
        return {"operator": "count", "exact": 0}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"operator": "count", "exact": value}
    normalized = str(value or "once_per_action").casefold()
    if normalized in {"none", "never", "absent", "zero"}:
        return {"operator": "count", "exact": 0}
    if normalized in {"one_or_more", "at_least_once"}:
        return {"operator": "count", "minimum": 1}
    return {"operator": "count", "exact": 1}


def _requirement_source(row: dict[str, Any], index: int) -> dict[str, Any]:
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    return {
        **source,
        "reference": source.get("reference") or row.get("_source") or f"requirement {index}",
        "plan_order": source.get("plan_order", index),
        "requirement_id": str(row.get("requirement_id") or f"REQ-{index:04d}"),
    }


def _safe_path(value: Any, location: str) -> str:
    path = str(value or "").strip()
    if not path:
        raise PredicateError(f"{location}: field path is empty.")
    if len(path) > 512 or "\n" in path or "```" in path or not valid_path(path):
        raise PredicateError(f"{location}: invalid or implausible field path '{path[:80]}'.")
    return path


def _event_tags_and_destinations(
    raw: dict[str, Any], requirements: list[dict[str, Any]], scope: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[str]]:
    tag_values = list(raw.get("tags", [])) if isinstance(raw.get("tags"), list) else []
    destination_values = (
        list(raw.get("destinations", [])) if isinstance(raw.get("destinations"), list) else []
    )
    for row in requirements:
        expectation = row.get("expectation") if isinstance(row.get("expectation"), dict) else row
        if row.get("tag") or expectation.get("tag_name"):
            tag_values.append(row.get("tag") or expectation.get("tag_name"))
        if row.get("destination") or expectation.get("destination"):
            destination_values.append(row.get("destination") or expectation.get("destination"))

    tags: list[dict[str, Any]] = []
    seen_tags: set[str] = set()
    for index, value in enumerate(tag_values, start=1):
        tag = _normalize_tag(value, index)
        if tag["tag_id"] not in seen_tags and _tag_in_scope(tag, scope):
            tags.append(tag)
            seen_tags.add(tag["tag_id"])

    destinations: list[str] = []
    for value in [*destination_values, *scope.get("destination", [])]:
        identity = str(value or "").strip()
        if identity and identity not in destinations:
            destinations.append(identity)
    if len(destinations) == 1:
        for tag in tags:
            if tag.get("destination") in (None, ""):
                tag["destination"] = destinations[0]
    return tags, destinations


def _claim_target(
    archetype: str,
    path: str,
    source_event_name: str | None,
    expectation: dict[str, Any],
) -> dict[str, Any]:
    target = {
        "surface": "source",
        "path": path,
        "event_name": source_event_name,
        "label": f"Source - {path}",
    }
    variants = {
        "gtm": ("preview", "resolved_variable", f"Resolved variable - {path}"),
        "delivery": ("network", "request_parameter", f"Request parameter - {path}"),
        "reality": ("page", "page_value", f"Page/business value - {path}"),
        "sequence": ("stream", "order", f"Sequence - {path}"),
    }
    if archetype in variants:
        surface, check, label = variants[archetype]
        target.update({"surface": surface, "check": check, "label": label})
    if archetype == "delivery":
        target["destination"] = expectation.get("destination")
    return target


def _add_explicit_mirrors(
    builder: _ClaimBuilder,
    expectation: dict[str, Any],
    predicate: dict[str, Any],
    source: dict[str, Any],
    applicability: dict[str, Any],
    source_event_name: str | None,
    inferred_tag: Any,
    inferred_destination: Any,
    location: str,
) -> None:
    mirrors = (
        ("resolved_path", "gtm", "resolved_variable", "preview"),
        ("configuration_path", "gtm", "tag_configuration", "preview"),
        ("runtime_path", "delivery", "runtime_parameter", "preview"),
        ("request_path", "delivery", "request_parameter", "network"),
    )
    for key, mirror_type, check, evidence in mirrors:
        if expectation.get(key) in (None, ""):
            continue
        mirror_path = _safe_path(expectation[key], location)
        builder.add(
            mirror_type,
            {
                "surface": evidence,
                "check": check,
                "path": mirror_path,
                "event_name": expectation.get(
                    "resolved_event_name", expectation.get("forward_event_name", source_event_name)
                ),
                "tag_id": inferred_tag,
                "destination": inferred_destination,
                "label": f"{check.replace('_', ' ').title()} - {mirror_path}",
            },
            predicate,
            [evidence],
            source,
            applicability=applicability,
        )


def _add_ga4_forwarding_claims(
    builder: _ClaimBuilder,
    expectation: dict[str, Any],
    predicate: dict[str, Any],
    source: dict[str, Any],
    applicability: dict[str, Any],
    path: str,
    source_event_name: str | None,
    ga4_tags: list[dict[str, Any]],
    scope: dict[str, Any],
) -> None:
    if expectation.get("resolved_path") in (None, ""):
        builder.add(
            "gtm",
            {
                "surface": "preview",
                "check": "resolved_variable",
                "path": path,
                "event_name": source_event_name,
                "label": f"Resolved variable - {path}",
            },
            predicate,
            ["preview"],
            source,
            applicability=applicability,
        )
    for tag in ga4_tags:
        if expectation.get("runtime_path") in (None, ""):
            builder.add(
                "delivery",
                {
                    "surface": "preview",
                    "check": "runtime_parameter",
                    "path": path,
                    "event_name": source_event_name,
                    "tag_id": tag["tag_id"],
                    "destination": tag.get("destination"),
                    "label": f"Tag runtime - {tag['tag_name']} - {path}",
                },
                predicate,
                ["preview"],
                source,
                applicability=applicability,
            )
        send_required = tag.get("browser_send_required")
        if send_required is None:
            send_required = scope.get("browser_send_required", True)
        if send_required and expectation.get("request_path") in (None, ""):
            builder.add(
                "delivery",
                {
                    "surface": "network",
                    "check": "request_parameter",
                    "path": path,
                    "event_name": source_event_name,
                    "tag_id": tag["tag_id"],
                    "destination": tag.get("destination"),
                    "protocol": "ga4",
                    "label": f"Browser parameter - {tag['tag_name']} - {path}",
                },
                predicate,
                ["network"],
                source,
                applicability=applicability,
            )


def _compile_requirement(
    builder: _ClaimBuilder,
    row: dict[str, Any],
    index: int,
    *,
    tags: list[dict[str, Any]],
    destinations: list[str],
    scope: dict[str, Any],
    source_event_name: str | None,
    source_only: bool,
    state_only: bool,
) -> None:
    expectation = row.get("expectation") if isinstance(row.get("expectation"), dict) else row
    source = _requirement_source(row, index)
    location = str(source["reference"])
    explicit = str(expectation.get("claim_type") or row.get("claim_type") or "source").casefold()
    archetype = ARCHETYPE_ALIASES.get(explicit, explicit)
    if archetype not in CLAIM_ARCHETYPES:
        raise PredicateError(f"{location}: unsupported claim type '{explicit}'.")
    path = _safe_path(expectation.get("field_path", "event"), location)
    predicate = compile_predicate(expectation, location=location)
    condition = expectation.get("condition")
    applicability = condition if isinstance(condition, dict) else {}
    builder.add(
        archetype,
        _claim_target(archetype, path, source_event_name, expectation),
        predicate,
        ["datalayer", "source"] if archetype == "source" else [archetype],
        source,
        applicability=applicability,
    )

    inferred_tag = expectation.get("tag_name")
    if inferred_tag in (None, "") and len(tags) == 1:
        inferred_tag = tags[0]["tag_id"]
    inferred_destination = expectation.get("destination")
    if inferred_destination in (None, "") and len(destinations) == 1:
        inferred_destination = destinations[0]
    _add_explicit_mirrors(
        builder,
        expectation,
        predicate,
        source,
        applicability,
        source_event_name,
        inferred_tag,
        inferred_destination,
        location,
    )

    ga4_tags = [
        tag for tag in tags if _tag_protocol(tag) == "ga4" and tag.get("expected") == "fire"
    ]
    forwarding_required = (
        expectation.get("source_only") is not True
        and expectation.get("forwarding_required") is not False
    )
    ga4_scope = any(str(item).casefold() == "ga4" for item in scope.get("tag_scope", []))
    if (
        archetype == "source"
        and forwarding_required
        and not source_only
        and not state_only
        and (ga4_tags or ga4_scope)
    ):
        _add_ga4_forwarding_claims(
            builder,
            expectation,
            predicate,
            source,
            applicability,
            path,
            source_event_name,
            ga4_tags,
            scope,
        )
    for business_rule in expectation.get("business_rules", []):
        builder.add(
            "reality",
            {"surface": "business", "check": "relationship", "label": "Business relationship"},
            compile_predicate(
                {"operator": "relationship", "relationship": business_rule}, location=location
            ),
            ["page", "datalayer"],
            source,
            applicability=applicability,
        )


def _add_event_tag_claims(
    builder: _ClaimBuilder,
    raw: dict[str, Any],
    event_name: str | None,
    tags: list[dict[str, Any]],
    destinations: list[str],
    scope: dict[str, Any],
    source: dict[str, Any],
) -> None:
    occurrence = _occurrence_predicate(
        raw.get("expected_occurrence"), negative=raw.get("negative") is True
    )
    builder.add(
        "gtm",
        {
            "surface": "preview",
            "check": "event_match",
            "event_name": event_name,
            "label": "GTM Preview event match",
        },
        occurrence,
        ["preview"],
        source,
    )
    builder.add(
        "gtm",
        {
            "surface": "preview",
            "check": "tag_inventory",
            "event_name": event_name,
            "label": "GTM fired/non-fired inventory",
        },
        {"operator": "present"},
        ["preview"],
        source,
    )
    if not tags and scope.get("tag_scope"):
        builder.add(
            "gtm",
            {
                "surface": "preview",
                "check": "in_scope_tag_discovery",
                "event_name": event_name,
                "tag_scope": scope.get("tag_scope", []),
                "label": "Runtime in-scope tag discovery",
            },
            {"operator": "present"},
            ["preview"],
            source,
        )
    for tag in tags:
        _add_one_tag_claims(builder, tag, event_name, destinations, scope, source)
    if not tags and scope.get("browser_send_required"):
        for destination in destinations:
            builder.add(
                "delivery",
                {
                    "surface": "network",
                    "check": "destination_request",
                    "destination": destination,
                    "event_name": event_name,
                    "label": f"Destination routing - {destination}",
                },
                occurrence,
                ["network"],
                source,
            )


def _add_one_tag_claims(
    builder: _ClaimBuilder,
    tag: dict[str, Any],
    event_name: str | None,
    destinations: list[str],
    scope: dict[str, Any],
    source: dict[str, Any],
) -> None:
    builder.add(
        "gtm",
        {
            "surface": "preview",
            "check": "tag_configuration",
            "event_name": event_name,
            "tag_id": tag["tag_id"],
            "tag": tag,
            "label": f"Tag configuration - {tag['tag_name']}",
        },
        {"operator": "present"},
        ["preview"],
        source,
    )
    expected = tag["expected"]
    if expected == "not_fire":
        firing_predicate = {"operator": "count", "exact": 0}
    elif expected == "optional":
        firing_predicate = {"operator": "count", "minimum": 0, "maximum": 1}
    else:
        firing_predicate = {"operator": "count", "exact": 1}
    builder.add(
        "gtm",
        {
            "surface": "preview",
            "check": "tag_firing",
            "event_name": event_name,
            "tag_id": tag["tag_id"],
            "tag": tag,
            "label": f"Tag firing - {tag['tag_name']}",
        },
        firing_predicate,
        ["preview"],
        source,
    )
    send_required = tag.get("browser_send_required")
    if send_required is None:
        send_required = scope.get("browser_send_required", True)
    if not send_required or expected == "optional":
        return
    destination = tag.get("destination")
    if destination in (None, "") and len(destinations) == 1:
        destination = destinations[0]
    builder.add(
        "delivery",
        {
            "surface": "network",
            "check": "tag_request",
            "tag_id": tag["tag_id"],
            "tag": tag,
            "destination": destination,
            "event_name": event_name if _tag_protocol(tag) == "ga4" else None,
            "protocol": _tag_protocol(tag),
            "label": f"Browser request - {tag['tag_name']}",
        },
        firing_predicate,
        ["preview", "network"],
        source,
    )


def _compile_event(
    raw: dict[str, Any], requirements: list[dict[str, Any]], order: int, scope: dict[str, Any]
) -> dict[str, Any]:
    event_id = str(
        raw.get("event_id")
        or raw.get("event_group_id")
        or raw.get("event_name")
        or raw.get("name")
        or f"event-{order}"
    )
    event_name_value = raw.get("event_name", raw.get("name"))
    event_name = str(event_name_value).strip() if event_name_value not in (None, "") else None
    state_only = raw.get("state_only") is True or str(raw.get("mode") or "").casefold() in {
        "state",
        "state_only",
        "core_state",
    }
    source_event_name = None if state_only else event_name
    source_only = raw.get("source_only") is True or not scope.get("certify_tags", True)
    errors: list[str] = []
    builder = _ClaimBuilder(event_id)
    journey = (
        raw.get("journey")
        if isinstance(raw.get("journey"), dict)
        else {
            "action": raw.get("trigger", raw.get("action")),
            "url": raw.get("url"),
            "locale": raw.get("locale"),
        }
    )

    tags, destinations = _event_tags_and_destinations(raw, requirements, scope)

    default_source = {"reference": f"event {event_id}", "plan_order": order}
    builder.add(
        "reality",
        {"surface": "page", "check": "valid_outcome", "label": "Page/API outcome"},
        {"operator": "present"},
        ["page"],
        default_source,
    )
    if event_name and not state_only:
        builder.add(
            "source",
            {
                "surface": "source",
                "check": "event_occurrence",
                "event_name": event_name,
                "label": f"dataLayer/direct source - {event_name}",
            },
            _occurrence_predicate(
                raw.get("expected_occurrence"), negative=raw.get("negative") is True
            ),
            ["datalayer", "source"],
            default_source,
        )

    for index, row in enumerate(requirements, start=1):
        try:
            _compile_requirement(
                builder,
                row,
                index,
                tags=tags,
                destinations=destinations,
                scope=scope,
                source_event_name=source_event_name,
                source_only=source_only,
                state_only=state_only,
            )
        except PredicateError as error:
            errors.append(str(error))

    if not source_only and not state_only:
        _add_event_tag_claims(builder, raw, event_name, tags, destinations, scope, default_source)

    builder.add(
        "sequence",
        {"surface": "stream", "check": "surrounding_behavior", "label": "Sequence/anomaly stream"},
        {"operator": "present"},
        ["datalayer", "preview", "network", "lifecycle", "page"],
        default_source,
    )
    builder.add(
        "safety",
        {"surface": "all", "check": "sensitive_data", "label": "Data safety"},
        {"operator": "present"},
        ["page", "datalayer", "source", "preview", "network"],
        default_source,
    )

    explicit = raw.get("scenarios") if isinstance(raw.get("scenarios"), list) else []
    negative = (
        raw.get("negative_scenarios") if isinstance(raw.get("negative_scenarios"), list) else []
    )
    scenarios = [
        _scenario(value, event_id, index, negative=value in negative)
        for index, value in enumerate([*explicit, *negative], start=1)
    ]
    return {
        "event_id": event_id,
        "event_name": event_name,
        "label": str(raw.get("label") or raw.get("event_label") or event_name or event_id),
        "plan_order": order,
        "mode": "state_only" if state_only else "named_event",
        "journey": journey,
        "claims": builder.claims,
        "claim_count": len(builder.claims),
        "tags": tags,
        "destinations": destinations,
        "explicit_scenarios": scenarios,
        "known_dimensions": raw.get("known_dimensions", []),
        "allowed_companions": raw.get("allowed_companions", []),
        "required_consent_signals": raw.get("required_consent_signals", []),
        "compile_errors": errors,
        "compile_warnings": builder.warnings,
        "executable": not errors,
    }


def _event_inputs(value: dict[str, Any]) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    if isinstance(value.get("events"), list):
        output = []
        for event in value["events"]:
            if not isinstance(event, dict):
                continue
            requirements = event.get("requirements")
            if not isinstance(requirements, list):
                requirements = event.get("claims") if isinstance(event.get("claims"), list) else []
            output.append((event, [item for item in requirements if isinstance(item, dict)]))
        return output
    if not isinstance(value.get("requirements"), list):
        raise StateError("Tracking plan needs an events or requirements array.")
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for index, row in enumerate(value["requirements"], start=1):
        if not isinstance(row, dict):
            continue
        expectation = row.get("expectation") if isinstance(row.get("expectation"), dict) else row
        name = str(
            expectation.get("event_name")
            or row.get("event_name")
            or row.get("event_group_id")
            or ""
        ).strip()
        if not name:
            raise StateError(f"Requirement {index} has no event group/name.")
        group = str(row.get("event_group_id") or name)
        source = row.get("source") if isinstance(row.get("source"), dict) else {}
        normalized = {**row, "source": {**source, "plan_order": source.get("plan_order", index)}}
        grouped.setdefault(group, []).append(normalized)
    return [
        (
            {
                "event_id": group,
                "event_name": rows[0].get("expectation", rows[0]).get("event_name", group),
                "journey": rows[0].get("journey", {}),
            },
            rows,
        )
        for group, rows in grouped.items()
    ]


def normalize_plan(
    source: Path | str,
    *,
    run_id: str | None = None,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(source).expanduser().resolve()
    value, source_kind, digest = _load_source(path)
    normalized_scope = _normalize_scope(scope)
    events = [
        _compile_event(event, requirements, order, normalized_scope)
        for order, (event, requirements) in enumerate(_event_inputs(value), start=1)
    ]
    if not events:
        raise StateError("Tracking plan contains no event groups.")
    claim_count = sum(event["claim_count"] for event in events)
    requirement_count = sum(len(requirements) for _, requirements in _event_inputs(value))
    source_details = {"kind": source_kind, "path": str(path), "sha256": digest}
    if isinstance(value.get("_normalization"), dict):
        source_details["normalization"] = value["_normalization"]
    plan = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id or f"GTM-RECETTE-{uuid4().hex[:12].upper()}",
        "created_at": utc_now(),
        "source": source_details,
        "scope": normalized_scope,
        "event_count": len(events),
        "requirement_count": requirement_count,
        "claim_count": claim_count,
        "events": events,
    }
    plan["compile_digest"] = hashlib.sha256(canonical_json(events).encode("utf-8")).hexdigest()
    return plan


def initialize_run(
    source: Path | str,
    run_dir: Path | str,
    *,
    run_id: str | None = None,
    scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = normalize_plan(source, run_id=run_id, scope=scope)
    write_immutable_plan(run_dir, plan)
    return plan
