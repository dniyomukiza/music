"""
WebSocket implementation for Real time collaboration in Ink Studio
This module handles WebSocket connections for Real time editing, comments, and collaboration features.
"""

from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_login import current_user
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Import models
from glconnect.models import db, User
from glconnect.book_platform_models import (
    BookPlatformUser, BookProject, BookChapter, BookCollaboration, 
    BookComment, RealtimeSession
)

# Initialize SocketIO (this should be done in your main app file)
socketio = SocketIO(cors_allowed_origins=["https://glc.cool", "http://localhost:5000"], supports_credentials=True)

# Store active sessions
active_sessions = {}

@socketio.on('connect')
def handle_connect():
    """Handle new WebSocket connection"""
    if not current_user.is_authenticated:
        disconnect()
        return False
    
    print(f"User {current_user.username} connected")
    emit('connected', {'message': 'Connected to Ink Studio'})

@socketio.on('disconnect')
def handle_disconnect(*args, **kwargs):
    """Handle WebSocket disconnection.

    python-socketio passes at least one argument (e.g. disconnect reason).
    Any exception here can leave Werkzeug in a bad state for the next HTTP
    request (AssertionError: write() before start_response), e.g. contact form POST.
    """
    try:
        if current_user.is_authenticated:
            logger.info("User %s disconnected", current_user.username)
            user_sessions = [
                session_id
                for session_id, session_data in active_sessions.items()
                if session_data.get('user_id') == current_user.user_id
            ]
            for session_id in user_sessions:
                try:
                    cleanup_session(session_id)
                except Exception:
                    logger.exception("cleanup_session failed for %s", session_id)
    except Exception:
        logger.exception("disconnect handler failed")

@socketio.on('join_book')
def handle_join_book(data):
    """Handle user joining a book session"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    
    if not book_id:
        emit('error', {'message': 'Book ID required'})
        return False
    
    # Verify user has access to the book
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if not book_user:
        emit('error', {'message': 'Ink Studio profile required'})
        return False
    
    # Check if user is author or collaborator
    book = BookProject.query.get(book_id)
    if not book:
        emit('error', {'message': 'Book not found'})
        return False
    
    collaboration = BookCollaboration.query.filter_by(
        book_project_id=book_id, 
        collaborator_id=book_user.id,
        is_active=True
    ).first()
    
    if book.author_id != book_user.id and not collaboration:
        emit('error', {'message': 'Access denied'})
        return False
    
    # Create session ID
    session_id = f"book_{book_id}_{chapter_id or 'all'}_{current_user.user_id}"
    
    # Join the room
    room = f"book_{book_id}"
    if chapter_id:
        room += f"_chapter_{chapter_id}"
    
    join_room(room)
    
    # Store session data
    active_sessions[session_id] = {
        'user_id': current_user.user_id,
        'book_id': book_id,
        'chapter_id': chapter_id,
        'room': room,
        'joined_at': datetime.now(timezone.utc),
        'last_activity': datetime.now(timezone.utc)
    }
    
    # Create or update database session
    db_session = RealtimeSession.query.filter_by(
        user_id=book_user.id,
        book_project_id=book_id,
        chapter_id=chapter_id
    ).first()
    
    if not db_session:
        db_session = RealtimeSession(
            session_id=session_id,
            user_id=book_user.id,
            book_project_id=book_id,
            chapter_id=chapter_id
        )
        db.session.add(db_session)
    else:
        db_session.is_active = True
        db_session.last_activity = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Notify other users in the room
    emit('user_joined', {
        'user': {
            'id': book_user.id,
            'name': book_user.pen_name or current_user.username,
            'role': collaboration.role.value if collaboration else 'author'
        }
    }, room=room, include_self=False)
    
    # Send current active users to the joining user
    active_users = get_active_users_in_room(room)
    emit('active_users', {'users': active_users})
    
    print(f"User {current_user.username} joined book {book_id}, chapter {chapter_id}")

@socketio.on('leave_book')
def handle_leave_book(data):
    """Handle user leaving a book session"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    
    session_id = f"book_{book_id}_{chapter_id or 'all'}_{current_user.user_id}"
    room = f"book_{book_id}"
    if chapter_id:
        room += f"_chapter_{chapter_id}"
    
    cleanup_session(session_id)
    leave_room(room)
    
    # Notify other users
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    if book_user:
        emit('user_left', {
            'user': {
                'id': book_user.id,
                'name': book_user.pen_name or current_user.username
            }
        }, room=room)

@socketio.on('content_change')
def handle_content_change(data):
    """Handle Real time content changes"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    content = data.get('content')
    cursor_position = data.get('cursor_position')
    
    if not all([book_id, chapter_id, content is not None]):
        emit('error', {'message': 'Invalid content change data'})
        return False
    
    # Verify access
    if not verify_user_access(current_user.user_id, book_id):
        emit('error', {'message': 'Access denied'})
        return False
    
    # Update session activity
    session_id = f"book_{book_id}_{chapter_id}_{current_user.user_id}"
    if session_id in active_sessions:
        active_sessions[session_id]['last_activity'] = datetime.now(timezone.utc)
    
    # Broadcast to other users in the room
    room = f"book_{book_id}_chapter_{chapter_id}"
    emit('content_change', {
        'user_id': current_user.user_id,
        'content': content,
        'cursor_position': cursor_position,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room, include_self=False)
    
    print(f"Content change from user {current_user.username} in book {book_id}, chapter {chapter_id}")

@socketio.on('cursor_position')
def handle_cursor_position(data):
    """Handle cursor position updates"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    position = data.get('position')
    
    if not all([book_id, chapter_id, position is not None]):
        return False
    
    # Verify access
    if not verify_user_access(current_user.user_id, book_id):
        return False
    
    # Broadcast cursor position to other users
    room = f"book_{book_id}_chapter_{chapter_id}"
    emit('cursor_position', {
        'user_id': current_user.user_id,
        'position': position,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }, room=room, include_self=False)

