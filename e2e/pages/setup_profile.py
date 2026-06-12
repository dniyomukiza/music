"""Author profile setup (/mybook/setup-profile)."""
from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from e2e.config import E2EConfig
from e2e.pages.base import BasePage


class SetupProfilePage(BasePage):
    PATH = "/mybook/setup-profile"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#profileSetupForm", timeout=self.cfg.navigation_timeout_ms)

    def complete_minimal(self, pen_name: str | None = None) -> None:
        """Save profile once to unlock My books / Create book."""
        if pen_name:
            self.page.fill("#penName", pen_name)
        self.page.click("#inkSetupSubmit")
        # AJAX save then window.location — land on books dashboard (or ?next= target)
        expect(self.page).to_have_url(
            re.compile(r"/mybook/(books|upload-digital-book)"),
            timeout=self.cfg.navigation_timeout_ms,
        )
