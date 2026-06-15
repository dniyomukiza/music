"""
Ink Studio Models - Separate database tables for Ink Studio functionality
This module contains all database models for Ink Studio functionality.
These tables are separate from the main application to allow easy removal.

CASCADE DELETE BEHAVIOR:
- When a User is deleted, their BookPlatformUser profile is automatically deleted (CASCADE)
- When a BookPlatformUser is deleted, all their authored books (BookProject) are automatically deleted (CASCADE)
- When a BookProject is deleted, all chapters, comments, collaborations are automatically deleted (cascade='all, delete-orphan')
- Author information (pen_name, username) is dynamically fetched via SQLAlchemy relationships,
  so any updates to user/profile information are automatically reflected in book displays
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON, Enum, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
import uuid

# Use the same db instance from the main models
from glconnect.models import db

# Enums for Ink Studio
class BookStatus(PyEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CollaborationRole(PyEnum):
    AUTHOR = "author"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    CO_AUTHOR = "co_author"

class InvitationStatus(PyEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"

class CommentStatus(PyEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ARCHIVED = "archived"

class TransactionStatus(PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"

# Reviewer and Investment System Enums
class ReviewerStatus(PyEnum):
    PENDING = "pending"
    ACCREDITED = "accredited"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

class ReviewerLevel(PyEnum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

class ReviewStatus(PyEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PUBLISHED = "published"
    REJECTED = "rejected"


class ReviewRequestStatus(PyEnum):
    PENDING = "pending"      # Author sent request; reviewer has not accepted
    ACCEPTED = "accepted"    # Reviewer accepted; review not yet submitted
    IN_PROGRESS = "in_progress"  # Reviewer submitted; awaiting author approval
    COMPLETED = "completed"  # Author published review; task done
    CANCELLED = "cancelled"

class InvestmentStatus(PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class CampaignStatus(PyEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FUNDED = "funded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrintOrderStatus(PyEnum):
    PENDING_FULFILLMENT = "pending_fulfillment"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DistributionType(PyEnum):
    REVIEWER = "reviewer"
    INVESTOR = "investor"
    AUTHOR = "author"
    PLATFORM = "platform"

# Ink Studio User Model (extends existing User with book-specific fields)
class BookPlatformUser(db.Model):
    __tablename__ = 'book_platform_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    pen_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    social_links = db.Column(JSON, nullable=True)  # Store social media links as JSON
    writing_experience = db.Column(db.Text, nullable=True)
    payment_info = db.Column(JSON, nullable=True)  # Store payment details securely
    # Stripe Connect: Express (or Custom) connected account id for marketplace payouts (acct_...)
    stripe_connect_account_id = db.Column(db.String(255), nullable=True)
    # Set True after author saves /mybook/setup-profile once; required before My Books / Create book.
    author_card_setup_completed = db.Column(db.Boolean, default=False, nullable=False)
    # Account-level Author Publishing Agreement (versioned; re-accept when version bumps)
    author_agreement_version = db.Column(db.String(20), nullable=True)
    author_agreement_accepted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='book_platform_profile')
    # Note: author relationship is now explicitly defined on BookProject model to avoid backref conflicts
    authored_books = db.relationship('BookProject', foreign_keys='BookProject.author_id', lazy=True, cascade='all, delete-orphan')
    collaborations = db.relationship('BookCollaboration', backref='collaborator', lazy=True)
    comments = db.relationship('BookComment', backref='commenter', lazy=True)
    purchases = db.relationship('BookPurchase', backref='buyer', lazy=True)
    sales = db.relationship('BookSale', backref='seller', lazy=True)

# Book Project Model
class BookProject(db.Model):
    __tablename__ = 'book_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    genre = db.Column(db.String(100), nullable=True)
    language = db.Column(db.String(50), nullable=True)  # Language of the book (e.g., 'en', 'es', 'fr', 'de', etc.)
    target_audience = db.Column(db.String(100), nullable=True)
    word_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum(BookStatus), default=BookStatus.DRAFT)
    cover_image = db.Column(db.String(500), nullable=True)
    isbn = db.Column(db.String(20), nullable=True)
    publisher_name = db.Column(db.String(200), nullable=True)  # Platform imprint when listed
    isbn_assigned_at = db.Column(db.DateTime, nullable=True)
    price = db.Column(db.Float, nullable=True)  # Price in USD
    currency = db.Column(db.String(3), default='USD')
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Digital Book File Support
    digital_file_path = db.Column(db.String(500), nullable=True)  # Path to uploaded digital book file
    digital_file_type = db.Column(db.String(50), nullable=True)  # PDF, EPUB, DOCX, etc.
    digital_file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    digital_file_uploaded_at = db.Column(db.DateTime, nullable=True)
    digital_book_published = db.Column(db.Boolean, default=False)  # Whether digital book is published to marketplace
    digital_book_published_at = db.Column(db.DateTime, nullable=True)  # When digital book was published
    
    # Audio Book Support
    has_audiobook = db.Column(db.Boolean, default=False)
    audiobook_file_path = db.Column(db.String(500), nullable=True)  # Path to generated audio file
    audiobook_price = db.Column(db.Float, nullable=True)  # Separate price for audio version
    audiobook_duration = db.Column(db.Integer, nullable=True)  # Duration in seconds
    audiobook_generated_at = db.Column(db.DateTime, nullable=True)
    audiobook_voice = db.Column(db.String(100), nullable=True)  # TTS voice used
    audiobook_published = db.Column(db.Boolean, default=False)  # Whether audiobook is published to marketplace
    audiobook_published_at = db.Column(db.DateTime, nullable=True)  # When audiobook was published
    audiobook_segment_plan = db.Column(db.JSON, nullable=True)  # Section include/exclude draft for TTS prep

    # Print edition (author fulfills shipping; Ink collects payment)
    print_enabled = db.Column(db.Boolean, default=False, nullable=False)
    print_price = db.Column(db.Float, nullable=True)
    print_shipping_price = db.Column(db.Float, nullable=True, default=0.0)
    print_handling_days = db.Column(db.Integer, nullable=True, default=7)
    print_description = db.Column(db.Text, nullable=True)

    # Per-title listing attestation (Layer 2 of Author Publishing Agreement)
    listing_attestation_version = db.Column(db.String(20), nullable=True)
    listing_attestation_accepted_at = db.Column(db.DateTime, nullable=True)
    
    # Investment & Sales Tracking
    has_investment_campaign = db.Column(db.Boolean, default=False)
    total_sales = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    # Explicitly define author relationship to ensure it's a single object, not a collection
    # Note: Don't use backref here since authored_books already exists on BookPlatformUser
    author = db.relationship('BookPlatformUser', foreign_keys=[author_id], lazy=True, overlaps="authored_books")
    chapters = db.relationship('BookChapter', backref='book_project', lazy=True, cascade='all, delete-orphan')
    collaborations = db.relationship('BookCollaboration', backref='book_project', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('BookComment', backref='book_project', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('BookVersion', backref='book_project', lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('BookSale', backref='book_project', lazy=True)
    # audiobook_chapters defined on AudiobookChapter.book_project

# Book Chapter Model
class BookChapter(db.Model):
    __tablename__ = 'book_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Rich text content
    summary = db.Column(db.Text, nullable=True)  # Chapter summary
    chapter_number = db.Column(db.Integer, nullable=False)
    section_kind = db.Column(db.String(20), nullable=True)  # front | chapter | back | other
    word_count = db.Column(db.Integer, default=0)
    word_count_target = db.Column(db.Integer, nullable=True)  # Target word count for this chapter
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    
    # Relationships
    comments = db.relationship('BookComment', backref='chapter', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('ChapterVersion', backref='chapter', lazy=True, cascade='all, delete-orphan')


# Audiobook Chapter Model - per-chapter audio for listeners to pick and play
class AudiobookChapter(db.Model):
    __tablename__ = 'audiobook_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False)  # 1-based order
    title = db.Column(db.String(300), nullable=False)
    audio_file_path = db.Column(db.String(500), nullable=False)
    duration_seconds = db.Column(db.Integer, default=0)  # Duration in seconds
    book_chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id', ondelete='SET NULL'), nullable=True)  # Link to source chapter if any
    
    # Relationships
    # Ensure deleting a book deletes child audiobook chapters instead of trying to null FK.
    book_project = db.relationship(
        'BookProject',
        backref=db.backref(
            'audiobook_chapters',
            lazy=True,
            cascade='all, delete-orphan',
            passive_deletes=True,
        ),
    )
    book_chapter = db.relationship('BookChapter', backref='audiobook_chapter')


# Legacy table: AI-translated extra editions are no longer created; kept for DB compatibility & purge.
class DigitalBookEdition(db.Model):
    __tablename__ = 'digital_book_editions'
    __table_args__ = (
        UniqueConstraint('book_project_id', 'language_code', name='uq_digital_edition_book_lang'),
    )

    id = db.Column(db.Integer, primary_key=True)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False)
    language_code = db.Column(db.String(10), nullable=False)
    digital_file_path = db.Column(db.String(500), nullable=True)
    file_format = db.Column(db.String(10), default='txt', nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, ready, failed
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    book_project = db.relationship('BookProject', backref=db.backref('digital_book_editions', lazy=True, cascade='all, delete-orphan'))


# Book Collaboration Model
class BookCollaboration(db.Model):
    __tablename__ = 'book_collaborations'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(CollaborationRole), nullable=False)
    permissions = db.Column(JSON, nullable=True)  # Store specific permissions as JSON
    invited_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    joined_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    collaborator_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Relationships
    invitations = db.relationship('CollaborationInvitation', backref='collaboration', lazy=True, cascade='all, delete-orphan')

# Collaboration Invitation Model
class CollaborationInvitation(db.Model):
    __tablename__ = 'collaboration_invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum(CollaborationRole), nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(InvitationStatus), default=InvitationStatus.PENDING)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    collaboration_id = db.Column(db.Integer, db.ForeignKey('book_collaborations.id'), nullable=False)
    invited_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Relationships
    invited_by = db.relationship('BookPlatformUser', foreign_keys=[invited_by_id], backref='sent_invitations')

# Book Comment Model
class BookComment(db.Model):
    __tablename__ = 'book_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(CommentStatus), default=CommentStatus.ACTIVE)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Position in the text (for inline comments)
    start_position = db.Column(db.Integer, nullable=True)
    end_position = db.Column(db.Integer, nullable=True)
    selected_text = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id'), nullable=True)
    commenter_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('book_comments.id'), nullable=True)
    
    # Relationships
    replies = db.relationship('BookComment', backref=db.backref('parent_comment', remote_side=[id]), lazy=True)
    resolved_by = db.relationship('BookPlatformUser', foreign_keys=[commenter_id], backref=db.backref('resolved_comments', overlaps="commenter,comments"), overlaps="commenter,comments")

# Book Version Model (for version control)
class BookVersion(db.Model):
    __tablename__ = 'book_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version_number = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    is_current = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('BookPlatformUser', backref='created_versions')
    chapter_versions = db.relationship('ChapterVersion', backref='book_version', lazy=True, cascade='all, delete-orphan')

# Chapter Suggestion Model (for collaborative edits that need approval)
class ChapterSuggestion(db.Model):
    __tablename__ = 'chapter_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id'), nullable=False)
    suggested_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Suggested changes
    suggested_title = db.Column(db.String(200), nullable=True)
    suggested_content = db.Column(db.Text, nullable=True)
    suggested_summary = db.Column(db.Text, nullable=True)
    
    # Original values (for comparison/diff)
    original_content = db.Column(db.Text, nullable=True)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    review_message = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    chapter = db.relationship('BookChapter', backref='suggestions')
    suggested_by = db.relationship('BookPlatformUser', foreign_keys=[suggested_by_id], backref='chapter_suggestions')
    reviewed_by = db.relationship('BookPlatformUser', foreign_keys=[reviewed_by_id], backref='reviewed_suggestions')

# Chapter Version Model
class ChapterVersion(db.Model):
    __tablename__ = 'chapter_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version_number = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    is_current = db.Column(db.Boolean, default=False)
    summary = db.Column(db.Text, nullable=True)
    change_source = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id'), nullable=False)
    book_version_id = db.Column(db.Integer, db.ForeignKey('book_versions.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Relationships
    created_by = db.relationship('BookPlatformUser', backref='created_chapter_versions')

# Book Purchase Model
class BookPurchase(db.Model):
    __tablename__ = 'book_purchases'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)  # External payment processor ID
    purchased_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    # buyer_id is for users with BookPlatformUser profiles (authors/writers who also buy)
    # buyer_user_id is for regular users who only need a user account to purchase
    buyer_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=True)
    buyer_user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)  # Direct reference to users table
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    
    # Purchase format: digital (ebook), audiobook, bundle, print
    purchase_format = db.Column(db.String(20), default='digital', nullable=True)
    
    # Buyer information (stored for easy access and historical record)
    buyer_username = db.Column(db.String(80), nullable=True)  # Store username for quick access
    buyer_full_name = db.Column(db.String(200), nullable=True)  # Store full name (first_name + last_name or pen_name)

    __table_args__ = (
        CheckConstraint(
            "(buyer_id IS NOT NULL) OR (buyer_user_id IS NOT NULL)",
            name='check_book_purchase_has_buyer',
        ),
    )
    
    # Relationships
    sale = db.relationship('BookSale', backref='purchase', uselist=False)
    # Note: buyer relationship is handled via buyer_id -> BookPlatformUser
    # buyer_user_id directly references users.user_id (no relationship needed as it's a direct FK)
    
    # Relationship to User via buyer_user_id
    buyer_user = db.relationship('User', foreign_keys=[buyer_user_id], backref='book_purchases', lazy=True)
    
    def get_buyer_name(self):
        """Get buyer's name/username - uses stored values if available, otherwise queries database"""
        # Use stored value if available (faster, no database query needed)
        if self.buyer_full_name:
            return self.buyer_full_name
        
        from glconnect.models import User  # Import here to avoid circular dependency
        
        # Try buyer_id first (BookPlatformUser - has pen_name)
        if self.buyer_id:
            buyer = BookPlatformUser.query.get(self.buyer_id)
            if buyer:
                # Prefer pen_name, fallback to username
                if buyer.pen_name:
                    return buyer.pen_name
                if buyer.user:
                    return buyer.user.username
                return f"User {buyer.id}"
        
        # Fallback to buyer_user_id (User - has username, first_name, last_name)
        if self.buyer_user_id:
            user = User.query.get(self.buyer_user_id)
            if user:
                # Prefer full name if available, fallback to username
                if user.first_name and user.last_name:
                    return f"{user.first_name} {user.last_name}"
                return user.username

        return "Unknown Buyer"
    
    def get_buyer_username(self):
        """Get buyer's username - uses stored value if available, otherwise queries database"""
        # Use stored value if available (faster, no database query needed)
        if self.buyer_username:
            return self.buyer_username
        
        from glconnect.models import User  # Import here to avoid circular dependency
        
        # Try buyer_id first (BookPlatformUser)
        if self.buyer_id:
            buyer = BookPlatformUser.query.get(self.buyer_id)
            if buyer and buyer.user:
                return buyer.user.username
        
        # Fallback to buyer_user_id (User)
        if self.buyer_user_id:
            user = User.query.get(self.buyer_user_id)
            if user:
                return user.username
        
        return "Unknown"
    
    def get_buyer_email(self):
        """Get buyer's email - works for both buyer_id and buyer_user_id"""
        from glconnect.models import User  # Import here to avoid circular dependency
        
        # Try buyer_id first (BookPlatformUser)
        if self.buyer_id:
            buyer = BookPlatformUser.query.get(self.buyer_id)
            if buyer and buyer.user:
                return buyer.user.email
        
        # Fallback to buyer_user_id (User)
        if self.buyer_user_id:
            user = User.query.get(self.buyer_user_id)
            if user:
                return user.email

        return None
    
    def populate_buyer_info(self):
        """Populate buyer_username and buyer_full_name from related User/BookPlatformUser records"""
        from glconnect.models import User  # Import here to avoid circular dependency
        
        # Try buyer_id first (BookPlatformUser - has pen_name)
        if self.buyer_id:
            buyer = BookPlatformUser.query.get(self.buyer_id)
            if buyer:
                # Set username
                if buyer.user:
                    self.buyer_username = buyer.user.username
                    # Set full name - prefer pen_name, fallback to first_name + last_name
                    if buyer.pen_name:
                        self.buyer_full_name = buyer.pen_name
                    elif buyer.user.first_name and buyer.user.last_name:
                        self.buyer_full_name = f"{buyer.user.first_name} {buyer.user.last_name}"
                    else:
                        self.buyer_full_name = buyer.user.username
                else:
                    # No user relationship, use buyer ID as fallback
                    self.buyer_username = f"user_{self.buyer_id}"
                    self.buyer_full_name = f"User {self.buyer_id}"
        
        # Fallback to buyer_user_id (User - has username, first_name, last_name)
        elif self.buyer_user_id:
            user = User.query.get(self.buyer_user_id)
            if user:
                self.buyer_username = user.username
                # Prefer full name if available, fallback to username
                if user.first_name and user.last_name:
                    self.buyer_full_name = f"{user.first_name} {user.last_name}"
                else:
                    self.buyer_full_name = user.username


