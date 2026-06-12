"""Author removes or unpublishes listings — book disappears from marketplace."""
import pytest

from e2e.pages.listing_lifecycle import ListingLifecyclePage
from e2e.pages.marketplace import MarketplacePage
from e2e.support.fixture_factory import seed_published_written_book
from e2e.workflows.author import AuthorWorkflow
from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.author
@pytest.mark.edit
def test_author_remove_listing_hides_digital_book(page, e2e_config, test_published_digital_book):
    book = test_published_digital_book
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)

    ListingLifecyclePage(page, e2e_config).remove_listing(book.book_id)

    mp = MarketplacePage(page, e2e_config)
    mp.open()
    mp.search(book.title)
    mp.expect_book_absent(book.title)


@pytest.mark.author
@pytest.mark.edit
def test_author_unpublish_hides_written_book(page, e2e_config, test_written_book_for_campaign, user_registry):
    book = seed_published_written_book(test_written_book_for_campaign)
    user_registry.track(book.author_user)

    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)

    result = ListingLifecyclePage(page, e2e_config).unpublish_written_book(book.book_id)
    assert result.get("success") is True, result

    buyer_wf = BuyerWorkflow(page, page.context, e2e_config)
    buyer_wf.login(
        buyer_wf.seed_buyer(label="lifecycle"),
        next_path="/mybook/marketplace",
    )
    mp = MarketplacePage(page, e2e_config)
    mp.open()
    mp.search(book.title)
    mp.expect_book_absent(book.title)
