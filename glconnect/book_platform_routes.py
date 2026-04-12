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
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from mailtrap import MailtrapClient, Mail, Address

# Import models
from glconnect.models import db, User, Writer
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookChapter, BookCollaboration, 
    CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
    ChapterSuggestion, BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification,
    BookStatus, CollaborationRole, InvitationStatus, CommentStatus, TransactionStatus,
    AudioGenerationTask, AudiobookChapter, AccreditedReviewer, BookReview, InvestmentCampaign, BookInvestment,
    AuthorCampaignPayoutRequest,
    RevenueDistribution, ReviewerEarning, InvestmentPayout, PayoutRequest, ReviewerPayoutRequest, AuthorSalesPayoutRequest, RefundRequest, ReviewerStatus, ReviewerLevel,
    ReviewStatus, ReviewRequest, ReviewRequestStatus, InvestmentStatus, CampaignStatus, DistributionType
)

# Import additional modules
from glconnect.forms import DigitalBookUploadForm, ReviewerRegistrationForm, BookReviewForm, InvestmentCampaignForm, InvestmentForm
from glconnect.digital_book_processor import digital_book_processor
from glconnect.audiobook_text_segments import build_uploaded_book_audiobook_chapters
from glconnect.book_cover_ai import generate_book_cover_bytes
from glconnect.audio_book_generator import audio_book_generator
from glconnect.revenue_distribution_service import distribute_revenue
from glconnect.stripe_utils import init_stripe, get_webhook_secret
from glconnect.book_utils import is_book_published
import threading
from werkzeug.utils import secure_filename

# Create blueprint
book_bp = Blueprint('book_platform', __name__, url_prefix='/mybook')

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


def book_has_listing_cover(book):
    """Whether the book has a cover path or URL set for marketplace display."""
    if not book:
        return False
    c = getattr(book, 'cover_image', None)
    return bool(c and str(c).strip())


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
    """Get user profile - Writer profile is primary for Ink Studio"""
    if not current_user.is_authenticated:
        return None, None
    
    # Check for Writer profile first (primary users for Ink Studio)
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()
    if writer:
        return writer, 'writer'
    
    # Check for BookPlatformUser profile (legacy support)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if book_user:
        return book_user, 'book_platform'
    
    return None, None

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
    if not book.description or len(book.description.strip()) < 50:
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
        issues.append("Investment campaigns are only available for books created on the platform (with chapters), not for uploaded digital books.")
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

def writer_or_book_platform_required(f):
    """Decorator that requires Writer profile (primary) or BookPlatformUser profile (legacy) for Ink Studio access.
    Also allows freelancers to access with limited features."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('routes1.login'))
        
        # Allow freelancers to access with a temporary profile
        if current_user.role == 'freelancer':
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
            # If no profile exists, redirect to writer profile creation
            flash('You need a Writer profile to access Ink Studio', 'warning')
            return redirect(url_for('writer.writer_profile'))
        
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
            return redirect(url_for('routes1.login'))
        
        # Check if user has Ink Studio profile
        book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_user:
            return redirect(url_for('book_platform.setup_profile'))
        
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
        
        # Check if user is author or collaborator
        book = BookProject.query.get_or_404(book_id)
        collaboration = BookCollaboration.query.filter_by(
            book_project_id=book_id, 
            collaborator_id=book_user.id,
            is_active=True
        ).first()
        
        if book.author_id != book_user.id and not collaboration:
            return jsonify({'error': 'Access denied'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Ink Studio access route - handles redirects based on user type
@book_bp.route('/ink-studio')
def ink_studio_access():
    """Ink Studio access point - redirects to login if not authenticated, otherwise redirects based on role."""
    # If not authenticated, redirect to login (which has register link)
    if not current_user.is_authenticated:
        return redirect(url_for('routes1.login', next=url_for('book_platform.ink_studio_access')))

    # User is authenticated - redirect based on role
    from glconnect.models import Writer
    from glconnect.book_platform_models import BookPlatformUser
    
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    user_role = getattr(current_user, 'role', None)
    
    # Artist users → music dashboard
    if user_role == 'artist':
        return redirect(url_for('book_platform.music_dashboard'))
    
    # Author users → writer/profile if no profile, else /mybook dashboard
    elif user_role == 'author':
        if not writer and not book_user:
            return redirect('https://glc.cool/writer/profile')
        return redirect(url_for('book_platform.dashboard'))
    
    # Freelancer users → blogs
    elif user_role == 'freelancer':
        return redirect(url_for('blog.blogs'))
    
    # Blogger users → blogs
    elif user_role == 'blogger':
        return redirect(url_for('blog.blogs'))
    
    # All other users → content hub
    else:
        return redirect(url_for('book_platform.content_hub'))

# Main dashboard route
@book_bp.route('/')
@writer_or_book_platform_required
def dashboard(user_profile, profile_type):
    """Main Ink Studio dashboard - Writer profiles are primary users, freelancers have limited access"""
    
    # Handle freelancers separately - they get limited dashboard access
    if profile_type == 'freelancer':
        # Freelancers get a simplified dashboard focused on freelancing features
        from glconnect.models import Post
        # Get freelancer's stories
        freelancer_stories = Post.query.filter_by(user_id=current_user.user_id).order_by(Post.date_posted.desc()).limit(10).all()
        
        return render_template('book_platform/dashboard.html',
                             authored_books=[],
                             collaborations=[],
                             notifications=[],
                             user_profile=user_profile,
                             profile_type=profile_type,
                             is_author=False,
                             investment_campaigns=[],
                             review_requests=[],
                             user_reviewer_profile=None,
                             user_investments=[],
                             freelancer_stories=freelancer_stories,
                             is_freelancer=True)
    
    if profile_type == 'writer':
        # For writers, create a temporary BookPlatformUser-like object
        class WriterAsBookUser:
            def __init__(self, writer):
                self.id = writer.writer_id
                self.user_id = writer.user_id
                self.pen_name = writer.writer_name
                self.bio = writer.bio
                self.profile_picture = writer.profile_picture
        
        book_user = WriterAsBookUser(user_profile)
        
        # Use optimized database queries
        authored_books, collaborations, notifications = DatabaseOptimizer.get_dashboard_data(
            user_profile.user_id, 'writer'
        )[1:]  # Skip the first return value (book_user)
        
    else:
        # For BookPlatformUsers (legacy), use existing logic with eager loading
        # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
        from glconnect.book_platform_models import BookPlatformUser
        
        book_user = user_profile
        # Eager load author information to ensure fresh data from database
        authored_books = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).filter_by(author_id=book_user.id).all()
        collaborations = BookCollaboration.query.options(
            joinedload(BookCollaboration.book_project).joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).filter_by(
            collaborator_id=book_user.id, 
            is_active=True
        ).all()
        notifications = BookNotification.query.filter_by(
            user_id=book_user.id,
            is_read=False
        ).order_by(BookNotification.created_at.desc()).limit(5).all()
    
    # Determine if user is an author
    # Only users with 'author' role OR users who have actually authored books (but not excluded roles) are considered authors
    # Excluded roles should NEVER see author content, even if they have authored books
    excluded_roles = ['podcaster', 'freelancer', 'blogger', 'artist', 'other']
    has_authored_books = len(authored_books) > 0
    
    # User is considered an author only if:
    # 1. They have role 'author' AND have a writer/book_platform profile, OR
    # 2. They have actually authored books AND their role is NOT in excluded_roles
    # This ensures 'other' role users NEVER see author content, even if they have a writer profile
    if current_user.role in excluded_roles:
        # Excluded roles are NEVER authors, regardless of profile or books
        is_author = False
    elif current_user.role == 'author' and (profile_type == 'writer' or profile_type == 'book_platform'):
        # Users with 'author' role and writer/book_platform profile are authors
        is_author = True
    elif has_authored_books:
        # If they have authored books and role is not excluded, they're an author
        is_author = True
    else:
        # Default: not an author
        is_author = False
    
    # Get additional data for authors
    investment_campaigns = []
    review_requests = []
    if is_author:
        from glconnect.book_platform_models import InvestmentCampaign, BookReview, CampaignStatus, ReviewStatus
        author_id = get_profile_id(user_profile, profile_type)
        books_with_ids = [book.id for book in authored_books]
        if books_with_ids:
            investment_campaigns = InvestmentCampaign.query.filter(
                InvestmentCampaign.book_project_id.in_(books_with_ids)
            ).all()
            # Get books with pending review requests
            review_requests = BookReview.query.filter(
                BookReview.book_project_id.in_(books_with_ids),
                BookReview.status == ReviewStatus.SUBMITTED
            ).all()
    
    # Get data for regular users (reviewers/investors)
    user_reviewer_profile = None
    user_investments = []
    if not is_author:
        from glconnect.book_platform_models import AccreditedReviewer, BookInvestment, ReviewerStatus, InvestmentStatus
        user_reviewer_profile = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
        user_investments = BookInvestment.query.filter_by(
            investor_id=get_profile_id(user_profile, profile_type)
        ).filter(BookInvestment.status.in_([InvestmentStatus.ACTIVE, InvestmentStatus.CONFIRMED])).limit(5).all()
    
    return render_template('book_platform/dashboard.html', 
                         authored_books=authored_books,
                         collaborations=collaborations,
                         notifications=notifications,
                         user_profile=book_user,
                         profile_type=profile_type,
                         is_author=is_author,
                         investment_campaigns=investment_campaigns,
                         review_requests=review_requests,
                         user_reviewer_profile=user_reviewer_profile,
                         user_investments=user_investments,
                         freelancer_stories=[],
                         is_freelancer=False)


@book_bp.route('/my-listings')
@writer_or_book_platform_required
def author_my_listings(user_profile, profile_type):
    """Author hub: marketplace listings, sales, and links to manage each title."""
    if profile_type == 'freelancer':
        flash('This page is for authors with book listings.', 'info')
        return redirect(url_for('book_platform.dashboard'))

    author_id = get_profile_id(user_profile, profile_type)
    if not author_id:
        flash('Complete your Ink Studio profile to manage listings.', 'warning')
        return redirect(url_for('book_platform.setup_profile'))

    from sqlalchemy import func as sa_func
    from glconnect.book_utils import is_book_published

    books = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).filter_by(author_id=author_id).order_by(
        BookProject.updated_at.desc(),
        BookProject.created_at.desc(),
    ).all()

    book_ids = [b.id for b in books]
    sale_by_book = {}
    if book_ids:
        sale_rows = db.session.query(
            BookSale.book_project_id,
            sa_func.count(BookSale.id),
            sa_func.coalesce(sa_func.sum(BookSale.net_amount), 0.0),
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
            sa_func.coalesce(sa_func.sum(BookAnalytics.views), 0),
            sa_func.coalesce(sa_func.sum(BookAnalytics.downloads), 0),
            sa_func.coalesce(sa_func.sum(BookAnalytics.purchases), 0),
        ).filter(
            BookAnalytics.book_project_id.in_(book_ids)
        ).group_by(BookAnalytics.book_project_id).all()
        for row in analytics_rows:
            analytics_by_book[row[0]] = {
                'views': int(row[1] or 0),
                'downloads': int(row[2] or 0),
                'purchases': int(row[3] or 0),
            }

    listing_rows = []
    for book in books:
        s = sale_by_book.get(book.id, {'completed_units': 0, 'author_net': 0.0})
        a = analytics_by_book.get(book.id, {'views': 0, 'downloads': 0, 'purchases': 0})
        listing_rows.append({
            'book': book,
            'live': is_book_published(book),
            'completed_sales': s['completed_units'],
            'author_earnings': s['author_net'],
            'agg_views': a['views'],
            'agg_downloads': a['downloads'],
            'agg_purchases': a['purchases'],
        })

    n_live = sum(1 for r in listing_rows if r['live'])
    total_units = sum(r['completed_sales'] for r in listing_rows)
    total_earnings = sum(r['author_earnings'] for r in listing_rows)

    return render_template(
        'book_platform/author_my_listings.html',
        listing_rows=listing_rows,
        summary_live=n_live,
        summary_total_books=len(listing_rows),
        summary_units=total_units,
        summary_earnings=total_earnings,
        marketplace_cover_url=_marketplace_cover_url,
    )


# Profile setup
@book_bp.route('/setup-profile', methods=['GET', 'POST'])
@login_required
def setup_profile():
    """Setup Ink Studio profile"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Check if user already has an Ink Studio profile
            existing_profile = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
            
            if existing_profile:
                # Update existing profile
                existing_profile.pen_name = data.get('pen_name')
                existing_profile.bio = data.get('bio')
                existing_profile.website = data.get('website')
                existing_profile.social_links = data.get('social_links', {})
                existing_profile.writing_experience = data.get('writing_experience')
                existing_profile.genres = data.get('genres', [])
                existing_profile.updated_at = datetime.now(timezone.utc)
            else:
                # Create new Ink Studio user profile
                book_user = BookPlatformUser(
                    user_id=current_user.user_id,
                    pen_name=data.get('pen_name'),
                    bio=data.get('bio'),
                    website=data.get('website'),
                    social_links=data.get('social_links', {}),
                    writing_experience=data.get('writing_experience'),
                    genres=data.get('genres', [])
                )
                db.session.add(book_user)
            
            db.session.commit()
            
            return jsonify({'success': True, 'redirect': url_for('book_platform.dashboard')})
            
        except Exception as e:
            db.session.rollback()
            print(f"Profile setup error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('book_platform/setup_profile.html')

# Book management routes
@book_bp.route('/books')
@writer_or_book_platform_required
def books(user_profile, profile_type):
    """List all user's books - Only accessible to authors (Writer profiles or users who have authored books)"""
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    
    # Get the correct author_id (BookPlatformUser.id for consistency)
    author_id = get_profile_id(user_profile, profile_type)
    
    # Check if user is actually an author
    # Writer profiles are always authors, but BookPlatformUsers must have authored books
    if profile_type != 'writer':
        authored_books_count = BookProject.query.filter_by(author_id=author_id).count()
        if authored_books_count == 0:
            flash('You need to be an author to access this page. Create a Writer profile or start writing your first book.', 'warning')
            return redirect(url_for('book_platform.dashboard'))
    
    # Query books with eager loading of author information
    from glconnect.book_platform_models import InvestmentCampaign
    books = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).filter_by(author_id=author_id).all()
    
    # Get investment campaigns for books that have them (to avoid relationship issues)
    book_campaigns = {}
    for book in books:
        if book.has_investment_campaign:
            campaign = InvestmentCampaign.query.filter_by(book_project_id=book.id).first()
            if campaign:
                book_campaigns[book.id] = campaign
    
    # Calculate investment readiness for each book
    books_with_readiness = []
    for book in books:
        try:
            # The investment_campaign relationship uses uselist=False, so it should always be
            # a single object or None. If there's a data inconsistency, we'll handle it in the template.
            readiness = check_investment_readiness(book)
            books_with_readiness.append({
                'book': book,
                'investment_readiness': readiness
            })
        except Exception as e:
            logger.error(f"Error processing book {book.id} for investment readiness: {str(e)}", exc_info=True)
            # Add book with default readiness to prevent complete failure
            books_with_readiness.append({
                'book': book,
                'investment_readiness': {
                    'is_ready': False,
                    'issues': [f'Error checking readiness: {str(e)}'],
                    'chapter_count': 0,
                    'word_count': 0
                }
            })
    
    return render_template('book_platform/books.html', 
                         books_with_readiness=books_with_readiness,
                         book_campaigns=book_campaigns)

