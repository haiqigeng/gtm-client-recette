"""Frozen native Playwright methods for raw Tag Assistant evidence capture."""

from __future__ import annotations

import json
import re
from contextlib import suppress
from typing import Any


class TagAssistantError(ValueError):
    """Raised when the prepared Tag Assistant surface violates its contract."""


EVENT_ROW = re.compile(r"^(\d+)\s+(.+)$", re.S)
SNAPSHOT_BUTTON = re.compile(
    r'^\s*-\s+(?:\'|\")?button\s+"(?P<label>(?:[^"\\]|\\.)*)"\s+'
    r"\[ref=(?P<ref>[^\]]+)\]",
    re.MULTILINE,
)
SELECTED_EVENT = re.compile(r'generic\s+"Event:\s*(?P<name>[^"]+)"', re.I)
TAG_CARRIER = re.compile(
    r"^(?:trigger group|container loaded|dom ready|window loaded|"
    r"initiali[sz]ation)(?:\s+built-in trigger)?$",
    re.I,
)
GA4_TAG_BUTTON = re.compile(r"(?:Google Analytics:\s*GA4 Event|Google Tag)", re.I)
NUMBER = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?", re.I)
IDENTIFIER = re.compile(r"[A-Za-z_$][\w$.-]*")

# Tag Assistant renders its API Call chevron as the header's ::before pseudo-element,
# so it has no accessibility ref. This is the sole frozen production click for it.
API_CALL_EXPAND_CODE = """async (page) => {
  const header = page.locator('.api-call:not(.api-call--expanded) .api-call__header');
  if (await header.count() !== 1) throw new Error('Expected exactly one collapsed API call header');
  const box = await header.boundingBox();
  if (!box) throw new Error('API call header is not visible');
  await header.click({ position: { x: box.width - 20, y: box.height / 2 } });
  if (await page.locator('.api-call.api-call--expanded').count() !== 1) {
    throw new Error('API call did not expand');
  }
}"""


def _strip_javascript_comments(text: str) -> str:
    """Remove JavaScript comments without changing quoted content or evaluating code."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(text):
        character = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in "\"'`":
            quote = character
            output.append(character)
            index += 1
            continue
        if character == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if character == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index : index + 2] != "*/":
                index += 1
            index = min(index + 2, len(text))
            continue
        output.append(character)
        index += 1
    return "".join(output)


def _unescape_snapshot_label(value: str) -> str:
    if "\\" not in value:
        return value
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return value


def parse_event_overview(snapshot_text: str, preview_cursor: int) -> dict[str, Any]:
    """Parse all post-cursor Tag Assistant event buttons from one MCP snapshot."""
    if not isinstance(snapshot_text, str) or "Tag Assistant" not in snapshot_text:
        raise TagAssistantError("Snapshot is not a Tag Assistant accessibility surface.")
    if "Connected" not in snapshot_text:
        raise TagAssistantError("Tag Assistant snapshot is not connected.")
    if not isinstance(preview_cursor, int) or preview_cursor < 0:
        raise TagAssistantError("Preview cursor must be a non-negative integer.")
    rows: dict[int, dict[str, Any]] = {}
    for match in SNAPSHOT_BUTTON.finditer(snapshot_text):
        label = _unescape_snapshot_label(match.group("label"))
        event_match = EVENT_ROW.fullmatch(label)
        if not event_match:
            continue
        cursor = int(event_match.group(1))
        if cursor <= preview_cursor:
            continue
        rows[cursor] = {
            "cursor": cursor,
            "row_name": event_match.group(2).removesuffix(" Built-in trigger").strip(),
            "ref": match.group("ref"),
        }
    ordered = [rows[cursor] for cursor in sorted(rows)]
    return {
        "preview_cursor_before": preview_cursor,
        "preview_cursor_after": ordered[-1]["cursor"] if ordered else preview_cursor,
        "rows": ordered,
    }


def candidate_and_carrier_rows(
    overview: dict[str, Any], selector: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Bound detail capture to selector rows and plausible causal GTM carrier rows."""
    identities = {
        str(value).casefold()
        for key, value in selector.items()
        if key in {"event", "event_name"} and isinstance(value, str) and value
    }
    rows = overview.get("rows") if isinstance(overview, dict) else None
    if not identities or not isinstance(rows, list):
        raise TagAssistantError("Candidate selection requires one valid overview and selector.")
    candidates = [
        row
        for row in rows
        if isinstance(row, dict) and str(row.get("row_name") or "").casefold() in identities
    ]
    if not candidates:
        return {"candidate_rows": [], "carrier_rows": []}
    first = min(int(row["cursor"]) for row in candidates)
    carriers = [
        row
        for row in rows
        if isinstance(row, dict)
        and int(row.get("cursor", -1)) >= first
        and (
            str(row.get("row_name") or "").casefold() in identities
            or TAG_CARRIER.fullmatch(str(row.get("row_name") or "")) is not None
        )
    ]
    return {"candidate_rows": candidates, "carrier_rows": carriers}


