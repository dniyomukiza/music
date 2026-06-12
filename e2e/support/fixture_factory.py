"""DB seed helpers for composable E2E fixtures (skip UI prerequisites)."""
from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from e2e.config import FIXTURES_DIR
from e2e.support.user_factory import TestUser


@dataclass
class BookFixture:
    book_id: int
    title: str
    author_user: TestUser
    bp_user_id: int | None = None
    chapter_id: int | None = None


@dataclass
class CampaignFixture:
    campaign_id: int
    title: str
    book: BookFixture


def _app_context():
    from glconnect import create_app

    app, _socketio = create_app()
    return app


def _copy_cover_to_static() -> str:
    """Return relative path under static/ for BookProject.cover_image."""
    from flask import current_app

    src = FIXTURES_DIR / "cover.png"
    covers_dir = Path(current_app.root_path) / "static" / "book_covers"
    covers_dir.mkdir(parents=True, exist_ok=True)
    name = f"e2e_cover_{uuid.uuid4().hex[:8]}.png"
    shutil.copy2(src, covers_dir / name)
    return f"book_covers/{name}"


def _copy_ebook_to_static() -> tuple[str, str]:
    """Return (relative path, file_type) for digital listing."""
    from flask import current_app

    src = FIXTURES_DIR / "sample_ebook.txt"
    books_dir = Path(current_app.root_path) / "static" / "digital_books"
    books_dir.mkdir(parents=True, exist_ok=True)
    name = f"e2e_ebook_{uuid.uuid4().hex[:8]}.txt"
    shutil.copy2(src, books_dir / name)
    return f"digital_books/{name}", "txt"


def seed_author_profile(test_user: TestUser, *, pen_name: str | None = None) -> TestUser:
    """Ensure BookPlatformUser exists with author_card_setup_completed."""
    from glconnect import db
    from glconnect.book_platform_models import BookPlatformUser

    app = _app_context()
    with app.app_context():
        bp = BookPlatformUser.query.filter_by(user_id=test_user.user_id).first()
        if not bp:
            bp = BookPlatformUser(
                user_id=test_user.user_id,
                pen_name=pen_name or f"Pen {test_user.username[:20]}",
                bio="E2E author profile.",
                author_card_setup_completed=True,
            )
            db.session.add(bp)
        else:
            bp.author_card_setup_completed = True
            if pen_name:
                bp.pen_name = pen_name
        db.session.commit()
        db.session.remove()
    return test_user


def seed_in_platform_book(
    test_user: TestUser,
    *,
    title: str | None = None,
    with_chapter: bool = True,
    word_count: int = 1200,
) -> BookFixture:
    from glconnect import db
    from glconnect.book_platform_models import BookChapter, BookPlatformUser, BookProject, BookStatus

    app = _app_context()
    with app.app_context():
        bp = BookPlatformUser.query.filter_by(user_id=test_user.user_id).first()
        if not bp:
            raise RuntimeError("Call seed_author_profile before seed_in_platform_book")

        book_title = title or f"e2e-written-{uuid.uuid4().hex[:8]}"
        cover_rel = _copy_cover_to_static()
        book = BookProject(
            title=book_title,
            description="E2E in-platform book with enough metadata for campaigns and publishing.",
            genre="fiction",
            language="en",
            target_audience="adult",
            author_id=bp.id,
            cover_image=cover_rel,
            price=4.99,
            status=BookStatus.DRAFT,
            word_count=word_count if with_chapter else 0,
        )
        db.session.add(book)
        db.session.flush()

        chapter_id = None
        if with_chapter:
            content = " ".join(["word"] * word_count)
            chapter = BookChapter(
                book_project_id=book.id,
                title="Chapter One",
                content=content,
                chapter_number=1,
                word_count=word_count,
            )
            db.session.add(chapter)
            db.session.flush()
            chapter_id = chapter.id

        db.session.commit()
        fixture = BookFixture(
            book_id=book.id,
            title=book_title,
            author_user=test_user,
            bp_user_id=bp.id,
            chapter_id=chapter_id,
        )
        db.session.remove()
    return fixture


def seed_published_digital_book(
    test_user: TestUser,
    *,
    title: str | None = None,
    price: float = 3.99,
    audiobook_price: float | None = None,
) -> BookFixture:
    from glconnect import db
    from glconnect.book_platform_models import BookPlatformUser, BookProject, BookStatus

    app = _app_context()
    with app.app_context():
        bp = BookPlatformUser.query.filter_by(user_id=test_user.user_id).first()
        if not bp:
            raise RuntimeError("Call seed_author_profile before seed_published_digital_book")

        book_title = title or f"e2e-digital-{uuid.uuid4().hex[:8]}"
        cover_rel = _copy_cover_to_static()
        digital_rel, file_type = _copy_ebook_to_static()
        now = datetime.now(timezone.utc)

        book = BookProject(
            title=book_title,
            description="E2E published digital listing for marketplace purchase tests.",
            genre="Fiction",
            language="en",
            author_id=bp.id,
            cover_image=cover_rel,
            price=price,
            word_count=50,
            digital_file_path=digital_rel,
            digital_file_type=file_type,
            digital_file_size=1024,
            digital_file_uploaded_at=now,
            digital_book_published=True,
            digital_book_published_at=now,
            status=BookStatus.DRAFT,
        )
        if audiobook_price is not None:
            book.has_audiobook = True
            book.audiobook_price = audiobook_price
            book.audiobook_published = True
            book.audiobook_published_at = now

        db.session.add(book)
        db.session.commit()
        fixture = BookFixture(
            book_id=book.id,
            title=book_title,
            author_user=test_user,
            bp_user_id=bp.id,
        )
        db.session.remove()
    return fixture