class BookPrintOrder(db.Model):
    """Physical print order — author ships; platform collected payment via BookPurchase."""

    __tablename__ = 'book_print_orders'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    book_purchase_id = db.Column(
        db.Integer, db.ForeignKey('book_purchases.id', ondelete='CASCADE'), nullable=False, unique=True
    )
    book_project_id = db.Column(
        db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False, index=True
    )
    book_amount = db.Column(db.Float, nullable=False, default=0.0)
    shipping_amount = db.Column(db.Float, nullable=False, default=0.0)
    shipping_name = db.Column(db.String(200), nullable=True)
    shipping_line1 = db.Column(db.String(200), nullable=False)
    shipping_line2 = db.Column(db.String(200), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state = db.Column(db.String(100), nullable=True)
    shipping_postal = db.Column(db.String(30), nullable=False)
    shipping_country = db.Column(db.String(2), nullable=False, default='US')
    status = db.Column(db.Enum(PrintOrderStatus), default=PrintOrderStatus.PENDING_FULFILLMENT)
    tracking_number = db.Column(db.String(200), nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    purchase = db.relationship('BookPurchase', backref=db.backref('print_order', uselist=False))
    book_project = db.relationship('BookProject', backref='print_orders')


class LibraryBookHide(db.Model):
    """Buyer hid format(s) from My Library UI; purchase rows stay for history/support."""

    __tablename__ = 'library_book_hides'
    __table_args__ = (
        UniqueConstraint('user_id', 'book_project_id', name='uq_library_hide_user_book'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    hide_ebook = db.Column(db.Boolean, default=False, nullable=False)
    hide_audiobook = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ReaderAnnotation(db.Model):
    """User highlights, section bookmarks, and optional notes on the in-browser library reader (synced per account)."""

    __tablename__ = 'reader_annotations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False, index=True)
    section_index = db.Column(db.Integer, nullable=False)
    start_offset = db.Column(db.Integer, nullable=False, default=0)
    end_offset = db.Column(db.Integer, nullable=False, default=0)
    quote_text = db.Column(db.Text, nullable=True)
    note_text = db.Column(db.Text, nullable=True)
    kind = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], lazy=True)
    book_project = db.relationship('BookProject', foreign_keys=[book_project_id], lazy=True)


# Book Sale Model
class BookSale(db.Model):
    __tablename__ = 'book_sales'
    
    id = db.Column(db.Integer, primary_key=True)
    royalty_amount = db.Column(db.Float, nullable=False)
    royalty_percentage = db.Column(db.Float, nullable=False)
    platform_fee = db.Column(db.Float, nullable=False)
    net_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Sale format: 'digital' (ebook/digital copy), 'audiobook', 'bundle'. Used so earnings account for digital and audio.
    sale_format = db.Column(db.String(20), default='digital', nullable=True)
    
    # Revenue Distribution Tracking
    distributed_to_reviewers = db.Column(db.Float, default=0.0)
    distributed_to_investors = db.Column(db.Float, default=0.0)
    distribution_completed = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    seller_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    purchase_id = db.Column(db.Integer, db.ForeignKey('book_purchases.id'), nullable=False)

# Audio Generation Task Model
class AudioGenerationTask(db.Model):
    __tablename__ = 'audio_generation_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    book_project = db.relationship('BookProject', backref='audio_generation_tasks')

# Real-time Session Model (for WebSocket connections)
class RealtimeSession(db.Model):
    __tablename__ = 'realtime_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('book_chapters.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_activity = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('BookPlatformUser', backref='realtime_sessions')
    book_project = db.relationship('BookProject', backref='active_sessions')
    chapter = db.relationship('BookChapter', backref='active_sessions')

# Book Analytics Model
class BookAnalytics(db.Model):
    __tablename__ = 'book_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    views = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)
    purchases = db.Column(db.Integer, default=0)
    revenue = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='USD')
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    
    # Relationships
    book_project = db.relationship('BookProject', backref='analytics')

# Notification Model
class BookNotification(db.Model):
    __tablename__ = 'book_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # comment, invitation, sale, etc.
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=True)
    
    # Relationships
    user = db.relationship('BookPlatformUser', backref='notifications')
    book_project = db.relationship('BookProject', backref='notifications')

