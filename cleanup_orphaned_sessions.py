#!/usr/bin/env python3
"""
Cleanup script for orphaned realtime sessions
This script removes any realtime sessions that reference non-existent books
"""

from glconnect import create_app, db
from glconnect.book_platform_models import RealtimeSession, BookProject
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_orphaned_sessions():
    """Clean up any orphaned realtime sessions that reference non-existent books"""
    try:
        # Find sessions that reference books that no longer exist
        orphaned_sessions = db.session.query(RealtimeSession).outerjoin(
            BookProject, RealtimeSession.book_project_id == BookProject.id
        ).filter(BookProject.id.is_(None)).all()
        
        logger.info(f"Found {len(orphaned_sessions)} orphaned realtime sessions")
        
        for session in orphaned_sessions:
            logger.info(f"Deleting orphaned session: {session.session_id} (book_id: {session.book_project_id})")
            db.session.delete(session)
        
        if orphaned_sessions:
            db.session.commit()
            logger.info(f"✅ Successfully cleaned up {len(orphaned_sessions)} orphaned realtime sessions")
        else:
            logger.info("✅ No orphaned sessions found")
            
    except Exception as e:
        logger.error(f"❌ Error cleaning up orphaned sessions: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    app, socketio = create_app()
    with app.app_context():
        cleanup_orphaned_sessions()
