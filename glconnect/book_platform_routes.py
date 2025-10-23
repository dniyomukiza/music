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
from functools import wraps

# Import models
from glconnect.models import db, User, Writer
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookChapter, BookCollaboration, 
    CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
    BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification,
    BookStatus, CollaborationRole, InvitationStatus, CommentStatus, TransactionStatus
)

# Create blueprint
book_bp = Blueprint('book_platform', __name__, url_prefix='/mybook')

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

# Helper decorators
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
    """Get the correct ID based on profile type"""
    if profile_type == 'book_platform':
        return user_profile.id
    elif profile_type == 'writer':
        return user_profile.writer_id
    elif profile_type == 'temp':
        return user_profile.user_id
    else:
        return None

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
    """Ink Studio access point - redirects writers to dashboard, others to login"""
    if not current_user.is_authenticated:
        flash('Please log in to access Ink Studio', 'info')
        return redirect(url_for('routes1.login'))
    
    # Check if user has writer profile
    writer = current_user.writer_profiles.first()
    if writer:
        # Writer - redirect to Ink Studio dashboard
        return redirect(url_for('book_platform.dashboard'))
    else:
        # Non-writer - redirect to writer profile creation
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
        
        # Get books authored by this writer (from BookProject table)
        authored_books = BookProject.query.filter_by(author_id=book_user.id).all()
        
        # Get collaborations (if any)
        collaborations = BookCollaboration.query.filter_by(
            collaborator_id=book_user.id, 
            is_active=True
        ).all()
        
        # Get recent notifications (if any)
        notifications = BookNotification.query.filter_by(
            user_id=book_user.id,
            is_read=False
        ).order_by(BookNotification.created_at.desc()).limit(5).all()
        
    else:
        # For BookPlatformUsers (legacy), use existing logic
        book_user = user_profile
        authored_books = BookProject.query.filter_by(author_id=book_user.id).all()
        collaborations = BookCollaboration.query.filter_by(
            collaborator_id=book_user.id, 
            is_active=True
        ).all()
        notifications = BookNotification.query.filter_by(
            user_id=book_user.id,
            is_read=False
        ).order_by(BookNotification.created_at.desc()).limit(5).all()
    
    return render_template('book_platform/dashboard.html', 
                         authored_books=authored_books,
                         collaborations=collaborations,
                         notifications=notifications,
                         user_profile=book_user,
                         profile_type=profile_type)

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
    # Get the correct ID based on profile type
    author_id = get_profile_id(user_profile, profile_type)
    
    # If user has Writer profile, ensure they have a BookPlatformUser profile
    if profile_type == 'writer':
        book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
        if not book_platform_user:
            # Create BookPlatformUser for Writer
            book_platform_user = BookPlatformUser(
                user_id=current_user.user_id,
                pen_name=user_profile.writer_name,
                bio=user_profile.bio,
                profile_picture=user_profile.profile_picture
            )
            db.session.add(book_platform_user)
            db.session.commit()
            author_id = book_platform_user.id
        else:
            author_id = book_platform_user.id
    
    books = BookProject.query.filter_by(author_id=author_id).all()
    return render_template('book_platform/books.html', books=books)

@book_bp.route('/books/create', methods=['GET', 'POST'])
@writer_or_book_platform_required
def create_book(user_profile, profile_type):
    """Create a new book project - Writer profiles are primary users"""
    if request.method == 'POST':
        data = request.get_json()
        
        # Get the correct ID based on profile type
        author_id = get_profile_id(user_profile, profile_type)
        
        # If user has Writer profile, ensure they have a BookPlatformUser profile
        if profile_type == 'writer':
            book_platform_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
            if not book_platform_user:
                # Create BookPlatformUser for Writer
                book_platform_user = BookPlatformUser(
                    user_id=current_user.user_id,
                    pen_name=user_profile.writer_name,
                    bio=user_profile.bio,
                    profile_picture=user_profile.profile_picture
                )
                db.session.add(book_platform_user)
                db.session.flush()  # Get the ID without committing
                author_id = book_platform_user.id
            else:
                author_id = book_platform_user.id
        
        book = BookProject(
            title=data['title'],
            description=data.get('description'),
            genre=data.get('genre'),
            target_audience=data.get('target_audience'),
            author_id=author_id
        )
        
        db.session.add(book)
        db.session.commit()
        
        return jsonify({'success': True, 'book_id': book.id})
    
    return render_template('book_platform/create_book.html')

