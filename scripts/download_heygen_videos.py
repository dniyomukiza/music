#!/usr/bin/env python3
"""Download all completed HeyGen videos from a selected local date.

Uses the HeyGen v3 REST API directly. HEYGEN_API_KEY is loaded from the
repository .env file when available.

Examples:
    python3 scripts/download_heygen_videos.py
    python3 scripts/download_heygen_videos.py --dry-run
    python3 scripts/download_heygen_videos.py --date 2026-08-20
    python3 scripts/download_heygen_videos.py --timezone America/Los_Angeles
    python3 scripts/download_heygen_videos.py --asset captioned
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "video" / "heygen_downloads"
HEYGEN_API_BASE = "https://api.heygen.com"
COMPLETED_STATUSES = {"completed", "complete", "success", "succeeded"}


class HeyGenApiError(RuntimeError):
    """Raised when the HeyGen API returns an unusable response."""


def make_session(api_key: str) -> requests.Session:
    retry = Retry(
        total=5,
        connect=3,
        read=3,
        status=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET",)),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update(
        {
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "gro-news-heygen-downloader/1.0",
        }
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def response_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        return json.dumps(payload, ensure_ascii=False)[:1200]
    except ValueError:
        return response.text[:1200]


def api_get(
    session: requests.Session,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = session.get(
        f"{HEYGEN_API_BASE}{path}",
        params=params,
        timeout=(15, 90),
    )
    if not response.ok:
        raise HeyGenApiError(
            f"GET {path} failed ({response.status_code}): {response_error(response)}"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise HeyGenApiError(f"GET {path} returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HeyGenApiError(f"GET {path} returned an unexpected response")
    return payload


def list_all_videos(
    session: requests.Session,
    *,
    max_pages: int,
) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    token: str | None = None

    for _ in range(max_pages):
        params: dict[str, Any] = {"limit": 100}
        if token:
            params["token"] = token
        payload = api_get(session, "/v3/videos", params=params)
        data = payload.get("data") or []
        if not isinstance(data, list):
            raise HeyGenApiError("GET /v3/videos returned non-list data")

        for item in data:
            if not isinstance(item, dict):
                continue
            video_id = get_video_id(item)
            if video_id and video_id not in seen_ids:
                seen_ids.add(video_id)
                videos.append(item)

        has_more = bool(payload.get("has_more"))
        next_token = payload.get("next_token")
        if not has_more:
            return videos
        if not next_token or str(next_token) == token:
            raise HeyGenApiError("Video pagination did not provide a new next_token")
        token = str(next_token)

    raise HeyGenApiError(
        f"Stopped after {max_pages} pages; increase --max-pages to scan more videos"
    )


def get_video(session: requests.Session, video_id: str) -> dict[str, Any]:
    payload = api_get(session, f"/v3/videos/{video_id}")
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise HeyGenApiError(f"Video {video_id} returned no resource data")
    return data


def parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return datetime.fromtimestamp(float(text), tz=timezone.utc)
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def record_datetime(record: dict[str, Any], basis: str) -> datetime | None:
    keys = (
        ("completed_at", "created_at")
        if basis == "completed"
        else ("created_at", "completed_at")
    )
    for key in keys:
        parsed = parse_timestamp(record.get(key))
        if parsed:
            return parsed
    return None


def get_video_id(record: dict[str, Any]) -> str | None:
    value = record.get("id") or record.get("video_id")
    return str(value).strip() if value else None


def is_completed(record: dict[str, Any]) -> bool:
    return str(record.get("status") or "").strip().lower() in COMPLETED_STATUSES


def safe_filename(title: str, video_id: str, suffix: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title.strip()).strip("._-")
    if not stem:
        stem = "heygen_video"
    return f"{stem[:100]}_{video_id[:12]}{suffix}.mp4"


def download_url(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    overwrite: bool,
) -> str:
    if destination.exists() and not overwrite:
        return f"SKIP exists: {destination}"

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(f"{destination.suffix}.part")
    try:
        with session.get(
            url,
            stream=True,
            timeout=(15, 300),
            headers={"Accept": "video/mp4,application/octet-stream,*/*"},
        ) as response:
            response.raise_for_status()
            with partial.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)
        if not partial.is_file() or partial.stat().st_size == 0:
            raise HeyGenApiError(f"Downloaded file for {destination.name} is empty")
        partial.replace(destination)
    finally:
        if partial.exists():
            partial.unlink()
    return f"DOWNLOADED: {destination}"


def local_timezone(name: str | None):
    if not name:
        return datetime.now().astimezone().tzinfo
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {name}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download completed HeyGen videos from a selected date using the v3 API",
    )
    parser.add_argument(
        "--date",
        default="today",
        help="Local date to download (YYYY-MM-DD; default: today)",
    )
    parser.add_argument(
        "--timezone",
        help="IANA timezone for date filtering, e.g. America/Los_Angeles",
    )
    parser.add_argument(
        "--basis",
        choices=("created", "completed"),
        default="created",
        help="Filter by creation or completion date (default: created)",
    )
    parser.add_argument(
        "--asset",
        choices=("video", "captioned"),
        default="video",
        help="Download original or captioned MP4 (default: video)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Destination directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=100,
        help="Maximum 100-video API pages to scan (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List matching videos without downloading",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace files that already exist",
    )
    return parser


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = build_parser().parse_args()
    api_key = (os.getenv("HEYGEN_API_KEY") or "").strip()
    if not api_key:
        print("ERROR: HEYGEN_API_KEY is missing from .env.", file=sys.stderr)
        return 2
    if args.max_pages < 1:
        print("ERROR: --max-pages must be at least 1.", file=sys.stderr)
        return 2

    try:
        tz = local_timezone(args.timezone)
        selected_date = (
            datetime.now(tz).date()
            if args.date.lower() == "today"
            else date.fromisoformat(args.date)
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    session = make_session(api_key)
    try:
        all_videos = list_all_videos(session, max_pages=args.max_pages)
        matching_summaries = []
        unfinished = 0
        undated = 0
        for video in all_videos:
            timestamp = record_datetime(video, args.basis)
            if not timestamp:
                undated += 1
                continue
            if timestamp.astimezone(tz).date() != selected_date:
                continue
            if not is_completed(video):
                unfinished += 1
                continue
            matching_summaries.append(video)

        matching_summaries.sort(
            key=lambda item: record_datetime(item, args.basis)
            or datetime.min.replace(tzinfo=timezone.utc)
        )

        timezone_label = args.timezone or str(tz)
        print(
            f"Found {len(matching_summaries)} completed HeyGen video(s) "
            f"{args.basis} on {selected_date} ({timezone_label})."
        )

        failures = 0
        output_dir = args.output_dir.expanduser().resolve()
        for summary in matching_summaries:
            video_id = get_video_id(summary)
            if not video_id:
                continue
            try:
                # Refresh details so the pre-signed download URL is current.
                video = get_video(session, video_id)
                url_field = (
                    "captioned_video_url" if args.asset == "captioned" else "video_url"
                )
                url = str(video.get(url_field) or "").strip()
                title = str(video.get("title") or summary.get("title") or "heygen_video")
                suffix = "_captioned" if args.asset == "captioned" else ""
                destination = output_dir / safe_filename(title, video_id, suffix)
                if args.dry_run:
                    print(
                        f"WOULD DOWNLOAD: {title!r} ({video_id}) -> {destination}"
                    )
                    continue
                if not url:
                    raise HeyGenApiError(
                        f"Completed video {video_id} has no {url_field}"
                    )
                print(
                    download_url(
                        session,
                        url,
                        destination,
                        overwrite=args.overwrite,
                    )
                )
            except (HeyGenApiError, requests.RequestException) as exc:
                failures += 1
                print(f"FAILED: {video_id}: {exc}", file=sys.stderr)

        if unfinished:
            print(f"Skipped {unfinished} matching unfinished/failed video(s).")
        if undated:
            print(f"Skipped {undated} video(s) without a usable timestamp.")
        return 1 if failures else 0
    except (HeyGenApiError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
