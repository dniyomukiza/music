"""Digital book upload and marketplace listing."""
from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import Page, expect

from e2e.config import E2EConfig, FIXTURES_DIR
from e2e.pages.base import BasePage


class UploadDigitalBookPage(BasePage):
    PATH = "/mybook/upload-digital-book"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#digitalBookForm", timeout=self.cfg.navigation_timeout_ms)

    def accept_listing_terms(self) -> None:
        self.page.click("#showListingTermsBtnUpload")
        scroll = self.page.locator("#listingTermsScrollUpload")
        scroll.wait_for(state="visible")
        # Scroll terms panel to bottom to enable checkboxes
        self.page.evaluate(
            """() => {
                const el = document.getElementById('listingTermsScrollUpload');
                if (el) el.scrollTop = el.scrollHeight;
            }"""
        )
        for cb_id in (
            "listing_terms_rights_warranty",
            "listing_terms_takedown_consent",
            "listing_ai_rights_confirm",
        ):
            cb = self.page.locator(f"#{cb_id}")
            cb.wait_for(state="attached")
            self.page.evaluate(
                f"""() => {{
                    const cb = document.getElementById('{cb_id}');
                    if (cb) {{ cb.disabled = false; cb.checked = true; }}
                }}"""
            )

    def list_book(
        self,
        *,
        title: str,
        price: str = "4.99",
        genre: str = "Fiction",
        description: str = "E2E test listing.",
        ebook_path: Path | None = None,
        cover_path: Path | None = None,
    ) -> None:
        ebook = ebook_path or (FIXTURES_DIR / "sample_ebook.txt")
        cover = cover_path or (FIXTURES_DIR / "cover.png")

        self.page.fill("#title", title)
        self.page.fill("#genre", genre)
        self.page.fill("#description", description)
        self.page.select_option("#ebook_language", label="English")
        self.page.set_input_files("#digital_book_file_input", str(ebook))
        self.page.set_input_files("#cover_image", str(cover))
        self.page.fill("#digital_price", price)
        self.accept_listing_terms()
        self.page.click("#submitBtn")

        overlay = self.page.locator("#uploadProcessingOverlay")
        if overlay.is_visible():
            expect(overlay).to_be_hidden(timeout=self.cfg.upload_timeout_ms)

        expect(self.page).to_have_url(
            re.compile(r"/mybook/books/\d+/edit"),
            timeout=self.cfg.upload_timeout_ms,
        )