def selected_event_name(snapshot_text: str) -> str:
    match = SELECTED_EVENT.search(snapshot_text if isinstance(snapshot_text, str) else "")
    if not match:
        raise TagAssistantError("Selected Tag Assistant event identity is absent.")
    return match.group("name").strip()


def exact_button_ref(snapshot_text: str, label: str) -> str:
    matches = [
        match.group("ref")
        for match in SNAPSHOT_BUTTON.finditer(snapshot_text)
        if _unescape_snapshot_label(match.group("label")) == label
    ]
    if len(matches) != 1:
        raise TagAssistantError(
            f"Tag Assistant button must resolve exactly once; label={label!r}, "
            f"matches={len(matches)}."
        )
    return matches[0]


def compile_api_call_expand(snapshot_text: str, expected_event_name: str) -> dict[str, Any]:
    """Compile the one exact right-edge chevron click after selected-row validation."""
    selected = selected_event_name(snapshot_text)
    if selected.casefold() != str(expected_event_name or "").strip().casefold():
        raise TagAssistantError(
            f"Selected Tag Assistant event differs from expected event: "
            f"selected={selected!r}, expected={expected_event_name!r}."
        )
    calls = [
        line
        for line in snapshot_text.splitlines()
        if re.search(r"\b(?:dataLayer\.push|gtag\s*\()", line, re.I)
    ]
    if len(calls) != 1:
        raise TagAssistantError(
            f"Selected event must expose exactly one API Call; matches={len(calls)}."
        )
    if "..." not in calls[0] and "â€¦" not in calls[0]:
        raise TagAssistantError("Selected API Call is already expanded; no click is permitted.")
    return {
        "contract": "tag-assistant-api-expand-v1",
        "tool": "mcp__playwright__browser_run_code_unsafe",
        "arguments": {"code": API_CALL_EXPAND_CODE},
    }


def api_call_text(snapshot_text: str) -> str:
    """Extract one fully expanded API Call from a selected-row MCP snapshot."""
    for line in snapshot_text.splitlines() if isinstance(snapshot_text, str) else []:
        if not re.search(r"\b(?:dataLayer\.push|gtag\s*\()", line, re.I):
            continue
        value = line.split(":", 1)[1].strip() if ":" in line else line.strip()
        if value.startswith('"') and value.endswith('"'):
            with suppress(ValueError, TypeError):
                value = json.loads(value)
        if "..." in value or "…" in value:
            raise TagAssistantError("Tag Assistant API Call remains collapsed after one click.")
        return value
    raise TagAssistantError("Expanded Tag Assistant API Call text is absent.")


def concerned_tag_buttons(snapshot_text: str) -> list[dict[str, Any]]:
    """Return only fired Google/GA4 tag detail buttons from one Tags snapshot."""
    tags = []
    for match in SNAPSHOT_BUTTON.finditer(snapshot_text if isinstance(snapshot_text, str) else ""):
        label = _unescape_snapshot_label(match.group("label"))
        if not GA4_TAG_BUTTON.search(label):
            continue
        tags.append(
            {
                "name": re.sub(
                    r"\s+(?:Google Analytics:\s*GA4 Event|Google Tag)\s+-\s+"
                    r"(?:Succeeded|Failed)$",
                    "",
                    label,
                    flags=re.I,
                ),
                "label": label,
                "ref": match.group("ref"),
                "fired": bool(re.search(r"-\s+Succeeded$", label, re.I)),
            }
        )
    return tags


