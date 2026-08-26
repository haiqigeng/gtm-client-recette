from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from browser_capture import (
    REQUIRED_MCP_TOOLS,
    CaptureError,
    ga4_candidate_indices,
    network_delta,
    parse_network_detail,
    parse_network_list,
    validate_mcp_preflight,
    validate_page_capture,
)
from tag_assistant import (
    TagAssistantError,
    api_call_text,
    candidate_and_carrier_rows,
    compile_api_call_expand,
    concerned_tag_buttons,
    exact_button_ref,
    parse_event_overview,
    properties_table,
    selected_event_name,
)

TAG_ASSISTANT_OVERVIEW = """
- img "Tag Assistant" [ref=e6]
- generic [ref=e60]:
  - generic [ref=e61]: Connected
- button "21 view_item_list" [ref=e323]
- button "22 Set" [ref=e320]
- button "23 Consent Update" [ref=e317]
- button "24 Trigger Group" [ref=e298]
- button "25 Window Loaded Built-in trigger" [ref=e291]
"""

SELECTED_SOURCE = (
    TAG_ASSISTANT_OVERVIEW
    + """
- generic [ref=e178]:
  - generic "Event: view_item_list" [ref=e630]
  - generic [ref=e402]:
    - generic [ref=e403]: API call
    - generic [ref=e409]:
      - textbox [ref=e410]
      - generic [ref=e411]: "dataLayer.push({event: \\"view_item_list\\", ecommerce: {currency: \\"EUR\\"}})"
  - button "Tags" [ref=e208]
"""
)

SELECTED_COLLAPSED = SELECTED_SOURCE.replace(
    'dataLayer.push({event: \\"view_item_list\\", ecommerce: {currency: \\"EUR\\"}})',
    'dataLayer.push({event: \\"view_item_list\\", ...})',
)

TAG_SUMMARY = (
    TAG_ASSISTANT_OVERVIEW
    + """
- generic "Event: Trigger Group" [ref=e630]
- button "Tags" [ref=e208]
- 'button "GA4 - All - ViewItemList Google Analytics: GA4 Event - Succeeded" [ref=e647]':
- button "Google - All - Conversion Linker Conversion Linker - Succeeded" [ref=e638]
"""
)

TAG_DETAIL = """
- generic [ref=e696]: Tag details
- radio "Names" [checked] [ref=e701]
- radio "Values" [ref=e703]
- generic [ref=e704]:
  - generic [ref=e705]: Properties
  - table [ref=e707]:
    - row [ref=e709]:
      - columnheader "Name" [ref=e710]
      - columnheader "Value" [ref=e711]
    - row [ref=e713]:
      - cell "Type" [ref=e714]
      - 'cell "Google Analytics: GA4 Event" [ref=e716]'
    - row [ref=e749]:
      - cell "Event Name" [ref=e750]
      - cell "view_item_list" [ref=e752]
  - generic [ref=e774]: Firing Triggers
- button "Close screen" [ref=e687]
"""


