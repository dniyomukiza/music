#!/usr/bin/env python3
"""
Run the accountability columns migration
This script connects to your PostgreSQL database and runs the migration
"""

import psycopg2
import sys
import os

# Database connection string (from docker-compose.yml)
DB_URL = "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr"

def run_migration():
    """Run the migration script"""
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("Reading migration file...")
        migration_file = os.path.join(os.path.dirname(__file__), 'add_accountability_columns.sql')
        
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        print("Executing migration...")
        cur.execute(migration_sql)
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ Migration completed successfully!")
        print("\nColumns added:")
        print("  - investment_campaigns.cancelled_at")
        print("  - investment_campaigns.cancellation_reason")
        print("  - book_investments.refunded_at")
        print("  - reviewer_earnings.is_guarantee_payment")
        print("  - reviewer_earnings.notes")
        print("  - refund_requests table (new)")
        print("\nPlease restart your Flask server to apply changes.")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: Migration file not found: {migration_file}")
        return False
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)


