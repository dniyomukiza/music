"""Remove or unpublish marketplace listings."""
from __future__ import annotations

from e2e.pages.base import BasePage


class ListingLifecyclePage(BasePage):
    def remove_listing(self, book_id: int) -> dict:
        base = self.cfg.base_url.rstrip("/")
        resp = self.page.request.post(f"{base}/mybook/books/{book_id}/remove-listing")
        assert resp.ok, f"remove-listing failed: {resp.status} {resp.text()}"
        return resp.json()

    def unpublish_written_book(self, book_id: int) -> dict:
        base = self.cfg.base_url.rstrip("/")
        resp = self.page.request.post(f"{base}/mybook/books/{book_id}/unpublish")
        return resp.json()
