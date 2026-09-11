"""
Database Query Optimizer for Ink Studio
Optimizes database queries to reduce N+1 problems and improve performance
"""

from functools import wraps
from flask import current_app
from sqlalchemy.orm import joinedload, selectinload, subqueryload
from sqlalchemy import func, desc, asc, or_, and_
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
        
        # Single query to get all authored books with author info (eager load nested user relationship)
        authored_books = BookProject.query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).filter_by(author_id=author_id).all()
        
        # Single query to get collaborations with eager loading
        collaborations = BookCollaboration.query.options(
            joinedload(BookCollaboration.book_project).joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        ).filter_by(collaborator_id=author_id, is_active=True).all()
        
        # Single query to get recent notifications
        notifications = BookNotification.query.filter_by(
            user_id=author_id, is_read=False
        ).order_by(desc(BookNotification.created_at)).limit(5).all()
        
        return book_user, authored_books, collaborations, notifications
    
    @staticmethod
    def _marketplace_published_filter():
        from .book_platform_models import BookProject, BookStatus
        return or_(
            BookProject.status == BookStatus.PUBLISHED,
            BookProject.digital_book_published == True,
            BookProject.audiobook_published == True,
            and_(
                BookProject.print_enabled == True,
                BookProject.print_price.isnot(None),
                BookProject.print_price > 0,
            ),
        )

    @staticmethod
    def marketplace_books_base_query(genre=None, language=None, search_term=None, price_range=None):
        """
        Base query for marketplace listings (no eager load, safe for count).
        Search matches title, description, pen name, username, first/last name.
        """
        from .book_platform_models import BookProject, BookPlatformUser
        from .models import User

        query = BookProject.query.filter(DatabaseOptimizer._marketplace_published_filter())

        if genre:
            query = query.filter(BookProject.genre == genre)
        if language:
            query = query.filter(BookProject.language == language)

        if price_range:
            pr = (price_range or "").strip()

            def _price_column_in_range(column):
                if pr == "0-5":
                    return or_(column.is_(None), column <= 5)
                if pr == "5-10":
                    return and_(column.isnot(None), column > 5, column <= 10)
                if pr == "10-20":
                    return and_(column.isnot(None), column > 10, column <= 20)
                if pr == "20+":
                    return and_(column.isnot(None), column > 20)
                return None

            price_match = _price_column_in_range(BookProject.price)
            audio_match = _price_column_in_range(BookProject.audiobook_price)
            print_match = and_(
                BookProject.print_enabled == True,
                _price_column_in_range(BookProject.print_price),
            )
            query = query.filter(or_(price_match, audio_match, print_match))

        st = (search_term or "").strip()
        if st:
            term = f"%{st}%"
            query = (
                query.join(BookPlatformUser, BookProject.author_id == BookPlatformUser.id)
                .join(User, BookPlatformUser.user_id == User.user_id)
                .filter(
                    or_(
                        BookProject.title.ilike(term),
                        BookProject.description.ilike(term),
                        BookPlatformUser.pen_name.ilike(term),
                        User.username.ilike(term),
                        User.first_name.ilike(term),
                        User.last_name.ilike(term),
                    )
                )
            )
        return query

    @staticmethod
    @query_performance_monitor
    def count_marketplace_books(genre=None, language=None, search_term=None, price_range=None):
        return DatabaseOptimizer.marketplace_books_base_query(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        ).count()

    @staticmethod
    @query_performance_monitor
    def get_marketplace_books(
        limit=20,
        offset=0,
        genre=None,
        language=None,
        search_term=None,
        sort_by="newest",
        price_range=None,
    ):
        """Paginated marketplace books with sort. Default sort: newest first."""
        from .book_platform_models import BookProject, BookPlatformUser

        query = DatabaseOptimizer.marketplace_books_base_query(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        )
        query = query.options(
            joinedload(BookProject.author).joinedload(BookPlatformUser.user)
        )

        sort_by = (sort_by or "newest").lower()
        if sort_by == "oldest":
            query = query.order_by(asc(BookProject.created_at), asc(BookProject.id))
        elif sort_by == "price_low":
            query = query.order_by(asc(BookProject.price), asc(BookProject.id))
        elif sort_by == "price_high":
            query = query.order_by(desc(BookProject.price), asc(BookProject.id))
        elif sort_by == "title":
            query = query.order_by(asc(BookProject.title), asc(BookProject.id))
        elif sort_by == "popular":
            query = query.order_by(desc(BookProject.total_sales), desc(BookProject.id))
        else:
            query = query.order_by(desc(BookProject.created_at), desc(BookProject.id))

        return query.offset(offset).limit(limit).all()

    @staticmethod
    @query_performance_monitor
    def get_marketplace_list_stats(genre=None, language=None, search_term=None, price_range=None):
        """Totals for current filter (for marketplace sidebar)."""
        from .book_platform_models import BookProject

        total = DatabaseOptimizer.count_marketplace_books(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        )
        from .book_purchase_format import (
            marketplace_is_explicitly_free,
            marketplace_min_paid_price,
            _marketplace_stats_row_as_book,
        )

        base = DatabaseOptimizer.marketplace_books_base_query(
            genre=genre, language=language, search_term=search_term, price_range=price_range
        )
        rows = base.with_entities(
            BookProject.id,
            BookProject.price,
            BookProject.digital_book_published,
            BookProject.digital_file_path,
            BookProject.audiobook_published,
            BookProject.has_audiobook,
            BookProject.audiobook_price,
            BookProject.print_enabled,
            BookProject.print_price,
            BookProject.status,
        ).all()
        paid = 0
        free = 0
        for row in rows:
            book = _marketplace_stats_row_as_book(row)
            if marketplace_is_explicitly_free(book):
                free += 1
            elif marketplace_min_paid_price(book) is not None:
                paid += 1

        return {"total": total, "paid": paid, "free": free}

    @staticmethod
    @query_performance_monitor
    def get_available_languages():
        """Get all unique languages from published books with book counts"""
        from .book_platform_models import BookProject, BookStatus
        from sqlalchemy import or_
        
        languages = BookProject.query.with_entities(
            BookProject.language,
            func.count(BookProject.id).label('count')
        ).filter(
            or_(
                BookProject.status == BookStatus.PUBLISHED,
                BookProject.digital_book_published == True,
                BookProject.audiobook_published == True
            ),
            BookProject.language.isnot(None),
            BookProject.language != ''
        ).group_by(BookProject.language).order_by(BookProject.language).all()
        
        return [{'language': lang.language, 'count': lang.count} for lang in languages]
    
    @staticmethod
    @query_performance_monitor
    def get_available_genres():
        """Get all unique genres from published books with book counts"""
        from .book_platform_models import BookProject, BookStatus
        from sqlalchemy import or_
        
        genres = BookProject.query.with_entities(
            BookProject.genre,
            func.count(BookProject.id).label('count')
        ).filter(
            or_(
                BookProject.status == BookStatus.PUBLISHED,
                BookProject.digital_book_published == True,
                BookProject.audiobook_published == True
            ),
            BookProject.genre.isnot(None),
            BookProject.genre != ''
        ).group_by(BookProject.genre).order_by(BookProject.genre).all()
        
        return [{'genre': genre.genre, 'count': genre.count} for genre in genres]
    
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