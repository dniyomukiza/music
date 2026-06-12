"""Patron campaign discovery and investment."""
from __future__ import annotations

from playwright.sync_api import expect

from e2e.config import E2EConfig
from e2e.pages.base import BasePage
from e2e.support.stripe_checkout import complete_stripe_checkout


class InvestmentsPage(BasePage):
    PATH = "/mybook/investments"

    def open(self) -> None:
        self.goto(self.PATH)

    def open_campaign(self, campaign_id: int) -> None:
        self.goto(f"/mybook/investments/{campaign_id}")

    def invest(
        self,
        campaign_id: int,
        amount: str,
        *,
        context=None,
    ) -> None:
        self.goto(f"/mybook/investments/{campaign_id}/invest")
        self.page.wait_for_selector("#investmentForm", timeout=self.cfg.navigation_timeout_ms)
        self.page.fill("#investmentAmount", amount)
        with self.page.expect_navigation(
            url=lambda url: "checkout.stripe.com" in url,
            timeout=60000,
        ):
            self.page.click("#submitBtn")
        complete_stripe_checkout(self.page, timeout_ms=120_000)
        self.page.wait_for_load_state("networkidle")

    def expect_campaign_visible(self, title_fragment: str) -> None:
        expect(self.page.locator("body")).to_contain_text(title_fragment, timeout=30000)
