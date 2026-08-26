#!/usr/bin/env python3
"""Deterministic five-layer judgement for one fixed evidence bundle."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from state import RunError

PRIORITY = {
    "NOT_APPLICABLE": 0,
    "PASS": 1,
    "PENDING": 2,
    "REVIEW": 3,
    "BLOCKED": 4,
    "FAIL": 5,
}
LAYER_ORDER = (
    "Page/action reality",
    "Data Layer API Call",
    "GTM Tags",
    "Browser request",
    "Surrounding behavior",
)
MISSING = object()
TECHNICAL_EVENT = re.compile(
    r"^(?:gtm\.|message$|container loaded$|dom ready$|window loaded$|trigger group$|consent)",
    re.I,
)


def worst(values: list[str], default: str = "PASS") -> str:
    valid = [value for value in values if value in PRIORITY]
    return max(valid, key=PRIORITY.__getitem__) if valid else default


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def strict_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def _tokens(path: str) -> list[tuple[str, bool]]:
    output = []
    for part in path.split("."):
        array = part.endswith("[]")
        name = part[:-2] if array else part
        output.append((name, array))
    return output


def path_values(value: Any, path: str) -> list[Any]:
    current = [value]
    for name, array in _tokens(path):
        next_values: list[Any] = []
        for candidate in current:
            if not isinstance(candidate, dict):
                continue
            selected = MISSING
            if name in candidate:
                selected = candidate[name]
            else:
                match = next(
                    (key for key in candidate if str(key).casefold() == name.casefold()), None
                )
                if match is not None:
                    selected = candidate[match]
            if selected is MISSING:
                continue
            if array:
                if isinstance(selected, list):
                    next_values.extend(selected)
            else:
                next_values.append(selected)
        current = next_values
    return current


def _leaf_values(value: Any, leaf: str) -> list[Any]:
    output: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).casefold()).strip("_")
            normalized_leaf = re.sub(r"[^a-z0-9]+", "_", leaf.casefold()).strip("_")
            if normalized_key == normalized_leaf:
                output.extend(child if isinstance(child, list) else [child])
            else:
                output.extend(_leaf_values(child, leaf))
    elif isinstance(value, list):
        for child in value:
            output.extend(_leaf_values(child, leaf))
    return output


def _surface_values(payload: Any, path: str, surface: str) -> list[Any]:
    values = path_values(payload, path)
    if values or surface == "api_call":
        return values
    leaf = path.split(".")[-1].replace("[]", "")
    return _leaf_values(payload, leaf)


def _compact(value: Any, limit: int = 280) -> Any:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return text if len(text) <= limit else text[: limit - 3] + "..."
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _check(
    status: str,
    check: str,
    reason: str,
    *,
    path: str | None = None,
    expected: Any = None,
    observed: Any = None,
    check_next: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "check": check,
        "path": path,
        "reason": reason,
        "expected": _compact(expected) if expected is not None else None,
        "observed": _compact(observed) if observed is not None else None,
        "check_next": check_next,
    }


def _expected_for(reality: dict[str, Any], path: str) -> Any:
    expected = reality.get("expected", {})
    if isinstance(expected, dict):
        if path in expected:
            return expected[path]
        values = path_values(expected, path)
        if values:
            return values if "[]" in path else values[0]
        leaf = path.split(".")[-1].replace("[]", "")
        for key, value in expected.items():
            if str(key).split(".")[-1].replace("[]", "").casefold() == leaf.casefold():
                return value
    return MISSING


def _value_satisfies(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(strict_equal(left, right) for left, right in zip(actual, expected, strict=True))
        )
    if isinstance(actual, list):
        return bool(actual) and all(strict_equal(value, expected) for value in actual)
    return strict_equal(actual, expected)


def _availability_check(
    field: dict[str, Any], path: str, values: list[Any], observed: Any, surface: str
) -> dict[str, Any] | None:
    if observed is MISSING:
        status = "FAIL" if field.get("required", True) else "NOT_APPLICABLE"
        return _check(
            status,
            f"{surface}.field",
            "Required planned field is absent."
            if status == "FAIL"
            else "Optional field is absent.",
            path=path,
            expected="present" if status == "FAIL" else "optional",
            observed="absent",
            check_next=f"{surface} value for {path}",
        )
    expected_type = field.get("type")
    typed_values = values if "[]" in path else [observed]
    invalid = [
        json_type(value)
        for value in typed_values
        if expected_type and not _type_matches(value, expected_type)
    ]
    if not invalid:
        return None
    return _check(
        "FAIL",
        f"{surface}.type",
        "Observed JSON type differs from the tracking plan.",
        path=path,
        expected=expected_type,
        observed=invalid,
        check_next=f"{surface} type for {path}",
    )


def _plan_expectation(
    field: dict[str, Any], path: str, values: list[Any], observed: Any
) -> tuple[bool, Any]:
    rule = field.get("rule", "present")
    if rule == "equals":
        expected = field.get("expected")
        return _value_satisfies(observed, expected), expected
    if rule == "one_of":
        expected = field.get("allowed_values", [])
        candidates = values if "[]" in path else [observed]
        passed = all(
            any(strict_equal(value, option) for option in expected) for value in candidates
        )
        return passed, expected
    return bool(values), "present"


def _plan_value_check(
    field: dict[str, Any],
    path: str,
    values: list[Any],
    observed: Any,
    contextual: Any,
    surface: str,
) -> dict[str, Any]:
    passed, expected = _plan_expectation(field, path, values, observed)
    status = "PASS" if passed else "FAIL"
    reason = (
        "Value satisfies the tracking-plan rule."
        if passed
        else "Value violates the tracking-plan rule."
    )
    return _check(
        status,
        f"{surface}.plan_value",
        reason,
        path=path,
        expected=expected,
        observed=observed,
        check_next=None if passed else f"{surface} value for {path}",
    )


def _reality_value_check(path: str, observed: Any, contextual: Any, surface: str) -> dict[str, Any]:
    passed = _value_satisfies(observed, contextual)
    return _check(
        "PASS" if passed else "FAIL",
        f"{surface}.reality_value",
        "Value agrees with the real interaction context."
        if passed
        else "Value contradicts the real interaction context.",
        path=path,
        expected=contextual,
        observed=observed,
        check_next=None if passed else f"Website state and {surface} value for {path}",
    )


def _source_value_check(
    path: str, observed: Any, source_payload: Any, surface: str
) -> dict[str, Any] | None:
    if source_payload is MISSING:
        return None
    source_values = path_values(source_payload, path)
    source_observed: Any = (
        source_values if "[]" in path else source_values[0] if source_values else MISSING
    )
    if source_observed is MISSING:
        return None
    coherent = _value_satisfies(observed, source_observed)
    return _check(
        "PASS" if coherent else "FAIL",
        f"{surface}.source_coherence",
        "Value agrees with the exact Data Layer API Call."
        if coherent
        else "Value differs from the exact Data Layer API Call.",
        path=path,
        expected=source_observed,
        observed=observed,
        check_next=None if coherent else f"Cross-layer mapping for {path}",
    )


def _field_checks(
    fields: list[dict[str, Any]],
    payload: Any,
    reality: dict[str, Any],
    *,
    surface: str,
    source_payload: Any = MISSING,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for field in fields:
        path = field["path"]
        values = _surface_values(payload, path, surface)
        observed: Any = values if "[]" in path else values[0] if values else MISSING
        unavailable = _availability_check(field, path, values, observed, surface)
        if unavailable:
            output.append(unavailable)
            continue
        contextual = _expected_for(reality, path)
        output.append(_plan_value_check(field, path, values, observed, contextual, surface))
        if contextual is not MISSING:
            output.append(_reality_value_check(path, observed, contextual, surface))
        coherence = _source_value_check(path, observed, source_payload, surface)
        if coherence:
            output.append(coherence)
    return output


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return json_type(value) == expected


def _layer(name: str, checks: list[dict[str, Any]], attributable: bool) -> dict[str, Any]:
    status = worst([row["status"] for row in checks], default="BLOCKED")
    return {
        "layer": name,
        "status": status,
        "checks": checks,
        "passed": sum(row["status"] == "PASS" for row in checks),
        "total": len(checks),
        "attributable": attributable,
    }


def _completeness(surface: str, value: dict[str, Any]) -> list[dict[str, Any]]:
    if value.get("complete") is True:
        return [_check("PASS", f"{surface}.complete", "Evidence surface is complete.")]
    return [
        _check(
            "BLOCKED",
            f"{surface}.complete",
            str(value.get("reason") or "Evidence surface is incomplete."),
            expected="complete attributable evidence",
            observed="incomplete",
            check_next=surface,
        )
    ]


def _reality_layer(reality: dict[str, Any]) -> dict[str, Any]:
    checks = _completeness("reality", reality)
    attributable = reality.get("attributable") is True
    if not attributable:
        checks.append(
            _check(
                "BLOCKED",
                "reality.attribution",
                "Page/action evidence is not attributable to the selected action.",
                check_next="Target page and action outcome",
            )
        )
        return _layer(LAYER_ORDER[0], checks, False)
    page = reality.get("page", {}) if isinstance(reality.get("page"), dict) else {}
    status_code = page.get("status_code")
    page_proven = bool(str(page.get("url") or "").strip()) and (
        type(status_code) is int or page.get("reachable") is True
    )
    dead = (type(status_code) is int and status_code >= 400) or page.get("soft_404") is True
    checks.append(
        _check(
            "FAIL" if dead else "PASS" if page_proven else "BLOCKED",
            "reality.page",
            "Target is a dead, error, or soft-404 page."
            if dead
            else "Target page is reachable and not a detected error page."
            if page_proven
            else "Page reachability was not captured.",
            expected="reachable intended page",
            observed={"url": page.get("url"), "status": status_code},
            check_next=None if page_proven and not dead else "Target URL and page content",
        )
    )
    outcome = reality.get("outcome")
    checks.append(
        _check(
            "PASS" if outcome is True else "FAIL" if outcome is False else "BLOCKED",
            "reality.outcome",
            "Visible interaction outcome is valid."
            if outcome is True
            else "Visible interaction outcome failed."
            if outcome is False
            else "Visible interaction outcome was not captured.",
            expected="successful intended outcome",
            observed=outcome,
            check_next=None if outcome is True else "Visible result of the interaction",
        )
    )
    checks.extend(_finding_checks(reality.get("findings"), "reality"))
    return _layer(LAYER_ORDER[0], checks, True)


def _selected_payload(source: dict[str, Any]) -> Any:
    selected = source.get("selected")
    if not isinstance(selected, dict):
        return MISSING
    if isinstance(selected.get("payload"), dict):
        return selected["payload"]
    arguments = selected.get("arguments")
    if isinstance(arguments, list):
        for value in reversed(arguments):
            if isinstance(value, dict):
                return value
    return MISSING


def _source_layer(
    event: dict[str, Any], source: dict[str, Any], reality: dict[str, Any]
) -> tuple[dict[str, Any], Any]:
    checks = _completeness("api_call", source)
    attributable = source.get("attributable") is True
    if not attributable:
        checks.append(
            _check(
                "BLOCKED",
                "api_call.attribution",
                "No exact attributable Tag Assistant API Call was selected.",
                check_next="Selected Tag Assistant event and API Call tab",
            )
        )
        return _layer(LAYER_ORDER[1], checks, False), MISSING
    payload = _selected_payload(source)
    count = source.get("occurrence_count")
    source_complete = source.get("complete") is True
    if count == 1:
        occurrence_status = "PASS"
        occurrence_reason = "Exactly one planned API Call occurred."
    elif isinstance(count, int) and count > 1:
        occurrence_status = "FAIL"
        occurrence_reason = "The planned interaction produced duplicate API Calls."
    elif count == 0 and source_complete:
        occurrence_status = "FAIL"
        occurrence_reason = "The complete action window contains no planned API Call."
    else:
        occurrence_status = "BLOCKED"
        occurrence_reason = "Incomplete chronology cannot prove that the API Call is missing."
    checks.append(
        _check(
            occurrence_status,
            "api_call.occurrence",
            occurrence_reason,
            expected=1,
            observed=count,
            check_next=None if occurrence_status == "PASS" else "Tag Assistant event chronology",
        )
    )
    if payload is MISSING:
        checks.append(
            _check(
                "BLOCKED",
                "api_call.payload",
                "The exact expanded API Call payload is unavailable.",
                check_next="Tag Assistant API Call tab",
            )
        )
    else:
        identity_matches = _message_matches(event, {"payload": payload})
        checks.append(
            _check(
                "PASS" if identity_matches else "FAIL",
                "api_call.identity",
                "Selected API Call matches the planned source identity."
                if identity_matches
                else "Selected API Call does not match the planned source identity.",
                expected=event["selector"],
                observed=payload.get("event", "field-anchor")
                if isinstance(payload, dict)
                else payload,
                check_next=None if identity_matches else "Selected Tag Assistant API Call",
            )
        )
        checks.extend(_field_checks(event["fields"], payload, reality, surface="api_call"))
    return _layer(LAYER_ORDER[1], checks, True), payload


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            output.update(_flatten(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            output.update(_flatten(child, f"{prefix}[{index}]"))
    else:
        output[prefix] = value
    return output


def _tag_payload(tags: list[dict[str, Any]], section: str) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for tag in tags:
        value = tag.get(section)
        if isinstance(value, dict):
            output.update(value)
    return output


def _mapping_present(tags: list[dict[str, Any]], path: str) -> bool:
    canonical = path.replace("[]", "").casefold()
    leaf = canonical.split(".")[-1]
    for tag in tags:
        mapped_paths = tag.get("mapped_paths", [])
        for mapped in mapped_paths if isinstance(mapped_paths, list) else []:
            mapped_path = str(mapped).replace("[]", "").casefold().rstrip(".")
            if canonical == mapped_path or canonical.startswith(mapped_path + "."):
                return True
        mappings = tag.get("mappings", tag.get("configuration", {}))
        for key, value in _flatten(mappings).items():
            mapped_key = re.sub(r"\[\d+\]", "", key).replace("[]", "").casefold()
            if canonical == mapped_key or canonical.startswith(mapped_key + "."):
                return True
            text = re.sub(r"[^a-z0-9.]+", "_", f"{key} {value}".casefold())
            if canonical in text or re.search(rf"(?:^|[._]){re.escape(leaf)}(?:$|[._])", text):
                return True
    return False


def _delivery_identity_check(
    event: dict[str, Any], payload: Any, reality: dict[str, Any], surface: str
) -> dict[str, Any]:
    expected: Any = event["event_name"]
    if expected == "gtm.custom_event":
        contextual = _expected_for(reality, "event_name")
        expected = contextual if contextual is not MISSING else event["selector"].get("event_name")
    observed_values = _surface_values(payload, "event", surface)
    if not observed_values:
        observed_values = _surface_values(payload, "event_name", surface)
    observed: Any = observed_values[0] if observed_values else MISSING
    if observed is MISSING or expected is None:
        passed = False
    elif isinstance(expected, list):
        passed = any(strict_equal(observed, candidate) for candidate in expected)
    else:
        passed = strict_equal(observed, expected)
    return _check(
        "PASS" if passed else "FAIL",
        f"{surface}.event_identity",
        "Delivered event identity matches the planned event."
        if passed
        else "Delivered event identity is missing or differs from the planned event.",
        path="event",
        expected=expected,
        observed="absent" if observed is MISSING else observed,
        check_next=None if passed else f"{surface} event name",
    )


def _destination_values(value: Any) -> list[str]:
    output: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]+", "_", str(key).casefold()).strip("_")
            if normalized in {
                "destination_id",
                "measurement_id",
                "send_to",
                "tag_id",
                "tid",
            }:
                candidates = child if isinstance(child, list) else [child]
                for candidate in candidates:
                    output.extend(re.findall(r"\b(?:G|GT)-[A-Z0-9-]+\b", str(candidate), re.I))
            output.extend(_destination_values(child))
    elif isinstance(value, list):
        for child in value:
            output.extend(_destination_values(child))
    return list(dict.fromkeys(item.upper() for item in output))


def _planned_destination_check(
    event: dict[str, Any], payload: Any, surface: str
) -> dict[str, Any] | None:
    expected = event.get("expected_destination_id")
    if expected is None:
        return None
    observed = _destination_values(payload)
    passed = str(expected).upper() in observed
    return _check(
        "PASS" if passed else "FAIL",
        f"{surface}.destination",
        "GA4 destination matches the tracking plan."
        if passed
        else "GA4 destination is missing or differs from the tracking plan.",
        path="destination_id",
        expected=expected,
        observed=observed or "absent",
        check_next=None if passed else f"{surface} destination",
    )


def _gtm_firing_check(
    tags: list[dict[str, Any]], complete: bool
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fired = [tag for tag in tags if tag.get("fired") is True]
    status = "PASS" if fired else "FAIL" if complete else "BLOCKED"
    check = _check(
        status,
        "gtm.firing",
        "At least one concerned tag fired."
        if fired
        else "No concerned tag fired."
        if complete
        else "Incomplete tag evidence cannot prove non-firing.",
        expected="concerned fired tag",
        observed=[tag.get("name") for tag in tags],
        check_next=None if fired else "GTM trigger and exceptions",
    )
    return fired, check


def _gtm_duplicate_check(fired: list[dict[str, Any]]) -> dict[str, Any]:
    names = [str(tag.get("name") or "unknown") for tag in fired]
    duplicates = {name for name, count in Counter(names).items() if count > 1}
    duplicates.update(
        str(tag.get("name") or "unknown") for tag in fired if int(tag.get("firing_count") or 1) > 1
    )
    return _check(
        "FAIL" if duplicates else "PASS",
        "gtm.firing_count",
        "A concerned tag fired more than once."
        if duplicates
        else "Concerned tag firing counts are singular.",
        expected=1,
        observed=sorted(duplicates) or 1,
        check_next=None if not duplicates else "GTM trigger duplication",
    )


def _gtm_mapping_checks(
    fields: list[dict[str, Any]], fired: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    checks = []
    for field in fields:
        path = field["path"]
        mapped = _mapping_present(fired, path)
        checks.append(
            _check(
                "PASS" if mapped else "FAIL",
                "gtm.mapping",
                "Effective tag mapping is present."
                if mapped
                else "Planned field has no effective tag mapping.",
                path=path,
                expected="mapped",
                observed="mapped" if mapped else "absent",
                check_next=None if mapped else f"Tag Names/Values mapping for {path}",
            )
        )
    return checks


def _gtm_layer(
    event: dict[str, Any], gtm: dict[str, Any], reality: dict[str, Any], source_payload: Any
) -> dict[str, Any]:
    checks = _completeness("gtm", gtm)
    attributable = gtm.get("attributable") is True
    tags = [
        tag
        for tag in gtm.get("tags", [])
        if isinstance(tag, dict) and tag.get("concerned") is not False
    ]
    if not attributable:
        checks.append(
            _check(
                "BLOCKED",
                "gtm.attribution",
                "Concerned GTM tag evidence is not attributable to the selected API Call.",
                check_next="Tags tab on the selected event and causal Trigger Group",
            )
        )
        return _layer(LAYER_ORDER[2], checks, False)
    gtm_complete = gtm.get("complete") is True
    fired, firing_check = _gtm_firing_check(tags, gtm_complete)
    checks.extend((firing_check, _gtm_duplicate_check(fired)))
    if not fired:
        checks.extend(_finding_checks(gtm.get("findings"), "gtm"))
        return _layer(LAYER_ORDER[2], checks, True)
    details_complete = gtm_complete or all(tag.get("complete") is True for tag in fired)
    if not details_complete:
        checks.append(
            _check(
                "BLOCKED",
                "gtm.details",
                "Incomplete Names/Values evidence cannot certify mapping or runtime fields.",
                check_next="Concerned tag Names and Values",
            )
        )
        checks.extend(_finding_checks(gtm.get("findings"), "gtm"))
        return _layer(LAYER_ORDER[2], checks, True)
    runtime = _tag_payload(fired, "runtime")
    checks.append(_delivery_identity_check(event, runtime, reality, "gtm_runtime"))
    destination_check = _planned_destination_check(
        event,
        {
            "runtime": runtime,
            "mappings": _tag_payload(fired, "mappings"),
        },
        "gtm",
    )
    if destination_check:
        checks.append(destination_check)
    checks.extend(_gtm_mapping_checks(event["fields"], fired))
    checks.extend(
        _field_checks(
            event["fields"],
            runtime,
            reality,
            surface="gtm_runtime",
            source_payload=source_payload,
        )
    )
    checks.extend(_finding_checks(gtm.get("findings"), "gtm"))
    return _layer(LAYER_ORDER[2], checks, True)


def _network_payload(requests: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for request in requests:
        parameters = request.get("parameters")
        if isinstance(parameters, dict):
            output.update(parameters)
    return output


def _network_occurrence_check(requests: list[dict[str, Any]], complete: bool) -> dict[str, Any]:
    status = "PASS" if requests else "FAIL" if complete else "BLOCKED"
    return _check(
        status,
        "browser_request.occurrence",
        "Attributable browser request was observed."
        if requests
        else "No attributable browser request was observed."
        if complete
        else "Incomplete request evidence cannot prove that delivery is missing.",
        expected=">=1",
        observed=len(requests),
        check_next=None if requests else "Concerned tag destination request",
    )


def _network_transport_check(requests: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [
        row.get("url")
        for row in requests
        if row.get("failed") is True or type(row.get("status")) is int and row["status"] >= 400
    ]
    unknown = [
        row.get("url")
        for row in requests
        if row.get("failed") is not True
        and row.get("sent") is not True
        and not (type(row.get("status")) is int and 100 <= row["status"] < 400)
    ]
    status = "FAIL" if failures else "BLOCKED" if unknown else "PASS"
    return _check(
        status,
        "browser_request.transport",
        "A concerned request failed."
        if failures
        else "Request send/response completion is unavailable."
        if unknown
        else "No concerned request transport failure was observed.",
        expected="successful client send",
        observed=failures or unknown or "successful",
        check_next=None if status == "PASS" else "Browser request status/failure",
    )


def _network_duplicate_check(requests: list[dict[str, Any]]) -> dict[str, Any]:
    logical_ids = [str(row["logical_hit_id"]) for row in requests if row.get("logical_hit_id")]
    duplicates = {
        str(row.get("logical_hit_id") or row.get("url") or "unknown")
        for row in requests
        if row.get("duplicate") is True
    }
    duplicates.update(value for value, count in Counter(logical_ids).items() if count > 1)
    return _check(
        "FAIL" if duplicates else "PASS",
        "browser_request.duplicates",
        "Duplicate logical browser sends were observed."
        if duplicates
        else "No duplicate browser send was observed.",
        observed=sorted(duplicates) or "none",
        check_next=None if not duplicates else "Request retry/duplication chronology",
    )


def _network_layer(
    event: dict[str, Any], network: dict[str, Any], reality: dict[str, Any], source_payload: Any
) -> dict[str, Any]:
    checks = _completeness("browser_request", network)
    attributable = network.get("attributable") is True
    requests = [row for row in network.get("requests", []) if isinstance(row, dict)]
    if not attributable:
        checks.append(
            _check(
                "BLOCKED",
                "browser_request.attribution",
                "Browser request evidence is not attributable to the selected action/tag.",
                check_next="Playwright action-bounded request buffer",
            )
        )
        return _layer(LAYER_ORDER[3], checks, False)
    network_complete = network.get("complete") is True
    checks.append(_network_occurrence_check(requests, network_complete))
    if not requests:
        checks.extend(_finding_checks(network.get("findings"), "browser_request"))
        return _layer(LAYER_ORDER[3], checks, True)
    checks.extend((_network_transport_check(requests), _network_duplicate_check(requests)))
    payload = _network_payload(requests)
    checks.append(_delivery_identity_check(event, payload, reality, "browser_request"))
    destination_check = _planned_destination_check(event, payload, "browser_request")
    if destination_check:
        checks.append(destination_check)
    checks.extend(
        _field_checks(
            event["fields"],
            payload,
            reality,
            surface="browser_request",
            source_payload=source_payload,
        )
    )
    checks.extend(_finding_checks(network.get("findings"), "browser_request"))
    return _layer(LAYER_ORDER[3], checks, True)


def _finding_checks(value: Any, surface: str) -> list[dict[str, Any]]:
    output = []
    for index, finding in enumerate(value if isinstance(value, list) else []):
        if not isinstance(finding, dict):
            continue
        status = str(finding.get("status") or "REVIEW").upper()
        if status not in {"FAIL", "REVIEW", "PASS"}:
            status = "REVIEW"
        output.append(
            _check(
                status,
                str(finding.get("code") or f"{surface}.finding.{index + 1}"),
                str(finding.get("reason") or "Semantic finding was recorded."),
                path=finding.get("path"),
                expected=finding.get("expected"),
                observed=finding.get("observed"),
                check_next=finding.get("check_next"),
            )
        )
    return output


def _message_matches(event: dict[str, Any], row: dict[str, Any]) -> bool:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else row
    selector = event.get("selector", {"event": event["event_name"]})
    anchors = selector.get("anchor_fields", [])
    if isinstance(anchors, list) and anchors:
        minimum = min(2, len(anchors))
        return sum(bool(path_values(payload, str(path))) for path in anchors) >= minimum
    for key, expected in selector.items():
        values = path_values(payload, key)
        actual = values[0] if values else row.get(key)
        if isinstance(expected, list):
            if not any(strict_equal(actual, option) for option in expected):
                return False
        elif not strict_equal(actual, expected):
            return False
    return True


def _behavior_duplicate_check(
    event: dict[str, Any], messages: list[dict[str, Any]]
) -> dict[str, Any]:
    count = sum(_message_matches(event, row) for row in messages)
    return _check(
        "FAIL" if count > 1 else "PASS",
        "behavior.duplicate_event",
        "One interaction produced duplicate planned events."
        if count > 1
        else "No duplicate planned event was observed.",
        expected="<=1",
        observed=count,
        check_next=None if count <= 1 else "Preview message sequence",
    )


def _unexpected_business_events(event: dict[str, Any], messages: list[dict[str, Any]]) -> list[str]:
    unexpected = []
    for row in messages:
        name = str(row.get("event_name") or row.get("name") or "").strip()
        if not name or _message_matches(event, row):
            continue
        if TECHNICAL_EVENT.search(name) and row.get("business") is not True:
            continue
        if row.get("business") is True:
            unexpected.append(name)
    return unexpected


def _behavior_interjection_check(
    event: dict[str, Any], messages: list[dict[str, Any]]
) -> dict[str, Any]:
    unexpected = _unexpected_business_events(event, messages)
    return _check(
        "REVIEW" if unexpected else "PASS",
        "behavior.interjected_event",
        "Unexpected business events occurred inside the continuous action window."
        if unexpected
        else "No unexplained interjected business event was observed.",
        expected="causal planned sequence",
        observed=unexpected or "none",
        check_next=None
        if not unexpected
        else "Preview API Call chronology and causing interaction",
    )


def _behavior_stale_check(messages: list[dict[str, Any]], previous_cursor: int) -> dict[str, Any]:
    stale = [
        row.get("cursor")
        for row in messages
        if type(row.get("cursor")) is int and row["cursor"] <= previous_cursor
    ]
    return _check(
        "FAIL" if stale else "PASS",
        "behavior.stale_message",
        "Pre-action messages contaminated the action window."
        if stale
        else "Action window contains no stale Preview message.",
        expected=f"> {previous_cursor}",
        observed=stale or "fresh",
        check_next=None if not stale else "Preview cursor boundaries",
    )


def _behavior_layer(
    event: dict[str, Any],
    behavior: dict[str, Any],
    source: dict[str, Any],
    previous_cursor: int,
) -> dict[str, Any]:
    checks = _completeness("surrounding_behavior", behavior)
    attributable = behavior.get("attributable") is True
    if not attributable:
        checks.append(
            _check(
                "BLOCKED",
                "behavior.attribution",
                "Continuous Preview chronology is not attributable to this action window.",
                check_next="Tag Assistant cursor and message chronology",
            )
        )
        return _layer(LAYER_ORDER[4], checks, False)
    messages = [
        row for row in behavior.get("messages", source.get("calls", [])) if isinstance(row, dict)
    ]
    checks.extend(
        (
            _behavior_duplicate_check(event, messages),
            _behavior_interjection_check(event, messages),
            _behavior_stale_check(messages, previous_cursor),
        )
    )
    checks.extend(_finding_checks(behavior.get("findings"), "behavior"))
    return _layer(LAYER_ORDER[4], checks, True)


def _validate_bundle(bundle: dict[str, Any], action: dict[str, Any]) -> None:
    required = {
        "observer_contract",
        "action_id",
        "event_id",
        "scenario_id",
        "preview_cursor",
        "reality",
        "source",
        "gtm",
        "network",
        "behavior",
    }
    if set(bundle) != required:
        raise RunError("Evidence bundle fields do not match the fixed contract.")
    if bundle.get("observer_contract") != "playwright-mcp-v1":
        raise RunError("Evidence bundle did not come from the fixed native Playwright path.")
    for key in ("action_id", "event_id"):
        if str(bundle.get(key) or "") != str(action.get(key) or ""):
            raise RunError(f"Evidence {key} does not match the only open action.")
    if bundle.get("scenario_id") != action.get("event_name"):
        raise RunError("Evidence scenario_id must equal the canonical event_name.")
    for key in ("reality", "source", "gtm", "network", "behavior"):
        if not isinstance(bundle.get(key), dict):
            raise RunError(f"Evidence bundle requires object {key!r}.")
    cursor = bundle.get("preview_cursor")
    if not isinstance(cursor, int) or cursor < int(action.get("preview_cursor", 0)):
        raise RunError("Evidence bundle has a missing or regressed Preview cursor.")
    expected = bundle["reality"].get("expected")
    if not isinstance(expected, dict):
        raise RunError("Reality evidence requires an expected-values object.")


def judge_event(
    event: dict[str, Any], action: dict[str, Any], bundle: dict[str, Any]
) -> dict[str, Any]:
    _validate_bundle(bundle, action)
    reality = bundle["reality"]
    source = bundle["source"]
    layers: list[dict[str, Any]] = []
    layers.append(_reality_layer(reality))
    source_layer, source_payload = _source_layer(event, source, reality)
    layers.append(source_layer)
    layers.append(_gtm_layer(event, bundle["gtm"], reality, source_payload))
    layers.append(_network_layer(event, bundle["network"], reality, source_payload))
    if event.get("expected_destination_id") is None:
        fired = [
            tag
            for tag in bundle["gtm"].get("tags", [])
            if isinstance(tag, dict)
            and tag.get("concerned") is not False
            and tag.get("fired") is True
        ]
        tag_destinations = _destination_values(
            {
                "runtime": _tag_payload(fired, "runtime"),
                "mappings": _tag_payload(fired, "mappings"),
            }
        )
        request_destinations = _destination_values(
            _network_payload(
                [row for row in bundle["network"].get("requests", []) if isinstance(row, dict)]
            )
        )
        if tag_destinations and request_destinations:
            coherent = bool(set(tag_destinations) & set(request_destinations))
            status = "PASS" if coherent else "FAIL"
            reason = (
                "Observed GA4 tag and request destinations agree."
                if coherent
                else "Observed GA4 tag and request destinations disagree."
            )
        else:
            status = "BLOCKED"
            reason = "The plan has no destination expectation and observed destination evidence is incomplete."
        for index, surface in ((2, "gtm"), (3, "browser_request")):
            layer = layers[index]
            layer["checks"].append(
                _check(
                    status,
                    f"{surface}.destination_coherence",
                    reason,
                    path="destination_id",
                    expected="same observed GA4 destination",
                    observed={
                        "gtm": tag_destinations,
                        "browser_request": request_destinations,
                    },
                    check_next=None if status == "PASS" else "GA4 tag/request destination",
                )
            )
            layers[index] = _layer(layer["layer"], layer["checks"], layer["attributable"])
    layers.append(
        _behavior_layer(
            event,
            bundle["behavior"],
            source,
            int(action.get("preview_cursor", 0)),
        )
    )
    layer_statuses = [layer["status"] for layer in layers]
    status = worst(layer_statuses)
    problems = [
        check
        for layer in layers
        for check in layer["checks"]
        if check["status"] in {"FAIL", "BLOCKED", "REVIEW"}
    ]
    first_non_pass = max(
        problems,
        key=lambda check: PRIORITY[check["status"]],
        default=None,
    )
    return {
        "action_id": action["action_id"],
        "event_id": event["event_id"],
        "event_name": event["event_name"],
        "scenario_id": event["event_name"],
        "preview_cursor": bundle.get("preview_cursor", action.get("preview_cursor", 0)),
        "status": status,
        "reason": first_non_pass["reason"] if first_non_pass else "All five layers passed.",
        "layers": layers,
    }


def event_by_id(plan: dict[str, Any], event_id: str) -> dict[str, Any]:
    for event in plan.get("events", []):
        if event.get("event_id") == event_id:
            return event
    raise RunError(f"Unknown event id: {event_id}")
