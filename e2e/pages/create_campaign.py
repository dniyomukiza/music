"""Author campaign launch (/mybook/books/<id>/create-campaign)."""
from __future__ import annotations

import re

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class CreateCampaignPage(BasePage):
    def open(self, book_id: int) -> None:
        self.goto(f"/mybook/books/{book_id}/create-campaign")
        self.page.wait_for_selector('form[method="POST"]', timeout=self.cfg.navigation_timeout_ms)

    def launch_campaign(
        self,
        *,
        title: str,
        description: str,
        funding_goal: str = "500",
        minimum_investment: str = "10",
        period_days: str = "30",
    ) -> None:
        self.page.fill("#title", title)
        # CKEditor — set via textarea if present
        self.page.evaluate(
            """(text) => {
                const el = document.getElementById('description');
                if (el) el.value = text;
                if (window.CKEDITOR && CKEDITOR.instances && CKEDITOR.instances.description) {
                    CKEDITOR.instances.description.setData(text);
                }
            }""",
            description,
        )
        self.page.fill("#funding_goal", funding_goal)
        self.page.fill("#minimum_investment", minimum_investment)
        self.page.fill("#investment_period_days", period_days)
        with self.page.expect_navigation(
            url=re.compile(r"/mybook/(investments|books)"),
            timeout=self.cfg.navigation_timeout_ms,
        ):
            self.page.click('input[type="submit"].btn-primary, button[type="submit"].btn-primary')

    def expect_campaign_listed(self, title: str) -> None:
        expect(self.page.locator("body")).to_contain_text(title, timeout=30000)
