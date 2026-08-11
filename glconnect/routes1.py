import requests
import re,os
import json
from mailtrap import MailtrapClient, Mail, Address
from glconnect.forms import *
from glconnect.models import*
from glconnect.account_terms import (
    account_terms_context,
    record_account_terms_acceptance,
    validate_account_signup_terms,
)
from glconnect.password_reset_service import (
    apply_password_reset,
    find_user_by_username,
    mask_email,
    request_password_reset,
    verify_password_reset_token,
)
from flask import render_template, request, flash,redirect,url_for,current_app,Blueprint,session,g,jsonify
from itsdangerous import URLSafeTimedSerializer
from flask_login import login_user,logout_user,LoginManager,login_required,current_user
from urllib.parse import urlparse
from sqlalchemy import func
from glconnect.book_platform_security import rate_limit

# Load configuration from environment variables
config = {
    "SENDER_MAIL": os.getenv("SENDER_MAIL"),
    "SENDER_PASSWORD": os.getenv("SENDER_PASSWORD"),
    "RECEIVER_MAIL": os.getenv("RECEIVER_MAIL"),
    "MAIL_TRAP": os.getenv("MAIL_TRAP")
}
bp1 = Blueprint('routes1', __name__)
API_URL = os.getenv("FRONTEND_BASE_URL", "https://ndotonic.com").rstrip("/") + "/word/"
login_manager = LoginManager()
# Set when user opens login/register with next=/mybook/marketplace (fallback if query is lost on POST).
SESSION_AUTH_ENTRY_MARKETPLACE = "auth_entry_marketplace"

SIGNUP_ROLES = frozenset({"artist", "author", "blogger", "other"})

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp1.before_app_request
def load_logged_in_user():
    g.user_id = session.get('user_id')


@bp1.before_app_request
def require_confirmed_email_for_authenticated_users():
    """Do not let legacy unverified sessions continue using the platform."""
    if not getattr(current_user, 'is_authenticated', False):
        return None
    if getattr(current_user, 'confirmed', False) is True:
        return None

    allowed_endpoints = {
        'routes1.confirm_email',
        'routes1.check_email',
        'routes1.resend_confirmation',
        'routes1.logout',
        'routes1.login',
        'routes1.register',
        'routes1.reset_password',
        'routes1.reset_password_request',
    }
    if request.endpoint in allowed_endpoints or request.endpoint == 'static':
        return None

    # An account created before this safeguard may have an active session. End it
    # and send the person to verification instead of permitting platform access.
    session['pending_confirmation_user_id'] = current_user.user_id
    logout_user()
    session.pop('user_id', None)
    flash('Please verify your email address before using your account.', 'warning')
    return redirect(url_for('routes1.check_email'))


def safe_post_auth_next(candidate):
    """Return a same-site path (with optional query) for post-login/register redirect, or None."""
    if not candidate or not isinstance(candidate, str):
        return None
    c = candidate.strip()
    if not c:
        return None
    if c.startswith("//"):
        return None
    if "://" in c:
        try:
            parsed = urlparse(c)
        except Exception:
            return None
        req_host = (request.host or "").split(":")[0].lower()
        netloc = (parsed.netloc or "").split(":")[0].lower()
        if not netloc or netloc != req_host:
            return None
        path = parsed.path or "/"
        c = path + (("?" + parsed.query) if parsed.query else "")
    if not c.startswith("/") or c.startswith("//"):
        return None
    if "/ink-studio" in c:
        return None
    return c


def _marketplace_auth_return_path():
    return url_for("book_platform.marketplace")


def _safe_redirect_path_key(path_with_qs):
    if not path_with_qs:
        return ""
    p = path_with_qs.split("?")[0].rstrip("/")
    return p if p else "/"


def sync_auth_entry_marketplace_from_next(raw_next):
    """If auth was entered from marketplace links, remember for post-login / post-confirm redirect."""
    nxt = safe_post_auth_next(raw_next)
    mp = _marketplace_auth_return_path()
    if nxt and _safe_redirect_path_key(nxt) == _safe_redirect_path_key(mp):
        session[SESSION_AUTH_ENTRY_MARKETPLACE] = True
    else:
        session.pop(SESSION_AUTH_ENTRY_MARKETPLACE, None)


