"""Audiobook generation slice (slow; needs TTS credentials for full generation)."""
import os

import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.audiobook
@pytest.mark.slow
def test_audiobook_status_api_reachable(page, e2e_config, test_written_book_for_campaign):
    book = test_written_book_for_campaign
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    base = e2e_config.base_url.rstrip("/")
    resp = page.request.get(f"{base}/mybook/books/{book.book_id}/audio-generation-status")
    assert resp.status in (200, 404)


@pytest.mark.audiobook
@pytest.mark.slow
def test_audiobook_player_with_seeded_audio(page, e2e_config, test_audiobook_ready):
    book = test_audiobook_ready
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    from e2e.pages.audiobook import AudiobookPage

    AudiobookPage(page, e2e_config).open_player(book.book_id)
    AudiobookPage(page, e2e_config).expect_player_loaded()


@pytest.mark.audiobook
@pytest.mark.slow
def test_audiobook_generation_flow(page, e2e_config, test_written_book_for_campaign):
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.path.exists("tts.json"):
        pytest.skip("TTS credentials not configured (GOOGLE_APPLICATION_CREDENTIALS / tts.json)")

    book = test_written_book_for_campaign
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    result = wf.generate_audiobook(book.book_id)
    status = (result.get("status") or result.get("generation_status") or "").lower()
    assert status in ("completed", "complete", "done", "processing", "in_progress", "pending", "")
