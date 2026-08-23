"""Outbound email via Resend (replaces Mailtrap).

Set RESEND_API_KEY in `.env` locally, or in production `/etc/glconfig.json`
(same pattern as HEYGEN_API_KEY / Stripe). Replace `re_xxxxxxxxx` with the
key from https://resend.com/api-keys. Custom From addresses require a
verified domain at https://resend.com/domains; until then Resend only
accepts `onboarding@resend.dev`.
"""

from __future__ import annotations

import html as html_lib
import logging
import os
import re
from typing import Optional, Sequence, Union

logger = logging.getLogger(__name__)

DEFAULT_FROM_EMAIL = "onboarding@resend.dev"
DEFAULT_FROM_NAME = "Ndotonic"
INBOUND_RECEIVER = "info@ndotonic.com"
_TAG_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")


def _clean(value: Optional[str]) -> str:
    return (value or "").strip().strip('"').strip("'")


def _flask_config_value(key: str) -> str:
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            return _clean(current_app.config.get(key))
    except Exception:
        pass
    return ""


def _loaded_config_value(*keys: str) -> str:
    """Values already resolved from env or /etc/glconfig.json during package import."""
    try:
        from glconnect import config as app_config
    except Exception:
        return ""
    if not isinstance(app_config, dict):
        return ""
    for key in keys:
        value = _clean(app_config.get(key))
        if value:
            return value
    return ""


def get_resend_api_key() -> str:
    return (
        _flask_config_value("RESEND_API_KEY")
        or _clean(os.getenv("RESEND_API_KEY"))
        or _loaded_config_value("RESEND_API_KEY")
    )


def get_sender_email() -> str:
    return (
        _flask_config_value("RESEND_FROM")
        or _clean(os.getenv("RESEND_FROM"))
        or _flask_config_value("SENDER_MAIL")
        or _clean(os.getenv("SENDER_MAIL"))
        or DEFAULT_FROM_EMAIL
    )


def get_inbound_receiver() -> str:
    """Inbox for user-to-company mail (contact form, careers, alerts)."""
    return (
        _flask_config_value("RECEIVER_MAIL")
        or _clean(os.getenv("RECEIVER_MAIL"))
        or INBOUND_RECEIVER
    )


def is_mail_configured() -> bool:
    return bool(get_resend_api_key())


def _format_from(email: str, name: Optional[str]) -> str:
    address = _clean(email) or DEFAULT_FROM_EMAIL
    label = _clean(name)
    if label:
        return f"{label} <{address}>"
    return address


def _as_list(value: Optional[Union[str, Sequence[str]]]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        item = _clean(value)
        return [item] if item else []
    return [_clean(item) for item in value if _clean(item)]


def _text_to_html(text: str) -> str:
    escaped = html_lib.escape(text)
    return "<p>" + escaped.replace("\n", "<br>\n") + "</p>"


def _tag_value(raw: str) -> str:
    cleaned = _TAG_UNSAFE.sub("-", _clean(raw)).strip("-")
    return (cleaned or "email")[:50]


def send_email(
    *,
    to: Union[str, Sequence[str]],
    subject: str,
    text: Optional[str] = None,
    html: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    reply_to: Optional[Union[str, Sequence[str]]] = None,
    tags: Optional[Sequence[str]] = None,
) -> bool:
    """Send one email through Resend. Returns True on success."""
    api_key = get_resend_api_key()
    if not api_key:
        logger.error("RESEND_API_KEY is not set; email not sent")
        return False

    recipients = _as_list(to)
    if not recipients:
        logger.error("Email not sent: missing recipient")
        return False
    if not text and not html:
        logger.error("Email not sent: missing text and html body")
        return False

    params: dict = {
        "from": _format_from(from_email or get_sender_email(), from_name or DEFAULT_FROM_NAME),
        "to": recipients,
        "subject": subject,
        "html": html or _text_to_html(text or ""),
    }
    if text:
        params["text"] = text
    reply_list = _as_list(reply_to)
    if reply_list:
        params["reply_to"] = reply_list if len(reply_list) > 1 else reply_list[0]
    if tags:
        params["tags"] = [{"name": "category", "value": _tag_value(tag)} for tag in tags if _clean(tag)]

    try:
        import resend
    except ImportError:
        logger.warning("resend package missing; sending via Resend HTTP API")
        return _send_via_resend_http(api_key, params, recipients, subject)

    try:
        resend.api_key = api_key
        resend.Emails.send(params)
        return True
    except Exception:
        logger.exception("Resend send failed (to=%s subject=%s)", recipients, subject)
        return False


def _send_via_resend_http(
    api_key: str,
    params: dict,
    recipients: list[str],
    subject: str,
) -> bool:
    """Send through Resend's REST API when the SDK is not installed in the image."""
    try:
        import requests
    except ImportError:
        logger.error("Neither resend nor requests is installed; email not sent")
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=params,
            timeout=20,
        )
        if response.status_code >= 400:
            logger.error(
                "Resend HTTP send failed (to=%s subject=%s status=%s body=%s)",
                recipients,
                subject,
                response.status_code,
                (response.text or "")[:240],
            )
            return False
        return True
    except Exception:
        logger.exception("Resend HTTP send failed (to=%s subject=%s)", recipients, subject)
        return False
