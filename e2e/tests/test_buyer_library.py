"""Buyer reads and downloads purchased ebooks (no Stripe)."""
import pytest
from playwright.sync_api import expect

from e2e.pages.library_reader import LibraryReaderPage
from e2e.workflows.buyer import BuyerWorkflow


@pytest.mark.buyer
@pytest.mark.library
def test_buyer_reads_purchased_ebook(page, e2e_config, test_buyer_with_library):
    buyer, book = test_buyer_with_library
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(buyer, next_path="/mybook/library")

    reader = LibraryReaderPage(page, e2e_config)
    reader.open_read(book.book_id)
    reader.expect_reader_content(title_fragment=book.title)
    expect(page.locator("#readerBody")).to_contain_text("E2E Sample Ebook", timeout=15000)


@pytest.mark.buyer
@pytest.mark.library
def test_buyer_downloads_purchased_ebook(page, e2e_config, test_buyer_with_library):
    buyer, book = test_buyer_with_library
    wf = BuyerWorkflow(page, page.context, e2e_config)
    wf.login(buyer, next_path="/mybook/library")

    reader = LibraryReaderPage(page, e2e_config)
    resp = reader.download_digital(book.book_id)
    assert resp.ok, f"download failed: {resp.status} {resp.text()[:200]}"
    assert "attachment" in (resp.headers.get("content-disposition") or "").lower()
