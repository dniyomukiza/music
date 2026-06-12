"""Author creates an in-platform book project (partial workflow)."""
import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.author
def test_author_creates_in_platform_book(page, e2e_config, test_author, user_registry):
    user_registry.track(test_author)
    title = f"e2e-written-{test_author.username[-8:]}"

    wf = AuthorWorkflow(page, e2e_config)
    wf.login(test_author)
    wf.setup_profile(login=False)
    session = wf.create_in_platform_book(title=title)

    assert session.book_id is not None
    page.goto(f"{e2e_config.base_url}/mybook/books")
    assert title in page.content()
