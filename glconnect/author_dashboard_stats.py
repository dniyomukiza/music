"""
Author dashboard aggregates: sales, earnings, pricing, and reader engagement.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import func

from glconnect.book_platform_models import (
    BookAnalytics,
    BookProject,
    BookSale,
    TransactionStatus,
)
from glconnect.book_utils import is_book_published
from glconnect.book_purchase_format import print_listed, print_shipping_amount
from glconnect.platform_fee_policy import MARKETPLACE_PLATFORM_FEE_PERCENT


def _sale_transparency_row(sale: BookSale, title_by_id: Dict[int, str]) -> Dict[str, Any]:
    """Per-sale breakdown for author transparency (gross, platform fee, net)."""
    net = round(float(sale.net_amount or 0), 2)
    platform_fee = round(float(sale.platform_fee or 0), 2)
    gross = round(net + platform_fee, 2)
    when = sale.paid_at or sale.created_at
    fee_pct = (
        round(platform_fee / gross * 100, 1)
        if gross > 0
        else MARKETPLACE_PLATFORM_FEE_PERCENT
    )
    return {
        "sale_id": sale.id,
        "book_id": sale.book_project_id,
        "book_title": title_by_id.get(sale.book_project_id, "Book"),
        "format": getattr(sale, "sale_format", None) or "digital",
        "gross_amount": gross,
        "platform_fee": platform_fee,
        "platform_fee_percent": fee_pct,
        "net_amount": net,
        "tax_amount": None,
        "at": when.isoformat() if when else None,
        "at_label": when.strftime("%b %d, %Y") if when else "",
    }


def _fmt_price(val: Optional[float]) -> str:
    if val is None or val <= 0:
        return "Free"
    return f"${val:.2f}"


def build_author_dashboard_stats(author_id: int) -> Dict[str, Any]:
    """Sales, downloads, views, earnings, and per-book pricing for one author."""
    from glconnect import db

    books_q = (
        BookProject.query.filter_by(author_id=author_id)
        .order_by(BookProject.updated_at.desc(), BookProject.created_at.desc())
        .all()
    )
    book_ids = [b.id for b in books_q]

    sale_by_book: Dict[int, Dict[str, Any]] = {}
    if book_ids:
        for row in db.session.query(
            BookSale.book_project_id,
            func.count(BookSale.id),
            func.coalesce(func.sum(BookSale.net_amount), 0.0),
            func.coalesce(func.sum(BookSale.platform_fee), 0.0),
        ).filter(
            BookSale.book_project_id.in_(book_ids),
            BookSale.status == TransactionStatus.COMPLETED,
        ).group_by(BookSale.book_project_id).all():
            sale_by_book[row[0]] = {
                "completed_units": int(row[1] or 0),
                "author_net": float(row[2] or 0),
                "platform_fees": float(row[3] or 0),
            }

    analytics_by_book: Dict[int, Dict[str, int]] = {}
    if book_ids:
        for row in db.session.query(
            BookAnalytics.book_project_id,
            func.coalesce(func.sum(BookAnalytics.views), 0),
            func.coalesce(func.sum(BookAnalytics.downloads), 0),
            func.coalesce(func.sum(BookAnalytics.purchases), 0),
        ).filter(BookAnalytics.book_project_id.in_(book_ids)).group_by(
            BookAnalytics.book_project_id
        ).all():
            analytics_by_book[row[0]] = {
                "views": int(row[1] or 0),
                "downloads": int(row[2] or 0),
                "purchases": int(row[3] or 0),
            }

    by_book: List[Dict[str, Any]] = []
    summary = {
        "live_listings": 0,
        "total_sales": 0,
        "author_earnings": 0.0,
        "total_gross": 0.0,
        "total_platform_fees": 0.0,
        "total_views": 0,
        "total_downloads": 0,
        "analytics_purchases": 0,
        "marketplace_platform_fee_percent": MARKETPLACE_PLATFORM_FEE_PERCENT,
    }

    for book in books_q:
        s = sale_by_book.get(book.id, {"completed_units": 0, "author_net": 0.0, "platform_fees": 0.0})
        a = analytics_by_book.get(book.id, {"views": 0, "downloads": 0, "purchases": 0})
        live = is_book_published(book)
        if live:
            summary["live_listings"] += 1
        summary["total_sales"] += s["completed_units"]
        summary["author_earnings"] += s["author_net"]
        summary["total_gross"] += s["author_net"] + s.get("platform_fees", 0.0)
        summary["total_platform_fees"] += s.get("platform_fees", 0.0)
        summary["total_views"] += a["views"]
        summary["total_downloads"] += a["downloads"]
        summary["analytics_purchases"] += a["purchases"]

        bundle_base = None
        if book.price and book.audiobook_price:
            bundle_base = (float(book.price) + float(book.audiobook_price)) * 0.8

        print_on = print_listed(book)
        if print_on:
            pp = float(book.print_price or 0)
            ps = print_shipping_amount(book)
            price_print_label = f"${pp:.2f} + ${ps:.2f} ship"
        else:
            price_print_label = "—"

        by_book.append(
            {
                "id": book.id,
                "title": book.title,
                "live": live,
                "price_ebook": book.price,
                "price_ebook_label": _fmt_price(book.price),
                "price_audiobook": book.audiobook_price,
                "price_audiobook_label": _fmt_price(book.audiobook_price),
                "price_bundle_label": _fmt_price(bundle_base),
                "print_listed": print_on,
                "price_print_label": price_print_label,
                "digital_published": bool(getattr(book, "digital_book_published", False)),
                "audiobook_published": bool(getattr(book, "audiobook_published", False)),
                "has_audiobook": bool(getattr(book, "has_audiobook", False)),
                "sales": s["completed_units"],
                "earnings": round(s["author_net"], 2),
                "platform_fees": round(s.get("platform_fees", 0.0), 2),
                "gross": round(s["author_net"] + s.get("platform_fees", 0.0), 2),
                "views": a["views"],
                "downloads": a["downloads"],
            }
        )

    recent_sales: List[Dict[str, Any]] = []
    sales_breakdown: List[Dict[str, Any]] = []
    if book_ids:
        title_by_id = {b.id: b.title for b in books_q}
        rows = (
            BookSale.query.filter(
                BookSale.book_project_id.in_(book_ids),
                BookSale.status == TransactionStatus.COMPLETED,
            )
            .order_by(BookSale.paid_at.desc(), BookSale.created_at.desc())
            .all()
        )
        for sale in rows:
            row = _sale_transparency_row(sale, title_by_id)
            sales_breakdown.append(row)
        recent_sales = sales_breakdown[:8]

    summary["author_earnings"] = round(summary["author_earnings"], 2)
    summary["total_gross"] = round(summary["total_gross"], 2)
    summary["total_platform_fees"] = round(summary["total_platform_fees"], 2)
    return {
        "summary": summary,
        "books": by_book,
        "recent_sales": recent_sales,
        "sales_breakdown": sales_breakdown,
    }
