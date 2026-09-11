#!/usr/bin/env python3
"""Unit tests for Parallel research packets (no live API calls)."""

import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
package = types.ModuleType("glconnect")
package.__path__ = [str(ROOT / "glconnect")]
sys.modules.setdefault("glconnect", package)

from glconnect.parallel_news_search import (
    format_research_block,
    search_topic,
    search_topics_for_news,
)


def test_empty_without_key():
    with patch.dict(os.environ, {"PARALLEL_API_KEY": ""}, clear=False):
        os.environ.pop("PARALLEL_API_KEY", None)
        os.environ.pop("PARALLEL_KEY", None)
        packet = search_topic("markets")
        assert packet["source"] == "unconfigured"
        assert packet["items"] == []
        assert format_research_block(packet) == ""


def test_format_packet():
    text = format_research_block({
        "topic": "markets",
        "source": "parallel",
        "items": [{
            "title": "Markets rise",
            "url": "https://example.com/a",
            "excerpts": ["Stocks gained 1%."],
        }],
    })
    assert "Markets rise" in text
    assert "https://example.com/a" in text
    assert "Stocks gained 1%." in text


def test_search_failure_is_empty():
    with patch.dict(os.environ, {"PARALLEL_API_KEY": "test-key"}):
        with patch("glconnect.parallel_news_search.requests.post", side_effect=RuntimeError("network")):
            packet = search_topic("sports")
    assert packet["source"] == "error"
    assert packet["items"] == []


def test_topics_helper_skips_when_unconfigured():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("PARALLEL_API_KEY", None)
        os.environ.pop("PARALLEL_KEY", None)
        packets = search_topics_for_news(["alpha", "beta"])
    assert packets["alpha"]["source"] == "unconfigured"
    assert packets["beta"]["items"] == []


def main():
    test_empty_without_key()
    test_format_packet()
    test_search_failure_is_empty()
    test_topics_helper_skips_when_unconfigured()
    print("OK: parallel_news_search tests passed")


if __name__ == "__main__":
    main()