@book_bp.route('/books/create', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_book(user_profile, profile_type):
    """Create a new book project - Writer profiles are primary users"""
    # Note: We allow access here to enable first-time book creation
    # The dashboard template will hide the "Start Writing" button for non-authors
    # This allows Writer profiles to create books immediately
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
        desc_val = (request.form.get('description') or '').strip()
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
            ai_res = generate_book_cover_bytes(title, desc_val, genre_val, art_brief)
            if not ai_res.get('success') or not ai_res.get('image_bytes'):
                return jsonify({
                    'success': False,
                    'error': ai_res.get('error') or 'Could not generate an AI cover. Upload an image or try again.',
                }), 400
            unique_cover_filename = f"ai_cover_{uuid.uuid4().hex[:10]}.png"
            abs_cover = os.path.join(covers_dir, unique_cover_filename)
            with open(abs_cover, 'wb') as out:
                out.write(ai_res['image_bytes'])
            cover_rel = f"book_covers/{unique_cover_filename}"
        else:
            return jsonify({
                'success': False,
                'error': 'Upload a cover image or enable “Generate cover with AI”.',
            }), 400

        book = BookProject(
            title=title,
            description=(request.form.get('description') or '').strip() or None,
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
            joinedload(BookProject.chapters)  # Also eager load chapters to avoid lazy loading issues
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
    
    try:
        return render_template('book_platform/view_book.html', 
                             book=book, 
                             chapters=chapters,
                             collaborations=collaborations,
                             is_author=is_author,
                             is_collaborator=is_collaborator,
                             investment_readiness=investment_readiness,
                             investment_campaign=campaign)
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
            
            # Debug logging for publish checkbox
            logger.debug(f"Edit book {book_id} - Form data keys: {list(data.keys())}")
            logger.debug(f"Edit book {book_id} - is_published value: {data.get('is_published', 'NOT PRESENT')}")
            
            # Update book fields
            book.title = data['title']
            book.description = data.get('description', '')
            book.genre = data.get('genre', '')
            book.language = data.get('language', '')
            book.target_audience = data.get('target_audience', '')
            book.price = float(data.get('price', 0)) if data.get('price') else None
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
            book.allow_collaboration = data.get('allow_collaboration') == 'on' or data.get('allow_collaboration') == True
            book.updated_at = datetime.now(timezone.utc)
            
            # Handle publishing status - separate for digital book and audiobook
            if book.digital_file_path:
                # For uploaded digital books, handle separate publishing
                publish_digital = data.get('publish_digital_book') == 'on'
                publish_audiobook = data.get('publish_audiobook') == 'on'
                
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
                    if not book.has_audiobook:
                        return jsonify({
                            'success': False, 
                            'error': 'Audiobook must be generated before it can be published.'
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
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'redirect': url_for('book_platform.view_book', book_id=book_id)
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Book edit error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return render_template('book_platform/edit_book.html', book=book)

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
            
            chapter = BookChapter(
                title=data['title'],
                content=content,
                summary=data.get('summary', ''),
                chapter_number=chapter_number,
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
        flash('This chapter is published and cannot be edited. Unpublish it first to make changes.', 'warning')
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
            
            # Update chapter fields
            chapter.title = data.get('title', chapter.title)
            chapter.content = data.get('content', chapter.content)
            chapter.summary = data.get('summary', chapter.summary)
            
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
            
            # Create version snapshot for change tracking
            try:
                # Get the current user's BookPlatformUser or Writer profile ID
                book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
                if book_user:
                    # Get or create a BookVersion for this book
                    book_version = BookVersion.query.filter_by(book_project_id=book_id, is_current=True).first()
                    if not book_version:
                        # Create a new book version if none exists
                        existing_book_versions = BookVersion.query.filter_by(book_project_id=book_id).count()
                        book_version = BookVersion(
                            book_project_id=book_id,
                            version_number=f"{existing_book_versions + 1}.0",
                            title=book.title,
                            word_count=book.word_count or 0,
                            is_current=True,
                            created_by_id=book_user.id
                        )
                        db.session.add(book_version)
                        db.session.flush()  # Flush to get book_version.id
                        # Set all other book versions to not current
                        BookVersion.query.filter_by(book_project_id=book_id).filter(BookVersion.id != book_version.id).update({'is_current': False})
                    
                    # Get next version number
                    existing_versions = ChapterVersion.query.filter_by(chapter_id=chapter_id).count()
                    version_number = f"{existing_versions + 1}.0"
                    
                    # Set all other versions to not current BEFORE creating new one
                    ChapterVersion.query.filter_by(chapter_id=chapter_id).update({'is_current': False})
                    
                    # Create version
                    version = ChapterVersion(
                        chapter_id=chapter_id,
                        book_version_id=book_version.id,
                        version_number=version_number,
                        title=chapter.title,
                        content=chapter.content,
                        word_count=chapter.word_count,
                        is_current=True,
                        created_by_id=book_user.id
                    )
                    db.session.add(version)
            except Exception as e:
                logging.error(f"Version tracking error: {e}", exc_info=True)
                # Don't fail the edit if version tracking fails
            
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
    return render_template('book_platform/edit_chapter.html', 
                         book=book, 
                         chapter=chapter)

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

@book_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@writer_or_book_platform_required
def delete_book(book_id, user_profile, profile_type):
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
            return jsonify({'error': 'Book not found'}), 404

        # Admins can delete any book; others must be the author
        if current_user.role != 'admin':
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
        
        # 14. Delete all chapters (cascade should handle this, but being explicit)
        BookChapter.query.filter_by(book_project_id=book_id).delete()
        
        # 15. Finally delete the book
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Book deleted successfully'})
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error deleting book {book_id}: {str(e)}\n{error_trace}")
        return jsonify({'error': f'Failed to delete book: {str(e)}'}), 500

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
    voice_name = data.get('voice_name', 'en-US-Standard-A')
    
    if not voice_name:
        return jsonify({'success': False, 'error': 'Voice name is required'}), 400
    
    try:
        full_text = ""
        
        # Check if this is an uploaded digital book
        if book.digital_file_path:
            # Extract text from uploaded digital file
            digital_file_path = os.path.join(current_app.root_path, 'static', book.digital_file_path)
            
            if not os.path.exists(digital_file_path):
                return jsonify({'success': False, 'error': 'Digital book file not found. Please re-upload the book.'}), 400
            
            # Get file type from book model or infer from extension
            file_type = book.digital_file_type or os.path.splitext(digital_file_path)[1].lstrip('.')
            
            # Extract text from digital file
            extraction_result = digital_book_processor.extract_text(digital_file_path, file_type)
            
            if not extraction_result['success']:
                return jsonify({'success': False, 'error': f'Failed to extract text from digital book: {extraction_result.get("error", "Unknown error")}'}), 400
            
            full_text = extraction_result.get('text', '')
            
            if not full_text.strip():
                return jsonify({'success': False, 'error': 'No text content found in the uploaded digital book file.'}), 400
        else:
            # For books created in the platform, extract text from published chapters
            # First check if there are any chapters at all
            all_chapters = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number).all()
            
            if not all_chapters:
                return jsonify({
                    'success': False, 
                    'error': 'No chapters found. Please create at least one chapter before generating an audiobook.'
                }), 400
            
            # Check for published chapters first
            chapters = [ch for ch in all_chapters if ch.is_published]
            
            # If no published chapters but book is published and chapters have content, use those chapters
            if not chapters:
                # Check if book is published and chapters have content
                chapters_with_content = [ch for ch in all_chapters if (ch.content or ch.summary)]
                
                if is_book_published(book) and chapters_with_content:
                    # Use chapters with content if book is published (they're effectively published)
                    logger.info(f"Book {book_id} is published but chapters not individually marked. Using chapters with content.")
                    chapters = chapters_with_content
                else:
                    # Get list of unpublished chapters with content for better error message
                    unpublished_with_content = [ch for ch in all_chapters if not ch.is_published and (ch.content or ch.summary)]
                    unpublished_count = len(unpublished_with_content)
                    total_unpublished = len([ch for ch in all_chapters if not ch.is_published])
                    
                    error_msg = f'No published chapters found. You have {len(all_chapters)} chapter(s) total, but none are published. '
                    if unpublished_with_content:
                        error_msg += f'You have {unpublished_count} unpublished chapter(s) with content. '
                    error_msg += 'Please go to each chapter and check the "Publish this chapter" checkbox before generating an audiobook.'
                    
                    logger.warning(f"Book {book_id}: {len(all_chapters)} chapters found, {total_unpublished} unpublished, {len(chapters)} published")
                    
                    return jsonify({'success': False, 'error': error_msg}), 400
            
            # Build per-chapter data for chapter-based audiobook (listeners can pick any chapter)
            chapters_for_audio = []
            for chapter in chapters:
                chapter_text = ""
                chapter_text += f"Chapter {chapter.chapter_number}: {chapter.title}\n\n"
                if chapter.summary:
                    import re
                    clean_summary = re.sub(r'<[^>]+>', '', chapter.summary)
                    clean_summary = re.sub(r'\s+', ' ', clean_summary).strip()
                    if clean_summary:
                        chapter_text += f"Summary: {clean_summary}\n\n"
                if chapter.content:
                    import re
                    clean_content = re.sub(r'<[^>]+>', '', chapter.content)
                    clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                    if clean_content:
                        chapter_text += f"{clean_content}\n\n"
                if chapter_text.strip():
                    chapters_for_audio.append({
                        'title': f"Chapter {chapter.chapter_number}: {chapter.title}",
                        'text': chapter_text,
                        'chapter_number': chapter.chapter_number,
                        'book_chapter_id': chapter.id
                    })
                    full_text += chapter_text
            
            if not full_text.strip():
                return jsonify({
                    'success': False, 
                    'error': 'Published chapters found but they contain no text content. Please add content to your chapters before generating an audiobook.'
                }), 400
        
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
        # Per-chapter audio: platform books use real chapters; uploads use detected headings or word-based parts
        if not book.digital_file_path:
            chapters_for_audio_thread = chapters_for_audio
        else:
            chapters_for_audio_thread = build_uploaded_book_audiobook_chapters(full_text)
        
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
    """Get available English voices for audiobook generation (for upload page)"""
    try:
        result = audio_book_generator.get_available_voices(language_filter='en')
        
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
    """Get available English voices for audiobook generation"""
    try:
        result = audio_book_generator.get_available_voices(language_filter='en')
        
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
    
    # Update chapter with suggested changes
    chapter = suggestion.chapter
    
    # Save current version before applying suggestion
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
- If you don't have an account yet, you'll be prompted to create one when you click the link
- After logging in, you'll need to set up your Ink Studio profile (a quick one-time setup) to accept the invitation and start collaborating

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

@book_bp.route('/invitations/<string:invitation_uuid>')
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
            return redirect(url_for('login'))
        
        # Check if user has Ink Studio profile
        book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_user:
            return redirect(url_for('book_platform.setup_profile'))
        
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
    
    return render_template('book_platform/accept_invitation.html', invitation=invitation)

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
def marketplace():
    """Browse published books in the marketplace (anonymous or signed-in)."""
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
        # Authors can list finished digital/audio-ready titles without writing in Ink Studio (same flow as /upload-digital-book)
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
def api_marketplace_book_detail(book_id):
    """JSON detail for marketplace modal / future PDP (published books only)."""
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
            'formats': {
                'digital': bool(book.digital_book_published and book.digital_file_path),
                'audiobook': bool(book.audiobook_published and book.has_audiobook),
            },
            'digital_file_type': (book.digital_file_type or '').upper() if book.digital_file_type else None,
            'audiobook_price': float(book.audiobook_price) if book.audiobook_price is not None else None,
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
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Check if book_user exists
    if not book_user:
        return jsonify({'error': 'Book platform user profile not found'}), 404
    
    # Only author can publish
    if book.author_id != book_user.id:
        return jsonify({'error': 'Only the author can publish the book'}), 403
    
    # Validate book is ready for publishing
    if not book.price or book.price <= 0:
        return jsonify({'error': 'Please set a price before publishing'}), 400
    if not book_has_listing_cover(book):
        return jsonify({'error': 'Please add a cover image before publishing to the marketplace.'}), 400

    book.status = BookStatus.PUBLISHED
    book.published_at = datetime.now(timezone.utc)
    
    # Mark investment campaign as FUNDED when book is published (investments stop at publication)
    if book.investment_campaign and book.investment_campaign.status == CampaignStatus.ACTIVE:
        book.investment_campaign.status = CampaignStatus.FUNDED
        if not book.investment_campaign.funded_at:
            book.investment_campaign.funded_at = datetime.now(timezone.utc)
    
    db.session.commit()
    
    return jsonify({'success': True})

@book_bp.route('/books/<int:book_id>/unpublish', methods=['POST'])
@writer_or_book_platform_required
def unpublish_book(book_id, user_profile, profile_type):
    """Unpublish a book from marketplace (change status to DRAFT)"""
    book = BookProject.query.get_or_404(book_id)
    
    # Get the correct author ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # Check if user has permission (author or admin)
    if book.author_id != author_id:
        # Check if user is admin using existing admin system
        if current_user.role != 'admin':
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
            BookChapter.query.filter_by(book_project_id=book_id).delete()
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
    """Admin panel to manage reviewer accreditation"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    
    status_filter = request.args.get('status', 'pending')
    
    query = AccreditedReviewer.query
    
    if status_filter == 'pending':
        query = query.filter_by(accreditation_status=ReviewerStatus.PENDING)
    elif status_filter == 'accredited':
        query = query.filter_by(accreditation_status=ReviewerStatus.ACCREDITED)
    elif status_filter == 'all':
        pass  # Show all
    
    reviewers = query.order_by(AccreditedReviewer.created_at.desc()).all()
    
    return render_template('book_platform/admin_reviewers.html', 
                         reviewers=reviewers,
                         status_filter=status_filter)

@book_bp.route('/admin/reviewers/<int:reviewer_id>/approve', methods=['POST'])
@login_required
def approve_reviewer(reviewer_id):
    """Approve a reviewer application"""
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        reviewer = AccreditedReviewer.query.get_or_404(reviewer_id)
        
        if reviewer.accreditation_status != ReviewerStatus.PENDING:
            return jsonify({
                'success': False, 
                'message': f'Reviewer is already {reviewer.accreditation_status.value}'
            }), 400
        
        # Approve the reviewer
        reviewer.accreditation_status = ReviewerStatus.ACCREDITED
        reviewer.accreditation_date = datetime.now(timezone.utc)
        # Set expiration to 1 year from now
        from datetime import timedelta
        reviewer.accreditation_expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        
        # Set initial level based on credentials (can be upgraded later)
        if reviewer.credentials and len(reviewer.credentials) > 200:
            reviewer.accreditation_level = ReviewerLevel.SILVER
        else:
            reviewer.accreditation_level = ReviewerLevel.BRONZE
        
        db.session.commit()
        
        logger.info(f"Reviewer {reviewer.reviewer_name} (ID: {reviewer_id}) approved by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Reviewer "{reviewer.reviewer_name}" has been approved and accredited.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving reviewer {reviewer_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error approving reviewer'}), 500

@book_bp.route('/admin/reviewers/<int:reviewer_id>/reject', methods=['POST'])
@login_required
def reject_reviewer(reviewer_id):
    """Reject a reviewer application"""
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        reviewer = AccreditedReviewer.query.get_or_404(reviewer_id)
        
        if reviewer.accreditation_status != ReviewerStatus.PENDING:
            return jsonify({
                'success': False, 
                'message': f'Reviewer is already {reviewer.accreditation_status.value}'
            }), 400
        
        # Get rejection reason from request
        rejection_reason = request.json.get('reason', '') if request.is_json else ''
        
        # Reject the reviewer (or revoke if already accredited)
        reviewer.accreditation_status = ReviewerStatus.REVOKED
        
        db.session.commit()
        
        logger.info(f"Reviewer {reviewer.reviewer_name} (ID: {reviewer_id}) rejected by admin {current_user.username}. Reason: {rejection_reason}")
        
        return jsonify({
            'success': True,
            'message': f'Reviewer application for "{reviewer.reviewer_name}" has been rejected.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting reviewer {reviewer_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error rejecting reviewer'}), 500

@book_bp.route('/admin/reviewers/<int:reviewer_id>/suspend', methods=['POST'])
@login_required
def suspend_reviewer(reviewer_id):
    """Suspend an accredited reviewer"""
    # Check if user is admin
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        reviewer = AccreditedReviewer.query.get_or_404(reviewer_id)
        
        if reviewer.accreditation_status != ReviewerStatus.ACCREDITED:
            return jsonify({
                'success': False, 
                'message': 'Can only suspend accredited reviewers'
            }), 400
        
        reviewer.accreditation_status = ReviewerStatus.SUSPENDED
        
        db.session.commit()
        
        logger.info(f"Reviewer {reviewer.reviewer_name} (ID: {reviewer_id}) suspended by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Reviewer "{reviewer.reviewer_name}" has been suspended.'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error suspending reviewer {reviewer_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': 'Error suspending reviewer'}), 500

@book_bp.route('/books/<int:book_id>/purchase', methods=['POST'])
@login_required
def purchase_book(book_id):
    """Purchase a book - accessible to all logged-in users, prevents self-purchase"""
    # Wrap entire function in try-except to ensure JSON responses
    try:
        # Get custom amount and purchase type from request
        request_data = request.get_json() or {}
        custom_amount = request_data.get('custom_amount')
        purchase_type = (request_data.get('purchase_type') or 'digital').lower()
        if purchase_type not in ('digital', 'audiobook', 'bundle'):
            purchase_type = 'digital'
        
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
        
        # Prevent self-purchase: Check if current user is the author
        # Get author's user_id from book.author (BookPlatformUser) -> user relationship
        try:
            if book.author:
                author_user_id = None
                # Try to get user_id from book.author.user_id (direct field)
                if hasattr(book.author, 'user_id'):
                    author_user_id = book.author.user_id
                # Fallback: try to get from book.author.user relationship
                elif hasattr(book.author, 'user') and book.author.user:
                    author_user_id = book.author.user.user_id
                
                if author_user_id and author_user_id == buyer_user_id:
                    return jsonify({'error': 'You cannot purchase your own book'}), 400
        except Exception as self_purchase_check_error:
            logger.warning(f"Error checking self-purchase: {self_purchase_check_error}, continuing anyway")
            # Continue with purchase if check fails (better to allow than block)
        
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
        if purchase_type == 'audiobook':
            if not book.has_audiobook or not book.audiobook_published:
                return jsonify({'error': 'This book does not have an audiobook available for purchase.'}), 400
            if not book.audiobook_price or book.audiobook_price <= 0:
                return jsonify({'error': 'Audiobook price is not set. Please contact the author.'}), 400
            base_price = book.audiobook_price
        elif purchase_type == 'bundle':
            if not book.has_audiobook or not book.audiobook_published:
                return jsonify({'error': 'Bundle requires an audiobook. This book does not have one available.'}), 400
            if not book.audiobook_price or book.audiobook_price <= 0:
                return jsonify({'error': 'Audiobook price is not set. Cannot create bundle.'}), 400
            base_price = (book.price + book.audiobook_price) * 0.8  # 20% bundle discount
        else:
            base_price = book.price
        
        # Check if already purchased THIS FORMAT - user can own digital + audiobook separately
        existing_purchase = False
        from sqlalchemy import text
        
        try:
            # Query completed purchases for this user+book
            q = text("""
                SELECT id, COALESCE(purchase_format, 'digital') as fmt FROM book_purchases 
                WHERE book_project_id = :book_id AND status = 'COMPLETED'
                AND (buyer_id = :buyer_id OR (buyer_user_id = :buyer_user_id AND :buyer_user_id IS NOT NULL))
            """)
            rows = db.session.execute(q, {
                'book_id': book_id, 'buyer_id': buyer_id or 0,
                'buyer_user_id': buyer_user_id if has_buyer_user_id_col else None
            }).fetchall()
            formats = [r.fmt for r in rows] if rows else []
            if not formats and buyer_id:
                q2 = text("""
                    SELECT COALESCE(purchase_format, 'digital') as fmt FROM book_purchases 
                    WHERE buyer_id = :buyer_id AND book_project_id = :book_id AND status = 'COMPLETED'
                """)
                rows2 = db.session.execute(q2, {'buyer_id': buyer_id, 'book_id': book_id}).fetchall()
                formats = [r.fmt for r in rows2] if rows2 else []
            if not formats and has_buyer_user_id_col:
                q3 = text("""
                    SELECT COALESCE(purchase_format, 'digital') as fmt FROM book_purchases 
                    WHERE buyer_user_id = :uid AND book_project_id = :book_id AND status = 'COMPLETED'
                """)
                rows3 = db.session.execute(q3, {'uid': buyer_user_id, 'book_id': book_id}).fetchall()
                formats = [r.fmt for r in rows3] if rows3 else []
            
            has_digital = 'digital' in formats or 'bundle' in formats
            has_audiobook = 'audiobook' in formats or 'bundle' in formats
            if purchase_type == 'digital':
                existing_purchase = has_digital
            elif purchase_type == 'audiobook':
                existing_purchase = has_audiobook
            else:
                existing_purchase = 'bundle' in formats or (has_digital and has_audiobook)
        except Exception as e:
            logger.warning(f"Error checking existing purchase by format: {e}")
            # Fallback: if purchase_format column missing, any completed purchase blocks (assume all are digital)
            try:
                r = db.session.execute(text("""
                    SELECT 1 FROM book_purchases WHERE book_project_id = :bid AND status = 'COMPLETED'
                    AND (buyer_id = :bid2 OR buyer_user_id = :uid)
                    LIMIT 1
                """), {'bid': book_id, 'bid2': buyer_id or 0, 'uid': buyer_user_id}).fetchone()
                existing_purchase = r is not None
            except Exception:
                pass
        
        if existing_purchase:
            fmt_msg = {'digital': 'digital copy', 'audiobook': 'audiobook', 'bundle': 'bundle'}[purchase_type]
            return jsonify({'error': f'You have already purchased this {fmt_msg}.'}), 400
        
        # Validate book has a price for the selected format
        if not base_price or base_price <= 0:
            return jsonify({'error': f'This {purchase_type} is not available for purchase. Please contact the author.'}), 400
        
        # Validate book has an author
        if not book.author_id:
            logger.error(f"Book {book_id} has no author_id - cannot create sale")
            return jsonify({'error': 'Book has no author. Cannot process purchase.'}), 400
        
        # Validate book has a price
        if not book.price or book.price <= 0:
            logger.error(f"Book {book_id} has no price or invalid price: {book.price}")
            return jsonify({'error': 'This book is not available for purchase. Please contact the author.'}), 400
        
        # Validate and set payment amount (custom amount must be >= base price for this format)
        if custom_amount is not None:
            try:
                custom_amount = float(custom_amount)
                if custom_amount < base_price:
                    return jsonify({'error': f'Payment amount must be at least ${base_price:.2f}'}), 400
                payment_amount = custom_amount
                logger.info(f"Using custom payment amount: ${payment_amount:.2f} (base: ${base_price:.2f} for {purchase_type})")
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid payment amount'}), 400
        else:
            payment_amount = base_price
            logger.info(f"Using base price for {purchase_type}: ${payment_amount:.2f}")
        
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
            if not book.price or book.price <= 0:
                raise ValueError(f"Book {book_id} has invalid price: {book.price}")
            
            logger.info(f"✅ Prerequisites validated: book exists, author_id={book.author_id}, price=${book.price}")
            logger.info(f"🔍 About to check for existing sale or create new one...")
            
            # Check if sale already exists
            existing_sale = BookSale.query.filter_by(purchase_id=purchase.id).first()
            if existing_sale:
                logger.info(f"Existing sale check: Found existing sale ID={existing_sale.id}")
            else:
                logger.info(f"Existing sale check: No existing sale found (will create new one)")
            
            if not existing_sale:
                # Calculate revenue split: base price depends on format; extra amount goes 100% to author
                sale_format = getattr(purchase, 'purchase_format', None) or purchase_type
                if sale_format == 'audiobook':
                    base_price = book.audiobook_price or book.price
                elif sale_format == 'bundle':
                    base_price = (book.price + (book.audiobook_price or 0)) * 0.8
                else:
                    base_price = book.price
                purchase_amount = getattr(purchase, 'amount', base_price)
                extra_amount = max(0, purchase_amount - base_price)  # Amount exceeding base price
                
                royalty_percentage = 0.7
                # Base price: 70% to author, 30% to platform
                base_royalty = base_price * royalty_percentage
                base_platform_fee = base_price - base_royalty
                
                # Extra amount: 100% to author, 0% to platform
                royalty_amount = base_royalty + extra_amount  # Author gets base royalty + all extra
                platform_fee = base_platform_fee  # Platform only gets fee from base price
                
                logger.info(f"📊 Calculating revenue split:")
                logger.info(f"   Base price: ${base_price:.2f}")
                logger.info(f"   Purchase amount: ${purchase_amount:.2f}")
                logger.info(f"   Extra amount: ${extra_amount:.2f}")
                logger.info(f"   Base royalty (70%): ${base_royalty:.2f}")
                logger.info(f"   Base platform fee (30%): ${base_platform_fee:.2f}")
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
        try:
            import stripe
            stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or current_app.config.get('STRIPE_API_KEY')
            if stripe_api_key:
                stripe.api_key = stripe_api_key
                domain_url = current_app.config.get('FRONTEND_BASE_URL') or request.url_root.rstrip('/')
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': (book.currency or 'USD').lower(),
                            'product_data': {
                                'name': book.title,
                                'description': f'Purchase of "{book.title}"' + (f' ({purchase_type})' if purchase_type != 'digital' else ''),
                            },
                            'unit_amount': int(payment_amount * 100),
                        },
                        'quantity': 1,
                    }],
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
                stripe_checkout_url = checkout_session.url
        except Exception as stripe_err:
            logger.warning(f"Could not create Stripe Checkout Session: {stripe_err}")
        
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
            return jsonify({
                'success': False,
                'error': 'Payment processing is not configured. Please set STRIPE_SECRET_KEY and try again.'
            }), 503
        logger.info(f"✅ Returning success response: {response_data}")
        return jsonify(response_data)
        
        
    except Exception as e:
        db.session.rollback()
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
            from flask import current_app
            is_debug = current_app.config.get('DEBUG', False) or current_app.config.get('FLASK_ENV') == 'development'
        except:
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
                book = BookProject.query.get(book_id)
                if not book:
                    return jsonify({'error': 'Book not found'}), 404
                
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
                        if sale_format == 'audiobook':
                            base_price = book.audiobook_price or book.price
                        elif sale_format == 'bundle':
                            base_price = (book.price + (book.audiobook_price or 0)) * 0.8
                        else:
                            base_price = book.price
                        extra_amount = max(0, payment_amount - base_price)
                        royalty_percentage = 0.7
                        base_royalty = base_price * royalty_percentage
                        base_platform_fee = base_price - base_royalty
                        royalty_amount = base_royalty + extra_amount
                        platform_fee = base_platform_fee
                        
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
                try:
                    import stripe
                    stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or current_app.config.get('STRIPE_API_KEY')
                    if stripe_api_key:
                        stripe.api_key = stripe_api_key
                        checkout_session = stripe.checkout.Session.create(
                            payment_method_types=['card'],
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
                        stripe_checkout_url = checkout_session.url
                except Exception as e:
                    logger.warning(f"Fallback Stripe checkout failed: {e}")
                
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
                return jsonify({'success': False, 'error': 'Payment processing is not configured.'}), 503
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
                    return redirect(url_for('book_platform.view_book', book_id=book_id))
        
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
            
            # Prevent self-purchase
            if book.author and book.author.user_id == buyer_user_id:
                flash('You cannot purchase your own book.', 'error')
                return redirect(url_for('book_platform.marketplace'))
            
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
            sale_format = getattr(purchase, 'purchase_format', None) or 'digital'
            if sale_format == 'audiobook':
                base_price = book.audiobook_price or book.price
            elif sale_format == 'bundle':
                base_price = (book.price + (book.audiobook_price or 0)) * 0.8
            else:
                base_price = book.price
            extra_amount = max(0, purchase.amount - base_price)
            royalty_percentage = 0.7
            base_royalty = base_price * royalty_percentage
            base_platform_fee = base_price - base_royalty
            royalty_amount = base_royalty + extra_amount
            platform_fee = base_platform_fee
            
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

        flash('Purchase successful! Thank you for your purchase.', 'success')
        logger.info(
            f"✅ Purchase {purchase.id} recorded from Stripe success for book {book_id}, sale id={getattr(sale, 'id', None)}"
        )
        return redirect(url_for('book_platform.view_book', book_id=book_id))
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error processing purchase success: {str(e)}", exc_info=True)
        flash('Error recording purchase. Please contact support with your payment confirmation.', 'error')
        return redirect(url_for('book_platform.marketplace'))

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
        stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or current_app.config.get('STRIPE_API_KEY')
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
            
            # Prevent self-purchase
            if book.author and purchase.buyer_user_id and book.author.user_id == purchase.buyer_user_id:
                logger.warning(f"Self-purchase attempt blocked for purchase {purchase.id}")
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
                # Create sale record - use purchase_format for correct sale type and base price
                sale_format = getattr(purchase, 'purchase_format', None) or 'digital'
                if sale_format == 'audiobook':
                    base_price = book.audiobook_price or book.price
                elif sale_format == 'bundle':
                    base_price = (book.price + (book.audiobook_price or 0)) * 0.8
                else:
                    base_price = book.price
                extra_amount = max(0, purchase.amount - base_price)  # Amount exceeding base price
                
                royalty_percentage = 0.7
                base_royalty = base_price * royalty_percentage
                base_platform_fee = base_price - base_royalty
                royalty_amount = base_royalty + extra_amount  # Author gets base royalty + all extra
                platform_fee = base_platform_fee
                
                logger.info(f"Revenue split for purchase {purchase.id} ({sale_format}): base=${base_price:.2f} (royalty=${base_royalty:.2f}, fee=${base_platform_fee:.2f}), extra=${extra_amount:.2f}, total=${purchase.amount:.2f}")
                
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
                        # Update campaign funding on successful payment
                        campaign.current_funding += investment.amount
                        
                        # If goal reached, mark campaign as FUNDED (stops new investments)
                        if campaign.current_funding >= campaign.funding_goal:
                            campaign.status = CampaignStatus.FUNDED
                            campaign.funded_at = datetime.now(timezone.utc)
                            # Activate all confirmed investments
                            for inv in campaign.investments:
                                if inv.status == InvestmentStatus.CONFIRMED:
                                    if not inv.return_start_date:
                                        inv.return_start_date = datetime.now(timezone.utc)
                                    inv.status = InvestmentStatus.ACTIVE
                        else:
                            # Activate this investment for returns even if goal not reached
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
                    # If no purchase found but we have book_id, create new purchase (fallback)
                    elif book_id:
                        logger.warning(f"⚠️  checkout.session.completed received but couldn't find matching purchase. book_id={book_id}, purchase_id={purchase_id}, amount=${amount_total}, email={customer_email}. Creating new purchase...")
                        try:
                            book_id = int(book_id)
                            user = User.query.filter_by(email=customer_email).first() if customer_email else None
                            
                            if user:
                                buyer_user_id = user.user_id
                                book = BookProject.query.get(book_id)
                                
                                if book and book.author and book.author.user_id != buyer_user_id:
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
                                        
                                        # Revenue sharing: base book price is split 70/30, extra amount goes 100% to author
                                        base_price = book.price
                                        extra_amount = max(0, actual_amount - base_price)  # Amount exceeding book price
                                        
                                        # Base price: 70% to author, 30% to platform
                                        base_royalty = base_price * 0.7
                                        base_platform_fee = base_price * 0.3
                                        
                                        # Extra amount: 100% to author, 0% to platform
                                        royalty_amount = base_royalty + extra_amount  # Author gets base royalty + all extra
                                        platform_fee = base_platform_fee  # Platform only gets fee from base price
                                        
                                        sale = BookSale(
                                            seller_id=book.author_id,
                                            book_project_id=book_id,
                                            purchase_id=purchase.id,
                                            royalty_amount=royalty_amount,
                                            royalty_percentage=0.7,
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
    """Get author details for marketplace display"""
    try:
        # Ensure BookPlatformUser is accessible
        from glconnect.book_platform_models import BookPlatformUser, BookStatus
        
        # Get the author (BookPlatformUser)
        author = BookPlatformUser.query.get_or_404(author_id)
        
        # Get Writer profile if it exists (for bio and profile picture)
        writer = Writer.query.filter_by(user_id=author.user_id).first()
        
        # Use Writer profile data if available, otherwise use BookPlatformUser data
        author_name = author.pen_name or author.user.username
        author_bio = None
        author_profile_picture = None
        
        if writer:
            # Writer profile takes precedence
            author_bio = writer.bio
            author_profile_picture = writer.profile_picture
        else:
            # Fall back to BookPlatformUser data
            author_bio = author.bio
            author_profile_picture = author.profile_picture
        
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
                'email': author.user.email if author.user else None,
                'bio': author_bio,
                'profile_picture': author_profile_picture,
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
    
    # For non-API routes, let Flask handle it normally
    raise error

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
@book_bp.route('/upload-digital-book', methods=['GET', 'POST'])
@book_platform_required
def upload_digital_book():
    """List a finished ebook on Ink Studio: upload file + cover (author need not write the book in-platform)."""
    
    logger.info(f"Upload digital book - Method: {request.method}, User: {current_user.user_id if current_user.is_authenticated else 'Not authenticated'}")
    
    form = DigitalBookUploadForm()
    
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
                    # Don't show recaptcha errors to user in development
                    if field != 'recap' or os.getenv('FLASK_ENV') != 'development':
                        flash(f"{field}: {error}", "error")
            return render_template('book_platform/upload_digital_book.html', form=form)
        else:
            logger.info("Form validation passed")
    
    if form.validate_on_submit():
        try:
            logger.info("Starting digital book upload process")
            
            # Get user profile
            user_profile, profile_type = get_user_profile()
            logger.info(f"User profile: {profile_type}, User ID: {current_user.user_id}")
            
            if not user_profile:
                logger.error("No user profile found")
                flash("Please ensure you have an Ink Studio or Writer profile.", "error")
                return render_template('book_platform/upload_digital_book.html', form=form)
            
            author_id = get_profile_id(user_profile, profile_type)
            logger.info(f"Author ID: {author_id}")
            
            if not author_id:
                flash("Error: Could not determine author ID. Please ensure your profile is set up correctly.", "error")
                logger.error(f"get_profile_id returned None for user_id={current_user.user_id}, profile_type={profile_type}")
                return render_template('book_platform/upload_digital_book.html', form=form)
            
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
                flash(f"Failed to extract text from file: {extraction_result['error']}", "error")
                return render_template('book_platform/upload_digital_book.html', form=form)

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
                ai_res = generate_book_cover_bytes(
                    form.title.data or "",
                    form.description.data or "",
                    form.genre.data or "",
                    form.cover_art_brief.data or "",
                )
                if not ai_res.get("success") or not ai_res.get("image_bytes"):
                    flash(
                        ai_res.get("error")
                        or "Could not generate an AI cover. Upload an image or try again.",
                        "error",
                    )
                    return render_template('book_platform/upload_digital_book.html', form=form)
                unique_cover_filename = f"ai_cover_{uuid.uuid4().hex[:10]}.png"
                abs_cover = os.path.join(covers_dir, unique_cover_filename)
                with open(abs_cover, "wb") as out:
                    out.write(ai_res["image_bytes"])
                cover_path = f"book_covers/{unique_cover_filename}"
            else:
                flash(
                    "Please upload a cover image or check “Generate cover with AI” so your listing has artwork.",
                    "error",
                )
                return render_template('book_platform/upload_digital_book.html', form=form)
            
            # Create book project
            logger.info(f"Creating book project: {form.title.data}")
            book = BookProject(
                title=form.title.data,
                description=form.description.data,
                genre=form.genre.data,
                language='en',  # Default to English for uploaded books (audiobooks are English-only)
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
            
            db.session.add(book)
            db.session.flush()  # Flush to get book.id
            logger.info(f"Book created with ID: {book.id}, Title: {book.title}")
            db.session.commit()
            logger.info(f"Book {book.id} committed to database successfully")
            
            # Generate audiobook if requested
            logger.info(f"Generate audiobook checkbox: {form.generate_audiobook.data}")
            logger.info(f"Audiobook price: {form.audiobook_price.data}")
            logger.info(f"Audiobook voice: {form.audiobook_voice.data}")
            
            if form.generate_audiobook.data:
                # Get voice selection or use default
                selected_voice = form.audiobook_voice.data or 'en-US-Standard-A'
                audiobook_price = form.audiobook_price.data or 0.0
                
                if not selected_voice:
                    flash("Please select a voice for your audiobook.", "error")
                    return render_template('book_platform/upload_digital_book.html', form=form)
                # Create audio generation task
                audio_task = AudioGenerationTask(
                    book_project_id=book.id,
                    status='pending'
                )
                db.session.add(audio_task)
                db.session.commit()
                
                # Start audio generation in background
                def generate_audio_background():
                    try:
                        # Update task status
                        audio_task.status = 'processing'
                        audio_task.progress = 10
                        db.session.commit()
                        
                        # Chapter-based audio (Audible-style) for uploads: headings or word-based parts
                        upload_chapters = build_uploaded_book_audiobook_chapters(
                            extraction_result.get('text') or ''
                        )
                        audio_result = audio_book_generator.generate_audiobook_by_chapters(
                            upload_chapters,
                            book.id,
                            selected_voice
                        )
                        
                        if audio_result['success']:
                            book.has_audiobook = True
                            book.audiobook_price = audiobook_price
                            book.audiobook_generated_at = datetime.now(timezone.utc)
                            book.audiobook_voice = selected_voice
                            ch_results = audio_result.get('chapter_results') or []
                            book.audiobook_duration = audio_result.get('duration', 0)
                            book.audiobook_file_path = (
                                ch_results[0]['audio_file_path'] if ch_results else None
                            )
                            for ch in ch_results:
                                db.session.add(
                                    AudiobookChapter(
                                        book_project_id=book.id,
                                        chapter_number=ch['chapter_number'],
                                        title=ch['title'],
                                        audio_file_path=ch['audio_file_path'],
                                        duration_seconds=ch.get('duration', 0),
                                        book_chapter_id=ch.get('book_chapter_id'),
                                    )
                                )
                            
                            # Update task
                            audio_task.status = 'completed'
                            audio_task.progress = 100
                            audio_task.completed_at = datetime.now(timezone.utc)
                            
                            db.session.commit()
                            
                            flash("Audiobook generated successfully!", "success")
                        else:
                            # Update task with error
                            audio_task.status = 'failed'
                            audio_task.error_message = audio_result['error']
                            db.session.commit()
                            
                            flash(f"Audiobook generation failed: {audio_result['error']}", "error")
                            
                    except Exception as e:
                        audio_task.status = 'failed'
                        audio_task.error_message = str(e)
                        db.session.commit()
                        flash(f"Audiobook generation failed: {str(e)}", "error")
                
                # Start background thread
                thread = threading.Thread(target=generate_audio_background)
                thread.daemon = True
                thread.start()
                
                flash("Digital book uploaded successfully! Audiobook generation started in the background.", "success")
            else:
                flash("Digital book uploaded successfully!", "success")
            
            logger.info(f"Upload successful! Redirecting to book {book.id}")
            return redirect(url_for('book_platform.view_book', book_id=book.id))
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Error uploading book: {str(e)}"
            flash(error_msg, "error")
            logger.error(f"Error in upload_digital_book: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            print(f"ERROR in upload_digital_book: {str(e)}")
            traceback.print_exc()
    
    # GET request - show form
    if request.method == 'GET':
        logger.info("Showing upload digital book form")
    
    return render_template('book_platform/upload_digital_book.html', form=form)

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
    
    if not book.digital_file_path:
        flash("Digital file not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    # Serve the file
    file_path = os.path.join(current_app.root_path, 'static', book.digital_file_path)
    
    if not os.path.exists(file_path):
        flash("Digital file not found.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    return send_from_directory(
        os.path.dirname(file_path),
        os.path.basename(file_path),
        as_attachment=True,
        download_name=f"{book.title}.{book.digital_file_type}"
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
    book = BookProject.query.get_or_404(book_id)
    
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

    return render_template(
        'book_platform/audiobook_player.html',
        book=book,
        chapters=chapters,
        chapter_tracklist=chapter_tracklist,
        single_audiobook_src=single_audiobook_src,
    )


@book_bp.route('/books/<int:book_id>/download-audio')
@login_required
def download_audio_book(book_id):
    """Download audio book file"""
    book = BookProject.query.get_or_404(book_id)
    
    if not book.has_audiobook or not book.audiobook_file_path:
        flash("Audiobook not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    # Check if user has purchased this book (same logic as digital download)
    # No profile required - just user account
    user_id = current_user.user_id
    
    # Check if user is the author (by comparing user_id directly)
    is_author = False
    if book.author and book.author.user_id == user_id:
        is_author = True
    
    if not is_author:
        # Check if user has purchased audiobook or bundle (grants audiobook download access)
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
    
    # Serve the audio file
    if not os.path.exists(book.audiobook_file_path):
        flash("Audiobook file not found.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    # Convert full path to relative path for serving
    static_path = os.path.join(current_app.root_path, 'static')
    if book.audiobook_file_path.startswith(static_path):
        relative_path = os.path.relpath(book.audiobook_file_path, static_path)
        return send_from_directory(
            os.path.join(current_app.root_path, 'static'),
            relative_path,
            as_attachment=True,
            download_name=f"{book.title}_audiobook.mp3"
        )
    else:
        return send_from_directory(
            os.path.dirname(book.audiobook_file_path),
            os.path.basename(book.audiobook_file_path),
            as_attachment=True,
            download_name=f"{book.title}_audiobook.mp3"
        )

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
        flash('Investment campaigns are not available for uploaded books. Uploaded books can only be sold (digital/audio) in the marketplace.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Check if campaign already exists
    existing_campaign = InvestmentCampaign.query.filter_by(book_project_id=book_id).first()
    if existing_campaign:
        flash('An investment campaign already exists for this book.', 'info')
        return redirect(url_for('book_platform.investment_campaign', campaign_id=existing_campaign.id))
    
    # Check if book is ready for investment
    investment_readiness = check_investment_readiness(book)
    
    if not investment_readiness['is_ready']:
        flash('Your book is not ready for investment yet. Please complete the following requirements:', 'warning')
        for issue in investment_readiness['issues']:
            flash(f'• {issue}', 'info')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    form = InvestmentCampaignForm()
    
    if form.validate_on_submit():
        try:
            # Create timezone-aware datetimes in UTC
            start_date = datetime.now(timezone.utc)
            end_date = start_date + timedelta(days=form.investment_period_days.data)
            
            campaign = InvestmentCampaign(
                book_project_id=book_id,
                title=form.title.data,
                description=form.description.data,
                pitch_video_url=form.pitch_video_url.data,
                funding_goal=form.funding_goal.data,
                minimum_investment=form.minimum_investment.data,
                maximum_investment=form.maximum_investment.data if form.maximum_investment.data else None,
                revenue_share_percentage=form.revenue_share_percentage.data,
                return_multiplier_cap=form.return_multiplier_cap.data,
                investment_period_days=form.investment_period_days.data,
                status=CampaignStatus.ACTIVE,
                start_date=start_date,
                end_date=end_date
            )
            
            db.session.add(campaign)
            book.has_investment_campaign = True
            db.session.commit()
            
            flash('Investment campaign created successfully!', 'success')
            return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating campaign: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('book_platform/create_campaign.html', form=form, book=book)

# Investment Marketplace
@book_bp.route('/investments', methods=['GET'])
@login_required
def investments():
    """Browse investment campaigns - visible to investors regardless of book publication status
    
    Investment campaigns are designed to get funding BEFORE publishing, so campaigns
    are visible as soon as they're created (ACTIVE status), even if the book is still in draft.
    
    IMPORTANT: Authors cannot see their own book campaigns here - they can only invest in other authors' books.
    """
    status_filter = request.args.get('status', 'active')
    search_query = request.args.get('q', '')
    
    # Join with BookProject to enable search
    # Campaigns are visible based on their status (ACTIVE, FUNDED, DRAFT), not book status
    # This allows investors to fund books before they're published
    query = InvestmentCampaign.query.join(BookProject)
    
    # Exclude campaigns where the current user is the author
    # Authors can only invest in books that are NOT their own
    user_profile, profile_type = get_user_profile()
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        if author_id:
            query = query.filter(BookProject.author_id != author_id)
            logger.info(f"Investments page - Filtering out campaigns for user's own books (author_id: {author_id})")
    
    # Filter by campaign status
    if status_filter == 'active':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.ACTIVE)
    elif status_filter == 'funded':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.FUNDED)
    elif status_filter == 'draft':
        query = query.filter(InvestmentCampaign.status == CampaignStatus.DRAFT)
    elif status_filter == 'all':
        # Show all campaigns except cancelled/failed
        query = query.filter(
            InvestmentCampaign.status.in_([
                CampaignStatus.DRAFT,
                CampaignStatus.ACTIVE,
                CampaignStatus.FUNDED
            ])
        )
    # Default to active if no valid filter
    
    if search_query:
        query = query.filter(
            db.or_(
                InvestmentCampaign.title.ilike(f'%{search_query}%'),
                BookProject.title.ilike(f'%{search_query}%'),
                BookProject.description.ilike(f'%{search_query}%')
            )
        )
    
    campaigns = query.order_by(InvestmentCampaign.created_at.desc()).all()
    
    return render_template('book_platform/investments.html', 
                         campaigns=campaigns,
                         status_filter=status_filter,
                         search_query=search_query)

# Investment Campaign Details
@book_bp.route('/investments/<int:campaign_id>', methods=['GET'])
def investment_campaign(campaign_id):
    """View investment campaign details"""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    book = campaign.book_project
    
    # Safety check: ensure book is a single object, not a collection
    if book is None:
        flash('Book project not found for this campaign.', 'error')
        return redirect(url_for('book_platform.investments'))
    
    investments = BookInvestment.query.filter_by(campaign_id=campaign_id).all()
    
    # Group investments by investor to show unique investors with totals
    from collections import defaultdict
    investor_totals = defaultdict(lambda: {'total_amount': 0.0, 'investments': [], 'first_investment_date': None, 'last_investment_date': None})
    
    for investment in investments:
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
    
    # Get book reviews (accredited reviews)
    from glconnect.book_platform_models import BookReview, ReviewStatus
    accredited_reviews = []
    if book and hasattr(book, 'id'):
        accredited_reviews = BookReview.query.filter_by(
            book_project_id=book.id,
            status=ReviewStatus.PUBLISHED
        ).all()
    
    # Calculate average rating
    avg_rating = sum(r.rating for r in accredited_reviews) / len(accredited_reviews) if accredited_reviews else 0
    
    # Get book chapters count and completed chapters
    chapters_count = 0
    completed_chapters = []
    completed_chapters_count = 0
    if book and hasattr(book, 'chapters') and book.chapters:
        chapters_count = len(book.chapters)
        completed_chapters = [ch for ch in book.chapters if ch.content and hasattr(ch, 'id')]
        completed_chapters_count = len(completed_chapters)
    
    # Calculate days remaining
    from datetime import timedelta
    days_remaining = 0
    if campaign.end_date:
        # Ensure end_date is timezone-aware for comparison
        end_date = campaign.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        days_remaining = max(0, (end_date - datetime.now(timezone.utc)).days)
    
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
                         author_other_books=author_other_books,
                         is_author=is_author)

# Make Investment
@book_bp.route('/investments/<int:campaign_id>/invest', methods=['GET', 'POST'])
@login_required
def make_investment(campaign_id):
    """User invests in a campaign"""
    campaign = InvestmentCampaign.query.options(
        joinedload(InvestmentCampaign.book_project)
    ).get_or_404(campaign_id)
    
    book = campaign.book_project
    
    logger.info(f"Make investment attempt - User: {current_user.user_id}, Campaign: {campaign_id}, Status: {campaign.status.value}, Book Status: {book.status.value if book else 'None'}")
    
    # Stop new investments if book is published OR goal has been reached
    if book and is_book_published(book):
        logger.warning(f"Investment blocked - Book {book.id} is already published")
        flash('This campaign is no longer accepting investments because the book is already published.', 'error')
        return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # Campaign must be ACTIVE to accept investments (FUNDED means goal reached, no more investments)
    if campaign.status != CampaignStatus.ACTIVE:
        logger.warning(f"Investment blocked - Campaign {campaign_id} status is {campaign.status.value}, not ACTIVE")
        if campaign.status == CampaignStatus.FUNDED:
            flash('This campaign has reached its funding goal and is no longer accepting new investments.', 'error')
        else:
            flash('This campaign is not currently accepting investments.', 'error')
        return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # All users can invest - ensure they have a BookPlatformUser profile for investment tracking
    # Get or create BookPlatformUser profile for the investor
    from glconnect.book_platform_models import BookPlatformUser
    from glconnect.models import Writer
    
    investor_user_id = current_user.user_id
    
    # Prevent self-investment: Check if current user is the author
    # This check uses user_id to ensure authors cannot invest in their own books
    if book and book.author:
        # Check both user_id and author_id to be thorough
        if book.author.user_id == investor_user_id:
            logger.warning(f"Investment blocked - User {investor_user_id} is the author of book {book.id}")
            flash('You cannot invest in your own book.', 'error')
            return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # Get or create BookPlatformUser profile for investment
    bp_user = BookPlatformUser.query.filter_by(user_id=investor_user_id).first()
    
    if not bp_user:
        # Create BookPlatformUser profile for investment
        # Try to get info from Writer profile if user is an author
        writer = Writer.query.filter_by(user_id=investor_user_id).first()
        
        try:
            bp_user = BookPlatformUser(
                user_id=investor_user_id,
                pen_name=writer.writer_name if writer else current_user.username,
                bio=writer.bio if writer else "Investor",
                profile_picture=writer.profile_picture if writer else "static/uploads/default_writer.jpg"
            )
            db.session.add(bp_user)
            db.session.commit()
            logger.info(f"Created BookPlatformUser {bp_user.id} for investor {investor_user_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create BookPlatformUser for investor: {str(e)}", exc_info=True)
            flash('Failed to set up investor profile. Please try again.', 'error')
            return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    investor_id = bp_user.id
    
    # Double-check: Prevent investing in own book using investor_id
    if book and book.author_id == investor_id:
        logger.warning(f"Investment blocked - Investor {investor_id} is the author_id of book {book.id}")
        flash('You cannot invest in your own book.', 'error')
        return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # Handle both JSON (AJAX) and form submissions (like book purchase)
    form = InvestmentForm()
    request_data = request.get_json() if request.is_json else None
    amount = None
    
    if request_data:
        # JSON request (AJAX) - same pattern as book purchase
        try:
            amount = float(request_data.get('amount', 0))
            if amount <= 0:
                return jsonify({'error': 'Invalid investment amount'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid investment amount'}), 400
    else:
        # Form submission - use form validation
        form = InvestmentForm()
        if not form.validate_on_submit():
            return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
        amount = form.amount.data
    
    # Validate amount (same for both JSON and form)
    if amount < campaign.minimum_investment:
        error_msg = f'Minimum investment is ${campaign.minimum_investment:.2f}'
        if request_data:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
    
    if campaign.maximum_investment and amount > campaign.maximum_investment:
        error_msg = f'Maximum investment is ${campaign.maximum_investment:.2f}'
        if request_data:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
    
    # Check if goal would be exceeded
    if campaign.current_funding + amount > campaign.funding_goal:
        max_remaining = campaign.funding_goal - campaign.current_funding
        error_msg = f'Investment would exceed the funding goal. Maximum remaining: ${max_remaining:.2f}'
        if request_data:
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
    
    try:
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
            revenue_share_percentage=campaign.revenue_share_percentage,
            return_multiplier=campaign.return_multiplier_cap,
            status=InvestmentStatus.PENDING,
            payment_status=TransactionStatus.PENDING
        )
        
        db.session.add(investment)
        db.session.commit()
        logger.info(f"Created investment {investment.id} for campaign {campaign_id}, amount: ${amount}")

        # Create Stripe Checkout Session (same pattern as book purchase)
        domain_url = current_app.config.get("FRONTEND_BASE_URL") or request.url_root.rstrip("/")
        success_url = f"{domain_url}{url_for('book_platform.investment_campaign', campaign_id=campaign_id)}?payment=success"
        cancel_url = f"{domain_url}{url_for('book_platform.investment_campaign', campaign_id=campaign_id)}?payment=cancelled"
        
        stripe_checkout_url = None
        stripe_error = None
        try:
            import stripe
            stripe_api_key = current_app.config.get('STRIPE_SECRET_KEY') or current_app.config.get('STRIPE_API_KEY')
            logger.info(f"Investment Stripe key check: stripe_api_key exists = {bool(stripe_api_key)}")
            if stripe_api_key:
                stripe.api_key = stripe_api_key
                logger.info(f"Creating Stripe checkout session for investment {investment.id}, amount: ${amount}")
                checkout_session = stripe.checkout.Session.create(
                    mode="payment",
                    payment_method_types=["card"],
                    line_items=[
                        {
                            "price_data": {
                                "currency": "usd",
                                "unit_amount": int(amount * 100),
                                "product_data": {
                                    "name": f"Investment in '{book.title}'",
                                    "description": f"Campaign #{campaign.id} on Ink Studio",
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
                stripe_checkout_url = checkout_session.url
                logger.info(f"Successfully created Stripe checkout session: {stripe_checkout_url}")
            else:
                stripe_error = "Stripe API key not found in configuration"
                logger.warning(f"Stripe API key not found in config for investment {investment.id}")
        except Exception as e:
            stripe_error = str(e)
            logger.error(f"Could not create Stripe Checkout Session for investment {investment.id}: {e}", exc_info=True)
        
        # Return JSON response (same pattern as book purchase)
        if request_data:
            response = {
                'success': True,
                'investment_id': investment.id,
                'status': 'pending',
                'message': 'Investment created. Redirecting to payment...',
                'success_url': success_url,
                'cancel_url': cancel_url,
            }
            if stripe_checkout_url:
                response['stripe_checkout_url'] = stripe_checkout_url
                return jsonify(response)
            else:
                error_msg = stripe_error or 'Stripe payment is not configured. Please set STRIPE_SECRET_KEY in your environment.'
                logger.warning(f"Stripe checkout URL not available for investment {investment.id}: {error_msg}")
                return jsonify({'success': False, 'error': error_msg}), 503
        else:
            # Form submission - redirect to Stripe (backward compatibility)
            if stripe_checkout_url:
                return redirect(stripe_checkout_url, code=303)
            else:
                flash('Stripe payment is not configured. Please contact support.', 'error')
                return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error making investment: {str(e)}", exc_info=True)
        error_msg = f'An error occurred: {str(e)}'
        if request_data:
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
    
    # Render form for GET requests or form validation errors
    form = InvestmentForm() if not request_data else None
    return render_template('book_platform/make_investment.html', form=form, campaign=campaign)

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
                    # Also refresh related investments to get latest total_returns before distribution
                    investments = BookInvestment.query.filter_by(book_project_id=sale.book_project_id).all()
                    for inv in investments:
                        db.session.refresh(inv)
                    
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
                
                # Refresh all investments after distribution to ensure UI shows latest data
                all_investments = BookInvestment.query.all()
                for inv in all_investments:
                    db.session.refresh(inv)
                logger.info(f"✅ Refreshed {len(all_investments)} investments with latest returns")
            else:
                db.session.rollback()
                logger.warning(f"⚠️  No distributions were successful, rolled back")
    except Exception as e:
        logger.error(f"Error processing pending distributions: {e}", exc_info=True)
        db.session.rollback()
    
    earnings_data = {
        'reviewer_earnings': [],
        'investment_returns': [],
        'author_sales': [],
        'reviewer_earnings_by_book': {},
        'investment_returns_by_book': {},
        'author_sales_by_book': {}
    }
    
    # Reviewer earnings
    reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    if reviewer:
        earnings_data['reviewer_earnings'] = ReviewerEarning.query.filter_by(
            reviewer_id=reviewer.id
        ).order_by(ReviewerEarning.created_at.desc()).limit(50).all()
        earnings_data['total_reviewer_earnings'] = reviewer.total_earnings
        # Available = sum of PENDING earnings (for payout request)
        earnings_data['reviewer_available_balance'] = sum(
            e.amount for e in ReviewerEarning.query.filter_by(
                reviewer_id=reviewer.id, status=TransactionStatus.PENDING
            ).all()
        )
        earnings_data['reviewer_pending_payout_requests'] = ReviewerPayoutRequest.query.filter_by(
            reviewer_id=reviewer.id, status='PENDING'
        ).all()
        
        # Group earnings by book
        from collections import defaultdict
        earnings_by_book = defaultdict(lambda: {'earnings': [], 'total': 0.0, 'book': None})
        for earning in earnings_data['reviewer_earnings']:
            book_id = earning.review.book_project_id
            earnings_by_book[book_id]['earnings'].append(earning)
            earnings_by_book[book_id]['total'] += earning.amount
            if not earnings_by_book[book_id]['book']:
                earnings_by_book[book_id]['book'] = earning.review.book_project
        earnings_data['reviewer_earnings_by_book'] = dict(earnings_by_book)
    
    # Investment returns - accessible to all users who have invested
    # IMPORTANT: Authors can only invest in books that are NOT their own
    # Find investments by user_id through BookPlatformUser (investments are linked via investor_id = book_platform_users.id)
    book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if book_platform_user:
        investor_id = book_platform_user.id
        # Get all investments for this investor, but EXCLUDE investments in books where they are the author
        # Join with BookProject to filter out self-investments
        all_investments = BookInvestment.query.join(
            BookProject, BookInvestment.book_project_id == BookProject.id
        ).filter(
            BookInvestment.investor_id == investor_id,
            BookProject.author_id != investor_id  # Exclude investments in own books
        ).all()
        
        # Only show investments that are confirmed or active (pending investments don't have returns yet)
        investments = [inv for inv in all_investments if inv.status.value in ['confirmed', 'active']]
        
        # IMPORTANT: Refresh investments AFTER processing distributions to get latest returns
        for investment in investments:
            db.session.refresh(investment)
        
        earnings_data['investments'] = investments
        earnings_data['total_investment_returns'] = sum(inv.total_returns for inv in investments)
        logger.info(f"Earnings dashboard - Total investment returns: ${earnings_data['total_investment_returns']:.2f} from {len(investments)} investments (excluding own books)")
        
        # Get payout history and available balance for each investment
        for investment in investments:
            payouts = InvestmentPayout.query.filter_by(
                investment_id=investment.id
            ).order_by(InvestmentPayout.created_at.desc()).limit(20).all()
            investment.payouts_list = payouts
            investment.available_balance = (investment.total_returns or 0) - (getattr(investment, 'paid_out_amount', 0) or 0)
            investment.pending_payout_requests = PayoutRequest.query.filter_by(
                investment_id=investment.id, status='PENDING'
            ).all()
            # Verify total_returns matches sum of payouts (for debugging)
            calculated_returns = sum(p.amount for p in payouts)
            if abs((investment.total_returns or 0) - calculated_returns) > 0.01:
                logger.warning(f"Investment {investment.id} total_returns (${investment.total_returns}) doesn't match sum of payouts (${calculated_returns})")
    else:
        # User doesn't have a BookPlatformUser profile yet, but might have investments
        # This shouldn't happen if they invested (investment requires profile), but check anyway
        earnings_data['investments'] = []
        earnings_data['total_investment_returns'] = 0.0
    
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
    
    return render_template('book_platform/earnings.html', earnings_data=earnings_data, payout_minimum=PAYOUT_MINIMUM_AMOUNT)


# Minimum amount to request payout (USD) - investors must reach this balance to cash out to bank
PAYOUT_MINIMUM_AMOUNT = 50.0


@book_bp.route('/earnings/request-payout', methods=['POST'])
@login_required
def request_payout():
    """Investor requests payout of available earnings"""
    data = request.get_json() or {}
    investment_id = data.get('investment_id')
    amount = data.get('amount')
    
    if not investment_id or amount is None:
        return jsonify({'error': 'Missing investment_id or amount'}), 400
    
    try:
        investment_id = int(investment_id)
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid investment_id or amount'}), 400
    
    if amount < PAYOUT_MINIMUM_AMOUNT:
        return jsonify({'error': f'Minimum payout amount is ${PAYOUT_MINIMUM_AMOUNT:.2f}'}), 400
    
    bp_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not bp_user:
        return jsonify({'error': 'Investor profile not found'}), 403
    
    investment = BookInvestment.query.filter_by(
        id=investment_id, investor_id=bp_user.id
    ).first()
    if not investment:
        return jsonify({'error': 'Investment not found or you do not own it'}), 404
    
    available = (investment.total_returns or 0) - (getattr(investment, 'paid_out_amount', 0) or 0)
    if amount > available:
        return jsonify({'error': f'Amount exceeds available balance (${available:.2f})'}), 400
    
    # Check for existing pending request
    pending = PayoutRequest.query.filter_by(
        investment_id=investment_id, status='PENDING'
    ).first()
    if pending:
        return jsonify({'error': 'You already have a pending payout request for this investment'}), 400
    
    payout_request = PayoutRequest(
        investment_id=investment_id,
        amount=amount,
        currency=investment.currency or 'USD',
        status='PENDING'
    )
    db.session.add(payout_request)
    db.session.commit()
    
    logger.info(f"Payout request {payout_request.id} created: investment={investment_id}, amount=${amount}")
    return jsonify({
        'success': True,
        'message': f'Payout request of ${amount:.2f} submitted. Admin will process it shortly.',
        'payout_request_id': payout_request.id
    })


@book_bp.route('/earnings/request-reviewer-payout', methods=['POST'])
@login_required
def request_reviewer_payout():
    """Reviewer requests payout of available earnings (min $50, mirrors investor flow)"""
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
    """Admin view of pending payout requests"""
    if current_user.role != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    pending = PayoutRequest.query.filter_by(status='PENDING').order_by(
        PayoutRequest.requested_at.asc()
    ).all()
    paid = PayoutRequest.query.filter_by(status='PAID').order_by(
        PayoutRequest.paid_at.desc()
    ).limit(50).all()
    
    return render_template('book_platform/admin_payout_requests.html',
        pending=pending, paid=paid
    )


@book_bp.route('/admin/payout-requests/<int:request_id>/mark-paid', methods=['POST'])
@login_required
def admin_mark_payout_paid(request_id):
    """Admin marks a payout request as paid (after bank transfer)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    payout_request = PayoutRequest.query.get_or_404(request_id)
    if payout_request.status != 'PENDING':
        return jsonify({'error': 'Payout request is not pending'}), 400
    
    investment = payout_request.investment
    available = (investment.total_returns or 0) - (getattr(investment, 'paid_out_amount', 0) or 0)
    if payout_request.amount > available:
        return jsonify({'error': f'Amount (${payout_request.amount:.2f}) exceeds available balance (${available:.2f})'}), 400
    
    payout_request.status = 'PAID'
    payout_request.paid_at = datetime.now(timezone.utc)
    payout_request.admin_notes = (request.get_json() or {}).get('admin_notes', '')
    
    investment.paid_out_amount = (getattr(investment, 'paid_out_amount', 0) or 0) + payout_request.amount
    db.session.commit()
    
    logger.info(f"Payout request {payout_request.id} marked paid by admin {current_user.username}")
    flash(f'Payout of ${payout_request.amount:.2f} marked as paid.', 'success')
    return redirect(url_for('book_platform.admin_payout_requests'))


@book_bp.route('/admin/payout-requests/<int:request_id>/cancel', methods=['POST'])
@login_required
def admin_cancel_payout_request(request_id):
    """Admin cancels a payout request"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    payout_request = PayoutRequest.query.get_or_404(request_id)
    if payout_request.status != 'PENDING':
        return jsonify({'error': 'Payout request is not pending'}), 400
    
    payout_request.status = 'CANCELLED'
    db.session.commit()
    
    flash('Payout request cancelled.', 'info')
    return redirect(url_for('book_platform.admin_payout_requests'))


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
            user_role = 'investor'
    
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
    
    elif user_role == 'investor' and user_profile:
        investor_id = get_profile_id(user_profile, profile_type)
        investment = BookInvestment.query.filter_by(
            book_project_id=book_id,
            investor_id=investor_id
        ).first()
        if investment:
            payouts = InvestmentPayout.query.filter_by(
                investment_id=investment.id
            ).order_by(InvestmentPayout.created_at.desc()).all()
            user_earnings['total'] = investment.total_returns
            user_earnings['per_sale'] = payouts
    
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

# Investor Returns by Book
@book_bp.route('/investments/my-returns/<int:book_id>', methods=['GET'])
@login_required
def investor_returns_by_book(book_id):
    """Investor view of their returns for a specific book"""
    book = BookProject.query.get_or_404(book_id)
    user_profile, profile_type = get_user_profile()
    
    if not user_profile:
        flash('You need a profile to view investment returns.', 'error')
        return redirect(url_for('book_platform.setup_profile'))
    
    investor_id = get_profile_id(user_profile, profile_type)
    investment = BookInvestment.query.filter_by(
        book_project_id=book_id,
        investor_id=investor_id
    ).first_or_404()
    
    # Refresh investment to get latest total_returns
    db.session.refresh(investment)
    
    # Get all payouts for this investment
    payouts = InvestmentPayout.query.filter_by(
        investment_id=investment.id
    ).order_by(InvestmentPayout.created_at.desc()).all()
    
    logger.info(f"Investment returns page - Investment {investment.id}: status={investment.status.value}, total_returns=${investment.total_returns}, payouts={len(payouts)}")
    
    # Get sales data
    sales = BookSale.query.filter_by(
        book_project_id=book_id
    ).order_by(BookSale.created_at.desc()).all()
    
    # Match payouts to sales
    payouts_by_sale = {}
    for payout in payouts:
        if payout.distribution:
            sale_id = payout.distribution.source_sale_id
            payouts_by_sale[sale_id] = payout
    
    # Calculate ROI
    roi_percentage = (investment.total_returns / investment.amount * 100) if investment.amount > 0 else 0
    max_possible_return = investment.amount * investment.return_multiplier
    progress_to_cap = (investment.total_returns / max_possible_return * 100) if max_possible_return > 0 else 0
    
    return render_template('book_platform/investor_returns_book.html',
                         book=book,
                         investment=investment,
                         payouts=payouts,
                         sales=sales,
                         payouts_by_sale=payouts_by_sale,
                         roi_percentage=roi_percentage,
                         max_possible_return=max_possible_return,
                         progress_to_cap=progress_to_cap)

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
        can_first, msg_first = can_request_first_draft_release(book, campaign, db)
        can_pub, msg_pub = can_request_publication_release(book, campaign, db)
        first_amount = (campaign.current_funding * 0.5) if not campaign.author_first_draft_released else 0
        pub_amount = (campaign.current_funding * 0.5) if campaign.author_first_draft_released and not campaign.author_publication_released else 0
        fund_release = {
            'total_funding': campaign.current_funding,
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
    from glconnect.book_platform_models import AuthorCampaignPayoutRequest
    
    if milestone == 'first_draft':
        can_req, msg = can_request_first_draft_release(book, campaign, db)
        amount = campaign.current_funding * (FIRST_DRAFT_RELEASE_PERCENT / 100)
    else:
        can_req, msg = can_request_publication_release(book, campaign, db)
        amount = campaign.current_funding * (PUBLICATION_RELEASE_PERCENT / 100)
    
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


# Investor refund request (only before first draft is out)
@book_bp.route('/investments/<int:investment_id>/request-refund', methods=['POST'])
@login_required
def request_investment_refund(investment_id):
    """Investor requests refund - only allowed before first draft is completed (25k+ words)"""
    from glconnect.book_platform_models import BookInvestment, RefundRequest, TransactionStatus
    from glconnect.accountability_service import FIRST_DRAFT_MIN_WORDS
    
    investment = BookInvestment.query.options(
        joinedload(BookInvestment.book_project),
        joinedload(BookInvestment.campaign)
    ).get_or_404(investment_id)
    
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        return jsonify({'error': 'Profile required'}), 403
    
    investor_id = get_profile_id(user_profile, profile_type)
    if investment.investor_id != investor_id:
        return jsonify({'error': 'Not your investment'}), 403
    
    if investment.status == InvestmentStatus.REFUNDED:
        return jsonify({'error': 'Investment already refunded'}), 400
    
    # Check for existing pending refund
    pending = RefundRequest.query.filter_by(
        investment_id=investment_id,
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
        investment_id=investment_id,
        amount=investment.amount,
        currency=investment.currency or 'USD',
        reason='Investor requested refund (before first draft)',
        status=TransactionStatus.PENDING
    )
    db.session.add(refund)
    db.session.commit()
    
    logger.info(f"Investor refund request {refund.id} for investment {investment_id}")
    if request.is_json or request.content_type == 'application/json':
        return jsonify({
            'success': True,
            'message': f'Refund request of ${investment.amount:.2f} submitted. Admin will process it shortly.'
        })
    flash(f'Refund request of ${investment.amount:.2f} submitted. Admin will process it shortly.', 'success')
    return redirect(url_for('book_platform.investment_refund_status', investment_id=investment_id))


@book_bp.route('/investments/<int:investment_id>/refund-status', methods=['GET'])
@login_required
def investment_refund_status(investment_id):
    """View refund status for an investment"""
    from glconnect.book_platform_models import BookInvestment, RefundRequest
    
    investment = BookInvestment.query.options(
        joinedload(BookInvestment.book_project),
        joinedload(BookInvestment.campaign)
    ).get_or_404(investment_id)
    
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to view this page.', 'error')
        return redirect(url_for('book_platform.investments'))
    
    investor_id = get_profile_id(user_profile, profile_type)
    if investment.investor_id != investor_id:
        flash('You can only view your own investment refunds.', 'error')
        return redirect(url_for('book_platform.investments'))
    
    # Check if refund allowed (before first draft, no pending refund)
    from glconnect.accountability_service import FIRST_DRAFT_MIN_WORDS
    try:
        from glconnect.book_platform_routes import update_book_word_count
        update_book_word_count(investment.book_project)
    except Exception:
        pass
    word_count = (investment.book_project.word_count or 0)
    has_pending = any(r.status == TransactionStatus.PENDING for r in refunds)
    can_request_refund = (
        word_count < FIRST_DRAFT_MIN_WORDS
        and investment.status.value != 'refunded'
        and not has_pending
    )
    
    refunds = RefundRequest.query.filter_by(investment_id=investment_id).order_by(
        RefundRequest.created_at.desc()
    ).all()
    
    return render_template('book_platform/investment_refund_status.html',
                         investment=investment,
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
# UNIFIED CONTENT HUB - BLOGS, NEWS, FREELANCING
# ============================================================================

@book_bp.route('/content-hub')
@login_required
def content_hub():
    """
    Unified Content Hub - Access point for all content types:
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
    """yt-dlp → MP4 in static/ytautovid → DB → merge videolist.m3u for HLS TV."""
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
                output_folder = os.path.join(glconnect_dir, 'static', 'ytautovid')
                output_folder = os.path.normpath(output_folder)

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
                _set_tv_download_status('ingesting', 'Saving to database…', url=url, step=current_step)
                added, _ = PlaylistIngestion.ingest_videos_from_folder(output_folder, source_url=url)
                _set_tv_download_status(
                    'ingesting',
                    f'Saved to database. {added} new video(s).' if added > 0 else 'Saved (no new rows; duplicates or empty).',
                    url=url,
                    step=current_step,
                )

                current_step = 'playlist'
                _set_tv_download_status('ingesting', 'Writing TV playlist (videolist.m3u)…', url=url, step=current_step)
                npaths = sync_tv_videolist_from_db()
                _set_tv_download_status(
                    'ingesting',
                    f'Playlist updated: {npaths} path(s) in videolist.m3u.',
                    url=url,
                    step=current_step,
                )

                if added > 0:
                    _set_tv_download_status(
                        'completed',
                        f'Done. {added} new video(s); TV playlist has {npaths} entr(y/ies). Liquidsoap will reload if watch mode is on.',
                        url=url,
                        completed=True,
                        step=None,
                    )
                    logger.info("Admin TV download finished: %s new video(s), %s playlist paths", added, npaths)
                else:
                    _set_tv_download_status(
                        'completed',
                        'Completed but no new videos in DB (duplicates). Playlist refreshed.',
                        url=url,
                        completed=True,
                        step=None,
                    )
            except Exception as e:
                logger.exception("Admin TV download failed at step %s: %s", current_step, e)
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
    """Rewrite video/videolist.m3u from videolist_extra.m3u + downloaded_videos."""
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
