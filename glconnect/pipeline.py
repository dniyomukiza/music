import os
import json
from flask import Flask, has_app_context
from subprocess import run
from dotenv import load_dotenv
try:
    from glconnect.models import db, Song, DownloadedSong
except ImportError:
    from models import db, Song, DownloadedSong

# Load configuration from environment variables
config = {
    "DB_URL": os.getenv("DB_URL", "postgresql://music_owqr_user:D8SRPZ7ubYN79Pdh6E8aKzg4O2yirBrL@dpg-ct1ae39u0jms73cdpjdg-a.oregon-postgres.render.com/music_owqr")
}
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "abarayon"
db.init_app(app)

# Connect to existing database (don't create tables)
# with app.app_context():
#     db.create_all()

# Path to your output folder for music files
output_folder = os.path.join(os.getcwd(), "glconnect/static/ytauto")

class AudioDownloader:
    def __init__(self, playlist_url=None, output_folder=None):
        self.playlist_url = playlist_url.strip() if playlist_url else None
        self.output_folder = os.path.expanduser(output_folder) if output_folder else os.getcwd()

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def download_audio(self):
        if not self.playlist_url:
            raise ValueError("No playlist URL provided for downloading.")
        import shutil
        ytdlp_path = shutil.which("yt-dlp")
        if not ytdlp_path:
            raise FileNotFoundError(
                "yt-dlp is not installed or not in PATH. Install it (e.g. pip install yt-dlp or brew install yt-dlp) and try again."
            )
        self.prepare_output_folder()
        print(f"Downloading to folder: {self.output_folder}")
        # Build options so URL is the only positional arg (avoid yt-dlp confusing cookies path with URL)
        command = [
            ytdlp_path,
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--yes-playlist",
            "--extractor-args", "youtube:player_client=android,web",
            # JS runtime for YouTube signature/n challenge solving (EJS); Node is in app image
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "-o", os.path.join(self.output_folder, "%(title)s.%(ext)s"),
        ]
        # YTDLP_COOKIES_FILE is set in container env (e.g. /usr/src/appdir/ytdlp_cookies.txt); used as-is
        cookies_file = os.environ.get("YTDLP_COOKIES_FILE")
        if cookies_file and os.path.isfile(cookies_file):
            command.extend(["--cookies", cookies_file])
            print(f"Using cookies file: {cookies_file}")
        elif cookies_file:
            print(f"YTDLP_COOKIES_FILE is set but file not found: {cookies_file} (download may fail with 'Sign in to confirm you're not a bot')")
        else:
            print("No YTDLP_COOKIES_FILE set; if YouTube blocks with 'bot' error, add cookies (see docs/YTDLP_COOKIES.md)")
        command.append(self.playlist_url)
        print(f"Running command: {' '.join(command)}")
        result = run(command, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip() or f"Exit code {result.returncode}"
            raise RuntimeError(f"yt-dlp failed: {err}")
        mp3s = [f for f in os.listdir(self.output_folder) if f.endswith(".mp3")]
        if not mp3s:
            raise RuntimeError("yt-dlp finished but no MP3 files were saved. Check the URL and that the video/playlist is available.")
        print(f"Download completed successfully! {len(mp3s)} file(s) saved to: {self.output_folder}")

    def download_and_convert(self):
        self.download_audio()

class MusicFileRenamer:
    @staticmethod
    def clean_music_names(directory):
        if not os.path.exists(directory):
            print(f"Directory {directory} does not exist yet. Skipping rename step.")
            return
        directory = os.path.abspath(directory)
        for filename in os.listdir(directory):
            try:
                src = os.path.join(directory, filename)
                if not os.path.isfile(src):
                    continue
                base_name, extension = os.path.splitext(filename)
                import re
                base_name = re.sub(r'\[.*?\]', '', base_name)
                base_name = re.sub(r'\(.*?\)', '', base_name)
                base_name = re.sub(r'[^\w\s\-&]', '', base_name)
                base_name = re.sub(r'\s+', ' ', base_name).strip()
                parts = base_name.split(" - ")
                if len(parts) == 2:
                    artist = parts[0].strip()
                    song = parts[1].strip()
                    new_filename = f"{artist} - {song}{extension}"
                    if new_filename != filename:
                        dst = os.path.join(directory, new_filename)
                        os.rename(src, dst)
                        print(f"Renamed: {filename} -> {new_filename}")
                    else:
                        print(f"No changes needed: {filename}")
                else:
                    print(f"Skipping file (unexpected format): {filename}")
            except Exception as e:
                print(f"Error renaming {filename}: {e}")

class PlaylistIngestion:
    @staticmethod
    def extract_name_artist(file_path):
        file_path = os.path.normpath(file_path)
        keyword = os.path.join("ytauto", "") 
        if keyword in file_path:
            relative_path = file_path.split(keyword, 1)[1]
        else:
            print(f"Skipping file, 'ytauto/' not found in path: {file_path}")
            return None, None  
        
        # Extract artist and song name
        if ' - ' in relative_path:
            artist, song_name = relative_path.split(' - ', 1)
            song_name = song_name.replace('.mp3', '').strip()
        else:
            artist = None
            song_name = os.path.basename(relative_path).replace('.mp3', '').strip()
    
        return artist, song_name

    @staticmethod
    def _do_ingest(m3u_path):
        """Inner ingestion: expects to run inside an active Flask app context. Returns (added_count, skipped_count)."""
        with open(m3u_path, 'r') as m3u_file:
            added_count = 0
            skipped_count = 0
            for line in m3u_file:
                line = line.strip()
                if line:
                    artist, song_name = PlaylistIngestion.extract_name_artist(line)
                    if artist is None and song_name is None:
                        continue
                    existing = DownloadedSong.query.filter_by(
                        artist=artist,
                        name=song_name
                    ).first()
                    if existing:
                        print(f"Skipped duplicate download: {artist} - {song_name}")
                        skipped_count += 1
                    else:
                        row = DownloadedSong(name=song_name, artist=artist, local_path=line)
                        db.session.add(row)
                        print(f"Added download: {artist} - {song_name}")
                        added_count += 1
            db.session.commit()
            print(f"Download ingestion complete: {added_count} added, {skipped_count} skipped.")
            return added_count, skipped_count
        return 0, 0

    @staticmethod
    def ingest_songs_from_m3u(file_path):
        """Ingest YouTube-downloaded tracks into downloaded_songs table only (not songs). Returns (added_count, skipped_count)."""
        if has_app_context():
            return PlaylistIngestion._do_ingest(file_path)
        with app.app_context():
            return PlaylistIngestion._do_ingest(file_path)

    @staticmethod
    def ingest_songs_from_folder(output_folder):
        """
        Ingest by reading the folder directly: each file gets a row with local_path = exact filename.
        So when you later click Clean, we know exactly which file to rename (no matching by name/artist).
        Does NOT write the M3U file; M3U is written only when you click Clean.
        Returns (added_count, skipped_count).
        """
        if not has_app_context():
            with app.app_context():
                return PlaylistIngestion._do_ingest_from_folder(output_folder)
        return PlaylistIngestion._do_ingest_from_folder(output_folder)

    @staticmethod
    def _do_ingest_from_folder(output_folder):
        """Inner: scan folder, insert rows with exact local_path. Must run in app context."""
        prefix_liq = "/liqfolder/glconnect/static/ytauto/"
        if not os.path.isdir(output_folder):
            print(f"Output folder does not exist: {output_folder}")
            return 0, 0
        mp3_files = [f for f in os.listdir(output_folder) if f.endswith(".mp3")]
        added_count = 0
        skipped_count = 0
        for filename in sorted(mp3_files, key=lambda x: x.lower()):
            artist, song_name = _parse_artist_title(filename)
            key_artist = (artist or "").strip() or None
            key_name = (song_name or "").strip() or "Unknown"
            existing = DownloadedSong.query.filter_by(artist=key_artist, name=key_name).first()
            if existing:
                print(f"Skipped duplicate: {artist} - {song_name}")
                skipped_count += 1
                continue
            local_path = prefix_liq + filename
            row = DownloadedSong(name=key_name, artist=key_artist, local_path=local_path)
            db.session.add(row)
            print(f"Added: {artist} - {song_name} -> {filename}")
            added_count += 1
        db.session.commit()
        print(f"Folder ingestion complete: {added_count} added, {skipped_count} skipped. M3U not written (run Clean after editing DB).")
        return added_count, skipped_count

    @staticmethod
    def save_song_to_db(artist, song_name, local_path):
        """Save one YouTube-downloaded track to downloaded_songs table."""
        with app.app_context():
            existing = DownloadedSong.query.filter_by(artist=artist, name=song_name).first()
            if existing:
                print(f"Skipped duplicate: {artist} - {song_name}")
                return False
            row = DownloadedSong(name=song_name, artist=artist, local_path=local_path)
            db.session.add(row)
            db.session.commit()
            print(f"Added download: {artist} - {song_name}")
            return True


def _parse_artist_title(filename):
    """Return (artist, song_name) from filename like 'Artist - Song.mp3'. Normalize for dedupe."""
    name = os.path.basename(filename).replace(".mp3", "").strip()
    if " - " in name:
        artist, song_name = name.split(" - ", 1)
        return (artist.strip() or None, song_name.strip())
    return (None, name or None)


def create_or_append_m3u_playlist(output_folder, m3u_filename):
    print(f"Preparing clean .m3u playlist in {output_folder}...")
    glconnect_dir = os.path.dirname(os.path.dirname(output_folder))
    m3u_path = os.path.join(glconnect_dir, m3u_filename)
    print(f"M3U file will be created at: {m3u_path}")

    if not os.path.exists(output_folder):
        print(f"Output folder does not exist: {output_folder}")
        return

    mp3_files = [f for f in os.listdir(output_folder) if f.endswith(".mp3")]
    clean_files = [
        f for f in mp3_files
        if "[" not in f and "]" not in f and "(" not in f and ")" not in f
    ]
    for f in mp3_files:
        if f not in clean_files:
            print(f"Skipping file with brackets/parentheses: {f}")

    # One entry per (artist, title): first occurrence kept, rest are duplicates
    seen_key = {}  # (artist, song_name) -> filename
    for filename in sorted(clean_files, key=lambda x: x.split(" - ")[-1].lower()):
        artist, song_name = _parse_artist_title(filename)
        key = (artist or "", song_name or "")
        if key not in seen_key:
            seen_key[key] = filename

    unique_filenames = list(seen_key.values())
    unique_filenames.sort(key=lambda x: x.split(" - ")[-1].lower())
    print(f"Found {len(clean_files)} MP3 files, {len(unique_filenames)} unique (no duplicates in M3U).")

    # Remove duplicate files from folder (keep one per artist+title)
    for filename in clean_files:
        if filename not in unique_filenames:
            path = os.path.join(output_folder, filename)
            try:
                os.remove(path)
                print(f"Removed duplicate file: {filename}")
            except OSError as e:
                print(f"Could not remove duplicate {filename}: {e}")

    with open(m3u_path, "w") as m3u_file:
        for filename in unique_filenames:
            liqfolder_path = f"/liqfolder/glconnect/static/ytauto/{filename}"
            m3u_file.write(liqfolder_path + "\n")
    print(f"Clean playlist created (no duplicates): {m3u_path}")


def _sanitize_filename(s):
    """Replace path/FS-unsafe chars for use in filenames."""
    if not s:
        return ""
    for c in '\\/:*?"<>|':
        s = s.replace(c, " ")
    return " ".join(s.split()).strip()[:200]


def _normalize_for_match(s):
    """Normalize string for fuzzy matching (lowercase, collapse spaces, drop ft/feat)."""
    if not s:
        return ""
    s = s.lower().strip()
    for x in ("ft.", "ft ", "feat.", "feat "):
        s = s.replace(x, " ")
    return " ".join(s.split())


def _parse_filename_as_artist_title(filename):
    """Return (artist, title) from 'Artist - Title.mp3' or 'Title by Artist.mp3', else (None, None)."""
    base = filename.replace(".mp3", "").strip()
    if " by " in base:
        parts = base.split(" by ", 1)
        return (parts[1].strip(), parts[0].strip())  # (artist, title)
    if " - " in base:
        parts = base.split(" - ", 1)
        return (parts[0].strip(), parts[1].strip())  # (artist, title)
    return (None, None)


def _find_matching_file(output_folder, artist, name, exclude_filenames):
    """
    Find an .mp3 in output_folder whose parsed (artist, title) matches the given artist/name.
    Title: exact match (normalized) OR cleaned name is a prefix of file title (e.g. DB "Wake Up"
    matches file "Wake Upsms" so we find it after you edited name and local_path).
    Artist: exact or one contains the other. Exclude filenames already claimed. Returns filename or None.
    """
    if not os.path.isdir(output_folder):
        return None
    anorm = _normalize_for_match(artist)
    nnorm = _normalize_for_match(name)
    if not nnorm:
        return None
    for fn in os.listdir(output_folder):
        if not fn.endswith(".mp3") or fn in exclude_filenames:
            continue
        a, n = _parse_filename_as_artist_title(fn)
        if n is None:
            continue
        nfile = _normalize_for_match(n)
        # Title: exact match, or cleaned name is prefix of file title (e.g. "Wake Up" -> "Wake Upsms")
        if nfile != nnorm and not (nnorm and nfile.startswith(nnorm)):
            continue
        # Artist: exact or one contains the other
        if not anorm:
            return fn
        if a is None:
            continue
        anorm_file = _normalize_for_match(a)
        if anorm_file == anorm or anorm in anorm_file or anorm_file in anorm:
            return fn
    return None


def _get_new_round_files_by_mtime(output_folder, n, exclude_basenames):
    """
    Return n files that are the "new round" (most recently modified), excluding those in exclude_basenames.
    Order: by mtime ascending so index 0 = oldest in batch = first downloaded.
    """
    if not os.path.isdir(output_folder) or n <= 0:
        return []
    candidates = []
    for fn in os.listdir(output_folder):
        if not fn.endswith(".mp3") or fn in exclude_basenames:
            continue
        path = os.path.join(output_folder, fn)
        try:
            mtime = os.path.getmtime(path)
            candidates.append((fn, mtime))
        except OSError:
            continue
    if len(candidates) < n:
        return []
    candidates.sort(key=lambda x: x[1], reverse=True)
    batch = candidates[:n]
    batch.sort(key=lambda x: x[1])
    return [fn for fn, _ in batch]


def sync_from_downloaded_songs():
    """
    After manual cleanup of downloaded_songs (name, artist), rename files on disk to
    '{name} by {artist}.mp3', update local_path in DB, and overwrite the M3U with DB paths.
    Only processes rows where synced_at IS NULL (this round's new songs). Matching: (1) file at local_path,
    (2) by name/artist hint, (3) by position in round (k-th row = k-th "new" file by mtime, first = first downloaded).
    Must run inside Flask app context. Returns (renamed_count, m3u_updated).
    """
    from datetime import datetime, timezone
    glconnect_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(glconnect_dir, "static", "ytauto")
    m3u_path = os.path.join(glconnect_dir, "ytauto.m3u")
    prefix_liq = "/liqfolder/glconnect/static/ytauto/"

    # Only process rows not yet synced (this round = only new songs since last sync)
    unsynced = DownloadedSong.query.filter(
        DownloadedSong.local_path.isnot(None),
        DownloadedSong.local_path != "",
        DownloadedSong.synced_at.is_(None),
    ).order_by(DownloadedSong.id).all()
    renamed_count = 0
    now = datetime.now(timezone.utc)
    used_filenames = set()
    synced_paths = set()
    for r in DownloadedSong.query.filter(DownloadedSong.synced_at.isnot(None)).filter(DownloadedSong.local_path.isnot(None)):
        p = (r.local_path or "").strip()
        if p:
            synced_paths.add(os.path.basename(p))
    round_files_by_position = _get_new_round_files_by_mtime(output_folder, len(unsynced), synced_paths) if unsynced else []
    for idx, row in enumerate(unsynced):
        name = (row.name or "").strip()
        artist = (row.artist or "").strip()
        if not name and not artist:
            continue
        current_path = (row.local_path or "").strip()
        if not current_path.startswith(prefix_liq):
            # Support paths that only have the filename part
            current_filename = os.path.basename(current_path) if "/" in current_path or "\\" in current_path else current_path
        else:
            current_filename = current_path[len(prefix_liq):].lstrip("/")
        current_file = os.path.join(output_folder, current_filename)
        if not os.path.isfile(current_file):
            # Fallback: find a file on disk that matches (artist, name) after you cleaned DB
            current_filename = _find_matching_file(output_folder, artist, name, used_filenames)
            if current_filename:
                current_file = os.path.join(output_folder, current_filename)
                used_filenames.add(current_filename)
                print(f"Matched (file not at DB path): {current_filename}")
            else:
                if idx < len(round_files_by_position):
                    current_filename = round_files_by_position[idx]
                    if current_filename not in used_filenames:
                        current_file = os.path.join(output_folder, current_filename)
                        used_filenames.add(current_filename)
                        print(f"Matched (position in round): {current_filename}")
                    else:
                        print(f"Skip (file not found): {current_file}")
                        continue
                else:
                    print(f"Skip (file not found): {current_file}")
                    continue
        used_filenames.add(current_filename)
        part_name = (_sanitize_filename(name) or "Unknown").replace(".mp3", "").strip() or "Unknown"
        part_artist = _sanitize_filename(artist) or "Unknown"
        # name = song name, artist = artist name; "by" precedes artist
        new_filename = f"{part_name}.mp3 by {part_artist}"
        new_file = os.path.join(output_folder, new_filename)
        new_local_path = f"{prefix_liq}{new_filename}"
        if os.path.normpath(current_file) == os.path.normpath(new_file):
            row.local_path = new_local_path
            row.synced_at = now
            db.session.add(row)
            continue
        if os.path.exists(new_file) and os.path.normpath(new_file) != os.path.normpath(current_file):
            print(f"Skip (target exists): {new_filename}")
            row.synced_at = now
            db.session.add(row)
            continue
        try:
            os.rename(current_file, new_file)
            row.local_path = new_local_path
            row.synced_at = now
            db.session.add(row)
            renamed_count += 1
            print(f"Renamed: {current_filename} -> {new_filename}")
        except OSError as e:
            print(f"Error renaming {current_filename}: {e}")
    db.session.commit()

    # Write full M3U from all rows (so playlist stays complete; only this round's files were renamed)
    all_rows = DownloadedSong.query.filter(
        DownloadedSong.local_path.isnot(None),
        DownloadedSong.local_path != "",
    ).order_by(DownloadedSong.id).all()
    with open(m3u_path, "w") as m3u_file:
        for row in all_rows:
            path = (row.local_path or "").strip()
            if path:
                m3u_file.write(path + "\n")
    print(f"M3U overwritten from DB: {m3u_path}")
    return renamed_count, True
