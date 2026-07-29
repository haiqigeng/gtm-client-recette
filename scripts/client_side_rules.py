#!/usr/bin/env python3
"""Deterministic client-side rule, sensitive-data, and path helpers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlsplit

MISSING = object()

BUSINESS_RULE_OPERATORS = {
    "equals_path",
    "sum_product_equals",
    "all_items_equal",
    "implies",
    "unique_across_requirements",
    "range",
    "format",
    "regex",
}
FORMATS = {"email", "uuid", "iso_date", "iso_datetime", "iso_currency"}
SENSITIVE_CATEGORIES = {
    "email",
    "phone",
    "postal_address",
    "person_name",
    "ip_address",
    "sensitive_query_parameter",
    "custom",
}
DEFAULT_FORBIDDEN_CATEGORIES = sorted(SENSITIVE_CATEGORIES - {"custom"})

EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+(?![\w.-])", re.I)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\s().-]*){8,15}(?!\w)")
IP_RE = re.compile(
    r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)"
)
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)
ISO_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")

SENSITIVE_KEY_CATEGORIES = {
    "email": "email",
    "email_address": "email",
    "user_email": "email",
    "mail": "email",
    "phone": "phone",
    "phone_number": "phone",
    "telephone": "phone",
    "mobile": "phone",
    "first_name": "person_name",
    "firstname": "person_name",
    "last_name": "person_name",
    "lastname": "person_name",
    "full_name": "person_name",
    "fullname": "person_name",
    "street": "postal_address",
    "street_address": "postal_address",
    "address": "postal_address",
    "postal_address": "postal_address",
    "postcode": "postal_address",
    "postal_code": "postal_address",
    "zipcode": "postal_address",
    "zip_code": "postal_address",
    "ip": "ip_address",
    "ip_address": "ip_address",
}
SENSITIVE_QUERY_KEYS = {
    "email",
    "email_address",
    "mail",
    "phone",
    "telephone",
    "mobile",
    "first_name",
    "last_name",
    "full_name",
    "address",
    "street",
    "postcode",
    "postal_code",
    "zip",
}


def _path_tokens(path: str) -> list[str | int | None]:
    """Parse dotted paths plus numeric, wildcard, or quoted literal keys."""
    if not isinstance(path, str) or not path.strip():
        return []
    tokens: list[str | int | None] = []
    value = path.strip()
    index = 0
    expect_token = True
    while index < len(value):
        if value[index] == ".":
            if expect_token:
                return []
            expect_token = True
            index += 1
            continue
        if value[index] == "[":
            cursor = index + 1
            if cursor >= len(value):
                return []
            if value[cursor] in {'"', "'"}:
                quote = value[cursor]
                cursor += 1
                characters: list[str] = []
                while cursor < len(value):
                    character = value[cursor]
                    if character == "\\":
                        cursor += 1
                        if cursor >= len(value):
                            return []
                        escapes = {"n": "\n", "r": "\r", "t": "\t"}
                        characters.append(escapes.get(value[cursor], value[cursor]))
                    elif character == quote:
                        break
                    else:
                        characters.append(character)
                    cursor += 1
                if cursor >= len(value) or value[cursor] != quote:
                    return []
                cursor += 1
                if cursor >= len(value) or value[cursor] != "]":
                    return []
                tokens.append("".join(characters))
                index = cursor + 1
            else:
                closing = value.find("]", cursor)
                if closing < 0:
                    return []
                content = value[cursor:closing]
                if content == "":
                    tokens.append(None)
                elif content.isdigit():
                    tokens.append(int(content))
                else:
                    return []
                index = closing + 1
            expect_token = False
            continue
        cursor = index
        while cursor < len(value) and value[cursor] not in ".[":
            if value[cursor] == "]":
                return []
            cursor += 1
        token = value[index:cursor]
        if not token:
            return []
        tokens.append(token)
        index = cursor
        expect_token = False
    if expect_token:
        return []
    return tokens


def path_values(value: Any, path: str) -> list[Any]:
    """Return every value addressed by a dotted path; [] expands arrays."""
    current = [value]
    for token in _path_tokens(path):
        next_values: list[Any] = []
        for item in current:
            if token is None:
                if isinstance(item, list):
                    next_values.extend(item)
            elif isinstance(token, int):
                if isinstance(item, list) and 0 <= token < len(item):
                    next_values.append(item[token])
            elif isinstance(item, dict) and token in item:
                next_values.append(item[token])
        current = next_values
        if not current:
            break
    return current


def path_value(value: Any, path: str) -> Any:
    """Return a single addressed value or MISSING when absent/ambiguous."""
    values = path_values(value, path)
    return values[0] if len(values) == 1 else MISSING


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _strict_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/number equality shortcut."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if _is_number(left) or _is_number(right):
        return _is_number(left) and _is_number(right) and left == right
    return type(left) is type(right) and left == right


def _compact(value: Any, path_hint: str | None = None) -> Any:
    """Keep rule output useful without copying payloads or obvious identifiers."""
    if value is MISSING:
        return "<absent>"
    if isinstance(value, str):
        key_hint = re.sub(r"[^a-zA-Z0-9_]+", "_", path_hint.rsplit(".", 1)[-1]) if path_hint else ""
        scan_value: Any = {key_hint: value} if key_hint else value
        findings = scan_sensitive_value(
            scan_value,
            policy={
                "forbidden_categories": DEFAULT_FORBIDDEN_CATEGORIES,
                "scan_unkeyed_phone_values": True,
                "scan_unkeyed_ip_values": True,
            },
        )
        categories = sorted({item["category"] for item in findings})
        return {
            "redacted": True,
            "categories": categories or ["unclassified_string"],
            "value_fingerprint": _fingerprint(value),
            "value_length": len(value),
        }
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return {"type": "array", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "object", "keys": sorted(str(key) for key in value)}
    return str(type(value).__name__)


def _condition(payload: Any, condition: dict[str, Any]) -> bool | None:
    value = path_value(payload, str(condition.get("path", "")))
    rule = str(condition.get("match_rule", "equals"))
    expected = condition.get("expected_value")
    if rule == "present":
        return value is not MISSING
    if rule == "absent":
        return value is MISSING
    if value is MISSING:
        return False
    if rule == "equals":
        return _strict_equal(value, expected)
    if rule == "not_empty":
        return value not in ("", [], {}, None)
    if rule == "one_of":
        allowed = condition.get("allowed_values")
        return isinstance(allowed, list) and any(
            _strict_equal(value, candidate) for candidate in allowed
        )
    if rule == "greater_than":
        return _is_number(value) and _is_number(expected) and value > expected
    if rule == "greater_than_or_equal":
        return _is_number(value) and _is_number(expected) and value >= expected
    if rule == "regex":
        pattern = condition.get("pattern")
        if not isinstance(value, str) or not isinstance(pattern, str):
            return False
        try:
            return re.fullmatch(pattern, value) is not None
        except re.error:
            return None
    return None


def format_matches(value: Any, format_name: str) -> bool:
    if not isinstance(value, str):
        return False
    if format_name == "email":
        return EMAIL_RE.fullmatch(value) is not None
    if format_name == "uuid":
        return UUID_RE.fullmatch(value) is not None
    if format_name == "iso_currency":
        return ISO_CURRENCY_RE.fullmatch(value) is not None
    if format_name == "iso_date":
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True
    if format_name == "iso_datetime":
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        return True
    return False


def evaluate_business_rule(
    rule: dict[str, Any],
    payload: Any,
    all_payloads: Iterable[Any] = (),
) -> dict[str, Any]:
    """Evaluate one allowlisted declarative rule without executing expressions."""
    rule_id = str(rule.get("rule_id", "")).strip()
    operator = str(rule.get("operator", "")).strip()
    result: dict[str, Any] = {
        "rule_id": rule_id,
        "operator": operator,
        "status": "REVIEW",
        "reason": "",
    }
    if not rule_id:
        result["reason"] = "Missing rule_id."
        return result
    if operator not in BUSINESS_RULE_OPERATORS:
        result["reason"] = f"Unsupported operator '{operator}'."
        return result

    passed: bool | None = None
    actual: Any = MISSING
    expected: Any = MISSING
    actual_path_hint: str | None = None
    expected_path_hint: str | None = None

    if operator == "equals_path":
        left_path = str(rule.get("left_path", ""))
        right_path = str(rule.get("right_path", ""))
        left = path_value(payload, left_path)
        right = path_value(payload, right_path)
        actual, expected = left, right
        actual_path_hint, expected_path_hint = left_path, right_path
        passed = left is not MISSING and right is not MISSING and _strict_equal(left, right)

    elif operator == "sum_product_equals":
        target_path = str(rule.get("target_path", ""))
        target = path_value(payload, target_path)
        items = path_value(payload, str(rule.get("items_path", "")))
        price_field = str(rule.get("price_field", "price"))
        quantity_field = str(rule.get("quantity_field", "quantity"))
        tolerance = rule.get("tolerance", 0)
        if not _is_number(tolerance) or tolerance < 0:
            result["reason"] = "tolerance must be a non-negative number."
            return result
        computed = 0.0
        valid_items = isinstance(items, list) and bool(items)
        if valid_items:
            for item in items:
                if not isinstance(item, dict):
                    valid_items = False
                    break
                price = item.get(price_field)
                quantity = item.get(quantity_field, 1)
                if not _is_number(price) or not _is_number(quantity):
                    valid_items = False
                    break
                computed += float(price) * float(quantity)
        actual, expected = target, computed
        actual_path_hint = target_path
        passed = (
            valid_items
            and _is_number(target)
            and math.isclose(
                float(target),
                computed,
                rel_tol=0.0,
                abs_tol=float(tolerance),
            )
        )

    elif operator == "all_items_equal":
        items = path_value(payload, str(rule.get("items_path", "")))
        item_field = str(rule.get("item_field", ""))
        expected = path_value(payload, str(rule.get("expected_path", "")))
        valid_items = (
            isinstance(items, list)
            and bool(items)
            and all(isinstance(item, dict) for item in items)
        )
        values = [item.get(item_field, MISSING) for item in items] if valid_items else []
        actual = values
        actual_path_hint = str(rule.get("item_field", ""))
        expected_path_hint = str(rule.get("expected_path", ""))
        passed = (
            valid_items
            and expected is not MISSING
            and all(value is not MISSING and _strict_equal(value, expected) for value in values)
        )

    elif operator == "implies":
        antecedent = rule.get("if")
        consequent = rule.get("then")
        if not isinstance(antecedent, dict) or not isinstance(consequent, dict):
            result["reason"] = "implies requires object-valued 'if' and 'then' conditions."
            return result
        if_result = _condition(payload, antecedent)
        then_result = _condition(payload, consequent)
        actual = {"if": if_result, "then": then_result}
        expected = {"if_true_requires_then": True}
        passed = (
            None if if_result is None or then_result is None else (not if_result or then_result)
        )

    elif operator == "unique_across_requirements":
        path = str(rule.get("path", ""))
        values = [
            candidate
            for item in all_payloads
            if (candidate := path_value(item, path)) is not MISSING
        ]
        actual = {"value_count": len(values), "unique_count": len(set(map(_stable_key, values)))}
        expected = {"all_values_unique": True}
        current = path_value(payload, path)
        passed = current is not MISSING and len(values) == len(set(map(_stable_key, values)))

    elif operator == "range":
        actual_path_hint = str(rule.get("path", ""))
        actual = path_value(payload, actual_path_hint)
        minimum = rule.get("min")
        maximum = rule.get("max")
        expected = {"min": minimum, "max": maximum}
        if actual is MISSING or not _is_number(actual):
            passed = False
        else:
            passed = (minimum is None or (_is_number(minimum) and actual >= minimum)) and (
                maximum is None or (_is_number(maximum) and actual <= maximum)
            )

    elif operator == "format":
        actual_path_hint = str(rule.get("path", ""))
        actual = path_value(payload, actual_path_hint)
        format_name = str(rule.get("format", ""))
        expected = format_name
        passed = format_name in FORMATS and format_matches(actual, format_name)

    elif operator == "regex":
        actual_path_hint = str(rule.get("path", ""))
        actual = path_value(payload, actual_path_hint)
        pattern = rule.get("pattern")
        expected = pattern
        try:
            passed = (
                isinstance(actual, str)
                and isinstance(pattern, str)
                and re.fullmatch(pattern, actual) is not None
            )
        except re.error:
            result["reason"] = "Invalid regular expression."
            return result

    result["status"] = "PASS" if passed is True else "FAIL" if passed is False else "REVIEW"
    result["actual"] = _compact(actual, actual_path_hint)
    result["expected"] = _compact(expected, expected_path_hint)
    if not result["reason"]:
        result["reason"] = (
            "Rule satisfied."
            if passed is True
            else "Rule not satisfied."
            if passed is False
            else "Rule could not be evaluated deterministically."
        )
    return result


def _stable_key(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return repr(value)


def evaluate_report_business_rules(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate declared business rules for every normalized requirement."""
    requirements = data.get("requirements")
    if not isinstance(requirements, list):
        return []
    all_payloads: list[dict[str, Any]] = []
    seen_occurrences: set[tuple[str, Any]] = set()
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        raw = requirement.get("raw_api_call")
        if not isinstance(raw, dict) or not isinstance(raw.get("payload"), dict):
            continue
        occurrence_key = (
            str(requirement.get("event_group_id", "")),
            raw.get("event_index", requirement.get("requirement_id")),
        )
        if occurrence_key in seen_occurrences:
            continue
        seen_occurrences.add(occurrence_key)
        all_payloads.append(raw["payload"])
    output: list[dict[str, Any]] = []
    for requirement in requirements:
        if not isinstance(requirement, dict):
            continue
        expectation = requirement.get("expectation")
        raw = requirement.get("raw_api_call")
        if not isinstance(expectation, dict) or not isinstance(raw, dict):
            continue
        payload = raw.get("payload")
        rules = expectation.get("business_rules")
        if not isinstance(payload, dict) or not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            result = evaluate_business_rule(rule, payload, all_payloads)
            result["requirement_id"] = requirement.get("requirement_id")
            output.append(result)
    return output


