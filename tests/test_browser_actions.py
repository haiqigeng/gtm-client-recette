from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from browser_actions import (
    ActionError,
    compile_mcp_action,
    resolve_snapshot_ref,
    validate_decision,
    validate_scenario_decision,
)


def event(url: str | None = "https://example.test/product") -> dict:
    return {"event_id": "E-0001", "event_name": "view_item", "entry_url": url}


def decision(operation: str, *, role: str | None = None, name: str | None = None, value=None):
    locator = None if operation == "navigate" else {"role": role, "name": name, "exact": True}
    return {
        "event_id": "E-0001",
        "scenario_id": "view_item",
        "operation": operation,
        "semantic_locator": locator,
        "value": value,
        "reason": "The tracking-plan trigger and visible control agree.",
        "evidence_refs": ["Plan!A1", "before:control"],
    }


def scenario(target_url: str, *, source: str, setup: list[dict] | None = None) -> dict:
    return {
        "event_id": "E-0001",
        "scenario_id": "view_item",
        "target_url": target_url,
        "target_source": source,
        "setup_actions": setup or [],
        "measured_action": decision("click", role="button", name="Buy"),
        "reason": "The plan meaning and live page identify the scenario.",
        "evidence_refs": ["Plan!A1", "live:target"],
    }


SNAPSHOT = """
- main [ref=e1]:
  - button "Buy" [ref=e2]
  - textbox "Email" [ref=e3]
  - combobox "Language" [ref=e4]
"""


class BrowserActionTests(unittest.TestCase):
    def test_actions_compile_to_exact_mcp_calls(self) -> None:
        click = compile_mcp_action(
            event(), decision("click", role="button", name="Buy"), snapshot_text=SNAPSHOT
        )
        self.assertEqual(click["contract"], "playwright-mcp-action-v1")
        self.assertEqual(click["calls"][0]["tool"], "mcp__playwright__browser_click")
        self.assertEqual(click["calls"][0]["arguments"]["target"], "e2")

        fill = compile_mcp_action(
            event(),
            decision("fill", role="textbox", name="Email", value="test@example.test"),
            snapshot_text=SNAPSHOT,
        )
        self.assertEqual(fill["calls"][0]["tool"], "mcp__playwright__browser_fill_form")
        self.assertEqual(fill["calls"][0]["arguments"]["fields"][0]["target"], "e3")

        select = compile_mcp_action(
            event(),
            decision("select", role="combobox", name="Language", value="French"),
            snapshot_text=SNAPSHOT,
        )
        self.assertEqual(select["calls"][0]["tool"], "mcp__playwright__browser_select_option")

        press = compile_mcp_action(
            event(),
            decision("press", role="textbox", name="Email", value="Enter"),
            snapshot_text=SNAPSHOT,
        )
        self.assertEqual(
            [call["tool"] for call in press["calls"]],
            ["mcp__playwright__browser_click", "mcp__playwright__browser_press_key"],
        )

        navigate = compile_mcp_action(event(), decision("navigate"))
        self.assertEqual(navigate["calls"][0]["arguments"]["url"], event()["entry_url"])

    def test_exact_snapshot_resolution_has_no_fallback(self) -> None:
        locator = {"role": "button", "name": "Buy", "exact": True}
        self.assertEqual(resolve_snapshot_ref(SNAPSHOT, locator), "e2")
        with self.assertRaisesRegex(ActionError, "matches=0"):
            resolve_snapshot_ref(SNAPSHOT, {**locator, "name": "Missing"})
        with self.assertRaisesRegex(ActionError, "matches=2"):
            resolve_snapshot_ref(SNAPSHOT + '\n- button "Buy" [ref=e5]', locator)

    def test_invalid_decision_fails_before_call_compilation(self) -> None:
        invalid = decision("click", role="button", name="Buy")
        invalid["semantic_locator"]["exact"] = False
        with self.assertRaisesRegex(ActionError, "exact must be true"):
            validate_decision(invalid, event())
        with self.assertRaisesRegex(ActionError, "fill requires one exact textbox"):
            compile_mcp_action(
                event(),
                decision("fill", role="button", name="Buy", value="x"),
                snapshot_text=SNAPSHOT,
            )

    def test_scenario_remains_one_same_origin_path(self) -> None:
        accepted = validate_scenario_decision(
            scenario(
                "https://example.test/product",
                source="LIVE",
                setup=[decision("click", role="button", name="Buy")],
            ),
            event(None),
            "https://example.test/home",
        )
        self.assertEqual(len(accepted["setup_actions"]), 1)
        long_setup = [decision("click", role="button", name="Buy") for _ in range(13)]
        accepted = validate_scenario_decision(
            scenario("https://example.test/product", source="LIVE", setup=long_setup),
            event(None),
            "https://example.test/home",
        )
        self.assertEqual(len(accepted["setup_actions"]), 13)
        with self.assertRaisesRegex(ActionError, "prepared site origin"):
            validate_scenario_decision(
                scenario("https://outside.test/product", source="LIVE"),
                event(None),
                "https://example.test/home",
            )
        with self.assertRaisesRegex(ActionError, "supplied plan URL"):
            validate_scenario_decision(
                scenario("https://example.test/other", source="LIVE"),
                event("https://example.test/product"),
                "https://example.test/home",
            )


if __name__ == "__main__":
    unittest.main()
