"""Marketplace browse and purchase."""
from __future__ import annotations

from playwright.sync_api import Page, expect

from e2e.config import E2EConfig
from e2e.pages.base import BasePage
from e2e.support.stripe_checkout import complete_stripe_checkout


class MarketplacePage(BasePage):
    PATH = "/mybook/marketplace"

    def open(self) -> None:
        self.goto(self.PATH)
        self.page.wait_for_selector("#booksGrid", timeout=self.cfg.navigation_timeout_ms)

    def search(self, query: str) -> None:
        self.page.fill("#searchInput", query)
        self.page.press("#searchInput", "Enter")
        # Client-side filter — networkidle can hang on long-polling / analytics.
        self.page.wait_for_timeout(800)

    def filter_by_genre(self, genre_value: str) -> None:
        self.page.select_option("#genre", value=genre_value)
        self.page.wait_for_load_state("domcontentloaded")

    def expect_book_absent(self, title: str) -> None:
        expect(self.page.locator("#booksGrid")).not_to_contain_text(title, timeout=30000)

    def open_book_modal(self, book_id: int) -> None:
        self.page.evaluate(f"viewBook({book_id})")
        self.page.wait_for_selector("#bookDetailsModal.show", timeout=15000)
        self.page.wait_for_selector("#bookDetailsActions button", timeout=15000)

    def start_purchase_from_modal(self) -> None:
        """Book details modal → payment modal."""
        buy_btn = self.page.locator("#bookDetailsActions button:has-text('Buy')")
        buy_btn.first.click()
        self.page.wait_for_selector("#customPaymentModal.show", timeout=15000)

    def select_purchase_type(self, purchase_type: str = "digital") -> None:
        """digital | audiobook | bundle"""
        mapping = {
            "digital": "#purchaseTypeDigital",
            "audiobook": "#purchaseTypeAudiobook",
            "bundle": "#purchaseTypeBundle",
        }
        selector = mapping.get(purchase_type, "#purchaseTypeDigital")
        radio = self.page.locator(selector)
        if radio.is_visible():
            radio.check()

    def purchase_book(
        self,
        book_id: int,
        *,
        purchase_type: str = "digital",
        complete_stripe: bool = True,
    ) -> None:
        self.open_book_modal(book_id)
        self.start_purchase_from_modal()
        self.select_purchase_type(purchase_type)
        self.page.click("#confirmPurchaseBtn")

        if not complete_stripe:
            return

        try:
            self.page.wait_for_url(
                lambda url: "checkout.stripe.com" in url,
                timeout=45_000,
            )
        except Exception as exc:
            hint = ""
            for sel in ("#customPaymentModal .alert-danger", "#customPaymentModal .text-danger", ".toast-body"):
                loc = self.page.locator(sel)
                if loc.count():
                    hint = loc.first.inner_text(timeout=2000)
                    break
            raise AssertionError(
                f"Never reached Stripe Checkout (stuck at {self.page.url}). "
                f"Server may be using sk_live_; set STRIPE_SECRET_FOR_TEST in .env and restart with E2E_TESTING=1 "
                f"and FRONTEND_BASE_URL=http://localhost:5000, then restart Flask. "
                f"{f'UI error: {hint}' if hint else ''}"
            ) from exc
        # #region agent log
        import json
        import time as _time
        from e2e.config import resolve_stripe_secret_key
        _sk = resolve_stripe_secret_key()
        try:
            with open("/Applications/untitled folder/music-1/.cursor/debug-f3d0e1.log", "a", encoding="utf-8") as _f:
                _f.write(
                    json.dumps(
                        {
                            "sessionId": "f3d0e1",
                            "hypothesisId": "A",
                            "location": "marketplace.py:purchase_book",
                            "message": "reached stripe checkout redirect",
                            "data": {
                                "checkout_url": self.page.url,
                                "stripe_for_test_prefix": (_sk[:12] + "...") if _sk else "not set",
                                "is_test_key": _sk.startswith("sk_test_"),
                            },
                            "timestamp": int(_time.time() * 1000),
                        }
                    )
                    + "\n"
                )
        except Exception:
            pass
        # #endregion
        complete_stripe_checkout(self.page, timeout_ms=120_000)
        try:
            self.page.wait_for_url(
                lambda url: "/mybook/purchase/success" in url or "/mybook/library" in url,
                timeout=120_000,
            )
        except Exception as exc:
            raise AssertionError(
                f"Stripe Checkout did not return to the app (stuck at {self.page.url}). "
                "Set FRONTEND_BASE_URL=http://localhost:5000 in .env and restart Flask."
            ) from exc
        self.page.wait_for_load_state("domcontentloaded")

    def expect_book_visible(self, title: str) -> None:
        expect(self.page.locator("#booksGrid")).to_contain_text(title, timeout=30000)
