"""
Book Platform Models - Separate database tables for the book platform
This module contains all database models for the book platform functionality.
These tables are separate from the main application to allow easy removal.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Float, JSON, Enum
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
import uuid

# Use the same db instance from the main models
from glconnect.models import db

# Enums for the book platform
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

# Book Platform User Model (extends existing User with book-specific fields)
class BookPlatformUser(db.Model):
    __tablename__ = 'book_platform_users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, unique=True)
    pen_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    social_links = db.Column(JSON, nullable=True)  # Store social media links as JSON
    writing_experience = db.Column(db.Text, nullable=True)
    genres = db.Column(JSON, nullable=True)  # Store preferred genres as JSON array
    payment_info = db.Column(JSON, nullable=True)  # Store payment details securely
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', backref='book_platform_profile')
    authored_books = db.relationship('BookProject', backref='author', lazy=True, foreign_keys='BookProject.author_id')
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
    target_audience = db.Column(db.String(100), nullable=True)
    word_count = db.Column(db.Integer, default=0)
    status = db.Column(db.Enum(BookStatus), default=BookStatus.DRAFT)
    cover_image = db.Column(db.String(200), nullable=True)
    isbn = db.Column(db.String(20), nullable=True)
    price = db.Column(db.Float, nullable=True)  # Price in USD
    currency = db.Column(db.String(3), default='USD')
    published_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Foreign Keys
    author_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    
    # Relationships
    chapters = db.relationship('BookChapter', backref='book_project', lazy=True, cascade='all, delete-orphan')
    collaborations = db.relationship('BookCollaboration', backref='book_project', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('BookComment', backref='book_project', lazy=True, cascade='all, delete-orphan')
    versions = db.relationship('BookVersion', backref='book_project', lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('BookSale', backref='book_project', lazy=True)

# Book Chapter Model
class BookChapter(db.Model):
    __tablename__ = 'book_chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)  # Rich text content
    summary = db.Column(db.Text, nullable=True)  # Chapter summary
    chapter_number = db.Column(db.Integer, nullable=False)
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
    resolved_by = db.relationship('BookPlatformUser', foreign_keys=[commenter_id], backref='resolved_comments')

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

# Chapter Version Model
class ChapterVersion(db.Model):
    __tablename__ = 'chapter_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    version_number = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    word_count = db.Column(db.Integer, default=0)
    is_current = db.Column(db.Boolean, default=False)
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
    buyer_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    
    # Relationships
    sale = db.relationship('BookSale', backref='purchase', uselist=False)

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
    
    # Foreign Keys
    seller_id = db.Column(db.Integer, db.ForeignKey('book_platform_users.id'), nullable=False)
    book_project_id = db.Column(db.Integer, db.ForeignKey('book_projects.id'), nullable=False)
    purchase_id = db.Column(db.Integer, db.ForeignKey('book_purchases.id'), nullable=False)

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

