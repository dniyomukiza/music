"""Stripe Connect payout onboarding."""
from __future__ import annotations

import re

from playwright.sync_api import BrowserContext, expect

from e2e.pages.base import BasePage


class PayoutSetupPage(BasePage):
    PATH = "/mybook/payout-setup"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#btnStripeConnect", timeout=self.cfg.navigation_timeout_ms)

    def start_connect_onboarding(self, context: BrowserContext) -> None:
        with context.expect_page(timeout=60000) as page_info:
            self.page.click("#btnStripeConnect")
        connect_page = page_info.value
        connect_page.wait_for_load_state("domcontentloaded")
        expect(connect_page).to_have_url(
            re.compile(r"connect\.stripe\.com|stripe\.com"),
            timeout=60000,
        )
