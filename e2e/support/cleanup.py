"""Database and filesystem cleanup for E2E test data."""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


def delete_users_by_ids(user_ids: Iterable[int]) -> None:
    """Remove test users and all cascaded Ink Studio data from the live database."""
    from glconnect import create_app, db
    from glconnect.user_deletion_handler import delete_user_and_all_data

    ids = [int(uid) for uid in user_ids if uid]
    if not ids:
        return

    app, _socketio = create_app()
    with app.app_context():
        for user_id in ids:
            result = delete_user_and_all_data(user_id)
            if result.get("success"):
                logger.info("E2E cleanup: deleted user_id=%s — %s", user_id, result.get("message"))
            else:
                logger.warning("E2E cleanup failed for user_id=%s: %s", user_id, result.get("message"))
        db.session.remove()


def delete_user_by_username(username: str) -> bool:
    """Delete a single user by username; returns True if removed."""
    from glconnect import create_app, db
    from glconnect.models import User
    from glconnect.user_deletion_handler import delete_user_and_all_data

    app, _socketio = create_app()
    with app.app_context():
        user = User.query.filter(User.username.ilike(username)).first()
        if not user:
            return False
        result = delete_user_and_all_data(user.user_id)
        db.session.remove()
        return bool(result.get("success"))
