"""Chapter creation for in-platform books."""
from __future__ import annotations

import re

from playwright.sync_api import expect

from e2e.pages.base import BasePage


class CreateChapterPage(BasePage):
    def open(self, book_id: int) -> None:
        self.goto(f"/mybook/books/{book_id}/chapters/create")
        self.page.wait_for_selector("#createChapterForm", timeout=self.cfg.navigation_timeout_ms)

    def create_chapter(
        self,
        *,
        title: str,
        content: str,
        chapter_number: int = 1,
    ) -> None:
        self.page.fill("#title", title)
        self.page.fill("#chapter_number", str(chapter_number))
        # Quill editor — set hidden textarea via JS
        self.page.evaluate(
            """(text) => {
                const ta = document.getElementById('content');
                if (ta) ta.value = text;
            }""",
            content,
        )
        with self.page.expect_navigation(
            url=re.compile(rf"/mybook/books/\d+"),
            timeout=self.cfg.navigation_timeout_ms,
        ):
            self.page.click('#createChapterForm button[type="submit"]')

    def expect_on_book_view(self, book_id: int) -> None:
        expect(self.page).to_have_url(re.compile(rf"/mybook/books/{book_id}"))
