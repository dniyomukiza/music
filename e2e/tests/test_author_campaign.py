"""Author launches a patron campaign (standalone slice)."""
import pytest
from playwright.sync_api import expect

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.campaign
@pytest.mark.author
def test_author_launches_campaign_ui(page, e2e_config, test_written_book_for_campaign):
    book = test_written_book_for_campaign
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    camp_title = f"e2e-camp-ui-{book.book_id}"
    wf.launch_campaign(book.book_id, title=camp_title)
    page.goto(f"{e2e_config.base_url}/mybook/investments")
    expect(page.locator("body")).to_contain_text(camp_title, timeout=30000)


@pytest.mark.campaign
@pytest.mark.author
def test_uploaded_book_cannot_create_campaign(page, e2e_config, test_published_digital_book):
    """Negative: digital-upload books redirect away from create-campaign."""
    book = test_published_digital_book
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    page.goto(f"{e2e_config.base_url}/mybook/books/{book.book_id}/create-campaign")
    expect(page).to_have_url(
        f"{e2e_config.base_url.rstrip('/')}/mybook/books/{book.book_id}",
        timeout=15000,
    )
