"""
Patron support tracking: projects a user backed and marketplace listing alerts.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from flask import current_app, url_for
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

PATRON_LISTING_NOTIFICATION_TYPE = 'campaign_listed'


def ensure_patron_book_platform_user(user_id: int, db: Any):
    """
    Return (or create) a minimal BookPlatformUser row so any signed-in account
    can fund campaigns and track supported projects, including author accounts.
    """
    from glconnect.book_platform_models import BookPlatformUser
    from glconnect.models import User, Writer

    existing = BookPlatformUser.query.filter_by(user_id=user_id).first()
    if existing:
        return existing

    user = User.query.get(user_id)
    writer = Writer.query.filter_by(user_id=user_id).first()
    display_name = (
        (writer.writer_name if writer and writer.writer_name else None)
        or (user.username if user else None)
        or "Patron"
    )
    bp_user = BookPlatformUser(
        user_id=user_id,
        pen_name=display_name,
        bio=writer.bio if writer and writer.bio else "Patron",
        profile_picture=(
            writer.profile_picture
            if writer and writer.profile_picture
            else "static/uploads/default_writer.jpg"
        ),
    )
    db.session.add(bp_user)
    db.session.commit()
    return bp_user


def _trackable_statuses():
    from glconnect.book_platform_models import InvestmentStatus

    return (
        InvestmentStatus.CONFIRMED,
        InvestmentStatus.ACTIVE,
        InvestmentStatus.COMPLETED,
        InvestmentStatus.REFUNDED,
    )


def group_patron_supported_projects(investor_bp_id: int, db: Any) -> list[dict[str, Any]]:
    """Group a patron's contributions by campaign, newest activity first."""
    from glconnect.book_platform_models import BookInvestment, BookProject

    if not investor_bp_id:
        return []

    investments = (
        BookInvestment.query.options(
            joinedload(BookInvestment.campaign),
            joinedload(BookInvestment.book_project).joinedload(BookProject.author),
        )
        .filter(
            BookInvestment.investor_id == investor_bp_id,
            BookInvestment.status.in_(_trackable_statuses()),
        )
        .order_by(BookInvestment.invested_at.desc())
        .all()
    )

    groups: dict[int, dict[str, Any]] = {}
    for inv in investments:
        cid = inv.campaign_id
        if cid not in groups:
            groups[cid] = {
                'campaign': inv.campaign,
                'book': inv.book_project,
                'total_amount': 0.0,
                'contribution_count': 0,
                'first_supported_at': None,
                'last_supported_at': None,
                'has_refund': False,
                'investments': [],
            }
        group = groups[cid]
        group['total_amount'] += float(inv.amount or 0)
        group['contribution_count'] += 1
        group['investments'].append(inv)
        from glconnect.book_platform_models import InvestmentStatus

        if inv.status == InvestmentStatus.REFUNDED:
            group['has_refund'] = True
        if inv.invested_at:
            if not group['first_supported_at'] or inv.invested_at < group['first_supported_at']:
                group['first_supported_at'] = inv.invested_at
            if not group['last_supported_at'] or inv.invested_at > group['last_supported_at']:
                group['last_supported_at'] = inv.invested_at

    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(
        groups.values(),
        key=lambda item: item['last_supported_at'] or min_dt,
        reverse=True,
    )


def patron_listing_notifications(
    investor_bp_id: int,
    db: Any,
    *,
    unread_only: bool = False,
    limit: int = 20,
) -> list[Any]:
    from glconnect.book_platform_models import BookNotification

    query = BookNotification.query.filter_by(
        user_id=investor_bp_id,
        notification_type=PATRON_LISTING_NOTIFICATION_TYPE,
    )
    if unread_only:
        query = query.filter_by(is_read=False)
    return query.order_by(BookNotification.created_at.desc()).limit(limit).all()


