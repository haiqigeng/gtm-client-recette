from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_runtime_has_only_fixed_python_components(self) -> None:
        names = {path.name for path in (ROOT / "scripts").iterdir() if path.is_file()}
        self.assertEqual(
            names,
            {
                "adaptive.py",
                "browser_actions.py",
                "browser_capture.py",
                "evidence.py",
                "judge.py",
                "mcp_bridge.py",
                "recette.py",
                "report.py",
                "run_tests.py",
                "state.py",
                "tag_assistant.py",
                "xlsx_plan.py",
            },
        )
        self.assertFalse(any((ROOT / "scripts").glob("*.js")))

    def test_skill_freezes_one_scenario_ga4_and_playwright_mcp(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8").casefold()
        self.assertIn("one live scenario per identifiable event", skill)
        self.assertIn("no scope confirmation phrase", skill)
        self.assertIn("playwright mcp", skill)
        self.assertIn("tag assistant screenshots", skill)
        for forbidden in ("retry", "fallback", "backup", "second scenario"):
            self.assertIn(f"no {forbidden}", skill)

    def test_imperfect_plan_and_live_resolution_contract_is_explicit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        contract = (ROOT / "references" / "contracts.md").read_text(encoding="utf-8")
        self.assertIn("shortest finite genuinely necessary", skill)
        self.assertIn("same-origin target", skill)
        self.assertIn('"schema_version":"3.0.0"', contract)
        self.assertIn("data_layer_payload", contract)
        self.assertIn("every other tab is ignored", contract.casefold())
        self.assertIn("parsed as text without evaluation", contract)
        self.assertIn("Tag Assistant screenshots", contract)
        self.assertNotIn("entry_url must be", contract)

    def test_production_runtime_has_no_page_javascript_or_ad_hoc_browser_code(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in (ROOT / "scripts").glob("*.py")
        )
        self.assertNotIn("playwright.sync_api", source)
        self.assertNotIn("browser_evaluate", source)
        self.assertNotIn("page.evaluate", source)
        tag_source = (ROOT / "scripts" / "tag_assistant.py").read_text(encoding="utf-8")
        self.assertIn("box.width - 20", tag_source)
        self.assertIn("Expected exactly one collapsed API call header", tag_source)
        self.assertNotIn("dispatchEvent", tag_source)

    def test_removed_legacy_machinery_is_absent(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8") for path in (ROOT / "scripts").glob("*.py")
        )
        for forbidden in (
            "compile_xlsx",
            "consecutive_zero_evidence",
            "coverage_unreachable",
            "playwright-mcp-v8",
            "prepare_bundle",
        ):
            self.assertNotIn(forbidden, source)

    def test_python_runtime_has_no_empty_functions(self) -> None:
        for path in (ROOT / "scripts").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertFalse(
                        len(node.body) == 1 and isinstance(node.body[0], ast.Pass),
                        f"empty function {node.name} in {path.name}",
                    )


if __name__ == "__main__":
    unittest.main()
