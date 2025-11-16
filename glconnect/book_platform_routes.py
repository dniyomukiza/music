"""
Ink Studio Routes - Flask routes for the Ink Studio functionality
This module contains all routes for Ink Studio including:
- Book creation and management
- Collaboration features
- Real-time editing
- Marketplace functionality
- User management
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import os
import uuid
import json
import logging
import re
from functools import wraps
from sqlalchemy.orm import joinedload

# Import models
from glconnect.models import db, User, Writer
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookChapter, BookCollaboration, 
    CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
    ChapterSuggestion, BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification,
    BookStatus, CollaborationRole, InvitationStatus, CommentStatus, TransactionStatus,
    AudioGenerationTask, AccreditedReviewer, BookReview, InvestmentCampaign, BookInvestment,
    RevenueDistribution, ReviewerEarning, InvestmentPayout, RefundRequest, ReviewerStatus, ReviewerLevel,
    ReviewStatus, InvestmentStatus, CampaignStatus, DistributionType
)

# Import additional modules
from glconnect.forms import DigitalBookUploadForm, ReviewerRegistrationForm, BookReviewForm, InvestmentCampaignForm, InvestmentForm
from glconnect.digital_book_processor import digital_book_processor
from glconnect.audio_book_generator import audio_book_generator
from glconnect.revenue_distribution_service import distribute_revenue
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
    """Recalculate and update the book's total word count from all chapters"""
    try:
        # Ensure all chapters have their word count calculated
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
    """Check if a book is ready for investment and return readiness status"""
    issues = []
    
    if not book.title or len(book.title.strip()) < 3:
        issues.append("Book must have a title (at least 3 characters)")
    if not book.description or len(book.description.strip()) < 50:
        issues.append("Book must have a description (at least 50 characters)")
    if not book.genre:
        issues.append("Book must have a genre selected")
    if not book.language:
        issues.append("Book must have a language selected")
    
    # Check if book has at least one chapter
    chapter_count = len(book.chapters) if book.chapters else 0
    if chapter_count == 0:
        issues.append("Book must have at least one chapter")
    
    # Ensure word count is up to date before checking
    update_book_word_count(book)
    
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
    """Decorator that requires Writer profile (primary) or BookPlatformUser profile (legacy) for Ink Studio access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('routes1.login'))
        
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
    """Ink Studio access point - role-aware redirects for authors."""
    if not current_user.is_authenticated:
        flash('Please log in to access Ink Studio', 'info')
        return redirect(url_for('routes1.login'))

    # Resolve existing profiles
    writer = Writer.query.filter_by(user_id=current_user.user_id).first()
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()

    # Author-specific behavior: require setup if no profile yet
    if getattr(current_user, 'role', None) == 'author':
        if writer or book_user:
            return redirect(url_for('book_platform.dashboard'))
        flash('Please set up your author profile to access Ink Studio.', 'info')
        return redirect(url_for('book_platform.setup_profile'))

    # Non-authors: keep existing fallback behavior
    if writer or book_user:
        return redirect(url_for('book_platform.dashboard'))
    flash('You need a writer profile to access Ink Studio. Please create a writer profile first.', 'info')
    return redirect(url_for('writer.writer_profile'))

# Main dashboard route
@book_bp.route('/')
@writer_or_book_platform_required
def dashboard(user_profile, profile_type):
    """Main Ink Studio dashboard - Writer profiles are primary users"""
    
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
    
    # Determine if user is an author (has writer/book platform profile, not just authored books)
    # Users with writer or book platform profiles are considered authors even if they haven't created books yet
    is_author = profile_type == 'writer' or (profile_type == 'book_platform' and book_user is not None)
    
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
                         user_investments=user_investments)

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
    """List all user's books"""
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    
    # Get the correct author_id (BookPlatformUser.id for consistency)
    author_id = get_profile_id(user_profile, profile_type)
    
    # Query books with eager loading of author information to ensure fresh data
    books = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).filter_by(author_id=author_id).all()
    
    # Calculate investment readiness for each book
    books_with_readiness = []
    for book in books:
        readiness = check_investment_readiness(book)
        books_with_readiness.append({
            'book': book,
            'investment_readiness': readiness
        })
    
    return render_template('book_platform/books.html', books_with_readiness=books_with_readiness)