def get_role_based_redirect(user):
    """Initial post-login destination: authors enter Ink Studio; everyone else enters Content Hub."""
    from glconnect.book_platform_routes import _author_requires_setup_profile

    if user.role == "author":
        if _author_requires_setup_profile(user.user_id):
            return redirect(url_for('book_platform.setup_profile'))
        return redirect(url_for('book_platform.books'))

    return redirect(url_for('book_platform.content_hub'))

@bp1.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    raw_next = (
        request.form.get("next")
        if request.method == "POST"
        else request.args.get("next")
    )
    sync_auth_entry_marketplace_from_next(raw_next)

    if request.method == 'POST':
        terms_err = validate_account_signup_terms(request.form)
        if terms_err:
            flash(terms_err, 'error')
        elif form.validate_on_submit():
            new_user_username = form.username.data
            new_user_password = form.password.data
            new_user_email = form.email.data
            new_user_fname = form.fname.data
            new_user_lname = form.lname.data
            new_user_role = (request.form.get("role") or form.role.data or "other").strip()

            if new_user_role not in SIGNUP_ROLES:
                flash("Please choose a valid role.", "error")
            # Validate username and password
            elif len(new_user_username) < 5:
                flash("Username must be at least 5 characters with one uppercase letter and a digit.", 'error')
            elif len(new_user_password) < 8 \
                or not re.search(r"[A-Z]", new_user_password) \
                or not re.search(r"[^\w\s]", new_user_password):
                flash("Password must be at least 8 characters with a capital letter and a special symbol.", 'error')

            else:
                existing_email_user = User.query.filter(
                    func.lower(User.email) == new_user_email.strip().lower()
                ).first()
                if existing_email_user:
                    if not existing_email_user.confirmed:
                        session['pending_confirmation_user_id'] = existing_email_user.user_id
                        _send_confirmation_for_user(existing_email_user)
                        flash('An account with that email is awaiting verification. We sent a new confirmation link if delivery is available.', 'info')
                        return redirect(url_for('routes1.check_email'))
                    flash('An account with that email already exists. Please sign in instead.', 'error')
                    return redirect(url_for('routes1.login'))

                # Create user without confirmation
                new_user = User(
                    username=new_user_username,
                    email=new_user_email,
                    first_name=new_user_fname,
                    last_name=new_user_lname,
                    confirmed=False,
                    role=new_user_role
                )
                new_user.set_password(new_user_password)
                record_account_terms_acceptance(new_user)

                try:
                    db.session.add(new_user)
                    db.session.commit()

                    session['pending_confirmation_user_id'] = new_user.user_id
                    if not _send_confirmation_for_user(new_user):
                        flash(
                            "Your account was created, but we couldn’t send the confirmation email. "
                            "Please try again in a little while or contact support if this keeps happening.",
                            "error",
                        )

                    nxt = safe_post_auth_next(
                        request.args.get("next") or request.form.get("next")
                    )
                    if nxt:
                        session["post_confirm_next"] = nxt

                    # Redirect to a page telling the user to check their email
                    return redirect(url_for('routes1.check_email'))

                except Exception as e:
                    db.session.rollback()
                    flash("An error occurred while creating your account. Please try again.", 'error')

    register_next = safe_post_auth_next(
        request.form.get("next") or request.args.get("next")
    )
    return render_template(
        "register.html",
        title="Register",
        form=form,
        register_next=register_next,
        **account_terms_context(),
    )

