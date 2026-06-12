"""Pytest + Playwright fixtures, cleanup registry, and fixture files."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import Browser, BrowserContext, Page

# Ensure project root is importable for glconnect + e2e package
E2E_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = E2E_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(E2E_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_ROOT))

from e2e.config import FIXTURES_DIR, get_config, resolve_stripe_secret_key
from e2e.support.app_health import app_is_healthy
from e2e.support.cleanup import delete_users_by_ids
from e2e.support.fixture_factory import (
    BookFixture,
    CampaignFixture,
    seed_audiobook_on_book,
    seed_author_profile,
    seed_completed_purchase,
    seed_in_platform_book,
    seed_live_campaign,
    seed_published_digital_book,
)
from e2e.support.registry_log import append_created_user_ids
from e2e.support.user_factory import TestUser, build_test_user, seed_user_in_db

# Signal the Flask app to skip registration reCAPTCHA during UI sign-up
os.environ.setdefault("E2E_TESTING", "1")


@pytest.fixture(scope="session")
def e2e_config():
    cfg = get_config()
    if not app_is_healthy(cfg.base_url):
        pytest.skip(
            f"Flask app not reachable at {cfg.base_url} (GET /health failed). "
            "Start the server with: FLASK_ENV=development E2E_TESTING=1 python run.py"
        )
    return cfg


@pytest.fixture(scope="session", autouse=True)
def ensure_fixture_assets():
    """Create minimal cover.png and sample ebook if missing."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    cover = FIXTURES_DIR / "cover.png"
    if not cover.is_file():
        try:
            from PIL import Image

            img = Image.new("RGB", (400, 600), color=(30, 60, 90))
            img.save(cover, format="PNG")
        except ImportError:
            # 1x1 PNG fallback without Pillow
            cover.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
                )
            )
    ebook = FIXTURES_DIR / "sample_ebook.txt"
    if not ebook.is_file():
        ebook.write_text(
            "E2E Sample Ebook\n\nThis is a minimal manuscript for automated marketplace listing tests.\n",
            encoding="utf-8",
        )


@pytest.fixture(scope="session")
def worker_id(request):
    return getattr(request.config, "workerinput", {}).get("workerid", "master")


class UserRegistry:
    """Track user_ids created during tests for guaranteed teardown."""

    def __init__(self) -> None:
        self._ids: list[int] = []

    def track(self, user: TestUser) -> TestUser:
        if user.user_id:
            self._ids.append(user.user_id)
        return user

    def track_id(self, user_id: int) -> None:
        self._ids.append(user_id)

    def cleanup(self) -> None:
        if not self._ids:
            return
        ids = list(dict.fromkeys(self._ids))
        if os.getenv("E2E_CLEANUP", "0").strip() in ("1", "true", "yes"):
            delete_users_by_ids(ids)
        else:
            append_created_user_ids(ids)
        self._ids.clear()


@pytest.fixture
def user_registry():
    registry = UserRegistry()
    yield registry
    registry.cleanup()


@pytest.fixture
def test_author(e2e_config, worker_id, user_registry) -> TestUser:
    user = seed_user_in_db(build_test_user(e2e_config, role="author", worker_id=worker_id, label="author"))
    return user_registry.track(user)


@pytest.fixture
def test_buyer(e2e_config, worker_id, user_registry) -> TestUser:
    user = seed_user_in_db(build_test_user(e2e_config, role="other", worker_id=worker_id, label="buyer"))
    return user_registry.track(user)


@pytest.fixture
def test_author_with_profile(test_author, user_registry) -> TestUser:
    return user_registry.track(seed_author_profile(test_author))


@pytest.fixture
def test_in_platform_book(test_author_with_profile, user_registry) -> BookFixture:
    book = seed_in_platform_book(test_author_with_profile, with_chapter=False)
    user_registry.track(test_author_with_profile)
    return book


@pytest.fixture
def test_written_book_for_campaign(test_author_with_profile, user_registry) -> BookFixture:
    book = seed_in_platform_book(test_author_with_profile, with_chapter=True, word_count=1200)
    user_registry.track(test_author_with_profile)
    return book


@pytest.fixture
def test_published_digital_book(test_author_with_profile, worker_id, user_registry) -> BookFixture:
    title = f"e2e-digital-{worker_id}-{uuid.uuid4().hex[:6]}"
    book = seed_published_digital_book(test_author_with_profile, title=title, price=2.99)
    user_registry.track(test_author_with_profile)
    return book


@pytest.fixture
def test_audiobook_ready(test_published_digital_book, user_registry) -> BookFixture:
    seed_audiobook_on_book(test_published_digital_book.book_id)
    user_registry.track(test_published_digital_book.author_user)
    return test_published_digital_book


@pytest.fixture
def test_live_campaign(test_written_book_for_campaign, user_registry) -> CampaignFixture:
    campaign = seed_live_campaign(test_written_book_for_campaign)
    user_registry.track(test_written_book_for_campaign.author_user)
    return campaign


@pytest.fixture
def test_buyer_with_library(test_published_digital_book, test_buyer, user_registry) -> tuple[TestUser, BookFixture]:
    seed_completed_purchase(test_buyer, test_published_digital_book, purchase_format="digital")
    user_registry.track(test_buyer)
    user_registry.track(test_published_digital_book.author_user)
    return test_buyer, test_published_digital_book


@pytest.fixture
def browser_context_args(e2e_config):
    return {
        "base_url": e2e_config.base_url,
        "ignore_https_errors": True,
    }


@pytest.fixture
def page(context: BrowserContext, e2e_config) -> Page:
    pg = context.new_page()
    pg.set_default_timeout(e2e_config.navigation_timeout_ms)
    yield pg
    pg.close()


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_app: test needs running Flask app at E2E_BASE_URL")


def pytest_collection_modifyitems(config, items):
    """Skip @stripe tests before browser/DB fixtures when no sk_test_ key is available."""
    stripe_key = resolve_stripe_secret_key()
    if stripe_key.startswith("sk_test_"):
        return
    reason = (
        "Stripe E2E disabled: set STRIPE_SECRET_FOR_TEST=sk_test_... in .env (production STRIPE_SECRET_KEY is not used). "
        f"Current STRIPE_SECRET_FOR_TEST prefix: {stripe_key[:12] + '...' if stripe_key else 'not set'}"
    )
    skip = pytest.mark.skip(reason=reason)
    for item in items:
        if "stripe" in item.keywords:
            item.add_marker(skip)


def _e2e_headed_requested(pytestconfig) -> bool:
    """True when the browser should be visible (headed / debug)."""
    if pytestconfig.getoption("--headed", default=False):
        return True
    if os.getenv("E2E_HEADED", "").lower() in ("1", "true", "yes"):
        return True
    # pytest-playwright also heads when VS Code/Cursor debugger is attached
    pydevd = sys.modules.get("pydevd")
    if pydevd and hasattr(pydevd, "get_global_debugger"):
        debugger = pydevd.get_global_debugger()
        if debugger and getattr(debugger, "is_attached", lambda: False)():
            return True
    return False


@pytest.fixture(scope="session")
def browser_type_launch_args(pytestconfig):
    launch_options: dict = {"headless": not _e2e_headed_requested(pytestconfig)}
    slowmo = pytestconfig.getoption("--slowmo", default=None)
    if slowmo is None:
        env_slow = os.getenv("E2E_SLOW_MO", "").strip()
        if env_slow.isdigit():
            slowmo = int(env_slow)
    if slowmo:
        launch_options["slow_mo"] = slowmo
    return launch_options