# Accredited Reviewer Model
class AccreditedReviewer(db.Model):
    __tablename__ = 'accredited_reviewers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, unique=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    
    # Accreditation Details
    accreditation_status = db.Column(db.Enum(ReviewerStatus), default=ReviewerStatus.PENDING)
    accreditation_level = db.Column(db.Enum(ReviewerLevel), default=ReviewerLevel.BRONZE)
    accreditation_date = db.Column(db.DateTime, nullable=True)
    accreditation_expires_at = db.Column(db.DateTime, nullable=True)
    
    # Credentials
    credentials = db.Column(JSON, nullable=True)  # Education, certifications, publications
    specialties = db.Column(JSON, nullable=True)  # Genres they review
    portfolio_url = db.Column(db.String(500), nullable=True)
    
    # Performance Metrics
    total_reviews = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)
    total_earnings = db.Column(db.Float, default=0.0)
    books_reviewed = db.Column(db.Integer, default=0)
    
    # Financial
    payment_info = db.Column(JSON, nullable=True)
    default_revenue_share_percentage = db.Column(db.Float, default=2.5)  # Default % per book
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='reviewer_profile')
    reviews = db.relationship('BookReview', backref='reviewer', lazy=True)
    earnings = db.relationship('ReviewerEarning', backref='reviewer', lazy=True)


