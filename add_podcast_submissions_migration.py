"""
Migration script to create podcast_submissions table
Run this script to add the necessary table to the database
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, PodcastSubmission
from sqlalchemy import inspect

def run_migration():
    app, socketio = create_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        # Create PodcastSubmission table if it doesn't exist
        if 'podcast_submissions' not in inspector.get_table_names():
            PodcastSubmission.__table__.create(db.engine)
            print("✓ Created 'podcast_submissions' table")
        else:
            print("✓ 'podcast_submissions' table already exists")
        
        print("\n✅ Migration completed successfully!")

if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

