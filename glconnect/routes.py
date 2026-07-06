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

# Former multi-role careers page — served at /legacy/careers; swap into CAREER_POSITIONS to restore.
CAREER_POSITIONS_LEGACY = (
    "Co founder CTO",
    "Board Member",
    "AI Agent Engineer",
    "Quality Testing",
    "Penetration Tester",
)


def career_positions_allowed():
    """Union of current and legacy role titles (careers apply accepts both)."""
    return tuple(dict.fromkeys((*CAREER_POSITIONS, *CAREER_POSITIONS_LEGACY)))

bp = Blueprint('routes', __name__)

@bp.route('/')
def index():
    """Site entry — platform directory lives at /about; former hero landing is /legacy/home."""
    # #region agent log
    try:
        import json, time
        with open("/Applications/untitled folder/music-1/.cursor/debug-4b74e6.log", "a", encoding="utf-8") as _lf:
            _lf.write(json.dumps({"sessionId": "4b74e6", "hypothesisId": "route", "location": "routes.py:index", "message": "root redirect to about", "data": {}, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
    # #endregion
    return redirect(url_for('routes.about'), code=301)

@bp.route('/home')
def home():
    """Legacy URL — platform directory is at /about."""
    return redirect(url_for('routes.about'), code=301)

@bp.route('/marketplace')
@login_required
def marketplace():
    """Universal marketplace access - redirects to Ink Studio marketplace"""
    return redirect(url_for('book_platform.marketplace'))

@bp.route('/about')
def about():
    from glconnect.ink_studio_v1 import about_site_link_groups

    # #region agent log
    try:
        import json, time
        with open("/Applications/untitled folder/music-1/.cursor/debug-4b74e6.log", "a", encoding="utf-8") as _lf:
            _lf.write(json.dumps({"sessionId": "4b74e6", "hypothesisId": "B", "location": "routes.py:about", "message": "about route enter", "data": {"authenticated": current_user.is_authenticated}, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
    # #endregion
    link_groups = about_site_link_groups()
    # #region agent log
    try:
        import json, time
        with open("/Applications/untitled folder/music-1/.cursor/debug-4b74e6.log", "a", encoding="utf-8") as _lf:
            _lf.write(json.dumps({"sessionId": "4b74e6", "hypothesisId": "B", "location": "routes.py:about", "message": "link groups built", "data": {"group_count": len(link_groups)}, "timestamp": int(time.time() * 1000)}) + "\n")
    except Exception:
        pass
    # #endregion
    return render_template(
        'about.html',
        link_groups=link_groups,
        is_authenticated=current_user.is_authenticated,
    )


@bp.route('/legacy/about')
@login_required
def about_legacy():
    """Former marketing about page (bento layout). Swap template in ``about()`` to restore site-wide."""
    from glconnect.ink_studio_v1 import about_scroll_nav_urls

    return render_template('about_legacy.html', about_nav=about_scroll_nav_urls())


@bp.route('/legacy/home')
def home_legacy():
    """Former public home landing (pre platform-directory /about links). Swap template in ``index()`` to restore."""
    return render_template('landing_legacy.html')


@bp.route('/legacy/careers')
def careers_legacy():
    """Former multi-role careers page. Swap template/positions in ``careers()`` to restore."""
    return render_template('careers_legacy.html', positions=CAREER_POSITIONS_LEGACY)


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

