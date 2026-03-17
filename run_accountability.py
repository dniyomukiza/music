#!/usr/bin/env python3
"""
Run daily accountability check for all books with funded campaigns.
Schedule via cron (e.g. daily at 2am):
    0 2 * * * cd /path/to/project && python run_accountability.py
"""
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    from glconnect import create_app, db
    from glconnect.accountability_service import check_all_books_accountability

    app, _ = create_app()
    with app.app_context():
        result = check_all_books_accountability(db)
        if result.get('success'):
            logger.info(f"Accountability check complete: {result.get('books_checked', 0)} books checked")
            for r in result.get('results', []):
                res = r.get('result', {})
                if res.get('actions_taken'):
                    logger.info(f"  Book {r.get('book_id')}: {res.get('actions_taken')}")
                if res.get('warnings'):
                    logger.warning(f"  Book {r.get('book_id')}: {res.get('warnings')}")
        else:
            logger.error(f"Accountability check failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)


if __name__ == '__main__':
    main()
