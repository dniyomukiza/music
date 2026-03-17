#!/usr/bin/env python3
"""
Run the digital_book_published and audiobook_published columns migration
This script connects to your PostgreSQL database and runs the migration
"""

import psycopg2
import sys
import os

# Database connection string (from docker-compose.yml or environment)
DB_URL = os.getenv("DB_URL", "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr")

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_name = %s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]

def run_migration():
    """Run the migration script - safely checks for existing columns before adding"""
    conn = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        columns_to_add = [
            ('digital_book_published', 'BOOLEAN DEFAULT FALSE', 'Whether digital book is published to marketplace'),
            ('digital_book_published_at', 'TIMESTAMP', 'When digital book was published'),
            ('audiobook_published', 'BOOLEAN DEFAULT FALSE', 'Whether audiobook is published to marketplace'),
            ('audiobook_published_at', 'TIMESTAMP', 'When audiobook was published'),
        ]
        
        added_columns = []
        skipped_columns = []
        
        print("Checking existing schema...")
        for column_name, column_type, description in columns_to_add:
            if check_column_exists(cur, 'book_projects', column_name):
                print(f"  ⚠️  Column '{column_name}' already exists - skipping")
                skipped_columns.append(column_name)
            else:
                print(f"  ➕ Adding column '{column_name}'...")
                try:
                    cur.execute(f"""
                        ALTER TABLE book_projects 
                        ADD COLUMN {column_name} {column_type}
                    """)
                    cur.execute(f"""
                        COMMENT ON COLUMN book_projects.{column_name} IS %s
                    """, (description,))
                    added_columns.append(column_name)
                    print(f"     ✅ Added '{column_name}' successfully")
                except psycopg2.Error as e:
                    print(f"     ❌ Failed to add '{column_name}': {e}")
                    conn.rollback()
                    return False
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Migration completed successfully!")
        print("="*60)
        if added_columns:
            print(f"\n📝 New columns added ({len(added_columns)}):")
            for col in added_columns:
                print(f"   • {col}")
        if skipped_columns:
            print(f"\n⏭️  Columns already exist ({len(skipped_columns)}):")
            for col in skipped_columns:
                print(f"   • {col}")
        print("\n💡 Please restart your Flask server to apply changes.")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