def seed_audiobook_on_book(book_id: int) -> None:
    """Attach a minimal audiobook chapter so marketplace can sell audiobook/bundle."""
    from glconnect import db
    from glconnect.book_platform_models import AudiobookChapter, BookProject

    app = _app_context()
    with app.app_context():
        book = BookProject.query.get(book_id)
        if not book:
            raise RuntimeError(f"Book {book_id} not found")
        audio_dir = Path(app.root_path) / "static" / "audiobooks"
        audio_dir.mkdir(parents=True, exist_ok=True)
        # Minimal silent-ish placeholder path (player may 404 without real audio; listing still works)
        rel = f"audiobooks/e2e_{book_id}_{uuid.uuid4().hex[:6]}.mp3"
        (Path(app.root_path) / "static" / rel).write_bytes(b"\x00" * 128)
        ac = AudiobookChapter(
            book_project_id=book.id,
            chapter_number=1,
            title="E2E Audio Chapter",
            audio_file_path=rel,
            duration_seconds=60,
        )
        db.session.add(ac)
        now = datetime.now(timezone.utc)
        book.has_audiobook = True
        book.audiobook_price = book.audiobook_price or 2.99
        book.audiobook_published = True
        book.audiobook_published_at = now
        db.session.commit()
        db.session.remove()


def seed_live_campaign(book: BookFixture, *, title: str | None = None) -> CampaignFixture:
    from glconnect import db
    from glconnect.book_platform_models import CampaignStatus, InvestmentCampaign

    app = _app_context()
    with app.app_context():
        camp_title = title or f"e2e-campaign-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        campaign = InvestmentCampaign(
            book_project_id=book.book_id,
            title=camp_title,
            description="E2E patron campaign with enough description text for discovery and funding tests.",
            funding_goal=500.0,
            minimum_investment=10.0,
            maximum_investment=200.0,
            revenue_share_percentage=0.0,
            return_multiplier_cap=1.0,
            investment_period_days=30,
            status=CampaignStatus.ACTIVE,
            start_date=now,
            current_funding=0.0,
        )
        db.session.add(campaign)
        db.session.commit()
        fixture = CampaignFixture(campaign_id=campaign.id, title=camp_title, book=book)
        db.session.remove()
    return fixture


def _ensure_buyer_platform_user(buyer: TestUser) -> int:
    """Postgres requires buyer_id; ensure a BookPlatformUser row exists for the buyer."""
    from glconnect import db
    from glconnect.book_platform_models import BookPlatformUser

    bp = BookPlatformUser.query.filter_by(user_id=buyer.user_id).first()
    if not bp:
        bp = BookPlatformUser(
            user_id=buyer.user_id,
            pen_name=buyer.display_name or buyer.username,
            bio="E2E reader profile.",
        )
        db.session.add(bp)
        db.session.flush()
    return bp.id


def seed_completed_purchase(buyer: TestUser, book: BookFixture, *, purchase_format: str = "digital") -> int:
    """Insert a completed BookPurchase so buyer can read/download without Stripe."""
    from glconnect import db
    from glconnect.book_platform_models import BookPurchase, TransactionStatus

    app = _app_context()
    with app.app_context():
        amount = 2.99
        if purchase_format == "audiobook":
            amount = 2.99
        elif purchase_format == "bundle":
            amount = 4.99
        buyer_bp_id = _ensure_buyer_platform_user(buyer)
        purchase = BookPurchase(
            buyer_id=buyer_bp_id,
            buyer_user_id=buyer.user_id,
            book_project_id=book.book_id,
            amount=amount,
            currency="USD",
            status=TransactionStatus.COMPLETED,
            purchase_format=purchase_format,
            purchased_at=datetime.now(timezone.utc),
            buyer_username=buyer.username,
            buyer_full_name=buyer.display_name,
            payment_method="e2e_seed",
        )
        db.session.add(purchase)
        db.session.commit()
        pid = purchase.id
        db.session.remove()
    return pid


def seed_pending_purchase(buyer: TestUser, book: BookFixture, *, amount: float | None = None) -> int:
    """Insert PENDING purchase for Stripe webhook integration tests."""
    from glconnect import db
    from glconnect.book_platform_models import BookPurchase, TransactionStatus

    app = _app_context()
    with app.app_context():
        from glconnect.book_platform_models import BookProject

        proj = BookProject.query.get(book.book_id)
        price = amount if amount is not None else (proj.price if proj else 2.99)
        buyer_bp_id = _ensure_buyer_platform_user(buyer)
        purchase = BookPurchase(
            buyer_id=buyer_bp_id,
            buyer_user_id=buyer.user_id,
            book_project_id=book.book_id,
            amount=price,
            currency="USD",
            status=TransactionStatus.PENDING,
            purchase_format="digital",
            buyer_username=buyer.username,
            buyer_full_name=buyer.display_name,
        )
        db.session.add(purchase)
        db.session.commit()
        pid = purchase.id
        db.session.remove()
    return pid


def seed_published_written_book(book: BookFixture) -> BookFixture:
    from glconnect import db
    from glconnect.book_platform_models import BookProject, BookStatus

    app = _app_context()
    with app.app_context():
        proj = BookProject.query.get(book.book_id)
        if not proj:
            raise RuntimeError(f"Book {book.book_id} not found")
        now = datetime.now(timezone.utc)
        proj.status = BookStatus.PUBLISHED
        proj.published_at = now
        db.session.commit()
        db.session.remove()
    return book