@socketio.on('add_comment')
def handle_add_comment(data):
    """Handle Real time comment additions"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    content = data.get('content')
    start_position = data.get('start_position')
    end_position = data.get('end_position')
    selected_text = data.get('selected_text')
    
    if not all([book_id, chapter_id, content]):
        emit('error', {'message': 'Invalid comment data'})
        return False
    
    # Verify access
    if not verify_user_access(current_user.user_id, book_id):
        emit('error', {'message': 'Access denied'})
        return False
    
    # Create comment in database
    book_user = BookPlatformUser.query.filter_by(user_id=current_user.user_id).first()
    comment = BookComment(
        content=content,
        book_project_id=book_id,
        chapter_id=chapter_id,
        commenter_id=book_user.id,
        start_position=start_position,
        end_position=end_position,
        selected_text=selected_text
    )
    
    db.session.add(comment)
    db.session.commit()
    
    # Broadcast to all users in the room
    room = f"book_{book_id}"
    if chapter_id:
        room += f"_chapter_{chapter_id}"
    
    emit('comment_added', {
        'comment': {
            'id': comment.id,
            'content': content,
            'commenter': {
                'id': book_user.id,
                'name': book_user.pen_name or current_user.username
            },
            'start_position': start_position,
            'end_position': end_position,
            'selected_text': selected_text,
            'created_at': comment.created_at.isoformat()
        }
    }, room=room)
    
    print(f"Comment added by user {current_user.username} in book {book_id}, chapter {chapter_id}")

@socketio.on('resolve_comment')
def handle_resolve_comment(data):
    """Handle comment resolution"""
    if not current_user.is_authenticated:
        return False
    
    comment_id = data.get('comment_id')
    if not comment_id:
        emit('error', {'message': 'Comment ID required'})
        return False
    
    # Get comment and verify access
    comment = BookComment.query.get(comment_id)
    if not comment:
        emit('error', {'message': 'Comment not found'})
        return False
    
    if not verify_user_access(current_user.user_id, comment.book_project_id):
        emit('error', {'message': 'Access denied'})
        return False
    
    # Resolve comment
    comment.is_resolved = True
    comment.resolved_at = datetime.now(timezone.utc)
    comment.status = 'resolved'
    
    db.session.commit()
    
    # Broadcast to all users in the room
    room = f"book_{comment.book_project_id}"
    if comment.chapter_id:
        room += f"_chapter_{comment.chapter_id}"
    
    emit('comment_resolved', {
        'comment_id': comment_id,
        'resolved_by': {
            'id': current_user.user_id,
            'name': current_user.username
        },
        'resolved_at': comment.resolved_at.isoformat()
    }, room=room)
    
    print(f"Comment {comment_id} resolved by user {current_user.username}")

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicators"""
    if not current_user.is_authenticated:
        return False
    
    book_id = data.get('book_id')
    chapter_id = data.get('chapter_id')
    is_typing = data.get('is_typing', False)
    
    if not book_id:
        return False
    
    # Verify access
    if not verify_user_access(current_user.user_id, book_id):
        return False
    
    # Broadcast typing indicator
    room = f"book_{book_id}"
    if chapter_id:
        room += f"_chapter_{chapter_id}"
    
    emit('typing', {
        'user_id': current_user.user_id,
        'user_name': current_user.username,
        'is_typing': is_typing
    }, room=room, include_self=False)

def verify_user_access(user_id, book_id):
    """Verify if user has access to the book"""
    book_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
    if not book_user:
        return False
    
    book = BookProject.query.get(book_id)
    if not book:
        return False
    
    # Check if user is author
    if book.author_id == book_user.id:
        return True
    
    # Check if user is collaborator
    collaboration = BookCollaboration.query.filter_by(
        book_project_id=book_id, 
        collaborator_id=book_user.id,
        is_active=True
    ).first()
    
    return collaboration is not None

def get_active_users_in_room(room):
    """Get list of active users in a room"""
    active_users = []
    
    for session_id, session_data in active_sessions.items():
        if session_data.get('room') == room:
            user_id = session_data.get('user_id')
            user = User.query.get(user_id)
            book_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
            
            if user and book_user:
                active_users.append({
                    'id': book_user.id,
                    'name': book_user.pen_name or user.username,
                    'joined_at': session_data.get('joined_at').isoformat()
                })
    
    return active_users

def cleanup_session(session_id):
    """Clean up a session"""
    if session_id in active_sessions:
        session_data = active_sessions[session_id]
        
        # Update database session
        db_session = RealtimeSession.query.filter_by(session_id=session_id).first()
        if db_session:
            db_session.is_active = False
            db.session.commit()
        
        # Remove from active sessions
        del active_sessions[session_id]

def cleanup_inactive_sessions():
    """Clean up inactive sessions (call this periodically)"""
    current_time = datetime.now(timezone.utc)
    inactive_sessions = []
    
    for session_id, session_data in active_sessions.items():
        last_activity = session_data.get('last_activity')
        if last_activity and (current_time - last_activity).seconds > 300:  # 5 minutes
            inactive_sessions.append(session_id)
    
    for session_id in inactive_sessions:
        cleanup_session(session_id)

# Periodic cleanup task (you might want to run this in a background task)
@socketio.on('ping')
def handle_ping():
    """Handle ping to keep connection alive"""
    emit('pong')

# Error handlers
@socketio.on_error_default
def default_error_handler(e):
    """Default error handler for WebSocket events"""
    print(f"WebSocket error: {e}")
    emit('error', {'message': 'An error occurred'})

