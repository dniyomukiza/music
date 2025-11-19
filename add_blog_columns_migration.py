"""
Migration script to add category, language, and country columns to post table
Run this script to add the new columns for blog filtering and translation features
"""

from glconnect import create_app, db
from glconnect.models import Post
from sqlalchemy import text

def add_blog_columns():
    """Add new columns to post table if they don't exist"""
    app, socketio = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('post')]
            
            # Add category column if it doesn't exist
            if 'category' not in columns:
                print("Adding 'category' column to post table...")
                db.session.execute(text("ALTER TABLE post ADD COLUMN category VARCHAR(100)"))
                print("✓ Added 'category' column")
            else:
                print("✓ 'category' column already exists")
            
            # Add language column if it doesn't exist
            if 'language' not in columns:
                print("Adding 'language' column to post table...")
                db.session.execute(text("ALTER TABLE post ADD COLUMN language VARCHAR(50) DEFAULT 'en'"))
                print("✓ Added 'language' column")
            else:
                print("✓ 'language' column already exists")
            
            # Add country column if it doesn't exist
            if 'country' not in columns:
                print("Adding 'country' column to post table...")
                db.session.execute(text("ALTER TABLE post ADD COLUMN country VARCHAR(100)"))
                print("✓ Added 'country' column")
            else:
                print("✓ 'country' column already exists")
            
            db.session.commit()
            print("\n✅ Migration completed successfully!")
            print("All columns have been added to the post table.")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during migration: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

if __name__ == '__main__':
    print("=" * 60)
    print("Blog Columns Migration Script")
    print("=" * 60)
    print("\nThis script will add the following columns to the 'post' table:")
    print("  - category (VARCHAR(100))")
    print("  - language (VARCHAR(50), default 'en')")
    print("  - country (VARCHAR(100))")
    print("\nStarting migration...\n")
    
    success = add_blog_columns()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed! You can now use the Content Hub.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Please check the error messages above.")
        print("=" * 60)