def mark_patron_listing_notifications_read(investor_bp_id: int, db: Any) -> int:
    from glconnect.book_platform_models import BookNotification

    notes = BookNotification.query.filter_by(
        user_id=investor_bp_id,
        notification_type=PATRON_LISTING_NOTIFICATION_TYPE,
        is_read=False,
    ).all()
    now = datetime.now(timezone.utc)
    for note in notes:
        note.is_read = True
        note.read_at = now
    if notes:
        db.session.commit()
    return len(notes)


def _marketplace_book_url(book_id: int) -> str:
    try:
        return url_for('book_platform.marketplace', open_book=book_id, _external=False)
    except Exception:
        base = (current_app.config.get('FRONTEND_BASE_URL') or '').rstrip('/')
        if base:
            return f'{base}/mybook/marketplace?open_book={book_id}'
        return f'/mybook/marketplace?open_book={book_id}'


def _send_patron_listing_email(bp_user: Any, book: Any, marketplace_url: str) -> bool:
    from mailtrap import Address, Mail, MailtrapClient

    user = getattr(bp_user, 'user', None)
    to_email = getattr(user, 'email', None) if user else None
    if not to_email:
        return False

    sender = os.getenv('SENDER_MAIL')
    api_key = os.getenv('MAIL_TRAP')
    if not sender or not api_key:
        return False

    body = '\n'.join([
        'Good news from Ink Studio!',
        '',
        f'"{book.title}", a project you supported as a patron, is now listed on the marketplace.',
        '',
        f'View it here: {marketplace_url}',
        '',
        'Thank you for helping bring this story to readers.',
        '',
        'Ink Studio',
    ])
    try:
        MailtrapClient(token=api_key).send(Mail(
            sender=Address(email=sender, name='Ink Studio'),
            to=[Address(email=to_email)],
            subject=f'Now on the marketplace: {book.title}',
            text=body,
            category='Patron project listed',
        ))
        return True
    except Exception as exc:
        logger.warning('Patron listing email failed for book %s: %s', getattr(book, 'id', None), exc)
        return False


def notify_patrons_book_listed(book: Any, db: Any, *, send_email: bool = True) -> dict[str, Any]:
    """
    Notify patrons who backed this book when it is first listed on the marketplace.
    """
    from glconnect.book_platform_models import (
        BookInvestment,
        BookNotification,
        BookPlatformUser,
        BookStatus,
    )

    if getattr(book, 'status', None) != BookStatus.PUBLISHED:
        return {'notified': 0, 'skipped': 'not_published'}

    backers = (
        BookInvestment.query.filter(
            BookInvestment.book_project_id == book.id,
            BookInvestment.status.in_(_trackable_statuses()),
        )
        .all()
    )
    by_investor: dict[int, BookInvestment] = {}
    for inv in backers:
        by_investor[inv.investor_id] = inv

    marketplace_url = _marketplace_book_url(book.id)
    notified = 0
    emailed = 0

    for investor_id in by_investor:
        bp_user = BookPlatformUser.query.get(investor_id)
        if not bp_user:
            continue

        existing = BookNotification.query.filter_by(
            user_id=bp_user.id,
            book_project_id=book.id,
            notification_type=PATRON_LISTING_NOTIFICATION_TYPE,
        ).first()
        if existing:
            continue

        db.session.add(BookNotification(
            user_id=bp_user.id,
            book_project_id=book.id,
            title=f'"{book.title}" is on the marketplace',
            message=(
                'A project you supported is now listed on the Ink Studio marketplace. '
                'You helped make this happen!'
            ),
            notification_type=PATRON_LISTING_NOTIFICATION_TYPE,
        ))
        notified += 1

        if send_email and _send_patron_listing_email(bp_user, book, marketplace_url):
            emailed += 1

    if notified:
        db.session.commit()
        logger.info(
            'Notified %s patron(s) that book %s is listed (%s email(s) sent)',
            notified,
            book.id,
            emailed,
        )

    return {'notified': notified, 'emailed': emailed}
