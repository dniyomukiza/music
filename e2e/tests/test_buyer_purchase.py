"""Buyer purchases listed books — ebook, audiobook, bundle (standalone slices)."""
import pytest

from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.buyer
@pytest.mark.stripe
def test_buyer_purchases_ebook(page, context, e2e_config, test_published_digital_book, test_buyer):
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    book = test_published_digital_book
    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer)
    wf.purchase_ebook(book.book_id, book_title=book.title)
    wf.assert_in_library(book.title, book_id=book.book_id)


@pytest.mark.buyer
@pytest.mark.stripe
def test_buyer_purchases_audiobook(page, context, e2e_config, test_audiobook_ready, test_buyer):
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    book = test_audiobook_ready
    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer)
    wf.purchase_audiobook(book.book_id, book_title=book.title)
    wf.assert_in_library(book.title, book_id=book.book_id)


@pytest.mark.buyer
@pytest.mark.stripe
def test_buyer_purchases_bundle(page, context, e2e_config, test_audiobook_ready, test_buyer):
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    book = test_audiobook_ready
    wf = BuyerWorkflow(page, context, e2e_config)
    wf.login(test_buyer)
    wf.purchase_bundle(book.book_id, book_title=book.title)
    wf.assert_in_library(book.title, book_id=book.book_id)


@pytest.mark.buyer
@pytest.mark.stripe
def test_buyer_purchases_listed_book(page, context, e2e_config, test_author, test_buyer, user_registry):
    """Legacy path: author lists via UI then buyer purchases (integration smoke)."""
    if not e2e_config.stripe_enabled:
        pytest.skip("STRIPE_SECRET_FOR_TEST (sk_test_*) not configured")

    from e2e.workflows.author import AuthorWorkflow

    user_registry.track(test_author)
    user_registry.track(test_buyer)
    title = f"e2e-buy-{test_author.username[-8:]}"

    author_wf = AuthorWorkflow(page, e2e_config)
    author_wf.login(test_author)
    author_wf.setup_profile(login=False)
    session = author_wf.list_digital_book(title=title, price="2.99")
    assert session.book_id

    buyer_wf = BuyerWorkflow(page, context, e2e_config)
    buyer_wf.login(test_buyer)
    buyer_wf.purchase_from_marketplace(session.book_id, book_title=title)
    buyer_wf.assert_in_library(title, book_id=session.book_id)
