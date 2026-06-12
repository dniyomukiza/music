"""Verify the Flask app is reachable before running browser tests."""
from __future__ import annotations

import urllib.error
import urllib.request


def app_is_healthy(base_url: str, timeout: float = 5.0) -> bool:
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
