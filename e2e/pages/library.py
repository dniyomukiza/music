"""Buyer library page."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class LibraryPage(BasePage):
    PATH = "/mybook/library"

    def open(self, book_id: int | None = None) -> None:
        path = self.PATH
        if book_id is not None:
            path = f"{path}?book_id={book_id}"
        self.goto(path)
        self.page.wait_for_selector("#library-main", timeout=self.cfg.navigation_timeout_ms)

    def expect_book_in_library(self, title: str) -> None:
        expect(self.page.locator("#libraryList, #library-main")).to_contain_text(
            title, timeout=self.cfg.navigation_timeout_ms
        )
