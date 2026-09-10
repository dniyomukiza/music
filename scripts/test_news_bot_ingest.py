#!/usr/bin/env python3
"""Unit tests for bot news ingest (no TTS or Gemini calls)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from types import SimpleNamespace
from unittest.mock import patch

from glconnect.news_agent import (
    NewsPipelineTrace,
    parse_bot_news_reports,
    _segments_from_bot_reports,
)
from glconnect.news_routes import _bot_ingest_authorized


def test_parse_maps_aliases_and_desks():
    reports, error = parse_bot_news_reports({
        "source": "grok-bot",
        "reporters": [
            {"topic": "NBA finals", "category": "sports", "script": "The Lakers closed out the series."},
            {"title": "Rate cut", "desk": "economy", "copy": "The Fed held rates steady."},
            {"topic": "Chip export rules", "category": "technology", "text": "New limits hit foundries."},
        ],
    })
    assert error is None
    assert [row["category"] for row in reports] == ["sports", "finance", "tech"]
    assert reports[1]["topic"] == "Rate cut"


def test_parse_rejects_missing_script_and_placeholder():
    reports, error = parse_bot_news_reports({
        "reporters": [{"topic": "Markets", "category": "finance", "script": ""}],
    })
    assert reports == []
    assert "missing script" in error

    reports, error = parse_bot_news_reports({
        "reporters": [{
            "topic": "Markets",
            "category": "finance",
            "script": "We are checking official statements and independent reporting.",
        }],
    })
    assert reports == []
    assert "placeholder" in error


def test_bot_segments_skip_gemini_and_assign_roster():
    reports, error = parse_bot_news_reports({
        "reporters": [
            {"topic": "Openers", "category": "sports", "script": "Ernest here with the late score."},
            {"topic": "Bonds", "category": "finance", "script": "Yields eased after the open."},
        ],
    })
    assert error is None
    trace = NewsPipelineTrace([row["topic"] for row in reports])
    _, scripts, segments, assignments = _segments_from_bot_reports(reports, trace=trace)
    assert [row["name"] for row in assignments] == ["Ernest", "Isabella"]
    assert [row["desk"] for row in assignments] == ["sports", "finance"]
    assert scripts[0].startswith("Ernest here")
    assert segments[0][3] == "Ernest"
    assign_stage = next(row for row in trace.stages if row["stage"] == "scripts_assign")
    assert assign_stage["skipped"] == ["topic_intake", "categorize", "scripts_generate"]
    assert assign_stage["source"] == "grok-bot"


def test_bot_ingest_token():
    with patch.dict("os.environ", {"NEWS_BOT_INGEST_TOKEN": "secret-token"}, clear=False):
        assert _bot_ingest_authorized(SimpleNamespace(headers={"Authorization": "Bearer secret-token"}))
        assert _bot_ingest_authorized(SimpleNamespace(headers={"X-News-Bot-Token": "secret-token"}))
        assert not _bot_ingest_authorized(SimpleNamespace(headers={"Authorization": "Bearer wrong"}))
        assert not _bot_ingest_authorized(SimpleNamespace(headers={}))


if __name__ == "__main__":
    test_parse_maps_aliases_and_desks()
    test_parse_rejects_missing_script_and_placeholder()
    test_bot_segments_skip_gemini_and_assign_roster()
    test_bot_ingest_token()
    print("ok")
