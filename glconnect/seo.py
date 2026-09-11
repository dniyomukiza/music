"""Public SEO helpers: robots.txt and sitemap.xml for search engines."""

from __future__ import annotations

from datetime import datetime, timezone
from xml.sax.saxutils import escape

# Crawl budget: app areas that require login or are not marketing content.
_ROBOTS_DISALLOW_PREFIXES = (
    "/mybook/",
    "/routes1/",
    "/routes2/",
    "/music/",
    "/writer/",
    "/prof/",
    "/playlist2/",
    "/art/",
    "/book/",
    "/api/",
    "/static/",
    "/hls/",
    "/_analytics",
    "/analytics",
    "/health",
    "/marketplace",
    "/blog/blogpost",
    "/blog/update",
    "/blog/delete",
)


def site_base_url() -> str:
    from flask import current_app, request

    base = (current_app.config.get("FRONTEND_BASE_URL") or "").strip().rstrip("/")
    if base:
        return base
    return request.url_root.rstrip("/")


def build_robots_txt() -> str:
    base = site_base_url()
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
    ]
    for prefix in _ROBOTS_DISALLOW_PREFIXES:
        lines.append(f"Disallow: {prefix}")
    lines.extend(
        [
            "",
            f"Sitemap: {base}/sitemap.xml",
        ]
    )
    return "\n".join(lines) + "\n"


def _sitemap_url(loc: str, lastmod: str | None, changefreq: str | None, priority: str | None) -> str:
    parts = ["  <url>", f"    <loc>{escape(loc)}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{escape(lastmod)}</lastmod>")
    if changefreq:
        parts.append(f"    <changefreq>{escape(changefreq)}</changefreq>")
    if priority:
        parts.append(f"    <priority>{escape(priority)}</priority>")
    parts.append("  </url>")
    return "\n".join(parts)


def build_sitemap_xml(*, policy_keys) -> str:
    """Build sitemap for anonymous, indexable pages only."""
    base = site_base_url()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entries: list[tuple[str, str | None, str | None, str | None]] = [
        (f"{base}/", today, "weekly", "1.0"),
        (f"{base}/policies", today, "monthly", "0.7"),
        (f"{base}/careers", today, "monthly", "0.6"),
        (f"{base}/careers/apply", today, "monthly", "0.5"),
        (f"{base}/pitch-deck", today, "monthly", "0.5"),
        (f"{base}/platform", today, "monthly", "0.4"),
        (f"{base}/blog/blogs", today, "daily", "0.7"),
        (f"{base}/blog/contact", today, "yearly", "0.4"),
    ]

    for key in sorted(policy_keys):
        entries.append((f"{base}/policies/{key}", today, "monthly", "0.6"))

    try:
        from glconnect.models import Post, db

        rows = (
            db.session.query(Post.id, Post.date_posted)
            .order_by(Post.date_posted.desc())
            .limit(2000)
            .all()
        )
        for post_id, posted in rows:
            lastmod = posted.strftime("%Y-%m-%d") if posted else today
            entries.append((f"{base}/blog/post/{post_id}", lastmod, "weekly", "0.6"))
    except Exception:
        pass

    body = "\n".join(_sitemap_url(*entry) for entry in entries)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )
