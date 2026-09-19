"""Password reset: token lifecycle, validation, and outbound email."""

from __future__ import annotations

import re
from typing import Optional, Tuple

from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer

from glconnect.email_service import send_email
from glconnect.models import User, db

PASSWORD_RESET_SALT = "password-reset"
PASSWORD_RESET_MAX_AGE_SECONDS = 3600

_PASSWORD_SPECIAL = re.compile(r"[^\w\s]")


def password_strength_error(password: str) -> Optional[str]:
    """Return an error message when password fails policy, else None."""
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters long, contain a capital letter, and a special symbol."
    if not re.search(r"[A-Z]", password):
        return "Password must be at least 8 characters long, contain a capital letter, and a special symbol."
    if not _PASSWORD_SPECIAL.search(password):
        return "Password must be at least 8 characters long, contain a capital letter, and a special symbol."
    return None


def mask_email(email: str) -> str:
    """Return a privacy-preserving hint, e.g. j***@example.com."""
    local, _, domain = (email or "").partition("@")
    if not local or not domain:
        return "***"
    if len(local) == 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + ("*" * min(3, len(local) - 2)) + local[-1]
    return f"{masked_local}@{domain}"


def find_user_by_username(username: str) -> Optional[User]:
    name = (username or "").strip()
    if not name:
        return None
    return User.query.filter(User.username.ilike(name)).first()


def find_user_by_login_identifier(identifier: str) -> Optional[User]:
    """Resolve account by username or email."""
    ident = (identifier or "").strip()
    if not ident:
        return None
    if "@" in ident:
        return User.query.filter(User.email.ilike(ident)).first()
    return find_user_by_username(ident)


def build_password_reset_token(email: str) -> str:
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt=PASSWORD_RESET_SALT)


def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.loads(
            token,
            salt=PASSWORD_RESET_SALT,
            max_age=PASSWORD_RESET_MAX_AGE_SECONDS,
        )
    except Exception:
        return None


def build_password_reset_url(email: str) -> str:
    token = build_password_reset_token(email)
    return url_for("routes1.reset_password", token=token, _external=True)


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    return send_email(
        to=to_email,
        subject="Reset your Ndotonic password",
        text=(
            "We received a request to reset your Ndotonic password.\n\n"
            f"Reset your password (link expires in 1 hour):\n{reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        ),
        from_name="Ndotonic",
        tags=["reset-password"],
    )


def issue_password_reset(user: User) -> bool:
    """Generate token and email reset link. Returns True when mail was sent."""
    if not user or not user.email:
        return False
    reset_url = build_password_reset_url(user.email)
    return send_password_reset_email(user.email, reset_url)


def request_password_reset(identifier: str) -> Tuple[bool, Optional[str]]:
    """
    Look up account and send reset email.

    Returns (sent, masked_email). masked_email is set only when mail was sent.
    """
    user = find_user_by_login_identifier(identifier)
    if not user:
        return False, None
    if not issue_password_reset(user):
        return False, None
    return True, mask_email(user.email)


def apply_password_reset(user: User, new_password: str) -> Optional[str]:
    """Validate and persist a new password. Returns error message or None on success."""
    err = password_strength_error(new_password)
    if err:
        return err
    user.set_password(new_password)
    db.session.commit()
    return None
