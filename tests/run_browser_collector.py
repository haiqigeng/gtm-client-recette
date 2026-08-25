from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import Error, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "tests" / "fixtures" / "tag_assistant.html").read_text(encoding="utf-8")
COLLECTOR = (ROOT / "scripts" / "playwright_collector.js").read_text(encoding="utf-8")


def main() -> int:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "https://tagassistant.google.com/**",
            lambda route: route.fulfill(status=200, content_type="text/html", body=HTML),
        )
        page.goto("https://tagassistant.google.com/fixture")
        installed = page.evaluate(COLLECTOR)
        assert installed == {
            "observer_contract": "playwright-mcp-v8",
            "installed": True,
            "current_cursor": 3,
            "current_document_cursor": 1,
            "max_collection_ms": 5000,
        }
        result = page.evaluate(
            "spec => globalThis.__gtmRecetteCollect(spec)",
            {
                "observer_contract": "playwright-mcp-v8",
                "preview_cursor": 1,
                "selector": {"event": "view_item"},
            },
        )
        assert result["preview_cursor"] == 3
        assert result["source"]["complete"] is True
        assert result["source"]["occurrence_count"] == 1
        assert result["source"]["selected"]["payload"]["ecommerce"]["currency"] == "EUR"
        assert result["gtm"]["complete"] is True
        assert len(result["gtm"]["tags"]) == 1
        assert result["gtm"]["tags"][0]["runtime"]["ecommerce"]["items"][0]["quantity"] == 1
        assert result["behavior"]["messages"][0]["business"] is True
        try:
            page.evaluate(COLLECTOR)
        except Error as error:
            assert "already installed" in str(error)
        else:
            raise AssertionError("Observer reinstall was not rejected.")
        browser.close()
    print(json.dumps({"collector_browser_fixture": "PASS"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
