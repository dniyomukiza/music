"""In-app ebook reader and download."""
from __future__ import annotations

from playwright.sync_api import APIResponse, expect

from e2e.pages.base import BasePage


class LibraryReaderPage(BasePage):
    def open_read(self, book_id: int, *, chapter_index: int = 0) -> None:
        self.goto(f"/mybook/library/books/{book_id}/read?ch={chapter_index}")
        self.page.wait_for_selector("#readerBody", timeout=self.cfg.navigation_timeout_ms)

    def expect_reader_content(self, *, title_fragment: str | None = None) -> None:
        expect(self.page.locator("#readerBody")).to_be_visible()
        if title_fragment:
            expect(self.page.locator("body")).to_contain_text(title_fragment, timeout=15000)

    def download_digital(self, book_id: int) -> APIResponse:
        base = self.cfg.base_url.rstrip("/")
        return self.page.request.get(f"{base}/mybook/books/{book_id}/download-digital")