@book_bp.route('/books/<int:book_id>')
@book_platform_required
def view_book(book_id):
    """View book details and chapters"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Check access
    collaboration = BookCollaboration.query.filter_by(
        book_project_id=book_id, 
        collaborator_id=book_user.id,
        is_active=True
    ).first()
    
    if book.author_id != book_user.id and not collaboration:
        flash('Access denied', 'error')
        return redirect(url_for('book_platform.dashboard'))
    
    chapters = BookChapter.query.filter_by(book_project_id=book_id).order_by(BookChapter.chapter_number).all()
    collaborations = BookCollaboration.query.filter_by(book_project_id=book_id, is_active=True).all()
    
    return render_template('book_platform/view_book.html', 
                         book=book, 
                         chapters=chapters,
                         collaborations=collaborations)

@book_bp.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
@book_platform_required
def edit_book(book_id):
    """Edit book details"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author can edit book details
    if book.author_id != book_user.id:
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
            
            chapter = BookChapter(
                title=data['title'],
                content=data.get('content', ''),
                summary=data.get('summary', ''),
                chapter_number=chapter_number,
                word_count_target=int(data.get('word_count_target', 0)) if data.get('word_count_target') else None,
                book_project_id=book_id,
                is_published=data.get('is_published') == 'on' or data.get('is_published') == True
            )
            
            db.session.add(chapter)
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
@book_platform_required
def edit_chapter(book_id, chapter_id):
    """Edit chapter - GET shows form, POST saves changes"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)
    
    # Check if user has permission to edit this chapter
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        flash('Ink Studio profile required', 'error')
        return redirect(url_for('book_platform.setup_profile'))
    
    # Check if user is the author of the book
    if book.author_id != book_user.id:
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
            chapter.word_count = len(data.get('content', '').split()) if data.get('content') else chapter.word_count
            chapter.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'word_count': chapter.word_count})
            else:
                flash('Chapter updated successfully!', 'success')
                return redirect(url_for('book_platform.view_chapter', book_id=book_id, chapter_id=chapter_id))
                
        except Exception as e:
            db.session.rollback()
            print(f"Chapter update error: {e}")
            print(f"Error type: {type(e)}")
            print(f"Data received: {data}")
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 500
            else:
                flash(f'Error updating chapter: {str(e)}', 'error')
    
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

@book_bp.route('/books/<int:book_id>/delete', methods=['POST'])
@book_platform_required
def delete_book(book_id):
    """Delete a book and all its chapters"""
    book = BookProject.query.get_or_404(book_id)

    # Check if user has permission
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
            return jsonify({'error': 'Ink Studio profile required'}), 403

    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'error': 'You can only delete your own books'}), 403

    try:
        # Delete all chapters first (cascade should handle this, but being explicit)
        BookChapter.query.filter_by(book_project_id=book_id).delete()
        
        # Delete the book
        db.session.delete(book)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Book deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@book_bp.route('/books/<int:book_id>/chapters/<int:chapter_id>/delete', methods=['POST'])
@book_platform_required
def delete_chapter(book_id, chapter_id):
    """Delete a chapter"""
    book = BookProject.query.get_or_404(book_id)
    chapter = BookChapter.query.get_or_404(chapter_id)

    # Check if user has permission
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
            return jsonify({'error': 'Ink Studio profile required'}), 403

    # Check if user is the author of the book
    if book.author_id != book_user.id:
        return jsonify({'error': 'You can only delete chapters in your own books'}), 403

    if chapter.book_project_id != book_id:
        return jsonify({'error': 'Chapter not found in this book'}), 404

    try:
        # Delete the chapter
        db.session.delete(chapter)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Chapter deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Collaboration routes
@book_bp.route('/books/<int:book_id>/collaborate')
@book_platform_required
def collaborate(book_id):
    """Collaboration management page"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author can manage collaborations
    if book.author_id != book_user.id:
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
@book_platform_required
def invite_collaborator(book_id):
    """Invite a collaborator"""
    book = BookProject.query.get_or_404(book_id)
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    
    # Only author can invite collaborators
    if book.author_id != book_user.id:
        return jsonify({'error': 'Only the author can invite collaborators'}), 403
    
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
        # Debug: Check if we can query books at all
        all_books = BookProject.query.all()
        print(f"Total books in database: {len(all_books)}")
        
        # Debug: Check published books
        published_books = BookProject.query.filter_by(status=BookStatus.PUBLISHED).all()
        print(f"Published books: {len(published_books)}")
        
        # For now, show all books regardless of status for debugging
        books = BookProject.query.all()
        return render_template('book_platform/marketplace.html', books=books)
    except Exception as e:
        print(f"Marketplace error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return empty list on error
        return render_template('book_platform/marketplace.html', books=[])

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

@book_bp.route('/books/<int:book_id>/purchase', methods=['POST'])
@login_required
def purchase_book(book_id):
    """Purchase a book - accessible to all logged-in users, prevents self-purchase"""
    book = BookProject.query.get_or_404(book_id)
    
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
        chapter.word_count = len(data.get('content', '').split()) if data.get('content') else chapter.word_count
        chapter.updated_at = datetime.now(timezone.utc)
        
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
    from glconnect.forms import DigitalBookUploadForm
    from glconnect.digital_book_processor import digital_book_processor
    from glconnect.audio_book_generator import audio_book_generator
    from glconnect.book_platform_models import AudioGenerationTask
    import threading
    
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
