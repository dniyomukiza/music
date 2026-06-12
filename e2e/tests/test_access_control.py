"""Role-based navigation: readers see GLC, authors see Ink Studio; blocked author routes."""
import pytest
from playwright.sync_api import expect

from e2e.pages.library import LibraryPage
from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.buyer
@pytest.mark.access
def test_buyer_sees_glc_branding_not_ink_studio(page, e2e_config, test_buyer):
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer, next_path="/mybook/library")

    LibraryPage(page, e2e_config).open()
    expect(page.locator(".ink-lib-brand")).to_contain_text("GLC")
    expect(page.locator(".ink-lib-brand")).not_to_contain_text("Ink Studio")


@pytest.mark.author
@pytest.mark.access
def test_author_sees_ink_studio_branding(page, e2e_config, test_author_with_profile):
    from e2e.pages.auth import LoginPage

    LoginPage(page, e2e_config).open(next_path="/mybook/library")
    LoginPage(page, e2e_config).login(test_author_with_profile)

    LibraryPage(page, e2e_config).open()
    expect(page.locator(".ink-lib-brand")).to_contain_text("Ink Studio")


@pytest.mark.buyer
@pytest.mark.access
def test_buyer_blocked_from_author_create_book(page, e2e_config, test_buyer):
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(test_buyer, next_path="/mybook/books/create")

    page.wait_for_load_state("networkidle")
    assert "/mybook/setup-profile" in page.url or "/routes1/login" in page.url
    expect(page.locator("body")).not_to_contain_text("Create a new book", timeout=5000)
