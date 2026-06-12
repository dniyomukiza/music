"""Base page object with shared navigation helpers."""
from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from e2e.config import E2EConfig


class BasePage:
    def __init__(self, page: Page, cfg: E2EConfig) -> None:
        self.page = page
        self.cfg = cfg

    def goto(self, path: str) -> None:
        if path.startswith("http"):
            url = path
        else:
            url = f"{self.cfg.base_url.rstrip('/')}{path}"
        # commit avoids net::ERR_ABORTED when the server issues an immediate redirect
        self.page.goto(url, wait_until="commit", timeout=self.cfg.navigation_timeout_ms)
        self.page.wait_for_load_state("domcontentloaded", timeout=self.cfg.navigation_timeout_ms)

    def expect_url_contains(self, fragment: str) -> None:
        expect(self.page).to_have_url(re.compile(re.escape(fragment)))