@book_bp.route('/books/create', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_book(user_profile, profile_type):
    """Create a new book project - Writer profiles are primary users"""
    if request.method == 'POST':
        data = request.get_json()
        
        # Get the correct author_id (BookPlatformUser.id)
        author_id = get_profile_id(user_profile, profile_type)
        
        book = BookProject(
            title=data['title'],
            description=data.get('description'),
            genre=data.get('genre'),
            language=data.get('language'),
            target_audience=data.get('target_audience'),
            author_id=author_id
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
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).get_or_404(book_id)
    
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
    
    # Ensure book word count is up to date
    update_book_word_count(book)
    db.session.commit()
    
    # Check investment readiness
    investment_readiness = check_investment_readiness(book)
    
    return render_template('book_platform/view_book.html', 
                         book=book, 
                         chapters=chapters,
                         collaborations=collaborations,
                         is_author=is_author,
                         is_collaborator=is_collaborator,
                         investment_readiness=investment_readiness)

@book_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@writer_or_book_platform_required
def edit_book(book_id, user_profile, profile_type):
    """Edit book details"""
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    
    # Eager load author information to ensure fresh data from database
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).get_or_404(book_id)
    
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
            
            # Update book fields
            book.title = data['title']
            book.description = data.get('description', '')
            book.genre = data.get('genre', '')
            book.language = data.get('language', '')
            book.target_audience = data.get('target_audience', '')
            book.price = float(data.get('price', 0)) if data.get('price') else None
            book.word_count_target = int(data.get('word_count_target', 0)) if data.get('word_count_target') else None
            book.tags = data.get('tags', '')
            book.cover_image = data.get('cover_image', '')
            book.is_published = data.get('is_published') == 'on' or data.get('is_published') == True
            book.allow_collaboration = data.get('allow_collaboration') == 'on' or data.get('allow_collaboration') == True
            book.updated_at = datetime.now(timezone.utc)
            
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

        # Get the correct author ID based on profile type
        author_id = get_profile_id(user_profile, profile_type)
        
        # Debug logging and error handling
        if author_id is None:
            print(f"ERROR: get_profile_id returned None for user_id={current_user.user_id}, profile_type={profile_type}")
            return jsonify({'error': 'Profile configuration error. Please ensure you have a Writer or Ink Studio profile.'}), 403

        # Check if user is the author of the book
        if book.author_id != author_id:
            print(f"Permission denied: book.author_id={book.author_id}, user author_id={author_id}, user_id={current_user.user_id}")
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
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user has permission
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        return jsonify({'error': 'Ink Studio profile required'}), 403
    
    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'error': 'You can only generate audiobooks for your own books'}), 403
    
    # Check if book already has audiobook
    if book.has_audiobook:
        return jsonify({'error': 'This book already has an audiobook version'}), 400
    
    # Get request data
    data = request.get_json()
    audiobook_price = data.get('audiobook_price', 0.0)
    voice_name = data.get('voice_name', 'en-US-Standard-A')
    
    try:
        # Extract text from all published chapters
        chapters = BookChapter.query.filter_by(
            book_project_id=book_id,
            is_published=True
        ).order_by(BookChapter.chapter_number).all()
        
        if not chapters:
            return jsonify({'error': 'No published chapters found. Publish at least one chapter before generating audiobook.'}), 400
        
        # Combine all chapter content
        full_text = ""
        for chapter in chapters:
            if chapter.content:
                # Clean HTML content and extract text
                import re
                clean_content = re.sub(r'<[^>]+>', '', chapter.content)
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                full_text += f"Chapter {chapter.chapter_number}: {chapter.title}\n\n{clean_content}\n\n"
        
        if not full_text.strip():
            return jsonify({'error': 'No text content found in published chapters'}), 400
        
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
                
                # Generate audiobook
                audio_result = audio_book_generator.generate_audiobook(
                    full_text,
                    book.id,
                    voice_name
                )
                
                if audio_result['success']:
                    # Update book with audiobook info
                    book.has_audiobook = True
                    book.audiobook_file_path = audio_result['audio_file_path']
                    book.audiobook_price = audiobook_price
                    book.audiobook_duration = audio_result['duration']
                    book.audiobook_generated_at = datetime.now(timezone.utc)
                    book.audiobook_voice = voice_name
                    
                    # Update task
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
                logger.error(f"Error in background audiobook generation: {str(e)}")
                audio_task.status = 'failed'
                audio_task.error_message = str(e)
                db.session.commit()
        
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
        logger.error(f"Error starting audiobook generation for book {book_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    invitations = CollaborationInvitation.query.filter_by(
        collaboration_id=BookCollaboration.query.filter_by(book_project_id=book_id).first().id
    ).all() if collaborations else []
    
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
    
    # Create collaboration
    collaboration = BookCollaboration(
        book_project_id=book_id,
        collaborator_id=book_user.id,  # Placeholder until invitation is accepted
        role=CollaborationRole(data['role'])
    )
    db.session.add(collaboration)
    db.session.flush()  # Get the ID
    
    # Create invitation
    invitation = CollaborationInvitation(
        collaboration_id=collaboration.id,
        invited_by_id=book_user.id,
        email=data['email'],
        role=CollaborationRole(data['role']),
        message=data.get('message'),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    db.session.add(invitation)
    db.session.commit()
    
    # TODO: Send email invitation
    
    return jsonify({'success': True, 'invitation_id': invitation.id})

@book_bp.route('/invitations/<string:invitation_uuid>')
def accept_invitation(invitation_uuid):
    """Accept collaboration invitation"""
    invitation = CollaborationInvitation.query.filter_by(uuid=invitation_uuid).first_or_404()
    
    if invitation.status != InvitationStatus.PENDING:
        flash('This invitation is no longer valid', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    if invitation.expires_at < datetime.now(timezone.utc):
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

# Marketplace routes
@book_bp.route('/marketplace')
@login_required
def marketplace():
    """Browse published books in marketplace - accessible to all logged-in users"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Limit to 20 books per page
        
        # Get filter parameters
        genre = request.args.get('genre', None)
        language = request.args.get('language', None)
        search_term = request.args.get('search', None)
        
        # Use optimized database queries with pagination and filters
        books = DatabaseOptimizer.get_marketplace_books(limit=per_page, genre=genre, language=language, search_term=search_term)
        
        # Get available genres and languages with book counts
        available_genres = DatabaseOptimizer.get_available_genres()
        available_languages = DatabaseOptimizer.get_available_languages()
        
        # Check if user has writer profile for conditional UI elements
        has_writer_profile = Writer.query.filter_by(user_id=current_user.user_id).first() is not None
        
        return render_template('book_platform/marketplace.html', 
                             books=books, 
                             has_writer_profile=has_writer_profile,
                             page=page,
                             per_page=per_page,
                             selected_genre=genre,
                             selected_language=language,
                             available_genres=available_genres,
                             available_languages=available_languages,
                             search_term=search_term)
    except Exception as e:
        print(f"Marketplace error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty list on error
        return render_template('book_platform/marketplace.html', 
                             books=[], 
                             has_writer_profile=False,
                             page=1,
                             per_page=20,
                             selected_genre=None,
                             selected_language=None,
                             available_genres=[],
                             available_languages=[],
                             search_term=None)

@book_bp.route('/books/<int:book_id>/publish', methods=['POST'])
@book_platform_required
def publish_book(book_id):
    """Publish a book to marketplace"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author can publish
    if book.author_id != book_user.id:
        return jsonify({'error': 'Only the author can publish the book'}), 403
    
    # Validate book is ready for publishing
    if not book.price or book.price <= 0:
        return jsonify({'error': 'Please set a price before publishing'}), 400
    
    book.status = BookStatus.PUBLISHED
    book.published_at = datetime.now(timezone.utc)
    
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

@book_bp.route('/admin/books')
@login_required
def admin_books():
    """Admin panel to manage all books"""
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('book_platform.marketplace'))
    
    # Use optimized database queries
    books = DatabaseOptimizer.get_admin_books_data()
    
    return render_template('book_platform/admin_books.html', books=books)

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
    # Ensure BookPlatformUser is accessible (import at function level to avoid scoping issues)
    from glconnect.book_platform_models import BookPlatformUser
    
    # Eager load author information to ensure fresh data from database
    book = BookProject.query.options(
        joinedload(BookProject.author).joinedload(BookPlatformUser.user)
    ).get_or_404(book_id)
    
    # Get user profile (Writer or BookPlatformUser) - if no profile, create a temporary one for purchase
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        # For users without profiles, create a temporary profile for purchase tracking
        class TempUserProfile:
            def __init__(self, user_id):
                self.id = user_id  # Use user_id as the ID for purchase tracking
                self.user_id = user_id
        
        user_profile = TempUserProfile(current_user.user_id)
        profile_type = 'temp'
    
    # Can't buy your own book (only applies to users with Writer/BookPlatformUser profiles)
    if profile_type in ['writer', 'book_platform'] and book.author_id == get_profile_id(user_profile, profile_type):
        return jsonify({'error': 'You cannot purchase your own book'}), 400
    
    # Check if already purchased
    existing_purchase = BookPurchase.query.filter_by(
        buyer_id=get_profile_id(user_profile, profile_type),
        book_project_id=book_id,
        status=TransactionStatus.COMPLETED
    ).first()
    
    if existing_purchase:
        return jsonify({'error': 'You have already purchased this book'}), 400
    
    # Create purchase record
    purchase = BookPurchase(
        buyer_id=get_profile_id(user_profile, profile_type),
        book_project_id=book_id,
        amount=book.price,
        currency=book.currency,
        status=TransactionStatus.PENDING
    )
    
    db.session.add(purchase)
    db.session.commit()
    
    # TODO: Integrate with payment processor (Stripe, PayPal, etc.)
    # For now, mark as completed
    purchase.status = TransactionStatus.COMPLETED
    purchase.purchased_at = datetime.now(timezone.utc)
    
    # Create sale record for author
    royalty_percentage = 0.7  # 70% to author, 30% platform fee
    royalty_amount = book.price * royalty_percentage
    platform_fee = book.price - royalty_amount
    
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
        paid_at=datetime.now(timezone.utc)
    )
    
    db.session.add(sale)
    db.session.commit()
    
    # Trigger revenue distribution
    try:
        from glconnect.revenue_distribution_service import distribute_revenue
        distribution_result = distribute_revenue(sale, db)
        if not distribution_result.get('success'):
            logger.warning(f"Revenue distribution failed for sale {sale.id}: {distribution_result.get('error')}")
    except Exception as e:
        logger.error(f"Error triggering revenue distribution for sale {sale.id}: {str(e)}", exc_info=True)
        # Don't fail the purchase if distribution fails - it can be retried later
    
    return jsonify({'success': True, 'purchase_id': purchase.id})

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
    """Upload and process digital book files"""
    
    form = DigitalBookUploadForm()
    
    if form.validate_on_submit():
        try:
            # Get user profile
            user_profile, profile_type = get_user_profile()
            author_id = get_profile_id(user_profile, profile_type)
            
            # Handle file uploads
            digital_file = form.digital_book_file.data
            cover_image = form.cover_image.data
            
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
            
            # Save cover image if provided
            cover_path = None
            if cover_image:
                cover_filename = secure_filename(cover_image.filename)
                cover_name, cover_ext = os.path.splitext(cover_filename)
                unique_cover_filename = f"{cover_name}_{uuid.uuid4().hex[:8]}{cover_ext}"
                cover_path = os.path.join(covers_dir, unique_cover_filename)
                cover_image.save(cover_path)
                cover_path = f"book_covers/{unique_cover_filename}"
            
            # Extract text from digital book
            extraction_result = digital_book_processor.extract_text(digital_file_path, file_type)
            
            if not extraction_result['success']:
                flash(f"Failed to extract text from file: {extraction_result['error']}", "error")
                return render_template('book_platform/upload_digital_book.html', form=form)
            
            # Create book project
            book = BookProject(
                title=form.title.data,
                description=form.description.data,
                genre=form.genre.data,
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
            db.session.commit()
            
            # Generate audiobook if requested
            if form.generate_audiobook.data and form.audiobook_price.data:
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
                        
                        # Generate audiobook
                        audio_result = audio_book_generator.generate_audiobook(
                            extraction_result['text'],
                            book.id,
                            form.audiobook_voice.data
                        )
                        
                        if audio_result['success']:
                            # Update book with audiobook info
                            book.has_audiobook = True
                            book.audiobook_file_path = audio_result['audio_file_path']
                            book.audiobook_price = form.audiobook_price.data
                            book.audiobook_duration = audio_result['duration']
                            book.audiobook_generated_at = datetime.now(timezone.utc)
                            book.audiobook_voice = form.audiobook_voice.data
                            
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
            
            return redirect(url_for('book_platform.book_detail', book_id=book.id))
            
        except Exception as e:
            flash(f"Error uploading book: {str(e)}", "error")
            logger.error(f"Error in upload_digital_book: {str(e)}")
    
    return render_template('book_platform/upload_digital_book.html', form=form)

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
    """Download digital book file"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user has purchased this book
    user_profile, profile_type = get_user_profile()
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        
        # Check if user is the author
        if book.author_id == author_id:
            # Author can always download
            pass
        else:
            # Check if user has purchased the book
            purchase = BookPurchase.query.filter_by(
                buyer_id=author_id,
                book_project_id=book_id,
                status=TransactionStatus.COMPLETED
            ).first()
            
            if not purchase:
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

@book_bp.route('/books/<int:book_id>/download-audio')
@login_required
def download_audio_book(book_id):
    """Download audio book file"""
    book = BookProject.query.get_or_404(book_id)
    
    if not book.has_audiobook or not book.audiobook_file_path:
        flash("Audiobook not available for this book.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    # Check if user has purchased this book (same logic as digital download)
    user_profile, profile_type = get_user_profile()
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        
        # Check if user is the author
        if book.author_id == author_id:
            # Author can always download
            pass
        else:
            # Check if user has purchased the book
            purchase = BookPurchase.query.filter_by(
                buyer_id=author_id,
                book_project_id=book_id,
                status=TransactionStatus.COMPLETED
            ).first()
            
            if not purchase:
                flash("You must purchase this book to download it.", "error")
                return redirect(url_for('book_platform.marketplace'))
    
    # Serve the audio file
    if not os.path.exists(book.audiobook_file_path):
        flash("Audiobook file not found.", "error")
        return redirect(url_for('book_platform.marketplace'))
    
    return send_from_directory(
        os.path.dirname(book.audiobook_file_path),
        os.path.basename(book.audiobook_file_path),
        as_attachment=True,
        download_name=f"{book.title}_audiobook.mp3"
    )

# ============================================================================
# REVIEWER & INVESTMENT SYSTEM ROUTES
# ============================================================================

# Reviewer Registration
@book_bp.route('/reviewers/register', methods=['GET', 'POST'])
@login_required
def register_reviewer():
    """Register as an accredited reviewer"""
    # Check if already registered
    existing_reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    if existing_reviewer:
        flash('You are already registered as a reviewer.', 'info')
        return redirect(url_for('book_platform.reviewer_profile', reviewer_id=existing_reviewer.id))
    
    form = ReviewerRegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Parse specialties
            specialties = []
            if form.specialties.data:
                specialties = [s.strip() for s in form.specialties.data.split(',') if s.strip()]
            
            # Handle profile picture upload
            profile_picture_path = None
            if form.profile_picture.data and form.profile_picture.data.filename:
                upload_folder = os.path.join(current_app.root_path, 'static', 'reviewer_uploads')
                os.makedirs(upload_folder, exist_ok=True)
                filename = secure_filename(form.profile_picture.data.filename)
                filepath = os.path.join(upload_folder, filename)
                form.profile_picture.data.save(filepath)
                profile_picture_path = f"reviewer_uploads/{filename}"
            
            # Create reviewer profile
            reviewer = AccreditedReviewer(
                user_id=current_user.user_id,
                reviewer_name=form.reviewer_name.data,
                bio=form.bio.data,
                profile_picture=profile_picture_path,
                portfolio_url=form.portfolio_url.data,
                specialties=specialties if specialties else None,
                credentials=form.credentials.data,
                default_revenue_share_percentage=form.default_revenue_share.data or 2.5,
                accreditation_status=ReviewerStatus.PENDING
            )
            
            db.session.add(reviewer)
            db.session.commit()
            
            flash('Reviewer application submitted! It will be reviewed by our team.', 'success')
            return redirect(url_for('book_platform.reviewers'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering reviewer: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('book_platform/register_reviewer.html', form=form)

# Reviewer Marketplace
@book_bp.route('/reviewers', methods=['GET'])
def reviewers():
    """Browse accredited reviewers"""
    status_filter = request.args.get('status', 'accredited')
    genre_filter = request.args.get('genre', '')
    search_query = request.args.get('q', '')
    
    query = AccreditedReviewer.query
    
    if status_filter == 'accredited':
        query = query.filter_by(accreditation_status=ReviewerStatus.ACCREDITED)
    elif status_filter == 'all':
        pass  # Show all
    
    if genre_filter:
        query = query.filter(AccreditedReviewer.specialties.contains([genre_filter]))
    
    if search_query:
        query = query.filter(
            db.or_(
                AccreditedReviewer.reviewer_name.ilike(f'%{search_query}%'),
                AccreditedReviewer.bio.ilike(f'%{search_query}%')
            )
        )
    
    reviewers_list = query.order_by(AccreditedReviewer.average_rating.desc()).all()
    
    return render_template('book_platform/reviewers.html', 
                         reviewers=reviewers_list,
                         status_filter=status_filter,
                         genre_filter=genre_filter,
                         search_query=search_query)

# Reviewer Profile
@book_bp.route('/reviewers/<int:reviewer_id>', methods=['GET'])
def reviewer_profile(reviewer_id):
    """View reviewer profile"""
    reviewer = AccreditedReviewer.query.get_or_404(reviewer_id)
    reviews = BookReview.query.filter_by(reviewer_id=reviewer_id, status=ReviewStatus.PUBLISHED).all()
    
    return render_template('book_platform/reviewer_profile.html', reviewer=reviewer, reviews=reviews)

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
    
    if request.method == 'POST':
        reviewer_id = request.form.get('reviewer_id')
        if reviewer_id:
            reviewer = AccreditedReviewer.query.get(reviewer_id)
            if reviewer and reviewer.accreditation_status == ReviewerStatus.ACCREDITED:
                # Create a review request (could be a notification or separate model)
                flash(f'Review request sent to {reviewer.reviewer_name}. They will be notified.', 'success')
                return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    # Get available reviewers
    available_reviewers = AccreditedReviewer.query.filter_by(
        accreditation_status=ReviewerStatus.ACCREDITED
    ).all()
    
    return render_template('book_platform/request_review.html', 
                         book=book, 
                         reviewers=available_reviewers)

# Submit Review
@book_bp.route('/books/<int:book_id>/reviews/submit', methods=['GET', 'POST'])
@login_required
def submit_review(book_id):
    """Reviewer submits a review for a book"""
    book = BookProject.query.get_or_404(book_id)
    
    # Check if user is an accredited reviewer
    reviewer = AccreditedReviewer.query.filter_by(user_id=current_user.user_id).first()
    if not reviewer or reviewer.accreditation_status != ReviewerStatus.ACCREDITED:
        flash('You must be an accredited reviewer to submit reviews.', 'error')
        return redirect(url_for('book_platform.register_reviewer'))
    
    # Check if already reviewed
    existing_review = BookReview.query.filter_by(
        book_project_id=book_id,
        reviewer_id=reviewer.id
    ).first()
    
    if existing_review:
        flash('You have already submitted a review for this book.', 'info')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    form = BookReviewForm()
    
    if form.validate_on_submit():
        try:
            review = BookReview(
                book_project_id=book_id,
                reviewer_id=reviewer.id,
                title=form.title.data,
                content=form.content.data,
                rating=form.rating.data,
                revenue_share_percentage=form.revenue_share_percentage.data,
                minimum_sales_threshold=form.minimum_sales_threshold.data or 0,
                is_public=form.is_public.data,
                status=ReviewStatus.SUBMITTED,
                submitted_at=datetime.now(timezone.utc)
            )
            
            db.session.add(review)
            
            # Update reviewer stats
            reviewer.total_reviews += 1
            
            db.session.commit()
            
            flash('Review submitted successfully! It will be published after author approval.', 'success')
            return redirect(url_for('book_platform.view_book', book_id=book_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting review: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('book_platform/submit_review.html', form=form, book=book)

# Investment Campaign Creation
@book_bp.route('/books/<int:book_id>/create-campaign', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_investment_campaign(book_id, user_profile, profile_type):
    """Author creates an investment campaign for their book"""
    book = BookProject.query.get_or_404(book_id)
    author_id = get_profile_id(user_profile, profile_type)
    
    if book.author_id != author_id:
        flash('You can only create campaigns for your own books.', 'error')
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
    """Browse investment campaigns - only shows campaigns for published books"""
    status_filter = request.args.get('status', 'active')
    search_query = request.args.get('q', '')
    
    # Join with BookProject to filter by book status and enable search
    query = InvestmentCampaign.query.join(BookProject).filter(
        BookProject.status == BookStatus.PUBLISHED  # Only show campaigns for published books
    )
    
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
    campaign = InvestmentCampaign.query.get_or_404(campaign_id)
    book = campaign.book_project
    investments = BookInvestment.query.filter_by(campaign_id=campaign_id).all()
    
    # Calculate progress
    progress_percentage = (campaign.current_funding / campaign.funding_goal * 100) if campaign.funding_goal > 0 else 0
    
    # Get author information
    author = book.author if book else None
    
    # Get book reviews (accredited reviews)
    from glconnect.book_platform_models import BookReview, ReviewStatus
    accredited_reviews = BookReview.query.filter_by(
        book_project_id=book.id,
        status=ReviewStatus.PUBLISHED
    ).all() if book else []
    
    # Calculate average rating
    avg_rating = sum(r.rating for r in accredited_reviews) / len(accredited_reviews) if accredited_reviews else 0
    
    # Get book chapters count and completed chapters
    chapters_count = len(book.chapters) if book and book.chapters else 0
    completed_chapters = [ch for ch in book.chapters if ch.content] if book and book.chapters else []
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
    
    return render_template('book_platform/campaign_details.html', 
                         campaign=campaign,
                         book=book,
                         investments=investments,
                         progress_percentage=progress_percentage,
                         author=author,
                         accredited_reviews=accredited_reviews,
                         avg_rating=avg_rating,
                         chapters_count=chapters_count,
                         completed_chapters=completed_chapters[:3],  # First 3 for preview
                         completed_chapters_count=completed_chapters_count,
                         days_remaining=days_remaining,
                         author_other_books=author_other_books)

# Make Investment
@book_bp.route('/investments/<int:campaign_id>/invest', methods=['GET', 'POST'])
@login_required
def make_investment(campaign_id):
    """User invests in a campaign"""
    campaign = InvestmentCampaign.query.get_or_404(campaign_id)
    
    if campaign.status != CampaignStatus.ACTIVE:
        flash('This campaign is not currently accepting investments.', 'error')
        return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # Check if campaign has expired
    if campaign.end_date:
        # Ensure end_date is timezone-aware for comparison
        end_date = campaign.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        if end_date < datetime.now(timezone.utc):
            flash('This campaign has expired.', 'error')
            return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
    
    # Get user profile
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to invest.', 'error')
        return redirect(url_for('book_platform.setup_profile'))
    
    investor_id = get_profile_id(user_profile, profile_type)
    
    # Check if already invested
    existing_investment = BookInvestment.query.filter_by(
        campaign_id=campaign_id,
        investor_id=investor_id
    ).first()
    
    form = InvestmentForm()
    
    if form.validate_on_submit():
        try:
            amount = form.amount.data
            
            # Validate amount
            if amount < campaign.minimum_investment:
                flash(f'Minimum investment is ${campaign.minimum_investment:.2f}', 'error')
                return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
            
            if campaign.maximum_investment and amount > campaign.maximum_investment:
                flash(f'Maximum investment is ${campaign.maximum_investment:.2f}', 'error')
                return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
            
            # Check if goal would be exceeded
            if campaign.current_funding + amount > campaign.funding_goal:
                flash(f'Investment would exceed the funding goal. Maximum remaining: ${campaign.funding_goal - campaign.current_funding:.2f}', 'error')
                return render_template('book_platform/make_investment.html', form=form, campaign=campaign)
            
            # Calculate investment percentage
            investment_percentage = (amount / campaign.funding_goal) * 100
            
            # Create investment
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
            
            # Update campaign funding
            campaign.current_funding += amount
            
            # Check if goal reached
            if campaign.current_funding >= campaign.funding_goal:
                campaign.status = CampaignStatus.FUNDED
                campaign.funded_at = datetime.now(timezone.utc)
                # Set return start date (when book is published)
                for inv in campaign.investments:
                    inv.return_start_date = datetime.now(timezone.utc)
                    inv.status = InvestmentStatus.ACTIVE
            
            db.session.commit()
            
            # TODO: Integrate with payment processor (Stripe)
            # For now, mark as confirmed
            investment.payment_status = TransactionStatus.COMPLETED
            investment.status = InvestmentStatus.CONFIRMED
            investment.invested_at = datetime.now(timezone.utc)
            db.session.commit()
            
            flash('Investment successful! Thank you for supporting this book.', 'success')
            return redirect(url_for('book_platform.investment_campaign', campaign_id=campaign_id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error making investment: {str(e)}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('book_platform/make_investment.html', form=form, campaign=campaign)

# Earnings Dashboard
@book_bp.route('/earnings', methods=['GET'])
@login_required
def earnings_dashboard():
    """View earnings for reviewers, investors, and authors"""
    user_profile, profile_type = get_user_profile()
    
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
    
    # Investment returns
    if user_profile:
        investor_id = get_profile_id(user_profile, profile_type)
        investments = BookInvestment.query.filter_by(investor_id=investor_id).all()
        earnings_data['investments'] = investments
        earnings_data['total_investment_returns'] = sum(inv.total_returns for inv in investments)
        
        # Get payout history for each investment
        for investment in investments:
            investment.payouts_list = InvestmentPayout.query.filter_by(
                investment_id=investment.id
            ).order_by(InvestmentPayout.created_at.desc()).limit(20).all()
    
    # Author sales
    if user_profile:
        author_id = get_profile_id(user_profile, profile_type)
        sales = BookSale.query.filter_by(seller_id=author_id).order_by(
            BookSale.created_at.desc()
        ).limit(50).all()
        earnings_data['author_sales'] = sales
        earnings_data['total_author_revenue'] = sum(sale.net_amount for sale in sales)
        
        # Group sales by book
        sales_by_book = defaultdict(lambda: {'sales': [], 'total': 0.0, 'book': None})
        for sale in sales:
            book_id = sale.book_project_id
            sales_by_book[book_id]['sales'].append(sale)
            sales_by_book[book_id]['total'] += sale.net_amount
            if not sales_by_book[book_id]['book']:
                sales_by_book[book_id]['book'] = sale.book_project
        earnings_data['author_sales_by_book'] = dict(sales_by_book)
    
    return render_template('book_platform/earnings.html', earnings_data=earnings_data)

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
    
    # Get all payouts for this investment
    payouts = InvestmentPayout.query.filter_by(
        investment_id=investment.id
    ).order_by(InvestmentPayout.created_at.desc()).all()
    
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
    from glconnect.accountability_service import get_accountability_status
    status_result = get_accountability_status(book_id, db)
    
    if not status_result.get('success'):
        flash('Error loading accountability status.', 'error')
        return redirect(url_for('book_platform.view_book', book_id=book_id))
    
    return render_template('book_platform/accountability_status.html',
                         book=book,
                         status=status_result.get('status'))

@book_bp.route('/investments/<int:investment_id>/refund-status', methods=['GET'])
@login_required
def investment_refund_status(investment_id):
    """View refund status for an investment"""
    from glconnect.book_platform_models import BookInvestment, RefundRequest
    
    investment = BookInvestment.query.get_or_404(investment_id)
    
    # Check if user is the investor
    user_profile, profile_type = get_user_profile()
    if not user_profile:
        flash('You need a profile to view this page.', 'error')
        return redirect(url_for('book_platform.investments'))
    
    investor_id = get_profile_id(user_profile, profile_type)
    if investment.investor_id != investor_id:
        flash('You can only view your own investment refunds.', 'error')
        return redirect(url_for('book_platform.investments'))
    
    # Get refund requests
    refunds = RefundRequest.query.filter_by(
        investment_id=investment_id
    ).order_by(RefundRequest.created_at.desc()).all()
    
    return render_template('book_platform/investment_refund_status.html',
                         investment=investment,
                         refunds=refunds)
