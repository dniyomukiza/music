#!/usr/bin/env python3
"""Unit tests for Parallel Monitor requests and webhook verification."""

import base64
import hashlib
import hmac
import json
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
package = types.ModuleType("glconnect")
package.__path__ = [str(ROOT / "glconnect")]
sys.modules.setdefault("glconnect", package)

from glconnect.parallel_news_monitor import (
    create_monitor,
    event_values,
    verify_webhook_signature,
)


def _signature(secret, webhook_id, timestamp, body):
    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = webhook_id.encode() + b"." + timestamp.encode() + b"." + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def test_valid_webhook_signature():
    body = json.dumps({"type": "monitor.event.detected"}, separators=(",", ":")).encode()
    secret = "whsec_" + base64.b64encode(b"test-secret-key").decode()
    timestamp = "1700000000"
    assert verify_webhook_signature(
        body=body,
        webhook_id="whevent_123",
        webhook_timestamp=timestamp,
        signature_header=_signature(secret, "whevent_123", timestamp, body),
        secret=secret,
        now=1700000000,
    )


def test_rejects_stale_or_tampered_webhook():
    body = b'{"ok":true}'
    secret = "whsec_" + base64.b64encode(b"test-secret-key").decode()
    signature = _signature(secret, "whevent_123", "1700000000", body)
    assert not verify_webhook_signature(
        body=body + b" ",
        webhook_id="whevent_123",
        webhook_timestamp="1700000000",
        signature_header=signature,
        secret=secret,
        now=1700000000,
    )
    assert not verify_webhook_signature(
        body=body,
        webhook_id="whevent_123",
        webhook_timestamp="1700000000",
        signature_header=signature,
        secret=secret,
        now=1700001000,
    )


def test_create_uses_stable_monitor_contract():
    response = Mock(status_code=200)
    response.json.return_value = {
        "monitor_id": "monitor_123",
        "status": "active",
        "frequency": "1h",
    }
    with patch.dict("os.environ", {"PARALLEL_API_KEY": "test-key"}):
        with patch("glconnect.parallel_news_monitor.requests.request", return_value=response) as call:
            create_monitor(
                topic="US markets",
                desk="business",
                frequency="1h",
                processor="lite",
                webhook_url="https://ndotonic.com/routes2/news/api/parallel-monitors/webhook",
                external_id="glc-news-123",
            )
    args, kwargs = call.call_args
    assert args == ("POST", "https://api.parallel.ai/v1/monitors")
    assert kwargs["json"]["type"] == "event_stream"
    assert kwargs["json"]["frequency"] == "1h"
    assert kwargs["json"]["settings"]["query"].endswith("US markets")
    assert kwargs["json"]["metadata"]["desk"] == "business"


def test_event_values_extracts_sources():
    values = event_values({
        "event_id": "mevt_1",
        "event_group_id": "mevtgrp_1",
        "event_date": "2026-08-21",
        "output": {
            "content": "A material development happened.",
            "basis": [{
                "confidence": "high",
                "citations": [
                    {"url": "https://example.com/a"},
                    {"url": "https://example.com/a"},
                    {"url": "https://example.com/b"},
                ],
            }],
        },
    })
    assert values["parallel_event_id"] == "mevt_1"
    assert json.loads(values["citations"]) == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    assert values["confidence"] == "high"


def main():
    test_valid_webhook_signature()
    test_rejects_stale_or_tampered_webhook()
    test_create_uses_stable_monitor_contract()
    test_event_values_extracts_sources()
    print("OK: parallel_news_monitor tests passed")


if __name__ == "__main__":
    main()