def _normalize_path(path: str) -> str:
    return re.sub(r"\[\d+\]", "[]", path)


def _is_allowlisted(path: str, allowlisted_paths: set[str]) -> bool:
    normalized = _normalize_path(path)
    return path in allowlisted_paths or normalized in allowlisted_paths


def _fingerprint(value: Any) -> str:
    serialized = _stable_key(value)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _finding(
    *,
    path: str,
    category: str,
    confidence: str,
    basis: str,
    value: Any,
    forbidden: set[str],
    allowlisted_paths: set[str],
) -> dict[str, Any]:
    allowlisted = _is_allowlisted(path, allowlisted_paths)
    status = (
        "PASS"
        if allowlisted or category not in forbidden
        else "FAIL"
        if confidence == "confirmed"
        else "REVIEW"
    )
    return {
        "path": path,
        "category": category,
        "confidence": confidence,
        "basis": basis,
        "allowlisted": allowlisted,
        "status": status,
        "redacted_value": f"<redacted:{category}>",
        "value_fingerprint": _fingerprint(value),
        "value_length": len(str(value)),
    }


def scan_sensitive_value(
    value: Any,
    *,
    root_path: str = "$",
    policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Scan one client-side value and return findings without retaining raw values."""
    policy = policy or {}
    forbidden = {
        str(item)
        for item in policy.get("forbidden_categories", DEFAULT_FORBIDDEN_CATEGORIES)
        if str(item)
    }
    allowlisted_paths = {str(item) for item in policy.get("allowlisted_paths", []) if str(item)}
    custom_patterns = policy.get("custom_patterns", [])
    findings: list[dict[str, Any]] = []

    def add(
        path: str,
        category: str,
        confidence: str,
        basis: str,
        candidate: Any,
    ) -> None:
        signature = (path, category, basis, _fingerprint(candidate))
        if any(
            (
                item["path"],
                item["category"],
                item["basis"],
                item["value_fingerprint"],
            )
            == signature
            for item in findings
        ):
            return
        findings.append(
            _finding(
                path=path,
                category=category,
                confidence=confidence,
                basis=basis,
                value=candidate,
                forbidden=forbidden,
                allowlisted_paths=allowlisted_paths,
            )
        )

    def walk(item: Any, path: str, key: str | None = None) -> None:
        normalized_key = re.sub(r"[^a-z0-9]+", "_", (key or "").lower()).strip("_")
        key_category = SENSITIVE_KEY_CATEGORIES.get(normalized_key)
        if key_category and item not in (None, "", [], {}):
            add(path, key_category, "confirmed", "sensitive_field_name", item)

        if isinstance(item, dict):
            for child_key, child in item.items():
                child_path = f"{path}.{child_key}" if path else str(child_key)
                walk(child, child_path, str(child_key))
            return
        if isinstance(item, list):
            for index, child in enumerate(item):
                walk(child, f"{path}[{index}]", key)
            return
        if not isinstance(item, str) or not item:
            return

        for match in EMAIL_RE.finditer(item):
            add(path, "email", "confirmed", "email_pattern", match.group(0))
        if key_category == "phone":
            for match in PHONE_RE.finditer(item):
                add(path, "phone", "confirmed", "phone_pattern_in_phone_field", match.group(0))
        elif policy.get("scan_unkeyed_phone_values") is True:
            for match in PHONE_RE.finditer(item):
                add(path, "phone", "suspected", "unkeyed_phone_pattern", match.group(0))
        if key_category == "ip_address" or policy.get("scan_unkeyed_ip_values") is True:
            for match in IP_RE.finditer(item):
                add(
                    path,
                    "ip_address",
                    "confirmed" if key_category == "ip_address" else "suspected",
                    "ip_pattern",
                    match.group(0),
                )

        if item.startswith(("http://", "https://")):
            for query_key, query_value in parse_qsl(urlsplit(item).query, keep_blank_values=True):
                normalized_query = re.sub(r"[^a-z0-9]+", "_", query_key.lower()).strip("_")
                if normalized_query in SENSITIVE_QUERY_KEYS and query_value:
                    add(
                        f"{path}?{query_key}",
                        "sensitive_query_parameter",
                        "confirmed",
                        "sensitive_query_key",
                        query_value,
                    )

        if isinstance(custom_patterns, list):
            for custom in custom_patterns:
                if not isinstance(custom, dict):
                    continue
                pattern = custom.get("pattern")
                if not isinstance(pattern, str):
                    continue
                try:
                    matches = list(re.finditer(pattern, item))
                except re.error:
                    continue
                for match in matches:
                    add(
                        path,
                        str(custom.get("category", "custom")),
                        str(custom.get("confidence", "suspected")),
                        f"custom_pattern:{custom.get('pattern_id', 'unnamed')}",
                        match.group(0),
                    )

    walk(value, root_path)
    return sorted(findings, key=lambda item: (item["path"], item["category"], item["basis"]))


def requirement_sensitive_targets(requirement: dict[str, Any]) -> dict[str, Any]:
    """Return the client-side values that are relevant to leakage checks."""
    targets: dict[str, Any] = {}
    raw = requirement.get("raw_api_call")
    if isinstance(raw, dict) and "payload" in raw:
        targets["raw_api_call.payload"] = raw["payload"]
    resolved = requirement.get("resolved_data_layer")
    if isinstance(resolved, dict) and "snapshot" in resolved:
        targets["resolved_data_layer.snapshot"] = resolved["snapshot"]
    tag = requirement.get("tag")
    if isinstance(tag, dict) and "runtime_value" in tag:
        targets["tag.runtime_value"] = tag["runtime_value"]
    request = requirement.get("destination_request")
    if isinstance(request, dict):
        for field in (
            "request_url",
            "query_parameters",
            "request_body",
            "request_headers",
            "field_value",
        ):
            if field in request:
                targets[f"destination_request.{field}"] = request[field]
    journey = requirement.get("journey")
    if isinstance(journey, dict):
        for field in ("url", "page_title", "action_value"):
            if field in journey:
                targets[f"journey.{field}"] = journey[field]
    signal = requirement.get("source_signal")
    if isinstance(signal, dict):
        for field in ("payload", "value"):
            if field in signal:
                targets[f"source_signal.{field}"] = signal[field]
    checks = requirement.get("client_checks")
    if isinstance(checks, list):
        for index, check in enumerate(checks):
            if isinstance(check, dict) and "actual" in check:
                targets[f"client_checks[{index}].actual"] = check["actual"]
    return targets


def scan_requirement_sensitive_data(
    requirement: dict[str, Any],
    policy: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Scan the normalized client-side surfaces for one requirement."""
    output: list[dict[str, Any]] = []
    for path, value in requirement_sensitive_targets(requirement).items():
        output.extend(scan_sensitive_value(value, root_path=path, policy=policy))
    return sorted(output, key=lambda item: (item["path"], item["category"], item["basis"]))
