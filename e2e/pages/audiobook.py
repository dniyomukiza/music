"""Audiobook generation and status polling."""
from __future__ import annotations

import time

from playwright.sync_api import expect

from e2e.config import E2EConfig
from e2e.pages.base import BasePage


class AudiobookPage(BasePage):
    def open_edit(self, book_id: int) -> None:
        self.goto(f"/mybook/books/{book_id}/edit")
        self.page.wait_for_selector("#editBookForm", timeout=self.cfg.navigation_timeout_ms)

    def trigger_generation(self, book_id: int) -> str | None:
        """POST generate-audiobook; return task_id if JSON provides one."""
        resp = self.page.request.post(
            f"{self.cfg.base_url.rstrip('/')}/mybook/books/{book_id}/generate-audiobook",
        )
        if not resp.ok:
            return None
        try:
            data = resp.json()
            return data.get("task_id")
        except Exception:
            return None

    def poll_until_complete(
        self,
        book_id: int,
        *,
        timeout_ms: int | None = None,
        poll_interval_s: float = 5.0,
    ) -> dict:
        deadline = time.time() + (timeout_ms or self.cfg.upload_timeout_ms) / 1000
        last: dict = {}
        base = self.cfg.base_url.rstrip("/")
        while time.time() < deadline:
            resp = self.page.request.get(f"{base}/mybook/books/{book_id}/audio-generation-status")
            if resp.ok:
                last = resp.json()
                status = (last.get("status") or last.get("generation_status") or "").lower()
                if status in ("completed", "complete", "done"):
                    return last
                if status in ("failed", "error"):
                    return last
            time.sleep(poll_interval_s)
        return last

    def open_player(self, book_id: int) -> None:
        self.goto(f"/mybook/audiobook/{book_id}/player")
        self.page.wait_for_load_state("domcontentloaded")

    def expect_player_loaded(self) -> None:
        expect(self.page.locator("body")).to_contain_text("Audiobook", timeout=30000)