def properties_table(snapshot_text: str) -> dict[str, str]:
    """Parse the Tag details Properties table in Names or Values display."""
    text = snapshot_text if isinstance(snapshot_text, str) else ""
    start = text.find(": Properties")
    if start < 0:
        raise TagAssistantError("Tag details Properties table is absent.")
    end = text.find(": Firing Triggers", start)
    section = text[start : end if end >= 0 else len(text)]
    rows = re.split(r"(?m)^\s*-\s+row(?:\s|\[)", section)[1:]
    output: dict[str, str] = {}
    for row in rows:
        cells = []
        for cell in re.split(r"(?m)^\s*-\s+(?:'|\")?cell(?:\s|\[)", row)[1:]:
            quoted = re.search(r'"((?:[^"\\]|\\.)*)"', cell)
            if quoted:
                cells.append(_unescape_snapshot_label(quoted.group(1)))
                continue
            descendant = re.search(
                r'(?m)^\s*-\s+generic(?:\s+\[ref=[^\]]+\])?:\s+"?([^"\n]+)"?$', cell
            )
            cells.append(descendant.group(1).strip() if descendant else "")
        if len(cells) >= 2 and cells[0] and cells[0].casefold() != "name":
            output[cells[0]] = cells[1]
    if not output:
        raise TagAssistantError("Tag details Properties table contains no data rows.")
    return output


def _tokens(text: str) -> list[tuple[str, Any]]:
    output: list[tuple[str, Any]] = []
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if character in "{}[]:,()+":
            output.append((character, character))
            index += 1
            continue
        if character in "\"'`":
            quote = character
            index += 1
            value = ""
            while index < len(text):
                current = text[index]
                index += 1
                if current == quote:
                    output.append(("value", value))
                    break
                if current != "\\":
                    value += current
                    continue
                if index >= len(text):
                    raise TagAssistantError("Unterminated API Call escape.")
                escaped = text[index]
                index += 1
                escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v"}
                if escaped == "u" and re.fullmatch(r"[0-9a-fA-F]{4}", text[index : index + 4]):
                    value += chr(int(text[index : index + 4], 16))
                    index += 4
                else:
                    value += escapes.get(escaped, escaped)
            else:
                raise TagAssistantError("Unterminated API Call string.")
            continue
        number = NUMBER.match(text, index)
        if number:
            raw = number.group(0)
            output.append(
                ("value", float(raw) if any(mark in raw.casefold() for mark in ".e") else int(raw))
            )
            index = number.end()
            continue
        identifier = IDENTIFIER.match(text, index)
        if identifier:
            raw = identifier.group(0)
            literals = {"true": True, "false": False, "null": None, "undefined": None, "NaN": None}
            output.append(("value", literals.get(raw, raw)))
            index = identifier.end()
            continue
        raise TagAssistantError(f"Unsupported API Call token at {index}.")
    return output


class _ValueParser:
    def __init__(self, tokens: list[tuple[str, Any]]) -> None:
        self.tokens = tokens
        self.index = 0

    def _peek(self) -> str | None:
        return self.tokens[self.index][0] if self.index < len(self.tokens) else None

    def _take(self, token_type: str) -> Any:
        if self._peek() != token_type:
            raise TagAssistantError(f"Expected API Call token {token_type}.")
        value = self.tokens[self.index][1]
        self.index += 1
        return value

    def _atom(self) -> Any:
        token_type = self._peek()
        if token_type == "value":
            return self._take("value")
        if token_type == "{":
            self._take("{")
            value: dict[str, Any] = {}
            while self._peek() != "}":
                key = str(self._take("value"))
                self._take(":")
                value[key] = self.value()
                if self._peek() == ",":
                    self._take(",")
                else:
                    break
            self._take("}")
            return value
        if token_type == "[":
            self._take("[")
            value = []
            while self._peek() != "]":
                value.append(self.value())
                if self._peek() == ",":
                    self._take(",")
                else:
                    break
            self._take("]")
            return value
        if token_type == "(":
            self._take("(")
            value = self.value()
            self._take(")")
            return value
        raise TagAssistantError("Missing or unsupported API Call value.")

    def value(self) -> Any:
        value = self._atom()
        while self._peek() == "+":
            self._take("+")
            right = self._atom()
            value = f"{'' if value is None else value}{'' if right is None else right}"
        return value

    def arguments(self) -> list[Any]:
        values = []
        while self.index < len(self.tokens):
            values.append(self.value())
            if self._peek() == ",":
                self._take(",")
            else:
                break
        if self.index != len(self.tokens):
            raise TagAssistantError("Unparsed API Call content.")
        return values


