"""Full written-book journey: register → profile → book → chapter → campaign → publish."""
import pytest
from playwright.sync_api import expect

from e2e.support.user_factory import resolve_user_id
from e2e.workflows.author import AuthorWorkflow


@pytest.mark.journey
@pytest.mark.full_workflow
@pytest.mark.slow
def test_author_written_book_to_publication(page, e2e_config, worker_id, user_registry):
    title = f"e2e-written-journey-{worker_id}"
    wf = AuthorWorkflow(page, e2e_config, worker_id=worker_id)
    user = wf.register_author(label="written-journey")
    uid = resolve_user_id(user.username, email=user.email)
    if uid:
        user.user_id = uid
        user_registry.track_id(uid)

    wf.setup_profile(pen_name=f"Pen {user.username[:12]}", login=False)
    session = wf.create_in_platform_book(title=title)
    assert session.book_id

    content = " ".join(["journey"] * 1200)
    wf.add_chapter(session.book_id, title="Opening", content=content)

    camp_title = f"e2e-journey-camp-{worker_id}"
    wf.launch_campaign(session.book_id, title=camp_title)

    wf.edit_listing(session.book_id, price="6.99")
    assert wf.publish_book_api(session.book_id)

    page.goto(f"{e2e_config.base_url}/mybook/marketplace")
    expect(page.locator("#booksGrid")).to_contain_text(title, timeout=60000)
