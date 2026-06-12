"""Author profile / account management (standalone slice)."""
import pytest
from playwright.sync_api import expect

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.account
@pytest.mark.author
def test_author_updates_setup_profile(page, e2e_config, test_author_with_profile):
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(test_author_with_profile)
    pen = "E2E Pen Updated"
    wf.setup_profile(pen_name=pen, login=False)
    page.goto(f"{e2e_config.base_url}/mybook/setup-profile")
    expect(page.locator("#penName")).to_have_value(pen, timeout=15000)
