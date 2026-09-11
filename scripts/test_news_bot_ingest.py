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
from glconnect.news_routes import _bot_ingest_authorized, _run_bot_scripts_thread


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


def _test_app():
    from glconnect import create_app, config as glconfig

    env_patch = patch.dict(
        "os.environ",
        {"DATABASE_URL": "sqlite:///:memory:", "DB_URL": "sqlite:///:memory:"},
        clear=False,
    )
    config_patch = patch.dict(glconfig, {"DB_URL": "sqlite:///:memory:"}, clear=False)
    with env_patch, config_patch:
        return create_app(
            config_overrides={
                "JWT_SECRET_KEY": "test-secret",
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_ENGINE_OPTIONS": {},
                "WTF_CSRF_ENABLED": False,
            }
        )


def test_bot_scripts_accepts_async():
    """POST /bot-scripts returns 202 immediately and runs pipeline in a background thread."""
    import threading as threading_module

    started = {"called": False, "task_id": None}

    def fake_thread_start(self):
        started["called"] = True
        started["task_id"] = self._args[2]
        return None

    result = _test_app()
    app = result[0] if isinstance(result, tuple) else result
    payload = {
        "source": "grok-bot",
        "reporters": [
            {"topic": "Markets", "category": "finance", "script": "Yields eased after the open."},
        ],
    }

    with patch.dict("os.environ", {"NEWS_BOT_INGEST_TOKEN": "secret-token"}, clear=False):
        with patch.object(threading_module.Thread, "start", fake_thread_start):
            with patch("glconnect.news_routes._create_running_news_task", return_value="task-async-123"):
                with app.test_client() as client:
                    response = client.post(
                        "/routes2/news/bot-scripts",
                        json=payload,
                        headers={"Authorization": "Bearer secret-token"},
                    )

    assert response.status_code == 202
    body = response.get_json()
    assert body["task_id"] == "task-async-123"
    assert body["status"] == "accepted"
    assert started["called"] is True
    assert started["task_id"] == "task-async-123"


def test_bot_scripts_sync_errors():
    result = _test_app()
    app = result[0] if isinstance(result, tuple) else result
    payload = {
        "reporters": [{"topic": "Markets", "category": "finance", "script": ""}],
    }

    with patch.dict("os.environ", {"NEWS_BOT_INGEST_TOKEN": "secret-token"}, clear=False):
        with app.test_client() as client:
            unauthorized = client.post("/routes2/news/bot-scripts", json=payload)
            bad_token = client.post(
                "/routes2/news/bot-scripts",
                json=payload,
                headers={"Authorization": "Bearer wrong"},
            )
            bad_payload = client.post(
                "/routes2/news/bot-scripts",
                json=payload,
                headers={"Authorization": "Bearer secret-token"},
            )

    assert unauthorized.status_code == 401
    assert bad_token.status_code == 401
    assert bad_payload.status_code == 400


def test_run_bot_scripts_thread_records_failure():
    result = _test_app()
    app = result[0] if isinstance(result, tuple) else result
    reports = [{"topic": "Markets", "category": "finance", "script": "Yields eased."}]

    with patch("glconnect.news_routes.generate_broadcast_from_bot_copy", side_effect=RuntimeError("tts down")):
        with patch("glconnect.news_routes.update_task_in_db") as update_task:
            with patch("glconnect.news_routes.tasks", {"task-fail-1": {"status": "running"}}):
                with patch("glconnect.news_routes._tasks_lock"):
                    _run_bot_scripts_thread(app, reports, "task-fail-1", "grok-bot")

    update_task.assert_called_once()
    kwargs = update_task.call_args.kwargs
    assert kwargs["status"] == "failed"
    assert "tts down" in kwargs["error"]


if __name__ == "__main__":
    test_parse_maps_aliases_and_desks()
    test_parse_rejects_missing_script_and_placeholder()
    test_bot_segments_skip_gemini_and_assign_roster()
    test_bot_ingest_token()
    test_bot_scripts_accepts_async()
    test_bot_scripts_sync_errors()
    test_run_bot_scripts_thread_records_failure()
    print("ok")
