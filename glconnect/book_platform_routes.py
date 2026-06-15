"""
Ink Studio Routes - Flask routes for the Ink Studio functionality
This module contains all routes for Ink Studio including:
- Book creation and management
- Collaboration features
- Real-time editing
- Marketplace functionality
- User management
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, current_app, send_from_directory, send_file, abort, Response
from flask_login import login_required, current_user, login_user
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import os
import uuid
import json
import logging
import re
from functools import wraps
import zipfile
from tempfile import SpooledTemporaryFile
from typing import List, Optional
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from mailtrap import MailtrapClient, Mail, Address

# Import models
from glconnect.models import db, User, Writer
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookChapter, BookCollaboration, 
    CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
    ChapterSuggestion,     BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification,
    LibraryBookHide,
    ReaderAnnotation,
    BookStatus, CollaborationRole, InvitationStatus, CommentStatus, TransactionStatus,
    AudioGenerationTask, AudiobookChapter, AccreditedReviewer, BookReview, InvestmentCampaign, BookInvestment,
    SavedBookCampaign,
    AuthorCampaignPayoutRequest,
    RevenueDistribution, ReviewerEarning, InvestmentPayout, PayoutRequest, ReviewerPayoutRequest, AuthorSalesPayoutRequest, RefundRequest, ReviewerStatus, ReviewerLevel,
    ReviewStatus, ReviewRequest, ReviewRequestStatus, InvestmentStatus, CampaignStatus, DistributionType,
    BookPrintOrder, PrintOrderStatus,
)

# Import additional modules
from glconnect.forms import DigitalBookUploadForm, ReviewerRegistrationForm, BookReviewForm, InvestmentCampaignForm, InvestmentForm, EditCampaignProjectForm
from glconnect.digital_book_processor import digital_book_processor
from glconnect.audiobook_text_segments import build_uploaded_book_audiobook_chapters
from glconnect.audiobook_generation_helpers import build_audiobook_source, filter_and_renumber_chapters
from glconnect.audiobook_segment_classifier import suggest_includes_for_chapters
from glconnect.book_cover_ai import generate_book_cover_bytes
from glconnect.platform_fee_policy import (
    apply_campaign_fee_terms,
    campaign_fee_summary,
    campaign_milestone_release_amount,
    ensure_campaign_fee_terms,
    marketplace_author_royalty_fraction,
)
from glconnect.book_purchase_format import (
    normalize_purchase_format,
    print_listed,
    print_shipping_amount,
    base_price_for_format,
    total_checkout_amount,
    revenue_split_for_purchase,
    STRIPE_PRINT_SHIPPING_COUNTRIES,
)
from glconnect.author_publishing_agreement import (
    AUTHOR_PUBLISHING_AGREEMENT_VERSION,
    LISTING_ATTESTATION_VERSION,
    author_has_accepted_agreement,
    author_requires_publishing_agreement,
    record_author_agreement_acceptance,
    validate_listing_terms_payload,
    record_listing_attestation,
    agreement_context_for_templates,
)
from glconnect.book_cover_preview import (
    clear_edit_preview,
    clear_listing_preview,
    edit_preview_image_rel,
    listing_preview_image_rel,
    promote_edit_preview_to_cover,
    promote_listing_preview_to_cover,
    save_edit_preview,
    save_listing_preview,
    set_listing_preview_accepted,
    maybe_remove_local_cover_file,
)
from glconnect.audio_book_generator import audio_book_generator
from glconnect.book_language_tts import (
    book_language_select_choices,
    language_label,
    TTS_BOOK_LANGUAGES,
    tts_voice_list_prefix,
)
from glconnect.revenue_distribution_service import distribute_revenue
from glconnect.stripe_utils import (
    init_stripe,
    get_stripe_server_secret_key,
    get_webhook_secret,
    checkout_payment_method_types_for_currency,
    checkout_customer_email_for_user,
    marketplace_book_payment_intent_data,
    author_needs_stripe_payout_setup,
)
from glconnect.book_utils import (
    audiobook_ready_for_marketplace_publish,
    delete_book_chapter_version_graph_for_project,
    is_book_published,
)
from glconnect.author_dashboard_stats import build_author_dashboard_stats
from glconnect.project_description_media import (
    MEDIA_GUIDE,
    ProjectDescriptionError,
    build_audio_html,
    build_image_html,
    build_video_html,
    build_video_iframe_html,
    normalize_video_embed_url,
    project_description_plain_length,
    sanitize_project_description,
    save_project_media_file,
    ckeditor_upload_response,
)
from glconnect.chapter_version_service import (
    list_chapter_versions as fetch_chapter_versions,
    resolve_version_actor_id,
    restore_chapter_version as apply_chapter_version_restore,
    snapshot_chapter,
)
import threading
from werkzeug.utils import secure_filename

# Create blueprint
book_bp = Blueprint('book_platform', __name__, url_prefix='/mybook')


@book_bp.context_processor
def _inject_author_agreement_template_context():
    return agreement_context_for_templates()


@book_bp.after_request
def _ink_studio_disable_page_cache(response):
    """Prevent browser back-cache from showing authenticated Ink Studio after logout."""
    if response.content_type and 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Initialize logger
logger = logging.getLogger(__name__)


# Image upload configuration
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB

def get_image_upload_folder():
    """Get the image upload folder for book chapters"""
    upload_folder = os.path.join(current_app.root_path, 'static', 'book_images')
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

def allowed_image_file(filename):
    """Check if the uploaded file is an allowed image type"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def _author_requires_setup_profile(user_id: int) -> bool:
    """True until user_id has saved Ink Studio author card at /mybook/setup-profile."""
    bu = BookPlatformUser.query.filter_by(user_id=user_id).first()
    if not bu:
        return True
    return not bool(getattr(bu, "author_card_setup_completed", False))


def _author_needs_publishing_agreement(user_id: int) -> bool:
    """True until author accepts the current account-level Author Publishing Agreement."""
    return author_requires_publishing_agreement(user_id)


def _redirect_to_publishing_agreement(next_path: str = None):
    """Redirect authors to accept the account-level agreement before listing."""
    n = safe_mybook_next_path(next_path, url_for('book_platform.books'))
    return redirect(url_for('book_platform.author_publishing_agreement', next=n))


def _author_needs_marketplace_profile_step() -> bool:
    """True until the author saves Ink Studio author card once at /mybook/setup-profile."""
    if not current_user.is_authenticated:
        return False
    return _author_requires_setup_profile(current_user.user_id)


def _safe_next_url_for_profile_setup(req) -> str:
    """After setup-profile save: only same-site paths under /mybook (open-redirect safe)."""
    n = (req.values.get("next") or "").strip()
    if n.startswith("/mybook") and not n.startswith("//") and ".." not in n and "\n" not in n:
        return n
    return url_for("book_platform.books")


def _setup_profile_next_query_param() -> str:
    """Optional ?next= from GET /setup-profile; only allow internal /mybook paths."""
    n = (request.args.get("next") or "").strip()
    if n.startswith("/mybook") and not n.startswith("//") and ".." not in n and "\n" not in n:
        return n
    return ""


def _normalize_public_website(url):
    """Return a safe https URL for public author links, or None if invalid/empty."""
    from urllib.parse import urlparse, urlunparse

    if not url or not str(url).strip():
        return None
    raw = str(url).strip()
    lo = raw.lower()
    if lo.startswith(('javascript:', 'data:', 'vbscript:', 'file:')):
        return None
    if '://' not in raw:
        raw = 'https://' + raw.lstrip('/')
    try:
        parsed = urlparse(raw)
    except Exception:
        return None
    if parsed.scheme not in ('http', 'https'):
        return None
    netloc = parsed.netloc
    if not netloc:
        return None
    path = parsed.path or ''
    return urlunparse(
        ('https', netloc, path, parsed.params or '', parsed.query or '', parsed.fragment or '')
    )


def _public_website_label(https_url):
    """Short label for link text (host + path)."""
    from urllib.parse import urlparse

    if not https_url:
        return None
    p = urlparse(https_url)
    label = p.netloc + (p.path if p.path not in ('', '/') else '')
    if len(label) > 52:
        label = label[:49] + '…'
    return label


def _marketplace_author_bio(author, writer):
    """Prefer Ink Studio (BookPlatformUser) bio when set; else Writer bio."""
    if author and author.bio and str(author.bio).strip():
        return str(author.bio).strip()
    if writer and writer.bio and str(writer.bio).strip():
        return str(writer.bio).strip()
    return None


def _marketplace_author_profile_picture(author, writer):
    """Prefer Ink Studio photo when set and not default; else Writer photo."""
    def _is_default(p):
        return not p or str(p).strip() == 'static/uploads/default_writer.jpg'

    if author:
        bp = (author.profile_picture or '').strip()
        if bp and not _is_default(bp):
            return bp
    if writer and writer.profile_picture and not _is_default(writer.profile_picture):
        return str(writer.profile_picture).strip()
    return None


def book_has_listing_cover(book):
    """Whether the book has a cover path or URL set for marketplace display."""
    if not book:
        return False
    c = getattr(book, 'cover_image', None)
    return bool(c and str(c).strip())


def safe_mybook_next_path(candidate, default_path):
    """Allow only same-site Ink Studio paths (mitigate open redirects)."""
    if not candidate or not isinstance(candidate, str):
        return default_path
    c = candidate.strip()
    if "://" in c or c.startswith("//"):
        return default_path
    if not c.startswith("/mybook"):
        return default_path
    return c


def library_reader_split_plain_pages(text: str, max_chars: int = 12000) -> List[str]:
    """Split extracted plain text into pages for library prev/next navigation."""
    if not text or not str(text).strip():
        return []
    text = str(text).strip()
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    paras = re.split(r"\n\s*\n", text)
    buf: List[str] = []
    size = 0
    for para in paras:
        plen = len(para) + 2
        if size + plen > max_chars and buf:
            chunks.append("\n\n".join(buf))
            buf = [para]
            size = len(para)
        else:
            buf.append(para)
            size += plen
    if buf:
        chunks.append("\n\n".join(buf))
    out: List[str] = []
    for pg in chunks:
        if len(pg) <= max_chars:
            out.append(pg)
        else:
            for i in range(0, len(pg), max_chars):
                out.append(pg[i : i + max_chars])
    return out


def build_library_reader_pages(book: BookProject) -> List[dict]:
    """Sections shown in /library/books/<id>/read: chapters first, else extracted file split into parts."""
    book_id = book.id
    chapters = (
        BookChapter.query.filter_by(book_project_id=book_id)
        .order_by(BookChapter.chapter_number)
        .all()
    )
    chapter_blocks = []
    for ch in chapters:
        body = (ch.content or '').strip()
        if body:
            chapter_blocks.append({'title': ch.title or f'Chapter {ch.chapter_number}', 'html': ch.content})

    plain_text = None
    if not chapter_blocks and book.digital_file_path:
        rel_path = book.digital_file_path
        file_path = os.path.join(current_app.root_path, 'static', rel_path)
        if os.path.exists(file_path):
            file_type = (book.digital_file_type or 'txt').lower().lstrip('.') or 'txt'
            try:
                extraction = digital_book_processor.extract_text(file_path, file_type)
                if extraction.get('success') and extraction.get('text'):
                    plain_text = extraction['text']
            except Exception as ex:
                logger.warning('build_library_reader_pages extract failed for book %s: %s', book_id, ex)

    reader_pages: List[dict] = []
    for block in chapter_blocks:
        reader_pages.append({'title': block['title'], 'html': block['html'], 'plain': None})
    if not reader_pages and plain_text:
        parts = library_reader_split_plain_pages(plain_text)
        n = len(parts)
        for i, chunk in enumerate(parts):
            reader_pages.append({
                'title': f'Part {i + 1} of {n}' if n > 1 else 'Full text',
                'html': None,
                'plain': chunk,
            })
    return reader_pages


def _library_reader_user_has_ebook_access(book: BookProject, user_id: int) -> bool:
    if book.author and book.author.user_id == user_id:
        return True
    bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
    buyer_id = bp_user.id if bp_user else None
    purchases = BookPurchase.query.filter(
        db.or_(
            BookPurchase.buyer_user_id == user_id,
            (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false(),
        ),
        BookPurchase.book_project_id == book.id,
        BookPurchase.status == TransactionStatus.COMPLETED,
    ).all()
    return any(
        getattr(p, 'purchase_format', 'digital') in ('digital', 'bundle') for p in purchases
    )


def _reader_annotation_to_dict(a: ReaderAnnotation) -> dict:
    return {
        'id': a.id,
        'section_index': a.section_index,
        'start_offset': a.start_offset,
        'end_offset': a.end_offset,
        'quote_text': a.quote_text,
        'note_text': a.note_text,
        'kind': a.kind,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'updated_at': a.updated_at.isoformat() if a.updated_at else None,
    }


def _delete_reader_annotations_for_user_book(user_id: int, book_project_id: int) -> None:
    """Remove persisted library-reader highlights/bookmarks for one buyer + title."""
    ReaderAnnotation.query.filter_by(
        user_id=user_id,
        book_project_id=book_project_id,
    ).delete(synchronize_session=False)


def _delete_reader_annotations_for_book(book_project_id: int) -> None:
    """Remove all reader annotations when a book is deleted (all buyers)."""
    ReaderAnnotation.query.filter_by(book_project_id=book_project_id).delete(synchronize_session=False)


def resolved_audiobook_chapter_disk_path(chapter) -> Optional[str]:
    """Resolve AudiobookChapter.audio_file_path to an existing filesystem path."""
    p = (getattr(chapter, "audio_file_path", None) or "").strip()
    if not p:
        return None
    if os.path.isabs(p) and os.path.exists(p):
        return p
    static_root = os.path.join(current_app.root_path, "static")
    if p.startswith(static_root) and os.path.exists(p):
        return p
    rel = p.lstrip("/")
    cand = os.path.join(static_root, rel)
    if os.path.exists(cand):
        return cand
    if os.path.exists(p):
        return p
    return None


def save_book_cover_file(file_storage):
    """
    Persist an uploaded cover to static/book_covers/.
    Returns a relative path suitable for BookProject.cover_image, or None if invalid.
    """
    if not file_storage or not getattr(file_storage, 'filename', None):
        return None
    if not allowed_image_file(file_storage.filename):
        return None
    covers_dir = os.path.join(current_app.root_path, 'static', 'book_covers')
    os.makedirs(covers_dir, exist_ok=True)
    cover_filename = secure_filename(file_storage.filename)
    cover_name, cover_ext = os.path.splitext(cover_filename)
    unique_cover_filename = f"{cover_name}_{uuid.uuid4().hex[:8]}{cover_ext}"
    abs_path = os.path.join(covers_dir, unique_cover_filename)
    file_storage.save(abs_path)
    return f"book_covers/{unique_cover_filename}"


# Import performance optimizations
from .database_optimizer import DatabaseOptimizer, QueryCache, cache_result
# from .performance_optimizer import MemoryManager, memory_monitor

# Add memory monitoring to key functions (temporarily disabled)
# @memory_monitor
def get_user_profile():
    """Ink Studio profile (BookPlatformUser) first; legacy Writer row as fallback."""
    if not current_user.is_authenticated:
        return None, None

    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if book_user:
        return book_user, 'book_platform'

    writer = Writer.query.filter_by(user_id=current_user.user_id).first()
    if writer:
        return writer, 'writer'

    return None, None

def _profile_for_ink_permission_checks():
    """Writer, BookPlatformUser, or freelancer stub — mirrors writer_or_book_platform_required (non-admin)."""
    if current_user.role == 'freelancer':
        class FreelancerProfile:
            def __init__(self, user):
                self.id = user.user_id
                self.user_id = user.user_id
                self.pen_name = user.username
                self.bio = None
                self.profile_picture = None

        return FreelancerProfile(current_user), 'freelancer'
    return get_user_profile()

def get_profile_id(user_profile, profile_type):
    """Get the correct ID based on profile type - returns BookPlatformUser.id for consistency"""
    try:
        if profile_type == 'book_platform':
            return user_profile.id
        elif profile_type == 'writer':
            # For writers, always use BookPlatformUser.id since books are stored with that as author_id
            if not current_user or not current_user.is_authenticated:
                print(f"ERROR: current_user not authenticated in get_profile_id")
                return None
            
            # Query for existing BookPlatformUser
            bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
            if bp_user:
                # Sync pen_name, bio, and profile_picture from Writer profile if they differ
                needs_update = False
                if bp_user.pen_name != user_profile.writer_name:
                    bp_user.pen_name = user_profile.writer_name
                    needs_update = True
                if bp_user.bio != (user_profile.bio or ""):
                    bp_user.bio = user_profile.bio or ""
                    needs_update = True
                if user_profile.profile_picture and bp_user.profile_picture != user_profile.profile_picture:
                    bp_user.profile_picture = user_profile.profile_picture
                    needs_update = True
                
                if needs_update:
                    db.session.commit()
                    print(f"INFO: Synced BookPlatformUser (id={bp_user.id}) with Writer profile changes")
                
                return bp_user.id
            else:
                # Create BookPlatformUser if it doesn't exist
                # Use the imported class directly to avoid any scoping issues
                new_bp_user = BookPlatformUser(
                    user_id=current_user.user_id,
                    pen_name=user_profile.writer_name,
                    bio=user_profile.bio or "",
                    profile_picture=user_profile.profile_picture or "static/uploads/default_writer.jpg"
                )
                db.session.add(new_bp_user)
                db.session.commit()
                print(f"INFO: Created new BookPlatformUser with id={new_bp_user.id} for user_id={current_user.user_id}")
                return new_bp_user.id
        elif profile_type == 'temp':
            return user_profile.user_id
        else:
            print(f"ERROR: Unknown profile_type={profile_type} in get_profile_id")
            return None
    except Exception as e:
        print(f"ERROR in get_profile_id: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def ink_studio_home_url():
    """Role-appropriate Ink Studio home — readers go to My library, not author profile setup."""
    from glconnect.ink_studio_v1 import ink_v1_books_launch

    if not current_user.is_authenticated:
        return url_for('book_platform.marketplace')
    if ink_v1_books_launch():
        if getattr(current_user, 'role', None) == 'author':
            if _author_requires_setup_profile(current_user.user_id):
                return url_for('book_platform.setup_profile')
        return url_for('book_platform.marketplace')
    role = getattr(current_user, 'role', None)
    if role == 'artist':
        return url_for('book_platform.music_dashboard')
    if role == 'freelancer':
        return url_for('book_platform.dashboard')
    if role == 'blogger':
        return url_for('blog.blogs')
    if role == 'podcaster':
        return url_for('book_platform.content_hub')
    if role == 'author':
        if _author_requires_setup_profile(current_user.user_id):
            return url_for('book_platform.setup_profile')
        return url_for('book_platform.books')
    if ink_studio_show_author_nav_links():
        return url_for('book_platform.books')
    return url_for('book_platform.my_library')


def ink_studio_show_author_nav_links():
    """My Books / Payout account in shared nav — same rules as dashboard ``is_author``."""
    if not current_user.is_authenticated:
        return False
    excluded_roles = ['podcaster', 'freelancer', 'blogger', 'artist', 'other']
    if current_user.role in excluded_roles:
        return False
    user_profile, profile_type = get_user_profile()
    if profile_type not in ('writer', 'book_platform') or not user_profile:
        return False
    author_id = get_profile_id(user_profile, profile_type)
    has_authored_books = (
        BookProject.query.filter_by(author_id=author_id).count() > 0 if author_id else False
    )
    if current_user.role == 'author' and profile_type in ('writer', 'book_platform'):
        return True
    if has_authored_books:
        return True
    return False


def count_words_from_html(html_content):
    """Count words from HTML content by stripping HTML tags first"""
    if not html_content:
        return 0
    try:
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        # Strip HTML entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Split on whitespace and count non-empty words
        words = [w for w in text.split() if w.strip()]
        return len(words)
    except Exception as e:
        # Fallback to simple split if regex fails
        logging.error(f"Error counting words from HTML: {e}")
        return len(html_content.split())

def update_book_word_count(book):
    """Recalculate and update the book's total word count from all chapters.

    IMPORTANT:
    - For books created inside the platform (with chapters), the word count
      comes from summing chapter contents.
    - For uploaded digital books (with a digital file and no chapters),
      the word count is taken from the digital file extraction process and
      should NOT be overwritten here.
    """
    try:
        # If this is an uploaded digital book (has a digital file path) and
        # there are no platform chapters, keep the existing word_count.
        # That value is set when the digital file is processed.
        try:
            has_digital_file = bool(getattr(book, "digital_file_path", None))
            has_chapters = bool(getattr(book, "chapters", None))
        except Exception:
            has_digital_file = False
            has_chapters = False

        if has_digital_file and not has_chapters:
            # Do not override the word count that came from the uploaded file
            return book.word_count or 0

        # Otherwise (platform-created books with chapters), recalculate from chapters
        total_words = 0
        for chapter in book.chapters:
            try:
                # If chapter word count is missing or 0 but has content, calculate it
                if (not chapter.word_count or chapter.word_count == 0) and chapter.content:
                    chapter.word_count = count_words_from_html(chapter.content)
                # Recalculate if content exists (to ensure accuracy)
                elif chapter.content:
                    chapter.word_count = count_words_from_html(chapter.content)
                total_words += chapter.word_count or 0
            except Exception as e:
                logging.error(f"Error calculating word count for chapter {chapter.id}: {e}")
                # Use existing word count if calculation fails
                total_words += chapter.word_count or 0

        book.word_count = int(total_words)
        return book.word_count
    except Exception as e:
        logging.error(f"Error updating book word count for book {book.id}: {e}")
        # Return existing word count if update fails
        return book.word_count or 0

def check_investment_readiness(book):
    """Check if a book is ready for investment and return readiness status.
    Campaigns apply only to books created on the platform (with chapters), not to uploaded digital books."""
    issues = []
    
    if not book.title or len(book.title.strip()) < 3:
        issues.append("Book must have a title (at least 3 characters)")
    if not book.description or project_description_plain_length(book.description) < PROJECT_DESCRIPTION_MIN_PLAIN_CHARS:
        issues.append("Book must have a description (at least 50 characters)")
    if not book.genre:
        issues.append("Book must have a genre selected")
    if not book.language:
        issues.append("Book must have a language selected")
    
    # Campaigns only for platform-created books (with chapters), not uploaded digital books
    try:
        has_digital_file = bool(getattr(book, "digital_file_path", None))
        chapter_count = len(book.chapters) if book.chapters else 0
    except Exception as e:
        logging.error(f"Error accessing chapters for book {book.id}: {e}")
        has_digital_file = False
        chapter_count = 0
    
    if has_digital_file and chapter_count == 0:
        issues.append("Book campaigns are only available for books created on the platform (with chapters), not for uploaded digital books.")
    elif chapter_count == 0:
        issues.append("Book must have at least one chapter")
    
    # Ensure word count is up to date before checking
    try:
        update_book_word_count(book)
    except Exception as e:
        logging.error(f"Error updating word count in check_investment_readiness for book {book.id}: {e}")
        # Continue with existing word count
    
    # Check if book has some content (word count)
    if book.word_count < 1000:
        issues.append("Book should have at least 1,000 words of content")
    
    return {
        'is_ready': len(issues) == 0,
        'issues': issues,
        'chapter_count': chapter_count,
        'word_count': book.word_count or 0
    }


_CONTRIBUTION_BACKER_STATUSES = (
    InvestmentStatus.CONFIRMED,
    InvestmentStatus.ACTIVE,
    InvestmentStatus.COMPLETED,
)


def campaign_backer_counts(campaign_ids):
    """Distinct patron count per campaign (confirmed/active/completed contributions only)."""
    if not campaign_ids:
        return {}
    from sqlalchemy import func

    rows = (
        db.session.query(
            BookInvestment.campaign_id,
            func.count(func.distinct(BookInvestment.investor_id)),
        )
        .filter(
            BookInvestment.campaign_id.in_(campaign_ids),
            BookInvestment.status.in_(_CONTRIBUTION_BACKER_STATUSES),
        )
        .group_by(BookInvestment.campaign_id)
        .all()
    )
    return {cid: cnt for cid, cnt in rows}


def saved_campaign_ids_for_user(user_id):
    """Campaign IDs the user saved to return to later."""
    if not user_id:
        return set()
    rows = SavedBookCampaign.query.filter_by(user_id=user_id).all()
    return {r.campaign_id for r in rows}


def writer_or_book_platform_required(f):
    """Decorator that requires Writer profile (primary) or BookPlatformUser profile (legacy) for Ink Studio access.
    Also allows freelancers to access with limited features."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('routes1.login', next=request.path))

        from glconnect.ink_studio_v1 import ink_v1_books_launch

        if ink_v1_books_launch() and current_user.role == 'freelancer':
            flash('Complete an author profile to list books or start book campaigns.', 'warning')
            return redirect(url_for('book_platform.setup_profile', next=request.path))
        
        # Allow freelancers to access with a temporary profile
        if current_user.role == 'freelancer' and not ink_v1_books_launch():
            class FreelancerProfile:
                def __init__(self, user):
                    self.id = user.user_id
                    self.user_id = user.user_id
                    self.pen_name = user.username
                    self.bio = None
                    self.profile_picture = None
            
            kwargs['user_profile'] = FreelancerProfile(current_user)
            kwargs['profile_type'] = 'freelancer'
            return f(*args, **kwargs)
        
        user_profile, profile_type = get_user_profile()
        if not user_profile:
            flash('Complete your Ink Studio author profile to access this area.', 'warning')
            return redirect(url_for('book_platform.setup_profile', next=request.path))
        
        # Add profile info to kwargs for use in the function
        kwargs['user_profile'] = user_profile
        kwargs['profile_type'] = profile_type
        
        return f(*args, **kwargs)
    return decorated_function

def integrated_auth_required(f):
    """Decorator that accepts both Writer and BookPlatformUser profiles (legacy name)"""
    return writer_or_book_platform_required(f)

def book_platform_required(f):
    """Decorator to ensure user has Ink Studio profile (legacy - for backward compatibility)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('routes1.login', next=request.path))
        
        # Check if user has Ink Studio profile
        book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_user:
            flash(
                'Complete your Ink Studio author profile before listing a book on the marketplace.',
                'warning',
            )
            return redirect(url_for('book_platform.setup_profile', next=request.path))
        
        return f(*args, **kwargs)
    return decorated_function

def collaboration_required(f):
    """Decorator to ensure user has collaboration access to book"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        book_id = kwargs.get('book_id')
        if not book_id:
            return jsonify({'error': 'Book ID required'}), 400

        book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_user:
            return jsonify({'error': 'Ink Studio profile required'}), 403

        book = BookProject.query.get_or_404(book_id)
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id,
            collaborator_id=book_user.id,
            is_active=True,
        ).first()

        if book.author_id != book_user.id and not collaboration:
            return jsonify({'error': 'Access denied'}), 403

        return f(*args, **kwargs)
    return decorated_function


def _user_can_view_chapter_history(book, book_user_id):
    if book.author_id == book_user_id:
        return True
    return BookCollaboration.query.filter_by(
        book_project_id=book.id,
        collaborator_id=book_user_id,
        is_active=True,
    ).first() is not None


@book_bp.route('/ink-studio')
def ink_studio_access():
    """Ink Studio access point - redirects to login if not authenticated, otherwise redirects based on role."""
    from glconnect.ink_studio_v1 import ink_v1_books_launch, ink_v1_role_redirect

    # If not authenticated, redirect to login (which has register link)
    if not current_user.is_authenticated:
        return redirect(url_for('routes1.login', next=url_for('book_platform.ink_studio_access')))

    if ink_v1_books_launch():
        return ink_v1_role_redirect(current_user)

    # User is authenticated - redirect based on role
    user_role = getattr(current_user, 'role', None)
    
    # Artist users → music dashboard
    if user_role == 'artist':
        return redirect(url_for('book_platform.music_dashboard'))
    
    # Author users → Ink Studio setup-profile until author card is complete
    elif user_role == 'author':
        if _author_requires_setup_profile(current_user.user_id):
            return redirect(url_for('book_platform.setup_profile'))
        return redirect(url_for('book_platform.books'))
    
    # Freelancer users → blogs
    elif user_role == 'freelancer':
        return redirect(url_for('blog.blogs'))
    
    # Blogger users → blogs
    elif user_role == 'blogger':
        return redirect(url_for('blog.blogs'))
    
    # All other users → content page
    else:
        return redirect(url_for('book_platform.content_hub'))

# Main dashboard route
@book_bp.route('/')
@login_required
def dashboard():
    """Ink Studio entry — role-based home; readers without author profiles go to My library."""
    from glconnect.ink_studio_v1 import ink_v1_books_launch

    if ink_v1_books_launch():
        if getattr(current_user, 'role', None) == 'author':
            if _author_requires_setup_profile(current_user.user_id):
                return redirect(url_for('book_platform.setup_profile'))
        return redirect(url_for('book_platform.marketplace'))

    role = getattr(current_user, 'role', None)

    if role == 'artist':
        return redirect(url_for('book_platform.music_dashboard'))

    if role == 'freelancer':
        from glconnect.models import Post

        class FreelancerProfile:
            def __init__(self, user):
                self.id = user.user_id
                self.user_id = user.user_id
                self.pen_name = user.username
                self.bio = None
                self.profile_picture = None

        freelancer_stories = (
            Post.query.filter_by(user_id=current_user.user_id)
            .order_by(Post.date_posted.desc())
            .limit(10)
            .all()
        )
        fp = FreelancerProfile(current_user)
        return render_template(
            'book_platform/dashboard.html',
            authored_books=[],
            collaborations=[],
            notifications=[],
            user_profile=fp,
            profile_type='freelancer',
            is_author=False,
            investment_campaigns=[],
            review_requests=[],
            user_reviewer_profile=None,
            user_investments=[],
            freelancer_stories=freelancer_stories,
            is_freelancer=True,
            marketplace_cover_url=_marketplace_cover_url,
            ink_nav_active='dashboard',
        )

    user_profile, profile_type = get_user_profile()

    if role == 'author':
        if _author_requires_setup_profile(current_user.user_id):
            return redirect(url_for('book_platform.setup_profile'))
        return redirect(url_for('book_platform.books'))

    if profile_type in ('writer', 'book_platform') and user_profile and ink_studio_show_author_nav_links():
        return redirect(url_for('book_platform.books'))

    if role == 'blogger':
        return redirect(url_for('blog.blogs'))

    if role == 'podcaster':
        return redirect(url_for('book_platform.content_hub'))

    return redirect(url_for('book_platform.my_library'))


@book_bp.route('/api/dashboard/author-stats', methods=['GET'])
@writer_or_book_platform_required
def api_author_dashboard_stats(user_profile, profile_type):
    """Live JSON stats for author dashboard (sales, downloads, engagement)."""
    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        return jsonify({'success': False, 'error': 'Author profile required'}), 403
    try:
        payload = build_author_dashboard_stats(author_id)
        payload['updated_at'] = datetime.now(timezone.utc).isoformat()
        return jsonify({'success': True, **payload})
    except Exception as exc:
        logger.error("api_author_dashboard_stats: %s", exc, exc_info=True)
        return jsonify({'success': False, 'error': 'Could not load stats'}), 500


@book_bp.route('/my-listings')
@writer_or_book_platform_required
def author_my_listings(user_profile, profile_type):
    """Merged into /mybook/books; keep URL for bookmarks and external links."""
    return redirect(url_for('book_platform.books'), code=301)


# Profile setup
@book_bp.route('/setup-profile', methods=['GET', 'POST'])
@login_required
def setup_profile():
    """Setup Ink Studio profile (optional bio, photo, website for marketplace author card)."""
    if request.method == 'POST':
        try:
            is_multipart = request.content_type and 'multipart/form-data' in request.content_type
            profile_pic_file = None
            if is_multipart:
                pen_name = request.form.get('pen_name')
                bio = request.form.get('bio')
                website_raw = request.form.get('website')
                writing_experience = request.form.get('writing_experience')
                try:
                    social_links = json.loads(request.form.get('social_links') or '{}')
                except json.JSONDecodeError:
                    social_links = {}
                if not isinstance(social_links, dict):
                    social_links = {}
                profile_pic_file = request.files.get('profile_picture')
            else:
                data = request.get_json() or {}
                pen_name = data.get('pen_name')
                bio = data.get('bio')
                website_raw = data.get('website')
                writing_experience = data.get('writing_experience')
                social_links = data.get('social_links', {})
                if not isinstance(social_links, dict):
                    social_links = {}

            website_norm = _normalize_public_website(website_raw)
            if str(website_raw or '').strip() and website_norm is None:
                return jsonify({
                    'success': False,
                    'error': 'Enter a valid website URL (e.g. yourname.com or https://yourname.com).',
                }), 400

            pen_name_clean = (pen_name or '').strip() or None
            bio_clean = (bio or '').strip() or None
            we_stored = website_norm

            existing_profile = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()

            if profile_pic_file and profile_pic_file.filename:
                if not allowed_image_file(profile_pic_file.filename):
                    return jsonify({
                        'success': False,
                        'error': 'Profile picture must be PNG, JPG, JPEG, GIF, WebP, or SVG.',
                    }), 400
                upload_dir = os.path.join(current_app.root_path, 'static', 'writer_uploads')
                os.makedirs(upload_dir, exist_ok=True)
                base_fn = secure_filename(profile_pic_file.filename)
                stem, ext = os.path.splitext(base_fn)
                unique_fn = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
                profile_pic_file.save(os.path.join(upload_dir, unique_fn))
                pic_rel = f"writer_uploads/{unique_fn}"
            else:
                pic_rel = None

            if existing_profile:
                existing_profile.pen_name = pen_name_clean
                existing_profile.bio = bio_clean
                existing_profile.website = we_stored
                existing_profile.social_links = social_links
                existing_profile.writing_experience = (writing_experience or '').strip() or None
                if pic_rel:
                    existing_profile.profile_picture = pic_rel
                existing_profile.updated_at = datetime.now(timezone.utc)
                existing_profile.author_card_setup_completed = True
            else:
                book_user = BookPlatformUser(
                    user_id=current_user.user_id,
                    pen_name=pen_name_clean,
                    bio=bio_clean,
                    website=we_stored,
                    social_links=social_links,
                    writing_experience=(writing_experience or '').strip() or None,
                    profile_picture=pic_rel,
                    author_card_setup_completed=True,
                )
                db.session.add(book_user)

            db.session.commit()

            bp = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
            redirect_url = _safe_next_url_for_profile_setup(request)
            if bp and author_requires_publishing_agreement(current_user.user_id, bp):
                redirect_url = url_for(
                    'book_platform.author_publishing_agreement',
                    next=redirect_url,
                )
            return jsonify({'success': True, 'redirect': redirect_url})

        except Exception as e:
            db.session.rollback()
            print(f"Profile setup error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    next_after = _setup_profile_next_query_param()
    is_collaborator_setup = '/invitations/' in next_after
    return render_template(
        'book_platform/setup_profile.html',
        book_user=book_user,
        next_after_setup=next_after,
        is_collaborator_setup=is_collaborator_setup,
        **agreement_context_for_templates(),
    )


@book_bp.route('/author-publishing-agreement', methods=['GET', 'POST'])
@login_required
def author_publishing_agreement():
    """Account-level Author Publishing Agreement — accept once (re-accept on version bump)."""
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not bp_user:
        flash('Complete your author profile first.', 'warning')
        return redirect(url_for('book_platform.setup_profile', next=request.path))

    next_url = safe_mybook_next_path(
        request.args.get('next') or request.form.get('next'),
        url_for('book_platform.books'),
    )

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        if not data.get('author_agreement_accept'):
            return jsonify({'success': False, 'error': 'You must accept the agreement to continue.'}), 400
        try:
            record_author_agreement_acceptance(bp_user)
            db.session.commit()
            return jsonify({'success': True, 'redirect': next_url})
        except Exception as e:
            db.session.rollback()
            logger.error('author agreement acceptance failed: %s', e, exc_info=True)
            return jsonify({'success': False, 'error': 'Could not save acceptance. Please try again.'}), 500

    ctx = agreement_context_for_templates()
    ctx.update({
        'next_url': next_url,
        'already_accepted': author_has_accepted_agreement(bp_user),
        'accepted_at': getattr(bp_user, 'author_agreement_accepted_at', None),
    })
    return render_template('book_platform/author_publishing_agreement.html', **ctx)

# Book management routes
@book_bp.route('/books')
@writer_or_book_platform_required
def books(user_profile, profile_type):
    """Author hub: all projects, marketplace listing status, sales, analytics, and investment tools."""
    from glconnect.book_platform_models import BookPlatformUser, InvestmentCampaign

    if profile_type == 'freelancer':
        flash('Listing and writing books in Ink Studio is for authors. Freelancers can publish stories from Content hub.', 'info')
        return redirect(url_for('book_platform.content_hub'))

    if _author_needs_marketplace_profile_step():
        flash(
            'Complete your author profile (Ink Studio author card) before managing or listing books.',
            'warning',
        )
        return redirect(url_for('book_platform.setup_profile', next=request.path))

    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        flash('Complete your Ink Studio profile to manage books.', 'warning')
        return redirect(url_for('book_platform.setup_profile', next=request.path))

    if profile_type != 'writer':
        authored_books_count = BookProject.query.filter_by(author_id=author_id).count()
        if authored_books_count == 0 and current_user.role not in ('author',):
            flash('Create your first book to get started.', 'info')
            return redirect(url_for('book_platform.create_book'))

    books_q = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).filter_by(author_id=author_id).order_by(
        BookProject.updated_at.desc(),
        BookProject.created_at.desc(),
    ).all()

    book_ids = [b.id for b in books_q]
    sale_by_book = {}
    if book_ids:
        sale_rows = db.session.query(
            BookSale.book_project_id,
            func.count(BookSale.id),
            func.coalesce(func.sum(BookSale.net_amount), 0.0),
        ).filter(
            BookSale.book_project_id.in_(book_ids),
            BookSale.status == TransactionStatus.COMPLETED,
        ).group_by(BookSale.book_project_id).all()
        for row in sale_rows:
            sale_by_book[row[0]] = {
                'completed_units': int(row[1] or 0),
                'author_net': float(row[2] or 0),
            }

    analytics_by_book = {}
    if book_ids:
        analytics_rows = db.session.query(
            BookAnalytics.book_project_id,
            func.coalesce(func.sum(BookAnalytics.views), 0),
            func.coalesce(func.sum(BookAnalytics.downloads), 0),
            func.coalesce(func.sum(BookAnalytics.purchases), 0),
        ).filter(
            BookAnalytics.book_project_id.in_(book_ids)
        ).group_by(BookAnalytics.book_project_id).all()
        for row in analytics_rows:
            analytics_by_book[row[0]] = {
                'views': int(row[1] or 0),
                'downloads': int(row[2] or 0),
                'purchases': int(row[3] or 0),
            }

    listing_stats = {}
    for book in books_q:
        s = sale_by_book.get(book.id, {'completed_units': 0, 'author_net': 0.0})
        a = analytics_by_book.get(book.id, {'views': 0, 'downloads': 0, 'purchases': 0})
        listing_stats[book.id] = {
            'live': is_book_published(book),
            'completed_sales': s['completed_units'],
            'author_earnings': s['author_net'],
            'agg_views': a['views'],
            'agg_downloads': a['downloads'],
            'agg_purchases': a['purchases'],
        }

    summary_live = sum(1 for b in books_q if listing_stats[b.id]['live'])
    summary_units = sum(listing_stats[b.id]['completed_sales'] for b in books_q)
    summary_earnings = sum(listing_stats[b.id]['author_earnings'] for b in books_q)
    summary_views = sum(listing_stats[b.id]['agg_views'] for b in books_q)
    summary_downloads = sum(listing_stats[b.id]['agg_downloads'] for b in books_q)

    author_dashboard_stats = None
    try:
        author_dashboard_stats = build_author_dashboard_stats(author_id)
    except Exception as stats_exc:
        logger.warning("Books page author stats failed: %s", stats_exc)

    book_campaigns = {}
    for book in books_q:
        if book.has_investment_campaign:
            campaign = InvestmentCampaign.query.filter_by(book_project_id=book.id).first()
            if campaign:
                book_campaigns[book.id] = campaign

    books_with_readiness = []
    for book in books_q:
        lst = listing_stats[book.id]
        try:
            readiness = check_investment_readiness(book)
            books_with_readiness.append({
                'book': book,
                'investment_readiness': readiness,
                'listing': lst,
            })
        except Exception as e:
            logger.error(f"Error processing book {book.id} for investment readiness: {str(e)}", exc_info=True)
            books_with_readiness.append({
                'book': book,
                'investment_readiness': {
                    'is_ready': False,
                    'issues': [f'Error checking readiness: {str(e)}'],
                    'chapter_count': 0,
                    'word_count': 0,
                },
                'listing': lst,
            })

    return render_template(
        'book_platform/books.html',
        books_with_readiness=books_with_readiness,
        book_campaigns=book_campaigns,
        summary_live=summary_live,
        summary_total_books=len(books_q),
        summary_units=summary_units,
        summary_earnings=summary_earnings,
        summary_views=summary_views,
        summary_downloads=summary_downloads,
        author_dashboard_stats=author_dashboard_stats,
        is_author=True,
        ink_nav_active='books',
        marketplace_cover_url=_marketplace_cover_url,
        author_needs_publishing_agreement=_author_needs_publishing_agreement(current_user.user_id),
    )

@book_bp.route('/books/create', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_book(user_profile, profile_type):
    """Create a new book project - Writer profiles are primary users"""
    # Note: We allow access here to enable first-time book creation
    # The dashboard template will hide the "Start Writing" button for non-authors
    # This allows Writer profiles to create books immediately
    if profile_type == 'freelancer':
        flash('Listing and writing books in Ink Studio is for authors. Freelancers can publish stories from the dashboard.', 'info')
        return redirect(url_for('book_platform.dashboard'))

    if _author_needs_marketplace_profile_step():
        flash(
            'Complete your author profile (Ink Studio author card) before creating a new book.',
            'warning',
        )
        if request.method == 'POST':
            return jsonify({
                'success': False,
                'error': 'Complete your author profile first.',
                'redirect': url_for('book_platform.setup_profile', next=request.path),
            }), 403
        return redirect(url_for('book_platform.setup_profile', next=request.path))

    if _author_needs_publishing_agreement(current_user.user_id):
        flash('Accept the Author Publishing Agreement before creating or listing books.', 'warning')
        if request.method == 'POST':
            return jsonify({
                'success': False,
                'error': 'Accept the Author Publishing Agreement first.',
                'redirect': url_for('book_platform.author_publishing_agreement', next=request.path),
            }), 403
        return _redirect_to_publishing_agreement(request.path)

    if request.method == 'POST':
        author_id = get_profile_id(user_profile, profile_type)
        if not author_id:
            return jsonify({'success': False, 'error': 'Could not resolve author profile.'}), 400

        # Require multipart upload so authors choose a cover at creation time
        if not request.content_type or 'multipart/form-data' not in request.content_type:
            return jsonify({
                'success': False,
                'error': 'Submit the form as multipart (cover file or AI cover).'
            }), 400

        title = (request.form.get('title') or '').strip()
        if not title:
            return jsonify({'success': False, 'error': 'Book title is required.'}), 400

        language = (request.form.get('language') or '').strip()
        if not language:
            return jsonify({'success': False, 'error': 'Please select a language for your book.'}), 400

        genre_val = (request.form.get('genre') or '').strip()
        raw_description = (request.form.get('description') or '').strip()
        try:
            desc_val = sanitize_project_description(raw_description, book_id=None) if raw_description else None
        except ProjectDescriptionError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
        use_ai_cover = request.form.get('use_ai_cover') == 'on'
        art_brief = (request.form.get('cover_art_brief') or '').strip()

        covers_dir = os.path.join(current_app.root_path, 'static', 'book_covers')
        os.makedirs(covers_dir, exist_ok=True)

        cover_file = request.files.get('cover_image')
        has_cover_file = bool(cover_file and getattr(cover_file, 'filename', None))
        cover_rel = None

        if has_cover_file:
            cover_rel = save_book_cover_file(cover_file)
            if not cover_rel:
                return jsonify({
                    'success': False,
                    'error': 'Invalid cover image. Use PNG, JPG, GIF, WebP, or SVG.'
                }), 400
        elif use_ai_cover:
            cover_rel = promote_listing_preview_to_cover()
            if not cover_rel:
                return jsonify({
                    'success': False,
                    'error': (
                        'Generate an AI cover preview and choose “Use this cover” before creating the book, '
                        'or upload a cover image instead.'
                    ),
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'Upload a cover image or choose Generate with AI and confirm a preview.',
            }), 400

        book = BookProject(
            title=title,
            description=desc_val,
            genre=(request.form.get('genre') or '').strip() or None,
            language=language,
            target_audience=(request.form.get('target_audience') or '').strip() or None,
            author_id=author_id,
            cover_image=cover_rel,
        )

        db.session.add(book)
        db.session.commit()

        return jsonify({'success': True, 'book_id': book.id})

    return render_template('book_platform/create_book.html')


def _ai_cover_preview_form_dict():
    if request.is_json:
        j = request.get_json(silent=True) or {}
    else:
        j = request.form.to_dict()
    return {
        "title": (j.get("title") or "").strip(),
        "description": (j.get("description") or "").strip(),
        "genre": (j.get("genre") or "").strip(),
        "cover_art_brief": (j.get("cover_art_brief") or j.get("art_brief") or "").strip(),
    }


def _author_display_name_for_cover(user_profile, profile_type, book=None):
    """Pen name (or username) used as author typography on AI-generated covers."""
    if book is not None:
        author = getattr(book, "author", None)
        if author:
            if getattr(author, "pen_name", None):
                return author.pen_name.strip()
            if getattr(author, "user", None) and author.user.username:
                return author.user.username.strip()
    if profile_type == "book_platform" and getattr(user_profile, "pen_name", None):
        return user_profile.pen_name.strip()
    if profile_type == "writer" and getattr(user_profile, "writer_name", None):
        return user_profile.writer_name.strip()
    if profile_type == "freelancer" and getattr(user_profile, "pen_name", None):
        return user_profile.pen_name.strip()
    if current_user.is_authenticated and current_user.username:
        return current_user.username.strip()
    return "Author"


@book_bp.route("/ai-cover-preview/listing", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_listing(user_profile, profile_type):
    """Generate a temporary AI cover for listing / create-book flows; user must accept before submit."""
    payload = _ai_cover_preview_form_dict()
    title = payload["title"]
    if len(title) < 1:
        return jsonify(success=False, error="Enter a title first, then generate a cover preview."), 400
    author_name = _author_display_name_for_cover(user_profile, profile_type)
    ai_res = generate_book_cover_bytes(
        title,
        payload["description"],
        payload["genre"],
        payload["cover_art_brief"],
        author_name=author_name,
    )
    if not ai_res.get("success") or not ai_res.get("image_bytes"):
        return jsonify(
            success=False,
            error=ai_res.get("error") or "Could not generate a cover preview. Try again or adjust your details.",
        ), 400
    save_listing_preview(ai_res["image_bytes"])
    preview_url = url_for("book_platform.ai_cover_preview_listing_image")
    return jsonify(success=True, preview_url=preview_url)


@book_bp.route("/ai-cover-preview/listing/image")
@writer_or_book_platform_required
def ai_cover_preview_listing_image(user_profile, profile_type):
    rel = listing_preview_image_rel()
    if not rel:
        abort(404)
    directory, fname = os.path.split(rel.replace("\\", "/"))
    return send_from_directory(
        os.path.join(current_app.root_path, "static", directory),
        fname,
        mimetype="image/png",
    )


@book_bp.route("/ai-cover-preview/listing/accept", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_listing_accept(user_profile, profile_type):
    if not set_listing_preview_accepted(True):
        return jsonify(success=False, error="No preview to accept. Generate a cover first."), 400
    return jsonify(success=True, preview_url=url_for("book_platform.ai_cover_preview_listing_image"))


@book_bp.route("/ai-cover-preview/listing/reject", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_listing_reject(user_profile, profile_type):
    clear_listing_preview()
    return jsonify(success=True)


@book_bp.route("/books/<int:book_id>/ai-cover-preview", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_for_book(book_id, user_profile, profile_type):
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if author_id is None or book.author_id != author_id:
        return jsonify(success=False, error="Only the author can update this cover."), 403
    payload = _ai_cover_preview_form_dict()
    title = payload["title"] or (book.title or "").strip()
    if len(title) < 1:
        return jsonify(success=False, error="Add a book title before generating a cover preview."), 400
    desc = payload["description"] or (book.description or "")
    genre = payload["genre"] or (book.genre or "")
    brief = payload["cover_art_brief"]
    author_name = _author_display_name_for_cover(user_profile, profile_type, book=book)
    ai_res = generate_book_cover_bytes(
        title,
        desc,
        genre,
        brief,
        author_name=author_name,
    )
    if not ai_res.get("success") or not ai_res.get("image_bytes"):
        return jsonify(
            success=False,
            error=ai_res.get("error") or "Could not generate a cover preview. Try again.",
        ), 400
    save_edit_preview(book_id, ai_res["image_bytes"])
    preview_url = url_for("book_platform.ai_cover_preview_edit_image", book_id=book_id)
    return jsonify(success=True, preview_url=preview_url)


@book_bp.route("/books/<int:book_id>/ai-cover-preview/image")
@writer_or_book_platform_required
def ai_cover_preview_edit_image(book_id, user_profile, profile_type):
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if author_id is None or book.author_id != author_id:
        abort(403)
    rel = edit_preview_image_rel(book_id)
    if not rel:
        abort(404)
    directory, fname = os.path.split(rel.replace("\\", "/"))
    return send_from_directory(
        os.path.join(current_app.root_path, "static", directory),
        fname,
        mimetype="image/png",
    )


@book_bp.route("/books/<int:book_id>/ai-cover-preview/accept", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_edit_accept(book_id, user_profile, profile_type):
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if author_id is None or book.author_id != author_id:
        return jsonify(success=False, error="Only the author can update this cover."), 403
    new_rel = promote_edit_preview_to_cover(book_id)
    if not new_rel:
        return jsonify(
            success=False,
            error="No preview to apply. Generate a new cover first.",
        ), 400
    old = book.cover_image
    maybe_remove_local_cover_file(old)
    book.cover_image = new_rel
    book.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(
        success=True,
        cover_url=url_for("static", filename=new_rel),
        message="Cover updated.",
    )


@book_bp.route("/books/<int:book_id>/ai-cover-preview/reject", methods=["POST"])
@writer_or_book_platform_required
def ai_cover_preview_edit_reject(book_id, user_profile, profile_type):
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if author_id is None or book.author_id != author_id:
        return jsonify(success=False, error="Only the author can update this cover."), 403
    clear_edit_preview(book_id)
    return jsonify(success=True)


@book_bp.route('/books/<int:book_id>')
@writer_or_book_platform_required
def view_book(book_id, user_profile, profile_type):
    """View book details and chapters"""
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    
    # Eager load author information to ensure fresh data from database
    # Use the explicit author relationship (not backref) to avoid collection issues
    campaign = None  # Initialize outside try block
    try:
        from glconnect.book_platform_models import InvestmentCampaign
        book = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user),
            joinedload(BookProject.chapters),
        ).get_or_404(book_id)
        
        # Get investment campaign directly to avoid relationship issues
        if book.has_investment_campaign:
            campaign = InvestmentCampaign.query.filter_by(book_project_id=book_id).first()
        
        # Refresh the book object to ensure we have the latest data
        db.session.refresh(book)
        
        # Verify author is loaded correctly (should be a single object, not a collection)
        if not book.author:
            logger.error(f"Book {book_id} has no author loaded - author_id={book.author_id}")
            flash('Book author information could not be loaded.', 'error')
            return redirect(url_for('book_platform.books'))
    except Exception as load_error:
        logger.error(f"Error loading book {book_id}: {load_error}", exc_info=True)
        flash('Error loading book information.', 'error')
        return redirect(url_for('book_platform.books'))
    
    # Get the correct author_id
    author_id = get_profile_id(user_profile, profile_type)
    
    # Error handling for profile resolution
    if author_id is None:
        print(f"ERROR: get_profile_id returned None for user_id={current_user.user_id}, profile_type={profile_type} in view_book")
        flash('Profile configuration error. Please ensure you have a Writer or Ink Studio profile.', 'error')
        return redirect(url_for('book_platform.books'))
    
    # Check access
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    collaboration = None
    if bp_user:
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id, 
            collaborator_id=bp_user.id,
            is_active=True
        ).first()
    
    is_author = book.author_id == author_id
    is_collaborator = collaboration is not None
    
    if not is_author and not is_collaborator:
        flash('Access denied', 'error')
        return redirect(url_for('book_platform.books'))
    
    chapters = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number).all()
    # Eager load author info for collaborations
    collaborations = BookCollaboration.query.options(
        joinedload(BookCollaboration.collaborator).joinedload(BookPlatformUser.user)
    ).filter_by(book_project_id=book_id, is_active=True).all()
    
    # For uploaded digital books, ensure word count is populated at least once
    # from the uploaded file if it's still 0 or missing.
    try:
        if getattr(book, "digital_file_path", None) and (not book.word_count or book.word_count == 0):
            from glconnect import digital_book_processor
            import os
            from flask import current_app

            file_type = book.digital_file_type
            # Reconstruct full path inside static folder (e.g. "digital_books/filename.pdf")
            digital_rel_path = book.digital_file_path
            digital_full_path = os.path.join(current_app.static_folder, digital_rel_path)

            extraction_result = digital_book_processor.extract_text(digital_full_path, file_type)
            if extraction_result.get("success") and extraction_result.get("word_count") is not None:
                book.word_count = extraction_result["word_count"]
                db.session.commit()
    except Exception as extraction_error:
        logger.error(f"Error backfilling word count from digital file for book {book_id}: {extraction_error}", exc_info=True)
        # Continue anyway – we will still try to use chapter-based word count logic below.
    
    # Ensure book word count is up to date for platform-created books
    try:
        update_book_word_count(book)
        db.session.commit()
    except Exception as word_count_error:
        logger.error(f"Error updating word count for book {book_id}: {word_count_error}", exc_info=True)
        # Continue anyway - word count is not critical
    
    # Check investment readiness (it will call update_book_word_count again, but that's okay)
    try:
        investment_readiness = check_investment_readiness(book)
        # Ensure any changes from check_investment_readiness are committed
        db.session.commit()
    except Exception as readiness_error:
        logger.error(f"Error checking investment readiness for book {book_id}: {readiness_error}", exc_info=True)
        investment_readiness = None  # Set to None if check fails
    
    digital_download_options = []
    if book.digital_file_path:
        pl = (book.language or "en").lower()
        digital_download_options.append(
            {
                "lang": pl,
                "label": f"{language_label(pl)} — original ({(book.digital_file_type or 'file').upper()})",
                "ready": True,
                "url": url_for("book_platform.download_digital_book", book_id=book.id, lang=pl),
            }
        )

    latest_audio_task = None
    has_listing_cover = book_has_listing_cover(book)
    pending_invitation_count = 0
    if is_author:
        latest_audio_task = (
            AudioGenerationTask.query.filter_by(book_project_id=book_id)
            .order_by(AudioGenerationTask.created_at.desc())
            .first()
        )
        pending_invitation_count = (
            CollaborationInvitation.query.join(BookCollaboration)
            .filter(
                BookCollaboration.book_project_id == book_id,
                CollaborationInvitation.status == InvitationStatus.PENDING,
            )
            .count()
        )

    try:
        return render_template('book_platform/view_book.html', 
                             book=book, 
                             chapters=chapters,
                             collaborations=collaborations,
                             pending_invitation_count=pending_invitation_count,
                             is_author=is_author,
                             is_collaborator=is_collaborator,
                             investment_readiness=investment_readiness,
                             investment_campaign=campaign,
                             digital_download_options=digital_download_options,
                             has_listing_cover=has_listing_cover,
                             latest_audio_task=latest_audio_task)
    except Exception as template_error:
        logger.error(f"Error rendering view_book template for book {book_id}: {template_error}", exc_info=True)
        flash('Error loading book view. Please try again.', 'error')
        return redirect(url_for('book_platform.books'))

@book_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@writer_or_book_platform_required
def edit_book(book_id, user_profile, profile_type):
    """Edit book details"""
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    from sqlalchemy.orm import joinedload
    
    # Eager load author information to ensure fresh data from database
    # This ensures book.author is a single object, not a collection
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).get_or_404(book_id)
    
    # Verify author relationship is loaded correctly
    if not book.author:
        logger.error(f"Book {book_id} has no author loaded - author_id={book.author_id}")
        flash('Book author information could not be loaded.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # Debug logging
    if author_id is None:
        print(f"ERROR: get_profile_id returned None for user_id={current_user.user_id}, profile_type={profile_type}")
        flash('Profile configuration error. Please ensure you have a Writer or Ink Studio profile.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Only author can edit book details
    if book.author_id != author_id:
        print(f"Permission denied: book.author_id={book.author_id}, user author_id={author_id}, user_id={current_user.user_id}")
        flash('Only the author can edit book details', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            listing_flow_requested = str(data.get('listing_flow') or '').strip().lower() in (
                '1', 'true', 'yes', 'on'
            )

            _prev_digital_pub = book.digital_book_published
            _prev_audiobook_pub = book.audiobook_published
            _prev_status = book.status
            
            # Debug logging for publish checkbox
            logger.debug(f"Edit book {book_id} - Form data keys: {list(data.keys())}")
            logger.debug(f"Edit book {book_id} - is_published value: {data.get('is_published', 'NOT PRESENT')}")
            
            # Update book fields
            book.title = data['title']
            raw_description = data.get('description', '')
            try:
                book.description = sanitize_project_description(raw_description, book_id=book_id)
            except ProjectDescriptionError as exc:
                return jsonify({'success': False, 'error': str(exc)}), 400
            book.genre = data.get('genre', '')
            if not book.digital_file_path:
                book.language = data.get('language', '')
            book.target_audience = data.get('target_audience', '')
            book.price = float(data.get('price', 0)) if data.get('price') else None
            book.print_enabled = _as_bool(data.get('print_enabled'))
            if data.get('print_price'):
                book.print_price = float(data.get('print_price'))
            elif not book.print_enabled:
                book.print_price = None
            book.print_shipping_price = float(data.get('print_shipping_price') or 0) if data.get('print_shipping_price') else 0.0
            if data.get('print_handling_days'):
                book.print_handling_days = max(1, int(data.get('print_handling_days')))
            book.print_description = (data.get('print_description') or '').strip() or None
            if book.print_enabled and (not book.print_price or book.print_price <= 0):
                return jsonify({'success': False, 'error': 'Set a print book price before enabling print sales.'}), 400
            book.word_count_target = int(data.get('word_count_target', 0)) if data.get('word_count_target') else None
            book.tags = data.get('tags', '')
            cover_upload = request.files.get('cover_upload')
            if cover_upload and cover_upload.filename:
                saved_cover = save_book_cover_file(cover_upload)
                if not saved_cover:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid cover upload. Use PNG, JPG, GIF, WebP, or SVG.'
                    }), 400
                book.cover_image = saved_cover
            elif 'cover_image' in request.form:
                ci = (request.form.get('cover_image') or '').strip()
                if ci:
                    book.cover_image = ci
            book.updated_at = datetime.now(timezone.utc)

            def _as_bool(v):
                if isinstance(v, bool):
                    return v
                if v is None:
                    return False
                return str(v).strip().lower() in ("1", "true", "yes", "on")

            newly_listing = False
            
            # Handle publishing status - separate for digital book and audiobook
            if book.digital_file_path:
                # For uploaded digital books, handle separate publishing
                publish_digital = data.get('publish_digital_book') == 'on'
                publish_audiobook = data.get('publish_audiobook') == 'on'
                if (
                    (publish_digital and not book.digital_book_published)
                    or (publish_audiobook and not book.audiobook_published)
                ):
                    terms_error = validate_listing_terms_payload(data)
                    if terms_error:
                        return jsonify({'success': False, 'error': terms_error}), 400
                    newly_listing = True
                # Handle digital book publishing
                if publish_digital:
                    price_value = book.price if book.price else (float(data.get('price', 0)) if data.get('price') else 0)
                    if not price_value or price_value <= 0:
                        return jsonify({
                            'success': False, 
                            'error': 'Please set a price before publishing your digital book to the marketplace.'
                        }), 400
                    if not book_has_listing_cover(book):
                        return jsonify({
                            'success': False,
                            'error': 'Please add a cover image before publishing to the marketplace. You can upload a file or set a cover URL in this form.'
                        }), 400
                    if not book.digital_book_published:
                        book.digital_book_published = True
                        book.digital_book_published_at = datetime.now(timezone.utc)
                        logger.info(f"Digital book {book_id} published via edit form")
                else:
                    if book.digital_book_published:
                        book.digital_book_published = False
                        logger.info(f"Digital book {book_id} unpublished via edit form")
                
                # Handle audiobook publishing
                if publish_audiobook:
                    ok_audio, audio_err = audiobook_ready_for_marketplace_publish(book)
                    if not ok_audio:
                        return jsonify({'success': False, 'error': audio_err}), 400
                    if not book.audiobook_published and data.get('confirm_audiobook_publish') != 'on':
                        return jsonify({
                            'success': False,
                            'error': (
                                'Confirm that you have previewed the audiobook and approve '
                                'publishing it to the marketplace.'
                            ),
                        }), 400
                    audiobook_price_value = book.audiobook_price if book.audiobook_price else 0
                    if not audiobook_price_value or audiobook_price_value < 0:
                        return jsonify({
                            'success': False, 
                            'error': 'Please set an audiobook price before publishing it to the marketplace.'
                        }), 400
                    if not book_has_listing_cover(book):
                        return jsonify({
                            'success': False,
                            'error': 'Please add a cover image before publishing the audiobook to the marketplace.'
                        }), 400
                    if not book.audiobook_published:
                        book.audiobook_published = True
                        book.audiobook_published_at = datetime.now(timezone.utc)
                        logger.info(f"Audiobook {book_id} published via edit form")
                else:
                    if book.audiobook_published:
                        book.audiobook_published = False
                        logger.info(f"Audiobook {book_id} unpublished via edit form")
            else:
                # For platform-created books, use the old status-based publishing
                is_published_flag = (
                    data.get('is_published') == 'on' or 
                    data.get('is_published') == True or 
                    data.get('is_published') == 'true' or
                    'is_published' in data
                )
                
                logger.info(f"Edit book {book_id} - is_published_flag: {is_published_flag}, price: {book.price}")
                
                if is_published_flag:
                    if book.status != BookStatus.PUBLISHED:
                        terms_error = validate_listing_terms_payload(data)
                        if terms_error:
                            return jsonify({'success': False, 'error': terms_error}), 400
                        newly_listing = True
                    price_value = book.price if book.price else (float(data.get('price', 0)) if data.get('price') else 0)
                    if not price_value or price_value <= 0:
                        return jsonify({
                            'success': False, 
                            'error': 'Please set a price before publishing your book to the marketplace.'
                        }), 400
                    if not book_has_listing_cover(book):
                        return jsonify({
                            'success': False,
                            'error': 'Please add a cover image before publishing to the marketplace.'
                        }), 400

                    if book.status != BookStatus.PUBLISHED:
                        book.status = BookStatus.PUBLISHED
                        if not book.published_at:
                            book.published_at = datetime.now(timezone.utc)
                        logger.info(f"Book {book_id} published via edit form - Status set to PUBLISHED")
                else:
                    if is_book_published(book):
                        book.status = BookStatus.DRAFT
                        logger.info(f"Book {book_id} unpublished via edit form - Status set to DRAFT")

            from glconnect.isbn_pool_service import assign_marketplace_isbn_if_needed, IsbnPoolError

            if newly_listing or (
                book.print_enabled
                and not getattr(book, 'listing_attestation_accepted_at', None)
                and _as_bool(data.get('print_enabled'))
            ):
                if not newly_listing:
                    terms_error = validate_listing_terms_payload(data)
                    if terms_error:
                        return jsonify({'success': False, 'error': terms_error}), 400
                record_listing_attestation(book)

            try:
                assign_marketplace_isbn_if_needed(book)
            except IsbnPoolError as e:
                db.session.rollback()
                return jsonify({'success': False, 'error': str(e)}), 503
            
            db.session.commit()

            redirect_path = (
                url_for('book_platform.books')
                if listing_flow_requested
                else url_for('book_platform.view_book', book_id=book_id)
            )
            just_published_digital = book.digital_book_published and not _prev_digital_pub
            just_published_audiobook = book.audiobook_published and not _prev_audiobook_pub
            just_published_chapter_book = (
                book.status == BookStatus.PUBLISHED and _prev_status != BookStatus.PUBLISHED
            )
            just_published = (
                just_published_digital or just_published_audiobook or just_published_chapter_book
            )
            resp = {'success': True, 'redirect': redirect_path}
            if (
                just_published
                and book.author
                and author_needs_stripe_payout_setup(book.author)
            ):
                resp['payout_setup_required'] = True
                resp['redirect'] = url_for(
                    'book_platform.author_payout_setup',
                    next=redirect_path,
                )
            
            return jsonify(resp)
            
        except Exception as e:
            db.session.rollback()
            print(f"Book edit error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    listing_flow = (request.args.get('flow') or '').strip().lower() == 'listing'
    if listing_flow or request.args.get('audiobook'):
        return redirect(url_for('book_platform.book_audiobook', book_id=book_id))
    campaign = InvestmentCampaign.query.filter_by(book_project_id=book.id).first()
    return render_template(
        'book_platform/edit_book.html',
        book=book,
        ebook_language_label=language_label(book.language),
        media_guide=MEDIA_GUIDE,
        investment_campaign=campaign,
    )

@book_bp.route('/books/<int:book_id>/audiobook', methods=['GET'])
@writer_or_book_platform_required
def book_audiobook(book_id, user_profile, profile_type):
    """Audiobook generation and publishing — separate from manuscript edit."""
    from glconnect.book_platform_models import BookPlatformUser
    from sqlalchemy.orm import joinedload

    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).get_or_404(book_id)

    if not book.author:
        flash('Book author information could not be loaded.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))

    author_id = get_profile_id(user_profile, profile_type)
    if author_id is None:
        flash('Profile configuration error. Please ensure you have a Writer or Ink Studio profile.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))

    if book.author_id != author_id:
        flash('Only the author can manage the audiobook', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))

    return render_template(
        'book_platform/book_audiobook.html',
        book=book,
        ebook_language_label=language_label(book.language),
    )

# Chapter management routes
@book_bp.route('/books/<int:book_id>/chapters')
@book_platform_required
def chapters(book_id):
    """List chapters for a book"""
    book = BookProject.query.get_or_404(book_id)
    chapters = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number).all()
    return render_template('book_platform/chapters.html', book=book, chapters=chapters)

@book_bp.route('/books/<int:book_id>/chapters/create', methods=['GET', 'POST'])
@book_platform_required
def create_chapter(book_id):
    """Create a new chapter"""
    book = BookProject.query.get_or_404(book_id)
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            
            # Get next chapter number
            last_chapter = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number.desc()).first()
            next_number = (last_chapter.chapter_number + 1) if last_chapter else 1
            
            # Use provided chapter number or calculate next
            chapter_number = int(data.get('chapter_number', next_number))
            
            # Calculate word count from content (strip HTML tags)
            content = data.get('content', '')
            word_count = count_words_from_html(content) if content else 0
            
            from glconnect.book_utils import normalize_section_kind_input

            chapter = BookChapter(
                title=data['title'],
                content=content,
                summary=data.get('summary', ''),
                chapter_number=chapter_number,
                section_kind=normalize_section_kind_input(data.get('section_kind'), data['title']),
                word_count=word_count,
                word_count_target=int(data.get('word_count_target', 0)) if data.get('word_count_target') else None,
                book_project_id=book_id,
                is_published=data.get('is_published') == 'on' or data.get('is_published') == True
            )
            
            db.session.add(chapter)
            db.session.flush()  # Flush to get chapter ID
            
            # Update book's total word count
            update_book_word_count(book)
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'chapter_id': chapter.id,
                'redirect': url_for('book_platform.view_book', book_id=book_id)
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Chapter creation error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # Get next chapter number for the form
    last_chapter = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number.desc()).first()
    next_chapter_number = (last_chapter.chapter_number + 1) if last_chapter else 1
    
    return render_template('book_platform/create_chapter.html', 
                         book=book, 
                         next_chapter_number=next_chapter_number)

@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>')
@book_platform_required
def view_chapter(book_id, chapter_id):
    """View and edit chapter"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    if chapter.book_project_id != book_id:
        flash('Chapter not found in this book', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Get comments for this chapter
    comments = BookComment.query.filter_by(chapter_id=chapter_id).order_by(BookComment.created_at).all()
    
    return render_template('book_platform/view_chapter.html', 
                         book=book, 
                         chapter=chapter,
                         comments=comments)

@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/edit', methods=['GET', 'POST'])
@writer_or_book_platform_required
def edit_chapter(book_id, chapter_id, user_profile, profile_type):
    """Edit chapter - GET shows form, POST saves changes"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # Check if user is the author of the book
    if book.author_id != author_id:
        flash('You can only edit chapters in your own books', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Check if chapter is published - if so, prevent editing
    if chapter.is_published:
        flash('This chapter is marked complete and cannot be edited. Reopen it first to make changes.', 'warning')
        return redirect(url_for('book_platform.view_chapter', book_id=book_id, chapter_id=chapter_id))
    
    if chapter.book_project_id != book_id:
        flash('Chapter not found in this book', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            
            actor_id = resolve_version_actor_id(book, current_user.user_id)
            if actor_id:
                snapshot_chapter(chapter, actor_id, change_source='author_edit')
            
            # Update chapter fields
            chapter.title = data.get('title', chapter.title)
            chapter.content = data.get('content', chapter.content)
            chapter.summary = data.get('summary', chapter.summary)
            from glconnect.book_utils import normalize_section_kind_input
            chapter.section_kind = normalize_section_kind_input(
                data.get('section_kind'),
                chapter.title,
            )
            
            # Handle word_count_target safely
            word_count_target = data.get('word_count_target', '')
            if word_count_target and word_count_target.strip():
                try:
                    chapter.word_count_target = int(word_count_target)
                except (ValueError, TypeError):
                    chapter.word_count_target = None
            else:
                chapter.word_count_target = None
            
            chapter.is_published = data.get('is_published') == 'on' or data.get('is_published') == True
            # Recalculate word count from content (strip HTML tags)
            content = data.get('content', '')
            if content:
                try:
                    chapter.word_count = count_words_from_html(content)
                except Exception as e:
                    logging.error(f"Error calculating word count: {e}")
                    # Fallback: use simple split if HTML parsing fails
                    chapter.word_count = len(content.split()) if content else 0
            else:
                chapter.word_count = 0
            chapter.updated_at = datetime.now(timezone.utc)
            
            # Update book's total word count
            update_book_word_count(book)
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'word_count': chapter.word_count})
            else:
                flash('Chapter updated successfully!', 'success')
                return redirect(url_for('book_platform.view_chapter', book_id=book_id, chapter_id=chapter_id))
                
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logging.error(f"Chapter update error: {error_msg}", exc_info=True)
            print(f"Chapter update error: {error_msg}")
            print(f"Error type: {type(e)}")
            try:
                print(f"Data received: {data}")
            except:
                print("Data not available in error handler")
            if request.is_json:
                return jsonify({'success': False, 'error': f'An unexpected error occurred: {error_msg}'}), 500
            else:
                flash(f'An unexpected error occurred while editing chapter: {error_msg}', 'error')
    
    # GET request - show edit form
    can_restore_versions = book.author_id == get_profile_id(user_profile, profile_type)
    return render_template(
        'book_platform/edit_chapter.html',
        book=book,
        chapter=chapter,
        can_restore_versions=can_restore_versions,
    )


@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/versions', methods=['GET'])
@writer_or_book_platform_required
def chapter_versions_list(book_id, chapter_id, user_profile, profile_type):
    """JSON list of saved chapter snapshots (collaboration change history)."""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    if chapter.book_project_id != book_id:
        return jsonify({'success': False, 'error': 'Chapter not found in this book'}), 404

    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user or not _user_can_view_chapter_history(book, book_user.id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    return jsonify({
        'success': True,
        'versions': fetch_chapter_versions(chapter_id),
        'can_restore': book.author_id == get_profile_id(user_profile, profile_type)
        and not chapter.is_published,
    })


@book_bp.route(
    '/books/<int:book_id>/chapters/<int:chapter_id>/versions/<int:version_id>/restore',
    methods=['POST'],
)
@writer_or_book_platform_required
def chapter_version_restore(book_id, chapter_id, version_id, user_profile, profile_type):
    """Roll chapter back to a prior snapshot (author only; chapter must be open for editing)."""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    author_id = get_profile_id(user_profile, profile_type)

    if book.author_id != author_id:
        return jsonify({'success': False, 'error': 'Only the author can restore a prior version'}), 403
    if chapter.is_published:
        return jsonify({'success': False, 'error': 'Reopen the chapter before restoring a version'}), 400
    if chapter.book_project_id != book_id:
        return jsonify({'success': False, 'error': 'Chapter not found in this book'}), 404

    actor_id = resolve_version_actor_id(book, current_user.user_id)
    if not actor_id:
        return jsonify({'success': False, 'error': 'Could not resolve author profile'}), 400

    ok, message, restored = apply_chapter_version_restore(chapter, version_id, actor_id)
    if not ok:
        return jsonify({'success': False, 'error': message}), 404

    update_book_word_count(book)
    db.session.commit()
    return jsonify({'success': True, 'message': message, 'version': restored})


@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/unpublish', methods=['POST'])
@book_platform_required
def unpublish_chapter(book_id, chapter_id):
    """Unpublish a chapter to allow editing"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)

    # Check if user has permission
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
            return jsonify({'error': 'Ink Studio profile required'}), 403

    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'error': 'You can only unpublish chapters in your own books'}), 403

    if chapter.book_project_id != book_id:
        return jsonify({'error': 'Chapter not found in this book'}), 404

    # Unpublish the chapter
    chapter.is_published = False
    chapter.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Chapter unpublished successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def cleanup_orphaned_sessions():
    """Clean up any orphaned realtime sessions that reference non-existent books"""
    try:
        # Find sessions that reference books that no longer exist
        orphaned_sessions = db.session.query(RealtimeSession).outerjoin(
            BookProject, RealtimeSession.book_project_id == BookProject.id
        ).filter(BookProject.id.is_(None)).all()
        
        for session in orphaned_sessions:
            db.session.delete(session)
        
        if orphaned_sessions:
            db.session.commit()
            logger.info(f"Cleaned up {len(orphaned_sessions)} orphaned realtime sessions")
            
    except Exception as e:
        logger.error(f"Error cleaning up orphaned sessions: {str(e)}")
        db.session.rollback()


def _delete_legacy_book_cart_rows(book_id: int) -> None:
    """Best-effort cleanup of legacy book_cart_items rows if the table still exists."""
    try:
        with db.session.begin_nested():
            db.session.execute(
                text("DELETE FROM book_cart_items WHERE book_project_id = :bid"),
                {"bid": int(book_id)},
            )
    except Exception:
        pass


@book_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@login_required
def delete_book(book_id):
    """Delete a book and all its chapters"""
    try:
        # Clean up any orphaned sessions first (don't let errors here break the flow)
        try:
            cleanup_orphaned_sessions()
        except Exception as cleanup_error:
            logger.warning(f"Error in cleanup_orphaned_sessions during book deletion: {str(cleanup_error)}")
        
        # Use get() instead of get_or_404() to return JSON error instead of HTML
        book = BookProject.query.get(book_id)
        if not book:
            # Idempotent delete: if already gone, treat as successful removal.
            return jsonify({'success': True, 'message': 'Book already removed'}), 200

        # Admins can delete any book without an Ink Studio author profile; authors need a resolved profile
        if current_user.role != 'admin':
            user_profile, profile_type = _profile_for_ink_permission_checks()
            if not user_profile:
                return jsonify({'error': 'You need a Writer profile to manage books. Please create a Writer profile in Ink Studio.'}), 403
            author_id = get_profile_id(user_profile, profile_type)
            if author_id is None:
                return jsonify({'error': 'Profile configuration error. Please ensure you have a Writer or Ink Studio profile.'}), 403
            if book.author_id != author_id:
                return jsonify({'error': 'You can only delete your own books'}), 403

        # Clean up related data in proper order to avoid foreign key constraints
        
        # 1. Clean up investment payouts first (they reference investments which reference campaigns)
        campaign = InvestmentCampaign.query.filter_by(book_project_id=book_id).first()
        if campaign:
            # Get all investments for this campaign
            investments = BookInvestment.query.filter_by(campaign_id=campaign.id).all()
            investment_ids = [inv.id for inv in investments]
            if investment_ids:
                InvestmentPayout.query.filter(InvestmentPayout.investment_id.in_(investment_ids)).delete(synchronize_session=False)
            
            # 2. Clean up investments (they reference campaign_id and book_project_id)
            BookInvestment.query.filter_by(campaign_id=campaign.id).delete()
            
            # 3. Clean up investment campaign (references book_project_id)
            db.session.delete(campaign)
        
        # 4. Clean up sales (they reference book_project_id and purchase_id)
        # Note: BookSale has book_project_id as NOT NULL, so we must delete, not update
        BookSale.query.filter_by(book_project_id=book_id).delete()
        
        # 5. Clean up purchases (they reference book_project_id)
        # Note: BookPurchase has book_project_id as NOT NULL, so we must delete, not update
        BookPurchase.query.filter_by(book_project_id=book_id).delete()
        _delete_legacy_book_cart_rows(book_id)
        _delete_reader_annotations_for_book(book_id)

        # 6. Clean up audio generation tasks (they reference book_project_id)
        AudioGenerationTask.query.filter_by(book_project_id=book_id).delete()
        
        # 7. Clean up realtime sessions (they reference book_project_id)
        RealtimeSession.query.filter_by(book_project_id=book_id).delete()
        
        # 8. Clean up comments (they reference book_project_id)
        BookComment.query.filter_by(book_project_id=book_id).delete()
        
        # 9. Clean up invitations via collaborations (CollaborationInvitation has collaboration_id, not book_project_id)
        collab_ids_subq = db.session.query(BookCollaboration.id).filter_by(book_project_id=book_id).subquery()
        CollaborationInvitation.query.filter(CollaborationInvitation.collaboration_id.in_(collab_ids_subq)).delete(synchronize_session=False)

        # 10. Clean up collaborations (they reference book_project_id)
        BookCollaboration.query.filter_by(book_project_id=book_id).delete()
        
        # 11. Clean up analytics (they reference book_project_id)
        BookAnalytics.query.filter_by(book_project_id=book_id).delete()
        
        # 12. Clean up notifications (they reference book_project_id)
        BookNotification.query.filter_by(book_project_id=book_id).delete()
        
        # 13. Clean up reviews (they reference book_project_id)
        BookReview.query.filter_by(book_project_id=book_id).delete()
        
        # 14. Chapters + chapter_versions + book_versions (bulk delete bypasses ORM cascade)
        delete_book_chapter_version_graph_for_project(book_id)
        
        # 15. Finally delete the book
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Book deleted successfully'})
    except Exception as e:
        db.session.rollback()
        # Safety fallback: if hard delete fails, at least remove listing visibility
        # so the book no longer appears in marketplace.
        try:
            book_fallback = BookProject.query.get(book_id)
            if book_fallback:
                book_fallback.status = BookStatus.DRAFT
                book_fallback.digital_book_published = False
                book_fallback.audiobook_published = False
                db.session.commit()
        except Exception:
            db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error deleting book {book_id}: {str(e)}\n{error_trace}")
        return jsonify({'error': f'Failed to delete book: {str(e)}'}), 500

@book_bp.route('/books/<int:book_id>/prepare-audiobook-segments', methods=['POST'])
@book_platform_required
def prepare_audiobook_segments(book_id):
    """
    Build section list from the current book text, run AI/heuristic include suggestions,
    persist draft on BookProject for the author to confirm before TTS.
    """
    book = BookProject.query.get(book_id)
    if not book:
        return jsonify({'success': False, 'error': 'Book not found'}), 404
    if not current_user or not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user or book.author_id != book_user.id:
        return jsonify({'success': False, 'error': 'You can only prepare audiobooks for your own books'}), 403
    if book.has_audiobook:
        return jsonify({'success': False, 'error': 'This book already has an audiobook version'}), 400

    src = build_audiobook_source(book, current_app.root_path)
    if not src['success']:
        return jsonify({'success': False, 'error': src['error']}), 400

    chapters_for_audio = src['chapters_for_audio']
    if not chapters_for_audio:
        return jsonify({'success': False, 'error': 'No sections found to narrate.'}), 400

    classifier, segments = suggest_includes_for_chapters(chapters_for_audio)
    plan = {
        'source_hash': src['source_hash'],
        'classifier': classifier,
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'segment_count': len(segments),
        'segments': segments,
    }
    book.audiobook_segment_plan = plan
    db.session.commit()

    return jsonify({
        'success': True,
        'source_hash': src['source_hash'],
        'classifier': classifier,
        'segment_count': len(segments),
        'segments': segments,
        'notice': (
            'Your ebook listing is unchanged—footnotes, index, tables, and appendix stay in the digital edition. '
            'Here you only choose what is read for the audiobook. Uncheck sections you do not want narrated. '
            'Suggestions use Gemini when GEMINI_API_KEY or GOOGLE_API_KEY is set (same as news), '
            'otherwise title-based rules only.'
        ),
    })

@book_bp.route('/books/<int:book_id>/generate-audiobook', methods=['POST'])
@book_platform_required
def generate_audiobook_for_book(book_id):
    """Generate audiobook from existing book content"""
    book = BookProject.query.get(book_id)
    if not book:
        return jsonify({'success': False, 'error': 'Book not found'}), 404
    
    # Check if user has permission
    if not current_user or not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        return jsonify({'success': False, 'error': 'Ink Studio profile required'}), 403
    
    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'success': False, 'error': 'You can only generate audiobooks for your own books'}), 403
    
    # Check if book already has audiobook
    if book.has_audiobook:
        return jsonify({'success': False, 'error': 'This book already has an audiobook version'}), 400
    
    # Get request data
    try:
        data = request.get_json() or {}
    except Exception as e:
        logger.error(f"Error parsing JSON request: {str(e)}")
        return jsonify({'success': False, 'error': 'Invalid JSON in request'}), 400
    
    audiobook_price = data.get('audiobook_price', 0.0)
    voice_name = data.get('voice_name', 'en-US-Neural2-A')
    
    if not voice_name:
        return jsonify({'success': False, 'error': 'Voice name is required'}), 400
    
    try:
        src = build_audiobook_source(book, current_app.root_path)
        if not src['success']:
            return jsonify({'success': False, 'error': src['error']}), 400

        full_text = src['full_text']
        chapters_for_audio = src['chapters_for_audio']
        source_hash = src['source_hash']

        source_hash_payload = data.get('source_hash')
        segment_includes_payload = data.get('segment_includes')

        if source_hash_payload:
            if source_hash_payload != source_hash:
                return jsonify({
                    'success': False,
                    'error': 'Your book text changed since you reviewed sections. Please click Review sections again.',
                    'stale_segment_plan': True,
                }), 409
            if not isinstance(segment_includes_payload, list):
                return jsonify({
                    'success': False,
                    'error': 'segment_includes must be a list of booleans, one per section.',
                }), 400
            segment_bools = []
            for x in segment_includes_payload:
                if isinstance(x, bool):
                    segment_bools.append(x)
                elif isinstance(x, (int, float)) and int(x) in (0, 1):
                    segment_bools.append(bool(int(x)))
                elif isinstance(x, str) and x.strip().lower() in ('true', 'false', '1', '0', 'yes', 'no'):
                    segment_bools.append(x.strip().lower() in ('true', '1', 'yes'))
                else:
                    return jsonify({
                        'success': False,
                        'error': 'segment_includes entries must be true/false for each section.',
                    }), 400
            filtered, ferr = filter_and_renumber_chapters(chapters_for_audio, segment_bools)
            if ferr:
                return jsonify({'success': False, 'error': ferr}), 400
            chapters_for_audio_thread = filtered
        else:
            chapters_for_audio_thread = list(chapters_for_audio)

        # Create audio generation task
        audio_task = AudioGenerationTask(
            book_project_id=book.id,
            status='pending'
        )
        db.session.add(audio_task)
        db.session.commit()
        
        # Store IDs and data for use in background thread (objects can't be passed between threads)
        task_id = audio_task.id
        book_id_for_thread = book.id
        full_text_for_thread = full_text
        voice_name_for_thread = voice_name
        audiobook_price_for_thread = audiobook_price
        
        app = current_app._get_current_object()

        def generate_audio_background():
            with app.app_context():
                try:
                    audio_task = AudioGenerationTask.query.get(task_id)
                    book = BookProject.query.get(book_id_for_thread)
                    
                    if not audio_task or not book:
                        logger.error(f"Could not find audio task {task_id} or book {book_id_for_thread} in background thread")
                        return
                    
                    audio_task.status = 'processing'
                    audio_task.progress = 10
                    db.session.commit()
                    
                    # Always chapter-based when we have segments (platform chapters or upload parts)
                    if chapters_for_audio_thread:
                        audio_result = audio_book_generator.generate_audiobook_by_chapters(
                            chapters_for_audio_thread,
                            book.id,
                            voice_name_for_thread
                        )
                    else:
                        audio_result = audio_book_generator.generate_audiobook(
                            full_text_for_thread,
                            book.id,
                            voice_name_for_thread
                        )
                    
                    if audio_result['success']:
                        book.has_audiobook = True
                        book.audiobook_price = audiobook_price_for_thread
                        book.audiobook_generated_at = datetime.now(timezone.utc)
                        book.audiobook_voice = voice_name_for_thread
                        
                        if chapters_for_audio_thread and audio_result.get('chapter_results'):
                            # Store per-chapter audio; keep first chapter path for backward compat
                            ch_results = audio_result['chapter_results']
                            book.audiobook_duration = audio_result.get('duration', 0)
                            book.audiobook_file_path = ch_results[0]['audio_file_path'] if ch_results else None
                            for ch in ch_results:
                                ac = AudiobookChapter(
                                    book_project_id=book.id,
                                    chapter_number=ch['chapter_number'],
                                    title=ch['title'],
                                    audio_file_path=ch['audio_file_path'],
                                    duration_seconds=ch.get('duration', 0),
                                    book_chapter_id=ch.get('book_chapter_id')
                                )
                                db.session.add(ac)
                        else:
                            book.audiobook_file_path = audio_result['audio_file_path']
                            book.audiobook_duration = audio_result.get('duration', 0)
                        
                        audio_task.status = 'completed'
                        audio_task.progress = 100
                        audio_task.completed_at = datetime.now(timezone.utc)
                        
                        db.session.commit()
                        logger.info(f"Audiobook generated successfully for book {book.id}")
                        
                    else:
                        # Update task with error
                        audio_task.status = 'failed'
                        audio_task.error_message = audio_result['error']
                        db.session.commit()
                        logger.error(f"Failed to generate audiobook for book {book.id}: {audio_result['error']}")
                        
                except Exception as e:
                    import traceback
                    error_trace = traceback.format_exc()
                    logger.error(f"Error in background audiobook generation: {str(e)}\n{error_trace}")
                    try:
                        # Try to update task status, but don't fail if we can't
                        audio_task = AudioGenerationTask.query.get(task_id)
                        if audio_task:
                            audio_task.status = 'failed'
                            audio_task.error_message = str(e)
                            db.session.commit()
                    except Exception as inner_e:
                        logger.error(f"Failed to update task status after error: {str(inner_e)}")
        
        # Start background thread
        thread = threading.Thread(target=generate_audio_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': 'Audiobook generation started. You will be notified when it\'s complete.',
            'task_id': audio_task.id
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error starting audiobook generation for book {book_id}: {str(e)}\n{error_trace}")
        return jsonify({
            'success': False,
            'error': f'Failed to start audiobook generation: {str(e)}'
        }), 500

@book_bp.route('/audiobook/available-voices', methods=['GET'])
@book_platform_required
def get_available_voices_upload():
    """Get available TTS voices for audiobook generation (filtered by ebook language)."""
    try:
        lang = (request.args.get("lang") or "en").strip().lower()
        prefix = tts_voice_list_prefix(lang)
        result = audio_book_generator.get_available_voices(language_filter=prefix)
        
        if result['success']:
            return jsonify({
                'success': True,
                'voices': result['voices']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to fetch voices')
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching available voices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@book_bp.route('/books/<int:book_id>/audiobook/available-voices', methods=['GET'])
@book_platform_required
def get_available_voices(book_id):
    """Get available TTS voices for audiobook generation (matches book language)."""
    try:
        book = BookProject.query.get_or_404(book_id)
        lang = (book.language or "en").strip().lower()
        prefix = tts_voice_list_prefix(lang)
        result = audio_book_generator.get_available_voices(language_filter=prefix)
        
        if result['success']:
            return jsonify({
                'success': True,
                'voices': result['voices']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to fetch voices')
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching available voices: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@book_bp.route('/audiobook/preview-voice', methods=['POST'])
@book_platform_required
def preview_voice_upload():
    """Generate a preview audio sample for a voice (for upload page)"""
    try:
        data = request.get_json()
        voice_name = data.get('voice_name')
        sample_text = data.get('sample_text')  # Optional custom sample
        
        if not voice_name:
            return jsonify({
                'success': False,
                'error': 'Voice name is required'
            }), 400
        
        result = audio_book_generator.generate_preview_audio(voice_name, sample_text)
        
        if result['success']:
            return jsonify({
                'success': True,
                'audio_url': result['audio_url']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate preview')
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating voice preview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@book_bp.route('/books/<int:book_id>/audiobook/preview-voice', methods=['POST'])
@book_platform_required
def preview_voice(book_id):
    """Generate a preview audio sample for a voice"""
    try:
        data = request.get_json()
        voice_name = data.get('voice_name')
        sample_text = data.get('sample_text')  # Optional custom sample
        
        if not voice_name:
            return jsonify({
                'success': False,
                'error': 'Voice name is required'
            }), 400
        
        result = audio_book_generator.generate_preview_audio(voice_name, sample_text)
        
        if result['success']:
            return jsonify({
                'success': True,
                'audio_url': result['audio_url']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate preview')
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating voice preview: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@book_bp.route('/books/<int:book_id>/audiobook-status', methods=['GET'])
@book_platform_required
def get_audiobook_status(book_id):
    """Get audiobook generation status"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user has permission
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        return jsonify({'error': 'Ink Studio profile required'}), 403
    
    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get latest audio generation task
    audio_task = AudioGenerationTask.query.filter_by(
        book_project_id=book_id
    ).order_by(AudioGenerationTask.created_at.desc()).first()
    
    if not audio_task:
        return jsonify({
            'has_audiobook': book.has_audiobook,
            'status': 'none',
            'progress': 0
        })
    
    return jsonify({
        'has_audiobook': book.has_audiobook,
        'status': audio_task.status,
        'progress': audio_task.progress or 0,
        'error_message': audio_task.error_message,
        'created_at': audio_task.created_at.isoformat() if audio_task.created_at else None,
        'completed_at': audio_task.completed_at.isoformat() if audio_task.completed_at else None
    })

@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/delete', methods=['POST'])
@writer_or_book_platform_required
def delete_chapter(book_id, chapter_id, user_profile, profile_type):
    """Delete a chapter"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)

    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)

    # Check if user is the author of the book
    if book.author_id != author_id:
        return jsonify({'error': 'You can only delete chapters in your own books'}), 403

    if chapter.book_project_id != book_id:
        return jsonify({'error': 'Chapter not found in this book'}), 404

    try:
        # Delete the chapter
        db.session.delete(chapter)
        db.session.flush()  # Flush to ensure deletion is processed
        
        # Update book's total word count
        update_book_word_count(book)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Chapter deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Suggestion routes for collaborative editing with approval workflow
@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/suggest', methods=['POST'])
@writer_or_book_platform_required
def suggest_chapter_edit(book_id, chapter_id, user_profile, profile_type):
    """Collaborator submits suggested edits for approval"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    # Get the current user
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        return jsonify({'error': 'Ink Studio profile required'}), 403
    
    # Get the correct author ID
    author_id = get_profile_id(user_profile, profile_type)
    
    # Check if user is the author - authors can edit directly, no suggestions needed
    if book.author_id == author_id:
        return jsonify({'error': 'Authors can edit directly. Use the edit endpoint instead.'}), 400
    
    # Check if user has collaboration permission
    collaboration = BookCollaboration.query.filter_by(
        book_project_id=book_id,
        collaborator_id=book_user.id,
        is_active=True
    ).first()
    
    if not collaboration or collaboration.role.value in ['viewer']:
        return jsonify({'error': 'You do not have permission to suggest edits'}), 403
    
    data = request.get_json()
    
    # Create suggestion
    suggestion = ChapterSuggestion(
        chapter_id=chapter_id,
        suggested_by_id=book_user.id,
        suggested_title=data.get('title', chapter.title),
        suggested_content=data.get('content', chapter.content),
        suggested_summary=data.get('summary', chapter.summary),
        original_content=chapter.content,
        status='pending'
    )
    
    db.session.add(suggestion)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Your suggested edits have been submitted for review',
        'suggestion_id': suggestion.id
    })

@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/suggestions')
@writer_or_book_platform_required
def view_suggestions(book_id, chapter_id, user_profile, profile_type):
    """View all suggestions for a chapter"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    # Only author can view suggestions
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        flash('Only the author can view suggestions', 'error')
        return redirect(url_for('book_platform.view_chapter', book_id=book_id, chapter_id=chapter_id))
    
    suggestions = ChapterSuggestion.query.filter_by(chapter_id=chapter_id).order_by(
        ChapterSuggestion.created_at.desc()
    ).all()
    
    return render_template('book_platform/suggestions.html',
                         book=book,
                         chapter=chapter,
                         suggestions=suggestions)

@book_bp.route('/suggestions/<int:suggestion_id>/approve', methods=['POST'])
@writer_or_book_platform_required
def approve_suggestion(suggestion_id, user_profile, profile_type):
    """Approve and merge a suggestion into the chapter"""
    suggestion = ChapterSuggestion.query.get_or_404(suggestion_id)
    book = BookProject.query.get_or_404(suggestion.chapter.book_project_id)
    
    # Only author can approve
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'error': 'Only the author can approve suggestions'}), 403
    
    if suggestion.status != 'pending':
        return jsonify({'error': 'This suggestion has already been processed'}), 400
    
    # Save snapshot, then apply collaborator suggestion
    chapter = suggestion.chapter
    actor_id = resolve_version_actor_id(book, current_user.user_id) or author_id
    snapshot_chapter(chapter, actor_id, change_source='suggestion_approved')
    
    chapter.content = suggestion.suggested_content
    chapter.title = suggestion.suggested_title
    chapter.summary = suggestion.suggested_summary or chapter.summary
    chapter.updated_at = datetime.now(timezone.utc)
    # Recalculate word count from content (strip HTML tags)
    if suggestion.suggested_content:
        chapter.word_count = count_words_from_html(suggestion.suggested_content)
    
    # Update book's total word count
    update_book_word_count(book)
    
    # Update suggestion status
    suggestion.status = 'approved'
    suggestion.reviewed_by_id = author_id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.review_message = request.json.get('message', '')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Suggestion approved and merged into chapter'
    })

@book_bp.route('/suggestions/<int:suggestion_id>/reject', methods=['POST'])
@writer_or_book_platform_required
def reject_suggestion(suggestion_id, user_profile, profile_type):
    """Reject a suggestion"""
    suggestion = ChapterSuggestion.query.get_or_404(suggestion_id)
    book = BookProject.query.get_or_404(suggestion.chapter.book_project_id)
    
    # Only author can reject
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'error': 'Only the author can reject suggestions'}), 403
    
    if suggestion.status != 'pending':
        return jsonify({'error': 'This suggestion has already been processed'}), 400
    
    # Update suggestion status
    suggestion.status = 'rejected'
    suggestion.reviewed_by_id = author_id
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.review_message = request.json.get('message', 'Rejected by author')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Suggestion rejected'
    })

@book_bp.route('/suggestions/<int:suggestion_id>')
@writer_or_book_platform_required
def view_suggestion(suggestion_id, user_profile, profile_type):
    """View a specific suggestion (with diff view)"""
    suggestion = ChapterSuggestion.query.get_or_404(suggestion_id)
    book = BookProject.query.get_or_404(suggestion.chapter.book_project_id)
    
    # Only author can view suggestions
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        flash('Only the author can view suggestions', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book.id))
    
    return render_template('book_platform/view_suggestion.html',
                         suggestion=suggestion,
                         book=book,
                         chapter=suggestion.chapter)

# Helper function to send collaboration invitation email
def send_collaboration_invitation_email(invitation, book, inviter):
    """Send collaboration invitation email via Mailtrap"""
    sender = os.getenv("SENDER_MAIL", "info@ndotonic.com")
    api_key = os.getenv("MAIL_TRAP")
    
    if not api_key:
        logger.warning("MAIL_TRAP API key not set. Cannot send collaboration invitation email.")
        return False
    
    # Generate invitation URL
    invitation_url = url_for('book_platform.accept_invitation', 
                            invitation_uuid=invitation.uuid, 
                            _external=True)
    
    # Get inviter name
    inviter_name = inviter.pen_name or (inviter.user.username if hasattr(inviter, 'user') and inviter.user else "The Author")
    
    # Build email content
    role_display = invitation.role.value.replace('_', ' ').title()
    subject = f"Collaboration Invitation: {book.title}"
    
    message_text = f"""Hello,

{inviter_name} has invited you to collaborate on the book "{book.title}" as a {role_display}.

"""
    
    if invitation.message:
        message_text += f"Message from {inviter_name}:\n{invitation.message}\n\n"
    
    message_text += f"""To accept this invitation, please click the link below:

{invitation_url}

This invitation will expire in 7 days.

Account Requirements:
- Click the link below to open your invitation
- Log in with your GLC account, or create one if you are new
- Accept the invitation to start collaborating

Best regards,
Ink Studio Team
"""
    
    try:
        mail = Mail(
            sender=Address(email=sender, name="Ink Studio"),
            to=[Address(email=invitation.email)],
            subject=subject,
            text=message_text,
            category="Collaboration Invitation"
        )
        client = MailtrapClient(token=api_key)
        client.send(mail)
        logger.info(f"Collaboration invitation email sent to {invitation.email} for book {book.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send collaboration invitation email: {str(e)}", exc_info=True)
        return False

# Collaboration routes
@book_bp.route('/books/<int:book_id>/collaborate')
@writer_or_book_platform_required
def collaborate(book_id, user_profile, profile_type):
    """Collaboration management page"""
    book = BookProject.query.get_or_404(book_id)
    
    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # Only author can manage collaborations
    if book.author_id != author_id:
        flash('Only the author can manage collaborations', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    collaborations = BookCollaboration.query.filter_by(book_project_id=book_id, is_active=True).all()
    # Pending invitations: any invitation for this book whose collaboration belongs to this book
    invitations = CollaborationInvitation.query.join(BookCollaboration).filter(
        BookCollaboration.book_project_id == book_id,
        CollaborationInvitation.status == InvitationStatus.PENDING
    ).all()
    
    return render_template('book_platform/collaborate.html', 
                         book=book, 
                         collaborations=collaborations,
                         invitations=invitations)

@book_bp.route('/books/<int:book_id>/invite', methods=['POST'])
@writer_or_book_platform_required
def invite_collaborator(book_id, user_profile, profile_type):
    """Invite a collaborator"""
    book = BookProject.query.get_or_404(book_id)
    
    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # Only author can invite collaborators
    if book.author_id != author_id:
        return jsonify({'error': 'Only the author can invite collaborators'}), 403
    
    # Get the BookPlatformUser object for the inviter
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        # This should not happen due to the decorator, but handle it gracefully
        return jsonify({'error': 'Ink Studio profile required'}), 403
    
    data = request.get_json()
    
    # Normalize role value to match enum values (lowercase with underscore)
    role_value = data['role'].lower().replace('-', '_').replace(' ', '_')
    
    # Map common variations to correct enum values
    role_mapping = {
        'co_author': 'co_author',
        'coauthor': 'co_author',
        'co-author': 'co_author',
        'author': 'author',
        'editor': 'editor',
        'reviewer': 'reviewer',
        'viewer': 'viewer'
    }
    
    normalized_role = role_mapping.get(role_value, role_value)
    
    try:
        collaboration_role = CollaborationRole(normalized_role)
    except ValueError:
        return jsonify({'error': f'Invalid collaboration role: {data["role"]}'}), 400
    
    # Create collaboration
    collaboration = BookCollaboration(
        book_project_id=book_id,
        collaborator_id=book_user.id,  # Placeholder until invitation is accepted
        role=collaboration_role
    )
    db.session.add(collaboration)
    db.session.flush()  # Get the ID
    
    # Create invitation
    invitation = CollaborationInvitation(
        collaboration_id=collaboration.id,
        invited_by_id=book_user.id,
        email=data['email'],
        role=collaboration_role,
        message=data.get('message'),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    db.session.add(invitation)
    db.session.commit()
    
    # Send email invitation via Mailtrap
    try:
        send_collaboration_invitation_email(invitation, book, book_user)
    except Exception as e:
        logger.error(f"Failed to send collaboration invitation email: {str(e)}", exc_info=True)
        # Don't fail the invitation if email fails - invitation is still created
    
    return jsonify({'success': True, 'invitation_id': invitation.id})

@book_bp.route('/invitations/<string:invitation_uuid>', methods=['GET', 'POST'])
def accept_invitation(invitation_uuid):
    """Accept collaboration invitation"""
    invitation = CollaborationInvitation.query.options(
        joinedload(CollaborationInvitation.collaboration).joinedload(BookCollaboration.book_project),
        joinedload(CollaborationInvitation.invited_by).joinedload(BookPlatformUser.user)
    ).filter_by(uuid=invitation_uuid).first_or_404()
    
    if invitation.status != InvitationStatus.PENDING:
        flash('This invitation is no longer valid', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    # Check expiration - ensure both datetimes are timezone-aware
    expires_at = invitation.expires_at
    if expires_at.tzinfo is None:
        # If timezone-naive, assume it's UTC
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    if expires_at < now:
        invitation.status = InvitationStatus.EXPIRED
        db.session.commit()
        flash('This invitation has expired', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Please log in to accept the invitation', 'error')
            return redirect(url_for(
                'routes1.login',
                next=url_for('book_platform.accept_invitation', invitation_uuid=invitation_uuid),
            ))
        
        # Check if user has Ink Studio profile
        book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_user:
            return redirect(url_for(
                'book_platform.setup_profile',
                next=url_for('book_platform.accept_invitation', invitation_uuid=invitation_uuid),
            ))
        
        # Update collaboration with actual user
        collaboration = invitation.collaboration
        if not collaboration:
            flash('Invalid invitation: collaboration not found', 'error')
            return redirect(url_for('book_platform.dashboard'))
        
        collaboration.collaborator_id = book_user.id
        collaboration.joined_at = datetime.now(timezone.utc)
        
        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED
        invitation.responded_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        flash('Invitation accepted successfully!', 'success')
        return redirect(url_for('book_platform.view_book', book_id=collaboration.book_project_id))
    
    return render_template(
        'book_platform/accept_invitation.html',
        invitation=invitation,
        invite_return_path=url_for('book_platform.accept_invitation', invitation_uuid=invitation_uuid),
    )

# Comments and feedback routes
@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/comments', methods=['POST'])
@collaboration_required
def add_comment(book_id, chapter_id):
    """Add a comment to a chapter"""
    data = request.get_json()
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    comment = BookComment(
        content=data['content'],
        book_project_id=book_id,
        chapter_id=chapter_id,
        commenter_id=book_user.id,
        start_position=data.get('start_position'),
        end_position=data.get('end_position'),
        selected_text=data.get('selected_text')
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Create notification for book author
    if book_user.id != BookProject.query.get(book_id).author_id:
        notification = BookNotification(
            user_id=BookProject.query.get(book_id).author_id,
            book_project_id=book_id,
            title='New Comment',
            message=f'{book_user.pen_name or book_user.user.username} commented on your book',
            notification_type='comment'
        )
        db.session.add(notification)
        db.session.commit()
    
    return jsonify({'success': True, 'comment_id': comment.id})

@book_bp.route('/comments/<int:comment_id>/resolve', methods=['POST'])
@book_platform_required
def resolve_comment(comment_id):
    """Resolve a comment"""
    comment = BookComment.query.get_or_404(comment_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author or commenter can resolve
    if comment.book_project.author_id != book_user.id and comment.commenter_id != book_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    comment.is_resolved = True
    comment.resolved_at = datetime.now(timezone.utc)
    comment.status = CommentStatus.RESOLVED
    
    db.session.commit()
    
    return jsonify({'success': True})

def _marketplace_cover_url(book):
    """Resolve cover image URL for API and templates."""
    placeholder = url_for("static", filename="book_platform/placeholder_cover.svg")
    if not book or not getattr(book, "cover_image", None):
        return placeholder
    path = (book.cover_image or "").strip()
    if not path:
        return placeholder
    if path.startswith(("http://", "https://")):
        return path
    if path.startswith("/"):
        return path
    return url_for("static", filename=path)


def send_book_purchase_receipt_email(book, purchase):
    """Send a text receipt via Mailtrap (same pattern as account confirmation in routes1)."""
    to_email = purchase.get_buyer_email()
    if not to_email:
        logger.warning("Purchase receipt skipped: no buyer email for purchase %s", purchase.id)
        return
    sender = os.getenv("SENDER_MAIL")
    api_key = os.getenv("MAIL_TRAP")
    if not sender or not api_key:
        logger.warning("Purchase receipt skipped: SENDER_MAIL or MAIL_TRAP not set")
        return

    base = (current_app.config.get("FRONTEND_BASE_URL") or "").rstrip("/")
    fmt = getattr(purchase, "purchase_format", None) or "digital"
    currency = (purchase.currency or "USD").upper()
    try:
        if base:
            view_url = f"{base}/mybook/books/{book.id}"
            dl_url = f"{base}/mybook/books/{book.id}/download-digital"
            player_url = f"{base}/mybook/audiobook/{book.id}/player"
        else:
            view_url = url_for("book_platform.view_book", book_id=book.id, _external=True)
            dl_url = url_for("book_platform.download_digital_book", book_id=book.id, _external=True)
            player_url = url_for("book_platform.audiobook_player", book_id=book.id, _external=True)
    except Exception:
        view_url = dl_url = player_url = ""

    lines = [
        "Thank you for your purchase on Ink Studio.",
        "",
        f"Book: {book.title}",
        f"Format: {fmt}",
        f"Amount: {currency} {purchase.amount:.2f}",
        f"Order reference: #{purchase.id}",
        "",
        f"Your book: {view_url}",
    ]
    if fmt in ("digital", "bundle") and dl_url:
        lines.append(f"Download digital copy: {dl_url}")
    if fmt in ("audiobook", "bundle") and player_url:
        lines.append(f"Audiobook player: {player_url}")
    body = "\n".join(lines)

    try:
        msg = Mail(
            sender=Address(email=sender, name="Ink Studio"),
            to=[Address(email=to_email)],
            subject=f"Receipt: {book.title}",
            text=body,
            category="Book purchase",
        )
        MailtrapClient(token=api_key).send(msg)
        logger.info("Sent purchase receipt for purchase %s", purchase.id)
    except Exception as e:
        logger.warning("Failed to send purchase receipt: %s", e, exc_info=True)


# Marketplace routes
@book_bp.route('/marketplace')
@login_required
def marketplace():
    """Browse published books in the marketplace (signed-in users only)."""
    try:
        page = max(1, request.args.get('page', 1, type=int) or 1)
        per_page = 20

        genre = request.args.get('genre', None) or None
        language = request.args.get('language', None) or None
        search_term = (request.args.get('search', None) or "").strip() or None
        sort_by = request.args.get('sort_by', 'newest') or 'newest'
        price_range = request.args.get('price_range', None) or None
        if price_range == '':
            price_range = None

        offset = (page - 1) * per_page

        books = DatabaseOptimizer.get_marketplace_books(
            limit=per_page,
            offset=offset,
            genre=genre,
            language=language,
            search_term=search_term,
            sort_by=sort_by,
            price_range=price_range,
        )
        total_books = DatabaseOptimizer.count_marketplace_books(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        )
        list_stats = DatabaseOptimizer.get_marketplace_list_stats(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        )
        total_pages = max(1, (total_books + per_page - 1) // per_page) if total_books else 1

        available_genres = DatabaseOptimizer.get_available_genres()
        available_languages = DatabaseOptimizer.get_available_languages()

        if getattr(current_user, "is_authenticated", False):
            uid = current_user.user_id
            has_writer_profile = Writer.query.filter_by(user_id=uid).first() is not None
            has_book_platform_user = BookPlatformUser.query.filter_by(user_id=uid).first() is not None
        else:
            has_writer_profile = False
            has_book_platform_user = False
        from glconnect.ink_studio_v1 import ink_is_author_account, ink_v1_books_launch

        if ink_v1_books_launch():
            can_list_book_on_marketplace = ink_is_author_account()
        else:
            # Authors can list finished digital/audio-ready titles without writing in Ink Studio
            can_list_book_on_marketplace = bool(has_writer_profile or has_book_platform_user)

        return render_template(
            'book_platform/marketplace.html',
            books=books,
            has_writer_profile=has_writer_profile,
            can_list_book_on_marketplace=can_list_book_on_marketplace,
            page=page,
            per_page=per_page,
            total_books=total_books,
            total_pages=total_pages,
            list_stats=list_stats,
            selected_genre=genre,
            selected_language=language,
            selected_sort=sort_by,
            selected_price_range=price_range,
            available_genres=available_genres,
            available_languages=available_languages,
            search_term=search_term or '',
            marketplace_cover_url=_marketplace_cover_url,
        )
    except Exception as e:
        # Rollback any failed transaction to prevent "transaction aborted" errors
        try:
            db.session.rollback()
        except Exception:
            pass  # Ignore rollback errors
        
        logger.error(f"Marketplace error: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc()
        # Return empty list on error
        return render_template(
            'book_platform/marketplace.html',
            books=[],
            has_writer_profile=False,
            can_list_book_on_marketplace=False,
            page=1,
            per_page=20,
            total_books=0,
            total_pages=1,
            list_stats={'total': 0, 'paid': 0, 'free': 0},
            selected_genre=None,
            selected_language=None,
            selected_sort='newest',
            selected_price_range=None,
            available_genres=[],
            available_languages=[],
            search_term='',
            marketplace_cover_url=_marketplace_cover_url,
        )


@book_bp.route('/api/marketplace/books/<int:book_id>', methods=['GET'])
@login_required
def api_marketplace_book_detail(book_id):
    """JSON detail for marketplace modal / future PDP (published books only)."""
    from glconnect.isbn_pool_service import format_isbn_display, platform_publisher_name

    lang_labels = {
        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'it': 'Italian',
        'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
        'ar': 'Arabic', 'hi': 'Hindi', 'nl': 'Dutch', 'pl': 'Polish', 'tr': 'Turkish',
        'other': 'Other',
    }
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).filter_by(id=book_id).first()
    if not book or not is_book_published(book):
        return jsonify({'success': False, 'error': 'Book not found or not available in the marketplace.'}), 404

    author = book.author
    author_name = 'Unknown'
    author_user_id = None
    if author:
        if author.pen_name:
            author_name = author.pen_name
        elif author.user:
            author_name = author.user.username
            author_user_id = author.user.user_id
        else:
            author_name = 'Author'

    author_listing_count = DatabaseOptimizer.marketplace_books_base_query().filter(
        BookProject.author_id == book.author_id
    ).count()

    inv = InvestmentCampaign.query.filter_by(book_project_id=book.id).first() if book.has_investment_campaign else None

    primary_lc = (book.language or "en").lower()
    digital_editions_payload = []
    if book.digital_book_published and book.digital_file_path:
        digital_editions_payload.append(
            {
                "language": primary_lc,
                "language_label": lang_labels.get(primary_lc, language_label(primary_lc)),
                "file_format": (book.digital_file_type or "").upper() or None,
                "kind": "original",
            }
        )
    payload = {
        'success': True,
        'book': {
            'id': book.id,
            'title': book.title,
            'description': book.description or '',
            'genre': book.genre or '',
            'language': book.language or '',
            'language_label': lang_labels.get((book.language or '').lower(), (book.language or 'Other').title()),
            'word_count': book.word_count or 0,
            'target_audience': book.target_audience or '',
            'price': float(book.price) if book.price is not None else None,
            'currency': book.currency or 'USD',
            'cover_url': _marketplace_cover_url(book),
            'published_at': book.published_at.isoformat() if book.published_at else None,
            'created_at': book.created_at.isoformat() if book.created_at else None,
            'isbn': book.isbn,
            'isbn_display': format_isbn_display(book.isbn) if book.isbn else None,
            'publisher_name': book.publisher_name or platform_publisher_name(),
            'formats': {
                'digital': bool(book.digital_book_published and book.digital_file_path),
                'audiobook': bool(book.audiobook_published and book.has_audiobook),
                'print': print_listed(book),
            },
            'print_price': float(book.print_price) if print_listed(book) else None,
            'print_shipping_price': float(book.print_shipping_price or 0) if print_listed(book) else None,
            'print_handling_days': int(book.print_handling_days or 7) if print_listed(book) else None,
            'print_description': (book.print_description or '') if print_listed(book) else '',
            'digital_file_type': (book.digital_file_type or '').upper() if book.digital_file_type else None,
            'digital_editions': digital_editions_payload,
            'audiobook_price': float(book.audiobook_price) if book.audiobook_price is not None else None,
            'audiobook_preview_url': (
                url_for('book_platform.serve_audiobook_preview', book_id=book.id)
                if (book.audiobook_published and book.has_audiobook and book.audiobook_file_path)
                else None
            ),
            'total_sales': book.total_sales or 0,
            'author': {
                'id': author.id if author else None,
                'name': author_name,
                'user_id': author_user_id,
                'marketplace_book_count': author_listing_count,
            },
            'investment': {
                'active': bool(inv and inv.status == CampaignStatus.ACTIVE) if inv else False,
                'funded': bool(inv and inv.status == CampaignStatus.FUNDED) if inv else False,
            } if book.has_investment_campaign else None,
        },
    }
    return jsonify(payload)


@book_bp.route('/books/<int:book_id>/publish', methods=['POST'])
@book_platform_required
def publish_book(book_id):
    """Publish a book to marketplace"""
    if _author_needs_publishing_agreement(current_user.user_id):
        return jsonify({
            'error': 'Accept the Author Publishing Agreement before publishing.',
            'redirect': url_for('book_platform.author_publishing_agreement', next=request.path),
        }), 403

    book = BookProject.query.options(joinedload(BookProject.author)).get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Check if book_user exists
    if not book_user:
        return jsonify({'error': 'Book platform user profile not found'}), 404
    
    # Only author can publish
    if book.author_id != book_user.id:
        return jsonify({'error': 'Only the author can publish the book'}), 403
    
    def _as_bool(v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    payload = request.get_json(silent=True) if request.is_json else request.form
    terms_error = validate_listing_terms_payload(payload or {})
    if terms_error:
        return jsonify({'error': terms_error}), 400
    record_listing_attestation(book)

    # Validate book is ready for publishing
    if not book.price or book.price <= 0:
        return jsonify({'error': 'Please set a price before publishing'}), 400
    if not book_has_listing_cover(book):
        return jsonify({'error': 'Please add a cover image before publishing to the marketplace.'}), 400

    was_already_published = book.status == BookStatus.PUBLISHED
    book.status = BookStatus.PUBLISHED
    book.published_at = datetime.now(timezone.utc)
    
    # Mark investment campaign as FUNDED when book is published (investments stop at publication)
    if book.investment_campaign and book.investment_campaign.status == CampaignStatus.ACTIVE:
        book.investment_campaign.status = CampaignStatus.FUNDED
        if not book.investment_campaign.funded_at:
            book.investment_campaign.funded_at = datetime.now(timezone.utc)
        from glconnect.platform_fee_policy import apply_campaign_fee_terms
        apply_campaign_fee_terms(book.investment_campaign, db)

    from glconnect.isbn_pool_service import assign_marketplace_isbn_if_needed, IsbnPoolError

    try:
        assign_marketplace_isbn_if_needed(book)
    except IsbnPoolError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 503
    
    db.session.commit()

    if not was_already_published:
        from glconnect.patron_support_service import notify_patrons_book_listed
        try:
            notify_patrons_book_listed(book, db)
        except Exception as exc:
            logger.warning('Patron listing notifications failed for book %s: %s', book.id, exc)

    resp = {'success': True}
    author_is_current = (
        book.author
        and getattr(book.author, 'user_id', None) == current_user.user_id
    )
    if (
        not was_already_published
        and author_is_current
        and author_needs_stripe_payout_setup(book.author)
    ):
        view_path = url_for('book_platform.view_book', book_id=book_id)
        resp['payout_setup_required'] = True
        resp['redirect'] = url_for('book_platform.author_payout_setup', next=view_path)
    return jsonify(resp)


@book_bp.route('/books/<int:book_id>/print-orders', methods=['GET'])
@writer_or_book_platform_required
def book_print_orders(book_id, user_profile, profile_type):
    """Author: orders to fulfill for print edition."""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        flash('Only the author can view print orders.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    orders = (
        BookPrintOrder.query.filter_by(book_project_id=book_id)
        .join(BookPurchase, BookPrintOrder.book_purchase_id == BookPurchase.id)
        .order_by(BookPrintOrder.created_at.desc())
        .all()
    )
    pending_count = sum(
        1 for o in orders if o.status == PrintOrderStatus.PENDING_FULFILLMENT
    )
    return render_template(
        'book_platform/print_orders.html',
        book=book,
        orders=orders,
        pending_count=pending_count,
    )


@book_bp.route('/books/<int:book_id>/print-orders/<int:order_id>/ship', methods=['POST'])
@writer_or_book_platform_required
def mark_print_order_shipped(book_id, order_id, user_profile, profile_type):
    """Author marks a print order shipped."""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    order = BookPrintOrder.query.filter_by(id=order_id, book_project_id=book_id).first_or_404()
    if order.status != PrintOrderStatus.PENDING_FULFILLMENT:
        return jsonify({'success': False, 'error': 'Order is not awaiting shipment'}), 400
    data = request.get_json(silent=True) or {}
    tracking = (data.get('tracking_number') or request.form.get('tracking_number') or '').strip()
    order.tracking_number = tracking[:200] if tracking else None
    order.status = PrintOrderStatus.SHIPPED
    order.shipped_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': 'Marked as shipped.' + (f' Tracking: {tracking}' if tracking else ''),
    })


@book_bp.route('/books/<int:book_id>/unpublish', methods=['POST'])
@login_required
def unpublish_book(book_id):
    """Unpublish a book from marketplace (change status to DRAFT)"""
    book = BookProject.query.get_or_404(book_id)

    if current_user.role != 'admin':
        user_profile, profile_type = _profile_for_ink_permission_checks()
        if not user_profile:
            return jsonify({'error': 'You need a Writer profile to manage books. Please create a Writer profile in Ink Studio.'}), 403
        author_id = get_profile_id(user_profile, profile_type)
        if author_id is None:
            return jsonify({'error': 'Profile configuration error. Please ensure you have a Writer or Ink Studio profile.'}), 403
        if book.author_id != author_id:
            return jsonify({'error': 'Only the author or admin can unpublish the book'}), 403
    
    # Only unpublish if currently published
    if book.status != BookStatus.PUBLISHED:
        return jsonify({'error': 'Book is not currently published'}), 400
    
    # Change status to DRAFT (removes from marketplace but keeps the book)
    book.status = BookStatus.DRAFT
    book.updated_at = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Book unpublished successfully. It has been removed from the marketplace but can be republished anytime.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@book_bp.route('/books/<int:book_id>/remove-listing', methods=['POST'])
@login_required
def remove_listing(book_id):
    """Remove marketplace visibility while keeping the book and relations."""
    book = BookProject.query.get_or_404(book_id)

    if current_user.role != 'admin':
        user_profile, profile_type = _profile_for_ink_permission_checks()
        if not user_profile:
            return jsonify({'error': 'You need a Writer profile to manage books. Please create a Writer profile in Ink Studio.'}), 403
        author_id = get_profile_id(user_profile, profile_type)
        if author_id is None:
            return jsonify({'error': 'Profile configuration error. Please ensure you have a Writer or Ink Studio profile.'}), 403
        if book.author_id != author_id:
            return jsonify({'error': 'Only the author or admin can remove this listing'}), 403

    listing_was_live = False
    if book.digital_file_path:
        if book.digital_book_published:
            book.digital_book_published = False
            listing_was_live = True
        if book.audiobook_published:
            book.audiobook_published = False
            listing_was_live = True
    else:
        if book.status == BookStatus.PUBLISHED:
            book.status = BookStatus.DRAFT
            listing_was_live = True

    if not listing_was_live:
        return jsonify({'error': 'This book is not currently live in the marketplace'}), 400

    book.updated_at = datetime.now(timezone.utc)
    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Listing removed from marketplace. Your book and relationships are preserved.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@book_bp.route('/admin', strict_slashes=False)
@login_required
def admin_hub():
    """Single entry point for all admin tasks – redirects to the full admin panel."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    return redirect(url_for('book_platform.admin_books'))

@book_bp.route('/admin/books')
@login_required
def admin_books():
    """Admin panel: one place for all approval and verification tasks (books, podcasts, songs, reviewers, word contributions, community dictionary, YouTube download)."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    books = DatabaseOptimizer.get_admin_books_data()
    return render_template('book_platform/admin_books.html', books=books)


@book_bp.route('/admin/books/delete-test-books', methods=['POST'])
@login_required
def admin_delete_test_books():
    """Admin: delete all books with 'test' in the title (removes test data from platform)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    test_books = BookProject.query.filter(BookProject.title.ilike('%test%')).all()
    
    deleted = []
    for book in test_books:
        book_id = book.id
        title = book.title
        try:
            campaign = InvestmentCampaign.query.filter_by(book_project_id=book_id).first()
            if campaign:
                investments = BookInvestment.query.filter_by(campaign_id=campaign.id).all()
                investment_ids = [inv.id for inv in investments]
                if investment_ids:
                    InvestmentPayout.query.filter(InvestmentPayout.investment_id.in_(investment_ids)).delete(synchronize_session=False)
                inv_ids = [inv.id for inv in investments]
                RefundRequest.query.filter(RefundRequest.investment_id.in_(inv_ids)).delete(synchronize_session=False)
                BookInvestment.query.filter_by(campaign_id=campaign.id).delete()
                AuthorCampaignPayoutRequest.query.filter_by(campaign_id=campaign.id).delete()
                db.session.delete(campaign)
            BookSale.query.filter_by(book_project_id=book_id).delete()
            BookPurchase.query.filter_by(book_project_id=book_id).delete()
            _delete_legacy_book_cart_rows(book_id)
            _delete_reader_annotations_for_book(book_id)
            AudioGenerationTask.query.filter_by(book_project_id=book_id).delete()
            RealtimeSession.query.filter_by(book_project_id=book_id).delete()
            BookComment.query.filter_by(book_project_id=book_id).delete()
            collab_ids_subq = db.session.query(BookCollaboration.id).filter_by(book_project_id=book_id).subquery()
            CollaborationInvitation.query.filter(CollaborationInvitation.collaboration_id.in_(collab_ids_subq)).delete(synchronize_session=False)
            BookCollaboration.query.filter_by(book_project_id=book_id).delete()
            BookAnalytics.query.filter_by(book_project_id=book_id).delete()
            BookNotification.query.filter_by(book_project_id=book_id).delete()
            BookReview.query.filter_by(book_project_id=book_id).delete()
            ReviewRequest.query.filter_by(book_project_id=book_id).delete()
            delete_book_chapter_version_graph_for_project(book_id)
            AudiobookChapter.query.filter_by(book_project_id=book_id).delete()
            db.session.delete(book)
            deleted.append(title)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting test book {book_id}: {e}", exc_info=True)
            return jsonify({'error': f'Failed to delete "{title}": {str(e)}'}), 500
    
    db.session.commit()
    if deleted:
        flash(f'Deleted {len(deleted)} test book(s): {", ".join(deleted)}', 'success')
    else:
        flash('No test books found to delete.', 'info')
    return redirect(url_for('book_platform.admin_books'))


# Admin Reviewer Management Routes
@book_bp.route('/admin/reviewers')
@login_required
def admin_reviewers():
    """Deprecated: reviewer management removed from product."""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    flash('Reviewer management has been retired. Book reviewers are no longer part of the platform.', 'info')
    return redirect(url_for('book_platform.admin_books'))

@book_bp.route('/admin/reviewers/<int:reviewer_id>/approve', methods=['POST'])
@login_required
def approve_reviewer(reviewer_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return jsonify({'success': False, 'message': 'Reviewer feature has been retired.'}), 410

@book_bp.route('/admin/reviewers/<int:reviewer_id>/reject', methods=['POST'])
@login_required
def reject_reviewer(reviewer_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return jsonify({'success': False, 'message': 'Reviewer feature has been retired.'}), 410

@book_bp.route('/admin/reviewers/<int:reviewer_id>/suspend', methods=['POST'])
@login_required
def suspend_reviewer(reviewer_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    return jsonify({'success': False, 'message': 'Reviewer feature has been retired.'}), 410


def _restore_library_visibility_for_owned_format(user_id: int, book_id: int, purchase_format: str) -> bool:
    """If this format was hidden from My Library, show it again. Returns True if DB state changed."""
    rec = LibraryBookHide.query.filter_by(user_id=user_id, book_project_id=book_id).first()
    if not rec:
        return False
    pf = (purchase_format or 'digital').lower().strip()
    changed = False
    if pf == 'digital':
        if rec.hide_ebook:
            rec.hide_ebook = False
            changed = True
    elif pf == 'audiobook':
        if rec.hide_audiobook:
            rec.hide_audiobook = False
            changed = True
    elif pf == 'bundle':
        if rec.hide_ebook or rec.hide_audiobook:
            rec.hide_ebook = False
            rec.hide_audiobook = False
            changed = True
    else:
        if rec.hide_ebook:
            rec.hide_ebook = False
            changed = True
    if not rec.hide_ebook and not rec.hide_audiobook:
        db.session.delete(rec)
        changed = True
    return changed


@book_bp.route('/library', methods=['GET'])
@login_required
def my_library():
    """Library for the logged-in user: completed purchases (ebook / audiobook). Empty if none.

    Purchases may reference the account as buyer_user_id (users.user_id) and/or buyer_id
    (BookPlatformUser.id on older rows). Authors and readers use the same User row when
    they buy; we OR those predicates so all completed sales for this login show up.
    """
    uid = current_user.user_id
    bp_user = BookPlatformUser.query.filter_by(user_id=uid).first()
    bp_pk = bp_user.id if bp_user else None
    match_login = [BookPurchase.buyer_user_id == uid]
    if bp_pk is not None:
        match_login.append(BookPurchase.buyer_id == bp_pk)
    purchases = BookPurchase.query.filter(
        BookPurchase.status == TransactionStatus.COMPLETED,
        db.or_(*match_login),
    ).order_by(BookPurchase.purchased_at.desc(), BookPurchase.created_at.desc()).all()

    hidden_map = {h.book_project_id: h for h in LibraryBookHide.query.filter_by(user_id=uid).all()}

    purchase_book_ids = {p.book_project_id for p in purchases}
    books_by_id = {}
    if purchase_book_ids:
        books_by_id = {
            b.id: b
            for b in BookProject.query.options(
                joinedload(BookProject.author).joinedload(BookPlatformUser.user)
            ).filter(BookProject.id.in_(purchase_book_ids)).all()
        }

    by_book = {}
    for p in purchases:
        bid = p.book_project_id
        hide = hidden_map.get(bid)
        hide_e = bool(hide.hide_ebook) if hide else False
        hide_a = bool(hide.hide_audiobook) if hide else False
        fmt = (getattr(p, 'purchase_format', 'digital') or 'digital').lower()
        from_digital = fmt in ('digital', 'bundle') and not hide_e
        from_audio = fmt in ('audiobook', 'bundle') and not hide_a
        if not from_digital and not from_audio:
            continue
        b = books_by_id.get(bid)
        if not b:
            continue
        row = by_book.get(bid)
        if not row:
            row = {
                'book': b,
                'has_digital': False,
                'has_audiobook': False,
                'latest_purchase_at': p.purchased_at or p.created_at,
            }
            by_book[bid] = row
        if from_digital:
            row['has_digital'] = True
        if from_audio:
            row['has_audiobook'] = True
        pt = p.purchased_at or p.created_at
        if pt and (row['latest_purchase_at'] is None or pt > row['latest_purchase_at']):
            row['latest_purchase_at'] = pt

    items = sorted(by_book.values(), key=lambda x: x['latest_purchase_at'] or datetime.now(timezone.utc), reverse=True)
    highlight_book_id = request.args.get('book_id', type=int)
    return render_template(
        'book_platform/my_library.html',
        items=items,
        marketplace_cover_url=_marketplace_cover_url,
        highlight_book_id=highlight_book_id,
    )


@book_bp.route('/library/books/<int:book_id>/hide', methods=['POST'])
@login_required
def library_hide_book(book_id):
    """Hide ebook and/or audiobook on My Library for this account (purchase history unchanged)."""
    uid = current_user.user_id
    fmt = (request.form.get('format') or '').strip().lower()
    bp_user = BookPlatformUser.query.filter_by(user_id=uid).first()
    bp_pk = bp_user.id if bp_user else None
    match_login = [BookPurchase.buyer_user_id == uid]
    if bp_pk is not None:
        match_login.append(BookPurchase.buyer_id == bp_pk)
    purchases = BookPurchase.query.filter(
        BookPurchase.book_project_id == book_id,
        BookPurchase.status == TransactionStatus.COMPLETED,
        db.or_(*match_login),
    ).all()
    if not purchases:
        flash('That title is not in your library.', 'warning')
        return redirect(url_for('book_platform.my_library'))

    owns_digital = False
    owns_audiobook = False
    for p in purchases:
        pf = (getattr(p, 'purchase_format', 'digital') or 'digital').lower()
        if pf in ('digital', 'bundle'):
            owns_digital = True
        if pf in ('audiobook', 'bundle'):
            owns_audiobook = True

    if fmt == 'ebook':
        if not owns_digital:
            flash('You do not have an ebook for that title.', 'warning')
            return redirect(url_for('book_platform.my_library'))
    elif fmt == 'audiobook':
        if not owns_audiobook:
            flash('You do not have an audiobook for that title.', 'warning')
            return redirect(url_for('book_platform.my_library'))
    else:
        flash('Choose ebook or audiobook to remove from this list.', 'warning')
        return redirect(url_for('book_platform.my_library'))

    rec = LibraryBookHide.query.filter_by(user_id=uid, book_project_id=book_id).first()
    if not rec:
        rec = LibraryBookHide(
            user_id=uid,
            book_project_id=book_id,
            hide_ebook=False,
            hide_audiobook=False,
        )
        db.session.add(rec)
    if fmt == 'ebook':
        rec.hide_ebook = True
        _delete_reader_annotations_for_user_book(uid, book_id)
    else:
        rec.hide_audiobook = True
    db.session.commit()
    label = 'Ebook' if fmt == 'ebook' else 'Audiobook'
    flash(f'{label} hidden from My Library. Your purchase is still on file.', 'info')
    return redirect(url_for('book_platform.my_library'))


@book_bp.route('/library/books/<int:book_id>/read', methods=['GET'])
@login_required
def library_read_ebook(book_id):
    """Minimal reader for buyers (and authors): full manuscript text + download only."""
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user),
    ).get_or_404(book_id)

    user_id = current_user.user_id
    if not _library_reader_user_has_ebook_access(book, user_id):
        flash('You must purchase this ebook to read it here.', 'error')
        return redirect(url_for('book_platform.marketplace'))

    reader_pages = build_library_reader_pages(book)

    total_pages = len(reader_pages)
    page_idx = request.args.get('ch', type=int)
    if page_idx is None:
        page_idx = 0
    if total_pages:
        page_idx = max(0, min(page_idx, total_pages - 1))
    else:
        page_idx = 0
    current_page = reader_pages[page_idx] if total_pages else None

    total_words = 0
    for p in reader_pages:
        chunk = (p.get('plain') or '').strip()
        if not chunk and p.get('html'):
            chunk = re.sub(r'<[^>]+>', ' ', p.get('html') or '')
        if chunk:
            total_words += len([w for w in re.split(r'\s+', chunk.strip()) if w])
    reading_minutes = max(1, round(total_words / 200)) if total_words else None

    audiobook_player_url = None
    if book.has_audiobook and _user_has_audiobook_access(book, user_id):
        audiobook_player_url = url_for('book_platform.audiobook_player', book_id=book.id)

    return render_template(
        'book_platform/library_read_ebook.html',
        book=book,
        reader_pages=reader_pages,
        current_page=current_page,
        page_idx=page_idx,
        total_pages=total_pages,
        download_url=url_for('book_platform.download_digital_book', book_id=book.id),
        library_url=url_for('book_platform.my_library'),
        audiobook_player_url=audiobook_player_url,
        reading_word_count=total_words,
        reading_minutes=reading_minutes,
        reader_annotations_url=url_for('book_platform.library_reader_annotations', book_id=book.id),
        reader_search_index_url=url_for('book_platform.library_reader_search_index', book_id=book.id),
        reader_read_url_base=url_for('book_platform.library_read_ebook', book_id=book.id),
    )


@book_bp.route('/library/books/<int:book_id>/annotations', methods=['GET', 'POST'])
@login_required
def library_reader_annotations(book_id):
    """List or create persisted reader highlights / bookmarks / notes."""
    book = BookProject.query.get_or_404(book_id)
    if not _library_reader_user_has_ebook_access(book, current_user.user_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    if request.method == 'GET':
        rows = (
            ReaderAnnotation.query.filter_by(
                user_id=current_user.user_id,
                book_project_id=book_id,
            )
            .order_by(ReaderAnnotation.section_index.asc(), ReaderAnnotation.start_offset.asc())
            .all()
        )
        return jsonify({
            'success': True,
            'annotations': [_reader_annotation_to_dict(a) for a in rows],
        })

    data = request.get_json(silent=True) or {}
    kind = (data.get('kind') or '').strip().lower()
    if kind not in ('highlight', 'bookmark'):
        return jsonify({'success': False, 'error': 'kind must be highlight or bookmark'}), 400

    try:
        section_index = int(data.get('section_index', -1))
    except (TypeError, ValueError):
        section_index = -1
    pages = build_library_reader_pages(book)
    if section_index < 0 or section_index >= len(pages):
        return jsonify({'success': False, 'error': 'Invalid section_index'}), 400

    start_offset = max(0, int(data.get('start_offset', 0)))
    end_offset = max(0, int(data.get('end_offset', 0)))
    quote_text = (data.get('quote_text') or None)
    if quote_text is not None:
        quote_text = quote_text.strip()[:50000]
    note_text = (data.get('note_text') or None)
    if note_text is not None:
        note_text = note_text.strip()[:20000]

    if kind == 'highlight':
        if not quote_text:
            return jsonify({'success': False, 'error': 'quote_text is required for highlights'}), 400
        if end_offset <= start_offset:
            return jsonify({'success': False, 'error': 'Invalid offsets for highlight'}), 400

    if kind == 'bookmark':
        start_offset = 0
        end_offset = 0
        quote_text = None

    ann = ReaderAnnotation(
        user_id=current_user.user_id,
        book_project_id=book_id,
        section_index=section_index,
        start_offset=start_offset,
        end_offset=end_offset,
        quote_text=quote_text,
        note_text=note_text,
        kind=kind,
    )
    db.session.add(ann)
    db.session.commit()
    return jsonify({'success': True, 'annotation': _reader_annotation_to_dict(ann)})


@book_bp.route('/library/books/<int:book_id>/annotations/<int:anno_id>', methods=['PATCH', 'DELETE'])
@login_required
def library_reader_annotation_detail(book_id, anno_id):
    """Update note text or delete a reader annotation."""
    book = BookProject.query.get_or_404(book_id)
    if not _library_reader_user_has_ebook_access(book, current_user.user_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    ann = ReaderAnnotation.query.filter_by(
        id=anno_id,
        user_id=current_user.user_id,
        book_project_id=book_id,
    ).first()
    if not ann:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    if request.method == 'DELETE':
        db.session.delete(ann)
        db.session.commit()
        return jsonify({'success': True})

    data = request.get_json(silent=True) or {}
    note_text = data.get('note_text')
    if note_text is None:
        return jsonify({'success': False, 'error': 'note_text required'}), 400
    ann.note_text = (str(note_text).strip()[:20000]) or None
    db.session.commit()
    return jsonify({'success': True, 'annotation': _reader_annotation_to_dict(ann)})


@book_bp.route('/library/books/<int:book_id>/reader-search-index', methods=['GET'])
@login_required
def library_reader_search_index(book_id):
    """Plain text per section for full-book search (same segmentation as the reader)."""
    book = BookProject.query.get_or_404(book_id)
    if not _library_reader_user_has_ebook_access(book, current_user.user_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    pages = build_library_reader_pages(book)
    sections = []
    for i, p in enumerate(pages):
        plain = (p.get('plain') or '').strip()
        if not plain and p.get('html'):
            plain = re.sub(r'<[^>]+>', ' ', p.get('html') or '')
            plain = re.sub(r'\s+', ' ', plain).strip()
        sections.append({
            'index': i,
            'title': p.get('title') or f'Section {i + 1}',
            'plain': plain or '',
        })
    return jsonify({'success': True, 'sections': sections})


def _create_print_order_from_checkout_session(purchase, book, session):
    """Create BookPrintOrder from Stripe Checkout session shipping (print purchases only)."""
    if normalize_purchase_format(getattr(purchase, 'purchase_format', None)) != 'print':
        return None
    existing = BookPrintOrder.query.filter_by(book_purchase_id=purchase.id).first()
    if existing:
        return existing
    shipping = session.get('shipping_details') or session.get('shipping') or {}
    if isinstance(shipping, dict) and shipping.get('address'):
        addr = shipping.get('address') or {}
        ship_name = shipping.get('name') or ''
    else:
        addr = {}
        ship_name = ''
    if not addr.get('line1'):
        cd = session.get('customer_details') or {}
        ship_name = ship_name or cd.get('name') or purchase.get_buyer_name() if hasattr(purchase, 'get_buyer_name') else ''
        addr = cd.get('address') or addr
    if not addr.get('line1'):
        logger.warning("Print purchase %s: no shipping address on Stripe session", purchase.id)
        return None
    book_amt = float(book.print_price or 0)
    ship_amt = print_shipping_amount(book)
    order = BookPrintOrder(
        book_purchase_id=purchase.id,
        book_project_id=book.id,
        book_amount=book_amt,
        shipping_amount=ship_amt,
        shipping_name=(ship_name or '')[:200] or None,
        shipping_line1=(addr.get('line1') or '')[:200],
        shipping_line2=(addr.get('line2') or '')[:200] or None,
        shipping_city=(addr.get('city') or '')[:100],
        shipping_state=(addr.get('state') or '')[:100] or None,
        shipping_postal=(addr.get('postal_code') or addr.get('zip') or '')[:30],
        shipping_country=(addr.get('country') or 'US')[:2].upper(),
        status=PrintOrderStatus.PENDING_FULFILLMENT,
    )
    db.session.add(order)
    return order


@book_bp.route('/books/<int:book_id>/purchase', methods=['POST'])
@login_required
def purchase_book(book_id):
    """Purchase a book — accessible to all logged-in users (including the author)."""
    # Wrap entire function in try-except to ensure JSON responses
    try:
        # Resolve app without referencing bare `current_app` — a nested `import current_app` in this
        # function would shadow the name and break even this line (UnboundLocalError).
        import flask as _flask_mod
        flask_app = _flask_mod.current_app._get_current_object()
        # Get custom amount and purchase type from request
        request_data = request.get_json() or {}
        custom_amount = request_data.get('custom_amount')
        purchase_type = normalize_purchase_format(request_data.get('purchase_type') or 'digital')
        
        # Initialize variables that might be needed in error handling
        buyer_user_id = current_user.user_id if current_user.is_authenticated else None
        if not buyer_user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
        from glconnect.book_platform_models import BookPlatformUser
        
        # Eager load author information to ensure fresh data from database
        book = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).get_or_404(book_id)
        
        # Buyers only need a user account - NO profile required
        buyer_user_id = current_user.user_id
        
        # Check if buyer_user_id column exists - if yes, we don't need BookPlatformUser profile
        # If no, we need to create one as a workaround
        has_buyer_user_id_col = False
        try:
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('book_purchases')]
            has_buyer_user_id_col = 'buyer_user_id' in columns
            logger.info(f"Column check: buyer_user_id exists = {has_buyer_user_id_col}")
        except Exception as col_check_error:
            logger.warning(f"Could not check for buyer_user_id column: {col_check_error}, assuming it doesn't exist")
            has_buyer_user_id_col = False
        
        # Always get buyer_id as fallback (even if buyer_user_id column exists)
        # This ensures we have a fallback if the column check was wrong or creation fails
        buyer_id = None
        bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
        if bp_user:
            buyer_id = bp_user.id
            logger.info(f"Found existing BookPlatformUser {buyer_id} for user {buyer_user_id}")
        elif not has_buyer_user_id_col:
            # Migration not run - need BookPlatformUser profile as workaround
            logger.info(f"buyer_user_id column not found - creating BookPlatformUser profile as workaround")
            try:
                # Get Writer profile info if user is an author
                from glconnect.models import Writer
                writer = Writer.query.filter_by(user_id=buyer_user_id).first()
                
                bp_user = BookPlatformUser(
                    user_id=buyer_user_id,
                    pen_name=writer.writer_name if writer else current_user.username,
                    bio=writer.bio if writer else "Reader",
                    profile_picture=writer.profile_picture if writer else "static/uploads/default_writer.jpg"
                )
                db.session.add(bp_user)
                db.session.commit()
                buyer_id = bp_user.id
                logger.info(f"✅ Created BookPlatformUser {buyer_id} as workaround (migration not run)")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to create BookPlatformUser: {str(e)}", exc_info=True)
                return jsonify({'error': f'Failed to process purchase: {str(e)}'}), 500
        
        if has_buyer_user_id_col:
            logger.info(f"buyer_user_id column exists - will try using user_id directly (buyer_id={buyer_id} available as fallback)")
        else:
            logger.info(f"buyer_user_id column not found - using buyer_id={buyer_id}")
        
        # Validate purchase type and set price
        if purchase_type == 'print':
            if not print_listed(book):
                return jsonify({'error': 'Print edition is not available for this book.'}), 400
            if not is_book_published(book):
                return jsonify({'error': 'This book is not listed on the marketplace yet.'}), 400
            base_price = base_price_for_format(book, 'print')
        elif purchase_type == 'audiobook':
            if not book.has_audiobook or not book.audiobook_published:
                return jsonify({'error': 'This book does not have an audiobook available for purchase.'}), 400
            if not book.audiobook_price or book.audiobook_price <= 0:
                return jsonify({'error': 'Audiobook price is not set. Please contact the author.'}), 400
            base_price = base_price_for_format(book, 'audiobook')
        elif purchase_type == 'bundle':
            if not book.has_audiobook or not book.audiobook_published:
                return jsonify({'error': 'Bundle requires an audiobook. This book does not have one available.'}), 400
            if not book.audiobook_price or book.audiobook_price <= 0:
                return jsonify({'error': 'Audiobook price is not set. Cannot create bundle.'}), 400
            base_price = base_price_for_format(book, 'bundle')
        else:
            base_price = base_price_for_format(book, 'digital')
        
        # Validate book has a price for the selected format
        if not base_price or base_price <= 0:
            return jsonify({'error': f'This {purchase_type} is not available for purchase. Please contact the author.'}), 400
        
        # Validate book has an author
        if not book.author_id:
            logger.error(f"Book {book_id} has no author_id - cannot create sale")
            return jsonify({'error': 'Book has no author. Cannot process purchase.'}), 400
        
        # Digital/bundle require ebook list price; print uses print_price only
        if purchase_type in ('digital', 'bundle') and (not book.price or book.price <= 0):
            logger.error(f"Book {book_id} has no digital price: {book.price}")
            return jsonify({'error': 'This book is not available for purchase. Please contact the author.'}), 400
        
        list_checkout_total = total_checkout_amount(book, purchase_type)
        
        # Validate and set payment amount (custom amount must be >= checkout total for this format)
        if custom_amount is not None:
            try:
                custom_amount = float(custom_amount)
                if custom_amount < list_checkout_total:
                    return jsonify({'error': f'Payment amount must be at least ${list_checkout_total:.2f}'}), 400
                payment_amount = custom_amount
                logger.info(f"Using custom payment amount: ${payment_amount:.2f} (base: ${list_checkout_total:.2f} for {purchase_type})")
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid payment amount'}), 400
        else:
            payment_amount = list_checkout_total
            logger.info(f"Using checkout total for {purchase_type}: ${payment_amount:.2f}")
        
        # Stripe Connect: require author connected account unless dev fallback is enabled
        author_connect_id = (
            (book.author.stripe_connect_account_id or "").strip()
            if book.author
            else ""
        )
        payment_intent_data, connect_checkout_error = marketplace_book_payment_intent_data(
            book=book,
            purchase_type=purchase_type,
            payment_amount=payment_amount,
            stripe_connect_account_id=author_connect_id or None,
        )
        if connect_checkout_error:
            return jsonify({'error': connect_checkout_error}), 400
        
        # Ensure currency is set
        if not book.currency:
            book.currency = 'USD'
        
        # SIMPLIFIED: Just use ORM - it handles enums automatically, no casting needed!
        # buyer_user_id is optional (nullable), so we can just not set it if column doesn't exist
        logger.info(f"=== STARTING PURCHASE for book {book_id} ===")
        logger.info(f"buyer_user_id={buyer_user_id}, buyer_id={buyer_id}")
        
        # Ensure we have buyer_id (create BookPlatformUser if needed)
        if not buyer_id:
            bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
            if not bp_user:
                from glconnect.models import Writer
                writer = Writer.query.filter_by(user_id=buyer_user_id).first()
                bp_user = BookPlatformUser(
                    user_id=buyer_user_id,
                    pen_name=writer.writer_name if writer else current_user.username,
                    bio=writer.bio if writer else "Reader",
                    profile_picture=writer.profile_picture if writer else "static/uploads/default_writer.jpg"
                )
                db.session.add(bp_user)
                db.session.commit()
            buyer_id = bp_user.id
        
        # SIMPLIFIED: Just use ORM - no enum casting, no raw SQL complexity!
        # ORM automatically handles PostgreSQL enum types
        purchase = BookPurchase(
            buyer_id=buyer_id,
            book_project_id=book_id,
            amount=payment_amount,
            currency=book.currency,
            status=TransactionStatus.PENDING,  # ORM handles enum automatically - no casting!
            purchase_format=purchase_type
        )
        # Add to session and try to flush
        # If buyer_user_id column doesn't exist, SQLAlchemy will fail because it's in the model
        # In that case, we'll use raw SQL to insert without that column
        purchase_already_committed = False  # Track if purchase was committed via raw SQL
        db.session.add(purchase)
        try:
            db.session.flush()  # Flush to get the ID, but don't commit yet
        except Exception as flush_error:
            # Check if it's a missing buyer_user_id column error
            if 'buyer_user_id' in str(flush_error).lower() and 'does not exist' in str(flush_error).lower():
                logger.warning(f"buyer_user_id column doesn't exist, using raw SQL insert: {flush_error}")
                db.session.rollback()
                
                # Use raw SQL to insert without buyer_user_id column
                from sqlalchemy import text
                import uuid as uuid_lib
                from datetime import datetime, timezone
                
                purchase_uuid = str(uuid_lib.uuid4())
                
                # Get buyer username and full name from the user
                buyer_username = None
                buyer_full_name = None
                try:
                    if current_user and current_user.is_authenticated:
                        buyer_username = current_user.username
                        buyer_full_name = getattr(current_user, 'full_name', None) or current_user.username
                    # Also try to get from BookPlatformUser
                    if buyer_id:
                        bp_user = BookPlatformUser.query.get(buyer_id)
                        if bp_user:
                            if not buyer_username:
                                buyer_username = bp_user.pen_name or (bp_user.user.username if bp_user.user else None)
                            if not buyer_full_name:
                                buyer_full_name = bp_user.pen_name or (bp_user.user.username if bp_user.user else None)
                except Exception as name_error:
                    logger.warning(f"Could not get buyer username/full name: {name_error}")
                
                # Check which columns exist - buyer_username, buyer_full_name, purchase_format might not exist
                from sqlalchemy import inspect as sql_inspect
                inspector = sql_inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('book_purchases')]
                has_buyer_username_col = 'buyer_username' in columns
                has_buyer_full_name_col = 'buyer_full_name' in columns
                has_purchase_format_col = 'purchase_format' in columns
                
                # Build INSERT statement with only existing columns
                base_params = {
                    'uuid': purchase_uuid, 'amount': payment_amount, 'currency': book.currency or 'USD',
                    'status': 'PENDING', 'book_project_id': book_id, 'buyer_id': buyer_id,
                    'created_at': datetime.now(timezone.utc)
                }
                if has_buyer_username_col and has_buyer_full_name_col:
                    base_params['buyer_username'] = buyer_username or ''
                    base_params['buyer_full_name'] = buyer_full_name or ''
                if has_purchase_format_col:
                    base_params['purchase_format'] = purchase_type
                
                if has_buyer_username_col and has_buyer_full_name_col and has_purchase_format_col:
                    result = db.session.execute(
                        text("""
                            INSERT INTO book_purchases (uuid, amount, currency, status, book_project_id, buyer_id, buyer_username, buyer_full_name, purchase_format, created_at)
                            VALUES (:uuid, :amount, :currency, :status, :book_project_id, :buyer_id, :buyer_username, :buyer_full_name, :purchase_format, :created_at)
                            RETURNING id
                        """),
                        base_params
                    )
                elif has_buyer_username_col and has_buyer_full_name_col:
                    result = db.session.execute(
                        text("""
                            INSERT INTO book_purchases (uuid, amount, currency, status, book_project_id, buyer_id, buyer_username, buyer_full_name, created_at)
                            VALUES (:uuid, :amount, :currency, :status, :book_project_id, :buyer_id, :buyer_username, :buyer_full_name, :created_at)
                            RETURNING id
                        """),
                        base_params
                    )
                else:
                    insert_cols = "uuid, amount, currency, status, book_project_id, buyer_id, created_at"
                    insert_vals = ":uuid, :amount, :currency, :status, :book_project_id, :buyer_id, :created_at"
                    if has_purchase_format_col:
                        insert_cols += ", purchase_format"
                        insert_vals += ", :purchase_format"
                    result = db.session.execute(
                        text(f"INSERT INTO book_purchases ({insert_cols}) VALUES ({insert_vals}) RETURNING id"),
                        base_params
                    )
                purchase_id = result.scalar()
                # CRITICAL: Don't commit yet - commit purchase and BookSale together
                # This ensures if BookSale creation fails, purchase is also rolled back
                # The purchase is in the transaction but not committed yet
                logger.info(f"✅ Purchase inserted via raw SQL (in transaction, not committed), ID={purchase_id}")
                
                # Ensure buyer_username and buyer_full_name are defined (they were set above)
                # If they're still None, set defaults
                if buyer_username is None:
                    buyer_username = ''
                if buyer_full_name is None:
                    buyer_full_name = ''
                
                # Create a minimal purchase object for the rest of the code
                # Don't query back from DB as SQLAlchemy will try to SELECT all columns including buyer_user_id
                class PurchaseObj:
                    def __init__(self, purchase_id, buyer_id, amount, currency, username='', full_name='', purchase_format='digital'):
                        self.id = purchase_id
                        self.buyer_id = buyer_id
                        self.amount = amount
                        self.currency = currency
                        self.status = TransactionStatus.PENDING
                        self.purchase_format = purchase_format
                        self.buyer_username = username
                        self.buyer_full_name = full_name
                
                purchase = PurchaseObj(purchase_id, buyer_id, payment_amount, book.currency or 'USD', buyer_username, buyer_full_name, purchase_type)
                logger.info(f"✅ Purchase object created (ID={purchase.id}), will commit with BookSale")
                purchase_already_committed = False  # Will commit purchase and sale together
            else:
                # Different error - re-raise it
                raise
        
        # Populate buyer info AFTER adding to session (so relationships are available)
        # This will set buyer_username and buyer_full_name from the database
        # Only try if purchase is an ORM object (not PurchaseObj)
        if hasattr(purchase, 'populate_buyer_info'):
            try:
                purchase.populate_buyer_info()
            except Exception as populate_error:
                # If populate_buyer_info fails, log but don't fail - buyer_id is sufficient
                logger.warning(f"Could not populate buyer info: {populate_error}, continuing anyway")
        
        if not purchase_already_committed:
            logger.info(f"✅ Created purchase using ORM (enum handled automatically), ID={purchase.id}")
        
        # Log purchase info (handle both ORM and minimal objects)
        purchase_info = f"ID={purchase.id}, amount=${getattr(purchase, 'amount', book.price)}"
        if hasattr(purchase, 'buyer_id'):
            purchase_info += f", buyer_id={purchase.buyer_id}"
        if hasattr(purchase, 'buyer_user_id'):
            purchase_info += f", buyer_user_id={purchase.buyer_user_id}"
        logger.info(f"Purchase object created: {purchase_info}")
        
        # Purchase is already created as PENDING - no need to update status
        # (Status is set in BookPurchase constructor above)
        
        # Don't commit purchase yet - we'll commit it with BookSale
        # This ensures both are in the same transaction (atomic operation)
        # If BookSale creation fails, purchase will also be rolled back
        logger.info(f"✅ Purchase ready (not yet committed), ID={purchase.id}")
        logger.info(f"   Will commit purchase and BookSale together for atomicity")
        
        # Create BookSale and trigger revenue distribution immediately, regardless of purchase status
        # This ensures sales and investment returns are tracked even for PENDING purchases
        logger.info("=" * 80)
        logger.info("🔍🔍🔍 MAIN PATH: Starting BookSale creation process")
        logger.info("=" * 80)
        logger.info(f"Purchase ID: {purchase.id}")
        logger.info(f"Purchase Type: {type(purchase).__name__}")
        logger.info(f"Purchase Amount: ${getattr(purchase, 'amount', 'N/A')}")
        logger.info(f"Book ID: {book_id}")
        logger.info(f"Book Object: {book}")
        logger.info(f"Book Author ID: {book.author_id if book else 'N/A'}")
        logger.info(f"Book Price: ${book.price if book else 'N/A'}")
        logger.info(f"Book Currency: {book.currency if book else 'N/A'}")
        logger.info(f"Purchase Already Committed: {purchase_already_committed}")
        
        # CRITICAL: Verify purchase exists in transaction (not yet committed to DB)
        # If purchase was created via raw SQL, it's in the transaction but not committed
        # If purchase was created via ORM, it's in the session but not committed
        # We need to check if it's visible in the current transaction
        try:
            from sqlalchemy import text
            # First, flush the session to ensure purchase is in the transaction
            if hasattr(purchase, '_sa_instance_state'):
                logger.info(f"🔄 Flushing session to ensure purchase is in transaction...")
                db.session.flush()
                logger.info(f"✅ Session flushed")
            
            # Check if purchase is visible in current transaction
            # For raw SQL inserts, they're already in the transaction
            # For ORM inserts, flush makes them visible
            purchase_check = db.session.execute(
                text("SELECT id, amount, book_project_id FROM book_purchases WHERE id = :id"),
                {'id': purchase.id}
            ).fetchone()
            if purchase_check:
                logger.info(f"✅ Purchase {purchase.id} verified in transaction: amount=${purchase_check[1]}, book_id={purchase_check[2]}")
                logger.info(f"   Purchase is ready for BookSale creation (not yet committed to DB)")
            else:
                logger.error(f"❌❌❌ Purchase {purchase.id} NOT FOUND in transaction!")
                logger.error(f"   This means purchase was never created or is in a different session")
                raise ValueError(f"Purchase {purchase.id} does not exist in transaction")
        except Exception as verify_error:
            logger.error(f"❌ Failed to verify purchase in transaction: {verify_error}", exc_info=True)
            raise
        
        # CRITICAL: This try block MUST create BookSale or raise an error
        # If it exits without creating BookSale, the verification step will catch it
        try:
            from glconnect.book_platform_models import BookSale
            
            # Validate prerequisites
            if not book:
                raise ValueError(f"Book {book_id} not found")
            if not book.author_id:
                raise ValueError(f"Book {book_id} has no author_id - cannot create sale")
            fmt_base = base_price_for_format(book, purchase_type)
            if not fmt_base or fmt_base <= 0:
                raise ValueError(f"Book {book_id} has invalid price for format {purchase_type}")
            
            logger.info(f"✅ Prerequisites validated: book exists, author_id={book.author_id}, format={purchase_type}, base=${fmt_base}")
            logger.info(f"🔍 About to check for existing sale or create new one...")
            
            # Check if sale already exists
            existing_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
            if existing_sale:
                logger.info(f"Existing sale check: Found existing sale ID={existing_sale.id}")
            else:
                logger.info(f"Existing sale check: No existing sale found (will create new one)")
            
            if not existing_sale:
                sale_format = getattr(purchase, 'purchase_format', None) or purchase_type
                purchase_amount = getattr(purchase, 'amount', total_checkout_amount(book, sale_format))
                base_price, extra_amount, royalty_amount, platform_fee = revenue_split_for_purchase(
                    book, sale_format, purchase_amount
                )
                royalty_percentage = marketplace_author_royalty_fraction()
                
                logger.info(f"📊 Calculating revenue split:")
                logger.info(f"   Format: {sale_format}")
                logger.info(f"   Base price: ${base_price:.2f}")
                logger.info(f"   Purchase amount: ${purchase_amount:.2f}")
                logger.info(f"   Extra amount: ${extra_amount:.2f}")
                logger.info(f"   Total royalty: ${royalty_amount:.2f}")
                logger.info(f"   Platform fee: ${platform_fee:.2f}")
                
                logger.info(f"🏗️  Creating BookSale object...")
                sale = BookSale(
                    seller_id=book.author_id,
                    book_project_id=book_id,
                    purchase_id=purchase.id,
                    royalty_amount=royalty_amount,
                    royalty_percentage=royalty_percentage,
                    platform_fee=platform_fee,
                    net_amount=royalty_amount,
                    currency=book.currency or 'USD',
                    status=TransactionStatus.PENDING,  # Sale status matches purchase status
                    paid_at=None,  # Will be set when purchase is completed
                    sale_format=sale_format  # digital, audiobook, or bundle - investors earn from all
                )
                logger.info(f"✅ BookSale object created (not yet in DB)")
                logger.info(f"   seller_id={sale.seller_id}, purchase_id={sale.purchase_id}, royalty_amount=${sale.royalty_amount}")
                
                logger.info(f"➕ Adding BookSale to session...")
                db.session.add(sale)
                logger.info(f"✅ BookSale added to session")
                
                # Commit both purchase and sale together in the same transaction
                # If purchase was created via ORM, flush it first
                # If purchase was created via raw SQL, it's already in the transaction
                logger.info(f"💾 Committing purchase and BookSale together (atomic operation)...")
                
                # Check if purchase is in ORM session (created via ORM) or raw SQL
                purchase_in_session = hasattr(purchase, '_sa_instance_state')
                logger.info(f"   Purchase in ORM session: {purchase_in_session}")
                logger.info(f"   Purchase already committed flag: {purchase_already_committed}")
                
                if purchase_in_session and not purchase_already_committed:
                    # Purchase was created via ORM - flush it first
                    logger.info(f"🔄 Flushing purchase (ORM) to ensure it's in transaction...")
                    db.session.flush()
                    logger.info(f"✅ Purchase flushed")
                elif not purchase_in_session:
                    # Purchase was created via raw SQL - it's already in the transaction
                    logger.info(f"ℹ️  Purchase created via raw SQL, already in transaction (no flush needed)")
                
                try:
                    # Commit both purchase and sale together - atomic operation
                    db.session.commit()
                    logger.info(f"✅✅✅ BookSale {sale.id} SUCCESSFULLY created and committed for purchase {purchase.id}")
                    logger.info(f"✅✅✅ Purchase {purchase.id} also committed in same transaction")
                    logger.info("=" * 80)
                except Exception as commit_error:
                    logger.error("=" * 80)
                    logger.error(f"❌❌❌ FAILED to commit BookSale - ROLLING BACK PURCHASE")
                    logger.error("=" * 80)
                    logger.error(f"Error Type: {type(commit_error).__name__}")
                    logger.error(f"Error Message: {str(commit_error)}")
                    logger.error(f"Purchase ID: {purchase.id}")
                    logger.error(f"Book ID: {book_id}")
                    logger.error(f"Author ID: {book.author_id}")
                    logger.error(f"Purchase already committed: {purchase_already_committed}")
                    logger.error(f"Sale object: seller_id={sale.seller_id}, purchase_id={sale.purchase_id}")
                    import traceback
                    logger.error(f"Full traceback:\n{traceback.format_exc()}")
                    logger.error("=" * 80)
                    logger.error(f"🔄 Rolling back transaction - purchase will NOT be committed")
                    db.session.rollback()
                    # Re-raise so the error is visible and purchase fails
                    raise
                
                # CRITICAL: Trigger revenue distribution - this calculates investor returns
                # This runs even for PENDING purchases to track returns immediately
                try:
                    result = distribute_revenue(sale, db)
                    if result and result.get('success'):
                        logger.info(f"✅ Revenue distributed for sale {sale.id} (PENDING purchase): {result}")
                    else:
                        logger.error(f"⚠️  Revenue distribution returned error for sale {sale.id}: {result}")
                except Exception as e:
                    logger.error(f"❌ Revenue distribution FAILED for sale {sale.id}: {str(e)}", exc_info=True)
                    # Mark sale for manual reconciliation
                    sale.distribution_completed = False
                    db.session.commit()
            else:
                logger.info(f"✅ BookSale already exists for purchase {purchase.id} (ID: {existing_sale.id})")
                logger.info(f"   Distribution completed: {existing_sale.distribution_completed}")
                # If sale exists but distribution wasn't completed, trigger it now
                if not existing_sale.distribution_completed:
                    logger.warning(f"⚠️  Sale {existing_sale.id} exists but distribution not completed. Triggering distribution...")
                    try:
                        result = distribute_revenue(existing_sale, db)
                        if result and result.get('success'):
                            logger.info(f"✅ Revenue distributed for existing sale {existing_sale.id}: {result}")
                            db.session.commit()
                        else:
                            logger.error(f"⚠️  Revenue distribution failed for existing sale {existing_sale.id}: {result}")
                    except Exception as e:
                        logger.error(f"❌ Revenue distribution FAILED for existing sale {existing_sale.id}: {str(e)}", exc_info=True)
                logger.info("=" * 80)
        except Exception as sale_error:
            # Log the error with full details so we can fix the root cause
            import traceback
            sale_traceback = traceback.format_exc()
            logger.error("=" * 80)
            logger.error("❌❌❌ BOOKSALE CREATION FAILED - DETECTING ROOT CAUSE")
            logger.error("=" * 80)
            logger.error(f"Purchase ID: {purchase.id}")
            logger.error(f"Purchase Type: {type(purchase).__name__}")
            logger.error(f"Purchase Amount: ${getattr(purchase, 'amount', 'N/A')}")
            logger.error(f"Purchase Status: {getattr(purchase, 'status', 'N/A')}")
            logger.error(f"Book ID: {book_id}")
            logger.error(f"Book Object: {book}")
            logger.error(f"Book Author ID: {book.author_id if book else 'N/A'}")
            logger.error(f"Book Price: ${book.price if book else 'N/A'}")
            logger.error(f"Book Currency: {book.currency if book else 'N/A'}")
            logger.error(f"Purchase Already Committed: {purchase_already_committed}")
            logger.error(f"Error Type: {type(sale_error).__name__}")
            logger.error(f"Error Message: {str(sale_error)}")
            logger.error(f"Full Traceback:\n{sale_traceback}")
            
            # Additional diagnostics
            try:
                # Check if purchase exists in DB
                purchase_check = db.session.execute(
                    text("SELECT id FROM book_purchases WHERE id = :id"),
                    {'id': purchase.id}
                ).fetchone()
                logger.error(f"Purchase exists in DB: {purchase_check is not None}")
                
                # Check if author exists
                if book and book.author_id:
                    author_check = db.session.execute(
                        text("SELECT id FROM book_platform_users WHERE id = :id"),
                        {'id': book.author_id}
                    ).fetchone()
                    logger.error(f"Author exists in DB: {author_check is not None}")
            except Exception as diag_error:
                logger.error(f"Diagnostic check failed: {diag_error}")
            
            logger.error("=" * 80)
            logger.error(f"Failed to create BookSale for purchase {purchase.id}: {sale_error}", exc_info=True)
            
            # Re-raise the error so it's visible and the purchase fails
            # This ensures we fix the root cause instead of silently failing
            # Wrap it in a custom exception so we can identify it in the outer handler
            class BookSaleCreationError(Exception):
                pass
            raise BookSaleCreationError(f"BookSale creation failed: {sale_error}") from sale_error
        
        # CRITICAL VERIFICATION: Verify BookSale was actually created
        logger.info("=" * 80)
        logger.info("🔍🔍🔍 VERIFICATION: Checking if BookSale was created...")
        logger.info("=" * 80)
        try:
            # Try ORM query first
            final_sale_check = BookSale.query.filter_by(purchase_id=purchase.id).first()
            if not final_sale_check:
                # Try raw SQL as fallback
                logger.warning(f"⚠️  BookSale not found via ORM query, trying raw SQL...")
                final_sale_check_raw = db.session.execute(
                    text("SELECT id FROM book_sales WHERE purchase_id = :purchase_id"),
                    {'purchase_id': purchase.id}
                ).fetchone()
                if final_sale_check_raw:
                    logger.error("=" * 80)
                    logger.error("❌❌❌ CRITICAL: BookSale exists in DB but not accessible via ORM!")
                    logger.error("=" * 80)
                    logger.error(f"Purchase ID: {purchase.id}")
                    logger.error(f"BookSale ID (from raw SQL): {final_sale_check_raw[0]}")
                    logger.error("This indicates a session/ORM issue")
                    raise ValueError(f"BookSale exists in DB but ORM query failed - session issue")
                else:
                    logger.error("=" * 80)
                    logger.error("❌❌❌ CRITICAL: BookSale creation code ran but no sale was created!")
                    logger.error("=" * 80)
                    logger.error(f"Purchase ID: {purchase.id} exists but BookSale does not")
                    logger.error("This should never happen - BookSale creation must have failed silently")
                    logger.error("=" * 80)
                    # Force rollback and fail the purchase
                    db.session.rollback()
                    raise ValueError(f"BookSale was not created for purchase {purchase.id} despite code execution")
            else:
                logger.info(f"✅✅✅ VERIFIED: BookSale {final_sale_check.id} exists for purchase {purchase.id}")
                logger.info(f"   Sale ID: {final_sale_check.id}")
                logger.info(f"   Seller ID: {final_sale_check.seller_id}")
                logger.info(f"   Royalty Amount: ${final_sale_check.royalty_amount}")
                logger.info(f"   Status: {final_sale_check.status}")
                logger.info("=" * 80)
        except Exception as verify_error:
            logger.error("=" * 80)
            logger.error(f"❌❌❌ VERIFICATION FAILED: {verify_error}")
            logger.error("=" * 80)
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()
            raise
        
        # Generate success and cancel URLs
        try:
            success_url = url_for('book_platform.purchase_success', book_id=book_id, purchase_id=purchase.id, _external=True)
            cancel_url = url_for('book_platform.marketplace', _external=True)
            logger.info(f"✅ URLs generated: success={success_url}, cancel={cancel_url}")
        except Exception as url_error:
            logger.error(f"❌ Failed to generate URLs: {url_error}", exc_info=True)
            # Use fallback URLs
            success_url = f"/mybook/purchase/success?book_id={book_id}&purchase_id={purchase.id}"
            cancel_url = "/mybook/marketplace"
        
        logger.info(f"✅ Purchase {purchase.id} created (PENDING). Success URL: {success_url}")
        
        # Create Stripe Checkout Session and return redirect URL
        stripe_checkout_url = None
        stripe_session_error = None
        try:
            import stripe

            stripe_api_key = get_stripe_server_secret_key(flask_app)
            if stripe_api_key:
                stripe.api_key = stripe_api_key
                domain_url = flask_app.config.get('FRONTEND_BASE_URL') or request.url_root.rstrip('/')
                checkout_kw = dict(
                    payment_method_types=checkout_payment_method_types_for_currency(
                        book.currency or 'USD'
                    ),
                    mode='payment',
                    success_url=success_url,
                    cancel_url=cancel_url,
                    client_reference_id=str(purchase.id),
                    metadata={
                        'book_id': str(book_id),
                        'purchase_id': str(purchase.id),
                        'purchase_type': purchase_type,
                    },
                )
                if purchase_type == 'print':
                    book_amt = base_price_for_format(book, 'print')
                    ship_amt = print_shipping_amount(book)
                    line_items = []
                    if book_amt > 0:
                        line_items.append({
                            'price_data': {
                                'currency': (book.currency or 'USD').lower(),
                                'product_data': {
                                    'name': f'{book.title} (print edition)',
                                    'description': 'Physical book — author ships to your address',
                                },
                                'unit_amount': int(round(book_amt * 100)),
                            },
                            'quantity': 1,
                        })
                    if ship_amt > 0:
                        line_items.append({
                            'price_data': {
                                'currency': (book.currency or 'USD').lower(),
                                'product_data': {
                                    'name': 'Shipping',
                                    'description': 'Flat shipping (author fulfills)',
                                },
                                'unit_amount': int(round(ship_amt * 100)),
                            },
                            'quantity': 1,
                        })
                    if not line_items:
                        line_items = [{
                            'price_data': {
                                'currency': (book.currency or 'USD').lower(),
                                'product_data': {'name': book.title},
                                'unit_amount': int(payment_amount * 100),
                            },
                            'quantity': 1,
                        }]
                    checkout_kw['line_items'] = line_items
                    checkout_kw['shipping_address_collection'] = {
                        'allowed_countries': STRIPE_PRINT_SHIPPING_COUNTRIES,
                    }
                else:
                    checkout_kw['line_items'] = [{
                        'price_data': {
                            'currency': (book.currency or 'USD').lower(),
                            'product_data': {
                                'name': book.title,
                                'description': f'Purchase of "{book.title}"' + (f' ({purchase_type})' if purchase_type != 'digital' else ''),
                            },
                            'unit_amount': int(payment_amount * 100),
                        },
                        'quantity': 1,
                    }]
                _buyer_email = checkout_customer_email_for_user(current_user)
                if _buyer_email:
                    checkout_kw['customer_email'] = _buyer_email
                if payment_intent_data:
                    checkout_kw['payment_intent_data'] = payment_intent_data
                    if author_connect_id:
                        checkout_kw['stripe_account'] = author_connect_id
                checkout_session = stripe.checkout.Session.create(**checkout_kw)
                stripe_checkout_url = checkout_session.url
        except Exception as stripe_err:
            stripe_session_error = stripe_err
        
        response_data = {
            'success': True,
            'purchase_id': purchase.id,
            'status': 'pending',
            'message': 'Purchase created. Redirecting to payment...',
            'success_url': success_url,
            'cancel_url': cancel_url,
        }
        if stripe_checkout_url:
            response_data['stripe_checkout_url'] = stripe_checkout_url
        else:
            from glconnect.stripe_utils import purchase_checkout_unavailable_response
            return purchase_checkout_unavailable_response(
                flask_app,
                stripe_session_error,
                stripe_connect_account_id=author_connect_id or None,
            )
        logger.info(f"✅ Returning success response: {response_data}")
        return jsonify(response_data)
        
        
    except Exception as e:
        db.session.rollback()
        # May be missing if the failure happened before `flask_app = ...` in the try block above.
        try:
            _purchase_app = flask_app
        except NameError:
            import flask as _flask_mod_ex
            _purchase_app = _flask_mod_ex.current_app._get_current_object()
        error_msg = str(e)
        import traceback
        error_traceback = traceback.format_exc()
        
        # Check if this is a BookSale creation error
        is_booksale_error = 'BookSaleCreationError' in str(type(e)) or 'BookSale' in error_msg
        
        # Log full error details for debugging (server-side only)
        logger.error("=" * 80)
        if is_booksale_error:
            logger.error("❌❌❌ BOOKSALE CREATION ERROR - Purchase will fail")
        else:
            logger.error("❌ PURCHASE ERROR - Full Technical Details (for debugging)")
        logger.error("=" * 80)
        logger.error(f"Request Context:")
        logger.error(f"  - Book ID: {book_id}")
        logger.error(f"  - Buyer User ID: {buyer_user_id}")
        logger.error(f"  - Request Path: {request.path if request else 'N/A'}")
        logger.error(f"  - Request Method: {request.method if request else 'N/A'}")
        logger.error(f"  - User: {current_user.username if current_user.is_authenticated else 'Anonymous'}")
        logger.error(f"Error Details:")
        logger.error(f"  - Error Type: {type(e).__name__}")
        logger.error(f"  - Error Message: {error_msg}")
        logger.error(f"  - Full Traceback:")
        logger.error(error_traceback)
        logger.error("=" * 80)
        # Also log with exc_info for stack trace in log handlers
        logger.error(f"Purchase failed for book {book_id}, buyer {buyer_user_id}: {error_msg}", exc_info=True)
        
        # Convert technical errors to user-friendly messages
        # TEMPORARILY: Always include error details for debugging
        user_friendly_error = "We encountered an issue processing your purchase. Please try again or contact support if the problem persists."
        
        # Check if we're in debug/development mode - include more details for debugging
        try:
            is_debug = _purchase_app.config.get('DEBUG', False) or _purchase_app.config.get('FLASK_ENV') == 'development'
        except Exception:
            is_debug = False
        
        # TEMPORARILY: Always show error details for debugging
        is_debug = True  # Force debug mode to see actual errors
        
        # Check for specific error types and provide better messages
        if 'psycopg2' in error_msg.lower() or 'database' in error_msg.lower() or 'sql' in error_msg.lower():
            user_friendly_error = "A database error occurred. Our team has been notified. Please try again in a moment."
            if is_debug:
                user_friendly_error += f" (Debug: {error_msg[:200]})"
        elif 'enum' in error_msg.lower() or 'transactionstatus' in error_msg.lower():
            user_friendly_error = "There was an issue with the purchase status. Please try again."
            if is_debug:
                user_friendly_error += f" (Debug: {error_msg[:200]})"
        elif 'not found' in error_msg.lower() or '404' in error_msg.lower():
            user_friendly_error = "The book you're trying to purchase could not be found."
        elif 'permission' in error_msg.lower() or 'unauthorized' in error_msg.lower():
            user_friendly_error = "You don't have permission to perform this action."
        elif is_debug:
            # In debug mode, include the actual error message
            user_friendly_error = f"We encountered an issue: {error_msg[:300]}"
        
        
        # Always return JSON, never HTML
        # Check if it's a database constraint error (missing column)
        if 'buyer_user_id' in error_msg.lower() or ('column' in error_msg.lower() and 'does not exist' in error_msg.lower()):
            logger.warning("⚠️  buyer_user_id column may not exist. Attempting fallback...")
            try:
                # Fallback: Create minimal BookPlatformUser and use buyer_id
                from glconnect.book_platform_models import BookPlatformUser
                minimal_bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                if not minimal_bp_user:
                    minimal_bp_user = BookPlatformUser(
                        user_id=buyer_user_id,
                        pen_name=current_user.username if current_user.is_authenticated else "User",
                        bio="Reader"
                    )
                    db.session.add(minimal_bp_user)
                    db.session.flush()
                    logger.info(f"Created minimal BookPlatformUser {minimal_bp_user.id} for purchase")
                else:
                    logger.info(f"Using existing BookPlatformUser {minimal_bp_user.id} for purchase")
                
                # Use raw SQL to create purchase (avoid buyer_user_id column)
                from sqlalchemy import text
                import uuid as uuid_lib
                from datetime import datetime, timezone
                
                purchase_uuid = str(uuid_lib.uuid4())
                book = BookProject.query.options(joinedload(BookProject.author)).get(book_id)
                if not book:
                    return jsonify({'error': 'Book not found'}), 404
                
                _cid_fb = (book.author.stripe_connect_account_id or "").strip() if book.author else ""
                _pi_fb, _connect_err_fb = marketplace_book_payment_intent_data(
                    book=book,
                    purchase_type=purchase_type,
                    payment_amount=payment_amount,
                    stripe_connect_account_id=_cid_fb or None,
                )
                if _connect_err_fb:
                    return jsonify({'success': False, 'error': _connect_err_fb}), 400
                
                # Check which columns exist
                from sqlalchemy import inspect as sql_inspect
                inspector = sql_inspect(db.engine)
                columns = [col['name'] for col in inspector.get_columns('book_purchases')]
                has_buyer_username_col = 'buyer_username' in columns
                has_buyer_full_name_col = 'buyer_full_name' in columns
                
                # Get buyer info for the SQL insert (only if columns exist)
                buyer_username = None
                buyer_full_name = None
                if (has_buyer_username_col or has_buyer_full_name_col) and minimal_bp_user:
                    if minimal_bp_user.user:
                        buyer_username = minimal_bp_user.user.username
                        if minimal_bp_user.pen_name:
                            buyer_full_name = minimal_bp_user.pen_name
                        elif minimal_bp_user.user.first_name and minimal_bp_user.user.last_name:
                            buyer_full_name = f"{minimal_bp_user.user.first_name} {minimal_bp_user.user.last_name}"
                        else:
                            buyer_full_name = minimal_bp_user.user.username
                
                # Use raw SQL to insert - only include columns that exist
                if has_buyer_username_col and has_buyer_full_name_col:
                    result = db.session.execute(
                        text("""
                            INSERT INTO book_purchases (uuid, amount, currency, status, book_project_id, buyer_id, buyer_username, buyer_full_name, created_at)
                            VALUES (:uuid, :amount, :currency, :status, :book_project_id, :buyer_id, :buyer_username, :buyer_full_name, :created_at)
                            RETURNING id
                        """),
                        {
                            'uuid': purchase_uuid,
                            'amount': payment_amount,
                            'currency': book.currency or 'USD',
                            'status': 'PENDING',  # Database enum is uppercase
                            'book_project_id': book_id,
                            'buyer_id': minimal_bp_user.id,
                            'buyer_username': buyer_username,
                            'buyer_full_name': buyer_full_name,
                            'created_at': datetime.now(timezone.utc)
                        }
                    )
                else:
                    # buyer_username/buyer_full_name don't exist - use minimal INSERT
                    # Database enum values are uppercase (PENDING, COMPLETED, etc.)
                    result = db.session.execute(
                        text("""
                            INSERT INTO book_purchases (uuid, amount, currency, status, book_project_id, buyer_id, created_at)
                            VALUES (:uuid, :amount, :currency, :status, :book_project_id, :buyer_id, :created_at)
                            RETURNING id
                        """),
                        {
                            'uuid': purchase_uuid,
                            'amount': payment_amount,
                            'currency': book.currency or 'USD',
                            'status': 'PENDING',  # Database enum is uppercase
                            'book_project_id': book_id,
                            'buyer_id': minimal_bp_user.id,
                            'created_at': datetime.now(timezone.utc)
                        }
                    )
                purchase_id = result.scalar()
                # CRITICAL: Don't commit yet - commit purchase and BookSale together
                # This ensures if BookSale creation fails, purchase is also rolled back
                logger.info(f"✅ Purchase inserted via raw SQL (in transaction, not committed), ID={purchase_id}")
                
                # Create a minimal purchase object for the rest of the code
                # Don't query back from DB as SQLAlchemy will try to SELECT all columns including buyer_user_id
                class PurchaseObj:
                    def __init__(self, purchase_id, buyer_id, amount, currency):
                        self.id = purchase_id
                        self.buyer_id = buyer_id
                        self.amount = amount
                        self.currency = currency
                        self.status = TransactionStatus.PENDING
                        self.buyer_username = buyer_username
                        self.buyer_full_name = buyer_full_name
                
                purchase = PurchaseObj(purchase_id, minimal_bp_user.id, payment_amount, book.currency or 'USD')
                logger.info(f"✅ Created purchase via raw SQL (no buyer_user_id column), ID={purchase_id}")
                
                # Create BookSale and trigger revenue distribution immediately, regardless of purchase status
                # This ensures sales and investment returns are tracked even for PENDING purchases
                try:
                    from glconnect.book_platform_models import BookSale
                    
                    # Check if sale already exists
                    existing_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
                    
                    if not existing_sale:
                        sale_format = getattr(purchase, 'purchase_format', None) or purchase_type
                        base_price, extra_amount, royalty_amount, platform_fee = revenue_split_for_purchase(
                            book, sale_format, payment_amount
                        )
                        royalty_percentage = marketplace_author_royalty_fraction()
                        
                        logger.info(f"Creating BookSale for purchase {purchase.id} (fallback, {sale_format}): base=${base_price:.2f}, total=${payment_amount:.2f}")
                        
                        sale = BookSale(
                            seller_id=book.author_id,
                            book_project_id=book_id,
                            purchase_id=purchase.id,
                            royalty_amount=royalty_amount,
                            royalty_percentage=royalty_percentage,
                            platform_fee=platform_fee,
                            net_amount=royalty_amount,
                            currency=book.currency,
                            status=TransactionStatus.PENDING,
                            paid_at=None,
                            sale_format=sale_format
                        )
                        db.session.add(sale)
                        db.session.commit()
                        
                        # CRITICAL: Trigger revenue distribution - this calculates investor returns
                        # This runs even for PENDING purchases to track returns immediately
                        try:
                            result = distribute_revenue(sale, db)
                            if result and result.get('success'):
                                logger.info(f"✅ Revenue distributed for sale {sale.id} (PENDING purchase, fallback): {result}")
                            else:
                                logger.error(f"⚠️  Revenue distribution returned error for sale {sale.id}: {result}")
                        except Exception as e:
                            logger.error(f"❌ Revenue distribution FAILED for sale {sale.id}: {str(e)}", exc_info=True)
                            # Mark sale for manual reconciliation
                            sale.distribution_completed = False
                            db.session.commit()
                    else:
                        logger.info(f"BookSale already exists for purchase {purchase.id} (fallback)")
                except Exception as sale_error:
                    # CRITICAL: Fail the purchase if BookSale creation fails
                    # This ensures data consistency - no purchase without a sale
                    logger.error("=" * 80)
                    logger.error(f"❌❌❌ BOOKSALE CREATION FAILED (fallback path) - FAILING PURCHASE")
                    logger.error("=" * 80)
                    logger.error(f"Purchase ID: {purchase.id}")
                    logger.error(f"Error: {sale_error}")
                    logger.error("=" * 80)
                    db.session.rollback()  # Rollback the purchase too
                    raise  # Re-raise to fail the purchase
                
                # Generate URLs
                success_url = url_for('book_platform.purchase_success', book_id=book_id, purchase_id=purchase.id, _external=True)
                cancel_url = url_for('book_platform.marketplace', _external=True)
                
                logger.info(f"✅ SUCCESS (fallback): Purchase {purchase.id} created via raw SQL")
                
                # Create Stripe Checkout for fallback path
                stripe_checkout_url = None
                stripe_fb_error = None
                try:
                    import stripe
                    stripe_api_key = get_stripe_server_secret_key(_purchase_app)
                    if stripe_api_key:
                        stripe.api_key = stripe_api_key
                        checkout_kw_fb = dict(
                            payment_method_types=checkout_payment_method_types_for_currency(
                                book.currency or 'USD'
                            ),
                            line_items=[{
                                'price_data': {
                                    'currency': (book.currency or 'USD').lower(),
                                    'product_data': {'name': book.title, 'description': f'Purchase of "{book.title}"'},
                                    'unit_amount': int(payment_amount * 100),
                                },
                                'quantity': 1,
                            }],
                            mode='payment',
                            success_url=success_url,
                            cancel_url=cancel_url,
                            client_reference_id=str(purchase.id),
                            metadata={'book_id': str(book_id), 'purchase_id': str(purchase.id), 'purchase_type': purchase_type},
                        )
                        _buyer_email_fb = checkout_customer_email_for_user(current_user)
                        if _buyer_email_fb:
                            checkout_kw_fb['customer_email'] = _buyer_email_fb
                        if _pi_fb:
                            checkout_kw_fb['payment_intent_data'] = _pi_fb
                            if _cid_fb:
                                checkout_kw_fb['stripe_account'] = _cid_fb
                        checkout_session = stripe.checkout.Session.create(**checkout_kw_fb)
                        stripe_checkout_url = checkout_session.url
                except Exception as e:
                    stripe_fb_error = e
                    logger.warning("Fallback Stripe checkout failed: %s", e, exc_info=True)
                
                response_data = {
                    'success': True,
                    'purchase_id': purchase.id,
                    'status': 'pending',
                    'message': 'Purchase created. Redirecting to payment...',
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                }
                if stripe_checkout_url:
                    response_data['stripe_checkout_url'] = stripe_checkout_url
                    return jsonify(response_data)
                from glconnect.stripe_utils import purchase_checkout_unavailable_response
                return purchase_checkout_unavailable_response(
                    _purchase_app,
                    stripe_fb_error,
                    stripe_connect_account_id=_cid_fb or None,
                )
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {str(fallback_error)}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'We encountered an issue processing your purchase. Please try again or contact support if the problem persists.'
                }), 500
        else:
            # Return JSON error with user-friendly message
            # Include debug info if in debug mode
            error_response = {
                'success': False,
                'error': user_friendly_error
            }
            if is_debug:
                error_response['debug_info'] = {
                    'error_type': type(e).__name__,
                    'error_message': error_msg[:500]  # First 500 chars of error
                }
            return jsonify(error_response), 500
    except Exception as outer_error:
        # Catch any exception that wasn't caught in inner try blocks
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = str(outer_error)
        logger.error("=" * 80)
        logger.error("❌ UNHANDLED PURCHASE ERROR - Full Technical Details (for debugging)")
        logger.error("=" * 80)
        logger.error(f"Request Context:")
        logger.error(f"  - Book ID: {book_id if 'book_id' in locals() else 'Unknown'}")
        logger.error(f"  - Buyer User ID: {buyer_user_id if 'buyer_user_id' in locals() else 'Unknown'}")
        logger.error(f"  - Request Path: {request.path if request else 'N/A'}")
        logger.error(f"  - Request Method: {request.method if request else 'N/A'}")
        logger.error(f"Error Details:")
        logger.error(f"  - Error Type: {type(outer_error).__name__}")
        logger.error(f"  - Error Message: {error_msg}")
        logger.error(f"  - Full Traceback:")
        logger.error(error_traceback)
        logger.error("=" * 80)
        # Also log with exc_info for stack trace in log handlers
        logger.error(f"Unhandled error in purchase_book: {error_msg}", exc_info=True)
        
        # Check if we're in debug mode
        try:
            is_debug = current_app.config.get('DEBUG', False) or current_app.config.get('FLASK_ENV') == 'development'
        except:
            is_debug = False
        
        # Convert to user-friendly message
        user_friendly_error = "We encountered an unexpected issue. Please try again or contact support if the problem persists."
        if 'psycopg2' in error_msg.lower() or 'database' in error_msg.lower():
            user_friendly_error = "A database error occurred. Our team has been notified. Please try again in a moment."
        
        error_response = {
            'success': False,
            'error': user_friendly_error
        }
        if is_debug:
            error_response['debug_info'] = {
                'error_type': type(outer_error).__name__,
                'error_message': error_msg[:500]
            }
        
        return jsonify(error_response), 500
    
    # Purchase is created as PENDING - sale and revenue distribution will happen in success callback
    # after payment is confirmed


@book_bp.route('/checkout/quick-register', methods=['POST'])
def checkout_quick_register():
    """Create an account during marketplace checkout, then continue as a logged-in buyer."""
    if getattr(current_user, 'is_authenticated', False):
        return jsonify({'success': True, 'already_logged_in': True})

    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    first_name = (data.get('first_name') or '').strip() or 'Reader'
    last_name = (data.get('last_name') or '').strip() or ''

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required.'}), 400
    if not username or len(username) < 2:
        return jsonify({'error': 'Choose a username (at least 2 characters).'}), 400
    if not password or len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters.'}), 400

    if User.query.filter(func.lower(User.email) == email).first():
        return jsonify({'error': 'That email is already registered. Sign in instead.'}), 400
    if User.query.filter(func.lower(User.username) == username.lower()).first():
        return jsonify({'error': 'That username is taken. Try another.'}), 400

    user = User(
        first_name=first_name,
        last_name=last_name or 'User',
        username=username,
        email=email,
        role='other',
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    session['user_id'] = user.user_id
    return jsonify({'success': True})


# Stripe Payment Success Callback
@book_bp.route('/purchase/success', methods=['GET', 'POST'])
@login_required
def purchase_success():
    """Handle successful Stripe payment and record purchase (signed-in buyer)."""
    try:
        notify_receipt = False
        def _post_purchase_redirect(book_id: int, purchase_format: str):
            """Route buyers after checkout — library for digital/audio, marketplace for print."""
            if normalize_purchase_format(purchase_format) == 'print':
                return redirect(url_for('book_platform.marketplace'))
            return redirect(url_for('book_platform.my_library', book_id=book_id))

        # Get purchase info from query params or session
        book_id = request.args.get('book_id') or request.form.get('book_id')
        session_id = request.args.get('session_id') or request.form.get('session_id')
        payment_intent_id = request.args.get('payment_intent') or request.form.get('payment_intent')
        purchase_id_raw = request.args.get('purchase_id') or request.form.get('purchase_id')

        purchase_id = None
        if purchase_id_raw is not None and str(purchase_id_raw).strip() != '':
            try:
                purchase_id = int(purchase_id_raw)
            except (TypeError, ValueError):
                purchase_id = None

        if not book_id:
            flash('Purchase information not found. Please contact support if payment was successful.', 'warning')
            return redirect(url_for('book_platform.marketplace'))

        book_id = int(book_id)

        buyer_user_id = current_user.user_id
        bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
        buyer_id = bp_user.id if bp_user else None

        purchase = None

        if purchase_id:
            pc = BookPurchase.query.get(purchase_id)
            if pc and pc.book_project_id != book_id:
                pc = None
            if pc and buyer_user_id is not None:
                owns = (pc.buyer_user_id == buyer_user_id) or (buyer_id and pc.buyer_id == buyer_id)
                if owns:
                    purchase = pc

        # If not found by purchase_id, look for existing COMPLETED purchase
        if not purchase and buyer_user_id is not None:
            existing_purchase = BookPurchase.query.filter(
                db.or_(
                    BookPurchase.buyer_user_id == buyer_user_id,
                    (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                ),
                BookPurchase.book_project_id == book_id,
                BookPurchase.status == TransactionStatus.COMPLETED
            ).first()
            
            if existing_purchase:
                # Check if BookSale already exists - if not, create it
                existing_sale = BookSale.query.filter_by(purchase_id=existing_purchase.id).first()
                if not existing_sale:
                    # Purchase is COMPLETED but no sale exists - create it now
                    purchase = existing_purchase
                else:
                    flash('Purchase already recorded!', 'info')
                    existing_fmt = getattr(existing_purchase, 'purchase_format', None) or 'digital'
                    return _post_purchase_redirect(book_id, existing_fmt)
        
        # If still not found, look for any purchase (COMPLETED or PENDING) for this book/user
        if not purchase and buyer_user_id is not None:
            purchase = BookPurchase.query.filter(
                db.or_(
                    BookPurchase.buyer_user_id == buyer_user_id,
                    (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                ),
                BookPurchase.book_project_id == book_id
            ).order_by(BookPurchase.created_at.desc()).first()

        if not purchase:
            flash(
                'We could not match this payment to your account. If you were charged, contact support with your confirmation email.',
                'warning',
            )
            return redirect(url_for('book_platform.marketplace'))

        # If purchase found, ensure it's COMPLETED and has BookSale
        if purchase:
            # Purchase exists - ensure it's COMPLETED
            book = BookProject.query.get_or_404(purchase.book_project_id)
            was_pending = purchase.status == TransactionStatus.PENDING
            purchase.status = TransactionStatus.COMPLETED
            purchase.purchased_at = purchase.purchased_at or datetime.now(timezone.utc)
            purchase.transaction_id = payment_intent_id or session_id or purchase.transaction_id
            purchase.payment_method = purchase.payment_method or 'stripe'
            
            # If purchase was PENDING and is now COMPLETED, update the sale status
            if was_pending:
                pending_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
                if pending_sale:
                    pending_sale.status = TransactionStatus.COMPLETED
                    pending_sale.paid_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info(f"✅ Updated sale {pending_sale.id} to COMPLETED for purchase {purchase.id}")
                    notify_receipt = True
        elif buyer_user_id is not None:
            # No purchase found - create new one (fallback, signed-in only)
            book = BookProject.query.get_or_404(book_id)
            
            # Ensure user has BookPlatformUser profile
            if not buyer_id:
                from glconnect.models import Writer
                writer = Writer.query.filter_by(user_id=buyer_user_id).first()
                
                bp_user = BookPlatformUser(
                    user_id=buyer_user_id,
                    pen_name=writer.writer_name if writer else current_user.username,
                    bio=writer.bio if writer else "Reader",
                    profile_picture=writer.profile_picture if writer else "static/uploads/default_writer.jpg"
                )
                db.session.add(bp_user)
                db.session.commit()
                buyer_id = bp_user.id
                logger.info(f"Created BookPlatformUser {buyer_id} for purchase success callback")
            
            # Create purchase record
            # Note: In purchase_success callback, we use book.price as amount since we don't have custom amount here
            # The webhook will update the amount if user paid more
            purchase = BookPurchase(
                buyer_id=buyer_id,
                buyer_user_id=buyer_user_id,
                book_project_id=book_id,
                amount=book.price,  # Will be updated by webhook if user paid more
                currency=book.currency,
                status=TransactionStatus.COMPLETED  # COMPLETED when success callback is reached
            )
            # Populate buyer information (username and full name)
            purchase.populate_buyer_info()
            db.session.add(purchase)
            db.session.flush()
            
            # Complete the purchase - always mark as COMPLETED when success callback is reached
            purchase.purchased_at = datetime.now(timezone.utc)
            purchase.transaction_id = payment_intent_id or session_id or purchase.transaction_id
            purchase.payment_method = 'stripe'
    
        # Check if sale already exists for this purchase
        existing_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
        
        if existing_sale:
            # Sale already exists - ensure revenue distribution was completed
            if not existing_sale.distribution_completed:
                logger.warning(f"⚠️  Sale {existing_sale.id} exists but distribution not completed. Attempting distribution...")
                try:
                    from glconnect.revenue_distribution_service import distribute_revenue
                    result = distribute_revenue(existing_sale, db)
                    if result and result.get('success'):
                        logger.info(f"✅ Revenue distributed for existing sale {existing_sale.id}: {result}")
                    else:
                        logger.error(f"⚠️  Revenue distribution failed for existing sale {existing_sale.id}: {result}")
                except Exception as e:
                    logger.error(f"❌ Revenue distribution FAILED for existing sale {existing_sale.id}: {str(e)}", exc_info=True)
            sale = existing_sale
        else:
            # Create sale record - use purchase_format for correct sale type
            sale_format = normalize_purchase_format(getattr(purchase, 'purchase_format', None))
            base_price, extra_amount, royalty_amount, platform_fee = revenue_split_for_purchase(
                book, sale_format, purchase.amount
            )
            royalty_percentage = 0.7
            
            logger.info(f"Revenue split for purchase {purchase.id} ({sale_format}): base=${base_price:.2f}, total=${purchase.amount:.2f}")
            
            sale = BookSale(
                seller_id=book.author_id,
                book_project_id=book_id,
                purchase_id=purchase.id,
                royalty_amount=royalty_amount,
                royalty_percentage=royalty_percentage,
                platform_fee=platform_fee,
                net_amount=royalty_amount,
                currency=book.currency,
                status=TransactionStatus.COMPLETED,
                paid_at=datetime.now(timezone.utc),
                sale_format=sale_format  # digital, audiobook, or bundle
            )
            db.session.add(sale)
            db.session.flush()  # Get sale.id before committing
            
            # Update book statistics (only if this is a new sale)
            book.total_sales = (book.total_sales or 0) + 1
            book.total_revenue = (book.total_revenue or 0.0) + book.price
            
            db.session.commit()
            
            # CRITICAL: Trigger revenue distribution - this calculates investor returns
            try:
                from glconnect.revenue_distribution_service import distribute_revenue
                result = distribute_revenue(sale, db)
                if result and result.get('success'):
                    logger.info(f"✅ Revenue distributed for sale {sale.id}: {result}")
                else:
                    logger.error(f"⚠️  Revenue distribution returned error for sale {sale.id}: {result}")
                    # Don't fail the purchase, but log the error
            except Exception as e:
                logger.error(f"❌ Revenue distribution FAILED for sale {sale.id}: {str(e)}", exc_info=True)
                # Mark sale for manual reconciliation
                sale.distribution_completed = False
                db.session.commit()
            # Don't fail the purchase - it's recorded, just needs manual distribution
            notify_receipt = True

        if notify_receipt:
            try:
                send_book_purchase_receipt_email(book, purchase)
            except Exception as receipt_err:
                logger.warning("Purchase receipt email error: %s", receipt_err, exc_info=True)

        success_fmt = normalize_purchase_format(getattr(purchase, 'purchase_format', None))
        if success_fmt == 'print' and session_id:
            try:
                init_stripe()
                import stripe
                checkout_session = stripe.checkout.Session.retrieve(session_id)
                session_payload = checkout_session.to_dict() if hasattr(checkout_session, 'to_dict') else dict(checkout_session)
                _create_print_order_from_checkout_session(purchase, book, session_payload)
                db.session.commit()
            except Exception as print_order_err:
                logger.warning(
                    "Could not create print order from checkout session %s: %s",
                    session_id,
                    print_order_err,
                    exc_info=True,
                )

        if success_fmt == 'print':
            handling_days = int(getattr(book, 'print_handling_days', None) or 7)
            flash(
                f'Print order confirmed! The author will ship within about {handling_days} business days.',
                'success',
            )
        else:
            flash('Purchase successful! Thank you for your purchase.', 'success')
        logger.info(
            f"✅ Purchase {purchase.id} recorded from Stripe success for book {book_id}, sale id={getattr(sale, 'id', None)}"
        )
        if success_fmt != 'print' and _restore_library_visibility_for_owned_format(buyer_user_id, book_id, success_fmt):
            db.session.commit()
        return _post_purchase_redirect(book_id, success_fmt)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing purchase success: {str(e)}", exc_info=True)
        flash('Error recording purchase. Please contact support with your payment confirmation.', 'error')
        return redirect(url_for('book_platform.marketplace'))


@book_bp.route('/payout-setup', methods=['GET'])
@writer_or_book_platform_required
def author_payout_setup(user_profile, profile_type):
    """After publishing, prompt authors to complete Stripe Connect so buyers can pay them."""
    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        flash('Could not resolve your author profile.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    bp_user = BookPlatformUser.query.get(author_id)
    if not bp_user:
        flash('Create your Ink Studio author profile first.', 'warning')
        return redirect(url_for('book_platform.dashboard'))
    default_next = url_for('book_platform.dashboard')
    next_path = safe_mybook_next_path(request.args.get('next'), default_next)
    if not author_needs_stripe_payout_setup(bp_user):
        # Smart routing: if payouts are already set up, send authors to Stripe account management.
        try:
            init_stripe()
            import stripe

            base = (current_app.config.get('FRONTEND_BASE_URL') or request.url_root).rstrip('/')
            stripe_key = (get_stripe_server_secret_key(current_app) or "").strip()
            if stripe_key.startswith("sk_live_") and base.startswith("http://"):
                base = "https://" + base[len("http://") :]
            refresh_url = f"{base}{url_for('book_platform.author_payout_setup', next=next_path)}"
            login = stripe.Account.create_login_link(
                bp_user.stripe_connect_account_id,
                redirect_url=refresh_url,
            )
            return redirect(login.url)
        except Exception as e:
            logger.warning(
                "Could not create Stripe login link for author=%s account=%s: %s",
                bp_user.id,
                bp_user.stripe_connect_account_id,
                e,
            )
            flash('Your payout account is connected. Could not open Stripe management right now; please try again.', 'warning')
            return redirect(next_path)
    return render_template(
        'book_platform/author_payout_setup.html',
        next_path=next_path,
    )


@book_bp.route('/stripe/connect/onboard', methods=['POST'])
@login_required
def stripe_connect_onboard():
    """Create a Stripe Express connected account (if needed) and return Account Link URL."""
    try:
        init_stripe()
    except RuntimeError as e:
        return jsonify({'success': False, 'error': str(e)}), 503

    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not bp_user:
        return jsonify({'success': False, 'error': 'Create your Ink Studio author profile first.'}), 400

    import stripe

    default_next = url_for('book_platform.dashboard')
    next_path = default_next
    if request.is_json:
        body = request.get_json(silent=True) or {}
        if body.get('next'):
            next_path = safe_mybook_next_path(body.get('next'), default_next)
    elif request.form.get('next'):
        next_path = safe_mybook_next_path(request.form.get('next'), default_next)

    country = (os.getenv('STRIPE_CONNECT_DEFAULT_COUNTRY') or 'US').strip().upper()

    def _create_connect_account_and_store_id():
        create_kwargs = {
            'type': 'express',
            'country': country,
            'capabilities': {
                'card_payments': {'requested': True},
                'transfers': {'requested': True},
            },
            'metadata': {'book_platform_user_id': str(bp_user.id)},
        }
        if getattr(current_user, 'email', None):
            create_kwargs['email'] = current_user.email
        acct = stripe.Account.create(**create_kwargs)
        bp_user.stripe_connect_account_id = acct.id
        db.session.commit()
    try:
        if not bp_user.stripe_connect_account_id:
            _create_connect_account_and_store_id()

        base = (current_app.config.get('FRONTEND_BASE_URL') or request.url_root).rstrip('/')
        # Stripe live mode requires HTTPS return/refresh URLs for Connect onboarding.
        stripe_key = (get_stripe_server_secret_key(current_app) or "").strip()
        if stripe_key.startswith("sk_live_") and base.startswith("http://"):
            base = "https://" + base[len("http://") :]
        refresh_url = f"{base}{url_for('book_platform.stripe_connect_onboard_return', refresh=1, next=next_path)}"
        return_url = f"{base}{url_for('book_platform.stripe_connect_onboard_return', next=next_path)}"
        try:
            link = stripe.AccountLink.create(
                account=bp_user.stripe_connect_account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
        except stripe.error.InvalidRequestError as e:
            err_msg = str(e)
            mode_mismatch = (
                'test mode account link for an account that was created in live mode' in err_msg
                or 'live mode account link for an account that was created in test mode' in err_msg
            )
            if not mode_mismatch:
                raise

            old_acct = bp_user.stripe_connect_account_id
            logger.warning(
                "Stripe Connect mode mismatch for user=%s account=%s. Recreating account in current mode.",
                bp_user.id,
                old_acct,
            )
            bp_user.stripe_connect_account_id = None
            db.session.commit()
            _create_connect_account_and_store_id()
            link = stripe.AccountLink.create(
                account=bp_user.stripe_connect_account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
        return jsonify({'success': True, 'url': link.url})
    except Exception as e:
        logger.error('Stripe Connect onboarding failed: %s', e, exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Could not start payout setup. Please try again or contact support.',
        }), 500


@book_bp.route('/stripe/connect/onboard-return', methods=['GET'])
@login_required
def stripe_connect_onboard_return():
    """Browser return URL after Stripe Connect onboarding."""
    flash('Payout setup updated. When Stripe shows your account as ready, you can receive book sales.', 'info')
    default_next = url_for('book_platform.dashboard')
    dest = safe_mybook_next_path(request.args.get('next'), default_next)
    return redirect(dest)


# Stripe Webhook Handler
@book_bp.route('/stripe/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events for payment confirmations"""
    import json
    
    try:
        # Try to import stripe (optional dependency)
        try:
            import stripe
            stripe_available = True
        except ImportError:
            stripe_available = False
            logger.warning("Stripe library not installed - webhook verification disabled")
        
        # Get webhook secret from config
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        if not webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured - webhook verification skipped")
        
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Production: never accept unsigned webhooks
        if not current_app.debug and (not webhook_secret or not stripe_available or not sig_header):
            logger.error("Stripe webhook rejected: signature verification required in production")
            return jsonify({'error': 'Webhook verification required'}), 503
        
        # Verify webhook signature (if secret is configured and stripe is available)
        if webhook_secret and sig_header and stripe_available:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError:
                logger.error("Invalid payload in Stripe webhook")
                return jsonify({'error': 'Invalid payload'}), 400
            except stripe.error.SignatureVerificationError:
                logger.error("Invalid signature in Stripe webhook")
                return jsonify({'error': 'Invalid signature'}), 400
        else:
            # Development only: parse JSON without verification when DEBUG is on
            event = json.loads(payload)
        
        # Set Stripe API key if available (for retrieving additional payment info if needed)
        stripe_api_key = get_stripe_server_secret_key(current_app)
        if stripe_api_key and stripe_available:
            stripe.api_key = stripe_api_key
        
        # Helper function to complete a purchase
        def complete_purchase(purchase, payment_intent_id=None, amount_total=None):
            """Complete a purchase and create sale record"""
            if not purchase or purchase.status != TransactionStatus.PENDING:
                return False
            
            book = BookProject.query.get(purchase.book_project_id)
            if not book:
                logger.error(f"Book {purchase.book_project_id} not found for purchase {purchase.id}")
                return False
            
            # Update purchase amount if actual amount paid differs (user paid more than book price)
            if amount_total and amount_total > 0:
                if abs(purchase.amount - amount_total) > 0.01:  # Allow $0.01 tolerance for rounding
                    logger.info(f"Updating purchase amount from ${purchase.amount:.2f} to ${amount_total:.2f} (actual amount paid)")
                    purchase.amount = amount_total
            
            # Complete the purchase
            purchase.status = TransactionStatus.COMPLETED
            purchase.purchased_at = datetime.now(timezone.utc)
            if payment_intent_id:
                purchase.transaction_id = payment_intent_id
            purchase.payment_method = 'stripe'
            db.session.flush()
            
            # Check if sale already exists
            existing_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
            if not existing_sale:
                sale_format = normalize_purchase_format(getattr(purchase, 'purchase_format', None))
                base_price, extra_amount, royalty_amount, platform_fee = revenue_split_for_purchase(
                    book, sale_format, purchase.amount
                )
                royalty_percentage = marketplace_author_royalty_fraction()
                
                logger.info(f"Revenue split for purchase {purchase.id} ({sale_format}): base=${base_price:.2f}, extra=${extra_amount:.2f}, total=${purchase.amount:.2f}")
                
                sale = BookSale(
                    seller_id=book.author_id,
                    book_project_id=purchase.book_project_id,
                    purchase_id=purchase.id,
                    royalty_amount=royalty_amount,
                    royalty_percentage=royalty_percentage,
                    platform_fee=platform_fee,
                    net_amount=royalty_amount,
                    currency=purchase.currency,
                    status=TransactionStatus.COMPLETED,
                    paid_at=datetime.now(timezone.utc),
                    sale_format=sale_format  # digital, audiobook, or bundle - investors earn from all
                )
                db.session.add(sale)
                db.session.flush()
                
                # Update book statistics (use actual amount paid)
                book.total_sales = (book.total_sales or 0) + 1
                book.total_revenue = (book.total_revenue or 0.0) + purchase.amount  # Includes any extra payment
                
                db.session.commit()
                
                # Trigger revenue distribution
                try:
                    from glconnect.revenue_distribution_service import distribute_revenue
                    result = distribute_revenue(sale, db)
                    if result and result.get('success'):
                        logger.info(f"✅ Revenue distributed for sale {sale.id}: {result}")
                    else:
                        logger.error(f"⚠️  Revenue distribution returned error for sale {sale.id}: {result}")
                        sale.distribution_completed = False
                        db.session.commit()
                except Exception as e:
                    logger.error(f"❌ Revenue distribution FAILED for sale {sale.id}: {str(e)}", exc_info=True)
                    sale.distribution_completed = False
                    db.session.commit()
                
                logger.info(f"✅ Purchase {purchase.id} completed, Sale {sale.id} created")
            else:
                # Sale already exists, check if distribution was completed
                if not existing_sale.distribution_completed:
                    logger.warning(f"⚠️  Sale {existing_sale.id} exists but distribution not completed. Attempting distribution...")
                    try:
                        from glconnect.revenue_distribution_service import distribute_revenue
                        result = distribute_revenue(existing_sale, db)
                        if result and result.get('success'):
                            logger.info(f"✅ Revenue distributed for existing sale {existing_sale.id}: {result}")
                        else:
                            logger.error(f"⚠️  Revenue distribution failed for existing sale {existing_sale.id}: {result}")
                    except Exception as e:
                        logger.error(f"❌ Revenue distribution FAILED for existing sale {existing_sale.id}: {str(e)}", exc_info=True)
                db.session.commit()
                logger.info(f"✅ Purchase {purchase.id} already has sale record, marked as completed")

            try:
                send_book_purchase_receipt_email(book, purchase)
            except Exception as receipt_err:
                logger.warning("Webhook purchase receipt email error: %s", receipt_err, exc_info=True)

            buyer_uid = getattr(purchase, 'buyer_user_id', None)
            pf = normalize_purchase_format(getattr(purchase, 'purchase_format', None))
            if buyer_uid and pf != 'print' and _restore_library_visibility_for_owned_format(
                buyer_uid, purchase.book_project_id, pf
            ):
                db.session.commit()

            return True
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            # Handle payment_intent.succeeded event (for direct Payment Intents)
            payment_intent = event['data']['object']
            payment_intent_id = payment_intent.get('id')
            amount_total = payment_intent.get('amount', 0) / 100.0  # Stripe amounts are in cents
            customer_email = payment_intent.get('receipt_email') or payment_intent.get('charges', {}).get('data', [{}])[0].get('billing_details', {}).get('email')
            metadata = payment_intent.get('metadata', {})
            book_id = metadata.get('book_id')
            purchase_id = metadata.get('purchase_id') or metadata.get('client_reference_id')
            
            logger.info(f"📥 Received payment_intent.succeeded webhook: payment_intent={payment_intent_id}, amount=${amount_total}, book_id={book_id}, purchase_id={purchase_id}")
            
            try:
                purchase = None
                
                # First, try to find by purchase_id from metadata
                if purchase_id:
                    try:
                        purchase_id_int = int(purchase_id)
                        purchase = BookPurchase.query.get(purchase_id_int)
                        if purchase and purchase.status == TransactionStatus.PENDING:
                            logger.info(f"Found PENDING purchase {purchase_id} from payment_intent metadata")
                    except (ValueError, TypeError):
                        pass
                
                # If no purchase found, try to find by book_id and user email
                if not purchase and book_id and customer_email:
                    try:
                        book_id = int(book_id)
                        user = User.query.filter_by(email=customer_email).first()
                        if user:
                            buyer_user_id = user.user_id
                            bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                            buyer_id = bp_user.id if bp_user else None
                            
                            purchase = BookPurchase.query.filter(
                                db.or_(
                                    BookPurchase.buyer_user_id == buyer_user_id,
                                    (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                                ),
                                BookPurchase.book_project_id == book_id,
                                BookPurchase.status == TransactionStatus.PENDING
                            ).first()
                            
                            if purchase:
                                logger.info(f"Found PENDING purchase {purchase.id} for book {book_id} and user {buyer_user_id}")
                    except (ValueError, TypeError):
                        pass
                
                # If still no purchase, try to find by amount and email
                if not purchase and customer_email and amount_total:
                    user = User.query.filter_by(email=customer_email).first()
                    if user:
                        buyer_user_id = user.user_id
                        bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                        buyer_id = bp_user.id if bp_user else None
                        
                        purchase = BookPurchase.query.filter(
                            db.or_(
                                BookPurchase.buyer_user_id == buyer_user_id,
                                (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                            ),
                            BookPurchase.status == TransactionStatus.PENDING,
                            db.func.abs(BookPurchase.amount - amount_total) < 0.01
                        ).order_by(BookPurchase.created_at.desc()).first()
                        
                        if purchase:
                            logger.info(f"Found PENDING purchase {purchase.id} by amount match: ${amount_total}")
                
                # Complete the purchase if found
                if purchase:
                    if complete_purchase(purchase, payment_intent_id, amount_total):
                        logger.info(f"✅ Purchase {purchase.id} completed from payment_intent.succeeded webhook")
                else:
                    logger.warning(f"⚠️  payment_intent.succeeded received but couldn't find matching purchase. payment_intent={payment_intent_id}, amount=${amount_total}, email={customer_email}")
                    
            except Exception as e:
                logger.error(f"Error processing payment_intent.succeeded webhook: {str(e)}", exc_info=True)
        
        elif event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {}) or {}
            
            # Check if this is an investment payment
            investment_id = metadata.get('investment_id')
            if investment_id:
                # Handle investment payment
                try:
                    investment = BookInvestment.query.get(int(investment_id))
                    if not investment:
                        logger.error(f"Stripe webhook: Investment {investment_id} not found")
                    elif (investment.payment_status == TransactionStatus.PENDING and 
                          investment.status == InvestmentStatus.PENDING):
                        campaign = investment.campaign
                        book = investment.book_project
                        
                        investment.payment_status = TransactionStatus.COMPLETED
                        investment.status = InvestmentStatus.CONFIRMED
                        investment.invested_at = datetime.now(timezone.utc)
                        # Store payment intent for investor refunds (before first draft only)
                        payment_intent_id = session.get('payment_intent')
                        if payment_intent_id:
                            investment.stripe_payment_intent_id = payment_intent_id
                        from glconnect.book_campaign_patronage import (
                            is_book_campaign_patronage_mode,
                            apply_patronage_terms_to_investment,
                        )
                        patronage = is_book_campaign_patronage_mode()
                        if patronage:
                            apply_patronage_terms_to_investment(investment)
                        # Update campaign funding on successful payment
                        campaign.current_funding += investment.amount

                        # First time goal is met → mark FUNDED (patrons may still give above goal)
                        if campaign.current_funding >= campaign.funding_goal:
                            if campaign.status != CampaignStatus.FUNDED:
                                campaign.status = CampaignStatus.FUNDED
                                if not campaign.funded_at:
                                    campaign.funded_at = datetime.now(timezone.utc)
                            from glconnect.platform_fee_policy import (
                                apply_campaign_fee_terms,
                                update_campaign_fee_totals,
                            )
                            apply_campaign_fee_terms(campaign, db)
                            update_campaign_fee_totals(campaign)
                            for inv in campaign.investments:
                                if inv.status == InvestmentStatus.CONFIRMED:
                                    if patronage:
                                        apply_patronage_terms_to_investment(inv)
                                    elif not inv.return_start_date:
                                        inv.return_start_date = datetime.now(timezone.utc)
                                    inv.status = InvestmentStatus.ACTIVE
                        else:
                            if not patronage:
                                investment.return_start_date = datetime.now(timezone.utc)
                            investment.status = InvestmentStatus.ACTIVE
                        
                        db.session.commit()
                        logger.info(f"Stripe webhook: Investment {investment.id} confirmed via Stripe")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Stripe webhook investment processing error: {e}", exc_info=True)
            else:
                # Handle book purchase payment
                # Extract book_id from metadata
                book_id = metadata.get('book_id')
                # Extract purchase_id from client_reference_id (set by backend)
                purchase_id = session.get('client_reference_id')
                customer_email = session.get('customer_details', {}).get('email')
                payment_intent_id = session.get('payment_intent')
                amount_total = session.get('amount_total', 0) / 100.0  # Stripe amounts are in cents
                
                try:
                    # First, try to find existing PENDING purchase by purchase_id
                    purchase = None
                    if purchase_id:
                        try:
                            purchase_id_int = int(purchase_id)
                            purchase = BookPurchase.query.get(purchase_id_int)
                            if purchase and purchase.status == TransactionStatus.PENDING:
                                logger.info(f"Found PENDING purchase {purchase_id} from webhook")
                                book_id = purchase.book_project_id
                        except (ValueError, TypeError):
                            pass
                    
                    # If no purchase found, try to find by book_id and user email
                    if not purchase and book_id:
                        try:
                            book_id = int(book_id)
                            user = User.query.filter_by(email=customer_email).first() if customer_email else None
                            
                            if user:
                                buyer_user_id = user.user_id
                                bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                                buyer_id = bp_user.id if bp_user else None
                                
                                # Check for existing PENDING purchase
                                purchase = BookPurchase.query.filter(
                                    db.or_(
                                        BookPurchase.buyer_user_id == buyer_user_id,
                                        (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                                    ),
                                    BookPurchase.book_project_id == book_id,
                                    BookPurchase.status == TransactionStatus.PENDING
                                ).first()
                                
                                if purchase:
                                    logger.info(f"Found PENDING purchase {purchase.id} for book {book_id} and user {buyer_user_id}")
                        except (ValueError, TypeError):
                            pass
                    
                    # If still no purchase, try to find by amount and email (fallback for missing book_id)
                    if not purchase and customer_email and amount_total:
                        user = User.query.filter_by(email=customer_email).first()
                        if user:
                            buyer_user_id = user.user_id
                            bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                            buyer_id = bp_user.id if bp_user else None
                            
                            # Find PENDING purchase matching amount (within $0.01 tolerance)
                            purchase = BookPurchase.query.filter(
                                db.or_(
                                    BookPurchase.buyer_user_id == buyer_user_id,
                                    (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
                                ),
                                BookPurchase.status == TransactionStatus.PENDING,
                                db.func.abs(BookPurchase.amount - amount_total) < 0.01
                            ).order_by(BookPurchase.created_at.desc()).first()
                            
                            if purchase:
                                logger.info(f"Found PENDING purchase {purchase.id} by amount match: ${amount_total}")
                                book_id = purchase.book_project_id
                    
                    # Complete the purchase if found
                    if purchase:
                        if complete_purchase(purchase, payment_intent_id, amount_total):
                            logger.info(f"✅ Purchase {purchase.id} completed from checkout.session.completed webhook")
                            if normalize_purchase_format(getattr(purchase, 'purchase_format', None)) == 'print':
                                book_for_print = BookProject.query.get(purchase.book_project_id)
                                if book_for_print:
                                    _create_print_order_from_checkout_session(purchase, book_for_print, session)
                                    db.session.commit()
                    # If no purchase found but we have book_id, create new purchase (fallback)
                    elif book_id:
                        logger.warning(f"⚠️  checkout.session.completed received but couldn't find matching purchase. book_id={book_id}, purchase_id={purchase_id}, amount=${amount_total}, email={customer_email}. Creating new purchase...")
                        try:
                            book_id = int(book_id)
                            user = User.query.filter_by(email=customer_email).first() if customer_email else None
                            
                            if user:
                                buyer_user_id = user.user_id
                                book = BookProject.query.get(book_id)
                                
                                if book:
                                    from glconnect.book_platform_models import BookPlatformUser
                                    from glconnect.models import Writer
                                    
                                    bp_user = BookPlatformUser.query.filter_by(user_id=buyer_user_id).first()
                                    buyer_id = bp_user.id if bp_user else None
                                    
                                    if not buyer_id:
                                        writer = Writer.query.filter_by(user_id=buyer_user_id).first()
                                        bp_user = BookPlatformUser(
                                            user_id=buyer_user_id,
                                            pen_name=writer.writer_name if writer else user.username,
                                            bio=writer.bio if writer else "Reader",
                                            profile_picture=writer.profile_picture if writer else "static/uploads/default_writer.jpg"
                                        )
                                        db.session.add(bp_user)
                                        db.session.commit()
                                        buyer_id = bp_user.id
                                    
                                    # Check if already recorded
                                    existing = BookPurchase.query.filter(
                                        BookPurchase.book_project_id == book_id,
                                        BookPurchase.transaction_id == payment_intent_id
                                    ).first()
                                    
                                    if not existing:
                                        # Get actual amount paid from Stripe (may be more than book price)
                                        actual_amount = amount_total if amount_total and amount_total > 0 else book.price
                                        
                                        purchase = BookPurchase(
                                            buyer_id=buyer_id,
                                            buyer_user_id=buyer_user_id,
                                            book_project_id=book_id,
                                            amount=actual_amount,  # Use actual amount paid
                                            currency=book.currency,
                                            status=TransactionStatus.COMPLETED,
                                            purchased_at=datetime.now(timezone.utc),
                                            transaction_id=payment_intent_id,
                                            payment_method='stripe',
                                            purchase_format='digital'  # Webhook fallback - no format in metadata
                                        )
                                        # Populate buyer information (username and full name)
                                        purchase.populate_buyer_info()
                                        db.session.add(purchase)
                                        db.session.flush()
                                        
                                        # Revenue sharing: 90% author / 10% platform on list price; extras to author
                                        base_price, extra_amount, royalty_amount, platform_fee = revenue_split_for_purchase(
                                            book, 'digital', actual_amount
                                        )
                                        
                                        sale = BookSale(
                                            seller_id=book.author_id,
                                            book_project_id=book_id,
                                            purchase_id=purchase.id,
                                            royalty_amount=royalty_amount,
                                            royalty_percentage=marketplace_author_royalty_fraction(),
                                            platform_fee=platform_fee,
                                            net_amount=royalty_amount,
                                            currency=book.currency,
                                            status=TransactionStatus.COMPLETED,
                                            paid_at=datetime.now(timezone.utc),
                                            sale_format='digital'  # Earnings account for digital copy sales
                                        )
                                        db.session.add(sale)
                                        db.session.commit()
                                        
                                        # Trigger revenue distribution
                                        try:
                                            from glconnect.revenue_distribution_service import distribute_revenue
                                            distribute_revenue(sale, db)
                                        except Exception as e:
                                            logger.error(f"Revenue distribution failed in webhook: {str(e)}")
                                        
                                        logger.info(f"✅ Purchase {purchase.id} created from Stripe webhook for book {book_id}")
                        except Exception as e:
                            logger.error(f"Error creating purchase from webhook: {str(e)}", exc_info=True)
                    else:
                        logger.warning(f"⚠️  Stripe webhook received but couldn't find book_id or purchase_id. Email: {customer_email}, Amount: ${amount_total}")
                        
                except Exception as e:
                    logger.error(f"Error processing webhook purchase: {str(e)}", exc_info=True)
        
        return jsonify({'received': True})
        
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Analytics routes
@book_bp.route('/books/<int:book_id>/analytics')
@book_platform_required
def book_analytics(book_id):
    """View book analytics"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author can view analytics
    if book.author_id != book_user.id:
        flash('Only the author can view analytics', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Get analytics data
    analytics = BookAnalytics.query.filter_by(book_project_id=book_id).all()
    sales = BookSale.query.filter_by(book_project_id=book_id, status=TransactionStatus.COMPLETED).all()
    
    return render_template('book_platform/analytics.html', 
                         book=book, 
                         analytics=analytics,
                         sales=sales)

# API routes for real-time features
@book_bp.route('/api/books/<int:book_id>/chapters/<int:chapter_id>/content', methods=['GET', 'POST'])
@collaboration_required
def chapter_content_api(book_id, chapter_id):
    """API endpoint for chapter content (for real-time editing)"""
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    if request.method == 'GET':
        return jsonify({
            'content': chapter.content,
            'title': chapter.title,
            'word_count': chapter.word_count,
            'updated_at': chapter.updated_at.isoformat() if chapter.updated_at else None
        })
    
    elif request.method == 'POST':
        data = request.get_json()
        actor_id = resolve_version_actor_id(chapter.book_project, current_user.user_id)
        if actor_id:
            snapshot_chapter(chapter, actor_id, change_source='collaboration')
        
        # Update chapter content
        chapter.content = data.get('content', chapter.content)
        chapter.title = data.get('title', chapter.title)
        # Recalculate word count from content (strip HTML tags)
        if data.get('content'):
            chapter.word_count = count_words_from_html(data.get('content', ''))
        chapter.updated_at = datetime.now(timezone.utc)
        
        # Update book's total word count
        book = chapter.book_project
        update_book_word_count(book)
        
        db.session.commit()
        
        return jsonify({'success': True, 'word_count': chapter.word_count})

@book_bp.route('/api/books/<int:book_id>/collaborators')
@collaboration_required
def collaborators_api(book_id):
    """Get active collaborators for a book"""
    collaborations = BookCollaboration.query.filter_by(
        book_project_id=book_id, 
        is_active=True
    ).all()
    
    collaborators = []
    for collab in collaborations:
        collaborators.append({
            'id': collab.collaborator.id,
            'name': collab.collaborator.pen_name or collab.collaborator.user.username,
            'role': collab.role.value,
            'joined_at': collab.joined_at.isoformat() if collab.joined_at else None
        })
    
    return jsonify({'collaborators': collaborators})

# API route for author details
@book_bp.route('/api/author/<int:author_id>/details', methods=['GET'])
@login_required
def get_author_details(author_id):
    """Get author details for marketplace display (no email—photo, bio, https website only)."""
    try:
        # Ensure BookPlatformUser is accessible
        from glconnect.book_platform_models import BookPlatformUser, BookStatus

        # Get the author (BookPlatformUser)
        author = BookPlatformUser.query.get_or_404(author_id)

        writer = Writer.query.filter_by(user_id=author.user_id).first()

        author_name = author.pen_name or (author.user.username if author.user else 'Author')
        author_bio = _marketplace_author_bio(author, writer)
        author_profile_picture = _marketplace_author_profile_picture(author, writer)

        website_href = _normalize_public_website((author.website or '').strip())
        website_label = _public_website_label(website_href)

        # Count published books by this author
        books_count = BookProject.query.filter_by(
            author_id=author_id,
            status=BookStatus.PUBLISHED
        ).count()

        return jsonify({
            'success': True,
            'author': {
                'id': author.id,
                'name': author_name,
                'bio': author_bio,
                'profile_picture': author_profile_picture,
                'website_href': website_href,
                'website_label': website_label,
                'books_count': books_count
            }
        })
    except Exception as e:
        logger.error(f"Error fetching author details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load author information'
        }), 500

# Error handlers
@book_bp.errorhandler(500)
def handle_500_error(error):
    """Handle 500 errors and return JSON for API routes"""
    import traceback
    error_traceback = traceback.format_exc()
    
    # Check if this is an API request (JSON expected)
    # Check for purchase endpoint or if request expects JSON
    is_api_request = (
        request.is_json or 
        '/purchase' in request.path or 
        request.path.startswith('/mybook/books/') or
        request.headers.get('Content-Type', '').startswith('application/json') or
        request.headers.get('Accept', '').startswith('application/json')
    )
    
    if is_api_request:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = str(error)
        
        # Log full technical details for debugging (server-side only)
        logger.error("=" * 80)
        logger.error("❌ BLUEPRINT 500 ERROR - Full Technical Details (for debugging)")
        logger.error("=" * 80)
        logger.error(f"Request Context:")
        logger.error(f"  - Path: {request.path}")
        logger.error(f"  - Method: {request.method}")
        logger.error(f"  - User: {request.remote_addr if request else 'N/A'}")
        logger.error(f"Error Details:")
        logger.error(f"  - Error Type: {type(error).__name__}")
        logger.error(f"  - Error Message: {error_msg}")
        logger.error(f"  - Full Traceback:")
        logger.error(error_traceback)
        logger.error("=" * 80)
        # Also log with exc_info for stack trace in log handlers
        logger.error(f"500 error in {request.path}: {error_msg}", exc_info=True)
        
        # Return user-friendly error message without exposing technical details
        return jsonify({
            'success': False,
            'error': 'We encountered an unexpected error. Our team has been notified. Please try again in a moment.'
        }), 500

    error_msg = str(getattr(error, 'description', None) or error)
    logger.error("Ink Studio page error on %s: %s", request.path, error_msg, exc_info=True)
    flash(
        'This page could not be loaded. If you were listing or creating a book, complete your author profile first, then try again.',
        'error',
    )
    return redirect(url_for('book_platform.marketplace'))

@book_bp.errorhandler(404)
def not_found(error):
    return render_template('book_platform/404.html'), 404

@book_bp.errorhandler(403)
def forbidden(error):
    return render_template('book_platform/403.html'), 403

# Image upload routes for CKEditor
@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/upload-image', methods=['POST'])
@writer_or_book_platform_required
def upload_chapter_image(book_id, chapter_id, user_profile, profile_type):
    """Upload image for a book chapter"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    # Verify chapter belongs to book
    if chapter.book_project_id != book_id:
        return jsonify({'error': 'Chapter not found'}), 404
    
    # Check access permissions
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        # Check if user is a collaborator
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id,
            collaborator_id=author_id,
            is_active=True
        ).first()
        if not collaboration:
            return jsonify({'error': 'Access denied'}), 403
    
    if 'upload' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['upload']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_image_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only image files are allowed.'}), 400
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > MAX_IMAGE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Save file
    upload_folder = get_image_upload_folder()
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)
    
    # Generate URL for the uploaded file
    image_url = f"/static/book_images/{unique_filename}"
    
    return jsonify({
        'success': True,
        'url': image_url,
        'filename': unique_filename
    })

@book_bp.route('/books/<int:book_id>/project-description/upload', methods=['POST'])
@writer_or_book_platform_required
def upload_project_description_media(book_id, user_profile, profile_type):
    """Upload image, audio, or video for rich project descriptions (CKEditor + toolbar)."""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id,
            collaborator_id=author_id,
            is_active=True,
        ).first()
        if not collaboration:
            return ckeditor_upload_response(error='Access denied')

    embed_url = (request.form.get('embed_url') or '').strip()
    if embed_url:
        normalized = normalize_video_embed_url(embed_url)
        if not normalized:
            return ckeditor_upload_response(error='Only YouTube and Vimeo links are allowed.')
        html = build_video_iframe_html(normalized)
        return jsonify({
            'uploaded': 1,
            'url': normalized,
            'html': html,
        })

    if 'upload' not in request.files:
        return ckeditor_upload_response(error='No file uploaded')

    file = request.files['upload']
    if not file or file.filename == '':
        return ckeditor_upload_response(error='No file selected')

    media_type = (request.form.get('media_type') or 'image').strip().lower()
    try:
        public_url, filename = save_project_media_file(
            file,
            book_id=book_id,
            app_root=current_app.root_path,
            media_type=media_type,
        )
    except ProjectDescriptionError as exc:
        return ckeditor_upload_response(error=str(exc))

    html = None
    if media_type == 'audio':
        html = build_audio_html(public_url)
    elif media_type == 'video':
        html = build_video_html(public_url)
    elif media_type == 'image':
        html = build_image_html(public_url)

    payload = {
        'uploaded': 1,
        'fileName': filename,
        'url': public_url,
        'html': html,
    }
    return jsonify(payload)

@book_bp.route('/books/<int:book_id>/images')
@writer_or_book_platform_required
def get_chapter_images(book_id, user_profile, profile_type):
    """Get all images uploaded for a book"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check access permissions
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        # Check if user is a collaborator
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id,
            collaborator_id=author_id,
            is_active=True
        ).first()
        if not collaboration:
            return jsonify({'error': 'Access denied'}), 403
    
    # Get all images in the book's image folder
    upload_folder = get_image_upload_folder()
    images = []
    
    if os.path.exists(upload_folder):
        for filename in os.listdir(upload_folder):
            if allowed_image_file(filename):
                images.append({
                    'url': f"/static/book_images/{filename}",
                    'filename': filename,
                    'name': os.path.splitext(filename)[0]
                })
    
    return jsonify({'images': images})

# Digital Book Upload Routes

def _render_upload_digital_book_form(form):
    return render_template(
        "book_platform/upload_digital_book.html",
        form=form,
    )


def _upload_digital_book_accepts_json():
    """True when the client expects JSON (fetch/XHR from upload form)."""
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return True
    accept = request.headers.get("Accept") or ""
    return "application/json" in accept


def _upload_digital_book_validation_response(form):
    import os as _os

    lines = []
    for field, errors in form.errors.items():
        for error in errors:
            if field != "recap" or _os.getenv("FLASK_ENV") != "development":
                lines.append(f"{field}: {error}")
    message = "; ".join(lines) if lines else "Please check the form and try again."
    if _upload_digital_book_accepts_json():
        return jsonify(success=False, error=message), 400
    for field, errors in form.errors.items():
        for error in errors:
            if field != "recap" or _os.getenv("FLASK_ENV") != "development":
                flash(f"{field}: {error}", "error")
    return _render_upload_digital_book_form(form)


def _upload_digital_book_error(form, message, status_code=400):
    if _upload_digital_book_accepts_json():
        return jsonify(success=False, error=message), status_code
    flash(message, "error")
    return _render_upload_digital_book_form(form)


@book_bp.route('/upload-digital-book', methods=['GET', 'POST'])
@book_platform_required
def upload_digital_book():
    """List a finished ebook on Ink Studio: upload file + cover (author need not write the book in-platform)."""
    
    logger.info(f"Upload digital book - Method: {request.method}, User: {current_user.user_id if current_user.is_authenticated else 'Not authenticated'}")

    if _author_needs_publishing_agreement(current_user.user_id):
        flash('Accept the Author Publishing Agreement before listing books.', 'warning')
        if request.method == 'POST' and _upload_digital_book_accepts_json():
            return jsonify({
                'success': False,
                'error': 'Accept the Author Publishing Agreement first.',
                'redirect': url_for('book_platform.author_publishing_agreement', next=request.path),
            }), 403
        if request.method == 'POST':
            flash('Accept the Author Publishing Agreement before listing books.', 'warning')
        return _redirect_to_publishing_agreement(request.path)
    
    form = DigitalBookUploadForm()
    _lang_choices = book_language_select_choices()
    form.ebook_language.choices = _lang_choices

    # In development, skip recaptcha validation
    import os
    if os.getenv('FLASK_ENV') == 'development':
        # Remove recaptcha from validation in development
        if hasattr(form, 'recap'):
            form.recap.validators = []
    
    if request.method == 'POST':
        logger.info(f"POST request received for digital book upload")
        logger.info(f"Form data keys: {list(request.form.keys())}")
        logger.info(f"Files in request: {list(request.files.keys())}")
        
        # Check if form validates
        if not form.validate():
            logger.warning(f"Form validation failed: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    logger.warning(f"  {field}: {error}")
            return _upload_digital_book_validation_response(form)
        else:
            logger.info("Form validation passed")
    
    def _as_bool(v):
        if isinstance(v, bool):
            return v
        if v is None:
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    if form.validate_on_submit():
        try:
            logger.info("Starting digital book upload process")
            
            # Get user profile
            user_profile, profile_type = get_user_profile()
            logger.info(f"User profile: {profile_type}, User ID: {current_user.user_id}")
            
            if not user_profile:
                logger.error("No user profile found")
                return _upload_digital_book_error(
                    form, "Please ensure you have an Ink Studio or Writer profile."
                )
            
            author_id = get_profile_id(user_profile, profile_type)
            logger.info(f"Author ID: {author_id}")
            
            if not author_id:
                logger.error(f"get_profile_id returned None for user_id={current_user.user_id}, profile_type={profile_type}")
                return _upload_digital_book_error(
                    form,
                    "Could not determine author ID. Please ensure your profile is set up correctly.",
                )

            terms_error = validate_listing_terms_payload(request.form or {})
            if terms_error:
                return _upload_digital_book_error(form, terms_error)
            
            # Handle file uploads
            digital_file = form.digital_book_file.data
            cover_image = form.cover_image.data
            
            logger.info(f"Digital file: {digital_file.filename if digital_file else 'None'}")
            logger.info(f"Cover image: {cover_image.filename if cover_image else 'None'}")
            logger.info(f"Title: {form.title.data}")
            
            # Create upload directories
            digital_books_dir = os.path.join(current_app.root_path, 'static', 'digital_books')
            covers_dir = os.path.join(current_app.root_path, 'static', 'book_covers')
            os.makedirs(digital_books_dir, exist_ok=True)
            os.makedirs(covers_dir, exist_ok=True)
            
            # Save digital book file
            digital_filename = secure_filename(digital_file.filename)
            name, ext = os.path.splitext(digital_filename)
            unique_digital_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
            digital_file_path = os.path.join(digital_books_dir, unique_digital_filename)
            digital_file.save(digital_file_path)
            
            # Get file info
            file_stat = os.stat(digital_file_path)
            file_type = ext.lower().lstrip('.')
            
            # Extract text from digital book (before cover AI so we fail fast on bad files)
            extraction_result = digital_book_processor.extract_text(digital_file_path, file_type)
            
            if not extraction_result['success']:
                return _upload_digital_book_error(
                    form,
                    f"Failed to extract text from file: {extraction_result['error']}",
                )

            # Cover: author file, or optional AI (Gemini); at least one required for marketplace rules
            cover_path = None
            has_cover_file = bool(cover_image and getattr(cover_image, "filename", None))
            if has_cover_file:
                cover_filename = secure_filename(cover_image.filename)
                cover_name, cover_ext = os.path.splitext(cover_filename)
                unique_cover_filename = f"{cover_name}_{uuid.uuid4().hex[:8]}{cover_ext}"
                abs_cover = os.path.join(covers_dir, unique_cover_filename)
                cover_image.save(abs_cover)
                cover_path = f"book_covers/{unique_cover_filename}"
            elif form.use_ai_cover.data:
                cover_path = promote_listing_preview_to_cover()
                if not cover_path:
                    return _upload_digital_book_error(
                        form,
                        "Generate an AI cover preview and choose “Use this cover” before listing your book, "
                        "or upload a cover image instead.",
                    )
            else:
                return _upload_digital_book_error(
                    form,
                    "Please upload a cover image or choose Generate with AI and confirm a preview.",
                )

            primary_lang = (form.ebook_language.data or "en").lower().strip()
            if primary_lang not in TTS_BOOK_LANGUAGES:
                return _upload_digital_book_error(
                    form, "Choose a supported ebook language from the list."
                )
            if form.digital_price.data is None:
                return _upload_digital_book_error(
                    form, "Set a digital ebook price before creating the listing."
                )
            if form.digital_price.data < 0:
                return _upload_digital_book_error(
                    form, "Price cannot be negative."
                )

            # Create book project
            logger.info(f"Creating book project: {form.title.data}")
            book = BookProject(
                title=form.title.data,
                description=form.description.data,
                genre=form.genre.data,
                language=primary_lang,
                author_id=author_id,
                word_count=extraction_result['word_count'],
                price=form.digital_price.data,
                cover_image=cover_path,
                digital_file_path=f"digital_books/{unique_digital_filename}",
                digital_file_type=file_type,
                digital_file_size=file_stat.st_size,
                digital_file_uploaded_at=datetime.now(timezone.utc),
                status=BookStatus.DRAFT
            )
            # Step 1 auto-publishes ebook listing; step 2 is audiobook-only tasks.
            book.digital_book_published = True
            book.digital_book_published_at = datetime.now(timezone.utc)
            record_listing_attestation(book)
            
            db.session.add(book)
            db.session.flush()  # Flush to get book.id
            logger.info(f"Book created with ID: {book.id}, Title: {book.title}")

            from glconnect.isbn_pool_service import assign_marketplace_isbn_if_needed, IsbnPoolError

            try:
                assign_marketplace_isbn_if_needed(book)
            except IsbnPoolError as e:
                db.session.rollback()
                flash(str(e), 'error')
                return redirect(url_for('book_platform.upload_digital_book'))

            db.session.commit()
            logger.info(f"Book {book.id} committed to database successfully")

            flash(
                "Step 1 complete: ebook is now live. Next: generate audiobook or skip for now."
                + (
                    " Note: PDF listings often read poorly in-browser; consider also offering EPUB or DOCX for reflowable reading."
                    if file_type == "pdf"
                    else ""
                ),
                "success",
            )
            
            logger.info(f"Upload successful! Redirecting to book {book.id}")
            next_step_url = url_for("book_platform.book_audiobook", book_id=book.id)
            if _upload_digital_book_accepts_json():
                return jsonify(
                    success=True,
                    redirect=next_step_url,
                )
            return redirect(next_step_url)
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error uploading book: {str(e)}"
            logger.error(f"Error in upload_digital_book: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"ERROR in upload_digital_book: {str(e)}")
            traceback.print_exc()
            return _upload_digital_book_error(form, error_msg, 500)
    
    # GET request - show form
    if request.method == 'GET':
        logger.info("Showing upload digital book form")
    
    return _render_upload_digital_book_form(form)

@book_bp.route('/debug/check-upload', methods=['GET'])
@book_platform_required
def debug_check_upload():
    """Debug endpoint to check upload status"""
    from glconnect.book_platform_models import BookProject, BookPlatformUser
    
    user_profile, profile_type = get_user_profile()
    author_id = get_profile_id(user_profile, profile_type)
    
    # Get recent books
    recent_books = BookProject.query.filter_by(author_id=author_id).order_by(BookProject.created_at.desc()).limit(5).all()
    
    debug_info = {
        'user_id': current_user.user_id,
        'author_id': author_id,
        'profile_type': profile_type,
        'recent_books': []
    }
    
    for book in recent_books:
        debug_info['recent_books'].append({
            'id': book.id,
            'title': book.title,
            'status': str(book.status),
            'created_at': str(book.created_at),
            'has_digital_file': bool(book.digital_file_path),
            'digital_file_path': book.digital_file_path
        })
    
    return jsonify(debug_info)

@book_bp.route('/books/<int:book_id>/audio-generation-status')
@book_platform_required
def audio_generation_status(book_id):
    """Check audio generation status for a book"""
    from glconnect.book_platform_models import AudioGenerationTask
    
    book = BookProject.query.get_or_404(book_id)
    
    # Check access permissions
    user_profile, profile_type = get_user_profile()
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get latest audio generation task
    task = AudioGenerationTask.query.filter_by(
        book_project_id=book_id
    ).order_by(AudioGenerationTask.created_at.desc()).first()
    
    if not task:
        return jsonify({'status': 'not_started'})
    
    return jsonify({
        'status': task.status,
        'progress': task.progress,
        'error_message': task.error_message,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None
    })

@book_bp.route('/books/<int:book_id>/download-digital')
@login_required
def download_digital_book(book_id):
    """Download digital book — author or signed-in buyer."""
    book = BookProject.query.get_or_404(book_id)
    user_id = current_user.user_id
    is_author = bool(book.author and book.author.user_id == user_id)
    if not is_author:
        bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
        buyer_id = bp_user.id if bp_user else None
        purchases = BookPurchase.query.filter(
            db.or_(
                BookPurchase.buyer_user_id == user_id,
                (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
            ),
            BookPurchase.book_project_id == book_id,
            BookPurchase.status == TransactionStatus.COMPLETED
        ).all()
        has_digital_access = any(
            getattr(p, 'purchase_format', 'digital') in ('digital', 'bundle') for p in purchases
        )
        if not has_digital_access:
            flash("You must purchase this book to download it.", "error")
            return redirect(url_for('book_platform.marketplace'))
    
    primary = (book.language or "en").lower().strip()
    req_lang = (request.args.get("lang") or primary).lower().strip()

    if req_lang != primary:
        flash("Only the original manuscript language is available for download.", "error")
        return redirect(url_for('book_platform.marketplace'))
    if not book.digital_file_path:
        flash("Digital file not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))
    rel_path = book.digital_file_path
    dl_ext = book.digital_file_type or "bin"

    file_path = os.path.join(current_app.root_path, 'static', rel_path)

    if not os.path.exists(file_path):
        flash("Digital file not found.", "error")
        return redirect(url_for('book_platform.marketplace'))

    safe_ext = (dl_ext or "txt").lstrip(".").lower() or "txt"
    download_basename = f"{book.title} ({language_label(req_lang)}).{safe_ext}"

    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True,
        download_name=download_basename,
    )

@book_bp.route('/audiobook/<int:book_id>/file')
@login_required
def serve_audiobook_file(book_id):
    """Serve the audiobook file — author or signed-in buyer."""
    book = BookProject.query.get_or_404(book_id)
    
    if not book.has_audiobook or not book.audiobook_file_path:
        return "Audiobook not found", 404

    user_id = current_user.user_id
    is_author = bool(book.author and book.author.user_id == user_id)
    if not is_author:
        bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
        buyer_id = bp_user.id if bp_user else None
        purchases = BookPurchase.query.filter(
            db.or_(
                BookPurchase.buyer_user_id == user_id,
                (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
            ),
            BookPurchase.book_project_id == book_id,
            BookPurchase.status == TransactionStatus.COMPLETED
        ).all()
        has_audiobook_access = any(
            getattr(p, 'purchase_format', 'digital') in ('audiobook', 'bundle') for p in purchases
        )
        if not has_audiobook_access:
            return "Access denied", 403
    
    # Check if file exists
    if not os.path.exists(book.audiobook_file_path):
        return "Audiobook file not found", 404
    
    # Convert full path to relative path for serving
    # audiobook_file_path is stored as full path, need to extract relative path
    static_path = os.path.join(current_app.root_path, 'static')
    if book.audiobook_file_path.startswith(static_path):
        relative_path = os.path.relpath(book.audiobook_file_path, static_path)
        return send_from_directory(
            os.path.join(current_app.root_path, 'static'),
            relative_path,
            as_attachment=False,  # Stream, don't force download
            mimetype='audio/mpeg'
        )
    else:
        # If it's already a relative path or different format, try direct serve
        return send_from_directory(
            os.path.dirname(book.audiobook_file_path),
            os.path.basename(book.audiobook_file_path),
            as_attachment=False,
            mimetype='audio/mpeg'
        )


@book_bp.route('/audiobook/<int:book_id>/preview')
def serve_audiobook_preview(book_id):
    """Serve a short public preview clip (first ~30s) for marketplace discovery."""
    book = BookProject.query.get_or_404(book_id)

    if not book.has_audiobook or not book.audiobook_published or not book.audiobook_file_path:
        return "Audiobook preview not available", 404
    if not os.path.exists(book.audiobook_file_path):
        return "Audiobook preview file not found", 404

    file_path = book.audiobook_file_path
    file_size = os.path.getsize(file_path)
    # Approximate 30 seconds at common audiobook bitrates.
    preview_limit = min(file_size, 512 * 1024)

    range_header = request.headers.get('Range', None)
    if range_header:
        range_match = re.search(r'bytes=(\d*)-(\d*)', range_header)
        if range_match:
            start_str, end_str = range_match.groups()
            if start_str:
                start = int(start_str)
                end = int(end_str) if end_str else (preview_limit - 1)
            else:
                suffix = int(end_str) if end_str else 0
                start = max(0, preview_limit - suffix)
                end = preview_limit - 1
            end = min(end, preview_limit - 1)
            if start >= preview_limit or start > end:
                return Response(status=416)
            chunk_size = end - start + 1
            with open(file_path, 'rb') as f:
                f.seek(start)
                chunk = f.read(chunk_size)
            response = Response(chunk, status=206, mimetype='audio/mpeg')
            response.headers['Content-Range'] = f'bytes {start}-{end}/{preview_limit}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(chunk_size)
            response.headers['Content-Disposition'] = 'inline; filename="audiobook-preview.mp3"'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response

    with open(file_path, 'rb') as f:
        chunk = f.read(preview_limit)
    response = Response(chunk, status=206, mimetype='audio/mpeg')
    response.headers['Content-Range'] = f'bytes 0-{preview_limit - 1}/{preview_limit}'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Length'] = str(preview_limit)
    response.headers['Content-Disposition'] = 'inline; filename="audiobook-preview.mp3"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


def _user_has_audiobook_access(book, user_id):
    """Check if user (author or purchaser) has audiobook access."""
    if book.author and book.author.user_id == user_id:
        return True
    bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
    buyer_id = bp_user.id if bp_user else None
    purchases = BookPurchase.query.filter(
        db.or_(
            BookPurchase.buyer_user_id == user_id,
            (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
        ),
        BookPurchase.book_project_id == book.id,
        BookPurchase.status == TransactionStatus.COMPLETED
    ).all()
    return any(
        getattr(p, 'purchase_format', 'digital') in ('audiobook', 'bundle') for p in purchases
    )


@book_bp.route('/audiobook/<int:book_id>/chapter/<int:chapter_id>/file')
@login_required
def serve_audiobook_chapter_file(book_id, chapter_id):
    """Serve a single audiobook chapter audio file."""
    book = BookProject.query.get_or_404(book_id)
    chapter = AudiobookChapter.query.filter_by(id=chapter_id, book_project_id=book_id).first_or_404()
    
    if not book.has_audiobook:
        return "Audiobook not found", 404

    if not _user_has_audiobook_access(book, current_user.user_id):
        return "Access denied", 403
    
    if not os.path.exists(chapter.audio_file_path):
        return "Chapter audio not found", 404
    
    static_path = os.path.join(current_app.root_path, 'static')
    if chapter.audio_file_path.startswith(static_path):
        relative_path = os.path.relpath(chapter.audio_file_path, static_path)
        return send_from_directory(
            os.path.join(current_app.root_path, 'static'),
            relative_path,
            as_attachment=False,
            mimetype='audio/mpeg'
        )
    return send_from_directory(
        os.path.dirname(chapter.audio_file_path),
        os.path.basename(chapter.audio_file_path),
        as_attachment=False,
        mimetype='audio/mpeg'
    )


@book_bp.route('/audiobook/<int:book_id>/player')
@login_required
def audiobook_player(book_id):
    """Audiobook player page with chapter list - listeners can pick and play any chapter."""
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user),
    ).get_or_404(book_id)
    
    if not book.has_audiobook:
        flash("Audiobook not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))

    if not _user_has_audiobook_access(book, current_user.user_id):
        flash("You must purchase the audiobook to listen.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    chapters = AudiobookChapter.query.filter_by(book_project_id=book_id).order_by(AudiobookChapter.chapter_number).all()
    chapter_tracklist = []
    for ch in chapters:
        src = url_for(
            'book_platform.serve_audiobook_chapter_file',
            book_id=book.id,
            chapter_id=ch.id,
        )
        chapter_tracklist.append({
            'id': ch.id,
            'title': ch.title,
            'seconds': ch.duration_seconds or 0,
            'src': src,
        })
    single_audiobook_src = None
    if not chapter_tracklist:
        single_audiobook_src = url_for('book_platform.serve_audiobook_file', book_id=book.id)

    author_label = 'Author'
    if book.author:
        author_label = book.author.pen_name or (
            book.author.user.username if book.author.user else author_label
        )

    return render_template(
        'book_platform/audiobook_player.html',
        book=book,
        chapters=chapters,
        chapter_tracklist=chapter_tracklist,
        single_audiobook_src=single_audiobook_src,
        cover_url=_marketplace_cover_url(book),
        author_label=author_label,
        audio_download_url=url_for('book_platform.download_audio_book', book_id=book.id),
    )


@book_bp.route('/books/<int:book_id>/download-audio')
@login_required
def download_audio_book(book_id):
    """Download audiobook as one MP3, or a ZIP of chapter MP3s when no single file exists."""
    book = BookProject.query.get_or_404(book_id)

    if not book.has_audiobook:
        flash("Audiobook not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))

    user_id = current_user.user_id
    is_author = bool(book.author and book.author.user_id == user_id)

    if not is_author:
        bp_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
        buyer_id = bp_user.id if bp_user else None
        purchases = BookPurchase.query.filter(
            db.or_(
                BookPurchase.buyer_user_id == user_id,
                (BookPurchase.buyer_id == buyer_id) if buyer_id else db.false()
            ),
            BookPurchase.book_project_id == book_id,
            BookPurchase.status == TransactionStatus.COMPLETED
        ).all()
        has_audiobook_access = any(
            getattr(p, 'purchase_format', 'digital') in ('audiobook', 'bundle') for p in purchases
        )
        if not has_audiobook_access:
            flash("You must purchase the audiobook to download it.", "error")
            return redirect(url_for('book_platform.marketplace'))

    safe_title = secure_filename((book.title or "audiobook").replace(" ", "_")) or "audiobook"

    single_path = (book.audiobook_file_path or "").strip()
    if single_path and os.path.exists(single_path):
        static_path = os.path.join(current_app.root_path, 'static')
        if single_path.startswith(static_path):
            relative_path = os.path.relpath(single_path, static_path)
            return send_from_directory(
                os.path.join(current_app.root_path, 'static'),
                relative_path,
                as_attachment=True,
                download_name=f"{safe_title}_audiobook.mp3",
            )
        return send_from_directory(
            os.path.dirname(single_path),
            os.path.basename(single_path),
            as_attachment=True,
            download_name=f"{safe_title}_audiobook.mp3",
        )

    ab_chapters = (
        AudiobookChapter.query.filter_by(book_project_id=book_id)
        .order_by(AudiobookChapter.chapter_number)
        .all()
    )
    zip_members = []
    for ch in ab_chapters:
        disk_path = resolved_audiobook_chapter_disk_path(ch)
        if not disk_path:
            continue
        slug = secure_filename((ch.title or f"chapter_{ch.chapter_number}")[:120]) or f"chapter_{ch.chapter_number}"
        arcname = f"{ch.chapter_number:03d}_{slug}.mp3"
        zip_members.append((disk_path, arcname))

    if not zip_members:
        flash("Downloadable audio files are not available for this title yet.", "error")
        return redirect(url_for('book_platform.my_library'))

    buf = SpooledTemporaryFile(max_size=80 * 1024 * 1024, mode="w+b")
    try:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for disk_path, arcname in zip_members:
                zf.write(disk_path, arcname=arcname)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f"{safe_title}_audiobook_chapters.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        logger.error("download_audio_book zip failed for book %s: %s", book_id, e, exc_info=True)
        flash("Could not build audiobook download.", "error")
        return redirect(url_for('book_platform.my_library'))

# ============================================================================
# REVIEWER & INVESTMENT SYSTEM ROUTES
# ============================================================================

def _accredited_book_reviews_disabled_flash():
    flash(
        'Accredited book reviews are no longer offered on Ink Studio. '
        'Collaboration roles, admin tools, and existing payouts are unchanged.',
        'info',
    )


def _accredited_book_reviews_disabled_redirect_public():
    _accredited_book_reviews_disabled_flash()
    if current_user.is_authenticated:
        return redirect(url_for('book_platform.dashboard'))
    return redirect(url_for('routes1.login'))


# Reviewer Registration
@book_bp.route('/reviewers/register', methods=['GET', 'POST'])
@login_required
def register_reviewer():
    """Register as an accredited reviewer"""
    _accredited_book_reviews_disabled_flash()
    return redirect(url_for('book_platform.dashboard'))

# Reviewer Marketplace
@book_bp.route('/reviewers', methods=['GET'])
def reviewers():
    """Browse accredited reviewers"""
    return _accredited_book_reviews_disabled_redirect_public()

# Books seeking review - visible to accredited reviewers (pending requests addressed to them)
@book_bp.route('/reviewers/books-seeking-review', methods=['GET'])
@login_required
def books_seeking_review():
    """Reviewers see books with pending review requests addressed to them"""
    _accredited_book_reviews_disabled_flash()
    return redirect(url_for('book_platform.dashboard'))


# Reviewer Profile
@book_bp.route('/reviewers/<int:reviewer_id>', methods=['GET'])
def reviewer_profile(reviewer_id):
    """View reviewer profile"""
    AccreditedReviewer.query.get_or_404(reviewer_id)
    return _accredited_book_reviews_disabled_redirect_public()

# Helper function to send reviewer invitation email
def send_reviewer_invitation_email(reviewer, book, inviter, message=None):
    """Send reviewer invitation email via Mailtrap"""
    sender = os.getenv("SENDER_MAIL", "info@ndotonic.com")
    api_key = os.getenv("MAIL_TRAP")
    
    if not api_key:
        logger.warning("MAIL_TRAP API key not set. Cannot send reviewer invitation email.")
        return False
    
    # Get reviewer email from user account
    if not reviewer.user or not reviewer.user.email:
        logger.warning(f"Reviewer {reviewer.id} has no associated user email")
        return False
    
    reviewer_email = reviewer.user.email
    
    # Generate book URL
    book_url = url_for('book_platform.view_book', book_id=book.id, _external=True)
    
    # Get inviter name
    inviter_name = inviter.pen_name or (inviter.user.username if hasattr(inviter, 'user') and inviter.user else "The Author")
    
    # Build email content
    subject = f"Review Invitation: {book.title}"
    
    message_text = f"""Hello {reviewer.reviewer_name},

{inviter_name} has invited you to review their book "{book.title}".

"""
    
    if message:
        message_text += f"Message from {inviter_name}:\n{message}\n\n"
    
    message_text += f"""Book Details:
- Title: {book.title}
- Description: {book.description[:200] if book.description else 'No description available'}...
- View Book: {book_url}

To accept this invitation and submit your review, please visit the book page using the link above.

As an accredited reviewer, you'll earn revenue share on book sales based on your review agreement.

Best regards,
Ink Studio Team
"""
    
    try:
        mail = Mail(
            sender=Address(email=sender, name="Ink Studio"),
            to=[Address(email=reviewer_email)],
            subject=subject,
            text=message_text,
            category="Reviewer Invitation"
        )
        client = MailtrapClient(token=api_key)
        client.send(mail)
        logger.info(f"Reviewer invitation email sent to {reviewer_email} for book {book.id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reviewer invitation email: {str(e)}", exc_info=True)
        return False

@book_bp.route('/reviewers/<int:reviewer_id>/invite', methods=['POST'])
@writer_or_book_platform_required
def invite_reviewer(reviewer_id, user_profile, profile_type):
    """Invite a reviewer to review a book"""
    return jsonify({
        'success': False,
        'error': 'Accredited book reviews are no longer available.',
    }), 410

# Request Review for Book
@book_bp.route('/books/<int:book_id>/request-review', methods=['GET', 'POST'])
@writer_or_book_platform_required
def request_review(book_id, user_profile, profile_type):
    """Author requests a review from accredited reviewers"""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    
    if book.author_id != author_id:
        flash('You can only request reviews for your own books.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    _accredited_book_reviews_disabled_flash()
    return redirect(url_for('book_platform.view_book', book_id=book_id))

# Submit Review
@book_bp.route('/books/<int:book_id>/reviews/submit', methods=['GET', 'POST'])
@login_required
def submit_review(book_id):
    """Reviewer submits a review for a book"""
    BookProject.query.get_or_404(book_id)
    _accredited_book_reviews_disabled_flash()
    return redirect(url_for('book_platform.view_book', book_id=book_id))


# Author publishes a submitted review (and records task completion / fixed-fee earning)
@book_bp.route('/books/<int:book_id>/reviews/<int:review_id>/publish', methods=['POST'])
@writer_or_book_platform_required
def publish_review(book_id, review_id, user_profile, profile_type):
    """Author approves and publishes a submitted review; if agreed_fee set, creates task earning for reviewer."""
    return jsonify({
        'success': False,
        'error': 'Accredited book reviews are no longer available.',
    }), 410
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'success': False, 'error': 'Only the author can publish reviews'}), 403
    
    review = BookReview.query.filter_by(id=review_id, book_project_id=book_id).first_or_404()
    if review.status != ReviewStatus.SUBMITTED:
        return jsonify({'success': False, 'error': 'Review is not in submitted state'}), 400
    
    review.status = ReviewStatus.PUBLISHED
    review.published_at = datetime.now(timezone.utc)
    
    if review.review_request_id:
        req = ReviewRequest.query.get(review.review_request_id)
        if req:
            req.status = ReviewRequestStatus.COMPLETED
            req.completed_at = datetime.now(timezone.utc)
    
    if review.agreed_fee and review.agreed_fee > 0:
        existing = ReviewerEarning.query.filter_by(review_id=review.id, is_guarantee_payment=False).first()
        if not existing:
            earning = ReviewerEarning(
                reviewer_id=review.reviewer_id,
                review_id=review.id,
                amount=review.agreed_fee,
                currency=book.currency or 'USD',
                status=TransactionStatus.PENDING,
                notes='Fixed fee for completed review (author-paid task)'
            )
            db.session.add(earning)
            review.reviewer.total_earnings = (review.reviewer.total_earnings or 0) + review.agreed_fee
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Review published.' + (f' Reviewer task fee: ${review.agreed_fee:.2f} (pending payout).' if review.agreed_fee else '')})


# Author marks fixed-fee task as paid (e.g. after external transfer or platform payout)
@book_bp.route('/books/<int:book_id>/reviews/<int:review_id>/pay-task', methods=['POST'])
@writer_or_book_platform_required
def pay_review_task(book_id, review_id, user_profile, profile_type):
    """Author marks the agreed fixed fee as paid for this review."""
    return jsonify({
        'success': False,
        'error': 'Accredited book reviews are no longer available.',
    }), 410
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        return jsonify({'success': False, 'error': 'Only the author can mark task as paid'}), 403
    
    review = BookReview.query.filter_by(id=review_id, book_project_id=book_id).first_or_404()
    if not review.agreed_fee or review.agreed_fee <= 0:
        return jsonify({'success': False, 'error': 'No agreed fee for this review'}), 400
    if review.author_paid_at:
        return jsonify({'success': False, 'error': 'Task already marked as paid'}), 400
    
    review.author_paid_at = datetime.now(timezone.utc)
    for earning in ReviewerEarning.query.filter_by(review_id=review.id, is_guarantee_payment=False).all():
        if earning.amount == review.agreed_fee:
            earning.status = TransactionStatus.COMPLETED
            earning.paid_at = datetime.now(timezone.utc)
            break
    db.session.commit()
    return jsonify({'success': True, 'message': f'Marked ${review.agreed_fee:.2f} as paid to reviewer.'})


# Investment Campaign Creation
@book_bp.route('/books/<int:book_id>/create-campaign', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_investment_campaign(book_id, user_profile, profile_type):
    """Author creates an investment campaign for their book. Uploaded books are never allowed campaigns."""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    
    if book.author_id != author_id:
        flash('You can only create campaigns for your own books.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Uploaded books (PDF/EPUB/DOCX) can never have campaigns—only selling digital/audio
    if book.digital_file_path:
        flash('Book campaigns are not available for uploaded books. Uploaded books can only be sold (digital/audio) in the marketplace.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Check if campaign already exists
    existing_campaign = InvestmentCampaign.query.filter_by(book_project_id=book_id).first()
    if existing_campaign:
        flash('A book campaign already exists for this title.', 'info')
        return redirect(url_for('book_platform.campaign_detail', campaign_id=existing_campaign.id))
    
    # Check if book is ready for investment
    investment_readiness = check_investment_readiness(book)
    
    if not investment_readiness['is_ready']:
        flash('Your book is not ready for a campaign yet. Please complete the following requirements:', 'warning')
        for issue in investment_readiness['issues']:
            flash(f'• {issue}', 'info')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    form = InvestmentCampaignForm()
    
    if form.validate_on_submit():
        try:
            from glconnect.book_campaign_patronage import (
                CAMPAIGN_GOAL_DEADLINE_DAYS,
                is_book_campaign_patronage_mode,
                patronage_campaign_terms,
            )
            patronage = is_book_campaign_patronage_mode()
            patronage_terms = patronage_campaign_terms() if patronage else {}
            # Create timezone-aware datetimes in UTC
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=CAMPAIGN_GOAL_DEADLINE_DAYS)
            
            campaign = InvestmentCampaign(
                book_project_id=book_id,
                title=form.title.data,
                description=sanitize_project_description(form.description.data, book_id=book_id),
                tentative_timeline=form.tentative_timeline.data or None,
                pitch_video_url=form.pitch_video_url.data,
                funding_goal=form.funding_goal.data,
                minimum_investment=0.01,
                maximum_investment=None,
                revenue_share_percentage=patronage_terms["revenue_share_percentage"],
                return_multiplier_cap=patronage_terms["return_multiplier_cap"],
                investment_period_days=CAMPAIGN_GOAL_DEADLINE_DAYS,
                status=CampaignStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date
            )
            
            db.session.add(campaign)
            book.has_investment_campaign = True
            db.session.commit()
            
            flash('Book campaign launched successfully!', 'success')
            return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign.id))
            
        except ProjectDescriptionError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating campaign: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template(
        'book_platform/create_campaign.html',
        form=form,
        book=book,
        media_guide=MEDIA_GUIDE,
    )


@book_bp.route('/campaigns/<int:campaign_id>/edit-project', methods=['GET', 'POST'])
@writer_or_book_platform_required
def edit_campaign_project(campaign_id, user_profile, profile_type):
    """Author edits campaign pitch and book project description shown on the campaign page."""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    book = campaign.book_project
    author_id = get_profile_id(user_profile, profile_type)

    if not author_id or book.author_id != author_id:
        flash('Only the author can edit this project.', 'error')
        return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))

    form = EditCampaignProjectForm()
    upload_url = url_for('book_platform.upload_project_description_media', book_id=book.id)
    preview_page_url = url_for(
        'book_platform.campaign_detail',
        campaign_id=campaign_id,
        preview=1,
    )

    if request.method == 'GET':
        form.title.data = campaign.title
        form.book_description.data = book.description or ''
        form.campaign_description.data = campaign.description or ''
        form.tentative_timeline.data = campaign.tentative_timeline or ''
        form.pitch_video_url.data = campaign.pitch_video_url or ''

    if form.validate_on_submit():
        try:
            book.description = sanitize_project_description(
                form.book_description.data,
                book_id=book.id,
            )
            campaign.title = form.title.data.strip()
            campaign.description = sanitize_project_description(
                form.campaign_description.data,
                book_id=book.id,
            )
            campaign.tentative_timeline = (form.tentative_timeline.data or '').strip() or None
            pitch_url = (form.pitch_video_url.data or '').strip() or None
            if pitch_url:
                embed = normalize_video_embed_url(pitch_url)
                campaign.pitch_video_url = embed or pitch_url
            else:
                campaign.pitch_video_url = None
            db.session.commit()
            flash('Project updated. Preview your campaign page before sharing.', 'success')
            return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id, preview=1))
        except ProjectDescriptionError as exc:
            db.session.rollback()
            flash(str(exc), 'error')
        except Exception as exc:
            db.session.rollback()
            logger.error('Error updating campaign project: %s', exc, exc_info=True)
            flash(f'An error occurred: {exc}', 'error')

    return render_template(
        'book_platform/edit_campaign_project.html',
        form=form,
        campaign=campaign,
        book=book,
        media_guide=MEDIA_GUIDE,
        upload_url=upload_url,
        preview_page_url=preview_page_url,
    )


def _legacy_investments_redirect(endpoint, **url_kwargs):
    """Permanent redirect from deprecated /investments/* URLs to /campaigns/* or /contributions/*."""
    query = request.args.to_dict(flat=True)
    return redirect(url_for(endpoint, **{**url_kwargs, **query}), code=301)


@book_bp.route('/investments', methods=['GET'])
@book_bp.route('/investments/', methods=['GET'])
def legacy_investments_discover_redirect():
    return _legacy_investments_redirect('book_platform.campaigns')


@book_bp.route('/investments/my-campaigns', methods=['GET'])
def legacy_my_campaigns_redirect():
    return _legacy_investments_redirect('book_platform.author_my_campaigns')


@book_bp.route('/investments/<int:campaign_id>', methods=['GET'])
def legacy_campaign_detail_redirect(campaign_id):
    return _legacy_investments_redirect('book_platform.campaign_detail', campaign_id=campaign_id)


@book_bp.route('/investments/<int:campaign_id>/invest', methods=['GET'])
def legacy_contribute_redirect(campaign_id):
    return _legacy_investments_redirect('book_platform.contribute_to_campaign', campaign_id=campaign_id)


@book_bp.route('/investments/my-returns/<int:book_id>', methods=['GET'])
def legacy_my_returns_redirect(book_id):
    return _legacy_investments_redirect('book_platform.investor_returns_by_book', book_id=book_id)


@book_bp.route('/investments/<int:contribution_id>/refund-status', methods=['GET'])
def legacy_refund_status_redirect(contribution_id):
    return _legacy_investments_redirect(
        'book_platform.contribution_refund_status',
        contribution_id=contribution_id,
    )


@book_bp.route('/campaigns/mine', methods=['GET'])
@writer_or_book_platform_required
def author_my_campaigns(user_profile, profile_type):
    """Author hub: manage patron campaigns started from their books."""
    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        flash('Complete your author profile to manage book campaigns.', 'warning')
        return redirect(url_for('book_platform.setup_profile', next=request.path))

    status_filter = request.args.get('status', 'all')
    query = (
        InvestmentCampaign.query
        .join(BookProject, InvestmentCampaign.book_project_id == BookProject.id)
        .options(joinedload(InvestmentCampaign.book_project))
        .filter(BookProject.author_id == author_id)
    )

    if status_filter == 'active':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.ACTIVE)
    elif status_filter == 'funded':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.FUNDED)
    elif status_filter == 'draft':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.DRAFT)
    elif status_filter != 'all':
        status_filter = 'all'

    campaigns = query.order_by(
        InvestmentCampaign.updated_at.desc(),
        InvestmentCampaign.created_at.desc(),
    ).all()

    return render_template(
        'book_platform/author_my_campaigns.html',
        campaigns=campaigns,
        status_filter=status_filter,
        is_author=True,
        ink_nav_active='my_campaigns',
        marketplace_cover_url=_marketplace_cover_url,
    )


# Patron campaign discovery — /campaigns is canonical; /investments GET → 301 redirect above.
@book_bp.route('/campaigns', methods=['GET'])
@login_required
def campaigns():
    """Browse patron book campaigns before publication."""
    from glconnect.book_campaign_patronage import resolve_expired_active_campaigns
    resolve_expired_active_campaigns(db)

    status_filter = request.args.get('status', 'active')
    search_query = request.args.get('q', '')
    saved_ids = saved_campaign_ids_for_user(current_user.user_id)
    
    # Join with BookProject to enable search
    query = InvestmentCampaign.query.join(BookProject)
    
    # Exclude campaigns where the current user is the author
    user_profile, profile_type = get_user_profile()
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        if author_id:
            query = query.filter(BookProject.author_id != author_id)
    
    if status_filter == 'saved':
        if saved_ids:
            query = query.filter(InvestmentCampaign.id.in_(saved_ids))
        else:
            query = query.filter(InvestmentCampaign.id == -1)
    elif status_filter == 'active':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.ACTIVE)
        query = query.filter(
            db.or_(
                InvestmentCampaign.end_date.is_(None),
                InvestmentCampaign.end_date > datetime.now(timezone.utc),
            )
        )
    elif status_filter == 'funded':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.FUNDED)
    elif status_filter == 'draft':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.DRAFT)
    elif status_filter == 'all':
        query = query.filter(
            InvestmentCampaign.status.in_([
                CampaignStatus.DRAFT,
                CampaignStatus.ACTIVE,
                CampaignStatus.FUNDED
            ])
        )
    elif status_filter != 'saved':
        status_filter = 'active'
        query = query.filter(InvestmentCampaign.status == CampaignStatus.ACTIVE)
        query = query.filter(
            db.or_(
                InvestmentCampaign.end_date.is_(None),
                InvestmentCampaign.end_date > datetime.now(timezone.utc),
            )
        )

    if search_query:
        query = query.filter(
            db.or_(
                InvestmentCampaign.title.ilike(f'%{search_query}%'),
                BookProject.title.ilike(f'%{search_query}%'),
                BookProject.description.ilike(f'%{search_query}%')
            )
        )
    
    if status_filter == 'saved':
        campaigns = query.order_by(InvestmentCampaign.updated_at.desc()).all()
    else:
        campaigns = query.order_by(InvestmentCampaign.created_at.desc()).all()
    backer_counts = campaign_backer_counts([c.id for c in campaigns])
    
    return render_template('book_platform/investments.html', 
                         campaigns=campaigns,
                         campaign_backer_counts=backer_counts,
                         saved_campaign_ids=saved_ids,
                         status_filter=status_filter,
                         search_query=search_query,
                         ink_nav_active='campaigns')


@book_bp.route('/campaigns/supported', methods=['GET'])
@login_required
def supported_projects():
    """Patron hub: track projects they supported and marketplace listing alerts."""
    from glconnect.patron_support_service import (
        group_patron_supported_projects,
        mark_patron_listing_notifications_read,
        patron_listing_notifications,
    )

    from glconnect.patron_support_service import ensure_patron_book_platform_user

    status_filter = request.args.get('status', 'all')
    bp_user = ensure_patron_book_platform_user(current_user.user_id, db)

    projects = group_patron_supported_projects(bp_user.id, db)

    if status_filter == 'active':
        projects = [p for p in projects if p['campaign'] and p['campaign'].status == CampaignStatus.ACTIVE]
    elif status_filter == 'listed':
        projects = [
            p for p in projects
            if p['book'] and p['book'].status == BookStatus.PUBLISHED
        ]
    elif status_filter == 'ended':
        projects = [
            p for p in projects
            if p['campaign'] and p['campaign'].status in (CampaignStatus.FAILED, CampaignStatus.CANCELLED)
        ]
    elif status_filter != 'all':
        status_filter = 'all'

    listing_alerts = patron_listing_notifications(bp_user.id, db, unread_only=True, limit=10)
    if listing_alerts:
        mark_patron_listing_notifications_read(bp_user.id, db)

    return render_template(
        'book_platform/supported_projects.html',
        projects=projects,
        listing_alerts=listing_alerts,
        status_filter=status_filter,
        ink_nav_active='supported',
        marketplace_cover_url=_marketplace_cover_url,
    )


@book_bp.route('/campaigns/<int:campaign_id>/translate', methods=['POST'])
@login_required
def translate_campaign_page(campaign_id):
    """AI-translate campaign page content for patrons (cached per language)."""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project).joinedload(BookProject.author),
    ).get_or_404(campaign_id)
    book = campaign.book_project
    if not book:
        return jsonify({'success': False, 'error': 'Book not found for this campaign'}), 404

    data = request.get_json(silent=True) or {}
    target_language = data.get('target_language') or request.form.get('target_language')
    if not target_language:
        return jsonify({'success': False, 'error': 'Target language is required'}), 400

    from glconnect.campaign_translation_service import translate_campaign

    result = translate_campaign(campaign, book, book.author, target_language, db)
    if not result.get('success'):
        return jsonify(result), 400
    return jsonify(result)


@book_bp.route('/campaigns/<int:campaign_id>/translations', methods=['GET'])
@login_required
def list_campaign_page_translations(campaign_id):
    """List languages with cached translations for a campaign."""
    InvestmentCampaign.query.get_or_404(campaign_id)
    from glconnect.campaign_translation_service import list_campaign_translation_languages

    return jsonify({
        'success': True,
        'languages': list_campaign_translation_languages(campaign_id, db),
    })


@book_bp.route('/campaigns/<int:campaign_id>/save', methods=['POST'])
@login_required
def toggle_saved_campaign(campaign_id):
    """Save or unsave a campaign for later (patrons only)."""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    book = campaign.book_project
    if book and book.author and book.author.user_id == current_user.user_id:
        return jsonify({'success': False, 'error': 'You cannot save your own campaign.'}), 400

    rec = SavedBookCampaign.query.filter_by(
        user_id=current_user.user_id,
        campaign_id=campaign_id,
    ).first()
    if rec:
        db.session.delete(rec)
        db.session.commit()
        return jsonify({'success': True, 'saved': False})

    db.session.add(SavedBookCampaign(
        user_id=current_user.user_id,
        campaign_id=campaign_id,
    ))
    db.session.commit()
    return jsonify({'success': True, 'saved': True})


# Campaign detail page (signed-in only — same gate as marketplace)
@book_bp.route('/campaigns/<int:campaign_id>', methods=['GET'])
@login_required
def campaign_detail(campaign_id):
    """View patron campaign details."""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    book = campaign.book_project
    
    from glconnect.book_campaign_patronage import ensure_campaign_goal_deadline_resolved
    ensure_campaign_goal_deadline_resolved(campaign, db)
    db.session.refresh(campaign)
    
    # Safety check: ensure book is a single object, not a collection
    if book is None:
        flash('Book project not found for this campaign.', 'error')
        return redirect(url_for('book_platform.campaigns'))
    
    investments = BookInvestment.query.filter_by(campaign_id=campaign_id).all()
    counted_investments = [
        inv for inv in investments if inv.status in _CONTRIBUTION_BACKER_STATUSES
    ]
    
    # Group investments by investor to show unique investors with totals
    from collections import defaultdict
    investor_totals = defaultdict(lambda: {'total_amount': 0.0, 'investments': [], 'first_investment_date': None, 'last_investment_date': None})
    
    for investment in counted_investments:
        investor_id = investment.investor_id
        investor_totals[investor_id]['total_amount'] += investment.amount
        investor_totals[investor_id]['investments'].append(investment)
        if investment.invested_at:
            if investor_totals[investor_id]['first_investment_date'] is None or investment.invested_at < investor_totals[investor_id]['first_investment_date']:
                investor_totals[investor_id]['first_investment_date'] = investment.invested_at
            if investor_totals[investor_id]['last_investment_date'] is None or investment.invested_at > investor_totals[investor_id]['last_investment_date']:
                investor_totals[investor_id]['last_investment_date'] = investment.invested_at
    
    # Convert to list of investor summaries with investor info
    investor_summaries = []
    for investor_id, data in investor_totals.items():
        # Get investor info from first investment
        first_investment = data['investments'][0]
        investor = first_investment.investor
        investor_summaries.append({
            'investor_id': investor_id,
            'investor': investor,
            'total_amount': data['total_amount'],
            'investment_count': len(data['investments']),
            'first_investment_date': data['first_investment_date'],
            'last_investment_date': data['last_investment_date'],
            'investments': data['investments']  # Keep individual investments for detailed view if needed
        })
    
    # Sort by total amount descending
    investor_summaries.sort(key=lambda x: x['total_amount'], reverse=True)
    unique_investor_count = len(investor_summaries)
    
    # Calculate progress
    progress_percentage = (campaign.current_funding / campaign.funding_goal * 100) if campaign.funding_goal > 0 else 0
    
    # Get author information
    author = book.author if book else None
    
    accredited_reviews = []
    avg_rating = 0
    
    # Get book chapters count and completed chapters
    chapters_count = 0
    completed_chapters = []
    completed_chapters_count = 0
    if book and hasattr(book, 'chapters') and book.chapters:
        chapters_count = len(book.chapters)
        completed_chapters = [ch for ch in book.chapters if ch.content and hasattr(ch, 'id')]
        completed_chapters_count = len(completed_chapters)
    
    # Calculate days remaining until the 2-year goal deadline
    from glconnect.book_campaign_patronage import (
        campaign_days_until_goal_deadline,
        campaign_goal_deadline,
        campaign_open_for_contributions,
        campaign_period_ended,
        campaign_goal_reached,
    )
    goal_deadline = campaign_goal_deadline(campaign)
    days_remaining = campaign_days_until_goal_deadline(campaign)
    
    # Get author's other books (for track record)
    author_other_books = []
    if author:
        author_other_books = BookProject.query.filter_by(
            author_id=author.id
        ).filter(BookProject.id != book.id).limit(5).all()
    
    # Check if current user is the author (to conditionally show/hide Invest Now button)
    is_author = False
    if current_user.is_authenticated and book:
        user_profile, profile_type = get_user_profile()
        if user_profile and hasattr(book, 'author_id'):
            current_user_id = get_profile_id(user_profile, profile_type)
            if current_user_id:
                is_author = (book.author_id == current_user_id)

    accepts_contributions, contribution_block_reason = campaign_open_for_contributions(campaign, book)
    period_ended = campaign_period_ended(campaign)
    goal_reached = campaign_goal_reached(campaign)

    share_url = url_for('book_platform.campaign_detail', campaign_id=campaign_id, _external=True)
    pitch_plain = ''
    if campaign.description:
        import re
        pitch_plain = re.sub(r'<[^>]+>', '', campaign.description)[:160].strip()

    campaign_is_saved = False
    if current_user.is_authenticated and not is_author:
        campaign_is_saved = campaign_id in saved_campaign_ids_for_user(current_user.user_id)

    from glconnect.campaign_translation_service import campaign_translation_context
    translation_ctx = campaign_translation_context(book)

    preview_mode = request.args.get('preview') in ('1', 'true', 'yes')
    if preview_mode and not is_author:
        preview_mode = False
    
    return render_template('book_platform/campaign_details.html', 
                         campaign=campaign,
                         book=book,
                         investments=investments,  # Keep for backward compatibility
                         investor_summaries=investor_summaries,  # New grouped data
                         unique_investor_count=unique_investor_count,  # Count of unique investors
                         progress_percentage=progress_percentage,
                         author=author,
                         accredited_reviews=accredited_reviews,
                         avg_rating=avg_rating,
                         chapters_count=chapters_count,
                         completed_chapters=completed_chapters[:3],  # First 3 for preview
                         completed_chapters_count=completed_chapters_count,
                         days_remaining=days_remaining,
                         goal_deadline=goal_deadline,
                         author_other_books=author_other_books,
                         is_author=is_author,
                         accepts_contributions=accepts_contributions,
                         contribution_block_reason=contribution_block_reason,
                         period_ended=period_ended,
                         goal_reached=goal_reached,
                         share_url=share_url,
                         pitch_plain=pitch_plain,
                         campaign_is_saved=campaign_is_saved,
                         preview_mode=preview_mode,
                         ink_nav_active='campaigns',
                         **translation_ctx)

# Patron contribution checkout (legacy POST /investments/<id>/invest still accepted)
@book_bp.route('/campaigns/<int:campaign_id>/contribute', methods=['GET', 'POST'])
@book_bp.route('/investments/<int:campaign_id>/invest', methods=['POST'])
@login_required
def contribute_to_campaign(campaign_id):
    """Patron contributes to a book campaign."""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    
    book = campaign.book_project

    from glconnect.campaign_translation_service import campaign_translation_context
    from glconnect.book_campaign_patronage import (
        PATRON_GIFT_PAYMENT_MIN_USD,
        campaign_open_for_contributions,
        ensure_campaign_goal_deadline_resolved,
    )
    contribute_template_kwargs = {
        'campaign': campaign,
        'book': book,
        'ink_nav_active': 'campaigns',
        'patron_gift_payment_min': PATRON_GIFT_PAYMENT_MIN_USD,
        **campaign_translation_context(book),
    }
    ensure_campaign_goal_deadline_resolved(campaign, db)
    db.session.refresh(campaign)
    logger.info(f"Make investment attempt - User: {current_user.user_id}, Campaign: {campaign_id}, Status: {campaign.status.value}, Book Status: {book.status.value if book else 'None'}")
    can_contribute, block_reason = campaign_open_for_contributions(campaign, book)
    if not can_contribute:
        logger.warning(f"Investment blocked - Campaign {campaign_id}: {block_reason}")
        flash(block_reason, 'error')
        return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))
    
    # All signed-in accounts can contribute (authors included — except to their own campaign).
    from glconnect.patron_support_service import ensure_patron_book_platform_user

    investor_user_id = current_user.user_id
    
    # Prevent self-investment: Check if current user is the author
    # This check uses user_id to ensure authors cannot invest in their own books
    if book and book.author:
        # Check both user_id and author_id to be thorough
        if book.author.user_id == investor_user_id:
            logger.warning(f"Investment blocked - User {investor_user_id} is the author of book {book.id}")
            flash('You cannot contribute to your own book campaign.', 'error')
            return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))
    
    from glconnect.patron_support_service import ensure_patron_book_platform_user

    try:
        bp_user = ensure_patron_book_platform_user(investor_user_id, db)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create patron profile for investor: {str(e)}", exc_info=True)
        flash('Failed to set up your supporter profile. Please try again.', 'error')
        return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))

    investor_id = bp_user.id
    
    # Double-check: Prevent investing in own book using investor_id
    if book and book.author_id == investor_id:
        logger.warning(f"Investment blocked - Investor {investor_id} is the author_id of book {book.id}")
        flash('You cannot contribute to your own book campaign.', 'error')
        return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))
    
    # Handle both JSON (AJAX) and form submissions (like book purchase)
    form = InvestmentForm()
    request_data = request.get_json() if request.is_json else None
    amount = None
    
    from glconnect.book_campaign_patronage import validate_patron_gift_amount

    if request_data:
        # JSON request (AJAX) - same pattern as book purchase
        try:
            amount = float(request_data.get('amount', 0))
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid contribution amount'}), 400
    else:
        # Form submission - use form validation
        form = InvestmentForm()
        if not form.validate_on_submit():
            return render_template('book_platform/contribute.html', form=form, **contribute_template_kwargs)
        amount = form.amount.data

    ok_amount, amount_error = validate_patron_gift_amount(amount)
    if not ok_amount:
        if request_data:
            return jsonify({'error': amount_error}), 400
        flash(amount_error, 'error')
        return render_template('book_platform/contribute.html', form=form, **contribute_template_kwargs)
    
    try:
        from glconnect.book_campaign_patronage import (
            is_book_campaign_patronage_mode,
            patronage_campaign_terms,
            apply_patronage_terms_to_investment,
        )
        patronage = is_book_campaign_patronage_mode()
        patronage_terms = patronage_campaign_terms() if patronage else {}
        # Calculate investment percentage
        investment_percentage = (amount / campaign.funding_goal) * 100
        
        # Create investment record in pending state; actual confirmation happens via Stripe webhook
        investment = BookInvestment(
            campaign_id=campaign_id,
            investor_id=investor_id,
            book_project_id=campaign.book_project_id,
            amount=amount,
            currency='USD',
            investment_percentage=investment_percentage,
            revenue_share_percentage=patronage_terms.get(
                "revenue_share_percentage", campaign.revenue_share_percentage
            ),
            return_multiplier=patronage_terms.get(
                "return_multiplier_cap", campaign.return_multiplier_cap
            ),
            status=InvestmentStatus.PENDING,
            payment_status=TransactionStatus.PENDING
        )
        if patronage:
            apply_patronage_terms_to_investment(investment)
        
        db.session.add(investment)
        db.session.flush()
        logger.info(f"Prepared patron contribution {investment.id} for campaign {campaign_id}, amount: ${amount}")

        # Create Stripe Checkout Session (same pattern as book purchase)
        domain_url = current_app.config.get("FRONTEND_BASE_URL") or request.url_root.rstrip("/")
        success_url = f"{domain_url}{url_for('book_platform.campaign_detail', campaign_id=campaign_id)}?payment=success"
        cancel_url = f"{domain_url}{url_for('book_platform.campaign_detail', campaign_id=campaign_id)}?payment=cancelled"
        
        stripe_checkout_url = None
        stripe_exc = None
        try:
            import stripe
            stripe_api_key = get_stripe_server_secret_key(current_app)
            logger.info(f"Patron contribution Stripe key check: stripe_api_key exists = {bool(stripe_api_key)}")
            if stripe_api_key:
                stripe.api_key = stripe_api_key
                logger.info(f"Creating Stripe checkout session for contribution {investment.id}, amount: ${amount}")
                _investor_email = checkout_customer_email_for_user(current_user)
                _inv_kw = dict(
                    mode="payment",
                    payment_method_types=checkout_payment_method_types_for_currency("USD"),
                    line_items=[
                        {
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": int(amount * 100),
                                "product_data": {
                                    "name": f"Patron gift — '{book.title}'",
                                    "description": f"Book campaign #{campaign.id} on Ink Studio (patronage, not an investment)",
                                },
                            },
                            "quantity": 1,
                        }
                    ],
                    metadata={
                        "investment_id": str(investment.id),
                        "campaign_id": str(campaign.id),
                        "book_id": str(book.id),
                        "investor_id": str(investor_id),
                    },
                    success_url=success_url,
                    cancel_url=cancel_url,
                )
                if _investor_email:
                    _inv_kw["customer_email"] = _investor_email
                checkout_session = stripe.checkout.Session.create(**_inv_kw)
                stripe_checkout_url = checkout_session.url
                logger.info(f"Successfully created Stripe checkout session: {stripe_checkout_url}")
            else:
                stripe_exc = RuntimeError("Stripe API key not found in configuration")
                logger.warning(f"Stripe API key not found in config for contribution {investment.id}")
        except Exception as e:
            stripe_exc = e
            logger.error(f"Could not create Stripe Checkout Session for contribution {investment.id}: {e}", exc_info=True)

        if not stripe_checkout_url:
            db.session.rollback()
            if request_data:
                from glconnect.stripe_utils import purchase_checkout_unavailable_response
                return purchase_checkout_unavailable_response(current_app, stripe_exc)
            flash(
                'Payment could not be started. If you operate this site, check Stripe API key IP restrictions.',
                'error',
            )
            return redirect(url_for('book_platform.campaign_detail', campaign_id=campaign_id))

        db.session.commit()
        
        # Return JSON response (same pattern as book purchase)
        if request_data:
            response = {
                'success': True,
                'investment_id': investment.id,
                'status': 'pending',
                'message': 'Contribution recorded. Redirecting to payment...',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'stripe_checkout_url': stripe_checkout_url,
            }
            return jsonify(response)
        else:
            return redirect(stripe_checkout_url, code=303)
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error making investment: {str(e)}", exc_info=True)
        error_msg = f'An error occurred: {str(e)}'
        if request_data:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
    
    # Render form for GET requests or form validation errors
    form = InvestmentForm() if not request_data else None
    return render_template('book_platform/contribute.html', form=form, **contribute_template_kwargs)

# Earnings Dashboard
@book_bp.route('/earnings', methods=['GET'])
@login_required
def earnings_dashboard():
    """View earnings for reviewers, investors, and authors - refreshes all data from database on load"""
    # Import all needed models at the top to avoid UnboundLocalError
    from glconnect.book_platform_models import (
        BookSale, TransactionStatus, BookInvestment, BookPlatformUser,
        AccreditedReviewer, ReviewerEarning, InvestmentPayout, BookProject
    )
    
    user_profile, profile_type = get_user_profile()
    logger.info(f"Earnings dashboard - User {current_user.user_id}, profile_type: {profile_type}, user_profile: {user_profile}")
    
    # Process any pending revenue distributions before displaying earnings
    # This ensures the dashboard always shows the latest data
    try:
        from glconnect.revenue_distribution_service import distribute_revenue
        
        # Find all sales that haven't been distributed yet
        # Process in chronological order (oldest first) to ensure proper return cap calculations
        undistributed_sales = BookSale.query.filter_by(
            distribution_completed=False
        ).order_by(BookSale.created_at.asc()).all()  # Oldest first
        
        if undistributed_sales:
            logger.info(f"Found {len(undistributed_sales)} undistributed sales - processing in chronological order...")
            success_count = 0
            for sale in undistributed_sales:
                try:
                    # Refresh sale to get latest data
                    db.session.refresh(sale)
                    result = distribute_revenue(sale, db)
                    if result and result.get('success'):
                        success_count += 1
                        summary = result.get('summary', {})
                        logger.info(f"✅ Distributed revenue for sale {sale.id} (Book {sale.book_project_id}): {summary}")
                    else:
                        error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                        logger.warning(f"⚠️  Failed to distribute revenue for sale {sale.id}: {error_msg}")
                except Exception as e:
                    logger.error(f"❌ Error distributing revenue for sale {sale.id}: {e}", exc_info=True)
            
            # Commit all successful distributions
            if success_count > 0:
                db.session.commit()
                logger.info(f"✅ Committed {success_count} revenue distributions")
                
            else:
                db.session.rollback()
                logger.warning(f"⚠️  No distributions were successful, rolled back")
    except Exception as e:
        logger.error(f"Error processing pending distributions: {e}", exc_info=True)
        db.session.rollback()
    
    earnings_data = {
        'reviewer_earnings': [],
        'patron_contributions': [],
        'author_sales': [],
        'reviewer_earnings_by_book': {},
        'author_sales_by_book': {}
    }
    
    # Accredited reviewer earnings retired — no reviewer section on dashboard
    
    # Patron contributions (no sale-linked returns)
    book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if book_platform_user:
        investor_id = book_platform_user.id
        all_investments = BookInvestment.query.join(
            BookProject, BookInvestment.book_project_id == BookProject.id
        ).filter(
            BookInvestment.investor_id == investor_id,
            BookProject.author_id != investor_id,
        ).order_by(BookInvestment.invested_at.desc()).all()
        earnings_data['patron_contributions'] = [
            inv for inv in all_investments
            if inv.status.value in ('confirmed', 'active', 'pending')
        ]
        earnings_data['total_contributed'] = sum(inv.amount for inv in earnings_data['patron_contributions'])
    else:
        earnings_data['patron_contributions'] = []
        earnings_data['total_contributed'] = 0.0
    
    # Author sales - only for users who are authors
    # Try multiple methods to find the user's sales
    sales = []
    author_id = None
    
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        logger.info(f"Earnings dashboard - User {current_user.user_id}, author_id from get_profile_id: {author_id}")
        if author_id:
            # Get all sales for this author (including pending, as they represent potential earnings)
            sales = BookSale.query.filter_by(seller_id=author_id).order_by(
                BookSale.created_at.desc()
            ).limit(50).all()
            
            logger.info(f"Earnings dashboard - User {current_user.user_id}, author_id: {author_id}, found {len(sales)} sales")
            if len(sales) > 0:
                logger.info(f"   First sale: ID={sales[0].id}, net_amount=${sales[0].net_amount}, status={sales[0].status.value}")
        else:
            logger.warning(f"Earnings dashboard - Could not get author_id for user {current_user.user_id}, profile_type: {profile_type}")
    
    # Fallback: If no sales found via profile, try finding BookPlatformUser directly
    if not sales or len(sales) == 0:
        logger.info(f"Earnings dashboard - Trying fallback: Looking for BookPlatformUser for user_id={current_user.user_id}")
        bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if bp_user:
            author_id = bp_user.id
            sales = BookSale.query.filter_by(seller_id=author_id).order_by(
                BookSale.created_at.desc()
            ).limit(50).all()
            logger.info(f"Earnings dashboard - Fallback found {len(sales)} sales for BookPlatformUser.id={author_id}")
    
    # Process sales if found
    if sales and len(sales) > 0:
        # Refresh all sales to get latest data from database
        for sale in sales:
            db.session.refresh(sale)
        earnings_data['author_sales'] = sales
        completed_sales = [s for s in sales if s.status == TransactionStatus.COMPLETED]
        earnings_data['total_author_revenue'] = sum(sale.net_amount for sale in completed_sales)
        earnings_data['completed_author_revenue'] = sum(sale.net_amount for sale in completed_sales)
        earnings_data['pending_author_revenue'] = sum(sale.net_amount for sale in sales if sale.status != TransactionStatus.COMPLETED)
        # Author payout: available = total - paid out
        author_paid_out = sum(
            r.amount for r in AuthorSalesPayoutRequest.query.filter_by(
                author_id=author_id, status='PAID'
            ).all()
        )
        earnings_data['author_available_balance'] = max(0, earnings_data['total_author_revenue'] - author_paid_out)
        earnings_data['author_pending_payout_requests'] = AuthorSalesPayoutRequest.query.filter_by(
            author_id=author_id, status='PENDING'
        ).all()
        
        # Group sales by book (completed only for revenue totals)
        sales_by_book = defaultdict(lambda: {'sales': [], 'total': 0.0, 'completed_total': 0.0, 'pending_total': 0.0, 'book': None})
        for sale in sales:
            book_id = sale.book_project_id
            sales_by_book[book_id]['sales'].append(sale)
            if sale.status == TransactionStatus.COMPLETED:
                sales_by_book[book_id]['total'] += sale.net_amount
                sales_by_book[book_id]['completed_total'] += sale.net_amount
            else:
                sales_by_book[book_id]['pending_total'] += sale.net_amount
            if not sales_by_book[book_id]['book']:
                sales_by_book[book_id]['book'] = sale.book_project
        earnings_data['author_sales_by_book'] = dict(sales_by_book)
    else:
        earnings_data['author_sales'] = []
        earnings_data['total_author_revenue'] = 0.0
        earnings_data['completed_author_revenue'] = 0.0
        earnings_data['pending_author_revenue'] = 0.0
        earnings_data['author_sales_by_book'] = {}
        earnings_data['author_available_balance'] = 0.0
        earnings_data['author_pending_payout_requests'] = []
        logger.warning(f"Earnings dashboard - No sales found for user {current_user.user_id}")
        
        # Group sales by book
        sales_by_book = defaultdict(lambda: {'sales': [], 'total': 0.0, 'book': None})
        for sale in sales:
            book_id = sale.book_project_id
            sales_by_book[book_id]['sales'].append(sale)
            sales_by_book[book_id]['total'] += sale.net_amount
            if not sales_by_book[book_id]['book']:
                sales_by_book[book_id]['book'] = sale.book_project
        earnings_data['author_sales_by_book'] = dict(sales_by_book)

    bp_for_stripe = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    is_seller_profile = profile_type in ('writer', 'book_platform')
    aid_earn = get_profile_id(user_profile, profile_type) if user_profile else None
    has_author_books = bool(aid_earn and BookProject.query.filter_by(author_id=aid_earn).first())
    author_payout_setup_needed = bool(
        bp_for_stripe
        and author_needs_stripe_payout_setup(bp_for_stripe)
        and (is_seller_profile or has_author_books)
    )
    
    return render_template(
        'book_platform/earnings.html',
        earnings_data=earnings_data,
        payout_minimum=PAYOUT_MINIMUM_AMOUNT,
        author_payout_setup_needed=author_payout_setup_needed,
    )


# Minimum amount to request author sales payout (USD)
PAYOUT_MINIMUM_AMOUNT = 50.0


@book_bp.route('/earnings/request-payout', methods=['POST'])
@login_required
def request_payout():
    """Retired: patrons do not receive sale-linked returns."""
    return jsonify({
        'error': 'Campaign contributions do not include earnings from book sales.',
    }), 410


@book_bp.route('/earnings/request-reviewer-payout', methods=['POST'])
@login_required
def request_reviewer_payout():
    """Reviewer requests payout of available earnings (min $50, mirrors investor flow)"""
    return jsonify({
        'error': 'Accredited reviewer payouts are no longer available.',
    }), 410
    data = request.get_json() or {}
    amount = data.get('amount')
    
    if amount is None:
        return jsonify({'error': 'Missing amount'}), 400
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400
    
    if amount < PAYOUT_MINIMUM_AMOUNT:
        return jsonify({'error': f'Minimum payout amount is ${PAYOUT_MINIMUM_AMOUNT:.2f}'}), 400
    
    reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    if not reviewer:
        return jsonify({'error': 'Reviewer profile not found'}), 403
    
    available = sum(
        e.amount for e in ReviewerEarning.query.filter_by(
            reviewer_id=reviewer.id, status=TransactionStatus.PENDING
        ).all()
    )
    if amount > available:
        return jsonify({'error': f'Amount exceeds available balance (${available:.2f})'}), 400
    
    pending = ReviewerPayoutRequest.query.filter_by(
        reviewer_id=reviewer.id, status='PENDING'
    ).first()
    if pending:
        return jsonify({'error': 'You already have a pending payout request'}), 400
    
    req = ReviewerPayoutRequest(
        reviewer_id=reviewer.id,
        amount=amount,
        currency='USD',
        status='PENDING'
    )
    db.session.add(req)
    db.session.commit()
    
    logger.info(f"Reviewer payout request {req.id} created: reviewer={reviewer.id}, amount=${amount}")
    return jsonify({
        'success': True,
        'message': f'Payout request of ${amount:.2f} submitted. Admin will process it shortly.',
        'payout_request_id': req.id
    })


@book_bp.route('/earnings/request-author-sales-payout', methods=['POST'])
@login_required
def request_author_sales_payout():
    """Author requests payout of sales earnings (min $50, mirrors investor flow)"""
    data = request.get_json() or {}
    amount = data.get('amount')
    
    if amount is None:
        return jsonify({'error': 'Missing amount'}), 400
    
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount'}), 400
    
    if amount < PAYOUT_MINIMUM_AMOUNT:
        return jsonify({'error': f'Minimum payout amount is ${PAYOUT_MINIMUM_AMOUNT:.2f}'}), 400
    
    user_profile, profile_type = get_user_profile()
    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        return jsonify({'error': 'Author profile not found'}), 403
    
    # Available = total revenue - paid out
    author_paid_out = sum(
        r.amount for r in AuthorSalesPayoutRequest.query.filter_by(
            author_id=author_id, status='PAID'
        ).all()
    )
    total_revenue = sum(
        s.net_amount for s in BookSale.query.filter_by(seller_id=author_id).all()
    )
    available = max(0, total_revenue - author_paid_out)
    
    if amount > available:
        return jsonify({'error': f'Amount exceeds available balance (${available:.2f})'}), 400
    
    pending = AuthorSalesPayoutRequest.query.filter_by(
        author_id=author_id, status='PENDING'
    ).first()
    if pending:
        return jsonify({'error': 'You already have a pending payout request'}), 400
    
    req = AuthorSalesPayoutRequest(
        author_id=author_id,
        amount=amount,
        currency='USD',
        status='PENDING'
    )
    db.session.add(req)
    db.session.commit()
    
    logger.info(f"Author sales payout request {req.id} created: author={author_id}, amount=${amount}")
    return jsonify({
        'success': True,
        'message': f'Payout request of ${amount:.2f} submitted. Admin will process it shortly.',
        'payout_request_id': req.id
    })


@book_bp.route('/admin/payout-requests')
@login_required
def admin_payout_requests():
    """Retired funder-return payouts; redirect to author sales payouts."""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    flash('Funder return payouts are retired. Use Author sales payouts instead.', 'info')
    return redirect(url_for('book_platform.admin_author_sales_payout_requests'))


@book_bp.route('/admin/payout-requests/<int:request_id>/mark-paid', methods=['POST'])
@login_required
def admin_mark_payout_paid(request_id):
    """Retired funder-return payouts."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    flash('Funder return payouts are retired.', 'info')
    return redirect(url_for('book_platform.admin_author_sales_payout_requests'))


@book_bp.route('/admin/payout-requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def admin_cancel_payout_request(request_id):
    """Retired funder-return payouts."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    flash('Funder return payouts are retired.', 'info')
    return redirect(url_for('book_platform.admin_author_sales_payout_requests'))


# Author Campaign Fund Release (50% first draft, 50% publication - investor safeguard)
@book_bp.route('/admin/author-payout-requests')
@login_required
def admin_author_payout_requests():
    """Admin view of author campaign fund release requests"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    pending = AuthorCampaignPayoutRequest.query.filter_by(status='pending').order_by(
        AuthorCampaignPayoutRequest.requested_at.asc()
    ).all()
    approved = AuthorCampaignPayoutRequest.query.filter(
        AuthorCampaignPayoutRequest.status.in_(['approved', 'paid'])
    ).order_by(AuthorCampaignPayoutRequest.approved_at.desc()).limit(50).all()
    
    return render_template('book_platform/admin_author_payout_requests.html',
        pending=pending, approved=approved
    )


@book_bp.route('/admin/author-payout-requests/<int:request_id>/approve', methods=['POST'])
@login_required
def admin_approve_author_payout(request_id):
    """Admin approves author campaign fund release - marks as paid (manual bank transfer)"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    req = AuthorCampaignPayoutRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_author_payout_requests'))
    
    campaign = req.campaign
    book = campaign.book_project
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    req.status = 'paid'
    req.approved_at = datetime.now(timezone.utc)
    req.approved_by_id = bp_user.id if bp_user else None
    req.paid_at = datetime.now(timezone.utc)
    req.admin_notes = (request.form.get('admin_notes') or request.get_json(silent=True) or {}).get('admin_notes', '')
    
    if req.milestone == 'first_draft':
        campaign.author_first_draft_released = True
        campaign.author_first_draft_released_at = datetime.now(timezone.utc)
        campaign.author_first_draft_amount = req.amount
    else:
        campaign.author_publication_released = True
        campaign.author_publication_released_at = datetime.now(timezone.utc)
        campaign.author_publication_amount = req.amount
    
    db.session.commit()
    
    logger.info(f"Author payout request {req.id} approved: campaign={campaign.id}, milestone={req.milestone}, amount=${req.amount:.2f}")
    flash(f'Author fund release of ${req.amount:.2f} ({req.milestone}) marked as paid. Process bank transfer to author.', 'success')
    return redirect(url_for('book_platform.admin_author_payout_requests'))


@book_bp.route('/admin/author-payout-requests/<int:request_id>/reject', methods=['POST'])
@login_required
def admin_reject_author_payout(request_id):
    """Admin rejects author campaign fund release"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    req = AuthorCampaignPayoutRequest.query.get_or_404(request_id)
    if req.status != 'pending':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_author_payout_requests'))
    
    req.status = 'rejected'
    req.rejection_reason = request.form.get('rejection_reason') or (request.get_json(silent=True) or {}).get('rejection_reason', '')
    req.approved_at = datetime.now(timezone.utc)
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    req.approved_by_id = bp_user.id if bp_user else None
    
    db.session.commit()
    
    flash('Author payout request rejected.', 'info')
    return redirect(url_for('book_platform.admin_author_payout_requests'))


# Reviewer Payout Requests (min $50, admin approval)
@book_bp.route('/admin/reviewer-payout-requests')
@login_required
def admin_reviewer_payout_requests():
    """Admin view of reviewer payout requests"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    flash('Reviewer payouts are retired. Process any legacy requests outside the app if needed.', 'info')
    return redirect(url_for('book_platform.admin_books'))
    
    pending = ReviewerPayoutRequest.query.filter_by(status='PENDING').options(
        joinedload(ReviewerPayoutRequest.reviewer).joinedload(AccreditedReviewer.user)
    ).order_by(ReviewerPayoutRequest.requested_at.asc()).all()
    
    paid = ReviewerPayoutRequest.query.filter_by(status='PAID').options(
        joinedload(ReviewerPayoutRequest.reviewer).joinedload(AccreditedReviewer.user)
    ).order_by(ReviewerPayoutRequest.paid_at.desc()).limit(50).all()
    
    return render_template('book_platform/admin_reviewer_payout_requests.html',
        pending=pending, paid=paid
    )


@book_bp.route('/admin/reviewer-payout-requests/<int:request_id>/mark-paid', methods=['POST'])
@login_required
def admin_mark_reviewer_payout_paid(request_id):
    """Admin marks reviewer payout as paid - marks underlying ReviewerEarnings as COMPLETED"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.admin_reviewer_payout_requests'))
    
    req = ReviewerPayoutRequest.query.get_or_404(request_id)
    if req.status != 'PENDING':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_reviewer_payout_requests'))
    
    reviewer = req.reviewer
    available = sum(
        e.amount for e in ReviewerEarning.query.filter_by(
            reviewer_id=reviewer.id, status=TransactionStatus.PENDING
        ).all()
    )
    if req.amount > available:
        flash(f'Amount (${req.amount:.2f}) exceeds available (${available:.2f}).', 'error')
        return redirect(url_for('book_platform.admin_reviewer_payout_requests'))
    
    # Mark oldest PENDING earnings as COMPLETED until we've covered the amount
    remaining = req.amount
    earnings = ReviewerEarning.query.filter_by(
        reviewer_id=reviewer.id, status=TransactionStatus.PENDING
    ).order_by(ReviewerEarning.created_at.asc()).all()
    
    for earning in earnings:
        if remaining <= 0:
            break
        earning.status = TransactionStatus.COMPLETED
        earning.paid_at = datetime.now(timezone.utc)
        remaining -= earning.amount
    # Note: may overpay slightly if last earning exceeds remaining (no partial payouts)
    
    req.status = 'PAID'
    req.paid_at = datetime.now(timezone.utc)
    req.admin_notes = (request.form.get('admin_notes') or (request.get_json(silent=True) or {}).get('admin_notes', ''))
    
    db.session.commit()
    
    logger.info(f"Reviewer payout request {req.id} marked paid: reviewer={reviewer.id}, amount=${req.amount:.2f}")
    flash(f'Reviewer payout of ${req.amount:.2f} marked as paid.', 'success')
    return redirect(url_for('book_platform.admin_reviewer_payout_requests'))


@book_bp.route('/admin/reviewer-payout-requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def admin_cancel_reviewer_payout_request(request_id):
    """Admin cancels reviewer payout request"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.admin_reviewer_payout_requests'))
    
    req = ReviewerPayoutRequest.query.get_or_404(request_id)
    if req.status != 'PENDING':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_reviewer_payout_requests'))
    
    req.status = 'CANCELLED'
    db.session.commit()
    
    flash('Reviewer payout request cancelled.', 'info')
    return redirect(url_for('book_platform.admin_reviewer_payout_requests'))


# Author Sales Payout Requests (earnings from book sales - min $50)
@book_bp.route('/admin/author-sales-payout-requests')
@login_required
def admin_author_sales_payout_requests():
    """Admin view of author sales payout requests"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    pending = AuthorSalesPayoutRequest.query.filter_by(status='PENDING').options(
        joinedload(AuthorSalesPayoutRequest.author).joinedload(BookPlatformUser.user)
    ).order_by(AuthorSalesPayoutRequest.requested_at.asc()).all()
    
    paid = AuthorSalesPayoutRequest.query.filter_by(status='PAID').options(
        joinedload(AuthorSalesPayoutRequest.author).joinedload(BookPlatformUser.user)
    ).order_by(AuthorSalesPayoutRequest.paid_at.desc()).limit(50).all()
    
    return render_template('book_platform/admin_author_sales_payout_requests.html',
        pending=pending, paid=paid
    )


@book_bp.route('/admin/author-sales-payout-requests/<int:request_id>/mark-paid', methods=['POST'])
@login_required
def admin_mark_author_sales_payout_paid(request_id):
    """Admin marks author sales payout as paid"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.admin_author_sales_payout_requests'))
    
    req = AuthorSalesPayoutRequest.query.get_or_404(request_id)
    if req.status != 'PENDING':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_author_sales_payout_requests'))
    
    req.status = 'PAID'
    req.paid_at = datetime.now(timezone.utc)
    req.admin_notes = (request.form.get('admin_notes') or (request.get_json(silent=True) or {}).get('admin_notes', ''))
    
    db.session.commit()
    
    logger.info(f"Author sales payout request {req.id} marked paid: author={req.author_id}, amount=${req.amount:.2f}")
    flash(f'Author sales payout of ${req.amount:.2f} marked as paid.', 'success')
    return redirect(url_for('book_platform.admin_author_sales_payout_requests'))


@book_bp.route('/admin/author-sales-payout-requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def admin_cancel_author_sales_payout_request(request_id):
    """Admin cancels author sales payout request"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.admin_author_sales_payout_requests'))
    
    req = AuthorSalesPayoutRequest.query.get_or_404(request_id)
    if req.status != 'PENDING':
        flash('Request is not pending.', 'error')
        return redirect(url_for('book_platform.admin_author_sales_payout_requests'))
    
    req.status = 'CANCELLED'
    db.session.commit()
    
    flash('Author sales payout request cancelled.', 'info')
    return redirect(url_for('book_platform.admin_author_sales_payout_requests'))


# Book Sales Transparency Page
@book_bp.route('/books/<int:book_id>/sales-transparency', methods=['GET'])
@login_required
def book_sales_transparency(book_id):
    """Transparent view of all sales and revenue distributions for a book"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user has access (author, reviewer, or investor)
    user_profile, profile_type = get_user_profile()
    has_access = False
    user_role = None
    
    # Check if author
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        if book.author_id == author_id:
            has_access = True
            user_role = 'author'
    
    # Check if reviewer
    reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    if reviewer:
        review = BookReview.query.filter_by(
            book_project_id=book_id,
            reviewer_id=reviewer.id
        ).first()
        if review:
            has_access = True
            user_role = 'reviewer'
    
    # Check if investor
    if user_profile:
        investor_id = get_profile_id(user_profile, profile_type)
        investment = BookInvestment.query.filter_by(
            book_project_id=book_id,
            investor_id=investor_id
        ).first()
        if investment:
            has_access = True
            user_role = 'patron'
    
    if not has_access:
        flash('You do not have access to view sales data for this book.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    
    # Get all sales with distributions
    sales = BookSale.query.filter_by(
        book_project_id=book_id
    ).order_by(BookSale.created_at.desc()).all()
    
    # Get distributions for each sale
    sales_data = []
    for sale in sales:
        distributions = RevenueDistribution.query.filter_by(
            source_sale_id=sale.id
        ).all()
        
        sale_info = {
            'sale': sale,
            'distributions': distributions,
            'total_sale_amount': sale.net_amount + sale.platform_fee,
            'platform': next((d for d in distributions if d.distribution_type == DistributionType.PLATFORM), None),
            'reviewers': [d for d in distributions if d.distribution_type == DistributionType.REVIEWER],
            'investors': [d for d in distributions if d.distribution_type == DistributionType.INVESTOR],
            'author': next((d for d in distributions if d.distribution_type == DistributionType.AUTHOR), None)
        }
        sales_data.append(sale_info)
    
    # Calculate totals
    total_sales = len(sales)
    total_revenue = sum(s.net_amount + s.platform_fee for s in sales)
    total_platform = sum(s.platform_fee for s in sales)
    total_reviewers = sum(s.distributed_to_reviewers for s in sales)
    total_investors = sum(s.distributed_to_investors for s in sales)
    total_author = total_revenue - total_platform - total_reviewers - total_investors
    
    # Get user-specific earnings
    user_earnings = {
        'total': 0.0,
        'per_sale': []
    }
    
    if user_role == 'reviewer' and reviewer:
        review = BookReview.query.filter_by(
            book_project_id=book_id,
            reviewer_id=reviewer.id
        ).first()
        if review:
            earnings = ReviewerEarning.query.filter_by(
                reviewer_id=reviewer.id,
                review_id=review.id
            ).order_by(ReviewerEarning.created_at.desc()).all()
            user_earnings['total'] = sum(e.amount for e in earnings)
            user_earnings['per_sale'] = earnings
    
    elif user_role == 'patron' and user_profile:
        investor_id = get_profile_id(user_profile, profile_type)
        investment = BookInvestment.query.filter_by(
            book_project_id=book_id,
            investor_id=investor_id
        ).first()
        if investment:
            user_earnings['total'] = investment.amount
            user_earnings['per_sale'] = []

    elif user_role == 'author':
        user_earnings['total'] = total_author
        user_earnings['per_sale'] = [s['author'] for s in sales_data if s['author']]
    
    return render_template('book_platform/sales_transparency.html',
                         book=book,
                         sales_data=sales_data,
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         total_platform=total_platform,
                         total_reviewers=total_reviewers,
                         total_investors=total_investors,
                         total_author=total_author,
                         user_role=user_role,
                         user_earnings=user_earnings)

# Reviewer Earnings by Book
# Reconciliation endpoint to manually trigger revenue distribution
@book_bp.route('/admin/reconcile-sales', methods=['POST'])
@login_required
def reconcile_sales():
    """Manually trigger revenue distribution for sales that weren't distributed"""
    # Check if user is admin (you may want to add proper admin check)
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from glconnect.book_platform_models import BookSale
        from glconnect.revenue_distribution_service import distribute_revenue
        
        # Find all sales that haven't been distributed
        undistributed_sales = BookSale.query.filter_by(distribution_completed=False).all()
        
        results = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for sale in undistributed_sales:
            results['processed'] += 1
            try:
                result = distribute_revenue(sale, db)
                if result and result.get('success'):
                    results['success'] += 1
                    logger.info(f"✅ Reconciled sale {sale.id}: {result}")
                else:
                    results['failed'] += 1
                    error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                    results['errors'].append(f"Sale {sale.id}: {error_msg}")
                    logger.error(f"❌ Failed to reconcile sale {sale.id}: {error_msg}")
            except Exception as e:
                results['failed'] += 1
                error_msg = str(e)
                results['errors'].append(f"Sale {sale.id}: {error_msg}")
                logger.error(f"❌ Error reconciling sale {sale.id}: {error_msg}", exc_info=True)
        
        return jsonify({
            'success': True,
            'message': f"Processed {results['processed']} sales. {results['success']} succeeded, {results['failed']} failed.",
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in reconcile_sales: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@book_bp.route('/reviewers/my-earnings/<int:book_id>', methods=['GET'])
@login_required
def reviewer_earnings_by_book(book_id):
    """Reviewer view of their earnings for a specific book"""
    _accredited_book_reviews_disabled_flash()
    return redirect(url_for('book_platform.earnings_dashboard'))
    book = BookProject.query.get_or_404(book_id)
    reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    
    if not reviewer:
        flash('You must be an accredited reviewer to view this page.', 'error')
        return redirect(url_for('book_platform.register_reviewer'))
    
    review = BookReview.query.filter_by(
        book_project_id=book_id,
        reviewer_id=reviewer.id
    ).first_or_404()
    
    # Get all earnings for this review
    earnings = ReviewerEarning.query.filter_by(
        reviewer_id=reviewer.id,
        review_id=review.id
    ).order_by(ReviewerEarning.created_at.desc()).all()
    
    # Get sales data
    sales = BookSale.query.filter_by(
        book_project_id=book_id
    ).order_by(BookSale.created_at.desc()).all()
    
    # Match earnings to sales
    earnings_by_sale = {}
    for earning in earnings:
        if earning.distribution:
            sale_id = earning.distribution.source_sale_id
            earnings_by_sale[sale_id] = earning
    
    return render_template('book_platform/reviewer_earnings_book.html',
                         book=book,
                         review=review,
                         earnings=earnings,
                         sales=sales,
                         earnings_by_sale=earnings_by_sale,
                         total_earnings=sum(e.amount for e in earnings))

# Retired: sale-linked funder returns (legacy /investments/my-returns → 301 redirect above)
@book_bp.route('/campaigns/my-returns/<int:book_id>', methods=['GET'])
@login_required
def investor_returns_by_book(book_id):
    """Redirect legacy returns URL to campaign discovery."""
    flash('Contributions do not include financial returns from book sales.', 'info')
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if bp_user:
        investment = BookInvestment.query.filter_by(
            book_project_id=book_id, investor_id=bp_user.id
        ).first()
        if investment and investment.campaign_id:
            return redirect(url_for('book_platform.campaign_detail', campaign_id=investment.campaign_id))
    return redirect(url_for('book_platform.campaigns'))

# Accountability & Refund Routes
@book_bp.route('/books/<int:book_id>/accountability', methods=['GET'])
@login_required
def book_accountability_status(book_id):
    """View accountability status for a book"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user is author
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to view this page.', 'error')
        return redirect(url_for('book_platform.setup_profile'))
    
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        flash('Only the author can view accountability status.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Get accountability status
    from glconnect.accountability_service import get_accountability_status, can_request_first_draft_release, can_request_publication_release, FIRST_DRAFT_MIN_WORDS
    status_result = get_accountability_status(book_id, db)
    
    if not status_result.get('success'):
        flash('Error loading accountability status.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Campaign fund release status (50% first draft, 50% publication - safeguard for investors)
    campaign = book.investment_campaign
    fund_release = {}
    if campaign and campaign.status == CampaignStatus.FUNDED:
        from glconnect.platform_fee_policy import campaign_fee_summary, campaign_milestone_release_amount
        ensure_campaign_fee_terms(campaign, db)
        fee_info = campaign_fee_summary(campaign, db)
        can_first, msg_first = can_request_first_draft_release(book, campaign, db)
        can_pub, msg_pub = can_request_publication_release(book, campaign, db)
        first_amount = campaign_milestone_release_amount(campaign, db) if not campaign.author_first_draft_released else 0
        pub_amount = campaign_milestone_release_amount(campaign, db) if campaign.author_first_draft_released and not campaign.author_publication_released else 0
        fund_release = {
            'total_funding': campaign.current_funding,
            'author_net_funding': fee_info['author_net_funding'],
            'platform_fee_percent': fee_info['platform_fee_percent'],
            'platform_fee_amount': fee_info['platform_fee_amount'],
            'is_first_author_project': fee_info['is_first_author_project'],
            'first_draft_released': campaign.author_first_draft_released,
            'first_draft_amount': campaign.author_first_draft_amount,
            'publication_released': campaign.author_publication_released,
            'publication_amount': campaign.author_publication_amount,
            'can_request_first_draft': can_first,
            'first_draft_message': msg_first,
            'can_request_publication': can_pub,
            'publication_message': msg_pub,
            'first_draft_amount_pending': first_amount,
            'publication_amount_pending': pub_amount,
            'first_draft_min_words': FIRST_DRAFT_MIN_WORDS
        }
    
    return render_template('book_platform/accountability_status.html',
                         book=book,
                         status=status_result.get('status'),
                         fund_release=fund_release)

@book_bp.route('/books/<int:book_id>/campaign/request-fund-release', methods=['POST'])
@login_required
def request_campaign_fund_release(book_id):
    """Author requests release of campaign funds (first draft 50% or publication 50%)"""
    book = BookProject.query.get_or_404(book_id)
    campaign = book.investment_campaign
    
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to request fund release.', 'error')
        return redirect(url_for('book_platform.setup_profile'))
    author_id = get_profile_id(user_profile, profile_type)
    if book.author_id != author_id:
        flash('Only the author can request campaign fund release.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    if not campaign or campaign.status != CampaignStatus.FUNDED:
        flash('No funded campaign for this book.', 'error')
        return redirect(url_for('book_platform.book_accountability_status', book_id=book_id))
    
    milestone = request.form.get('milestone')
    if not milestone and request.is_json:
        milestone = (request.get_json(silent=True) or {}).get('milestone')
    if milestone not in ('first_draft', 'publication'):
        flash('Invalid milestone.', 'error')
        return redirect(url_for('book_platform.book_accountability_status', book_id=book_id))
    
    from glconnect.accountability_service import can_request_first_draft_release, can_request_publication_release, FIRST_DRAFT_RELEASE_PERCENT, PUBLICATION_RELEASE_PERCENT
    from glconnect.platform_fee_policy import campaign_milestone_release_amount, ensure_campaign_fee_terms
    from glconnect.book_platform_models import AuthorCampaignPayoutRequest
    
    ensure_campaign_fee_terms(campaign, db)
    
    if milestone == 'first_draft':
        can_req, msg = can_request_first_draft_release(book, campaign, db)
        amount = campaign_milestone_release_amount(campaign, db, milestone_percent=FIRST_DRAFT_RELEASE_PERCENT)
    else:
        can_req, msg = can_request_publication_release(book, campaign, db)
        amount = campaign_milestone_release_amount(campaign, db, milestone_percent=PUBLICATION_RELEASE_PERCENT)
    
    if not can_req:
        flash(msg or 'Cannot request this release.', 'error')
        return redirect(url_for('book_platform.book_accountability_status', book_id=book_id))
    
    req = AuthorCampaignPayoutRequest(
        campaign_id=campaign.id,
        milestone=milestone,
        amount=amount,
        currency=campaign.book_project.currency or 'USD',
        status='pending'
    )
    db.session.add(req)
    db.session.commit()
    
    flash(f'Request for ${amount:.2f} ({milestone.replace("_", " ")} release) submitted. Admin will review shortly.', 'success')
    return redirect(url_for('book_platform.book_accountability_status', book_id=book_id))


# Patron contribution refund request (only before first draft is out)
@book_bp.route('/contributions/<int:contribution_id>/request-refund', methods=['POST'])
@book_bp.route('/investments/<int:contribution_id>/request-refund', methods=['POST'])
@login_required
def request_contribution_refund(contribution_id):
    """Patron requests refund — only allowed before first draft is completed (25k+ words)."""
    from glconnect.book_platform_models import BookInvestment, RefundRequest, TransactionStatus
    from glconnect.accountability_service import FIRST_DRAFT_MIN_WORDS
    
    investment = BookInvestment.query.options(
        joinedload(BookInvestment.book_project),
        joinedload(BookInvestment.campaign)
    ).get_or_404(contribution_id)
    
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        return jsonify({'error': 'Profile required'}), 403
    
    investor_id = get_profile_id(user_profile, profile_type)
    if investment.investor_id != investor_id:
        return jsonify({'error': 'Not your contribution'}), 403
    
    if investment.status == InvestmentStatus.REFUNDED:
        return jsonify({'error': 'Contribution already refunded'}), 400
    
    # Check for existing pending refund
    pending = RefundRequest.query.filter_by(
        investment_id=contribution_id,
        status=TransactionStatus.PENDING
    ).first()
    if pending:
        return jsonify({'error': 'Refund request already pending'}), 400
    
    book = investment.book_project
    campaign = investment.campaign
    if not campaign or campaign.status != CampaignStatus.FUNDED:
        return jsonify({'error': 'No funded campaign'}), 400
    
    # First draft = 25k+ words - refund only allowed before that
    try:
        update_book_word_count(book)
    except Exception:
        pass
    word_count = book.word_count or 0
    if word_count >= FIRST_DRAFT_MIN_WORDS:
        return jsonify({'error': f'First draft is complete ({word_count:,} words). Refunds only available before first draft.'}), 400
    
    refund = RefundRequest(
        investment_id=contribution_id,
        amount=investment.amount,
        currency=investment.currency or 'USD',
        reason='Patron requested refund (before first draft)',
        status=TransactionStatus.PENDING
    )
    db.session.add(refund)
    db.session.commit()
    
    logger.info(f"Patron refund request {refund.id} for contribution {contribution_id}")
    if request.is_json or request.content_type == 'application/json':
        return jsonify({
            'success': True,
            'message': f'Refund request of ${investment.amount:.2f} submitted. Admin will process it shortly.'
        })
    flash(f'Refund request of ${investment.amount:.2f} submitted. Admin will process it shortly.', 'success')
    return redirect(url_for('book_platform.contribution_refund_status', contribution_id=contribution_id))


@book_bp.route('/contributions/<int:contribution_id>/refund-status', methods=['GET'])
@login_required
def contribution_refund_status(contribution_id):
    """View refund status for a patron contribution."""
    from glconnect.book_platform_models import BookInvestment, RefundRequest
    
    investment = BookInvestment.query.options(
        joinedload(BookInvestment.book_project),
        joinedload(BookInvestment.campaign)
    ).get_or_404(contribution_id)
    
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to view this page.', 'error')
        return redirect(url_for('book_platform.campaigns'))
    
    investor_id = get_profile_id(user_profile, profile_type)
    if investment.investor_id != investor_id:
        flash('You can only view your own contribution refunds.', 'error')
        return redirect(url_for('book_platform.campaigns'))
    
    # Check if refund allowed (before first draft, no pending refund)
    from glconnect.accountability_service import FIRST_DRAFT_MIN_WORDS
    try:
        from glconnect.book_platform_routes import update_book_word_count
        update_book_word_count(investment.book_project)
    except Exception:
        pass
    word_count = (investment.book_project.word_count or 0)
    refunds = RefundRequest.query.filter_by(investment_id=contribution_id).order_by(
        RefundRequest.created_at.desc()
    ).all()
    has_pending = any(r.status == TransactionStatus.PENDING for r in refunds)
    can_request_refund = (
        word_count < FIRST_DRAFT_MIN_WORDS
        and investment.status.value != 'refunded'
        and not has_pending
    )
    
    return render_template('book_platform/contribution_refund_status.html',
                         investment=investment,
                         contribution=investment,
                         refunds=refunds,
                         can_request_refund=can_request_refund,
                         first_draft_min_words=FIRST_DRAFT_MIN_WORDS)


# Admin Refund Requests - process investor refunds via Stripe (before first draft only)
@book_bp.route('/admin/refund-requests')
@login_required
def admin_refund_requests():
    """Admin view of pending investor refund requests"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    from glconnect.book_platform_models import BookInvestment, TransactionStatus
    
    pending = RefundRequest.query.filter_by(status=TransactionStatus.PENDING).options(
        joinedload(RefundRequest.investment).joinedload(BookInvestment.investor),
        joinedload(RefundRequest.investment).joinedload(BookInvestment.book_project)
    ).order_by(RefundRequest.requested_at.asc()).all()
    
    completed = RefundRequest.query.filter_by(status=TransactionStatus.COMPLETED).options(
        joinedload(RefundRequest.investment).joinedload(BookInvestment.investor),
        joinedload(RefundRequest.investment).joinedload(BookInvestment.book_project)
    ).order_by(RefundRequest.processed_at.desc()).limit(50).all()
    
    return render_template('book_platform/admin_refund_requests.html',
        pending=pending, completed=completed
    )


@book_bp.route('/admin/refund-requests/<int:refund_id>/process', methods=['POST'])
@login_required
def admin_process_refund(refund_id):
    """Admin processes investor refund via Stripe"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.admin_refund_requests'))
    
    refund = RefundRequest.query.options(joinedload(RefundRequest.investment)).get_or_404(refund_id)
    
    if refund.status != TransactionStatus.PENDING:
        flash(f'Refund already processed.', 'warning')
        return redirect(url_for('book_platform.admin_refund_requests'))
    
    investment = refund.investment
    payment_intent_id = getattr(investment, 'stripe_payment_intent_id', None)
    
    if payment_intent_id:
        try:
            init_stripe()
            import stripe
            amount_cents = int(round(refund.amount * 100))
            stripe_refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount_cents,
                reason='requested_by_customer',
                metadata={'refund_request_id': str(refund.id), 'investment_id': str(investment.id)}
            )
            refund.refund_transaction_id = stripe_refund.id
            refund.status = TransactionStatus.COMPLETED
            refund.processed_at = datetime.now(timezone.utc)
            refund.payment_method = 'stripe'
            investment.status = InvestmentStatus.REFUNDED
            investment.refunded_at = datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Stripe refund processed: refund_request={refund.id}")
            flash(f'Refund of ${refund.amount:.2f} processed via Stripe.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Stripe refund failed: {e}", exc_info=True)
            flash(f'Stripe refund failed: {str(e)}. Process manually.', 'error')
    else:
        refund.status = TransactionStatus.COMPLETED
        refund.processed_at = datetime.now(timezone.utc)
        refund.payment_method = 'manual'
        refund.refund_transaction_id = f'manual-{refund.id}-{datetime.now(timezone.utc).strftime("%Y%m%d%H%M")}'
        investment.status = InvestmentStatus.REFUNDED
        investment.refunded_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'Refund of ${refund.amount:.2f} marked as processed (manual - no Stripe payment intent).', 'warning')
    
    return redirect(url_for('book_platform.admin_refund_requests'))


# ============================================================================
# SELF-PUBLISHING PIPELINE HUB
# ============================================================================

@book_bp.route('/publishing')
@login_required
def publishing_pipeline():
    """Legacy URL — use My books and Content hub instead."""
    return redirect(url_for('book_platform.books'), code=301)


@book_bp.route('/publicity')
@login_required
def publicity_promotion():
    """Legacy URL — publicity lives in Content hub."""
    return redirect(url_for('book_platform.content_hub'), code=301)


# ============================================================================
# UNIFIED CONTENT HUB - BLOGS, NEWS, FREELANCING
# ============================================================================

@book_bp.route('/content-hub')
@login_required
def content_hub():
    """
    Unified Content - Access point for all content types:
    - Stories & News (Blogs)
    - Podcasts & Audio (News broadcasts)
    - Freelance Journalism
    - Music (Artists & Songs)
    Accessible to ALL logged-in users (no author profile required)
    Maintains backward compatibility with existing routes
    """
    from glconnect.models import Post, Artist
    # Check if user has an artist profile
    artist_profile = Artist.query.filter_by(user_id=current_user.user_id).first()
    from sqlalchemy import inspect
    
    # Get recent blog posts for preview - handle missing columns gracefully
    try:
        # Rollback any existing failed transaction first
        db.session.rollback()
        
        # Check if new columns exist in database
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('post')]
        has_new_columns = all(col in columns for col in ['category', 'language', 'country'])
        
        if has_new_columns:
            # Query with new columns
            recent_posts = Post.query.order_by(Post.date_posted.desc()).limit(5).all()
        else:
            # Query only existing columns (backward compatible)
            recent_posts = db.session.query(
                Post.id, Post.title, Post.content, Post.date_posted, Post.user_id
            ).order_by(Post.date_posted.desc()).limit(5).all()
            # Convert to Post-like objects for template compatibility
            class SimplePost:
                def __init__(self, id, title, content, date_posted, user_id):
                    self.id = id
                    self.title = title
                    self.content = content
                    self.date_posted = date_posted
                    self.user_id = user_id
                    self.category = None
                    self.language = None
                    self.country = None
                    self.likes_count = 0
                    self.impressions_count = 0
                    # Get author relationship - use db.session.get to avoid transaction issues
                    try:
                        self.author = db.session.get(User, user_id)
                    except:
                        self.author = None
            
            recent_posts = [SimplePost(*post) for post in recent_posts]
    except Exception as e:
        logger.error(f"Error fetching recent posts: {e}")
        db.session.rollback()  # Rollback on error
        recent_posts = []
    
    # Get user's posts if any - handle missing columns gracefully
    user_posts = []
    if current_user.is_authenticated:
        try:
            # Rollback any existing failed transaction first
            db.session.rollback()
            
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('post')]
            has_new_columns = all(col in columns for col in ['category', 'language', 'country'])
            
            if has_new_columns:
                user_posts = Post.query.filter_by(user_id=current_user.user_id).order_by(Post.date_posted.desc()).limit(5).all()
            else:
                # Query only existing columns
                posts_data = db.session.query(
                    Post.id, Post.title, Post.content, Post.date_posted, Post.user_id
                ).filter_by(user_id=current_user.user_id).order_by(Post.date_posted.desc()).limit(5).all()
                
                class SimplePost:
                    def __init__(self, id, title, content, date_posted, user_id):
                        self.id = id
                        self.title = title
                        self.content = content
                        self.date_posted = date_posted
                        self.user_id = user_id
                        self.category = None
                        self.language = None
                        self.country = None
                        self.likes_count = 0
                        self.impressions_count = 0
                        # Get author relationship - use db.session.get to avoid transaction issues
                        try:
                            self.author = db.session.get(User, user_id)
                        except:
                            self.author = None
                
                user_posts = [SimplePost(*post) for post in posts_data]
        except Exception as e:
            logger.error(f"Error fetching user posts: {e}")
            db.session.rollback()  # Rollback on error
            user_posts = []
    
    return render_template('book_platform/content_hub.html',
                         recent_posts=recent_posts,
                         user_posts=user_posts,
                         has_artist_profile=artist_profile is not None,
                         artist_profile=artist_profile)

@book_bp.route('/stories')
@login_required
def stories_redirect():
    """Redirect to approved freelance stories - filtered by journalism categories"""
    # Redirect to blogs filtered by freelance journalism categories
    return redirect(url_for('blog.blogs', freelance='true'))

@book_bp.route('/blogs')
@login_required
def blogs_redirect():
    """Redirect to all blogs - no filtering"""
    return redirect(url_for('blog.blogs'))

@book_bp.route('/music/voice-agent', methods=['POST'])
def music_voice_agent():
    """Voice agent for music: answer questions about songs/artists, play, add to playlist, download."""
    from glconnect.music_voice_agent import run_agent_turn
    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "Message required", "text": "", "actions": []}), 400
    user_id = current_user.user_id if current_user.is_authenticated else None
    base_url = request.url_root.rstrip("/") if request.url_root else ""
    try:
        result = run_agent_turn(message, user_id=user_id, base_url=base_url)
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "text": "Sorry, something went wrong. Please try again.",
            "actions": []
        }), 500


@book_bp.route('/music')
def music_dashboard():
    """Standalone music dashboard for searching songs and managing playlists"""
    from glconnect.models import Artist
    # Check if user has an artist profile (only when logged in)
    artist_profile = None
    is_artist_account = False
    if current_user.is_authenticated:
        artist_profile = Artist.query.filter_by(user_id=current_user.user_id).first()
        is_artist_account = hasattr(current_user, 'role') and current_user.role == 'artist'
    return render_template('book_platform/music_dashboard.html', 
                         has_artist_profile=artist_profile is not None, 
                         artist_profile=artist_profile,
                         is_artist_account=is_artist_account)

@book_bp.route('/music/create-artist-profile', methods=['POST'])
@login_required
def create_artist_profile():
    """Create an artist profile for the current user - only for users with 'artist' role"""
    try:
        from glconnect.models import Artist
        import os
        from werkzeug.utils import secure_filename
        
        # Check if user has 'artist' role
        if not hasattr(current_user, 'role') or current_user.role != 'artist':
            return jsonify({
                'success': False, 
                'message': 'Only users with an artist account can create artist profiles. Please register with an artist account or contact support to change your account type.'
            }), 403
        
        # Check if user already has an artist profile
        existing_artist = Artist.query.filter_by(user_id=current_user.user_id).first()
        if existing_artist:
            return jsonify({'success': False, 'message': 'You already have an artist profile.'}), 400
        
        # Get form data (FormData instead of JSON)
        artist_name = request.form.get('artist_name', '').strip()
        bio = request.form.get('bio', '').strip()
        profile_pic_file = request.files.get('profile_pic')
        
        if not artist_name:
            return jsonify({'success': False, 'message': 'Artist name is required.'}), 400
        
        # Check if artist name already exists
        existing_name = Artist.query.filter_by(artist_name=artist_name).first()
        if existing_name:
            return jsonify({'success': False, 'message': 'This artist name is already taken.'}), 400
        
        # Handle profile picture upload (optional)
        profile_pic_filename = "static/uploads/default.jpg"  # Default value
        if profile_pic_file and profile_pic_file.filename != '':
            # Validate file extension
            if not allowed_image_file(profile_pic_file.filename):
                return jsonify({
                    'success': False, 
                    'message': f'Invalid image format. Allowed formats: {", ".join(ALLOWED_IMAGE_EXTENSIONS)}'
                }), 400
            
            # Validate file size
            profile_pic_file.seek(0, os.SEEK_END)
            file_size = profile_pic_file.tell()
            profile_pic_file.seek(0)
            if file_size > MAX_IMAGE_SIZE:
                return jsonify({
                    'success': False, 
                    'message': f'Image file is too large. Maximum allowed size is {MAX_IMAGE_SIZE // (1024 * 1024)}MB.'
                }), 400
            
            # Generate unique filename
            filename = secure_filename(profile_pic_file.filename)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
            
            # Define upload folder - save to static/uploads/ (matching database path format)
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Save the file
            filepath = os.path.join(upload_folder, unique_filename)
            profile_pic_file.save(filepath)
            
            # Store path as static/uploads/picname.jpg in database
            profile_pic_filename = f"static/uploads/{unique_filename}"
        
        # Create new artist profile
        new_artist = Artist(
            user_id=current_user.user_id,
            artist_name=artist_name,
            bio=bio or None,
            profile_pic=profile_pic_filename
        )
        
        db.session.add(new_artist)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Artist profile created successfully!',
            'artist_id': new_artist.artist_id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating artist profile: {e}")
        return jsonify({'success': False, 'message': f'Error creating profile: {str(e)}'}), 500

def sanitize_input_music(input_string):
    """Sanitize user inputs for music uploads"""
    if input_string:
        sanitized = input_string.strip()
        sanitized = re.sub(r'[^a-zA-Z0-9\s\-\.\/\:]', '', sanitized)
        return sanitized
    return ""

def sanitize_url_music(url):
    """Sanitize and enforce HTTPS for URLs"""
    if url:
        sanitized = sanitize_input_music(url)
        if not sanitized.startswith('http://') and not sanitized.startswith('https://'):
            sanitized = 'https://' + sanitized
        from urllib.parse import urlparse
        parsed = urlparse(sanitized)
        if parsed.scheme in ['http', 'https'] and parsed.netloc:
            return sanitized
    return ""

@book_bp.route('/music/upload-song', methods=['POST'])
@login_required
def upload_song_music_dashboard():
    """Upload a song from the music dashboard - only for users with 'artist' role"""
    try:
        from glconnect.models import Artist, Song_upload
        import os
        
        # Check if user has 'artist' role
        if not hasattr(current_user, 'role') or current_user.role != 'artist':
            return jsonify({
                'success': False, 
                'message': 'Only users with an artist account can upload songs. Please register with an artist account or contact support to change your account type.'
            }), 403
        
        # Check if user has an artist profile
        artist = Artist.query.filter_by(user_id=current_user.user_id).first()
        if not artist:
            return jsonify({'success': False, 'message': 'Please create an artist profile first.'}), 400
        
        # Get form data
        song_name = sanitize_input_music(request.form.get('song_name', '').strip())
        song_file = request.files.get('song_file')
        cover_image_file = request.files.get('cover_image')
        
        # Social media links
        twitter_link = sanitize_url_music(request.form.get('twitter', ''))
        instagram_link = sanitize_url_music(request.form.get('instagram', ''))
        spotify_link = sanitize_url_music(request.form.get('spotify', ''))
        apple_music_link = sanitize_url_music(request.form.get('apple_music', ''))
        
        # Validation
        if not song_name:
            return jsonify({'success': False, 'message': 'Song name is required.'}), 400
        
        if not song_file or song_file.filename == '':
            return jsonify({'success': False, 'message': 'Song file is required.'}), 400
        
        if not song_file.filename.lower().endswith('.mp3'):
            return jsonify({'success': False, 'message': 'Only MP3 files are allowed.'}), 400
        
        # Check file size (50 MB limit)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
        song_file.seek(0, os.SEEK_END)
        file_size = song_file.tell()
        song_file.seek(0)
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'message': 'File is too large. Maximum allowed size is 50 MB.'}), 400
        
        # Save to afro directory for searchability (matching the search path structure)
        afro_folder = os.path.join(os.getcwd(), 'glconnect', 'static', 'afro')
        os.makedirs(afro_folder, exist_ok=True)
        
        # Create filename with spaces and dashes (not underscores)
        # Sanitize but preserve spaces and dashes
        def sanitize_filename_preserve_spaces(text):
            """Sanitize filename but preserve spaces and dashes"""
            # Remove or replace dangerous characters but keep spaces, dashes, and alphanumeric
            import re
            # Keep alphanumeric, spaces, dashes, and dots
            sanitized = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', text)
            # Remove multiple consecutive spaces
            sanitized = re.sub(r'\s+', ' ', sanitized)
            # Strip leading/trailing spaces and dashes
            sanitized = sanitized.strip(' -')
            return sanitized
        
        # Format: "Artist Name - Song Name.mp3" with spaces preserved
        base_filename = f"{sanitize_filename_preserve_spaces(artist.artist_name)} - {sanitize_filename_preserve_spaces(song_name)}"
        mp3_filename = f"{base_filename}.mp3"
        mp3_path = os.path.join(afro_folder, mp3_filename)
        
        counter = 1
        while os.path.exists(mp3_path):
            mp3_filename = f"{base_filename} ({counter}).mp3"
            mp3_path = os.path.join(afro_folder, mp3_filename)
            counter += 1
        
        song_file.save(mp3_path)
        
        # Handle cover image - save to images folder
        images_folder = os.path.join(os.getcwd(), 'glconnect', 'static', 'images')
        os.makedirs(images_folder, exist_ok=True)
        
        if cover_image_file and cover_image_file.filename != '':
            cover_filename = secure_filename(cover_image_file.filename)
            cover_path = os.path.join(images_folder, cover_filename)
            cover_image_file.save(cover_path)
        else:
            cover_filename = "photo3.webp"
        
        # Store path that serve_song_file can resolve: relative to project (works in Docker /usr/src/appdir)
        full_db_path = f"glconnect/static/afro/{mp3_filename}"
        
        # Save to Song model for searchability (admin must approve before it appears in search)
        from glconnect.models import Song
        new_song = Song(
            name=song_name,
            artist=artist.artist_name,
            artist_id=artist.artist_id,
            local_path=full_db_path,  # Full path: /liqfolder/glconnect/static/afro/Artist Name - Song Name.mp3
            cover_image=cover_filename,
            approval_status='pending'
        )
        db.session.add(new_song)
        
        # Also create Song_upload entry for compatibility
        new_song_upload = Song_upload(
            name_song=song_name,
            name_artist=artist.artist_name,
            local_path=full_db_path,
            cover_image=cover_filename,
            twitter_link=twitter_link,
            instagram_link=instagram_link,
            spotify_link=spotify_link,
            apple_music_link=apple_music_link,
            artist_id=artist.artist_id,
            approval_status='pending'
        )
        db.session.add(new_song_upload)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Song uploaded successfully! It will be reviewed by an admin before appearing in search.',
            'song_id': new_song.id
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error uploading song: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error uploading song: {str(e)}'}), 500

@book_bp.route('/stories/create')
@login_required
def create_story_redirect():
    """Redirect to create blog post - maintains Ink Studio context"""
    # Bloggers and freelancers can create stories
    if current_user.role not in ['blogger', 'freelancer']:
        flash('Only users with blogger or freelancer role can create stories. Please contact admin to change your role.', 'error')
        return redirect(url_for('book_platform.content_hub'))
    return redirect(url_for('blog.blogpost'))

@book_bp.route('/podcasts')
@login_required
def podcasts_redirect():
    """Redirect to news/podcasts - maintains Ink Studio context"""
    return redirect('/routes2/news')

@book_bp.route('/news')
@login_required
def news_redirect():
    """Redirect to news broadcasts - maintains Ink Studio context"""
    return redirect('/routes2/news')

# ============================================================================
# PODCAST UPLOAD & ADMIN APPROVAL SYSTEM
# ============================================================================

@book_bp.route('/podcasts/upload', methods=['GET', 'POST'])
@login_required
def upload_podcast():
    """Upload a podcast (audio or video) - max 30 minutes, requires admin approval"""
    # Only podcasters can upload podcasts
    if current_user.role != 'podcaster':
        flash('Only users with podcaster role can upload podcasts. Please contact admin to change your role.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    if request.method == 'GET':
        from glconnect.models import PodcastSubmission
        # Get user's existing podcasts for replace option
        user_podcasts = PodcastSubmission.query.filter_by(user_id=current_user.user_id).order_by(
            PodcastSubmission.submitted_at.desc()
        ).all()
        return render_template('book_platform/upload_podcast.html', user_podcasts=user_podcasts)
    
    try:
        from glconnect.models import PodcastSubmission
        import os
        from werkzeug.utils import secure_filename
        
        # Try to import moviepy for duration checking
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip
            MOVIEPY_AVAILABLE = True
        except ImportError:
            MOVIEPY_AVAILABLE = False
            logger.warning("moviepy not available. Duration validation will be limited.")
        
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        language = request.form.get('language', 'en')
        file = request.files.get('podcast_file')
        
        # Validation
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('book_platform.upload_podcast'))
        
        if not file or file.filename == '':
            flash('Please select a podcast file to upload', 'error')
            return redirect(url_for('book_platform.upload_podcast'))
        
        # Check file extension
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.mp4', '.mov', '.avi', '.mkv'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            flash(f'Invalid file type. Allowed: {", ".join(allowed_extensions)}', 'error')
            return redirect(url_for('book_platform.upload_podcast'))
        
        # Determine file type
        is_video = file_ext in {'.mp4', '.mov', '.avi', '.mkv'}
        file_type = 'video' if is_video else 'audio'
        
        # Save file temporarily to check duration
        # Files are stored in glconnect/static/podcasts/ (matches /liqfolder/glconnect/static/podcasts/ in Docker)
        temp_dir = os.path.join(current_app.root_path, 'static', 'temp_podcasts')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(temp_file_path)
        
        # Get file size first
        file_size = os.path.getsize(temp_file_path)
        
        # Check duration (max 30 minutes = 1800 seconds)
        MAX_DURATION_SECONDS = 30 * 60  # 30 minutes
        duration = 0
        
        if MOVIEPY_AVAILABLE:
            try:
                if is_video:
                    clip = VideoFileClip(temp_file_path)
                    duration = int(clip.duration)
                    clip.close()
                else:
                    clip = AudioFileClip(temp_file_path)
                    duration = int(clip.duration)
                    clip.close()
                
                if duration > MAX_DURATION_SECONDS:
                    os.remove(temp_file_path)
                    flash(f'Podcast duration ({duration // 60} minutes) exceeds maximum allowed duration of 30 minutes', 'error')
                    return redirect(url_for('book_platform.upload_podcast'))
                
                if duration < 1:
                    os.remove(temp_file_path)
                    flash('Podcast file appears to be empty or corrupted', 'error')
                    return redirect(url_for('book_platform.upload_podcast'))
                    
            except Exception as e:
                os.remove(temp_file_path)
                logger.error(f"Error checking podcast duration: {e}")
                flash('Error processing podcast file. Please ensure the file is valid.', 'error')
                return redirect(url_for('book_platform.upload_podcast'))
        else:
            # Fallback: Use file size as rough estimate (not accurate but better than nothing)
            # Approximate: 1MB per minute for audio, 10MB per minute for video
            file_size_mb = file_size / (1024 * 1024)
            if is_video:
                estimated_duration = int(file_size_mb / 10 * 60)  # Rough estimate
            else:
                estimated_duration = int(file_size_mb / 1 * 60)  # Rough estimate
            
            if estimated_duration > MAX_DURATION_SECONDS:
                os.remove(temp_file_path)
                flash(f'File size suggests duration exceeds 30 minutes. Please ensure your podcast is under 30 minutes.', 'error')
                return redirect(url_for('book_platform.upload_podcast'))
            
            duration = estimated_duration  # Use estimate, admin can verify during review
            flash('Note: Duration validation is limited. Admin will verify the actual duration during review.', 'info')
        
        # Move to permanent location
        # Store in glconnect/static/podcasts/ (matches /liqfolder/glconnect/static/podcasts/ in Docker)
        podcast_dir = os.path.join(current_app.root_path, 'static', 'podcasts')
        os.makedirs(podcast_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        safe_title = secure_filename(title[:50])  # Limit title length for filename
        unique_filename = f"{current_user.user_id}_{timestamp}_{safe_title}{file_ext}"
        final_file_path = os.path.join(podcast_dir, unique_filename)
        
        # Move file
        os.rename(temp_file_path, final_file_path)
        
        # Create database record
        podcast = PodcastSubmission(
            user_id=current_user.user_id,
            title=title,
            description=description,
            file_path=final_file_path,
            file_type=file_type,
            duration_seconds=duration,
            file_size=file_size,
            status='pending',
            category=category if category else None,
            language=language
        )
        db.session.add(podcast)
        db.session.commit()
        
        flash('Podcast uploaded successfully! It will be reviewed by an admin before going live.', 'success')
        return redirect(url_for('book_platform.my_podcasts'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading podcast: {e}")
        flash('An error occurred while uploading your podcast. Please try again.', 'error')
        return redirect(url_for('book_platform.upload_podcast'))

@book_bp.route('/podcasts/my-podcasts')
@login_required
def my_podcasts():
    """View user's submitted podcasts - only for podcasters"""
    # Only podcasters can view their podcasts
    if current_user.role != 'podcaster':
        flash('Only users with podcaster role can manage podcasts. Please contact admin to change your role.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    from glconnect.models import PodcastSubmission
    
    podcasts = PodcastSubmission.query.filter_by(user_id=current_user.user_id).order_by(
        PodcastSubmission.submitted_at.desc()
    ).all()
    
    return render_template('book_platform/my_podcasts.html', podcasts=podcasts)

@book_bp.route('/podcasts/<int:podcast_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_podcast(podcast_id):
    """Edit or replace an existing podcast (only if pending or rejected)"""
    from glconnect.models import PodcastSubmission
    import os
    from werkzeug.utils import secure_filename
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    
    # Only allow editing if user owns it and it's not approved
    if podcast.user_id != current_user.user_id:
        flash('You do not have permission to edit this podcast', 'error')
        return redirect(url_for('book_platform.my_podcasts'))
    
    if podcast.status == 'approved':
        flash('Approved podcasts cannot be edited. Contact admin if you need to make changes.', 'error')
        return redirect(url_for('book_platform.my_podcasts'))
    
    if request.method == 'GET':
        # Get user's other podcasts for reference
        user_podcasts = PodcastSubmission.query.filter_by(user_id=current_user.user_id).order_by(
            PodcastSubmission.submitted_at.desc()
        ).all()
        return render_template('book_platform/edit_podcast.html', podcast=podcast, user_podcasts=user_podcasts)
    
    # Handle POST - update podcast
    try:
        # Try to import moviepy for duration checking
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip
            MOVIEPY_AVAILABLE = True
        except ImportError:
            MOVIEPY_AVAILABLE = False
            logger.warning("moviepy not available. Duration validation will be limited.")
        
        # Get form data
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        language = request.form.get('language', 'en')
        file = request.files.get('podcast_file')
        
        # Validation
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
        
        # Update metadata
        podcast.title = title
        podcast.description = description
        podcast.category = category if category else None
        podcast.language = language
        
        # If new file is uploaded, replace the old one
        if file and file.filename != '':
            # Check file extension
            allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg', '.mp4', '.mov', '.avi', '.mkv'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                flash(f'Invalid file type. Allowed: {", ".join(allowed_extensions)}', 'error')
                return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
            
            # Determine file type
            is_video = file_ext in {'.mp4', '.mov', '.avi', '.mkv'}
            file_type = 'video' if is_video else 'audio'
            
            # Save file temporarily to check duration
            temp_dir = os.path.join(current_app.root_path, 'static', 'temp_podcasts')
            os.makedirs(temp_dir, exist_ok=True)
            temp_file_path = os.path.join(temp_dir, secure_filename(file.filename))
            file.save(temp_file_path)
            
            # Get file size
            file_size = os.path.getsize(temp_file_path)
            
            # Check duration (max 30 minutes = 1800 seconds)
            MAX_DURATION_SECONDS = 30 * 60
            duration = 0
            
            if MOVIEPY_AVAILABLE:
                try:
                    if is_video:
                        clip = VideoFileClip(temp_file_path)
                        duration = int(clip.duration)
                        clip.close()
                    else:
                        clip = AudioFileClip(temp_file_path)
                        duration = int(clip.duration)
                        clip.close()
                    
                    if duration > MAX_DURATION_SECONDS:
                        os.remove(temp_file_path)
                        flash(f'Podcast duration ({duration // 60} minutes) exceeds maximum allowed duration of 30 minutes', 'error')
                        return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
                    
                    if duration < 1:
                        os.remove(temp_file_path)
                        flash('Podcast file appears to be empty or corrupted', 'error')
                        return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
                        
                except Exception as e:
                    os.remove(temp_file_path)
                    logger.error(f"Error checking podcast duration: {e}")
                    flash('Error processing podcast file. Please ensure the file is valid.', 'error')
                    return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
            else:
                # Fallback: Use file size as rough estimate
                file_size_mb = file_size / (1024 * 1024)
                if is_video:
                    estimated_duration = int(file_size_mb / 10 * 60)
                else:
                    estimated_duration = int(file_size_mb / 1 * 60)
                
                if estimated_duration > MAX_DURATION_SECONDS:
                    os.remove(temp_file_path)
                    flash(f'File size suggests duration exceeds 30 minutes. Please ensure your podcast is under 30 minutes.', 'error')
                    return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))
                
                duration = estimated_duration
                flash('Note: Duration validation is limited. Admin will verify the actual duration during review.', 'info')
            
            # Delete old file if exists
            if os.path.exists(podcast.file_path):
                try:
                    os.remove(podcast.file_path)
                except Exception as e:
                    logger.error(f"Error deleting old podcast file: {e}")
            
            # Move new file to permanent location
            podcast_dir = os.path.join(current_app.root_path, 'static', 'podcasts')
            os.makedirs(podcast_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            safe_title = secure_filename(title[:50])
            unique_filename = f"{current_user.user_id}_{timestamp}_{safe_title}{file_ext}"
            final_file_path = os.path.join(podcast_dir, unique_filename)
            
            # Move file
            os.rename(temp_file_path, final_file_path)
            
            # Update file info
            podcast.file_path = final_file_path
            podcast.file_type = file_type
            podcast.duration_seconds = duration
            podcast.file_size = file_size
            # Reset status to pending if it was rejected
            if podcast.status == 'rejected':
                podcast.status = 'pending'
                podcast.rejection_reason = None
        
        db.session.commit()
        flash('Podcast updated successfully! It will be reviewed by an admin if a new file was uploaded.', 'success')
        return redirect(url_for('book_platform.my_podcasts'))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating podcast: {e}")
        flash('An error occurred while updating your podcast. Please try again.', 'error')
        return redirect(url_for('book_platform.edit_podcast', podcast_id=podcast_id))

@book_bp.route('/podcasts/<int:podcast_id>/delete', methods=['POST'])
@login_required
def delete_podcast(podcast_id):
    """Delete a podcast submission (only if pending or rejected)"""
    from glconnect.models import PodcastSubmission
    import os
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    
    # Only allow deletion if user owns it and it's not approved
    if podcast.user_id != current_user.user_id:
        flash('You do not have permission to delete this podcast', 'error')
        return redirect(url_for('book_platform.my_podcasts'))
    
    if podcast.status == 'approved':
        flash('Approved podcasts cannot be deleted. Contact admin if needed.', 'error')
        return redirect(url_for('book_platform.my_podcasts'))
    
    # Delete file if exists
    if os.path.exists(podcast.file_path):
        try:
            os.remove(podcast.file_path)
        except Exception as e:
            logger.error(f"Error deleting podcast file: {e}")
    
    db.session.delete(podcast)
    db.session.commit()
    
    flash('Podcast deleted successfully', 'success')
    return redirect(url_for('book_platform.my_podcasts'))

# Admin routes for podcast approval
@book_bp.route('/admin/podcasts')
@login_required
def admin_podcasts():
    """Admin interface to review and approve/reject podcasts"""
    from glconnect.models import PodcastSubmission
    
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    # Get pending podcasts
    pending_podcasts = PodcastSubmission.query.filter_by(status='pending').order_by(
        PodcastSubmission.submitted_at.asc()
    ).all()
    
    # Get all podcasts for review history
    all_podcasts = PodcastSubmission.query.order_by(
        PodcastSubmission.submitted_at.desc()
    ).limit(50).all()
    
    return render_template('book_platform/admin_podcasts.html', 
                         pending_podcasts=pending_podcasts,
                         all_podcasts=all_podcasts)

@book_bp.route('/admin/podcasts/<int:podcast_id>/approve', methods=['POST'])
@login_required
def approve_podcast(podcast_id):
    """Approve a podcast submission"""
    from glconnect.models import PodcastSubmission
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    
    if podcast.status != 'pending':
        return jsonify({'success': False, 'error': 'Podcast is not pending approval'}), 400
    
    podcast.status = 'approved'
    podcast.reviewed_at = datetime.now(timezone.utc)
    podcast.reviewed_by = current_user.user_id
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Podcast approved successfully'})

@book_bp.route('/admin/podcasts/<int:podcast_id>/reject', methods=['POST'])
@login_required
def reject_podcast(podcast_id):
    """Reject a podcast submission"""
    from glconnect.models import PodcastSubmission
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    data = request.get_json()
    rejection_reason = data.get('reason', 'No reason provided')
    
    if podcast.status != 'pending':
        return jsonify({'success': False, 'error': 'Podcast is not pending approval'}), 400
    
    podcast.status = 'rejected'
    podcast.reviewed_at = datetime.now(timezone.utc)
    podcast.reviewed_by = current_user.user_id
    podcast.rejection_reason = rejection_reason
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Podcast rejected'})

@book_bp.route('/admin/podcasts/<int:podcast_id>/delete', methods=['POST'])
@login_required
def admin_delete_podcast(podcast_id):
    """Admin route to delete any podcast (approved, pending, or rejected)"""
    from glconnect.models import PodcastSubmission
    import os
    
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    podcast_title = podcast.title
    
    # Delete file if exists - try multiple possible locations
    file_path = podcast.file_path
    filename = os.path.basename(file_path) if file_path else None
    
    # Try multiple possible locations
    possible_paths = []
    if file_path and os.path.exists(file_path):
        possible_paths.append(file_path)
    
    if filename:
        correct_path = os.path.join(current_app.root_path, 'static', 'podcasts', filename)
        if os.path.exists(correct_path):
            possible_paths.append(correct_path)
        
        # Try old locations
        old_paths = [
            os.path.join(current_app.root_path, 'uploads', 'podcasts', filename),
            os.path.join(os.path.dirname(current_app.root_path), 'uploads', 'podcasts', filename),
            os.path.join(current_app.root_path, 'static', 'uploads', 'podcasts', filename),
        ]
        for old_path in old_paths:
            if os.path.exists(old_path):
                possible_paths.append(old_path)
    
    # Delete all found files
    for path in possible_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted podcast file: {path}")
        except Exception as e:
            logger.error(f"Error deleting podcast file {path}: {e}")
    
    # Delete from database
    try:
        db.session.delete(podcast)
        db.session.commit()
        logger.info(f"Admin {current_user.username} deleted podcast: {podcast_title} (ID: {podcast_id})")
        return jsonify({'success': True, 'message': f'Podcast "{podcast_title}" deleted successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting podcast from database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ----- Admin Song (Music) Approval -----
@book_bp.route('/admin/songs')
@login_required
def admin_songs():
    """Admin panel to review and approve/reject artist song uploads"""
    from glconnect.models import Song
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    status_filter = request.args.get('status', 'pending')
    if status_filter == 'pending':
        pending_songs = Song.query.filter_by(approval_status='pending').order_by(Song.id.desc()).all()
        all_songs = Song.query.filter(Song.approval_status != 'pending').order_by(Song.id.desc()).limit(50).all()
    else:
        pending_songs = Song.query.filter_by(approval_status='pending').order_by(Song.id.desc()).all()
        all_songs = Song.query.order_by(Song.id.desc()).limit(100).all()
    return render_template('book_platform/admin_songs.html',
                         pending_songs=pending_songs,
                         all_songs=all_songs,
                         status_filter=status_filter)

@book_bp.route('/admin/songs/<int:song_id>/approve', methods=['POST'])
@login_required
def admin_approve_song(song_id):
    """Approve a song submission - makes it visible in search and playlists"""
    from glconnect.models import Song, Song_upload
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    song = Song.query.get_or_404(song_id)
    if song.approval_status != 'pending':
        return jsonify({'success': False, 'error': 'Song is not pending approval'}), 400
    song.approval_status = 'approved'
    # Keep Song_upload in sync if exists (same artist/name)
    su = Song_upload.query.filter_by(name_song=song.name, name_artist=song.artist).order_by(Song_upload.upload_id.desc()).first()
    if su:
        su.approval_status = 'approved'
    db.session.commit()
    logger.info(f"Song '{song.name}' by '{song.artist}' (ID {song_id}) approved by admin {current_user.username}")
    return jsonify({'success': True, 'message': f'Song "{song.name}" approved successfully'})

@book_bp.route('/admin/songs/<int:song_id>/reject', methods=['POST'])
@login_required
def admin_reject_song(song_id):
    """Reject a song submission - hides from search/playlists"""
    from glconnect.models import Song, Song_upload
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    song = Song.query.get_or_404(song_id)
    if song.approval_status != 'pending':
        return jsonify({'success': False, 'error': 'Song is not pending approval'}), 400
    reason = request.get_json(silent=True) or {}
    rejection_reason = reason.get('reason', '').strip()
    song.approval_status = 'rejected'
    su = Song_upload.query.filter_by(name_song=song.name, name_artist=song.artist).order_by(Song_upload.upload_id.desc()).first()
    if su:
        su.approval_status = 'rejected'
    db.session.commit()
    logger.info(f"Song '{song.name}' by '{song.artist}' (ID {song_id}) rejected by admin {current_user.username}. Reason: {rejection_reason}")
    return jsonify({'success': True, 'message': 'Song rejected'})

# ----- Admin YouTube / Music Download (admin only) -----
# Shared status for admin UI progress (thread-safe)
_music_download_status = {
    'status': 'idle',   # idle | downloading | renaming | playlist | ingesting | completed | failed
    'step': None,       # download | rename | m3u | ingest (current or failed step)
    'message': '',
    'error': None,
    'url': '',
    'started_at': None,
    'completed_at': None,
}
_music_download_lock = threading.Lock()

def _set_music_download_status(status, message='', error=None, url=None, completed=False, step=None):
    with _music_download_lock:
        _music_download_status['status'] = status
        _music_download_status['message'] = message
        _music_download_status['error'] = error
        if step is not None:
            _music_download_status['step'] = step
        if url is not None:
            _music_download_status['url'] = url
        if status == 'downloading':
            _music_download_status['started_at'] = datetime.now(timezone.utc).isoformat()
            _music_download_status['completed_at'] = None
        if completed:
            _music_download_status['completed_at'] = datetime.now(timezone.utc).isoformat()

def _get_music_download_status():
    with _music_download_lock:
        return dict(_music_download_status)

@book_bp.route('/admin/music')
@login_required
def admin_music():
    """Admin-only page to paste a YouTube playlist/video URL and trigger song download pipeline"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    return render_template('book_platform/admin_music.html')

@book_bp.route('/admin/music/status')
@login_required
def admin_music_status():
    """Return current YouTube download workflow status for admin UI (polling)."""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403
    return jsonify(_get_music_download_status())

@book_bp.route('/admin/music/download', methods=['POST'])
@login_required
def admin_music_download():
    """Start YouTube download in background (admin only). Uses yt-dlp → rename → M3U → ingest."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    data = request.get_json() or request.form
    url = (data.get('url') or data.get('youtube_url') or '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'YouTube URL is required'}), 400
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'success': False, 'error': 'Please provide a valid YouTube playlist or video URL'}), 400

    # yt-dlp must be installed (e.g. pip install yt-dlp or brew install yt-dlp)
    import shutil
    if not shutil.which('yt-dlp'):
        return jsonify({
            'success': False,
            'error': 'yt-dlp is not installed. Install it to enable YouTube downloads (e.g. pip install yt-dlp, or brew install yt-dlp on macOS).'
        }), 400

    # Reset and set initial status so admin sees progress immediately
    _set_music_download_status('downloading', 'Starting…', url=url, step='download')

    app = current_app._get_current_object()
    def run_pipeline():
        with app.app_context():
            current_step = 'download'
            try:
                from glconnect import pipeline as pipeline_mod
                from glconnect.pipeline import (
                    AudioDownloader,
                    MusicFileRenamer,
                    PlaylistIngestion,
                )
                # Paths are resolved at runtime in the running process (in Docker: container paths under /usr/src/appdir)
                glconnect_dir = os.path.dirname(os.path.abspath(pipeline_mod.__file__))
                output_folder = os.path.join(glconnect_dir, 'static', 'ytauto')
                output_folder = os.path.normpath(output_folder)
                logger.info("YouTube download output_folder: %s", output_folder)

                # Step 1: Download
                current_step = 'download'
                _set_music_download_status('downloading', 'Downloading audio with yt-dlp (may take several minutes)…', url=url, step=current_step)
                downloader = AudioDownloader(playlist_url=url, output_folder=output_folder)
                downloader.download_and_convert()
                _set_music_download_status('downloading', 'Download finished.', url=url, step=current_step)

                # Step 2: Rename
                current_step = 'rename'
                _set_music_download_status('renaming', 'Renaming files and cleaning filenames…', url=url, step=current_step)
                renamer = MusicFileRenamer()
                renamer.clean_music_names(output_folder)
                _set_music_download_status('renaming', 'Renaming finished.', url=url, step=current_step)

                # Step 3: Save to database only (no M3U yet; M3U is written when you click Clean after editing DB)
                current_step = 'ingest'
                _set_music_download_status('ingesting', 'Saving to database…', url=url, step=current_step)
                added, _ = PlaylistIngestion.ingest_songs_from_folder(output_folder)
                _set_music_download_status('ingesting', f'Saved to database. {added} new song(s) added.' if added > 0 else 'Saved to database (no new songs; all duplicates or empty folder).', url=url, step=current_step)

                if added > 0:
                    _set_music_download_status('completed', f'Done. {added} new song(s) added to the catalog.', url=url, completed=True, step=None)
                    logger.info("Admin YouTube download pipeline finished: %s new songs added", added)
                else:
                    _set_music_download_status('completed', 'Completed but no new songs were added (all duplicates or M3U empty).', url=url, completed=True, step=None)
                    logger.warning("Admin YouTube download pipeline: 0 new songs added")
            except Exception as e:
                logger.exception("Admin YouTube download pipeline failed at step %s: %s", current_step, e)
                step_label = {'download': 'Download', 'rename': 'Renaming files', 'ingest': 'Saving to database'}.get(current_step, current_step)
                _set_music_download_status('failed', f'{step_label} failed.', error=str(e), url=url, completed=True, step=current_step)
    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({
        'success': True,
        'message': 'Download started. Watch the progress below.',
        'status': _get_music_download_status()
    })


@book_bp.route('/admin/music/sync-from-db', methods=['POST'])
@login_required
def admin_music_sync_from_db():
    """After manual cleanup of downloaded_songs: rename files to 'name by artist', update DB paths, overwrite M3U."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    try:
        from glconnect.pipeline import sync_from_downloaded_songs
        renamed, m3u_updated = sync_from_downloaded_songs()
        return jsonify({
            'success': True,
            'message': f'Synced: {renamed} file(s) renamed, M3U updated from database.',
            'renamed': renamed,
            'm3u_updated': m3u_updated,
        })
    except Exception as e:
        logger.exception("Admin music sync-from-db failed: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@book_bp.route('/admin/music/sync-from-disk', methods=['POST'])
@login_required
def admin_music_sync_from_disk():
    """Fix discrepancies: use actual files on disk as source of truth. Updates DB and M3U to match."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    try:
        from glconnect.pipeline import sync_from_disk
        updated, m3u_updated = sync_from_disk()
        return jsonify({
            'success': True,
            'message': f'Fixed from disk: {updated} row(s) updated, M3U rewritten from actual files.',
            'updated': updated,
            'm3u_updated': m3u_updated,
        })
    except Exception as e:
        logger.exception("Admin music sync-from-disk failed: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


# ----- Admin YouTube TV download (parallel to music; feeds Liquidsoap video/videolist.m3u) -----
_tv_download_status = {
    'status': 'idle',
    'step': None,
    'message': '',
    'error': None,
    'url': '',
    'started_at': None,
    'completed_at': None,
}
_tv_download_lock = threading.Lock()


def _set_tv_download_status(status, message='', error=None, url=None, completed=False, step=None):
    with _tv_download_lock:
        _tv_download_status['status'] = status
        _tv_download_status['message'] = message
        _tv_download_status['error'] = error
        if step is not None:
            _tv_download_status['step'] = step
        if url is not None:
            _tv_download_status['url'] = url
        if status == 'downloading':
            _tv_download_status['started_at'] = datetime.now(timezone.utc).isoformat()
            _tv_download_status['completed_at'] = None
        if completed:
            _tv_download_status['completed_at'] = datetime.now(timezone.utc).isoformat()


def _get_tv_download_status():
    with _tv_download_lock:
        return dict(_tv_download_status)


@book_bp.route('/admin/tv')
@login_required
def admin_tv():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    return render_template('book_platform/admin_tv.html')


@book_bp.route('/admin/tv/status')
@login_required
def admin_tv_status():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403
    return jsonify(_get_tv_download_status())


@book_bp.route('/admin/tv/download', methods=['POST'])
@login_required
def admin_tv_download():
    """yt-dlp → MP4 in glconnect/static/ytautovid → DB → merge video/videolist.m3u for HLS TV."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    data = request.get_json() or request.form
    url = (data.get('url') or data.get('youtube_url') or '').strip()
    if not url:
        return jsonify({'success': False, 'error': 'YouTube URL is required'}), 400
    if 'youtube.com' not in url and 'youtu.be' not in url:
        return jsonify({'success': False, 'error': 'Please provide a valid YouTube URL'}), 400
    import shutil
    if not shutil.which('yt-dlp'):
        return jsonify({
            'success': False,
            'error': 'yt-dlp is not installed. Install it to enable YouTube TV downloads.',
        }), 400

    _set_tv_download_status('downloading', 'Starting…', url=url, step='download')

    app = current_app._get_current_object()

    def run_pipeline():
        with app.app_context():
            current_step = 'download'
            try:
                from glconnect import pipeline as pipeline_mod
                from glconnect.pipeline import (
                    VideoDownloader,
                    MusicFileRenamer,
                    PlaylistIngestion,
                    sync_tv_videolist_from_db,
                )
                glconnect_dir = os.path.dirname(os.path.abspath(pipeline_mod.__file__))
                project_root = os.path.dirname(glconnect_dir)
                output_folder = os.path.normpath(
                    os.path.join(glconnect_dir, 'static', 'ytautovid')
                )
                os.makedirs(output_folder, exist_ok=True)

                # Pick up any MP4s already on disk (skipped re-download, manual copy, wrong DB path).
                try:
                    n_pre = sync_tv_videolist_from_db()
                    logger.info('TV playlist pre-sync before yt-dlp: %s path(s)', n_pre)
                except Exception as pre_exc:
                    logger.warning('TV playlist pre-sync failed (continuing): %s', pre_exc)

                current_step = 'download'
                _set_tv_download_status(
                    'downloading',
                    'Downloading video with yt-dlp (may take several minutes)…',
                    url=url,
                    step=current_step,
                )
                downloader = VideoDownloader(playlist_url=url, output_folder=output_folder)
                downloader.download_and_convert()
                _set_tv_download_status('downloading', 'Download finished.', url=url, step=current_step)

                current_step = 'rename'
                _set_tv_download_status('renaming', 'Renaming files…', url=url, step=current_step)
                MusicFileRenamer.clean_music_names(output_folder)
                _set_tv_download_status('renaming', 'Renaming finished.', url=url, step=current_step)

                current_step = 'ingest'
                _set_tv_download_status(
                    'ingesting',
                    'Writing videolist.m3u from disk (static/ytautovid + extra + DB)…',
                    url=url,
                    step=current_step,
                )
                n_disk = sync_tv_videolist_from_db()
                _set_tv_download_status(
                    'ingesting',
                    f'Playlist pass 1: {n_disk} path(s) in videolist.m3u.',
                    url=url,
                    step=current_step,
                )

                _set_tv_download_status('ingesting', 'Saving to database…', url=url, step=current_step)
                added, unchanged = PlaylistIngestion.ingest_videos_from_folder(
                    output_folder, source_url=url
                )
                _set_tv_download_status(
                    'ingesting',
                    (
                        f'DB reconciled: {added} new or updated row(s), {unchanged} unchanged.'
                        if added > 0
                        else f'DB unchanged ({unchanged} file(s) already catalogued).'
                    ),
                    url=url,
                    step=current_step,
                )

                current_step = 'playlist'
                _set_tv_download_status(
                    'ingesting',
                    'Refreshing videolist.m3u after DB ingest…',
                    url=url,
                    step='playlist',
                )
                npaths = sync_tv_videolist_from_db()
                _set_tv_download_status(
                    'ingesting',
                    f'Playlist pass 2: {npaths} path(s) in videolist.m3u.',
                    url=url,
                    step='playlist',
                )

                if added > 0:
                    _set_tv_download_status(
                        'completed',
                        f'Done. {added} DB change(s); videolist.m3u has {npaths} path(s). Liquidsoap reloads if watch mode is on.',
                        url=url,
                        completed=True,
                        step=None,
                    )
                    logger.info(
                        "Admin TV download finished: %s DB change(s), %s playlist paths",
                        added,
                        npaths,
                    )
                else:
                    _set_tv_download_status(
                        'completed',
                        f'Completed. No DB updates needed; videolist.m3u refreshed ({npaths} path(s)).',
                        url=url,
                        completed=True,
                        step=None,
                    )
            except Exception as e:
                logger.exception("Admin TV download failed at step %s: %s", current_step, e)
                try:
                    from glconnect.pipeline import sync_tv_videolist_from_db as _sync_tv
                    n_rec = _sync_tv()
                    logger.info(
                        "TV playlist refreshed after error: %s path(s) in videolist.m3u",
                        n_rec,
                    )
                except Exception:
                    logger.exception("TV playlist sync after failure failed")
                step_label = {
                    'download': 'Download',
                    'rename': 'Renaming',
                    'ingest': 'Database / playlist',
                    'playlist': 'Playlist',
                }.get(current_step, current_step)
                _set_tv_download_status(
                    'failed',
                    f'{step_label} failed.',
                    error=str(e),
                    url=url,
                    completed=True,
                    step=current_step,
                )

    threading.Thread(target=run_pipeline, daemon=True).start()
    return jsonify({
        'success': True,
        'message': 'TV download started.',
        'status': _get_tv_download_status(),
    })


@book_bp.route('/admin/tv/sync-playlist', methods=['POST'])
@login_required
def admin_tv_sync_playlist():
    """Rewrite video/videolist.m3u from videolist_extra.m3u + downloaded_videos + orphan *.mp4 on disk."""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin privileges required'}), 403
    try:
        from glconnect.pipeline import sync_tv_videolist_from_db
        n = sync_tv_videolist_from_db()
        return jsonify({
            'success': True,
            'message': f'TV playlist updated: {n} path(s) in videolist.m3u.',
            'paths': n,
        })
    except Exception as e:
        logger.exception("Admin TV sync-playlist failed: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500


@book_bp.route('/admin/stripe-diagnostics', methods=['GET'])
@login_required
def admin_stripe_diagnostics():
    """
    Admin-only: whether this running app process sees a valid Stripe *secret* key (sk_...).
    No key material is returned — only categories. Use to debug 'Payment processing is not configured'.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin privileges required'}), 403
    from glconnect.stripe_utils import (
        normalize_stripe_secret_candidate,
        process_env_has_stripe_secret,
        stripe_secret_configured,
        detect_server_outbound_ip,
        probe_stripe_server_key,
    )

    def classify(v):
        v = normalize_stripe_secret_candidate(v)
        if not v:
            return {'present': False, 'kind': 'empty'}
        if v.startswith('sk_live'):
            return {'present': True, 'kind': 'secret_live'}
        if v.startswith('sk_test'):
            return {'present': True, 'kind': 'secret_test'}
        if v.startswith('pk_'):
            return {'present': True, 'kind': 'publishable_only_server_needs_sk'}
        return {'present': True, 'kind': 'unrecognized'}

    cfg = current_app.config
    sk_meta = classify(cfg.get('STRIPE_SECRET_KEY'))
    api_meta = classify(cfg.get('STRIPE_API_KEY'))
    app_config_has_secret = sk_meta.get('kind') in ('secret_live', 'secret_test') or api_meta.get('kind') in (
        'secret_live',
        'secret_test',
    )
    # Env-only aliases (not duplicated into app.config)
    env_extra = {
        'STRIPE_KEY': classify(os.getenv('STRIPE_KEY')),
        'STRIPE_PRIVATE_KEY': classify(os.getenv('STRIPE_PRIVATE_KEY')),
    }
    outbound_ip = detect_server_outbound_ip()
    stripe_probe = probe_stripe_server_key(current_app)
    ip_restricted = (
        not stripe_probe.get('ok')
        and (stripe_probe.get('details') or {}).get('operator_error_code') == 'STRIPE_KEY_IP_RESTRICTED'
    )
    return jsonify({
        'STRIPE_SECRET_KEY': sk_meta,
        'STRIPE_API_KEY': api_meta,
        'env_keys_extra': env_extra,
        'app_config_has_secret': app_config_has_secret,
        'process_env_has_sk': process_env_has_stripe_secret(),
        'ready_for_checkout': stripe_secret_configured(current_app),
        'outbound_ip': outbound_ip,
        'stripe_key_probe': stripe_probe,
        'stripe_ip_allowlist_ok': stripe_probe.get('ok') is True,
        'stripe_ip_restricted': ip_restricted,
        'hint': (
            'Add outbound_ip to your Stripe secret key IP allowlist (Dashboard → Developers → API keys → '
            'Manage IP restrictions). Use the host egress IP below — not glc.cool’s public address. '
            'After updating Stripe, retry patron checkout.'
            if ip_restricted
            else (
                'If app_config_has_secret is false but process_env_has_sk is true, keys may exist only in os.environ. '
                'If ready_for_checkout is false, set a *secret* key (sk_...) in the production host environment '
                '(e.g. STRIPE_SECRET_KEY) and restart.'
            )
        ),
    })


@book_bp.route('/podcasts/<int:podcast_id>/play')
@login_required
def play_podcast(podcast_id):
    """Display podcast player page with HTML5 video/audio element"""
    from glconnect.models import PodcastSubmission
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    
    # Allow access if approved, if user owns it, or if user is admin (for reviewing pending podcasts)
    if not podcast.is_approved() and podcast.user_id != current_user.user_id and current_user.role != 'admin':
        flash('This podcast is not available', 'error')
        return redirect(url_for('book_platform.my_podcasts'))
    
    # Generate the URL to serve the file (using a separate route for actual file serving)
    media_url = url_for('book_platform.serve_podcast_file', podcast_id=podcast_id)
    
    return render_template('book_platform/podcast_player.html', 
                         podcast=podcast, 
                         media_url=media_url)

@book_bp.route('/podcasts/<int:podcast_id>/file')
@login_required
def serve_podcast_file(podcast_id):
    """Serve the actual podcast file with proper headers for streaming"""
    from glconnect.models import PodcastSubmission
    import mimetypes
    
    podcast = PodcastSubmission.query.get_or_404(podcast_id)
    
    # Allow access if approved, if user owns it, or if user is admin
    if not podcast.is_approved() and podcast.user_id != current_user.user_id and current_user.role != 'admin':
        return abort(403)
    
    # Try to resolve the file path - handle both absolute and relative paths
    file_path = podcast.file_path
    filename = os.path.basename(file_path) if file_path else None
    
    # The correct path where files should be stored
    correct_path = os.path.join(current_app.root_path, 'static', 'podcasts', filename) if filename else None
    
    # Try multiple possible locations in order of likelihood
    possible_paths = []
    
    # 1. First try the stored path (might be correct if file exists there)
    if file_path and os.path.exists(file_path):
        possible_paths.append(file_path)
    
    # 2. Try the correct path (where files should be: glconnect/static/podcasts/)
    if correct_path and os.path.exists(correct_path):
        possible_paths.append(correct_path)
    
    # 3. Try old wrong path formats (for backwards compatibility)
    if filename:
        old_paths = [
            os.path.join(current_app.root_path, 'uploads', 'podcasts', filename),
            os.path.join(os.path.dirname(current_app.root_path), 'uploads', 'podcasts', filename),
            os.path.join(current_app.root_path, 'static', 'uploads', 'podcasts', filename),
        ]
        for old_path in old_paths:
            if old_path not in possible_paths and os.path.exists(old_path):
                possible_paths.append(old_path)
    
    # Use the first path that exists
    if possible_paths:
        file_path = possible_paths[0]
        if len(possible_paths) > 1:
            logger.info(f"Found podcast file at: {file_path} (tried {len(possible_paths)} locations)")
    else:
        logger.error(f"Podcast file not found. Stored path: {podcast.file_path}, Expected: {correct_path}")
        return abort(404)
    
    # Determine MIME type based on file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    mime_type_map = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.avi': 'video/x-msvideo',
        '.mkv': 'video/x-matroska'
    }
    
    mimetype = mime_type_map.get(file_ext)
    if not mimetype:
        mimetype, _ = mimetypes.guess_type(file_path)
        if not mimetype:
            mimetype = 'audio/mpeg' if podcast.file_type == 'audio' else 'video/mp4'
    
    # iOS Safari requires Range request support for media streaming - without it,
    # video/audio may fail to play or have no sound on mobile
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    
    if range_header:
        # Parse Range header (format: bytes=start-end or bytes=-suffix for last N bytes)
        range_match = re.search(r'bytes=(\d*)-(\d*)', range_header)
        if range_match:
            start_str, end_str = range_match.groups()
            if start_str:
                start = int(start_str)
                end = int(end_str) if end_str else file_size - 1
            else:
                # Suffix range: bytes=-500 means last 500 bytes
                suffix = int(end_str) if end_str else 0
                start = max(0, file_size - suffix)
                end = file_size - 1
            end = min(end, file_size - 1)
            if start >= file_size or start > end:
                return Response(status=416)  # Range Not Satisfiable
            chunk_size = end - start + 1
            with open(file_path, 'rb') as f:
                f.seek(start)
                chunk = f.read(chunk_size)
            response = Response(chunk, status=206, mimetype=mimetype)
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(chunk_size)
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
    
    # No Range header: send full file
    response = send_file(file_path, mimetype=mimetype, as_attachment=False)
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@book_bp.route('/podcasts/library')
@login_required
def podcast_library():
    """Public-facing library of approved podcasts"""
    from glconnect.models import PodcastSubmission, User
    
    podcasts = PodcastSubmission.query.filter_by(status='approved').order_by(
        PodcastSubmission.reviewed_at.desc().nullslast(),
        PodcastSubmission.submitted_at.desc()
    ).all()
    
    return render_template('book_platform/podcast_library.html', podcasts=podcasts)