# Review Request Model (author requests a reviewer; optional fixed fee per task)
class ReviewRequest(db.Model):
    __tablename__ = 'review_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('accredited_reviewers.id', ondelete='CASCADE'), nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id', ondelete='CASCADE'), nullable=False)
    
    agreed_fee = db.Column(db.Float, nullable=True)  # Optional fixed fee author will pay on completion
    agreed_revenue_share = db.Column(db.Float, nullable=True)  # Optional % of sales (if author and reviewer agree)
    
    status = db.Column(db.Enum(ReviewRequestStatus), default=ReviewRequestStatus.PENDING)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    accepted_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    book_project = db.relationship('BookProject', backref='review_requests')
    reviewer = db.relationship('AccreditedReviewer', backref='review_requests')
    requested_by = db.relationship('BookPlatformUser', backref='sent_review_requests')
    review = db.relationship('BookReview', backref=db.backref('review_request', lazy=True), uselist=False, foreign_keys='BookReview.review_request_id')


# Book Review Model
class BookReview(db.Model):
    __tablename__ = 'book_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Review Content
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    is_featured = db.Column(db.Boolean, default=False)
    is_public = db.Column(db.Boolean, default=True)
    
    # Review Status
    status = db.Column(db.Enum(ReviewStatus), default=ReviewStatus.DRAFT)
    submitted_at = db.Column(db.DateTime, nullable=True)
    published_at = db.Column(db.DateTime, nullable=True)
    
    # Revenue Share Agreement
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # e.g., 2.5% of sales
    minimum_sales_threshold = db.Column(db.Integer, default=0)  # Minimum sales before earning
    
    # Author-paid task (freelancer style): fixed fee per completed review, paid when author publishes
    agreed_fee = db.Column(db.Float, nullable=True)  # Optional fixed amount author pays on completion
    author_paid_at = db.Column(db.DateTime, nullable=True)  # When author paid the fixed fee (if any)
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('accredited_reviewers.id', ondelete='CASCADE'), nullable=False)
    review_request_id = db.Column(db.Integer, db.ForeignKey('review_requests.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    book_project = db.relationship('BookProject', backref='accredited_reviews')
    earnings = db.relationship('ReviewerEarning', backref='review', lazy=True)

# Investment Campaign Model
class InvestmentCampaign(db.Model):
    __tablename__ = 'investment_campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Campaign Details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    pitch_video_url = db.Column(db.String(500), nullable=True)
    tentative_timeline = db.Column(db.String(200), nullable=True)
    
    # Funding Goals
    funding_goal = db.Column(db.Float, nullable=False)
    minimum_investment = db.Column(db.Float, nullable=False)
    maximum_investment = db.Column(db.Float, nullable=True)
    current_funding = db.Column(db.Float, default=0.0)
    
    # Terms
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # Total % shared with investors
    return_multiplier_cap = db.Column(db.Float, nullable=False, default=3.0)  # Max return (e.g., 3x)
    investment_period_days = db.Column(db.Integer, default=730)  # Days to reach goal (2 years)
    
    # Status
    status = db.Column(db.Enum(CampaignStatus), default=CampaignStatus.DRAFT)
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    funded_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    
    # Milestone-based fund release (safeguard for investors - author gets 50% at first draft, 50% at publication)
    author_first_draft_released = db.Column(db.Boolean, default=False)
    author_first_draft_released_at = db.Column(db.DateTime, nullable=True)
    author_first_draft_amount = db.Column(db.Float, nullable=True)  # 50% of current_funding when released
    author_publication_released = db.Column(db.Boolean, default=False)
    author_publication_released_at = db.Column(db.DateTime, nullable=True)
    author_publication_amount = db.Column(db.Float, nullable=True)  # Remaining 50% when released

    # Platform fee snapshot at funding (first project: 0% on pledges; later: 3%)
    is_first_author_project = db.Column(db.Boolean, default=False)
    campaign_platform_fee_percent = db.Column(db.Float, nullable=True)
    campaign_platform_fee_amount = db.Column(db.Float, nullable=True)
    author_net_funding = db.Column(db.Float, nullable=True)  # Pledges after campaign platform fee
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Relationships
    book_project = db.relationship('BookProject', backref='investment_campaign', uselist=False)
    investments = db.relationship('BookInvestment', backref='campaign', lazy=True, cascade='all, delete-orphan')


class SavedBookCampaign(db.Model):
    """Patron saved a campaign to return and support later."""

    __tablename__ = 'saved_book_campaigns'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'campaign_id', name='uq_saved_campaign_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('investment_campaigns.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], lazy=True)
    campaign = db.relationship('InvestmentCampaign', backref='saved_by_users', lazy=True)


