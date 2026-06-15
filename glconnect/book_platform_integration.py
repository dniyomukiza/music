"""
Ink Studio Integration Module
This module integrates Ink Studio with the main Flask application.
It handles database initialization, blueprint registration, and WebSocket setup.
"""

from flask import Flask
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_migrate import Migrate

# Import existing models and database
from glconnect.models import db, User

# Import Ink Studio components
from glconnect.book_platform_models import *
from glconnect.book_platform_routes import book_bp
from glconnect.book_platform_websocket import socketio
from glconnect.gemini_integration import gemini_bp
from glconnect.book_agent_routes import book_agents_bp

def init_book_platform(app):
    """
    Initialize Ink Studio with the Flask application.
    This function should be called from your main app initialization.
    """

    @app.context_processor
    def inject_csrf_token():
        """Expose csrf_token() in Jinja for manual forms (e.g. My Library hide)."""
        try:
            from flask_wtf.csrf import generate_csrf

            return {"csrf_token": generate_csrf}
        except Exception:
            return {"csrf_token": lambda: ""}

    @app.context_processor
    def inject_ink_studio_v1():
        from flask_login import current_user

        try:
            from glconnect.ink_studio_v1 import (
                ink_account_capabilities,
                ink_is_author_account,
                ink_show_author_workspace,
                ink_show_media_ecosystem,
                ink_v1_books_launch,
            )

            v1 = ink_v1_books_launch(app)
            caps = ink_account_capabilities()
            is_author = caps["is_author"]
            show_author_workspace = ink_show_author_workspace()
            return {
                "ink_v1_books_launch": v1,
                "ink_is_author_account": is_author,
                "ink_show_author_workspace": show_author_workspace,
                "ink_show_media_ecosystem": ink_show_media_ecosystem(app),
                "ink_account_capabilities": caps,
            }
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "inject_ink_studio_v1 failed safely: %s", exc, exc_info=True
            )
            from glconnect.ink_studio_v1 import ink_studio_v1_context_defaults

            return ink_studio_v1_context_defaults(app)

    @app.context_processor
    def inject_ink_studio_nav():
        from flask_login import current_user

        ctx = {
            'ink_nav_show_my_library': False,
            'ink_nav_show_author_nav': False,
        }
        if not getattr(current_user, 'is_authenticated', False):
            return ctx
        ctx['ink_nav_show_my_library'] = True
        try:
            from glconnect.book_platform_routes import (
                ink_studio_home_url,
                ink_studio_show_author_nav_links,
            )
            from glconnect.ink_studio_v1 import ink_show_author_workspace, ink_v1_books_launch

            if ink_v1_books_launch(app):
                ctx['ink_nav_show_author_nav'] = ink_show_author_workspace()
            else:
                ctx['ink_nav_show_author_nav'] = ink_studio_show_author_nav_links()
            ctx['ink_studio_home_url'] = ink_studio_home_url()
        except Exception:
            ctx['ink_nav_show_author_nav'] = False
            ctx['ink_studio_home_url'] = ''
        return ctx

    @app.context_processor
    def inject_book_campaign_patronage_ui():
        """Patronage vs legacy investment wording for Ink Studio campaign UI."""
        try:
            from glconnect.book_campaign_patronage import is_book_campaign_patronage_mode

            patronage = is_book_campaign_patronage_mode(app)
        except Exception:
            patronage = True
        return {"bcp_patronage": patronage}

    @app.context_processor
    def inject_manuscript_section_helpers():
        from glconnect.book_utils import (
            format_manuscript_summary,
            manuscript_section_heading,
            manuscript_section_kind,
            manuscript_section_rows,
            resolve_section_kind,
            section_kind_label,
        )

        return {
            'format_manuscript_summary': format_manuscript_summary,
            'manuscript_section_heading': manuscript_section_heading,
            'manuscript_section_kind': manuscript_section_kind,
            'manuscript_section_rows': manuscript_section_rows,
            'resolve_section_kind': resolve_section_kind,
            'section_kind_label': section_kind_label,
        }

    # Register the Ink Studio blueprints
    app.register_blueprint(book_bp)
    app.register_blueprint(gemini_bp)
    app.register_blueprint(book_agents_bp, url_prefix='/api/agents')
    
    # Initialize SocketIO with the app
    socketio.init_app(
        app,
        cors_allowed_origins=["https://glc.cool", "http://localhost:5000"],
        supports_credentials=True,
        async_mode="threading",
    )
    
    # Import WebSocket handlers to register them
    import glconnect.book_platform_websocket
    
    # Create database tables for Ink Studio
    with app.app_context():
        try:
            # Create all Ink Studio tables
            db.create_all()
            print("Ink Studio database tables created successfully")
        except Exception as e:
            print(f"Error creating Ink Studio tables: {e}")
    
    return app, socketio

