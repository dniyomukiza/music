"""Buyer journey: browse → purchase → library (and optional campaign support)."""
from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page

from e2e.config import E2EConfig
from e2e.pages.auth import LoginPage, RegisterPage
from e2e.pages.investments import InvestmentsPage
from e2e.pages.library import LibraryPage
from e2e.pages.marketplace import MarketplacePage
from e2e.support.user_factory import TestUser, build_test_user, seed_user_in_db


@dataclass
class BuyerSession:
    user: TestUser


class BuyerWorkflow:
    def __init__(self, page: Page, context: BrowserContext, cfg: E2EConfig, worker_id: str = "master") -> None:
        self.page = page
        self.context = context
        self.cfg = cfg
        self.worker_id = worker_id

    def register_buyer(self, label: str = "buyer") -> TestUser:
        user = build_test_user(self.cfg, role="other", worker_id=self.worker_id, label=label)
        RegisterPage(self.page, self.cfg).open(next_path="/mybook/marketplace")
        RegisterPage(self.page, self.cfg).register(user)
        LoginPage(self.page, self.cfg).open(next_path="/mybook/marketplace")
        LoginPage(self.page, self.cfg).login(user)
        return user

    def seed_buyer(self, label: str = "buyer") -> TestUser:
        return seed_user_in_db(build_test_user(self.cfg, role="other", worker_id=self.worker_id, label=label))

    def login(self, user: TestUser, next_path: str = "/mybook/marketplace") -> None:
        LoginPage(self.page, self.cfg).open(next_path=next_path)
        LoginPage(self.page, self.cfg).login(user)

    def purchase_from_marketplace(
        self,
        book_id: int,
        *,
        book_title: str | None = None,
        purchase_type: str = "digital",
    ) -> None:
        mp = MarketplacePage(self.page, self.cfg)
        mp.open()
        if book_title:
            mp.search(book_title)
            mp.expect_book_visible(book_title)
        mp.purchase_book(book_id, purchase_type=purchase_type)

    def purchase_ebook(self, book_id: int, *, book_title: str | None = None) -> None:
        self.purchase_from_marketplace(book_id, book_title=book_title, purchase_type="digital")

    def purchase_audiobook(self, book_id: int, *, book_title: str | None = None) -> None:
        self.purchase_from_marketplace(book_id, book_title=book_title, purchase_type="audiobook")

    def purchase_bundle(self, book_id: int, *, book_title: str | None = None) -> None:
        self.purchase_from_marketplace(book_id, book_title=book_title, purchase_type="bundle")

    def assert_in_library(self, book_title: str, book_id: int | None = None) -> None:
        LibraryPage(self.page, self.cfg).open(book_id=book_id)
        LibraryPage(self.page, self.cfg).expect_book_in_library(book_title)

    def update_account(self, *, first_name: str, last_name: str, email: str) -> None:
        from e2e.pages.reader_account import ReaderAccountPage

        ReaderAccountPage(self.page, self.cfg).open()
        ReaderAccountPage(self.page, self.cfg).update_profile(
            first_name=first_name, last_name=last_name, email=email
        )

    def fund_campaign(self, campaign_id: int, amount: str = "10.00") -> None:
        InvestmentsPage(self.page, self.cfg).invest(campaign_id, amount, context=self.context)

    def sponsor_campaign(self, campaign_id: int, amount: str = "10.00") -> None:
        self.fund_campaign(campaign_id, amount)
