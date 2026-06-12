"""Reader account settings (/mybook/account)."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class ReaderAccountPage(BasePage):
    PATH = "/mybook/account"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#reader-account-main", timeout=self.cfg.navigation_timeout_ms)

    def update_profile(self, *, first_name: str, last_name: str, email: str) -> None:
        self.page.fill("#first_name", first_name)
        self.page.fill("#last_name", last_name)
        self.page.fill("#email", email)
        self.page.click('form button[type="submit"]')
        self.page.wait_for_load_state("networkidle")

    def expect_name_fields(self, first_name: str, last_name: str) -> None:
        expect(self.page.locator("#first_name")).to_have_value(first_name)
        expect(self.page.locator("#last_name")).to_have_value(last_name)
