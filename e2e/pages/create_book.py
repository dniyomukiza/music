"""In-platform create book flow."""
from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import expect

from e2e.config import FIXTURES_DIR
from e2e.pages.base import BasePage


class CreateBookPage(BasePage):
    PATH = "/mybook/books/create"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#createBookForm", timeout=self.cfg.navigation_timeout_ms)

    def create_with_cover(
        self,
        *,
        title: str,
        description: str = "E2E in-platform book project.",
        cover_path: Path | None = None,
    ) -> int:
        cover = cover_path or (FIXTURES_DIR / "cover.png")
        self.page.fill("#title", title)
        self.page.fill("#description", description)
        self.page.select_option("#language", value="en")
        self.page.select_option("#genre", value="fiction")
        self.page.set_input_files("#cover_image", str(cover))
        with self.page.expect_navigation(
            url=re.compile(r"/mybook/books/\d+"),
            timeout=self.cfg.navigation_timeout_ms,
        ):
            self.page.click('button[type="submit"].btn-ink-gold')
        m = re.search(r"/mybook/books/(\d+)", self.page.url)
        if not m:
            raise RuntimeError(f"Could not parse book id from URL: {self.page.url}")
        return int(m.group(1))
