"""AI writing assistant slice (requires GEMINI_API_KEY)."""
import os

import pytest

from e2e.workflows.author import AuthorWorkflow


@pytest.mark.ai
def test_ai_assistant_api_generates_content(page, e2e_config, test_written_book_for_campaign):
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        pytest.skip("GEMINI_API_KEY or GOOGLE_API_KEY not configured")

    book = test_written_book_for_campaign
    assert book.chapter_id, "Fixture must include a chapter for AI editor tests"
    wf = AuthorWorkflow(page, e2e_config)
    wf.login(book.author_user)
    snippet = wf.use_ai_assistant(book.book_id, book.chapter_id)
    assert len(snippet) > 10
