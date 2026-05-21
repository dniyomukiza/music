"""
Book campaign patronage mode (nonprofit-style funding).

Authors run campaigns to raise money for stories with positive impact; funders discover
projects and contribute via existing Ink Studio flows. UI and routes stay the same;
this module toggles economics: no revenue-share returns to funders from marketplace sales.

Set BOOK_CAMPAIGN_PATRONAGE=0 to restore legacy investment returns (dev only).
"""

from __future__ import annotations

import os
from typing import Any, Optional


def _env_truthy(value: Optional[str], default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in ("0", "false", "no", "off")


def is_book_campaign_patronage_mode(app: Any = None) -> bool:
    """True when campaigns are patronage (contributions), not sale-linked investments."""
    if app is not None:
        return bool(app.config.get("BOOK_CAMPAIGN_PATRONAGE", True))
    try:
        from flask import current_app

        return bool(current_app.config.get("BOOK_CAMPAIGN_PATRONAGE", True))
    except RuntimeError:
        return _env_truthy(os.getenv("BOOK_CAMPAIGN_PATRONAGE"), default=True)


def patronage_campaign_terms() -> dict[str, float]:
    """Stored on campaigns/contributions; UI may still show legacy fields."""
    return {
        "revenue_share_percentage": 0.0,
        "return_multiplier_cap": 1.0,
    }


def effective_investor_pool_percentage(app: Any = None) -> float:
    """Share of each book sale paid to funders; 0 in patronage mode."""
    return 0.0 if is_book_campaign_patronage_mode(app) else 25.0


def apply_patronage_terms_to_investment(investment: Any) -> None:
    """Ensure a contribution record does not accrue sale-based returns."""
    investment.revenue_share_percentage = 0.0
    investment.return_multiplier = 1.0
