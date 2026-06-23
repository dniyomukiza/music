"""
Rich media rules and sanitization for Ink Studio project descriptions.

Authors can embed images, audio clips, video files, and YouTube/Vimeo links
using predetermined formats and size limits.
"""

from __future__ import annotations

import os
import re
import uuid
from io import BytesIO
from urllib.parse import parse_qs, urlparse

import bleach

# --- Upload limits (documented in the editor UI) ---
PROJECT_IMAGE_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "webp"})
PROJECT_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
PROJECT_IMAGE_MAX_WIDTH = 1920
PROJECT_IMAGE_MAX_HEIGHT = 1080
PROJECT_IMAGE_DISPLAY_MAX_WIDTH = 960

PROJECT_AUDIO_EXTENSIONS = frozenset({"mp3", "m4a", "ogg", "wav"})
PROJECT_AUDIO_MAX_BYTES = 15 * 1024 * 1024  # 15 MB

PROJECT_VIDEO_EXTENSIONS = frozenset({"mp4", "webm"})
PROJECT_VIDEO_MAX_BYTES = 100 * 1024 * 1024  # 100 MB

PROJECT_DESCRIPTION_MAX_CHARS = 50000
PROJECT_DESCRIPTION_MIN_PLAIN_CHARS = 50

EMBED_VIDEO_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "vimeo.com",
        "www.vimeo.com",
        "player.vimeo.com",
    }
)

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "h2",
    "h3",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "audio",
    "video",
    "source",
    "iframe",
    "figure",
    "figcaption",
    "div",
    "span",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "width", "height", "class", "loading"],
    "audio": ["src", "controls", "class", "preload"],
    "video": ["src", "controls", "class", "preload", "poster", "width", "height"],
    "source": ["src", "type"],
    "iframe": ["src", "width", "height", "class", "title", "allow", "allowfullscreen", "frameborder"],
    "div": ["class"],
    "span": ["class"],
    "figure": ["class"],
    "figcaption": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

PROJECT_MEDIA_STATIC_PREFIX = "/static/project_media/"

MEDIA_GUIDE = {
    "images": f"JPEG, PNG, or WebP, max 5 MB, up to {PROJECT_IMAGE_MAX_WIDTH}×{PROJECT_IMAGE_MAX_HEIGHT}px "
    f"(displayed at {PROJECT_IMAGE_DISPLAY_MAX_WIDTH}px wide)",
    "audio": "MP3, M4A, OGG, or WAV, max 15 MB",
    "video_files": "MP4 or WebM, max 100 MB",
    "video_embeds": "YouTube or Vimeo page links (we embed the official player)",
    "links": "Standard https:// links open in a new tab",
}


class ProjectDescriptionError(ValueError):
    """Raised when project description content fails validation."""


def get_project_media_upload_folder(app_root: str) -> str:
    folder = os.path.join(app_root, "static", "project_media")
    os.makedirs(folder, exist_ok=True)
    return folder


def allowed_project_image_file(filename: str) -> bool:
    return _extension(filename) in PROJECT_IMAGE_EXTENSIONS


def allowed_project_audio_file(filename: str) -> bool:
    return _extension(filename) in PROJECT_AUDIO_EXTENSIONS


def allowed_project_video_file(filename: str) -> bool:
    return _extension(filename) in PROJECT_VIDEO_EXTENSIONS


def project_media_public_path(book_id: int, filename: str) -> str:
    return f"{PROJECT_MEDIA_STATIC_PREFIX}{book_id}_{filename}"


def project_description_plain_text(html: str | None) -> str:
    if not html:
        return ""
    text = bleach.clean(html, tags=[], strip=True)
    return re.sub(r"\s+", " ", text).strip()


def project_description_plain_length(html: str | None) -> int:
    return len(project_description_plain_text(html))


