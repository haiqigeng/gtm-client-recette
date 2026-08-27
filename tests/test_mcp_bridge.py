from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts" / "mcp_bridge.py"


def line(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class McpBridgeTests(unittest.TestCase):
    def test_fixed_jsonl_bridge_parses_in_memory_and_writes_no_files(self) -> None:
        before = "1. [GET] https://example.test/ => [200]\n"
        after = (
            before + "2. [POST] https://www.google-analytics.com/g/collect?v=2&tid=G-X&en=view_item"
            " => [204]\n"
        )
        selected = """
- generic "Event: view_item" [ref=e1]
  - generic [ref=e2]: API call
  - generic [ref=e3]: "dataLayer.push({event: \\"view_item\\", ...})"
"""
        requests = [
            {
                "stage": "network_window",
                "before_text": before,
                "after_text": after,
                "navigation_occurred": False,
            },
            {
                "stage": "tag_selected",
                "snapshot_text": selected,
                "expected_event_name": "view_item",
            },
            {"stage": "close"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, "-B", str(BRIDGE)],
                cwd=directory,
                input="\n".join(line(request) for request in requests) + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = [json.loads(value) for value in completed.stdout.splitlines()]
            self.assertEqual(output[0]["result"]["ga4_candidate_indices"], [2])
            self.assertEqual(
                output[1]["result"]["tool"],
                "mcp__playwright__browser_run_code_unsafe",
            )
            self.assertEqual(output[2], {"status": "closed"})
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_page_capture_uses_existing_image_without_creating_handoff_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / ".image-E-0001-before.tmp.png"
            image.write_bytes(b"png-evidence")
            requests = [
                {
                    "stage": "page_capture",
                    "snapshot_text": '- heading "Product" [ref=e1]',
                    "screenshot_path": str(image),
                    "expected_url": "https://example.test/product",
                },
                {"stage": "close"},
            ]
            completed = subprocess.run(
                [sys.executable, "-B", str(BRIDGE)],
                cwd=directory,
                input="\n".join(line(request) for request in requests) + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = [json.loads(value) for value in completed.stdout.splitlines()]
            self.assertEqual(
                output[0]["result"]["aria_snapshot"],
                '- heading "Product" [ref=e1]',
            )
            self.assertEqual(list(Path(directory).iterdir()), [image])
            self.assertEqual(image.read_bytes(), b"png-evidence")

    def test_bridge_rejects_unknown_stage_and_exits(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(BRIDGE)],
            input=line({"stage": "invented"}) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 1)
        error = json.loads(completed.stdout)
        self.assertEqual(error["error"], "MCP_BRIDGE_CONTRACT")


if __name__ == "__main__":
    unittest.main()
