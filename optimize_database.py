#!/usr/bin/env python3
"""
Database Index Optimization Script for Ink Studio
Creates indexes to improve query performance
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_database_uri():
    """Get database URI from environment or config"""
    db_uri = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
    if db_uri:
        return db_uri.strip()

    print("Set DATABASE_URL or DB_URL before running this script.")
    return None

def create_indexes():
    """Create database indexes for optimal performance"""
    db_uri = get_database_uri()
    if not db_uri:
        print("Could not connect to database")
        return False
    
    engine = create_engine(db_uri)
    
    # Define indexes to create
    indexes = [
        # Book Project indexes
        "CREATE INDEX IF NOT EXISTS idx_book_projects_status ON book_projects(status);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_author_id ON book_projects(author_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_genre ON book_projects(genre);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_created_at ON book_projects(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_published_at ON book_projects(published_at);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_price ON book_projects(price);",
        
        # Book Platform User indexes
        "CREATE INDEX IF NOT EXISTS idx_book_platform_users_user_id ON book_platform_users(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_platform_users_pen_name ON book_platform_users(pen_name);",
        
        # Book Chapter indexes
        "CREATE INDEX IF NOT EXISTS idx_book_chapters_book_project_id ON book_chapters(book_project_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_chapters_chapter_number ON book_chapters(chapter_number);",
        
        # Book Collaboration indexes
        "CREATE INDEX IF NOT EXISTS idx_book_collaborations_book_project_id ON book_collaborations(book_project_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_collaborations_collaborator_id ON book_collaborations(collaborator_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_collaborations_is_active ON book_collaborations(is_active);",
        
        # Book Comment indexes
        "CREATE INDEX IF NOT EXISTS idx_book_comments_book_project_id ON book_comments(book_project_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_comments_commenter_id ON book_comments(commenter_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_comments_created_at ON book_comments(created_at);",
        
        # Book Purchase indexes
        "CREATE INDEX IF NOT EXISTS idx_book_purchases_buyer_id ON book_purchases(buyer_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_purchases_book_project_id ON book_purchases(book_project_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_purchases_status ON book_purchases(status);",
        "CREATE INDEX IF NOT EXISTS idx_book_purchases_created_at ON book_purchases(created_at);",
        
        # Book Sale indexes
        "CREATE INDEX IF NOT EXISTS idx_book_sales_seller_id ON book_sales(seller_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_sales_book_project_id ON book_sales(book_project_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_sales_created_at ON book_sales(created_at);",
        
        # Book Notification indexes
        "CREATE INDEX IF NOT EXISTS idx_book_notifications_user_id ON book_notifications(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_notifications_is_read ON book_notifications(is_read);",
        "CREATE INDEX IF NOT EXISTS idx_book_notifications_created_at ON book_notifications(created_at);",
        
        # Composite indexes for common query patterns
        "CREATE INDEX IF NOT EXISTS idx_book_projects_status_author ON book_projects(status, author_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_projects_status_genre ON book_projects(status, genre);",
        "CREATE INDEX IF NOT EXISTS idx_book_collaborations_active_collaborator ON book_collaborations(is_active, collaborator_id);",
        "CREATE INDEX IF NOT EXISTS idx_book_notifications_user_unread ON book_notifications(user_id, is_read);",
    ]
    
    try:
        with engine.connect() as conn:
            print("Creating database indexes...")
            
            for i, index_sql in enumerate(indexes, 1):
                try:
                    conn.execute(text(index_sql))
                    print(f"✓ Created index {i}/{len(indexes)}")
                except SQLAlchemyError as e:
                    print(f"✗ Failed to create index {i}: {e}")
            
            conn.commit()
            print(f"\n✓ Successfully created {len(indexes)} database indexes")
            return True
            
    except Exception as e:
        print(f"Error creating indexes: {e}")
        return False

def analyze_query_performance():
    """Analyze query performance and suggest optimizations"""
    db_uri = get_database_uri()
    if not db_uri:
        return False
    
    engine = create_engine(db_uri)
    
    # Common queries to analyze
    queries = [
        {
            'name': 'Published books with author info',
            'sql': '''
                SELECT bp.*, bpu.pen_name, u.username 
                FROM book_projects bp 
                JOIN book_platform_users bpu ON bp.author_id = bpu.id 
                JOIN users u ON bpu.user_id = u.user_id 
                WHERE bp.status = 'published' 
                ORDER BY bp.created_at DESC 
                LIMIT 50;
            '''
        },
        {
            'name': 'User dashboard data',
            'sql': '''
                SELECT bp.*, bc.*, bn.* 
                FROM book_projects bp 
                LEFT JOIN book_collaborations bc ON bp.author_id = bc.collaborator_id 
                LEFT JOIN book_notifications bn ON bp.author_id = bn.user_id 
                WHERE bp.author_id = 1;
            '''
        },
        {
            'name': 'Marketplace search',
            'sql': '''
                SELECT bp.*, bpu.pen_name 
                FROM book_projects bp 
                JOIN book_platform_users bpu ON bp.author_id = bpu.id 
                WHERE bp.status = 'published' 
                AND (bp.title ILIKE '%search%' OR bp.description ILIKE '%search%');
            '''
        }
    ]
    
    try:
        with engine.connect() as conn:
            print("\n=== Query Performance Analysis ===")
            
            for query in queries:
                print(f"\nAnalyzing: {query['name']}")
                try:
                    result = conn.execute(text(f"EXPLAIN ANALYZE {query['sql']}"))
                    for row in result:
                        print(f"  {row[0]}")
                except SQLAlchemyError as e:
                    print(f"  Error analyzing query: {e}")
            
            return True
            
    except Exception as e:
        print(f"Error analyzing queries: {e}")
        return False

def main():
    """Main function"""
    print("=== Ink Studio Database Optimization ===")
    
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        analyze_query_performance()
    else:
        success = create_indexes()
        if success:
            print("\n✓ Database optimization completed successfully!")
            print("Run 'python optimize_database.py analyze' to analyze query performance")
        else:
            print("\n✗ Database optimization failed!")

if __name__ == '__main__':
    main()