def send_confirmation_email(to_email, confirm_url):
    """Send verification email via Mailtrap. Returns True if sent, False if misconfigured or send failed."""
    sender = os.getenv("SENDER_MAIL")
    receiver = to_email
    api_key = config.get("MAIL_TRAP")

    if not sender:
        current_app.logger.error("SENDER_MAIL is not set; confirmation email not sent")
        return False
    if not api_key:
        current_app.logger.error("MAIL_TRAP is not set; confirmation email not sent")
        return False

    try:
        mail = Mail(
            sender=Address(email=sender, name="Please verify your account"),
            to=[Address(email=receiver)],
            subject="Please verify your account",
            text=(
                f"Click the link below to confirm your email:\n\n{confirm_url}"
            ),
            category="Verify email"
        )
        MailtrapClient(token=api_key).send(mail)
        return True
    except Exception as e:
        current_app.logger.exception(
            "Confirmation email failed for %s: %s", receiver, e
        )
        return False


def _send_confirmation_for_user(user):
    """Create a fresh, expiring verification link for an unconfirmed account."""
    if not user or getattr(user, 'confirmed', False):
        return False
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = serializer.dumps(user.email, salt='email-confirm')
    confirm_url = url_for('routes1.confirm_email', token=token, _external=True)
    return send_confirmation_email(user.email, confirm_url)


@bp1.route('/confirm/<token>')
def confirm_email(token):
    try:
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        email = s.loads(token, salt='email-confirm', max_age=3600) 
    except Exception as e:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('routes1.register'))  

    user = User.query.filter_by(email=email).first_or_404()
    if user.confirmed:
        flash('Your email has already been confirmed.', 'info')
    else:
        user.confirmed = True
        db.session.commit()
        flash('Your email has been confirmed. Welcome!', 'success')
    
    # Automatically log the user in after email confirmation
    login_user(user)
    session['user_id'] = user.user_id
    session.pop('pending_confirmation_user_id', None)

    pending = session.pop("post_confirm_next", None)
    dest = safe_post_auth_next(pending) if pending else None
    if dest:
        session.pop(SESSION_AUTH_ENTRY_MARKETPLACE, None)
        return redirect(dest)
    if session.pop(SESSION_AUTH_ENTRY_MARKETPLACE, None):
        return redirect(url_for("book_platform.marketplace"))

    # Use the same role-based redirect as login
    return get_role_based_redirect(user)

@bp1.route('/check_email')
def check_email():
    return render_template(
        'check_email.html',
        title='Check Email',
        confirmation_email=None,
    )


@bp1.route('/resend-confirmation', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=60)
def resend_confirmation():
    """Resend a verification link without revealing whether an address has an account."""
    # Form and JSON clients are both supported; do not echo an address in responses.
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        supplied = (payload.get('email') or '').strip().lower()
    else:
        supplied = (request.form.get('email') or '').strip().lower()
    user = None
    if supplied:
        user = User.query.filter(func.lower(User.email) == supplied).first()
    elif session.get('pending_confirmation_user_id'):
        user = User.query.get(session['pending_confirmation_user_id'])
    if user and not getattr(user, 'confirmed', False):
        _send_confirmation_for_user(user)
        session['pending_confirmation_user_id'] = user.user_id
    message = 'If an unverified account exists for that email, a confirmation link has been sent.'
    if request.is_json:
        return jsonify({'success': True, 'message': message})
    flash(message, 'info')
    return redirect(url_for('routes1.check_email'))

