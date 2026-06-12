"""Create uniquely named E2E users (UI or direct DB seeding)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from e2e.config import E2EConfig

Role = Literal["author", "other", "artist", "blogger", "podcaster"]


@dataclass
class TestUser:
    username: str
    email: str
    password: str
    role: str
    first_name: str
    last_name: str
    user_id: int | None = None

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


def unique_suffix(worker_id: str = "master") -> str:
    return f"{worker_id}-{uuid.uuid4().hex[:8]}"


def build_test_user(
    cfg: E2EConfig,
    *,
    role: Role = "author",
    worker_id: str = "master",
    label: str = "user",
) -> TestUser:
    suffix = unique_suffix(worker_id)
    username = f"{cfg.test_prefix}-{label}-{suffix}"[:40]
    return TestUser(
        username=username,
        email=f"{username}@example.com",
        password=cfg.default_password,
        role=role,
        first_name="E2E",
        last_name=label.title(),
    )


def seed_user_in_db(test_user: TestUser) -> TestUser:
    """Insert user directly (skips UI register + reCAPTCHA). Returns user with user_id set."""
    from glconnect import create_app, db
    from glconnect.models import User, Writer

    app, _socketio = create_app()
    with app.app_context():
        existing = User.query.filter(User.username.ilike(test_user.username)).first()
        if existing:
            test_user.user_id = existing.user_id
            return test_user

        user = User(
            username=test_user.username,
            email=test_user.email,
            first_name=test_user.first_name,
            last_name=test_user.last_name,
            confirmed=True,
            role=test_user.role,
        )
        user.set_password(test_user.password)
        db.session.add(user)
        db.session.commit()

        if test_user.role == "author":
            writer = Writer(
                user_id=user.user_id,
                writer_name=test_user.display_name,
                bio="",
                profile_picture="static/uploads/default_writer.jpg",
            )
            db.session.add(writer)
            db.session.commit()

        test_user.user_id = user.user_id
        db.session.remove()
    return test_user


def resolve_user_id(username: str, email: str | None = None) -> int | None:
    """Look up user_id after UI registration (brief retry for commit visibility)."""
    import time

    from glconnect import create_app, db
    from glconnect.models import User

    app, _socketio = create_app()
    with app.app_context():
        uid = None
        for _ in range(5):
            user = User.query.filter(User.username.ilike(username)).first()
            if not user and email:
                user = User.query.filter(User.email.ilike(email)).first()
            if user:
                uid = user.user_id
                break
            time.sleep(0.3)
        db.session.remove()
    return uid
