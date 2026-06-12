"""AI writing assistant API and chapter editor toolbar."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class AIAssistantPage(BasePage):
    def assert_api_enabled(self) -> None:
        base = self.cfg.base_url.rstrip("/")
        resp = self.page.request.get(f"{base}/mybook/ai/status")
        assert resp.ok, f"AI status failed: {resp.status}"
        data = resp.json()
        assert data.get("enabled"), data

    def generate_content_snippet(self, *, prompt: str = "Write one sentence about a river.") -> str:
        import json

        base = self.cfg.base_url.rstrip("/")
        resp = self.page.request.post(
            f"{base}/mybook/ai/generate-content",
            data=json.dumps({"prompt": prompt, "context": "", "max_tokens": 120}),
            headers={"Content-Type": "application/json"},
        )
        assert resp.ok, f"generate-content failed: {resp.status} {resp.text()}"
        data = resp.json()
        text = (
            data.get("content")
            or data.get("generated_content")
            or data.get("text")
            or data.get("result")
            or ""
        )
        assert isinstance(text, str) and len(text.strip()) > 0, data
        return text.strip()

    def open_chapter_editor(self, book_id: int, chapter_id: int) -> None:
        self.goto(f"/mybook/books/{book_id}/chapters/{chapter_id}/edit")
        self.page.wait_for_load_state("domcontentloaded")

    def expect_toolbar_present(self) -> None:
        expect(self.page.locator(".ai-assistant-toolbar, [data-ai-action], .ai-action-btn").first).to_be_attached(
            timeout=30000
        )