@bp1.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    login_ctx = {
        "show_password_reset_help": False,
        "failed_username": "",
        "masked_email": None,
        "reset_email_sent": False,
    }

    if request.method == "GET":
        sync_auth_entry_marketplace_from_next(request.args.get("next"))

    if request.method == "POST" and request.form.get("action") == "send_password_reset":
        identifier = (request.form.get("username") or form.username.data or "").strip()
        sent, masked = request_password_reset(identifier)
        login_ctx["failed_username"] = identifier
        form.username.data = identifier
        login_ctx["reset_email_sent"] = sent
        if sent and masked:
            flash(f"Password reset link sent to {masked}. Check your inbox.", "info")
        elif sent:
            flash("Password reset link sent. Check your inbox.", "info")
        else:
            flash(
                "We could not send a reset link right now. Try again shortly or use "
                "Reset password below with your username or email.",
                "error",
            )
            login_ctx["show_password_reset_help"] = True
            user = find_user_by_username(identifier)
            if user:
                login_ctx["masked_email"] = mask_email(user.email)
        return render_template(
            "login.html",
            title="Login",
            form=form,
            **login_ctx,
        )

    if form.validate_on_submit():
        username = (form.username.data or "").strip()
        password = form.password.data
        user = find_user_by_username(username)
        if user and user.check_password(password):
            if not getattr(user, 'confirmed', False):
                session['pending_confirmation_user_id'] = user.user_id
                flash('Verify your email address before signing in. You can request a new confirmation link below.', 'warning')
                return redirect(url_for('routes1.check_email'))
            login_user(user)
            session['user_id'] = user.user_id
            flash('Login successful!', 'success')

            next_page = safe_post_auth_next(
                request.args.get("next") or request.form.get("next")
            )
            if next_page:
                session.pop(SESSION_AUTH_ENTRY_MARKETPLACE, None)
                return redirect(next_page)
            if session.pop(SESSION_AUTH_ENTRY_MARKETPLACE, None):
                return redirect(url_for("book_platform.marketplace"))

            return get_role_based_redirect(user)

        flash("Those sign-in details did not match.", "error")
        login_ctx["show_password_reset_help"] = True
        login_ctx["failed_username"] = username
        form.username.data = username
        if user:
            login_ctx["masked_email"] = mask_email(user.email)

    return render_template(
        "login.html",
        title="Login",
        form=form,
        **login_ctx,
    )

@bp1.route('/playlist')
def playlist():
    """Render the playlist page."""
    return render_template('playlist.html')

@bp1.route('/words', methods=['GET', 'POST'])
def findwords():
    word = None

    if request.method == 'POST':
        word = request.form.get('word')
    elif request.method == 'GET':
        word = request.args.get('word')
    if word:
        word_data = word_details(word)
        return render_template('vocabulary.html', word=word_data)
    return render_template('vocabulary.html', word=None)

def word_details(word):
    try:
        from .models import WordsData
        
        # Search for the word in the local database
        word_data = WordsData.query.filter(WordsData.word == word.lower()).first()
        
        if word_data:
            # Extract English meaning properly
            meaning = "No meaning available"
            if word_data.igisobanuro_meaning and len(word_data.igisobanuro_meaning) > 0:
                last_meaning_array = word_data.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
            
            return {
                "word": word_data.word,
                "umuzi_root": word_data.umuzi_root,
                "basoma_phonetics": word_data.basoma_phonetics,
                "bandika_writing": word_data.bandika_writing,
                "icyiciro_pos": word_data.icyiciro_pos,
                "igisobanuro_meaning": word_data.igisobanuro_meaning,
                "english_meaning": meaning
            }
        else:
            return {"error": "Word not found in dictionary"}
            
    except Exception as e:
        print(f"Error in word_details: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error fetching word details: {e}"}

@bp1.route('/contribute-word', methods=['POST'])
def contribute_word():
    """Handle word contribution submissions."""
    try:
        from .models import WordContribution, WordsData, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Get form data
        word = request.form.get('kinyarwanda_word', '').strip()
        meaning = request.form.get('english_meaning', '').strip()
        example_sentence = request.form.get('example_sentence', '').strip()
        part_of_speech = request.form.get('part_of_speech', '').strip()
        phonetics = request.form.get('phonetics', '').strip()
        contributor_name = request.form.get('contributor_name', '').strip()
        
        # Validate required fields
        if not word or not meaning:
            return jsonify({
                'success': False,
                'message': 'Word and meaning are required fields.'
            }), 400
        
        # Check if word already exists in the main dictionary
        existing_word = WordsData.query.filter_by(word=word.lower()).first()
        if existing_word:
            return jsonify({
                'success': False,
                'message': f'The word "{word}" already exists in our dictionary.'
            }), 400
        
        # Check if word already has a pending contribution
        pending_contribution = WordContribution.query.filter_by(
            word=word.lower(), 
            status='pending'
        ).first()
        if pending_contribution:
            return jsonify({
                'success': False,
                'message': f'A contribution for "{word}" is already pending review.'
            }), 400
        
        # Create new contribution
        contribution = WordContribution(
            word=word.lower(),
            meaning=meaning,
            example_sentence=example_sentence if example_sentence else None,
            part_of_speech=part_of_speech if part_of_speech else None,
            phonetics=phonetics if phonetics else None,
            contributor_id=current_user.user_id if current_user.is_authenticated else None,
            contributor_name=contributor_name if contributor_name else 'Anonymous',
            status='pending'
        )
        
        db.session.add(contribution)
        db.session.commit()
        
        print(f"DEBUG: New word contribution submitted: '{word}' by {contributor_name or 'Anonymous'}")
        
        return jsonify({
            'success': True,
            'message': 'Contribution submitted successfully! It will be reviewed before being added to the dictionary.'
        })
        
    except Exception as e:
        print(f"Error in contribute_word: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred while submitting your contribution. Please try again.'
        }), 500

