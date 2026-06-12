"""Full upload journey — thin wrapper around existing full_digital_listing."""
import pytest
from playwright.sync_api import expect

from e2e.support.user_factory import resolve_user_id
from e2e.workflows.author import AuthorWorkflow


@pytest.mark.journey
@pytest.mark.full_workflow
@pytest.mark.slow
def test_author_upload_to_marketplace_journey(page, e2e_config, worker_id, user_registry):
    title = f"e2e-upload-journey-{worker_id}"
    wf = AuthorWorkflow(page, e2e_config, worker_id=worker_id)
    session = wf.full_digital_listing(use_ui_register=True, book_title=title, label="upload-journey")
    if session.user.user_id:
        user_registry.track_id(session.user.user_id)
    elif session.user.username:
        uid = resolve_user_id(session.user.username, email=session.user.email)
        if uid:
            user_registry.track_id(uid)

    page.goto(f"{e2e_config.base_url}/mybook/marketplace")
    expect(page.locator("#booksGrid")).to_contain_text(title, timeout=60000)
