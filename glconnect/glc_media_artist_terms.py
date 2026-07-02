"""GLC Media creator submission terms — artists, podcasters, promotion playback license."""

from datetime import datetime, timezone
from typing import Any, Optional

GLC_MEDIA_ARTIST_TERMS_VERSION = "1.0"
GLC_MEDIA_TRACK_SUBMISSION_VERSION = "1.0"
GLC_MEDIA_PODCASTER_TERMS_VERSION = "1.0"
GLC_MEDIA_PODCAST_SUBMISSION_VERSION = "1.0"


def _as_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def artist_has_glc_media_terms(artist: Any) -> bool:
    if not artist:
        return False
    version = getattr(artist, "glc_media_terms_version", None)
    accepted_at = getattr(artist, "glc_media_terms_accepted_at", None)
    return version == GLC_MEDIA_ARTIST_TERMS_VERSION and accepted_at is not None


def validate_glc_media_artist_terms(payload: Any) -> Optional[str]:
    """Validate artist-level GLC Media agreement checkboxes."""
    if payload is None:
        payload = {}
    if not _as_bool(payload.get("glc_media_terms_accept")):
        return "Please accept the GLC Media Artist Agreement."
    if not _as_bool(payload.get("glc_media_rights_warranty")):
        return "Please confirm you own or control all rights in music you submit."
    if not _as_bool(payload.get("glc_media_play_license")):
        return (
            "Please grant permission for GLC Media to play and promote your music "
            "until you withdraw in writing."
        )
    if not _as_bool(payload.get("glc_media_liability_waiver")):
        return "Please accept the copyright liability waiver and indemnification terms."
    return None


def validate_glc_media_track_submission_terms(payload: Any) -> Optional[str]:
    """Validate per-track submission attestation checkboxes."""
    if payload is None:
        payload = {}
    if not _as_bool(payload.get("glc_media_track_rights_confirm")):
        return "Please confirm you have rights to submit this track for GLC Media promotion."
    if not _as_bool(payload.get("glc_media_track_play_license")):
        return (
            "Please authorize GLC Media to play and promote this track "
            "until you withdraw in writing."
        )
    if not _as_bool(payload.get("glc_media_track_liability_waiver")):
        return "Please accept liability waiver for this track submission."
    return None


def user_has_glc_media_podcaster_terms(user: Any) -> bool:
    if not user:
        return False
    version = getattr(user, "glc_media_podcaster_terms_version", None)
    accepted_at = getattr(user, "glc_media_podcaster_terms_accepted_at", None)
    return version == GLC_MEDIA_PODCASTER_TERMS_VERSION and accepted_at is not None


def validate_glc_media_podcaster_terms(payload: Any) -> Optional[str]:
    """Validate podcaster-level GLC Media agreement checkboxes."""
    if payload is None:
        payload = {}
    if not _as_bool(payload.get("glc_media_terms_accept")):
        return "Please accept the GLC Media Podcaster Agreement."
    if not _as_bool(payload.get("glc_media_rights_warranty")):
        return "Please confirm you own or control all rights in podcast content you submit."
    if not _as_bool(payload.get("glc_media_play_license")):
        return (
            "Please grant permission for GLC Media to play and promote your podcasts "
            "until you withdraw in writing."
        )
    if not _as_bool(payload.get("glc_media_liability_waiver")):
        return "Please accept the copyright liability waiver and indemnification terms."
    return None


def validate_glc_media_podcast_submission_terms(payload: Any) -> Optional[str]:
    """Validate per-episode podcast submission attestation checkboxes."""
    if payload is None:
        payload = {}
    if not _as_bool(payload.get("glc_media_episode_rights_confirm")):
        return "Please confirm you have rights to submit this episode for GLC Media promotion."
    if not _as_bool(payload.get("glc_media_episode_play_license")):
        return (
            "Please authorize GLC Media to play and promote this episode "
            "until you withdraw in writing."
        )
    if not _as_bool(payload.get("glc_media_episode_liability_waiver")):
        return "Please accept liability waiver for this episode submission."
    return None


def record_user_glc_media_podcaster_terms(user: Any) -> None:
    user.glc_media_podcaster_terms_version = GLC_MEDIA_PODCASTER_TERMS_VERSION
    user.glc_media_podcaster_terms_accepted_at = datetime.now(timezone.utc)


def record_podcast_glc_media_submission(podcast: Any) -> None:
    podcast.glc_media_submission_version = GLC_MEDIA_PODCAST_SUBMISSION_VERSION
    podcast.glc_media_submission_accepted_at = datetime.now(timezone.utc)


def ensure_podcaster_glc_media_terms(user: Any, payload: Any) -> Optional[str]:
    """Record podcaster agreement on first upload if not yet accepted."""
    if user_has_glc_media_podcaster_terms(user):
        return None
    err = validate_glc_media_podcaster_terms(payload)
    if err:
        return err
    record_user_glc_media_podcaster_terms(user)
    return None


def record_artist_glc_media_terms(artist: Any) -> None:
    artist.glc_media_terms_version = GLC_MEDIA_ARTIST_TERMS_VERSION
    artist.glc_media_terms_accepted_at = datetime.now(timezone.utc)


def record_track_glc_media_submission(song: Any, song_upload: Any = None) -> None:
    now = datetime.now(timezone.utc)
    song.glc_media_submission_version = GLC_MEDIA_TRACK_SUBMISSION_VERSION
    song.glc_media_submission_accepted_at = now
    if song_upload is not None:
        song_upload.glc_media_submission_version = GLC_MEDIA_TRACK_SUBMISSION_VERSION
        song_upload.glc_media_submission_accepted_at = now


def glc_media_terms_context() -> dict:
    return {
        "glc_media_artist_terms_version": GLC_MEDIA_ARTIST_TERMS_VERSION,
        "glc_media_track_submission_version": GLC_MEDIA_TRACK_SUBMISSION_VERSION,
        "glc_media_podcaster_terms_version": GLC_MEDIA_PODCASTER_TERMS_VERSION,
        "glc_media_podcast_submission_version": GLC_MEDIA_PODCAST_SUBMISSION_VERSION,
    }