def normalize_video_embed_url(url: str | None) -> str | None:
    """Return a safe iframe embed URL for YouTube/Vimeo, or None."""
    url = (url or "").strip()
    if not url:
        return None

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    if not _is_allowed_embed_host(parsed.netloc):
        return None

    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    if "youtube.com" in parsed.netloc:
        if parsed.path == "/watch":
            video_id = (parse_qs(parsed.query).get("v") or [None])[0]
            if video_id:
                return f"https://www.youtube.com/embed/{video_id}"
        match = re.match(r"^/(embed|shorts)/([^/?#]+)", parsed.path)
        if match:
            return f"https://www.youtube.com/embed/{match.group(2)}"

    if "vimeo.com" in parsed.netloc:
        match = re.match(r"^/(?:video/)?(\d+)", parsed.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"

    return None


def build_video_iframe_html(embed_url: str) -> str:
    return (
        f'<div class="ink-project-embed ink-project-embed--video">'
        f'<iframe src="{embed_url}" title="Project video" width="560" height="315" '
        f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        f'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
    )


def build_audio_html(public_url: str) -> str:
    return (
        f'<div class="ink-project-media ink-project-media--audio">'
        f'<audio controls preload="metadata" src="{public_url}"></audio></div>'
    )


def build_video_html(public_url: str) -> str:
    return (
        f'<div class="ink-project-media ink-project-media--video">'
        f'<video controls preload="metadata" src="{public_url}"></video></div>'
    )


def build_image_html(public_url: str, alt: str = "Project image") -> str:
    safe_alt = bleach.clean(alt or "Project image", tags=[], strip=True)[:200]
    return (
        f'<figure class="ink-project-media ink-project-media--image">'
        f'<img src="{public_url}" alt="{safe_alt}" loading="lazy" '
        f'class="ink-project-media__img"></figure>'
    )


def sanitize_project_description(html: str | None, *, book_id: int | None = None) -> str:
    if not html:
        return ""

    if len(html) > PROJECT_DESCRIPTION_MAX_CHARS:
        raise ProjectDescriptionError(
            f"Description is too large (max {PROJECT_DESCRIPTION_MAX_CHARS:,} characters)."
        )

    cleaned = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    cleaned = _normalize_links(cleaned)
    cleaned = _enforce_media_sources(cleaned, book_id=book_id)
    cleaned = _normalize_embedded_video(cleaned)

    if len(cleaned) > PROJECT_DESCRIPTION_MAX_CHARS:
        raise ProjectDescriptionError(
            f"Description is too large (max {PROJECT_DESCRIPTION_MAX_CHARS:,} characters)."
        )
    return cleaned


def save_project_image(file_storage, *, book_id: int, app_root: str) -> tuple[str, str]:
    """Resize if needed, save image, return (public_url, filename)."""
    if not allowed_project_image_file(file_storage.filename):
        raise ProjectDescriptionError(
            "Invalid image type. Use JPEG, PNG, or WebP (max 5 MB)."
        )

    raw = file_storage.read()
    if len(raw) > PROJECT_IMAGE_MAX_BYTES:
        raise ProjectDescriptionError("Image is too large. Maximum size is 5 MB.")

    ext = _extension(file_storage.filename) or "jpg"
    if ext == "jpeg":
        ext = "jpg"

    try:
        from PIL import Image

        image = Image.open(BytesIO(raw))
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")
        elif image.mode == "RGBA" and ext in ("jpg", "jpeg"):
            image = image.convert("RGB")

        width, height = image.size
        if width > PROJECT_IMAGE_MAX_WIDTH or height > PROJECT_IMAGE_MAX_HEIGHT:
            image.thumbnail((PROJECT_IMAGE_MAX_WIDTH, PROJECT_IMAGE_MAX_HEIGHT), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        save_format = "JPEG" if ext in ("jpg", "jpeg") else ext.upper()
        if save_format == "JPG":
            save_format = "JPEG"
        image.save(buffer, format=save_format, optimize=True, quality=85)
        raw = buffer.getvalue()
        if len(raw) > PROJECT_IMAGE_MAX_BYTES:
            raise ProjectDescriptionError(
                "Image is too large after processing. Try a smaller file."
            )
    except ProjectDescriptionError:
        raise
    except Exception:
        # Fall back to storing the original bytes when Pillow cannot parse the file.
        pass

    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    folder = get_project_media_upload_folder(app_root)
    disk_name = f"{book_id}_{filename}"
    with open(os.path.join(folder, disk_name), "wb") as handle:
        handle.write(raw)

    public_url = project_media_public_path(book_id, filename)
    return public_url, filename


def save_project_media_file(
    file_storage,
    *,
    book_id: int,
    app_root: str,
    media_type: str,
) -> tuple[str, str]:
    media_type = (media_type or "image").strip().lower()
    if media_type == "image":
        return save_project_image(file_storage, book_id=book_id, app_root=app_root)

    if media_type == "audio":
        allowed = allowed_project_audio_file
        max_bytes = PROJECT_AUDIO_MAX_BYTES
        label = "audio"
        exts = ", ".join(sorted(PROJECT_AUDIO_EXTENSIONS))
    elif media_type == "video":
        allowed = allowed_project_video_file
        max_bytes = PROJECT_VIDEO_MAX_BYTES
        label = "video"
        exts = ", ".join(sorted(PROJECT_VIDEO_EXTENSIONS))
    else:
        raise ProjectDescriptionError("Unsupported media type.")

    if not allowed(file_storage.filename):
        raise ProjectDescriptionError(f"Invalid {label} type. Allowed: {exts}.")

    raw = file_storage.read()
    if len(raw) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise ProjectDescriptionError(f"{label.title()} file is too large (max {limit_mb} MB).")

    ext = _extension(file_storage.filename)
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    folder = get_project_media_upload_folder(app_root)
    disk_name = f"{book_id}_{filename}"
    with open(os.path.join(folder, disk_name), "wb") as handle:
        handle.write(raw)

    return project_media_public_path(book_id, filename), filename


def ckeditor_upload_response(*, url: str | None = None, filename: str | None = None, error: str | None = None):
    from flask import jsonify

    if error:
        return jsonify({"uploaded": 0, "error": {"message": error}}), 400
    return jsonify({"uploaded": 1, "fileName": filename or "", "url": url or ""})


def _extension(filename: str | None) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def _is_allowed_embed_host(netloc: str) -> bool:
    netloc = (netloc or "").lower()
    if netloc in EMBED_VIDEO_HOSTS:
        return True
    return netloc.endswith(".youtube.com") or netloc.endswith(".vimeo.com")


def _normalize_links(html: str) -> str:
    return re.sub(
        r'(<a\b[^>]*\bhref="[^"]+"[^>]*)(>)',
        lambda match: (
            match.group(1)
            + (' target="_blank"' if 'target=' not in match.group(1).lower() else "")
            + (' rel="noopener noreferrer"' if 'rel=' not in match.group(1).lower() else "")
            + match.group(2)
        ),
        html,
        flags=re.IGNORECASE,
    )


def _allowed_project_src(src: str, *, book_id: int | None) -> bool:
    if not src.startswith(PROJECT_MEDIA_STATIC_PREFIX):
        return False
    basename = src[len(PROJECT_MEDIA_STATIC_PREFIX) :]
    if book_id is not None:
        return basename.startswith(f"{book_id}_")
    return bool(re.match(r"^\d+_", basename))


def _enforce_media_sources(html: str, *, book_id: int | None) -> str:
    for tag in ("img", "audio", "video", "source"):
        html = re.sub(
            rf'<{tag}\b([^>]*)\bsrc="([^"]*)"([^>]*)>',
            lambda match: (
                match.group(0)
                if _allowed_project_src(match.group(2), book_id=book_id)
                else ""
            ),
            html,
            flags=re.IGNORECASE,
        )
    return html


def _normalize_embedded_video(html: str) -> str:
    def repl(match):
        src = match.group(1)
        embed = normalize_video_embed_url(src)
        if not embed:
            return ""
        return (
            f'<div class="ink-project-embed ink-project-embed--video">'
            f'<iframe src="{embed}" title="Project video" width="560" height="315" '
            f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
            f'gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
        )

    return re.sub(
        r'<iframe\b[^>]*\bsrc="([^"]+)"[^>]*>\s*</iframe>',
        repl,
        html,
        flags=re.IGNORECASE,
    )
