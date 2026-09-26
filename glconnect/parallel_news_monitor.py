"""Parallel Monitor API client and signed webhook helpers for GRO News."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import requests

from glconnect.parallel_news_search import parallel_api_key

PARALLEL_API_BASE = "https://api.parallel.ai/v1"
_REQUEST_TIMEOUT = (8, 30)
_WEBHOOK_TOLERANCE_SECONDS = 300
ALLOWED_FREQUENCIES = frozenset({"1h", "6h", "12h", "1d", "1w"})
ALLOWED_PROCESSORS = frozenset({"lite", "base"})


class ParallelMonitorError(RuntimeError):
    pass


def parallel_webhook_secret() -> str:
    return (os.getenv("PARALLEL_WEBHOOK_SECRET") or "").strip()


def _headers() -> dict[str, str]:
    api_key = parallel_api_key()
    if not api_key:
        raise ParallelMonitorError("PARALLEL_API_KEY is not configured")
    return {"Content-Type": "application/json", "x-api-key": api_key}


def _request(method: str, path: str, *, body: dict | None = None, params: dict | None = None) -> dict:
    try:
        response = requests.request(
            method,
            f"{PARALLEL_API_BASE}{path}",
            headers=_headers(),
            json=body,
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ParallelMonitorError(f"Parallel request failed: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = str((payload.get("error") or {}).get("message") or payload.get("message") or "")
        except Exception:
            detail = response.text[:200]
        raise ParallelMonitorError(
            f"Parallel returned HTTP {response.status_code}"
            + (f": {detail}" if detail else "")
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ParallelMonitorError("Parallel returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise ParallelMonitorError("Parallel returned an unexpected response")
    return payload


def normalize_frequency(value: str) -> str:
    frequency = (value or "1d").strip().lower()
    if frequency not in ALLOWED_FREQUENCIES:
        raise ValueError(
            f"frequency must be one of: {', '.join(sorted(ALLOWED_FREQUENCIES))}"
        )
    return frequency


def normalize_processor(value: str) -> str:
    processor = (value or "lite").strip().lower()
    if processor not in ALLOWED_PROCESSORS:
        raise ValueError(
            f"processor must be one of: {', '.join(sorted(ALLOWED_PROCESSORS))}"
        )
    return processor


def create_monitor(
    *,
    topic: str,
    desk: str,
    frequency: str,
    processor: str,
    webhook_url: str,
    external_id: str,
) -> dict:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic is required")
    if not webhook_url.startswith("https://"):
        raise ValueError("Parallel webhook URL must use HTTPS")
    query = f"Extract recent material news developments about {topic}"
    return _request(
        "POST",
        "/monitors",
        body={
            "type": "event_stream",
            "frequency": normalize_frequency(frequency),
            "processor": normalize_processor(processor),
            "settings": {"query": query},
            "webhook": {
                "url": webhook_url,
                "event_types": [
                    "monitor.event.detected",
                    "monitor.execution.failed",
                ],
            },
            "metadata": {
                "external_id": external_id,
                "topic": topic,
                "desk": (desk or "news").strip().lower(),
            },
        },
    )


def update_monitor(
    monitor_id: str,
    *,
    topic: str,
    desk: str,
    frequency: str,
    webhook_url: str,
    external_id: str,
) -> dict:
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("topic is required")
    query = f"Extract recent material news developments about {topic}"
    return _request(
        "POST",
        f"/monitors/{monitor_id}/update",
        body={
            "type": "event_stream",
            "frequency": normalize_frequency(frequency),
            "settings": {"query": query},
            "webhook": {
                "url": webhook_url,
                "event_types": [
                    "monitor.event.detected",
                    "monitor.execution.failed",
                ],
            },
            "metadata": {
                "external_id": external_id,
                "topic": topic,
                "desk": (desk or "news").strip().lower(),
            },
        },
    )


def cancel_monitor(monitor_id: str) -> dict:
    return _request("POST", f"/monitors/{monitor_id}/cancel")


def trigger_monitor(monitor_id: str) -> None:
    """Queue one immediate run without changing the monitor schedule."""
    api_key = parallel_api_key()
    if not api_key:
        raise ParallelMonitorError("PARALLEL_API_KEY is not configured")
    try:
        response = requests.post(
            f"{PARALLEL_API_BASE}/monitors/{monitor_id}/trigger",
            headers={"x-api-key": api_key},
            timeout=_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ParallelMonitorError(f"Parallel request failed: {type(exc).__name__}") from exc
    if response.status_code not in (200, 202, 204):
        raise ParallelMonitorError(
            f"Parallel returned HTTP {response.status_code} while triggering monitor"
        )


def fetch_monitor_events(monitor_id: str, event_group_id: str) -> list[dict]:
    payload = _request(
        "GET",
        f"/monitors/{monitor_id}/events",
        params={"event_group_id": event_group_id},
    )
    events = payload.get("events") or []
    return [event for event in events if isinstance(event, dict)]


def _signing_key(secret: str) -> bytes:
    encoded = secret[6:] if secret.startswith("whsec_") else secret
    try:
        return base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("PARALLEL_WEBHOOK_SECRET is not valid base64") from exc


def verify_webhook_signature(
    *,
    body: bytes,
    webhook_id: str,
    webhook_timestamp: str,
    signature_header: str,
    secret: str | None = None,
    now: float | None = None,
) -> bool:
    """Verify Standard Webhooks HMAC-SHA256 and reject stale requests."""
    secret = (secret or parallel_webhook_secret()).strip()
    if not all((secret, webhook_id, webhook_timestamp, signature_header)):
        return False
    try:
        timestamp = int(webhook_timestamp)
    except (TypeError, ValueError):
        return False
    if abs((now if now is not None else time.time()) - timestamp) > _WEBHOOK_TOLERANCE_SECONDS:
        return False
    try:
        signed = (
            webhook_id.encode()
            + b"."
            + webhook_timestamp.encode()
            + b"."
            + body
        )
        expected = base64.b64encode(
            hmac.new(_signing_key(secret), signed, hashlib.sha256).digest()
        ).decode()
    except (ValueError, TypeError):
        return False
    for part in signature_header.split():
        version, separator, signature = part.partition(",")
        if separator and version == "v1" and hmac.compare_digest(signature, expected):
            return True
    return False


def event_values(event: dict[str, Any]) -> dict[str, Any]:
    output = event.get("output") if isinstance(event.get("output"), dict) else {}
    basis = output.get("basis") if isinstance(output.get("basis"), list) else []
    citations = []
    confidences = []
    for row in basis:
        if not isinstance(row, dict):
            continue
        confidence = str(row.get("confidence") or "").strip()
        if confidence:
            confidences.append(confidence)
        for citation in row.get("citations") or []:
            if isinstance(citation, dict) and citation.get("url"):
                citations.append(str(citation["url"]))
    return {
        "parallel_event_id": str(event.get("event_id") or "").strip(),
        "event_group_id": str(event.get("event_group_id") or "").strip(),
        "event_date": str(event.get("event_date") or "").strip() or None,
        "content": str(output.get("content") or "").strip(),
        "citations": json.dumps(list(dict.fromkeys(citations))),
        "confidence": confidences[0] if confidences else None,
    }


def recent_event_packets(topics: list[str], per_topic: int = 3) -> dict[str, list[dict]]:
    """Return recent stored monitor events in the Search packet item shape."""
    try:
        from glconnect.models import db, ParallelNewsEvent, ParallelNewsMonitor

        packets: dict[str, list[dict]] = {}
        for topic in topics or []:
            rows = (
                ParallelNewsEvent.query.join(ParallelNewsMonitor)
                .filter(db.func.lower(ParallelNewsMonitor.topic) == topic.lower())
                .order_by(ParallelNewsEvent.received_at.desc())
                .limit(per_topic)
                .all()
            )
            items = []
            for row in rows:
                try:
                    urls = json.loads(row.citations or "[]")
                except (TypeError, ValueError):
                    urls = []
                items.append(
                    {
                        "title": f"Monitored development ({row.event_date or 'recent'})",
                        "url": urls[0] if urls else "",
                        "excerpts": [row.content],
                    }
                )
            if items:
                packets[topic] = items
        return packets
    except Exception as exc:
        print(f"DEBUG: Stored Parallel monitor events unavailable: {type(exc).__name__}")
        return {}
