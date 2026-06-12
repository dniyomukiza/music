"""
Full cross-role workflow — author lists a book while buyer purchases another listing.

Run in parallel with pytest-xdist:
  pytest e2e/tests/test_full_parallel_workflow.py -n 2 -m full_workflow
"""
import pytest

from e2e.support.user_factory import resolve_user_id
from e2e.workflows.author import AuthorWorkflow
from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.full_workflow
@pytest.mark.slow
def test_author_full_digital_listing_journey(page, e2e_config, worker_id, user_registry):
    """Entire author path: register → profile → upload → marketplace visibility."""
    title = f"e2e-full-author-{worker_id}"
    wf = AuthorWorkflow(page, e2e_config, worker_id=worker_id)
    session = wf.full_digital_listing(use_ui_register=True, book_title=title)
    if session.user.user_id:
        user_registry.track_id(session.user.user_id)

    page.goto(f"{e2e_config.base_url}/mybook/marketplace")
    assert title in page.locator("#booksGrid").inner_text()


@pytest.mark.full_workflow
@pytest.mark.buyer
@pytest.mark.stripe
@pytest.mark.slow
def test_buyer_marketplace_purchase_journey(page, context, e2e_config, worker_id, user_registry):
    """Buyer registers, purchases a book seeded by a parallel author run or local setup."""
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    author_wf = AuthorWorkflow(page, e2e_config, worker_id=worker_id)
    author = author_wf.seed_author(label="parallel-author")
    user_registry.track(author)
    author_wf.login(author)
    author_wf.setup_profile(login=False)
    title = f"e2e-parallel-buy-{worker_id}"
    session = author_wf.list_digital_book(title=title, price="1.99")

    buyer_wf = BuyerWorkflow(page, context, e2e_config, worker_id=worker_id)
    buyer = buyer_wf.register_buyer(label="parallel-buyer")
    buyer_uid = resolve_user_id(buyer.username)
    assert buyer_uid is not None
    user_registry.track_id(buyer_uid)

    buyer_wf.purchase_from_marketplace(session.book_id, book_title=title)
    buyer_wf.assert_in_library(title, book_id=session.book_id)