def parse_api_call(text: str) -> dict[str, Any]:
    """Parse dataLayer.push or gtag arguments without evaluating captured text."""
    source = _strip_javascript_comments(str(text or ""))
    match = re.search(r"(?:dataLayer\s*\.\s*push|gtag)\s*\(", source, re.I)
    if not match:
        return {"complete": False, "reason": "API Call has no dataLayer.push or gtag call."}
    start = match.end()
    depth = 1
    quote: str | None = None
    escaped = False
    for index in range(start, len(source)):
        character = source[index]
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in "\"'`":
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                try:
                    arguments = _ValueParser(_tokens(source[start:index])).arguments()
                except TagAssistantError as error:
                    return {"complete": False, "reason": str(error)}
                payload = next(
                    (value for value in reversed(arguments) if isinstance(value, dict)), None
                )
                if (
                    len(arguments) >= 2
                    and str(arguments[0]).casefold() == "event"
                    and isinstance(arguments[1], str)
                ):
                    payload = {"event": arguments[1], **(payload or {})}
                return {"complete": True, "arguments": arguments, "payload": payload}
    return {"complete": False, "reason": "API Call text is truncated."}


def _path_values(value: Any, path: str) -> list[Any]:
    current = [value]
    for part in path.split("."):
        is_array = part.endswith("[]")
        name = part[:-2] if is_array else part
        selected_values: list[Any] = []
        for candidate in current:
            if not isinstance(candidate, dict):
                continue
            key = next((key for key in candidate if str(key).casefold() == name.casefold()), None)
            if key is None:
                continue
            selected = candidate[key]
            if is_array and isinstance(selected, list):
                selected_values.extend(selected)
            elif not is_array:
                selected_values.append(selected)
        current = selected_values
    return current


def _same(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def detect_event(capture: dict[str, Any], selector: dict[str, Any]) -> dict[str, Any]:
    """Detect exact occurrences from candidate API Calls plus one complete row overview."""
    if not isinstance(selector, dict) or not selector or "event" not in selector:
        raise TagAssistantError("Event detection requires a selector containing event.")
    before = capture.get("preview_cursor_before")
    overview = capture.get("overview_rows")
    rows = capture.get("rows")
    if not isinstance(before, int) or not isinstance(overview, list) or not isinstance(rows, list):
        raise TagAssistantError("Raw Tag Assistant capture contract is invalid.")
    overview_rows = [row for row in overview if isinstance(row, dict)]
    contiguous = all(
        row.get("cursor") == before + index for index, row in enumerate(overview_rows, 1)
    )
    identities = {
        str(value).casefold()
        for key, value in selector.items()
        if key in {"event", "event_name"} and isinstance(value, str)
    }
    candidate_cursors = {
        row.get("cursor")
        for row in overview_rows
        if str(row.get("row_name") or "").casefold() in identities
    }
    calls = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("api_call_text"):
            continue
        parsed = parse_api_call(row.get("api_call_text", ""))
        payload = parsed.get("payload")
        calls.append(
            {
                "cursor": row.get("cursor"),
                "row_name": row.get("row_name"),
                "payload": payload,
                "arguments": parsed.get("arguments", []),
                "complete": parsed["complete"],
                "reason": parsed.get("reason"),
            }
        )
    captured_candidate_cursors = {
        call["cursor"] for call in calls if call["cursor"] in candidate_cursors
    }
    selected = [
        call
        for call in calls
        if isinstance(call["payload"], dict)
        and all(
            bool(values := _path_values(call["payload"], path))
            and any(_same(value, expected) for value in values)
            for path, expected in selector.items()
        )
    ]
    complete = (
        contiguous
        and candidate_cursors == captured_candidate_cursors
        and all(call["complete"] for call in calls if call["cursor"] in candidate_cursors)
    )
    return {
        "complete": complete,
        "attributable": contiguous,
        "occurrence_count": len(selected),
        "selected": selected[0] if selected else None,
        "calls": calls,
        "overview_rows": overview_rows,
        "reason": None if complete else "Preview chronology or API Call parsing is incomplete.",
    }