@bp1.route('/admin/contributions')
@login_required
def admin_contributions():
    """Admin page to review word contributions."""
    from .models import WordContribution, db
    from flask_login import current_user
    
    # Check if user is admin
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('routes1.findwords'))
    
    # Get all pending contributions
    pending_contributions = WordContribution.query.filter_by(status='pending').order_by(WordContribution.created_at.desc()).all()
    
    return render_template('admin_contributions.html', contributions=pending_contributions)

@bp1.route('/admin/approve-contribution/<int:contribution_id>', methods=['POST'])
@login_required
def approve_contribution(contribution_id):
    """Approve a word contribution and add it to the main dictionary."""
    try:
        from .models import WordContribution, WordsData, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get the contribution
        contribution = WordContribution.query.get_or_404(contribution_id)
        
        if contribution.status != 'pending':
            status_msg = {
                'approved': 'This contribution has already been approved',
                'rejected': 'This contribution has already been rejected'
            }.get(contribution.status, 'This contribution has already been processed')
            return jsonify({'success': False, 'message': status_msg}), 400
        
        # Add to community dictionary (separate from main dictionary)
        from .community_dictionary_manager import community_dictionary_manager
        
        word_data = {
            "word": contribution.word,
            "meaning": contribution.meaning,
            "example_sentence": contribution.example_sentence or "",
            "part_of_speech": contribution.part_of_speech or "",
            "phonetics": contribution.phonetics or "",
            "contributor_name": contribution.contributor_name or "Anonymous",
            "approved_by": current_user.username or "Admin"
        }
        
        success = community_dictionary_manager.add_word(word_data)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Error saving word to community dictionary. Word may already exist.'
            }), 500
        
        # Update contribution status
        contribution.status = 'approved'
        contribution.reviewed_at = datetime.now(timezone.utc)
        contribution.reviewer_id = current_user.user_id
        contribution.admin_notes = request.json.get('admin_notes', '') if request.is_json else ''
        
        db.session.commit()
        
        print(f"DEBUG: Contribution approved: '{contribution.word}' by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Word "{contribution.word}" has been approved and added to the community dictionary.'
        })
        
    except Exception as e:
        print(f"Error in approve_contribution: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error approving contribution'}), 500

@bp1.route('/admin/reject-contribution/<int:contribution_id>', methods=['POST'])
@login_required
def reject_contribution(contribution_id):
    """Reject a word contribution."""
    try:
        from .models import WordContribution, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get the contribution
        contribution = WordContribution.query.get_or_404(contribution_id)
        
        if contribution.status != 'pending':
            return jsonify({'success': False, 'message': 'Contribution already processed'}), 400
        
        # Update contribution status
        contribution.status = 'rejected'
        contribution.reviewed_at = datetime.now(timezone.utc)
        contribution.reviewer_id = current_user.user_id
        contribution.admin_notes = request.json.get('admin_notes', '') if request.is_json else ''
        
        db.session.commit()
        
        print(f"DEBUG: Contribution rejected: '{contribution.word}' by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Contribution for "{contribution.word}" has been rejected.'
        })
        
    except Exception as e:
        print(f"Error in reject_contribution: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error rejecting contribution'}), 500

@bp1.route('/admin/edit-contribution/<int:contribution_id>', methods=['POST'])
@login_required
def edit_contribution(contribution_id):
    """Edit a word contribution before approval."""
    try:
        from .models import WordContribution, db
        from flask_login import current_user
        from datetime import datetime, timezone
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        # Get the contribution
        contribution = WordContribution.query.get_or_404(contribution_id)
        
        if contribution.status != 'pending':
            return jsonify({'success': False, 'message': 'Contribution already processed'}), 400
        
        # Get updated data from request
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        # Update contribution fields
        if 'word' in data:
            contribution.word = data['word']
        if 'meaning' in data:
            contribution.meaning = data['meaning']
        if 'example_sentence' in data:
            contribution.example_sentence = data['example_sentence']
        if 'part_of_speech' in data:
            contribution.part_of_speech = data['part_of_speech']
        if 'phonetics' in data:
            contribution.phonetics = data['phonetics']
        if 'contributor_name' in data:
            contribution.contributor_name = data['contributor_name']
        
        # Add admin notes about the edit
        edit_note = f"Edited by {current_user.username} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
        if contribution.admin_notes:
            contribution.admin_notes += f"\n{edit_note}"
        else:
            contribution.admin_notes = edit_note
        
        db.session.commit()
        
        print(f"DEBUG: Contribution edited: '{contribution.word}' by admin {current_user.username}")
        
        return jsonify({
            'success': True,
            'message': f'Contribution for "{contribution.word}" has been updated.',
            'contribution': {
                'id': contribution.id,
                'word': contribution.word,
                'meaning': contribution.meaning,
                'example_sentence': contribution.example_sentence,
                'part_of_speech': contribution.part_of_speech,
                'phonetics': contribution.phonetics,
                'contributor_name': contribution.contributor_name
            }
        })
        
    except Exception as e:
        print(f"Error in edit_contribution: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error editing contribution'}), 500

@bp1.route('/api/game-words')
def get_game_words():
    """Get random words for the matching game from the original dictionary only."""
    try:
        from .models import WordsData
        import random
        
        # Get total count first
        total_count = WordsData.query.count()
        
        if total_count < 6:
            return jsonify({
                'success': False,
                'message': 'Not enough words in dictionary for the game. Need at least 6 words.'
            }), 400
        
        # Get 6 random words with fallback mechanism
        try:
            # Try the optimized approach first
            offset = random.randint(0, max(0, total_count - 6))
            selected_words = WordsData.query.order_by(WordsData.id).offset(offset).limit(6).all()
            
            # If we didn't get enough words, get more
            if len(selected_words) < 6:
                additional_needed = 6 - len(selected_words)
                additional_words = WordsData.query.filter(
                    ~WordsData.id.in_([w.id for w in selected_words])
                ).limit(additional_needed).all()
                selected_words.extend(additional_words)
        except Exception as e:
            print(f"Word game query failed: {e}, using fallback")
            # Fallback: get first 6 words (simple and reliable)
            selected_words = WordsData.query.limit(6).all()
        
        # Prepare game data
        game_words = []
        for word in selected_words:
            # Extract English meaning (usually the last item in the last array)
            if word.igisobanuro_meaning and len(word.igisobanuro_meaning) > 0:
                # Get the last meaning array and extract the English translation (last item)
                last_meaning_array = word.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
                else:
                    meaning = "No meaning available"
            else:
                meaning = "No meaning available"
            
            game_words.append({
                'id': word.id,
                'word': word.word,
                'meaning': meaning,
                'part_of_speech': word.icyiciro_pos[0] if word.icyiciro_pos else None
            })
        
        # Shuffle the meanings to make it challenging
        meanings = [word['meaning'] for word in game_words]
        random.shuffle(meanings)
        
        # Debug logging removed for better performance
        
        return jsonify({
            'success': True,
            'words': game_words,
            'meanings': meanings
        })
        
    except Exception as e:
        print(f"Error in get_game_words: {e}")
        return jsonify({
            'success': False,
            'message': f'Error fetching words for the game: {str(e)}'
        }), 500

@bp1.route('/api/search-word')
def search_word_api():
    """API endpoint for word search."""
    word = request.args.get('word', '').strip()
    if not word:
        return jsonify({'success': False, 'message': 'No word provided'}), 400
    
    try:
        from .models import WordsData
        
        # Search for the word in the local database (case-insensitive)
        word_data = WordsData.query.filter(WordsData.word.ilike(f'%{word.lower()}%')).first()
        
        if word_data:
            # Extract English meaning properly
            meaning = "No meaning available"
            if word_data.igisobanuro_meaning and len(word_data.igisobanuro_meaning) > 0:
                last_meaning_array = word_data.igisobanuro_meaning[-1]
                if isinstance(last_meaning_array, list) and len(last_meaning_array) > 0:
                    meaning = last_meaning_array[-1]  # English is usually last
                elif isinstance(last_meaning_array, str):
                    meaning = last_meaning_array
            
            return jsonify({
                'success': True,
                'word': {
                    "word": word_data.word,
                    "umuzi_root": word_data.umuzi_root,
                    "basoma_phonetics": word_data.basoma_phonetics,
                    "bandika_writing": word_data.bandika_writing,
                    "icyiciro_pos": word_data.icyiciro_pos,
                    "igisobanuro_meaning": word_data.igisobanuro_meaning,
                    "english_meaning": meaning
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Word not found in dictionary'
            }), 404
            
    except Exception as e:
        print(f"Error in search_word_api: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error searching for word: {str(e)}'
        }), 500


@bp1.route('/api/picture-word-game')
def get_picture_word_game():
    """Get words for picture-word matching game using pre-generated images."""
    try:
        from .models import WordsData, PictureGameItem, db
        import random
        from datetime import datetime, timezone
        
        # Get all available picture game items for maximum variety
        all_available_items = PictureGameItem.query.filter(
            PictureGameItem.is_active == True
        ).all()
        
        if len(all_available_items) >= 3:
            # Smart selection strategy for variety:
            # 1. Get items that haven't been used recently (last 5 games)
            # 2. Mix with some less-used items
            # 3. Always include some variety
            
            # Sort by usage: least used first, then by last used
            sorted_items = sorted(all_available_items, 
                                key=lambda x: (x.used_count, x.last_used or datetime.min.replace(tzinfo=timezone.utc)))
            
            # Create a weighted selection pool
            # 60% from least used items, 40% from random selection
            pool_size = min(15, len(sorted_items))  # Use up to 15 items for variety
            
            # Get least used items (60% of pool)
            least_used_count = int(pool_size * 0.6)
            least_used_items = sorted_items[:least_used_count]
            
            # Get random items from the rest (40% of pool)
            remaining_items = sorted_items[least_used_count:]
            random_count = pool_size - least_used_count
            random_items = random.sample(remaining_items, min(random_count, len(remaining_items))) if remaining_items else []
            
            # Combine both pools
            selection_pool = least_used_items + random_items
            
            # Randomly select 3 from the combined pool
            selected_items = random.sample(selection_pool, 3)
            
            # Log selection for debugging
            selected_words = [item.kinyarwanda_word for item in selected_items]
            print(f"🎮 Picture game selection: {selected_words} (from {len(all_available_items)} available)")
            
            # Update usage tracking
            for item in selected_items:
                item.used_count += 1
                item.last_used = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Convert to game data format with enhanced text-overlay support
            game_data = []
            for item in selected_items:
                # Parse text overlay data if available
                text_overlay_data = {}
                if item.text_overlay_data:
                    try:
                        text_overlay_data = json.loads(item.text_overlay_data)
                    except:
                        text_overlay_data = {}
                
                # Create enhanced image data from stored filename
                image_data = {
                    'type': 'stored_image',
                    'image_url': f"/static/pictures/{item.image_filename}",
                    'description': item.english_meaning,
                    'is_noun': True,
                    'image_type': item.image_type or 'text_overlay',
                    'text_overlay': {
                        'english_meaning': text_overlay_data.get('english_meaning', item.english_meaning),
                        'text_position': text_overlay_data.get('text_position', 'bottom_overlay'),
                        'text_type': text_overlay_data.get('text_type', 'english_only'),
                        'font_size': text_overlay_data.get('font_size', 'medium')
                    },
                    'pronunciation_guide': item.pronunciation_guide,
                    'context_hint': item.context_hint
                }
                
                game_data.append({
                    'id': item.id,
                    'word': item.kinyarwanda_word,
                    'meaning': item.english_meaning,
                    'image': image_data,
                    'part_of_speech': 'noun'  # Assume nouns for picture game
                })
            
            return jsonify({
                'success': True,
                'game_data': game_data,
                'source': 'pre_generated'
            })
        
        else:
            # Fallback: Generate on-demand if not enough pre-generated items
            return jsonify({
                'success': False,
                'message': 'Not enough pre-generated pictures available. Please run the daily generation script first.',
                'available_count': len(all_available_items),
                'needed_count': 3
            }), 400
        
    except Exception as e:
        print(f"Error in get_picture_word_game: {e}")
        return jsonify({
            'success': False,
            'message': 'Error loading picture-word game'
        }), 500
@bp1.route('/admin/community-dictionary')
@login_required
def community_dictionary():
    """View community dictionary (admin only)."""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': 'Access denied'}), 403
        
        stats = community_dictionary_manager.get_stats()
        words = community_dictionary_manager.get_all_words()
        
        return render_template('community_dictionary.html', 
                             stats=stats, 
                             words=words)
        
    except Exception as e:
        print(f"Error in community_dictionary: {e}")
        return jsonify({'success': False, 'message': 'Error loading community dictionary'}), 500

@bp1.route('/community-dictionary')
def community_dictionary_public():
    """View community dictionary (public read-only)."""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        stats = community_dictionary_manager.get_stats()
        words = community_dictionary_manager.get_all_words()
        
        return render_template('community_dictionary_public.html', 
                             stats=stats, 
                             words=words)
        
    except Exception as e:
        print(f"Error in community_dictionary_public: {e}")
        return jsonify({'success': False, 'message': 'Error loading community dictionary'}), 500

@bp1.route('/contribute-word')
def contribute_word_page():
    """Dedicated page for word contribution"""
    return render_template('contribute_word.html')


@bp1.route('/api/community-stats')
def get_community_stats():
    """API endpoint to get community dictionary statistics"""
    try:
        from .community_dictionary_manager import community_dictionary_manager
        
        stats = community_dictionary_manager.get_stats()
        
        # Get pending contributions count
        pending_count = WordContribution.query.filter_by(status='pending').count()
        stats['pending_words'] = pending_count
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            'total_words': 0,
            'approved_words': 0,
            'pending_words': 0,
            'error': str(e)
        })