def create_book_platform_tables():
    """
    Create only the Ink Studio tables.
    This can be used to add Ink Studio to an existing database.
    """
    from glconnect.book_platform_models import (
        BookPlatformUser, BookProject, BookChapter, BookCollaboration,
        CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
        ChapterSuggestion, BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification
    )
    
    # Create tables
    BookPlatformUser.__table__.create(db.engine, checkfirst=True)
    BookProject.__table__.create(db.engine, checkfirst=True)
    BookChapter.__table__.create(db.engine, checkfirst=True)
    BookCollaboration.__table__.create(db.engine, checkfirst=True)
    CollaborationInvitation.__table__.create(db.engine, checkfirst=True)
    BookComment.__table__.create(db.engine, checkfirst=True)
    BookVersion.__table__.create(db.engine, checkfirst=True)
    ChapterVersion.__table__.create(db.engine, checkfirst=True)
    ChapterSuggestion.__table__.create(db.engine, checkfirst=True)
    BookPurchase.__table__.create(db.engine, checkfirst=True)
    BookSale.__table__.create(db.engine, checkfirst=True)
    RealtimeSession.__table__.create(db.engine, checkfirst=True)
    BookAnalytics.__table__.create(db.engine, checkfirst=True)
    BookNotification.__table__.create(db.engine, checkfirst=True)
    
    print("Ink Studio tables created successfully")

def drop_book_platform_tables():
    """
    Drop all Ink Studio tables.
    This can be used to completely remove Ink Studio from the database.
    """
    from glconnect.book_platform_models import (
        BookPlatformUser, BookProject, BookChapter, BookCollaboration,
        CollaborationInvitation, BookComment, BookVersion, ChapterVersion,
        BookPurchase, BookSale, RealtimeSession, BookAnalytics, BookNotification
    )
    
    # Drop tables in reverse order to handle foreign key constraints
    BookNotification.__table__.drop(db.engine, checkfirst=True)
    BookAnalytics.__table__.drop(db.engine, checkfirst=True)
    RealtimeSession.__table__.drop(db.engine, checkfirst=True)
    BookSale.__table__.drop(db.engine, checkfirst=True)
    BookPurchase.__table__.drop(db.engine, checkfirst=True)
    ChapterVersion.__table__.drop(db.engine, checkfirst=True)
    BookVersion.__table__.drop(db.engine, checkfirst=True)
    BookComment.__table__.drop(db.engine, checkfirst=True)
    CollaborationInvitation.__table__.drop(db.engine, checkfirst=True)
    BookCollaboration.__table__.drop(db.engine, checkfirst=True)
    BookChapter.__table__.drop(db.engine, checkfirst=True)
    BookProject.__table__.drop(db.engine, checkfirst=True)
    BookPlatformUser.__table__.drop(db.engine, checkfirst=True)
    
    print("Ink Studio tables dropped successfully")

def get_book_platform_stats():
    """
    Get statistics about Ink Studio usage.
    """
    from glconnect.book_platform_models import (
        BookPlatformUser, BookProject, BookChapter, BookCollaboration,
        BookComment, BookPurchase, BookSale
    )
    
    stats = {
        'total_users': BookPlatformUser.query.count(),
        'total_books': BookProject.query.count(),
        'total_chapters': BookChapter.query.count(),
        'total_collaborations': BookCollaboration.query.count(),
        'total_comments': BookComment.query.count(),
        'total_purchases': BookPurchase.query.count(),
        'total_sales': BookSale.query.count(),
        'published_books': BookProject.query.filter_by(status=BookStatus.PUBLISHED).count(),
        'draft_books': BookProject.query.filter_by(status=BookStatus.DRAFT).count(),
    }
    
    return stats

def cleanup_book_platform_data():
    """
    Clean up old or unused data from Ink Studio.
    This can be run periodically to maintain database performance.
    """
    from glconnect.book_platform_models import (
        RealtimeSession, BookNotification, BookComment
    )
    from datetime import datetime, timezone, timedelta
    
    # Clean up old realtime sessions (older than 1 day)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=1)
    old_sessions = RealtimeSession.query.filter(
        RealtimeSession.last_activity < cutoff_date
    ).all()
    
    for session in old_sessions:
        db.session.delete(session)
    
    # Clean up old notifications (older than 30 days)
    notification_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    old_notifications = BookNotification.query.filter(
        BookNotification.created_at < notification_cutoff,
        BookNotification.is_read == True
    ).all()
    
    for notification in old_notifications:
        db.session.delete(notification)
    
    # Clean up resolved comments (older than 90 days)
    comment_cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    old_resolved_comments = BookComment.query.filter(
        BookComment.resolved_at < comment_cutoff,
        BookComment.is_resolved == True
    ).all()
    
    for comment in old_resolved_comments:
        db.session.delete(comment)
    
    db.session.commit()
    print(f"Cleaned up {len(old_sessions)} sessions, {len(old_notifications)} notifications, {len(old_resolved_comments)} comments")

# Example usage in your main app file:
"""
from flask import Flask
from glconnect.models import db
from glconnect.book_platform_integration import init_book_platform

def create_app():
    app = Flask(__name__)
    
    # Your existing app configuration
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'your-database-uri'
    
    # Initialize existing components
    db.init_app(app)
    
    # Initialize Ink Studio
    app, socketio = init_book_platform(app)
    
    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True)
"""
