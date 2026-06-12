"""E2E configuration loaded from environment."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

E2E_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = E2E_ROOT.parent
FIXTURES_DIR = E2E_ROOT / "fixtures"

for env_path in (PROJECT_ROOT / ".env", E2E_ROOT / ".env"):
    if env_path.is_file():
        load_dotenv(env_path)


@dataclass(frozen=True)
class E2EConfig:
    base_url: str
    default_password: str
    test_prefix: str
    stripe_enabled: bool
    upload_timeout_ms: int
    navigation_timeout_ms: int

    @property
    def routes_prefix(self) -> str:
        return f"{self.base_url.rstrip('/')}/routes1"

    @property
    def mybook_prefix(self) -> str:
        return f"{self.base_url.rstrip('/')}/mybook"


def resolve_stripe_secret_key() -> str:
    """E2E-only Stripe secret — uses STRIPE_SECRET_FOR_TEST, never production STRIPE_SECRET_KEY."""
    for key in ("STRIPE_SECRET_FOR_TEST",):
        value = (os.getenv(key) or "").strip()
        if value.startswith("sk_"):
            return value
    return ""


def get_config() -> E2EConfig:
    # Do not fall back to FRONTEND_BASE_URL — that is the app's public URL (e.g. glc.cool), not the E2E target.
    base = (os.getenv("E2E_BASE_URL") or "http://localhost:5000").rstrip("/")
    stripe_key = resolve_stripe_secret_key()
    return E2EConfig(
        base_url=base,
        default_password=os.getenv("E2E_DEFAULT_PASSWORD", "E2eTest1!"),
        test_prefix=os.getenv("E2E_TEST_PREFIX", "e2e"),
        stripe_enabled=stripe_key.startswith("sk_test_"),
        upload_timeout_ms=int(os.getenv("E2E_UPLOAD_TIMEOUT_MS", "180000")),
        navigation_timeout_ms=int(os.getenv("E2E_NAV_TIMEOUT_MS", "30000")),
    )
