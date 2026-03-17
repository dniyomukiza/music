"""
Migration script to add likes and impressions metrics to blog posts
Run this script to add the necessary columns and tables to the database
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, Post, PostLike, PostView
from sqlalchemy import text, inspect

def run_migration():
    app, socketio = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Check and add columns to Post table
        columns = [col['name'] for col in inspector.get_columns('post')]
        
        if 'likes_count' not in columns:
            db.session.execute(text("ALTER TABLE post ADD COLUMN likes_count INTEGER DEFAULT 0 NOT NULL"))
            print("✓ Added 'likes_count' column to post table")
        
        if 'impressions_count' not in columns:
            db.session.execute(text("ALTER TABLE post ADD COLUMN impressions_count INTEGER DEFAULT 0 NOT NULL"))
            print("✓ Added 'impressions_count' column to post table")
        
        # Initialize existing posts with 0 counts
        db.session.execute(text("UPDATE post SET likes_count = 0 WHERE likes_count IS NULL"))
        db.session.execute(text("UPDATE post SET impressions_count = 0 WHERE impressions_count IS NULL"))
        
        # Create PostLike table if it doesn't exist
        if 'post_likes' not in inspector.get_table_names():
            PostLike.__table__.create(db.engine)
            print("✓ Created 'post_likes' table")
        else:
            print("✓ 'post_likes' table already exists")
        
        # Create PostView table if it doesn't exist
        if 'post_views' not in inspector.get_table_names():
            PostView.__table__.create(db.engine)
            print("✓ Created 'post_views' table")
        else:
            print("✓ 'post_views' table already exists")
        
        # Update likes_count from actual PostLike records
        print("\nUpdating likes_count from existing likes...")
        posts_with_likes = db.session.execute(text("""
            SELECT post_id, COUNT(*) as like_count 
            FROM post_likes 
            GROUP BY post_id
        """)).fetchall()
        
        for post_id, like_count in posts_with_likes:
            db.session.execute(text("""
                UPDATE post 
                SET likes_count = :count 
                WHERE id = :post_id
            """), {'count': like_count, 'post_id': post_id})
        
        # Update impressions_count from actual PostView records
        print("Updating impressions_count from existing views...")
        posts_with_views = db.session.execute(text("""
            SELECT post_id, COUNT(*) as view_count 
            FROM post_views 
            GROUP BY post_id
        """)).fetchall()
        
        for post_id, view_count in posts_with_views:
            db.session.execute(text("""
                UPDATE post 
                SET impressions_count = :count 
                WHERE id = :post_id
            """), {'count': view_count, 'post_id': post_id})
        
        db.session.commit()
        print("\n✅ Migration completed successfully!")
        print("\nSummary:")
        print(f"  - Added metrics columns to post table")
        print(f"  - Created post_likes table for tracking likes")
        print(f"  - Created post_views table for tracking impressions")
        print(f"  - Initialized all existing posts with 0 counts")
        print(f"  - Synced counts from existing like/view records")

if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

