#!/usr/bin/env python3
"""Tests for rich project description media rules."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from glconnect.project_description_media import (  # noqa: E402
    MEDIA_GUIDE,
    build_video_iframe_html,
    normalize_video_embed_url,
    project_description_plain_length,
    sanitize_project_description,
)


def test_youtube_embed_normalization():
    assert normalize_video_embed_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == (
        "https://www.youtube.com/embed/dQw4w9WgXcQ"
    )
    assert normalize_video_embed_url("https://youtu.be/dQw4w9WgXcQ") == (
        "https://www.youtube.com/embed/dQw4w9WgXcQ"
    )


def test_vimeo_embed_normalization():
    assert normalize_video_embed_url("https://vimeo.com/123456789") == (
        "https://player.vimeo.com/video/123456789"
    )


def test_sanitize_keeps_allowed_media_for_book():
    book_id = 42
    src = f"/static/project_media/{book_id}_abc123.jpg"
    html = (
        f'<p>Hello</p><figure class="ink-project-media ink-project-media--image">'
        f'<img src="{src}" alt="Cover sketch"></figure>'
        f'<p><a href="https://example.com">Learn more</a></p>'
    )
    cleaned = sanitize_project_description(html, book_id=book_id)
    assert src in cleaned
    assert 'target="_blank"' in cleaned
    assert 'rel="noopener noreferrer"' in cleaned
    assert project_description_plain_length(cleaned) >= 5


def test_sanitize_strips_foreign_image_src():
    book_id = 7
    html = '<img src="/static/project_media/999_evil.jpg" alt="bad">'
    cleaned = sanitize_project_description(html, book_id=book_id)
    assert "999_evil" not in cleaned


def test_sanitize_embeds_youtube_iframe():
    book_id = 1
    raw = '<iframe src="https://www.youtube.com/watch?v=dQw4w9WgXcQ"></iframe>'
    cleaned = sanitize_project_description(raw, book_id=book_id)
    assert "youtube.com/embed/dQw4w9WgXcQ" in cleaned
    assert "ink-project-embed" in cleaned


def test_media_guide_has_expected_keys():
    assert set(MEDIA_GUIDE.keys()) >= {"images", "audio", "video_files", "video_embeds", "links"}


def test_build_video_iframe_html():
    html = build_video_iframe_html("https://www.youtube.com/embed/test")
    assert "iframe" in html
    assert "ink-project-embed" in html


def main():
    test_youtube_embed_normalization()
    test_vimeo_embed_normalization()
    test_sanitize_keeps_allowed_media_for_book()
    test_sanitize_strips_foreign_image_src()
    test_sanitize_embeds_youtube_iframe()
    test_media_guide_has_expected_keys()
    test_build_video_iframe_html()
    print("All project description media tests passed.")


if __name__ == "__main__":
    main()
