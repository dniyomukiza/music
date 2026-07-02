import os
import json
from flask import Flask, has_app_context
from subprocess import run
from dotenv import load_dotenv
try:
    from glconnect.models import db, Song, DownloadedSong, DownloadedVideo
except ImportError:
    from models import db, Song, DownloadedSong, DownloadedVideo

# Load configuration from environment variables
config = {
    "DB_URL": (os.getenv("DB_URL") or os.getenv("DATABASE_URL") or "").strip()
}
if not config["DB_URL"]:
    raise RuntimeError("DB_URL or DATABASE_URL is required.")
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.get('DB_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
_jwt_secret_key = (os.getenv("JWT_SECRET_KEY") or "").strip()
if not _jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY is required.")
app.config["JWT_SECRET_KEY"] = _jwt_secret_key
db.init_app(app)

# Connect to existing database (don't create tables)
# with app.app_context():
#     db.create_all()

# Path to your output folder for music files
output_folder = os.path.join(os.getcwd(), "glconnect/static/ytauto")

# TV program MP4s: glconnect/static/ytautovid/ → /liqfolder/glconnect/static/ytautovid/ in videolist.m3u
# Bumpers stay under video/ and tv_jingles.m3u only.
TV_PROGRAM_LIQ_PREFIX = "/liqfolder/glconnect/static/ytautovid/"
LEGACY_TV_PROGRAM_VIDEO_PREFIX = "/liqfolder/video/"

_TV_JINGLE_BASENAMES_LOWER = frozenset(
    ("tvjingle.mp4", "tvjingle2.mp4", "grojingle.mp4")
)


def tv_ytautovid_dir(glconnect_dir):
    """Filesystem dir for TV program MP4s (created if missing)."""
    d = os.path.join(glconnect_dir, "static", "ytautovid")
    os.makedirs(d, exist_ok=True)
    return d


def _is_tv_jingle_basename(path_or_name: str) -> bool:
    if not path_or_name:
        return False
    bn = os.path.basename(path_or_name.replace("\\", "/")).lower()
    return bn in _TV_JINGLE_BASENAMES_LOWER


def _migrate_program_mp4_to_ytautovid(glconnect_dir, video_dir, filename):
    """Move a non-jingle MP4 from legacy video/ into static/ytautovid/."""
    if _is_tv_jingle_basename(filename):
        return None
    yt_root = tv_ytautovid_dir(glconnect_dir)
    src = os.path.join(video_dir, filename)
    dst = os.path.join(yt_root, filename)
    if not os.path.isfile(src):
        return None
    if os.path.isfile(dst):
        try:
            os.remove(src)
        except OSError as exc:
            print(f"TV migrate: could not remove duplicate {src}: {exc}")
        return TV_PROGRAM_LIQ_PREFIX + filename
    import shutil

    shutil.move(src, dst)
    print(f"TV migrate: {filename} -> static/ytautovid/")
    return TV_PROGRAM_LIQ_PREFIX + filename


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


class VideoDownloader:
    """YouTube → merged MP4 (H.264/AAC-friendly) for TV / Liquidsoap HLS."""

    def __init__(self, playlist_url=None, output_folder=None):
        self.playlist_url = playlist_url.strip() if playlist_url else None
        self.output_folder = os.path.expanduser(output_folder) if output_folder else os.getcwd()

    def prepare_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def download_video(self):
        if not self.playlist_url:
            raise ValueError("No playlist URL provided for downloading.")
        import shutil
        ytdlp_path = shutil.which("yt-dlp")
        if not ytdlp_path:
            raise FileNotFoundError(
                "yt-dlp is not installed or not in PATH. Install it (e.g. pip install yt-dlp or brew install yt-dlp) and try again."
            )
        self.prepare_output_folder()
        print(f"Downloading TV video to folder: {self.output_folder}")
        command = [
            ytdlp_path,
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "--yes-playlist",
            "--extractor-args",
            "youtube:player_client=android,web",
            "--js-runtimes",
            "node",
            "--remote-components",
            "ejs:github",
            "-o",
            os.path.join(self.output_folder, "%(title)s.%(ext)s"),
        ]
        cookies_file = os.environ.get("YTDLP_COOKIES_FILE")
        if cookies_file and os.path.isfile(cookies_file):
            command.extend(["--cookies", cookies_file])
            print(f"Using cookies file: {cookies_file}")
        elif cookies_file:
            print(f"YTDLP_COOKIES_FILE is set but file not found: {cookies_file}")
        command.append(self.playlist_url)
        print(f"Running command: {' '.join(command)}")
        result = run(command, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip() or f"Exit code {result.returncode}"
            raise RuntimeError(f"yt-dlp failed: {err}")
        mp4s = [f for f in os.listdir(self.output_folder) if f.lower().endswith(".mp4")]
        if not mp4s:
            raise RuntimeError(
                "yt-dlp finished but no MP4 files were saved. Check the URL and that the video/playlist is available."
            )
        print(f"TV download completed successfully! {len(mp4s)} file(s) saved to: {self.output_folder}")

    def download_and_convert(self):
        self.download_video()


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

    @staticmethod
    def ingest_videos_from_folder(output_folder, source_url=None):
        """
        Scan folder for .mp4, add rows to downloaded_videos with Liquidsoap container paths.
        Returns (added_count, skipped_count).
        """
        if not has_app_context():
            with app.app_context():
                return PlaylistIngestion._do_ingest_videos_from_folder(output_folder, source_url)
        return PlaylistIngestion._do_ingest_videos_from_folder(output_folder, source_url)

    @staticmethod
    def _do_ingest_videos_from_folder(output_folder, source_url=None):
        """
        Align downloaded_videos with every *.mp4 on disk: insert new rows, or attach/update
        local_path when a row matched title parse but had no path / wrong file (manual copies,
        DB reset, renames). Skips only when this exact file is already catalogued.
        """
        prefix_liq = TV_PROGRAM_LIQ_PREFIX
        if not os.path.isdir(output_folder):
            print(f"TV output folder does not exist: {output_folder}")
            return 0, 0
        try:
            mp4_files = [f for f in os.listdir(output_folder) if f.lower().endswith(".mp4")]
        except OSError as exc:
            print(f"TV folder list failed {output_folder}: {exc}")
            return 0, 0
        added_count = 0
        updated_count = 0
        skipped_count = 0
        url_trim = (source_url or "").strip()[:500] or None

        by_basename = {}
        for row in DownloadedVideo.query.filter(
            DownloadedVideo.local_path.isnot(None),
            DownloadedVideo.local_path != "",
        ).all():
            lp = (row.local_path or "").strip().replace("\\", "/")
            bn = os.path.basename(lp)
            if bn.lower().endswith(".mp4"):
                by_basename.setdefault(bn, row)

        for filename in sorted(mp4_files, key=lambda x: x.lower()):
            if _is_tv_jingle_basename(filename):
                skipped_count += 1
                continue
            liq_path = prefix_liq + filename
            if filename in by_basename:
                row = by_basename[filename]
                if row.local_path != liq_path:
                    row.local_path = liq_path
                    if url_trim:
                        row.source_url = url_trim
                    updated_count += 1
                    print(f"Updated TV path: {filename}")
                else:
                    skipped_count += 1
                continue

            artist, title = _parse_video_title(filename)
            key_artist = (artist or "").strip() or None
            key_name = (title or "").strip() or "Unknown"
            twin = DownloadedVideo.query.filter_by(artist=key_artist, name=key_name).first()
            if twin:
                if twin.local_path != liq_path:
                    twin.local_path = liq_path
                    if url_trim:
                        twin.source_url = url_trim
                    updated_count += 1
                    print(f"Updated TV row (title match): {artist} - {title} -> {filename}")
                else:
                    skipped_count += 1
                by_basename[filename] = twin
                continue

            row = DownloadedVideo(
                name=key_name,
                artist=key_artist,
                local_path=liq_path,
                source_url=url_trim,
            )
            db.session.add(row)
            by_basename[filename] = row
            print(f"Added TV: {artist} - {title} -> {filename}")
            added_count += 1
        db.session.commit()
        print(
            f"TV folder ingestion: {added_count} new, {updated_count} path updates, {skipped_count} unchanged."
        )
        return added_count + updated_count, skipped_count


def _parse_artist_title(filename):
    """Return (artist, song_name) from filename like 'Artist - Song.mp3'. Normalize for dedupe."""
    name = os.path.basename(filename).replace(".mp3", "").strip()
    if " - " in name:
        artist, song_name = name.split(" - ", 1)
        return (artist.strip() or None, song_name.strip())
    return (None, name or None)


def _parse_video_title(filename):
    """Return (artist, title) from filename like 'Artist - Title.mp4'."""
    name = os.path.basename(filename)
    lower = name.lower()
    if lower.endswith(".mp4"):
        name = name[:-4]
    name = name.strip()
    if " - " in name:
        artist, title = name.split(" - ", 1)
        return (artist.strip() or None, title.strip())
    return (None, name or None)


def _tv_resolve_playable_liq_path(glconnect_dir, video_dir, local_path):
    """
    Return a playable program path under TV_PROGRAM_LIQ_PREFIX only.
    Legacy files under video/ are moved into static/ytautovid/ when found.
    """
    p = (local_path or "").strip().replace("\\", "/")
    if not p or _is_tv_jingle_basename(p):
        return None
    yt_root = tv_ytautovid_dir(glconnect_dir)
    bn = os.path.basename(p)
    if not bn.lower().endswith(".mp4"):
        return None

    dest = os.path.join(yt_root, bn)
    if os.path.isfile(dest):
        return TV_PROGRAM_LIQ_PREFIX + bn

    legacy = os.path.join(video_dir, bn)
    if os.path.isfile(legacy):
        return _migrate_program_mp4_to_ytautovid(glconnect_dir, video_dir, bn)

    return None


def sync_tv_videolist_from_db():
    """
    Rebuild video/videolist.m3u program lines as /liqfolder/glconnect/static/ytautovid/*.mp4
    from videolist_extra.m3u, downloaded_videos, disk under static/ytautovid/, and legacy video/
    (non-jingle MP4s moved into ytautovid/). Comments in the existing M3U are preserved.
    Must run inside Flask app context. Returns non-comment path count in final playlist.
    """
    glconnect_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(glconnect_dir)
    video_dir = os.path.join(project_root, "video")
    yt_root = tv_ytautovid_dir(glconnect_dir)
    extra_m3u = os.path.join(video_dir, "videolist_extra.m3u")
    out_m3u = os.path.join(video_dir, "videolist.m3u")
    comment_lines = []
    seen = set()
    program_paths = []

    if os.path.isfile(out_m3u):
        with open(out_m3u, "r", encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.rstrip("\n")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    comment_lines.append(line)
                    continue
                resolved = _tv_resolve_playable_liq_path(
                    glconnect_dir, video_dir, stripped
                )
                if resolved and resolved not in seen:
                    seen.add(resolved)
                    program_paths.append(resolved)

    def append_path(pp):
        pp = (pp or "").strip()
        if not pp or pp in seen or _is_tv_jingle_basename(pp):
            return
        resolved = _tv_resolve_playable_liq_path(glconnect_dir, video_dir, pp)
        if not resolved:
            return
        seen.add(resolved)
        program_paths.append(resolved)

    if os.path.isfile(extra_m3u):
        with open(extra_m3u, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if _is_tv_jingle_basename(line):
                        continue
                    append_path(line)
    rows = (
        DownloadedVideo.query.filter(
            DownloadedVideo.local_path.isnot(None),
            DownloadedVideo.local_path != "",
        )
        .order_by(DownloadedVideo.id)
        .all()
    )
    for row in rows:
        resolved = _tv_resolve_playable_liq_path(
            glconnect_dir, video_dir, (row.local_path or "").strip()
        )
        if resolved:
            append_path(resolved)
    # Orphan MP4s already in static/ytautovid/
    if os.path.isdir(yt_root):
        try:
            for fn in sorted(f for f in os.listdir(yt_root) if f.lower().endswith(".mp4")):
                append_path(TV_PROGRAM_LIQ_PREFIX + fn)
        except OSError as exc:
            print(f"TV sync: cannot list {yt_root}: {exc}")
    # Legacy program MP4s still sitting in video/ → move into ytautovid/
    if os.path.isdir(video_dir):
        try:
            for fn in sorted(f for f in os.listdir(video_dir) if f.lower().endswith(".mp4")):
                if _is_tv_jingle_basename(fn):
                    continue
                migrated = _migrate_program_mp4_to_ytautovid(glconnect_dir, video_dir, fn)
                if migrated:
                    append_path(migrated)
        except OSError as exc:
            print(f"TV sync: cannot list {video_dir}: {exc}")

    os.makedirs(video_dir, exist_ok=True)
    if not comment_lines:
        comment_lines = [
            "#EXTM3U",
            "# TV programs: /liqfolder/glconnect/static/ytautovid/*.mp4 (bumpers: tv_jingles.m3u only).",
        ]
    with open(out_m3u, "w", encoding="utf-8") as f:
        for line in comment_lines:
            f.write(line + "\n")
        for path in program_paths:
            f.write(path + "\n")

    print(
        f"TV videolist synced: {len(program_paths)} program path(s) under {TV_PROGRAM_LIQ_PREFIX} -> {out_m3u}"
    )
    _write_videolist_hls_m3u(video_dir, program_paths)
    return len(program_paths)


def _read_tv_jingle_paths(video_dir):
    """Absolute /liqfolder/... paths from video/tv_jingles.m3u (non-comment lines)."""
    jingle_m3u = os.path.join(video_dir, "tv_jingles.m3u")
    jingle_paths = []
    if not os.path.isfile(jingle_m3u):
        return jingle_paths
    with open(jingle_m3u, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                jingle_paths.append(line)
    return jingle_paths


def _interleave_jingles_two_programs(jingle_paths, program_paths):
    """
    Pattern: 1 bumper, 2 programs, repeat. If no jingles, returns program_paths only.
    If no programs but jingles exist, returns jingles only (edge case).
    """
    if not jingle_paths:
        return list(program_paths)
    if not program_paths:
        return list(jingle_paths)
    out = []
    j = 0
    nj = len(jingle_paths)
    i = 0
    nprog = len(program_paths)
    while i < nprog:
        out.append(jingle_paths[j % nj])
        j += 1
        out.append(program_paths[i])
        i += 1
        if i < nprog:
            out.append(program_paths[i])
            i += 1
    return out


def _write_videolist_hls_m3u(video_dir, program_paths):
    """
    Write video/videolist_hls.m3u for Liquidsoap HLS (scripts/video.liq).
    Interleaves tv_jingles.m3u entries as 1 bumper every 2 program tracks so a single
    playlist() is used, avoids rotate() never selecting the jingle branch for video.
    """
    out_hls = os.path.join(video_dir, "videolist_hls.m3u")
    jingle_paths = _read_tv_jingle_paths(video_dir)
    interleaved = _interleave_jingles_two_programs(jingle_paths, program_paths)
    os.makedirs(video_dir, exist_ok=True)
    with open(out_hls, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(
            "# Interleaved 1 bumper : 2 programs for Liquidsoap HLS. "
            "Regenerated when videolist sync runs (Admin TV or sync_tv_videolist_from_db). "
            "Edit tv_jingles.m3u + videolist sources, then sync, do not hand-edit paths here.\n"
        )
        for p in interleaved:
            f.write(p + "\n")
    print(f"TV HLS interleaved playlist: {len(interleaved)} paths -> {out_hls}")


def create_or_append_m3u_playlist(output_folder, m3u_filename):
    print(f"Preparing clean .m3u playlist in {output_folder}...")
    glconnect_dir = os.path.dirname(os.path.dirname(output_folder))
    project_root = os.path.dirname(glconnect_dir)
    m3u_path = os.path.join(project_root, m3u_filename)
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
    '{name}.mp3 by {artist}', update local_path in DB, and overwrite the M3U with DB paths.
    Only the NEW BATCH is touched: rows where synced_at IS NULL (this round's new songs).
    Existing songs (already synced) are never renamed or modified. M3U is rewritten from ALL rows
    (existing + new), so existing entries remain. Remove step only deletes files that lack " by "
    and are not referenced in any row's local_path (original or normalized). Matching for new batch:
    (1) file at local_path, (2) name/artist hint, (3) position in round.
    Must run inside Flask app context. Returns (renamed_count, m3u_updated).
    """
    from datetime import datetime, timezone
    glconnect_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(glconnect_dir)
    output_folder = os.path.join(glconnect_dir, "static", "ytauto")
    m3u_path = os.path.join(project_root, "ytauto.m3u")
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
            path = (row.local_path or "").strip().replace(" - ", " by ")
            if path:
                m3u_file.write(path + "\n")
    print(f"M3U overwritten from DB: {os.path.abspath(m3u_path)}")

    # Remove only files that (1) lack " by " and (2) are not referenced in DB (don't touch existing catalog)
    def _normalize_path(p):
        return (p or "").strip().replace(" - ", " by ")
    db_basenames = set()
    for r in all_rows:
        raw = (r.local_path or "").strip()
        if not raw:
            continue
        db_basenames.add(os.path.basename(raw))
        db_basenames.add(os.path.basename(_normalize_path(raw)))
    for fn in os.listdir(output_folder):
        if not fn.endswith(".mp3"):
            continue
        if " by " not in fn and fn not in db_basenames:
            path = os.path.join(output_folder, fn)
            try:
                os.remove(path)
                print(f"Removed (no ' by ', not in DB): {fn}")
            except OSError as e:
                print(f"Could not remove {fn}: {e}")

    return renamed_count, True


def sync_from_disk():
    """
    Fix discrepancies: use actual files on disk as source of truth.
    - Parses each .mp3 filename to extract name and artist
    - Updates downloaded_songs rows to match (local_path, name, artist)
    - Rewrites ytauto.m3u from actual files only (no orphan paths)
    Run inside Flask app context. Returns (updated_count, m3u_updated).
    """
    from datetime import datetime, timezone
    glconnect_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(glconnect_dir)
    output_folder = os.path.join(glconnect_dir, "static", "ytauto")
    m3u_path = os.path.join(project_root, "ytauto.m3u")
    prefix_liq = "/liqfolder/glconnect/static/ytauto/"

    if not os.path.isdir(output_folder):
        return 0, False

    # Collect all .mp3 files
    files_on_disk = sorted([f for f in os.listdir(output_folder) if f.lower().endswith(".mp3")])
    now = datetime.now(timezone.utc)
    updated_count = 0
    used_row_ids = set()

    for filename in files_on_disk:
        artist, title = _parse_filename_as_artist_title(filename)
        if title is None:
            continue
        name = title
        artist_str = artist or "Unknown"
        local_path = f"{prefix_liq}{filename}"

        # Find matching DB row: by basename in local_path, or by name+artist
        row = None
        for r in DownloadedSong.query.filter(
            DownloadedSong.local_path.isnot(None),
            DownloadedSong.local_path != "",
        ).all():
            if r.id in used_row_ids:
                continue
            bn = os.path.basename((r.local_path or "").strip())
            if bn == filename:
                row = r
                break
        if not row:
            anorm = _normalize_for_match(artist_str)
            nnorm = _normalize_for_match(name)
            for r in DownloadedSong.query.all():
                if r.id in used_row_ids:
                    continue
                r_anorm = _normalize_for_match(r.artist or "")
                r_nnorm = _normalize_for_match(r.name or "")
                if nnorm and r_nnorm and (nnorm == r_nnorm or nnorm in r_nnorm or r_nnorm in nnorm):
                    if not anorm or not r_anorm or anorm == r_anorm or anorm in r_anorm or r_anorm in anorm:
                        row = r
                        break

        if row:
            used_row_ids.add(row.id)
            changed = False
            if (row.local_path or "").strip() != local_path:
                row.local_path = local_path
                changed = True
            if (row.name or "").strip() != name:
                row.name = name
                changed = True
            if (row.artist or "").strip() != artist_str:
                row.artist = artist_str
                changed = True
            row.synced_at = now
            if changed:
                updated_count += 1
                print(f"Updated: {row.id} -> {filename} (name={name}, artist={artist_str})")
            db.session.add(row)

    db.session.commit()

    # Write M3U from actual files only (no DB orphans)
    with open(m3u_path, "w") as m3u_file:
        for filename in files_on_disk:
            m3u_file.write(f"{prefix_liq}{filename}\n")
    print(f"M3U rewritten from disk: {len(files_on_disk)} entries -> {os.path.abspath(m3u_path)}")

    return updated_count, True
