#!/usr/bin/env python3
"""Bound dynamic regular expressions and searched text used by acceptance rules."""

from __future__ import annotations

import re
from re import Pattern

MAX_PATTERN_LENGTH = 512
MAX_SEARCH_TEXT_LENGTH = 100_000
NESTED_QUANTIFIER = re.compile(
    r"\((?:[^()\\]|\\.)*(?:[+*?]|\{\d+(?:,\d*)?\})(?:[^()\\]|\\.)*\)(?:[+*?]|\{)"
)
QUANTIFIED_ALTERNATION = re.compile(
    r"\((?:\?(?:P?<[^>]+>|[:=!<])|)(?:[^()\\]|\\.)*\|(?:[^()\\]|\\.)*\)"
    r"(?:[+*?]|\{)"
)
BACKREFERENCE = re.compile(r"\\(?:[1-9][0-9]*|g<[^>]+>)")


def compile_pattern(value: object, *, label: str = "pattern") -> Pattern[str]:
    """Compile a bounded expression while rejecting common catastrophic forms."""
    pattern = str(value)
    if not pattern:
        raise ValueError(f"{label} cannot be empty")
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise ValueError(f"{label} exceeds {MAX_PATTERN_LENGTH} characters")
    if NESTED_QUANTIFIER.search(pattern):
        raise ValueError(f"{label} contains a nested quantified group")
    if QUANTIFIED_ALTERNATION.search(pattern):
        raise ValueError(f"{label} contains a quantified alternation")
    if BACKREFERENCE.search(pattern):
        raise ValueError(f"{label} contains a backreference")
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"{label} is not a valid regular expression") from exc


def bounded_text(value: object, *, label: str = "text") -> str:
    """Return text only when its size is safe for dynamic regular-expression matching."""
    text = str(value)
    if len(text) > MAX_SEARCH_TEXT_LENGTH:
        raise ValueError(f"{label} exceeds {MAX_SEARCH_TEXT_LENGTH} characters")
    return text


def fullmatch(value: object, text: object, *, label: str = "pattern") -> bool:
    return compile_pattern(value, label=label).fullmatch(bounded_text(text)) is not None


def search(value: object, text: object, *, label: str = "pattern") -> bool:
    return compile_pattern(value, label=label).search(bounded_text(text)) is not None


def finditer(value: object, text: object, *, label: str = "pattern") -> list[re.Match[str]]:
    """Return bounded matches for a conservatively validated dynamic expression."""
    return list(compile_pattern(value, label=label).finditer(bounded_text(text)))
