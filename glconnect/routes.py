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
    "Co founder CTO",
    "Board Member",
    "AI Agent Engineer",
    "Quality Testing",
    "Penetration Tester",
)

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    """Render the home page."""
    return render_template('landing.html')

@bp.route('/home')
def home():
    return render_template('home.html')

@bp.route('/marketplace')
@login_required
def marketplace():
    """Universal marketplace access - redirects to Ink Studio marketplace"""
    return redirect(url_for('book_platform.marketplace'))

@bp.route('/about')
@login_required
def about():
    return render_template('about.html')

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
    form.position.choices = [("", "Select a role…")] + [(p, p) for p in CAREER_POSITIONS]
    position_q = (request.args.get('position') or '').strip()
    if request.method == 'GET' and position_q in CAREER_POSITIONS:
        form.position.data = position_q

    sender = (os.getenv("SENDER_MAIL") or "").strip()
    receiver = (os.getenv("RECEIVER_MAIL") or "info@ndotonic.com").strip()
    api_key = (os.getenv("MAIL_TRAP") or "").strip()

    if form.validate_on_submit():
        position = (form.position.data or "").strip()
        if position not in CAREER_POSITIONS:
            flash("Please choose a valid position.", "error")
            return render_template(
                "careers_apply.html",
                form=form,
                positions=CAREER_POSITIONS,
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
                positions=CAREER_POSITIONS,
            )

        portfolio = (form.portfolio_url.data or "").strip()
        body = (
            f"Position: {position}\n"
            f"First name: {form.FirstName.data}\n"
            f"Last name: {form.LastName.data}\n"
            f"Email: {form.email.data}\n"
        )
        if portfolio:
            body += f"Portfolio / LinkedIn: {portfolio}\n"
        body += f"\nMessage:\n{form.message.data}"

        try:
            mail = Mail(
                sender=Address(email=sender, name="GLC Careers"),
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
                positions=CAREER_POSITIONS,
            )

        return redirect(
            url_for(
                "routes.careers_apply",
                position=position,
                applied="1",
            )
        )

    applied = (request.args.get("applied") or "").strip() == "1"
    applied_position = position_q if applied and position_q in CAREER_POSITIONS else None

    return render_template(
        "careers_apply.html",
        form=form,
        positions=CAREER_POSITIONS,
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

