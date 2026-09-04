"""Parallel Search API for GRO News research packets.

Audio still uses Google TTS. Gemini still writes scripts. This module only
fetches live web excerpts. If the key is missing or a call fails, callers
get an empty packet and the existing Gemini path continues unchanged.
"""

from __future__ import annotations

import os
from typing import Any

import requests

PARALLEL_SEARCH_URL = "https://api.parallel.ai/v1/search"
_DEFAULT_TIMEOUT = (8, 20)
_MAX_RESULTS = 5
_MAX_EXCERPTS = 2
_MAX_EXCERPT_CHARS = 420


def parallel_api_key() -> str:
    return (os.getenv("PARALLEL_API_KEY") or os.getenv("PARALLEL_KEY") or "").strip()


def _search_mode() -> str:
    mode = (os.getenv("PARALLEL_SEARCH_MODE") or "turbo").strip().lower()
    return mode if mode in {"turbo", "advanced"} else "turbo"


def _clip(text: Any, limit: int) -> str:
    value = " ".join(str(text or "").split())
    if len(value) > limit:
        return value[:limit].rstrip() + "..."
    return value


def _empty_packet(topic: str, reason: str = "none") -> dict:
    return {"topic": topic, "source": reason, "items": []}


def format_research_block(packet: dict | None) -> str:
    """Plain text Gemini can treat as the only allowed facts."""
    if not packet or not packet.get("items"):
        return ""
    lines = [f'RESEARCH PACKET for {packet.get("topic")!r}:']
    for item in packet["items"]:
        title = item.get("title") or "Untitled"
        url = item.get("url") or ""
        lines.append(f"- {title} ({url})")
        for excerpt in item.get("excerpts") or []:
            lines.append(f"  {excerpt}")
    return "\n".join(lines)


def _parse_results(payload: dict, topic: str) -> dict:
    items = []
    for row in (payload or {}).get("results") or []:
        if not isinstance(row, dict):
            continue
        excerpts = []
        for excerpt in row.get("excerpts") or []:
            clipped = _clip(excerpt, _MAX_EXCERPT_CHARS)
            if clipped:
                excerpts.append(clipped)
            if len(excerpts) >= _MAX_EXCERPTS:
                break
        url = str(row.get("url") or "").strip()
        title = str(row.get("title") or "").strip()
        if not (url or excerpts):
            continue
        items.append({"title": title, "url": url, "excerpts": excerpts})
        if len(items) >= _MAX_RESULTS:
            break
    source = "parallel" if items else "empty"
    return {"topic": topic, "source": source, "items": items}


def search_topic(topic: str) -> dict:
    """One Parallel Search call. Never raises to the bulletin pipeline."""
    topic = (topic or "").strip()
    if not topic:
        return _empty_packet(topic, "none")
    api_key = parallel_api_key()
    if not api_key:
        return _empty_packet(topic, "unconfigured")
    try:
        response = requests.post(
            PARALLEL_SEARCH_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
            },
            json={
                "objective": (
                    f"Find the latest verified news about {topic} "
                    "for a short radio bulletin. Prefer recent, concrete developments."
                ),
                "search_queries": [f"latest {topic} news"],
                "mode": _search_mode(),
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        if response.status_code >= 400:
            print(
                f"DEBUG: Parallel search HTTP {response.status_code} for topic={topic!r}"
            )
            return _empty_packet(topic, "http_error")
        payload = response.json()
        if not isinstance(payload, dict):
            return _empty_packet(topic, "invalid_payload")
        return _parse_results(payload, topic)
    except Exception as exc:
        print(f"DEBUG: Parallel search failed for topic={topic!r}: {type(exc).__name__}")
        return _empty_packet(topic, "error")


def search_topics_for_news(topics: list, trace=None) -> dict:
    """Search each topic. Returns {topic: packet}. Safe if Parallel is down."""
    packets = {}
    configured = bool(parallel_api_key())
    sourced = 0
    for topic in topics or []:
        packet = search_topic(topic)
        packets[topic] = packet
        if packet.get("items"):
            sourced += 1
    if trace:
        status = "ok" if sourced else ("skipped" if not configured else "empty")
        trace.stage(
            "parallel_search",
            status=status,
            configured=configured,
            mode=_search_mode() if configured else None,
            topics_with_facts=f"{sourced}/{len(topics or [])}",
        )
    print(
        f"DEBUG: Parallel search configured={configured} "
        f"topics_with_facts={sourced}/{len(topics or [])}"
    )
    return packets
