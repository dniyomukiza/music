"""Complete Stripe Checkout in Playwright using test cards."""
from __future__ import annotations

import json
import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Page

_DEBUG_LOG = "/Applications/untitled folder/music-1/.cursor/debug-f3d0e1.log"


def _dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    # #region agent log
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "f3d0e1",
                        "hypothesisId": hypothesis_id,
                        "location": location,
                        "message": message,
                        "data": data or {},
                        "timestamp": int(time.time() * 1000),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion


STRIPE_TEST_CARD = "4242424242424242"
STRIPE_TEST_EXP = "12/34"
STRIPE_TEST_CVC = "123"
STRIPE_TEST_ZIP = "10001"


def complete_stripe_checkout(checkout_page: Page, *, timeout_ms: int = 120_000) -> None:
    """
    Fill Stripe hosted Checkout and submit payment.

    Works with Stripe Checkout's iframe-based card element. After success,
    Stripe redirects to the app's purchase/success URL.
    """
    checkout_page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)

    if "checkout.stripe.com" not in checkout_page.url:
        checkout_page.wait_for_url(re.compile(r"checkout\.stripe\.com"), timeout=timeout_ms)

    # #region agent log
    try:
        body_snip = (checkout_page.locator("body").inner_text(timeout=5000) or "")[:400]
    except Exception as ex:
        body_snip = f"<body read failed: {type(ex).__name__}>"
    _dbg(
        "A",
        "stripe_checkout.py:complete_stripe_checkout",
        "checkout page loaded",
        {
            "url": checkout_page.url,
            "title": checkout_page.title(),
            "frame_count": len(checkout_page.frames),
            "frame_urls": [fr.url for fr in checkout_page.frames[:12]],
            "body_snippet": body_snip,
        },
    )
    # #endregion

    # Email field (sometimes pre-filled)
    email = checkout_page.locator('input[name="email"], input[id="email"]')
    if email.count() and email.first.is_visible():
        if not (email.first.input_value() or "").strip():
            email.first.fill("buyer@e2e.invalid")

    _fill_card_in_checkout(checkout_page, timeout_ms)

    pay_btn = checkout_page.locator(
        'button:has-text("Pay"), button[data-testid="hosted-payment-submit-button"], #submitButton'
    )
    pay_btn.first.click(timeout=timeout_ms)

    checkout_page.wait_for_load_state("networkidle", timeout=timeout_ms)


def _fill_card_in_checkout(page: Page, timeout_ms: int) -> None:
    """Try direct fields first, then iframe-hosted card inputs."""
    direct_selectors = [
        'input[name="cardNumber"]',
        'input[autocomplete="cc-number"]',
        "#cardNumber",
    ]
    direct_probe: list[dict] = []
    for sel in direct_selectors:
        loc = page.locator(sel)
        cnt = loc.count()
        vis = False
        try:
            vis = cnt > 0 and loc.first.is_visible()
        except Exception:
            pass
        direct_probe.append({"selector": sel, "count": cnt, "visible": vis})
        if vis:
            # #region agent log
            _dbg("B", "stripe_checkout.py:_fill_card_in_checkout", "filled direct card fields", {"selector": sel})
            # #endregion
            loc.first.fill(STRIPE_TEST_CARD)
            page.locator('input[name="cardExpiry"], input[autocomplete="cc-exp"]').first.fill(STRIPE_TEST_EXP)
            page.locator('input[name="cardCvc"], input[autocomplete="cc-csc"]').first.fill(STRIPE_TEST_CVC)
            zip_loc = page.locator('input[name="postalCode"], input[autocomplete="postal-code"]')
            if zip_loc.count() and zip_loc.first.is_visible():
                zip_loc.first.fill(STRIPE_TEST_ZIP)
            return

    frame_probe: list[dict] = []
    for frame in page.frames:
        try:
            number = frame.locator('input[name="cardnumber"], input[placeholder*="Card number"]')
            n_cnt = number.count()
            n_vis = False
            try:
                n_vis = n_cnt > 0 and number.first.is_visible()
            except Exception:
                pass
            frame_probe.append({"url": frame.url, "name": frame.name, "card_count": n_cnt, "card_visible": n_vis})
            if n_vis:
                # #region agent log
                _dbg("C", "stripe_checkout.py:_fill_card_in_checkout", "filled iframe card fields", {"frame_url": frame.url})
                # #endregion
                number.first.fill(STRIPE_TEST_CARD)
                frame.locator('input[name="exp-date"], input[placeholder*="MM"]').first.fill(STRIPE_TEST_EXP)
                frame.locator('input[name="cvc"], input[placeholder*="CVC"]').first.fill(STRIPE_TEST_CVC)
                return
        except Exception as ex:
            frame_probe.append({"url": frame.url, "error": type(ex).__name__})
            continue

    # #region agent log
    pm_tabs = []
    for tab_sel in (
        'button:has-text("Card")',
        '[data-testid="card-accordion-item"]',
        'text=Pay with card',
    ):
        tloc = page.locator(tab_sel)
        pm_tabs.append({"selector": tab_sel, "count": tloc.count()})
    all_inputs = page.locator("input")
    input_meta: list[dict] = []
    for i in range(min(all_inputs.count(), 15)):
        el = all_inputs.nth(i)
        try:
            input_meta.append(
                {
                    "name": el.get_attribute("name"),
                    "autocomplete": el.get_attribute("autocomplete"),
                    "placeholder": el.get_attribute("placeholder"),
                    "type": el.get_attribute("type"),
                    "visible": el.is_visible(),
                }
            )
        except Exception:
            break
    _dbg(
        "B,C,D,E",
        "stripe_checkout.py:_fill_card_in_checkout",
        "card fields not found",
        {
            "direct_probe": direct_probe,
            "frame_probe": frame_probe,
            "pm_tabs": pm_tabs,
            "input_meta": input_meta,
            "url": page.url,
        },
    )
    # #endregion

    raise RuntimeError("Could not locate Stripe card fields on checkout page")