@bp1.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_password_reset_token(token)
    if not email:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('routes1.reset_password_request'))

    user = User.query.filter_by(email=email).first_or_404()
    form = PasswordResetForm()

    if form.validate_on_submit():
        err = apply_password_reset(user, form.password.data)
        if err:
            flash(err, 'error')
        else:
            flash('Your password has been reset successfully. You can now log in.', 'success')
            return redirect(url_for('routes1.login'))

    return render_template('passreset.html', title='Reset Password', form=form, token=token)


@bp1.route('/reset_request', methods=['GET', 'POST'])
def reset_password_request():
    form = ResetRequestForm()
    prefill_login = (request.args.get("login") or request.args.get("username") or "").strip()

    if request.method == "GET" and prefill_login and not form.login.data:
        form.login.data = prefill_login

    if form.validate_on_submit():
        identifier = (form.login.data or "").strip()
        sent, masked = request_password_reset(identifier)

        if sent and masked:
            flash(f"Password reset link sent to {masked}. Check your inbox.", "info")
            return redirect(url_for('routes1.login'))
        if sent:
            flash("Password reset link sent. Check your inbox.", "info")
            return redirect(url_for('routes1.login'))

        flash(
            "No account matched that username or email. Check the spelling or create an account.",
            "error",
        )
        return redirect(url_for('routes1.register'))

    return render_template('passreq.html', title='Reset Password', form=form)
