"""Author journey: account → profile → list or create book."""
from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import BrowserContext, Page

from e2e.config import E2EConfig
from e2e.pages.ai_assistant import AIAssistantPage
from e2e.pages.audiobook import AudiobookPage
from e2e.pages.auth import LoginPage, RegisterPage
from e2e.pages.create_book import CreateBookPage
from e2e.pages.create_campaign import CreateCampaignPage
from e2e.pages.create_chapter import CreateChapterPage
from e2e.pages.edit_book import EditBookPage
from e2e.pages.earnings import EarningsPage
from e2e.pages.payout_setup import PayoutSetupPage
from e2e.pages.setup_profile import SetupProfilePage
from e2e.pages.upload_digital_book import UploadDigitalBookPage
from e2e.support.user_factory import TestUser, build_test_user, resolve_user_id, seed_user_in_db


@dataclass
class AuthorSession:
    user: TestUser
    book_id: int | None = None
    book_title: str | None = None


class AuthorWorkflow:
    def __init__(self, page: Page, cfg: E2EConfig, worker_id: str = "master") -> None:
        self.page = page
        self.cfg = cfg
        self.worker_id = worker_id

    def register_author(self, label: str = "author") -> TestUser:
        user = build_test_user(self.cfg, role="author", worker_id=self.worker_id, label=label)
        RegisterPage(self.page, self.cfg).open()
        RegisterPage(self.page, self.cfg).register(user)
        LoginPage(self.page, self.cfg).open()
        LoginPage(self.page, self.cfg).login(user)
        return user

    def seed_author(self, label: str = "author") -> TestUser:
        user = build_test_user(self.cfg, role="author", worker_id=self.worker_id, label=label)
        return seed_user_in_db(user)

    def login(self, user: TestUser) -> None:
        LoginPage(self.page, self.cfg).open()
        LoginPage(self.page, self.cfg).login(user)

    def setup_profile(
        self,
        user: TestUser | None = None,
        pen_name: str | None = None,
        *,
        login: bool = True,
    ) -> None:
        """Complete author profile. Pass login=False when the session is already authenticated."""
        if user and login:
            self.login(user)
        SetupProfilePage(self.page, self.cfg).open()
        SetupProfilePage(self.page, self.cfg).complete_minimal(pen_name=pen_name or "E2E Author")

    def list_digital_book(self, title: str, price: str = "4.99") -> AuthorSession:
        UploadDigitalBookPage(self.page, self.cfg).open()
        UploadDigitalBookPage(self.page, self.cfg).list_book(title=title, price=price)
        import re

        m = re.search(r"/mybook/books/(\d+)", self.page.url)
        book_id = int(m.group(1)) if m else None
        return AuthorSession(user=build_test_user(self.cfg), book_id=book_id, book_title=title)

    def create_in_platform_book(self, title: str) -> AuthorSession:
        CreateBookPage(self.page, self.cfg).open()
        book_id = CreateBookPage(self.page, self.cfg).create_with_cover(title=title)
        return AuthorSession(user=build_test_user(self.cfg), book_id=book_id, book_title=title)

    def full_digital_listing(
        self,
        *,
        use_ui_register: bool = True,
        label: str = "author",
        book_title: str,
    ) -> AuthorSession:
        if use_ui_register:
            user = self.register_author(label=label)
            uid = resolve_user_id(user.username, email=user.email)
            if uid:
                user.user_id = uid
        else:
            user = self.seed_author(label=label)
            self.login(user)
        self.setup_profile(pen_name=f"Pen {user.username[:12]}")
        session = self.list_digital_book(title=book_title)
        session.user = user
        return session

    def add_chapter(self, book_id: int, *, title: str, content: str) -> None:
        CreateChapterPage(self.page, self.cfg).open(book_id)
        CreateChapterPage(self.page, self.cfg).create_chapter(title=title, content=content)

    def launch_campaign(
        self,
        book_id: int,
        *,
        title: str,
        description: str | None = None,
    ) -> None:
        desc = description or (
            "E2E patron campaign description with enough characters to satisfy form validation "
            "and appear on the investments discovery page for backers."
        )
        CreateCampaignPage(self.page, self.cfg).open(book_id)
        CreateCampaignPage(self.page, self.cfg).launch_campaign(title=title, description=desc)

    def edit_listing(self, book_id: int, *, title: str | None = None, price: str | None = None) -> None:
        EditBookPage(self.page, self.cfg).open(book_id)
        if title:
            EditBookPage(self.page, self.cfg).update_title(title)
        if price:
            EditBookPage(self.page, self.cfg).update_price(price)
        EditBookPage(self.page, self.cfg).save()

    def publish_book_api(self, book_id: int) -> bool:
        base = self.cfg.base_url.rstrip("/")
        resp = self.page.request.post(
            f"{base}/mybook/books/{book_id}/publish",
            data={
                "listing_terms_rights_warranty": "on",
                "listing_terms_takedown_consent": "on",
            },
        )
        return resp.ok

    def start_connect_onboarding(self, context: BrowserContext) -> None:
        PayoutSetupPage(self.page, self.cfg).open()
        PayoutSetupPage(self.page, self.cfg).start_connect_onboarding(context)

    def open_earnings(self) -> None:
        EarningsPage(self.page, self.cfg).open()
        EarningsPage(self.page, self.cfg).expect_loaded()

    def generate_audiobook(self, book_id: int) -> dict:
        AudiobookPage(self.page, self.cfg).open_edit(book_id)
        AudiobookPage(self.page, self.cfg).trigger_generation(book_id)
        return AudiobookPage(self.page, self.cfg).poll_until_complete(book_id)

    def use_ai_assistant(self, book_id: int, chapter_id: int) -> str:
        AIAssistantPage(self.page, self.cfg).assert_api_enabled()
        AIAssistantPage(self.page, self.cfg).open_chapter_editor(book_id, chapter_id)
        AIAssistantPage(self.page, self.cfg).expect_toolbar_present()
        return AIAssistantPage(self.page, self.cfg).generate_content_snippet()
