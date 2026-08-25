from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_runtime_tree_is_lean_and_fixed(self) -> None:
        runtime = {
            path.name
            for path in (ROOT / "scripts").iterdir()
            if path.is_file()
            and path.name
            not in {"build_skill_package.py", "check_release.py", "verify_release_artifact.py"}
        }
        self.assertEqual(
            runtime,
            {
                "judge.py",
                "playwright_collector.js",
                "recette.py",
                "report.py",
                "state.py",
                "xlsx_plan.py",
            },
        )
        self.assertFalse((ROOT / "references").exists())
        self.assertFalse((ROOT / "scripts" / "core").exists())

    def test_runtime_cli_has_only_four_commands(self) -> None:
        source = (ROOT / "scripts" / "recette.py").read_text(encoding="utf-8")
        commands = set(re.findall(r'add_parser\("([^"]+)"', source))
        self.assertEqual(commands, {"start", "next", "complete", "finish"})
        for forbidden in ("reopen", "repair", "retry", "handoff", "mode", "provider"):
            self.assertNotIn(f'add_parser("{forbidden}"', source)

    def test_skill_forbids_old_surfaces_and_browser_alternatives(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8").lower()
        self.assertIn("exactly one `.xlsx`", skill)
        self.assertIn("headed standalone playwright mcp", skill)
        self.assertIn("do not inspect the accumulated data layer tab", skill)
        self.assertIn("after two consecutive zero-evidence events", skill)
        self.assertNotIn("in-app browser", skill)
        self.assertNotIn("firefox", skill)
        self.assertNotIn("yaml", skill)

    def test_collector_has_fixed_bound_and_no_old_panels(self) -> None:
        source = (ROOT / "scripts" / "playwright_collector.js").read_text(encoding="utf-8")
        self.assertIn("const MAX_MS = 5000", source)
        self.assertIn('const CONTRACT = "playwright-mcp-v8"', source)
        self.assertNotIn('readPanel("Data Layer")', source)
        self.assertNotIn('readPanel("Variables")', source)
        self.assertNotIn("timeout_ms", source)
        self.assertNotIn("fallback", source.lower())

    def test_python_runtime_has_no_obvious_empty_functions(self) -> None:
        for path in (ROOT / "scripts").glob("*.py"):
            if path.name in {
                "build_skill_package.py",
                "check_release.py",
                "verify_release_artifact.py",
            }:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertFalse(
                        len(node.body) == 1 and isinstance(node.body[0], ast.Pass),
                        f"empty function {node.name} in {path.name}",
                    )


if __name__ == "__main__":
    unittest.main()
