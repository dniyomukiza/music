"""
Database Query Optimizer for Ink Studio
Optimizes database queries to reduce N+1 problems and improve performance
"""

from functools import wraps
from flask import current_app
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy import func, desc, asc
import time
import logging

logger = logging.getLogger(__name__)

def query_performance_monitor(func):
    """Decorator to monitor query performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        if execution_time > 0.1:  # Log slow queries (>100ms)
            logger.warning(f"Slow query in {func.__name__}: {execution_time:.3f}s")
        
        return result
    return wrapper

class DatabaseOptimizer:
    """Optimized database query methods"""
    
    @staticmethod
    @query_performance_monitor
    def get_books_with_author_info(limit=None, status=None, author_id=None):
        """Get books with author information in a single query"""
        from .book_platform_models import BookProject, BookPlatformUser, BookStatus
        
        query = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        )
        
        if status:
            query = query.filter(BookProject.status == status)
        
        if author_id:
            query = query.filter(BookProject.author_id == author_id)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    @query_performance_monitor
    def get_dashboard_data(user_id, profile_type):
        """Get all dashboard data in optimized queries"""
        from .book_platform_models import BookProject, BookCollaboration, BookNotification, BookPlatformUser
        from .models import Writer
        
        if profile_type == 'writer':
            # Get writer profile with optimized query
            writer = Writer.query.filter_by(user_id=user_id).first()
            if not writer:
                return None, None, None, None
            
            # Get book platform user for this writer
            book_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
            if not book_user:
                return writer, [], [], []
            
            author_id = book_user.id
        else:
            book_user = BookPlatformUser.query.filter_by(user_id=user_id).first()
            if not book_user:
                return None, [], [], []
            author_id = book_user.id
        
        # Single query to get all authored books with author info
        authored_books = BookProject.query.options(
            joinedload(BookProject.author)
        ).filter_by(author_id=author_id).all()
        
        # Single query to get collaborations
        collaborations = BookCollaboration.query.options(
            joinedload(BookCollaboration.book_project)
        ).filter_by(collaborator_id=author_id, is_active=True).all()
        
        # Single query to get recent notifications
        notifications = BookNotification.query.filter_by(
            user_id=author_id, is_read=False
        ).order_by(desc(BookNotification.created_at)).limit(5).all()
        
        return book_user, authored_books, collaborations, notifications
    
    @staticmethod
    @query_performance_monitor
    def get_marketplace_books(limit=50, genre=None, search_term=None):
        """Get marketplace books with optimized queries"""
        from .book_platform_models import BookProject, BookStatus, BookPlatformUser
        
        query = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).filter(BookProject.status == BookStatus.PUBLISHED)
        
        if genre:
            query = query.filter(BookProject.genre == genre)
        
        if search_term:
            query = query.filter(
                BookProject.title.ilike(f'%{search_term}%') |
                BookProject.description.ilike(f'%{search_term}%')
            )
        
        return query.limit(limit).all()
    
    @staticmethod
    @query_performance_monitor
    def get_book_with_chapters(book_id):
        """Get book with all chapters in a single query"""
        from .book_platform_models import BookProject, BookChapter
        
        return BookProject.query.options(
            joinedload(BookProject.author),
            selectinload(BookProject.chapters).joinedload(BookChapter.versions)
        ).filter_by(id=book_id).first()
    
    @staticmethod
    @query_performance_monitor
    def get_admin_books_data():
        """Get all books for admin panel with optimized queries"""
        from .book_platform_models import BookProject, BookPlatformUser
        
        return BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).order_by(desc(BookProject.created_at)).all()
    
    @staticmethod
    def get_book_stats():
        """Get book statistics efficiently"""
        from .book_platform_models import BookProject, BookStatus
        
        stats = BookProject.query.with_entities(
            BookProject.status,
            func.count(BookProject.id).label('count')
        ).group_by(BookProject.status).all()
        
        return {stat.status.value: stat.count for stat in stats}

class QueryCache:
    """Simple in-memory cache for frequently accessed data"""
    
    _cache = {}
    _cache_timestamps = {}
    CACHE_DURATION = 300  # 5 minutes
    
    @classmethod
    def get(cls, key):
        """Get cached data if not expired"""
        if key in cls._cache:
            if time.time() - cls._cache_timestamps[key] < cls.CACHE_DURATION:
                return cls._cache[key]
            else:
                # Remove expired cache
                del cls._cache[key]
                del cls._cache_timestamps[key]
        return None
    
    @classmethod
    def set(cls, key, value):
        """Cache data with timestamp"""
        cls._cache[key] = value
        cls._cache_timestamps[key] = time.time()
    
    @classmethod
    def clear(cls):
        """Clear all cached data"""
        cls._cache.clear()
        cls._cache_timestamps.clear()

def cache_result(cache_key_func):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache_key_func(*args, **kwargs)
            cached_result = QueryCache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            QueryCache.set(cache_key, result)
            return result
        return wrapper
    return decorator