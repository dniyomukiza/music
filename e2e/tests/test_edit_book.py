"""Author edits book listing (standalone slice)."""
import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.edit
@pytest.mark.author
def test_author_edits_digital_listing(page, e2e_config, test_published_digital_book):
    book = test_published_digital_book
    new_title = f"{book.title}-edited"
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    wf.edit_listing(book.book_id, title=new_title, price="5.99")

    resp = page.request.get(
        f"{e2e_config.base_url.rstrip('/')}/mybook/api/marketplace/books/{book.book_id}"
    )
    assert resp.ok
    data = resp.json()
    book_payload = data.get("book") or data
    assert book_payload.get("title") == new_title
