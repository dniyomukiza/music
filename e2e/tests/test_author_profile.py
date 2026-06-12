"""Author profile setup (partial workflow)."""
import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.author
def test_author_completes_setup_profile(page, e2e_config, test_author):
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(test_author)
    wf.setup_profile(pen_name="E2E Pen Name", login=False)
    assert "/mybook/books" in page.url or "/mybook/" in page.url