class CaptureTests(unittest.TestCase):
    def test_mcp_preflight_requires_tools_target_and_connected_preview(self) -> None:
        tabs = """### Result
- 0: (current) [Tag Assistant [Connected]](https://tagassistant.google.com/#/preview)
- 1: [Target](https://example.test/)
"""
        result = validate_mcp_preflight(sorted(REQUIRED_MCP_TOOLS), tabs, "https://example.test/")
        self.assertEqual(result["target_tab"]["index"], 1)
        with self.assertRaisesRegex(CaptureError, "tool is unavailable"):
            validate_mcp_preflight(
                sorted(REQUIRED_MCP_TOOLS - {"mcp__playwright__browser_click"}),
                tabs,
                "https://example.test/",
            )
        with_extras = (
            tabs
            + "- 2: [Other site](https://unrelated.test/)\n"
            + "- 3: [GTM](https://tagmanager.google.com/)\n"
            + "- 4: [](about:blank)\n"
        )
        result = validate_mcp_preflight(
            sorted(REQUIRED_MCP_TOOLS), with_extras, "https://example.test/"
        )
        self.assertEqual(len(result["ignored_tabs"]), 3)
        with self.assertRaisesRegex(CaptureError, "connected Tag Assistant"):
            validate_mcp_preflight(
                sorted(REQUIRED_MCP_TOOLS),
                tabs.replace("[Connected]", "[Disconnected]"),
                "https://example.test/",
            )

    def test_page_capture_validates_mcp_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "before.png"
            image.write_bytes(b"png")
            capture = validate_page_capture(
                '- heading "Product" [ref=e1]', image, expected_url="https://example.test/p"
            )
            self.assertEqual(capture["observer_contract"], "playwright-mcp-page-v1")
            with self.assertRaisesRegex(CaptureError, "missing or empty"):
                validate_page_capture(
                    "snapshot", Path(directory) / "missing.png", expected_url="https://example.test"
                )

    def test_network_delta_and_detail_use_numbered_mcp_contract(self) -> None:
        before = """### Result
1. [GET] https://example.test/ => [200]
2. [POST] https://www.google-analytics.com/g/collect?v=2&tid=G-X&en=page_view => [204]
"""
        after = (
            before
            + "3. [POST] https://www.google-analytics.com/g/collect?v=2&tid=G-X&en=add_to_cart => [204]\n"
        )
        rows = network_delta(before, after, navigation_occurred=False)
        self.assertEqual([row["index"] for row in rows], [3])
        self.assertEqual(ga4_candidate_indices(rows), [3])
        self.assertEqual(len(network_delta(before, after, navigation_occurred=True)), 3)
        self.assertEqual(len(parse_network_list(after)), 3)
        detail = """#3 [POST] https://www.google-analytics.com/g/collect?v=2&tid=G-X&en=add_to_cart

  General
    status:    [204]

  Request body
    ep.currency=EUR

  Response headers
    content-type: text/plain
"""
        parsed = parse_network_detail(detail)
        self.assertEqual(parsed["status"], 204)
        self.assertEqual(parsed["post_data"], "ep.currency=EUR")

    def test_tag_assistant_snapshot_path_is_candidate_scoped(self) -> None:
        overview = parse_event_overview(TAG_ASSISTANT_OVERVIEW, 20)
        selected = candidate_and_carrier_rows(overview, {"event": "view_item_list"})
        self.assertEqual([row["cursor"] for row in selected["candidate_rows"]], [21])
        self.assertEqual([row["cursor"] for row in selected["carrier_rows"]], [21, 24, 25])
        self.assertNotIn(22, [row["cursor"] for row in selected["carrier_rows"]])

        self.assertEqual(selected_event_name(SELECTED_SOURCE), "view_item_list")
        expand = compile_api_call_expand(SELECTED_COLLAPSED, "view_item_list")
        self.assertEqual(expand["tool"], "mcp__playwright__browser_run_code_unsafe")
        self.assertIn("box.width - 20", expand["arguments"]["code"])
        self.assertIn(".api-call:not(.api-call--expanded)", expand["arguments"]["code"])
        self.assertIn('event: "view_item_list"', api_call_text(SELECTED_SOURCE))
        self.assertEqual(exact_button_ref(SELECTED_SOURCE, "Tags"), "e208")

        tags = concerned_tag_buttons(TAG_SUMMARY)
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]["ref"], "e647")
        self.assertTrue(tags[0]["fired"])
        self.assertEqual(properties_table(TAG_DETAIL)["Event Name"], "view_item_list")

    def test_tag_assistant_never_salvages_collapsed_or_ambiguous_evidence(self) -> None:
        with self.assertRaisesRegex(TagAssistantError, "remains collapsed"):
            api_call_text(SELECTED_COLLAPSED)
        with self.assertRaisesRegex(TagAssistantError, "already expanded"):
            compile_api_call_expand(SELECTED_SOURCE, "view_item_list")
        with self.assertRaisesRegex(TagAssistantError, "differs from expected"):
            compile_api_call_expand(SELECTED_COLLAPSED, "add_to_cart")
        with self.assertRaisesRegex(TagAssistantError, "exactly once"):
            exact_button_ref(SELECTED_SOURCE + '\n- button "Tags" [ref=e999]', "Tags")


if __name__ == "__main__":
    unittest.main()
