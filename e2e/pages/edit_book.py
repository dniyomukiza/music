"""Book listing edit (/mybook/books/<id>/edit)."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class EditBookPage(BasePage):
    def open(self, book_id: int) -> None:
        self.goto(f"/mybook/books/{book_id}/edit")
        self.page.wait_for_selector("#editBookForm", timeout=self.cfg.navigation_timeout_ms)

    def update_title(self, title: str) -> None:
        self.page.fill("#title", title)

    def update_price(self, price: str) -> None:
        self.page.fill("#price", price)

    def save(self) -> None:
        self.page.click('button[type="submit"].btn-primary, #editBookForm button[type="submit"]')
        self.page.wait_for_load_state("networkidle")

    def expect_title_value(self, title: str) -> None:
        expect(self.page.locator("#title")).to_have_value(title)
