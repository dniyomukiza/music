from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timezone
import psutil
import os
import logging

from mailtrap import MailtrapClient, Mail, Address

from glconnect.forms import CareerApplicationForm

logger = logging.getLogger(__name__)

CAREER_POSITIONS = (
    "Open pool",
)


def career_positions_allowed():
    """Roles shown and accepted on the careers apply form."""
    return CAREER_POSITIONS

bp = Blueprint('routes', __name__)


def _about_landing():
    """Public marketing home — bento/ticker links gate guests through sign-in."""
    from glconnect.ink_studio_v1 import about_scroll_nav_urls

    return render_template(
        'about.html',
        about_nav=about_scroll_nav_urls(),
        is_authenticated=current_user.is_authenticated,
    )


@bp.route('/')
def index():
    """Site entry — marketing landing (Turning stories into published books)."""
    return _about_landing()


@bp.route('/home')
def home():
    return _about_landing()


@bp.route('/about')
def about():
    """Alias for the public marketing landing."""
    return _about_landing()


@bp.route('/platform')
def platform():
    """Internal link directory for all active routes."""
    from glconnect.ink_studio_v1 import about_site_link_groups

    return render_template(
        'platform_directory.html',
        link_groups=about_site_link_groups(),
        is_authenticated=current_user.is_authenticated,
    )


_POLICY_PAGES = {
    'terms': {
        'title': 'Terms of Service',
        'eyebrow': 'Using Ndotonic',
        'description': 'The basic rules for accounts, the marketplace, and creator tools.',
    },
    'privacy': {
        'title': 'Privacy Policy',
        'eyebrow': 'Your information',
        'description': 'What we collect, why we use it, and what is public.',
    },
    'refunds': {
        'title': 'Refund & Cancellation Policy',
        'eyebrow': 'Purchases and support',
        'description': 'How digital purchases, print orders, and campaign contributions are handled.',
    },
    'shipping': {
        'title': 'Print Shipping & Fulfillment Policy',
        'eyebrow': 'Author-fulfilled print',
        'description': 'What buyers can expect when an author ships a physical book.',
    },
    'rights': {
        'title': 'Content, Rights & Takedown Policy',
        'eyebrow': 'Publishing responsibly',
        'description': 'The rights authors need and how we handle credible complaints.',
    },
    'ai': {
        'title': 'AI Use Policy',
        'eyebrow': 'Optional creator tools',
        'description': 'Responsibilities when using AI-assisted text, art, or narration.',
    },
}


@bp.route('/policies')
def policies():
    """Public index for customer- and creator-facing policies."""
    return render_template('policies.html', policy_pages=_POLICY_PAGES, active_policy=None)


@bp.route('/policies/<policy_key>')
def policy_detail(policy_key):
    """Public policy page; policy text lives in the template for reviewable releases."""
    policy = _POLICY_PAGES.get(policy_key)
    if not policy:
        return redirect(url_for('routes.policies'))
    return render_template(
        'policies.html',
        policy_pages=_POLICY_PAGES,
        active_policy=policy_key,
        policy=policy,
    )


@bp.route('/marketplace')
@login_required
def marketplace():
    """Universal marketplace access - redirects to Ink Studio marketplace"""
    return redirect(url_for('book_platform.marketplace'))


@bp.route('/pitch-deck')
def pitch_deck():
    return render_template('pitch_deck.html', deck_year=datetime.now(timezone.utc).year)

@bp.route('/careers')
def careers():
    """Careers page with job openings."""
    return render_template('careers.html', positions=CAREER_POSITIONS)


@bp.route('/careers/apply', methods=['GET', 'POST'])
def careers_apply():
    """Submit a job application via Mailtrap (same delivery path as the contact form)."""
    form = CareerApplicationForm()
    allowed_positions = career_positions_allowed()
    form.position.choices = [("", "Select a role…")] + [(p, p) for p in allowed_positions]
    position_q = (request.args.get('position') or '').strip()
    if request.method == 'GET' and position_q in allowed_positions:
        form.position.data = position_q

    sender = (os.getenv("SENDER_MAIL") or "").strip()
    receiver = (os.getenv("RECEIVER_MAIL") or "info@ndotonic.com").strip()
    api_key = (os.getenv("MAIL_TRAP") or "").strip()

    if form.validate_on_submit():
        position = (form.position.data or "").strip()
        if position not in allowed_positions:
            flash("Please choose a valid position.", "error")
            return render_template(
                "careers_apply.html",
                form=form,
                positions=allowed_positions,
            )

        if not sender or not receiver or not api_key:
            logger.warning(
                "Careers apply mail not configured (sender=%s receiver=%s api_key=%s)",
                bool(sender),
                bool(receiver),
                bool(api_key),
            )
            flash(
                "We can’t send applications right now. Please email info@ndotonic.com directly.",
                "error",
            )
            return render_template(
                "careers_apply.html",
                form=form,
                positions=allowed_positions,
            )

        body = (
            f"Position: {position}\n"
            f"First name: {form.FirstName.data}\n"
            f"Last name: {form.LastName.data}\n"
            f"Email: {form.email.data}\n"
            f"Phone: {form.phone.data}\n"
            f"\nMessage:\n{form.message.data}"
        )

        try:
            mail = Mail(
                sender=Address(email=sender, name="Ndotonic Careers"),
                to=[Address(email=receiver)],
                subject=f"Job application: {position}",
                text=body,
                category="Careers",
            )
            MailtrapClient(token=api_key).send(mail)
        except Exception:
            logger.exception("Careers application Mailtrap send failed")
            flash(
                "We couldn’t send your application. Please try again or email info@ndotonic.com.",
                "error",
            )
            return render_template(
                "careers_apply.html",
                form=form,
                positions=allowed_positions,
            )

        return redirect(
            url_for(
                "routes.careers_apply",
                position=position,
                applied="1",
            )
        )

    applied = (request.args.get("applied") or "").strip() == "1"
    applied_position = position_q if applied and position_q in allowed_positions else None

    return render_template(
        "careers_apply.html",
        form=form,
        positions=allowed_positions,
        applied=applied,
        applied_position=applied_position,
    )


@bp.route('/health')
def health():
    """Health check endpoint for monitoring and Docker healthchecks.

    Always returns HTTP 200 if the app process is serving requests. Metrics are best-effort:
    psutil can fail in some container/cgroup setups; a 500 here breaks Docker's urllib
    healthcheck and nginx depends_on: service_healthy.
    """
    payload = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        system_memory = psutil.virtual_memory()
        payload.update({
            'status': 'healthy',
            'memory_usage_mb': round(memory_mb, 2),
            'system_memory_percent': round(system_memory.percent, 2),
            'system_memory_available_gb': round(system_memory.available / 1024 / 1024 / 1024, 2),
        })
    except Exception as e:
        payload.update({
            'status': 'degraded',
            'error': str(e),
        })
    return jsonify(payload), 200
import glconnect.routes1
import glconnect.routes2