class CampaignTranslation(db.Model):
    """Cached AI translations of campaign page content for patrons."""

    __tablename__ = 'campaign_translations'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'language', name='uq_campaign_translation_lang'),
    )

    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(
        db.Integer,
        db.ForeignKey('investment_campaigns.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    language = db.Column(db.String(10), nullable=False)
    translated_title = db.Column(db.String(200), nullable=True)
    translated_book_title = db.Column(db.String(200), nullable=True)
    translated_author_bio = db.Column(db.Text, nullable=True)
    translated_book_description = db.Column(db.Text, nullable=True)
    translated_campaign_description = db.Column(db.Text, nullable=True)
    translated_tentative_timeline = db.Column(db.String(200), nullable=True)
    translation_method = db.Column(db.String(50), default='gemini')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    campaign = db.relationship('InvestmentCampaign', backref='translations', lazy=True)

# Book Investment Model
class BookInvestment(db.Model):
    __tablename__ = 'book_investments'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Investment Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    investment_percentage = db.Column(db.Float, nullable=False)  # % of total funding goal
    
    # Terms (inherited from campaign, but stored for historical accuracy)
    revenue_share_percentage = db.Column(db.Float, nullable=False)  # % of sales revenue
    return_multiplier = db.Column(db.Float, nullable=False)  # e.g., 1.5x return cap
    minimum_return = db.Column(db.Float, nullable=True)  # Guaranteed minimum return
    
    # Status
    status = db.Column(db.Enum(InvestmentStatus), default=InvestmentStatus.PENDING)
    payment_status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    
    # Timeline
    invested_at = db.Column(db.DateTime, nullable=True)
    return_start_date = db.Column(db.DateTime, nullable=True)  # When returns begin
    return_end_date = db.Column(db.DateTime, nullable=True)  # When returns stop
    
    # Returns Tracking
    total_returns = db.Column(db.Float, default=0.0)
    paid_out_amount = db.Column(db.Float, default=0.0)  # Amount already paid to investor; available = total_returns - paid_out_amount
    last_payout_date = db.Column(db.DateTime, nullable=True)
    
    # Refund tracking
    refunded_at = db.Column(db.DateTime, nullable=True)
    
    # Stripe payment intent (for refunds - stored when checkout completes)
    stripe_payment_intent_id = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    investor_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id', ondelete='CASCADE'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id', ondelete='CASCADE'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('investment_campaigns.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    investor = db.relationship('BookPlatformUser', backref='investments')
    book_project = db.relationship('BookProject', backref='investments')
    payouts = db.relationship('InvestmentPayout', backref='investment', lazy=True)

# Revenue Distribution Model
class RevenueDistribution(db.Model):
    __tablename__ = 'revenue_distributions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Distribution Details
    distribution_type = db.Column(db.Enum(DistributionType), nullable=False)  # REVIEWER, INVESTOR, AUTHOR, PLATFORM
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    # Status
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    transaction_id = db.Column(db.String(100), nullable=True)
    
    # Source
    source_sale_id = db.Column(db.Integer, db.ForeignKey('book_sales.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, nullable=False)  # Reviewer ID, Investor ID, or Author ID
    recipient_type = db.Column(db.String(50), nullable=False)  # 'reviewer', 'investor', 'author', 'platform'
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    source_sale = db.relationship('BookSale', backref='distributions')

# Reviewer Earning Model (for tracking earnings)
class ReviewerEarning(db.Model):
    __tablename__ = 'reviewer_earnings'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Guarantee payment flag (for when book isn't published)
    is_guarantee_payment = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    reviewer_id = db.Column(db.Integer, db.ForeignKey('accredited_reviewers.id', ondelete='CASCADE'), nullable=False)
    review_id = db.Column(db.Integer, db.ForeignKey('book_reviews.id', ondelete='CASCADE'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('revenue_distributions.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    distribution = db.relationship('RevenueDistribution', backref='reviewer_earnings')

# Investment Payout Model (for tracking payouts)
class InvestmentPayout(db.Model):
    __tablename__ = 'investment_payouts'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Foreign Keys
    investment_id = db.Column(db.Integer, db.ForeignKey('book_investments.id', ondelete='CASCADE'), nullable=False)
    distribution_id = db.Column(db.Integer, db.ForeignKey('revenue_distributions.id', ondelete='SET NULL'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    distribution = db.relationship('RevenueDistribution', backref='investment_payouts')

# Payout Request Model (investor requests withdrawal of earnings)
class PayoutRequest(db.Model):
    __tablename__ = 'payout_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    investment_id = db.Column(db.Integer, db.ForeignKey('book_investments.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID, CANCELLED
    
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    investment = db.relationship('BookInvestment', backref='payout_requests')


# Reviewer Payout Request (min $50, admin approval - mirrors investor payouts)
class ReviewerPayoutRequest(db.Model):
    __tablename__ = 'reviewer_payout_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    reviewer_id = db.Column(db.Integer, db.ForeignKey('accredited_reviewers.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID, CANCELLED
    
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    reviewer = db.relationship('AccreditedReviewer', backref='payout_requests')


# Author Sales Payout Request (earnings from book sales - min $50, admin approval)
class AuthorSalesPayoutRequest(db.Model):
    __tablename__ = 'author_sales_payout_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    author_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    status = db.Column(db.String(20), default='PENDING')  # PENDING, PAID, CANCELLED
    
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    paid_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    author = db.relationship('BookPlatformUser', backref='sales_payout_requests')


# Refund Request Model
class RefundRequest(db.Model):
    __tablename__ = 'refund_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    # Refund Details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    reason = db.Column(db.Text, nullable=False)
    
    # Status
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    processed_at = db.Column(db.DateTime, nullable=True)
    requested_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Payment processor info
    refund_transaction_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    
    # Foreign Keys
    investment_id = db.Column(db.Integer, db.ForeignKey('book_investments.id', ondelete='CASCADE'), nullable=False)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    investment = db.relationship('BookInvestment', backref='refund_requests')


# Author Campaign Payout Request - milestone-based release (first draft 50%, publication 50%)
class AuthorCampaignPayoutRequest(db.Model):
    __tablename__ = 'author_campaign_payout_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    
    campaign_id = db.Column(db.Integer, db.ForeignKey('investment_campaigns.id', ondelete='CASCADE'), nullable=False)
    milestone = db.Column(db.String(30), nullable=False)  # 'first_draft' | 'publication'
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    
    status = db.Column(db.String(20), default='pending')  # pending, approved, paid, rejected
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at = db.Column(db.DateTime, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id', ondelete='SET NULL'), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    
    campaign = db.relationship('InvestmentCampaign', backref='author_payout_requests')
    approved_by = db.relationship('BookPlatformUser', foreign_keys=[approved_by_id])


class IsbnPoolStatus(PyEnum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    RESERVED = "reserved"


class IsbnPoolEntry(db.Model):
    """Platform-owned ISBN inventory; one ISBN per listed book title (all formats)."""

    __tablename__ = "isbn_pool"

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.Enum(IsbnPoolStatus), default=IsbnPoolStatus.AVAILABLE, nullable=False)
    book_project_id = db.Column(
        db.Integer, db.ForeignKey("book_projects.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    book_project = db.relationship("BookProject", backref=db.backref("isbn_pool_entry", uselist=False))

