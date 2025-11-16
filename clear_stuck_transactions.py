#!/usr/bin/env python3
"""
Clear stuck database transactions
This script terminates any aborted transactions in the database
"""

import psycopg2
import sys
import os

# Database connection string
DB_URL = os.getenv('DATABASE_URL', "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr")

def clear_stuck_transactions():
    """Terminate stuck/aborted transactions"""
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # Find and terminate aborted transactions
        print("Checking for stuck transactions...")
        cur.execute("""
            SELECT pid, usename, datname, state, query 
            FROM pg_stat_activity 
            WHERE datname = 'music_owqr' 
            AND state = 'idle in transaction (aborted)';
        """)
        
        stuck_transactions = cur.fetchall()
        
        if stuck_transactions:
            print(f"Found {len(stuck_transactions)} stuck transaction(s):")
            for pid, user, db, state, query in stuck_transactions:
                print(f"  - PID {pid}: {state} (User: {user})")
                if query:
                    print(f"    Query: {query[:100]}...")
            
            # Terminate stuck transactions
            print("\nTerminating stuck transactions...")
            cur.execute("""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = 'music_owqr' 
                AND state = 'idle in transaction (aborted)';
            """)
            
            terminated = cur.rowcount
            conn.commit()
            print(f"✅ Terminated {terminated} stuck transaction(s)")
        else:
            print("✅ No stuck transactions found")
        
        # Also check for any other idle transactions
        cur.execute("""
            SELECT pid, usename, state 
            FROM pg_stat_activity 
            WHERE datname = 'music_owqr' 
            AND state LIKE 'idle%'
            AND pid != pg_backend_pid();
        """)
        
        idle_connections = cur.fetchall()
        if idle_connections:
            print(f"\nFound {len(idle_connections)} idle connection(s)")
            for pid, user, state in idle_connections:
                print(f"  - PID {pid}: {state} (User: {user})")
        
        cur.close()
        conn.close()
        
        print("\n✅ Database connection cleanup completed!")
        print("Please restart your Flask server now.")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = clear_stuck_transactions()
    sys.exit(0 if success else 1)





