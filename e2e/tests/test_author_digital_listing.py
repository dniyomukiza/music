"""Author lists a digital book on the marketplace (partial workflow)."""
import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.author
@pytest.mark.slow
def test_author_uploads_digital_book_to_marketplace(page, e2e_config, test_author, user_registry):
    user_registry.track(test_author)
    title = f"e2e-digital-{test_author.username[-8:]}"

    wf = AuthorWorkflow(page, e2e_config)
    wf.login(test_author)
    wf.setup_profile(pen_name="E2E Digital Author", login=False)
    session = wf.list_digital_book(title=title, price="3.99")

    assert session.book_id is not None
    page.goto(f"{e2e_config.base_url}/mybook/marketplace")
    page.wait_for_selector("#booksGrid")
    assert title in page.locator("#booksGrid").inner_text()
