"""Author earnings dashboard."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class EarningsPage(BasePage):
    PATH = "/mybook/earnings"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_load_state("domcontentloaded")

    def expect_loaded(self) -> None:
        expect(self.page.locator("body")).to_contain_text("Earnings", timeout=30000)
