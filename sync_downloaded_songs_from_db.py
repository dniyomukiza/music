#!/usr/bin/env python3
"""
One-off script: use downloaded_songs table to rename files to "name by artist.mp3"
and overwrite glconnect/ytauto.m3u. Run from project root (e.g. on server: ~/music).

Usage:
  On server (host, with DB env):
    cd ~/music && python sync_downloaded_songs_from_db.py

  Inside app container (uses container DB env):
    docker compose exec app python /usr/src/appdir/sync_downloaded_songs_from_db.py
"""
import os
import sys

# Use DATABASE_URL from env (Docker) as DB_URL if DB_URL not set
if not os.environ.get("DB_URL") and os.environ.get("DATABASE_URL"):
    os.environ["DB_URL"] = os.environ["DATABASE_URL"]

# Project root = directory where this script lives
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

def main():
    from glconnect.pipeline import app, sync_from_downloaded_songs

    with app.app_context():
        renamed, m3u_updated = sync_from_downloaded_songs()
    print(f"Done: {renamed} file(s) renamed, M3U updated: {m3u_updated}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
