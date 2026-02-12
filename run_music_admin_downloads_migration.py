#!/usr/bin/env python3
"""
Run migration: song approval_status, downloaded_songs table, playlists.download_id.
Idempotent – safe to run multiple times.
Uses DB_URL from environment.
"""

import os
import sys

DB_URL = os.getenv(
    "DB_URL",
    "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr",
)


def column_exists(cursor, table, column):
    cursor.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cursor.fetchone() is not None


def table_exists(cursor, table):
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


def run_migration():
    try:
        import psycopg2
    except ImportError:
        print("Install psycopg2: pip install psycopg2-binary")
        return False

    conn = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # 1. songs.approval_status
        if not column_exists(cur, "songs", "approval_status"):
            print("  Adding songs.approval_status...")
            cur.execute("ALTER TABLE songs ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'")
        else:
            print("  songs.approval_status already exists")

        # 2. song_upload.approval_status
        if not column_exists(cur, "song_upload", "approval_status"):
            print("  Adding song_upload.approval_status...")
            cur.execute("ALTER TABLE song_upload ADD COLUMN approval_status VARCHAR(20) DEFAULT 'approved'")
        else:
            print("  song_upload.approval_status already exists")

        # 3. Create downloaded_songs table
        if not table_exists(cur, "downloaded_songs"):
            print("  Creating table downloaded_songs...")
            cur.execute("""
                CREATE TABLE downloaded_songs (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    artist VARCHAR(100),
                    local_path VARCHAR(200),
                    created_at TIMESTAMP WITH TIME ZONE
                )
            """)
        else:
            print("  Table downloaded_songs already exists")

        # 4. playlists.download_id
        if not column_exists(cur, "playlists", "download_id"):
            print("  Adding playlists.download_id...")
            cur.execute(
                "ALTER TABLE playlists ADD COLUMN download_id INTEGER REFERENCES downloaded_songs(id)"
            )
        else:
            print("  playlists.download_id already exists")

        # 5. playlists.song_id allow NULL
        print("  Ensuring playlists.song_id is nullable...")
        cur.execute("ALTER TABLE playlists ALTER COLUMN song_id DROP NOT NULL")

        conn.commit()
        cur.close()
        conn.close()
        print("\nMigration completed successfully.")
        return True
    except Exception as e:
        if conn:
            conn.rollback()
            try:
                conn.close()
            except Exception:
                pass
        print(f"\nMigration failed: {e}")
        raise
    return False


if __name__ == "__main__":
    try:
        ok = run_migration()
        sys.exit(0 if ok else 1)
    except Exception:
        sys.exit(1)
