"""
Shared utilities for book platform - avoids circular imports.
"""


def is_book_published(book):
    """
    Unified check: book is published if:
    - status == PUBLISHED (platform-created books), or
    - digital_book_published == True (uploaded digital), or
    - audiobook_published == True (audiobook)
    """
    if not book:
        return False
    from glconnect.book_platform_models import BookStatus
    if book.status == BookStatus.PUBLISHED:
        return True
    if getattr(book, 'digital_book_published', False):
        return True
    if getattr(book, 'audiobook_published', False):
        return True
    return False
