"""Marketplace search and filters surface seeded listings."""
import pytest

from e2e.pages.marketplace import MarketplacePage
from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.buyer
@pytest.mark.discovery
def test_marketplace_search_finds_seeded_book(page, e2e_config, test_published_digital_book, test_buyer):
    book = test_published_digital_book
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer)

    mp = MarketplacePage(page, e2e_config)
    mp.open()
    mp.search(book.title)
    mp.expect_book_visible(book.title)


@pytest.mark.buyer
@pytest.mark.discovery
def test_marketplace_genre_filter_shows_seeded_book(page, e2e_config, test_published_digital_book, test_buyer):
    """Seeded digital books use genre 'Fiction' — filter via server-side search + genre URL."""
    book = test_published_digital_book
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer)

    mp = MarketplacePage(page, e2e_config)
    mp.goto(f"/mybook/marketplace?genre=Fiction&search={book.title}")
    mp.page.wait_for_selector("#booksGrid", timeout=mp.cfg.navigation_timeout_ms)
    mp.expect_book_visible(book.title)


@pytest.mark.buyer
@pytest.mark.discovery
def test_marketplace_sort_keeps_book_visible(page, e2e_config, test_published_digital_book, test_buyer):
    book = test_published_digital_book
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer)

    mp = MarketplacePage(page, e2e_config)
    mp.goto(f"/mybook/marketplace?sort_by=price_low&search={book.title}")
    mp.page.wait_for_selector("#booksGrid", timeout=mp.cfg.navigation_timeout_ms)
    mp.expect_book_visible(book.title)
