"""Shared compiler/judge predicate vocabulary.

This is the narrow reuse boundary around verified path, missing-state, strict JSON
equality/type, integer, safe-regex, range, and URL semantics. Compilation and judgment
call the same functions, so a plan cannot emit a rule the runtime does not understand.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from client_side_rules import MISSING
from safe_regex import fullmatch as safe_fullmatch
from value_semantics import field_state_for, is_json_number, json_value_type, strict_equal

SUPPORTED_OPERATORS = frozenset(
    {
        "present",
        "absent",
        "equals",
        "one_of",
        "non_empty",
        "regex",
        "range",
        "type",
        "state",
        "count",
        "order",
        "url_equals",
        "relationship",
    }
)
ALIASES = {
    "exists": "present",
    "not_empty": "non_empty",
    "matches": "regex",
    "in": "one_of",
    "enum": "one_of",
}
JSON_TYPES = frozenset({"null", "boolean", "number", "integer", "string", "array", "object"})


class PredicateError(ValueError):
    """Raised when a plan rule cannot be represented by the runtime judge."""


def _has(source: dict[str, Any], *names: str) -> bool:
    return any(name in source for name in names)


def _first(source: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in source:
            return source[name]
    return default


def _compile_equals(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    operator = predicate["operator"]
    if not _has(source, "expected", "expected_value", "value"):
        raise PredicateError(f"{location}: {operator} requires an expected value.")
    predicate["expected"] = _first(source, "expected", "expected_value", "value")


def _compile_one_of(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    allowed = _first(source, "allowed_values", "values", "expected")
    if allowed is None and isinstance(source.get("expected_value"), list):
        allowed = source["expected_value"]
    if not isinstance(allowed, list) or not allowed:
        raise PredicateError(f"{location}: one_of requires a non-empty allowed_values array.")
    predicate["allowed_values"] = allowed


def _compile_regex(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    pattern = _first(source, "pattern", "expected", "expected_value")
    if not isinstance(pattern, str) or not pattern:
        raise PredicateError(f"{location}: regex requires a non-empty pattern.")
    try:
        safe_fullmatch(pattern, "")
    except ValueError as error:
        raise PredicateError(f"{location}: unsafe regex: {error}") from error
    predicate["pattern"] = pattern


def _compile_range(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    minimum = _first(source, "minimum", "min")
    maximum = _first(source, "maximum", "max")
    if minimum is None and maximum is None:
        raise PredicateError(f"{location}: range requires minimum and/or maximum.")
    if minimum is not None and not is_json_number(minimum):
        raise PredicateError(f"{location}: range minimum must be a JSON number.")
    if maximum is not None and not is_json_number(maximum):
        raise PredicateError(f"{location}: range maximum must be a JSON number.")
    if minimum is not None:
        predicate["minimum"] = minimum
    if maximum is not None:
        predicate["maximum"] = maximum


def _compile_type(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    if "expected_type" not in predicate:
        expected = _first(source, "expected", "expected_value")
        if expected not in (None, ""):
            predicate["expected_type"] = str(expected).strip().casefold()
    if predicate.get("expected_type") not in JSON_TYPES:
        raise PredicateError(f"{location}: type requires a supported expected_type.")


def _compile_state(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    state = str(_first(source, "state", "expected", "expected_value", default="")).casefold()
    if state not in {"absent", "null", "empty", "value"}:
        raise PredicateError(f"{location}: state must be absent, null, empty, or value.")
    predicate["state"] = state


def _compile_count(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    exact = _first(source, "exact", "expected", "expected_value")
    minimum = _first(source, "minimum", "min")
    maximum = _first(source, "maximum", "max")
    values = [value for value in (exact, minimum, maximum) if value is not None]
    invalid = any(
        not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in values
    )
    if not values or invalid:
        raise PredicateError(f"{location}: count requires non-negative integer bounds.")
    for key, value in (("exact", exact), ("minimum", minimum), ("maximum", maximum)):
        if value is not None:
            predicate[key] = value


def _compile_order(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    sequence = _first(source, "sequence", "expected", "expected_value")
    if not isinstance(sequence, list) or not sequence:
        raise PredicateError(f"{location}: order requires a non-empty sequence.")
    predicate["sequence"] = sequence
    predicate["contiguous"] = source.get("contiguous") is True


def _compile_relationship(source: dict[str, Any], predicate: dict[str, Any], location: str) -> None:
    rule = _first(source, "relationship", "business_rule", "expected")
    if not isinstance(rule, dict):
        raise PredicateError(f"{location}: relationship requires a declarative rule object.")
    predicate["relationship"] = rule


PREDICATE_COMPILERS = {
    "equals": _compile_equals,
    "url_equals": _compile_equals,
    "one_of": _compile_one_of,
    "regex": _compile_regex,
    "range": _compile_range,
    "type": _compile_type,
    "state": _compile_state,
    "count": _compile_count,
    "order": _compile_order,
    "relationship": _compile_relationship,
}


def compile_predicate(
    source: dict[str, Any], *, location: str = "unknown source"
) -> dict[str, Any]:
    """Normalize and validate one predicate without dropping source values."""
    if not isinstance(source, dict):
        raise PredicateError(f"{location}: predicate must be an object.")
    raw_operator = str(_first(source, "operator", "match_rule", "rule", default="present"))
    operator = ALIASES.get(raw_operator.strip().casefold(), raw_operator.strip().casefold())
    if operator not in SUPPORTED_OPERATORS:
        raise PredicateError(f"{location}: unsupported predicate operator '{raw_operator}'.")

    predicate: dict[str, Any] = {"operator": operator}
    expected_type = _first(source, "expected_type", "type")
    if expected_type not in (None, "", "unknown"):
        normalized_type = str(expected_type).strip().casefold()
        if normalized_type not in JSON_TYPES:
            raise PredicateError(f"{location}: unsupported JSON type '{expected_type}'.")
        predicate["expected_type"] = normalized_type
    compiler = PREDICATE_COMPILERS.get(operator)
    if compiler is not None:
        compiler(source, predicate, location)
    if source.get("wire_coercion") is True:
        predicate["wire_coercion"] = True
    return predicate


def _matches_type(actual: Any, expected_type: str) -> bool:
    if expected_type == "integer":
        return isinstance(actual, int) and not isinstance(actual, bool)
    return json_value_type(actual) == expected_type


def _normalized_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    host = parsed.hostname.casefold() if parsed.hostname else ""
    port = f":{parsed.port}" if parsed.port else ""
    return urlunsplit(
        (parsed.scheme.casefold(), host + port, parsed.path or "/", parsed.query, parsed.fragment)
    )


def _is_subsequence(expected: list[Any], actual: list[Any], contiguous: bool) -> bool:
    if contiguous:
        width = len(expected)
        return any(
            actual[index : index + width] == expected for index in range(len(actual) - width + 1)
        )
    iterator = iter(actual)
    return all(
        any(strict_equal(candidate, wanted) for candidate in iterator) for wanted in expected
    )


def _evaluate_equals(actual: Any, predicate: dict[str, Any], wire: bool) -> bool:
    expected = predicate.get("expected")
    passed = strict_equal(actual, expected)
    return passed or (
        wire and predicate.get("wire_coercion") is True and str(actual) == str(expected)
    )


def _evaluate_one_of(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    return any(strict_equal(actual, candidate) for candidate in predicate["allowed_values"])


def _evaluate_non_empty(actual: Any, _predicate: dict[str, Any], _wire: bool) -> bool:
    return actual not in (None, "", [], {})


def _evaluate_regex(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    return isinstance(actual, str) and safe_fullmatch(predicate["pattern"], actual)


def _evaluate_range(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    if not is_json_number(actual):
        return False
    if "minimum" in predicate and actual < predicate["minimum"]:
        return False
    return "maximum" not in predicate or actual <= predicate["maximum"]


def _evaluate_type(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    return _matches_type(actual, predicate["expected_type"])


def _evaluate_count(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    if isinstance(actual, int) and not isinstance(actual, bool):
        count = actual
    elif isinstance(actual, (list, tuple, dict, set)):
        count = len(actual)
    else:
        return False
    if "exact" in predicate and count != predicate["exact"]:
        return False
    if "minimum" in predicate and count < predicate["minimum"]:
        return False
    return "maximum" not in predicate or count <= predicate["maximum"]


def _evaluate_order(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    return isinstance(actual, list) and _is_subsequence(
        predicate["sequence"], actual, predicate.get("contiguous") is True
    )


def _evaluate_url(actual: Any, predicate: dict[str, Any], _wire: bool) -> bool:
    return _normalized_url(actual) == _normalized_url(predicate.get("expected"))


PREDICATE_EVALUATORS = {
    "equals": _evaluate_equals,
    "one_of": _evaluate_one_of,
    "non_empty": _evaluate_non_empty,
    "regex": _evaluate_regex,
    "range": _evaluate_range,
    "type": _evaluate_type,
    "count": _evaluate_count,
    "order": _evaluate_order,
    "url_equals": _evaluate_url,
}


def evaluate_predicate(
    actual: Any, predicate: dict[str, Any], *, wire: bool = False
) -> dict[str, Any]:
    """Evaluate one compiled predicate and return a reason-code-bearing result."""
    operator = str(predicate.get("operator") or "")
    if operator not in SUPPORTED_OPERATORS:
        return {
            "status": "BLOCKED",
            "reason_code": "predicate.unsupported",
            "reason": f"Unsupported operator '{operator}'.",
        }

    missing = actual is MISSING
    if operator == "absent":
        passed = missing
    elif operator == "present":
        passed = not missing
    elif operator == "state":
        state = "absent" if missing else field_state_for(actual)
        passed = state == predicate["state"]
    elif missing:
        return {
            "status": "FAIL",
            "reason_code": "value.absent",
            "reason": "Required value is absent.",
        }
    elif operator == "relationship":
        return {
            "status": "REVIEW",
            "reason_code": "relationship.context_required",
            "reason": "Relationship requires contextual semantic evaluation.",
        }
    else:
        evaluator = PREDICATE_EVALUATORS[operator]
        passed = evaluator(actual, predicate, wire)

    if passed and "expected_type" in predicate and operator != "type":
        passed = _matches_type(actual, predicate["expected_type"])
        if not passed:
            return {
                "status": "FAIL",
                "reason_code": "value.type_mismatch",
                "reason": (
                    f"Expected JSON type {predicate['expected_type']}; "
                    f"observed {json_value_type(actual)}."
                ),
            }
    return {
        "status": "PASS" if passed else "FAIL",
        "reason_code": "predicate.pass" if passed else "predicate.mismatch",
        "reason": (
            "Predicate satisfied." if passed else f"Observed value does not satisfy {operator}."
        ),
    }


def predicate_expected(predicate: dict[str, Any]) -> Any:
    """Return a compact renderer-facing expectation."""
    operator = predicate.get("operator")
    if operator in {"equals", "url_equals"}:
        return predicate.get("expected")
    if operator == "one_of":
        return predicate.get("allowed_values")
    if operator == "type":
        return {"type": predicate.get("expected_type")}
    if operator == "state":
        return {"state": predicate.get("state")}
    if operator in {"range", "count"}:
        return {key: predicate[key] for key in ("exact", "minimum", "maximum") if key in predicate}
    if operator == "order":
        return predicate.get("sequence")
    return operator
