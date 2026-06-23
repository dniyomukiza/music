import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from .models import *
from .forms import *
from dotenv import load_dotenv
from mailtrap import MailtrapClient, Mail, Address
from flask import redirect,url_for,render_template,request,flash,abort,send_from_directory,jsonify
from flask import Blueprint,render_template,request,flash,redirect,url_for,send_file,current_app,session
from flask_login import current_user, login_required, logout_user
from flask_ckeditor import CKEditor,upload_success, upload_fail
import google.generativeai as genai
from sqlalchemy import inspect, func
import logging

logger = logging.getLogger(__name__)
load_dotenv()
# Load configuration from environment variables
config = {
    "SENDER_MAIL": os.getenv("SENDER_MAIL"),
    "SENDER_PASSWORD": os.getenv("SENDER_PASSWORD"),
    "RECEIVER_MAIL": os.getenv("RECEIVER_MAIL"),
    "MAIL_TRAP": os.getenv("MAIL_TRAP")
}
blog= Blueprint("blog", __name__)
creditor = CKEditor()

# Blog routes are part of Ink Studio's public digital space
# Accessible to ALL logged in users (general accounts), not just authors/writers
# No author/writer profile required - just a regular user account

@blog.route("/blogpost",methods=['GET','POST'])
@login_required
def blogpost():
    """Create a blog post - bloggers and freelancers can create stories"""
    # Only bloggers and freelancers can create stories
    if current_user.role not in ['blogger', 'freelancer']:
        flash('Only users with blogger or freelancer role can create stories. Please contact admin to change your role.', 'error')
        return redirect(url_for('blog.blogs'))
    
    #log_web_visit()
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            author=current_user,
            category=form.category.data if form.category.data else None,
            language=form.language.data if form.language.data else 'en',
            country=form.country.data if form.country.data else None
        )
        db.session.add(post)
        db.session.commit()
        flash("Your post has been created!")
        return redirect(url_for('blog.blogs'))
    return render_template("blogpost.html",title="New Post",form=form)

@blog.errorhandler(401)
def unauthorized(error):
    flash("You are not currently logged in")
    return redirect(url_for('routes1.login'))    

@blog.route("/blogs",methods=['GET','POST'])
def blogs():
    """
    Blog listing - requires login to access
    Part of Ink Studio's digital space for freelance journalists and storytellers
    """
    from sqlalchemy import inspect
    
    #log_web_visit()
    p = request.args.get('page', 1, type=int)
    category = request.args.get('category', None)
    language = request.args.get('language', None)
    country = request.args.get('country', None)
    freelance = request.args.get('freelance', None)  # Filter for freelance journalism stories
    
    # Check if new columns exist in database
    try:
        db.session.rollback()  # Rollback any failed transaction first
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('post')]
        has_metrics_columns = all(col in columns for col in ['likes_count', 'impressions_count'])
        has_filter_columns = all(col in columns for col in ['category', 'language', 'country'])
    except Exception as e:
        logger.error(f"Error checking database columns: {e}")
        has_metrics_columns = False
        has_filter_columns = False
    
    # Build query - handle missing columns gracefully
    try:
        # Use explicit column selection to avoid selecting non-existent columns
        # Never use Post.query directly as it tries to select ALL model columns
        base_columns = [Post.id, Post.title, Post.content, Post.date_posted, Post.user_id]
        
        # Add optional columns if they exist
        if has_filter_columns:
            base_columns.extend([Post.category, Post.language, Post.country])
        
        query = db.session.query(*base_columns)
        
        # Apply filters only if columns exist
        if has_filter_columns:
            if freelance:
                freelance_categories = ['News', 'Features', 'Opinion', 'Investigative', 'Analysis', 'Editorial']
                query = query.filter(Post.category.in_(freelance_categories))
            elif category:
                query = query.filter(Post.category == category)
            
            if language:
                query = query.filter(Post.language == language)
            if country:
                query = query.filter(Post.country.ilike(f'%{country}%'))
        
        # Order by date (newest first)
        query = query.order_by(Post.date_posted.desc())
        
        # Manual pagination (always use this to avoid Post.query issues)
        # Show 6 blogs per page
        per_page = 6
        total = query.count()
        offset = (p - 1) * per_page
        posts_data = query.limit(per_page).offset(offset).all()
        
        # Create SimplePost objects
        class SimplePost:
            def __init__(self, id, title, content, date_posted, user_id, category=None, language=None, country=None):
                self.id = id
                self.title = title
                self.content = content
                self.date_posted = date_posted
                self.user_id = user_id
                self.category = category if has_filter_columns else None
                self.language = language if has_filter_columns else None
                self.country = country if has_filter_columns else None
                self.likes_count = 0
                self.impressions_count = 0
                try:
                    self.author = db.session.get(User, user_id)
                except:
                    self.author = None
        
        # Create pagination object
        class Page:
            def __init__(self, items, page, total, per_page):
                self.items = items
                self.page = page
                self.pages = (total + per_page - 1) // per_page if total > 0 else 1
                self.per_page = per_page
                self.total = total
                self.has_next = offset + per_page < total
                self.has_prev = page > 1
                self.prev_num = page - 1 if page > 1 else None
                self.next_num = page + 1 if offset + per_page < total else None
        
        posts = Page([SimplePost(*post) for post in posts_data], p, total, per_page)
    except Exception as e:
        logger.error(f"Error querying posts: {e}")
        db.session.rollback()
        # Return empty result on error
        class EmptyPage:
            items = []
            page = p
            pages = 1
            per_page = 6
            total = 0
            has_next = False
            has_prev = False
            prev_num = None
            next_num = None
        posts = EmptyPage()
    
    # Load actual metrics from database for all posts
    # Also check which posts the user has liked
    user_liked_posts = set()
    if current_user.is_authenticated:
        try:
            liked_post_ids = db.session.query(PostLike.post_id).filter_by(user_id=current_user.user_id).all()
            user_liked_posts = {post_id[0] for post_id in liked_post_ids}
        except Exception as e:
            logger.error(f"Error fetching user likes: {e}")
            db.session.rollback()
    
    # Get all post IDs to query metrics
    post_ids = [post.id for post in posts.items]
    
    # Load actual likes_count from PostLike table
    if post_ids:
        try:
            from sqlalchemy import func
            likes_counts = db.session.query(
                PostLike.post_id,
                func.count(PostLike.id).label('count')
            ).filter(PostLike.post_id.in_(post_ids)).group_by(PostLike.post_id).all()
            likes_dict = {post_id: count for post_id, count in likes_counts}
        except Exception as e:
            logger.error(f"Error fetching likes counts: {e}")
            db.session.rollback()
            likes_dict = {}
        
        # Load actual impressions_count from PostView table
        try:
            impressions_counts = db.session.query(
                PostView.post_id,
                func.count(PostView.id).label('count')
            ).filter(PostView.post_id.in_(post_ids)).group_by(PostView.post_id).all()
            impressions_dict = {post_id: count for post_id, count in impressions_counts}
        except Exception as e:
            logger.error(f"Error fetching impressions counts: {e}")
            db.session.rollback()
            impressions_dict = {}
    else:
        likes_dict = {}
        impressions_dict = {}
    
    for post in posts.items:
        # Set actual likes_count from database
        post.likes_count = likes_dict.get(post.id, 0)
        # Set actual impressions_count from database
        post.impressions_count = impressions_dict.get(post.id, 0)
        # Add user_liked attribute
        post.user_liked = post.id in user_liked_posts
    
    # Get available filter options for dropdowns - only if columns exist
    available_categories = []
    available_languages = []
    available_countries = []
    
    if has_filter_columns:
        try:
            available_categories = db.session.query(Post.category).distinct().filter(Post.category.isnot(None)).all()
            available_categories = [cat[0] for cat in available_categories if cat[0]]
            
            available_languages = db.session.query(Post.language).distinct().filter(Post.language.isnot(None)).all()
            available_languages = [lang[0] for lang in available_languages if lang[0]]
            
            available_countries = db.session.query(Post.country).distinct().filter(Post.country.isnot(None)).all()
            available_countries = [country[0] for country in available_countries if country[0]]
        except Exception as e:
            logger.error(f"Error fetching filter options: {e}")
            db.session.rollback()
    
    return render_template(
        "blogs.html",
        posts=posts,
        selected_category=category,
        selected_language=language,
        selected_country=country,
        is_freelance_filter=bool(freelance),
        available_categories=available_categories,
        available_languages=available_languages,
        available_countries=available_countries
    )

@blog.route("/post/<int:post_id>")
def update(post_id):
     #log_web_visit()
     post = Post.query.get_or_404(post_id)
     
     # Track impression/view
     track_post_view(post_id)
     
     # Reload the post object to get updated impressions_count from database
     db.session.expire(post)  # Expire the object to force reload
     db.session.refresh(post)  # Reload from database
     
     # Check if current user has liked this post
     user_has_liked = False
     if current_user.is_authenticated:
         user_like = PostLike.query.filter_by(post_id=post_id, user_id=current_user.user_id).first()
         user_has_liked = user_like is not None
     
     return render_template("singlepost.html", title=post.title, post=post, user_has_liked=user_has_liked)

@blog.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    sender = (os.getenv("SENDER_MAIL") or config.get("SENDER_MAIL") or "").strip()
    receiver = (os.getenv("RECEIVER_MAIL") or config.get("RECEIVER_MAIL") or "").strip()
    api_key = (os.getenv("MAIL_TRAP") or config.get("MAIL_TRAP") or "").strip()

    if form.validate_on_submit():
        if not sender or not receiver or not api_key:
            logger.warning(
                "Contact form mail not configured (sender=%s receiver=%s api_key=%s)",
                bool(sender),
                bool(receiver),
                bool(api_key),
            )
            flash(
                "We can’t send messages from the contact form right now. Please try again later.",
                "error",
            )
            return render_template("contact.html", form=form)

        try:
            mail = Mail(
                sender=Address(email=sender, name="Message form GLC user"),
                to=[Address(email=receiver)],
                subject="New Contact Form Submission",
                text=(
                    f"First name: {form.FirstName.data}\n"
                    f"Last name: {form.LastName.data}\n"
                    f"Email: {form.email.data}\n"
                    f"Message: {form.message.data}"
                ),
                category="User Contact",
            )
            MailtrapClient(token=api_key).send(mail)
        except Exception:
            logger.exception("Contact form Mailtrap send failed")
            flash(
                "We couldn’t send your message. Please try again in a moment.",
                "error",
            )
            return render_template("contact.html", form=form)

        flash("Thank you for reaching out. We will get back to you ASAP.", "success")
        return redirect(url_for("blog.contact"))

    return render_template("contact.html", form=form)

def _clear_auth_cookies(response):
    """Delete session cookies with the same flags Flask used when setting them."""
    cookie_name = current_app.config.get('SESSION_COOKIE_NAME', 'session')
    cookie_path = current_app.config.get('SESSION_COOKIE_PATH') or '/'
    cookie_domain = current_app.config.get('SESSION_COOKIE_DOMAIN')
    cookie_secure = bool(current_app.config.get('SESSION_COOKIE_SECURE', False))
    cookie_httponly = bool(current_app.config.get('SESSION_COOKIE_HTTPONLY', True))
    cookie_samesite = current_app.config.get('SESSION_COOKIE_SAMESITE') or 'Lax'

    response.delete_cookie(
        cookie_name,
        path=cookie_path,
        domain=cookie_domain,
        secure=cookie_secure,
        httponly=cookie_httponly,
        samesite=cookie_samesite,
    )
    remember_name = current_app.config.get('REMEMBER_COOKIE_NAME', 'remember_token')
    response.delete_cookie(
        remember_name,
        path=current_app.config.get('REMEMBER_COOKIE_PATH', cookie_path),
        domain=current_app.config.get('REMEMBER_COOKIE_DOMAIN', cookie_domain),
        secure=bool(current_app.config.get('REMEMBER_COOKIE_SECURE', cookie_secure)),
        httponly=bool(current_app.config.get('REMEMBER_COOKIE_HTTPONLY', True)),
        samesite=current_app.config.get('REMEMBER_COOKIE_SAMESITE', cookie_samesite),
    )
    return response


@blog.route('/logout', methods=['GET', 'POST'])
def logout():
    """Always clear server session and auth cookies, then send user to login."""
    if current_user.is_authenticated:
        logout_user()
    session.clear()

    response = redirect(url_for('routes1.login'))
    _clear_auth_cookies(response)

    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    flash("You are logged out", 'success')
    return response

@blog.route('/curr')
@login_required
def curr_user():
    return 'current user is '+current_user.username


@blog.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update2(post_id):
    #log_web_visit()
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    
    form = PostForm()
    if form.validate_on_submit():  
        post.title = form.title.data
        post.content = form.content.data
        post.category = form.category.data if form.category.data else None
        post.language = form.language.data if form.language.data else 'en'
        post.country = form.country.data if form.country.data else None
        db.session.commit()
        flash("Blog has been updated!")
        return redirect(url_for("blog.blogs", post_id=post.id))  
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.category.data = post.category or ''
        form.language.data = post.language or 'en'
        form.country.data = post.country or ''
    return render_template("blogpost.html", title="Update Post", form=form, legend="Update your blog")

@blog.route("/post/<int:post_id>/delete", methods=['GET', 'POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
         abort(403)
    db.session.delete(post)
    db.session.commit() 
    flash(" You blog post has been deleted!")
    return redirect(url_for("blog.blogs"))

# Define the UPLOAD_FOLDER and ensure it exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'glconnect', 'static', 'uploads')
# Route to serve uploaded files
@blog.route('/files/<path:filename>')
def files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@blog.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('upload')

    if f:
        # Check file type (you can add more allowed extensions as needed)
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif',"docx"}
        file_extension = f.filename.rsplit('.', 1)[-1].lower()

        if file_extension not in allowed_extensions:
            return upload_fail(message='Invalid file type. Only image files are allowed.')

        # Define file path
        file_path = os.path.join(UPLOAD_FOLDER, f.filename)

        # Save the file
        f.save(file_path)

        # Generate URL for the uploaded file
        url = url_for('blog.files', filename=f.filename)

        # Return the success response
        return upload_success(url, filename=f.filename) 
    
    return upload_fail(message='No file uploaded', filename=None)


@blog.route("/play-audio/<int:post_id>")
def play_audio(post_id):
    post = Post.query.get_or_404(post_id)
    text = post.content  # Blog post content

    # Generate the audio file
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    # Ensure the 'audio' directory exists
    audio_dir = os.path.join(current_app.root_path, 'static', 'audio')
    if not os.path.exists(audio_dir):
        os.makedirs(audio_dir)

    # Create a file path to save the audio
    audio_path = os.path.join(audio_dir, f"post_{post_id}.mp3")

    # If the audio response is a generator, we need to get the content properly
    with open(audio_path, "wb") as f:
        # Assuming `audio` is a generator, you need to iterate through it or process it
        for chunk in audio:
            f.write(chunk)  # Write each chunk to the file

    # Return the audio file as a response
    return send_file(audio_path, mimetype="audio/mp3")

# Translation functionality using Gemini
def get_gemini_model():
    """Get configured Gemini model for translation"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        print(f"Error initializing Gemini: {e}")
        return None

# Language code to name mapping
LANGUAGE_NAMES = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese',
    'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
    'sw': 'Swahili', 'rw': 'Kinyarwanda', 'nl': 'Dutch', 'pl': 'Polish',
    'tr': 'Turkish', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian',
    'cs': 'Czech', 'sv': 'Swedish', 'da': 'Danish', 'fi': 'Finnish',
    'no': 'Norwegian', 'he': 'Hebrew', 'uk': 'Ukrainian', 'ro': 'Romanian',
    'hu': 'Hungarian', 'el': 'Greek', 'bg': 'Bulgarian', 'hr': 'Croatian',
    'sk': 'Slovak', 'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian',
    'lt': 'Lithuanian', 'mt': 'Maltese', 'ga': 'Irish', 'cy': 'Welsh'
}

@blog.route("/post/<int:post_id>/translate", methods=['POST'])
def translate_post(post_id):
    """Translate a blog post to a target language using Gemini"""
    try:
        post = Post.query.get_or_404(post_id)
        data = request.get_json()
        target_language = data.get('target_language')
        
        if not target_language:
            return jsonify({'success': False, 'error': 'Target language is required'}), 400
        
        # Check if translation already exists
        existing_translation = StoryTranslation.query.filter_by(
            post_id=post_id,
            language=target_language
        ).first()
        
        if existing_translation:
            return jsonify({
                'success': True,
                'translated_title': existing_translation.translated_title,
                'translated_content': existing_translation.translated_content,
                'language': existing_translation.language,
                'cached': True
            })
        
        # Get Gemini model
        model = get_gemini_model()
        if not model:
            return jsonify({'success': False, 'error': 'Translation service not available'}), 500
        
        # Get source and target language names
        source_lang_name = LANGUAGE_NAMES.get(post.language or 'en', 'English')
        target_lang_name = LANGUAGE_NAMES.get(target_language, target_language)
        
        # Create translation prompt
        translation_prompt = f"""Translate the following blog post from {source_lang_name} to {target_lang_name}. 
Maintain the original formatting, tone, and style. Preserve any HTML tags if present.

Title: {post.title}

Content:
{post.content}

Please provide the translation in the following JSON format:
{{
    "translated_title": "translated title here",
    "translated_content": "translated content here"
}}"""
        
        # Generate translation
        response = model.generate_content(
            translation_prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8000,
                temperature=0.3,  # Lower temperature for more accurate translations
                top_p=0.8,
                top_k=40
            )
        )
        
        if not response.parts or len(response.parts) == 0:
            return jsonify({'success': False, 'error': 'Translation failed - no response from AI'}), 500
        
        translated_text = response.text.strip()
        
        # Try to parse JSON response
        try:
            # Extract JSON from response (in case there's extra text)
            import re
            json_match = re.search(r'\{.*\}', translated_text, re.DOTALL)
            if json_match:
                translation_data = json.loads(json_match.group())
            else:
                # If no JSON found, treat entire response as content
                translation_data = {
                    'translated_title': post.title,  # Fallback
                    'translated_content': translated_text
                }
        except json.JSONDecodeError:
            # If JSON parsing fails, split response into title and content
            lines = translated_text.split('\n', 1)
            translation_data = {
                'translated_title': lines[0] if lines else post.title,
                'translated_content': lines[1] if len(lines) > 1 else translated_text
            }
        
        translated_title = translation_data.get('translated_title', post.title)
        translated_content = translation_data.get('translated_content', translated_text)
        
        # Save translation to database
        translation = StoryTranslation(
            post_id=post_id,
            language=target_language,
            translated_title=translated_title,
            translated_content=translated_content,
            translation_method='gemini'
        )
        db.session.add(translation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'translated_title': translated_title,
            'translated_content': translated_content,
            'language': target_language,
            'cached': False
        })
        
    except Exception as e:
        print(f"Translation error: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@blog.route("/post/<int:post_id>/translations")
def get_post_translations(post_id):
    """Get all available translations for a post"""
    post = Post.query.get_or_404(post_id)
    translations = StoryTranslation.query.filter_by(post_id=post_id).all()
    
    return jsonify({
        'success': True,
        'original_language': post.language or 'en',
        'translations': [
            {
                'id': t.id,
                'language': t.language,
                'language_name': LANGUAGE_NAMES.get(t.language, t.language),
                'translated_title': t.translated_title,
                'translated_at': t.translated_at.isoformat() if t.translated_at else None
            }
            for t in translations
        ]
    })

# Helper function to track post views/impressions
def track_post_view(post_id):
    """Track a view/impression for a post"""
    try:
        post = Post.query.get(post_id)
        if not post:
            return
        
        # Get user ID if authenticated
        user_id = current_user.user_id if current_user.is_authenticated else None
        
        # Get IP address and session ID for anonymous tracking
        ip_address = request.remote_addr
        session_id = session.get('session_id', None)
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Check if this is a unique view
        # For logged in users: check by user_id
        if user_id:
            existing_view = PostView.query.filter_by(
                post_id=post_id,
                user_id=user_id
            ).first()
        else:
            # For anonymous: check by IP and session within last 24 hours
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            existing_view = PostView.query.filter(
                PostView.post_id == post_id,
                PostView.ip_address == ip_address,
                PostView.session_id == session_id,
                PostView.viewed_at >= yesterday
            ).first()
        
        # Only count as new impression if unique
        if not existing_view:
            new_view = PostView(
                post_id=post_id,
                user_id=user_id,
                ip_address=ip_address,
                session_id=session_id
            )
            db.session.add(new_view)
            db.session.flush()  # Flush to get the new view in the session before counting
            
            # Update post impressions count - count all views for this post
            actual_count = db.session.query(func.count(PostView.id)).filter_by(post_id=post_id).scalar()
            post.impressions_count = actual_count
            
            db.session.commit()
            
            logger.info(f"Tracked view for post {post_id}: impressions_count = {actual_count}")
            
            # Emit Real time update via WebSocket if available
            try:
                from glconnect.book_platform_integration import socketio
                if socketio:
                    socketio.emit('post_metrics_update', {
                        'post_id': post_id,
                        'impressions_count': post.impressions_count,
                        'likes_count': post.likes_count
                    }, namespace='/', broadcast=True)
            except:
                pass  # WebSocket not available, continue silently
        else:
            # Even if view already exists, refresh the count to ensure accuracy
            actual_count = db.session.query(func.count(PostView.id)).filter_by(post_id=post_id).scalar()
            if post.impressions_count != actual_count:
                post.impressions_count = actual_count
                db.session.commit()
                logger.info(f"Updated impressions_count for post {post_id}: {actual_count}")
                
    except Exception as e:
        logger.error(f"Error tracking post view: {e}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

@blog.route("/post/<int:post_id>/like", methods=['POST'])
@login_required
def like_post(post_id):
    """Like or unlike a post - ensures only one like per user per post"""
    try:
        post = Post.query.get_or_404(post_id)
        
        # Check if user already liked this post (with explicit lock to prevent race conditions)
        existing_like = PostLike.query.filter_by(
            post_id=post_id,
            user_id=current_user.user_id
        ).first()
        
        if existing_like:
            # Unlike: remove the like
            db.session.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            action = 'unliked'
            user_has_liked = False
        else:
            # Double check to prevent race conditions (check again before adding)
            duplicate_check = PostLike.query.filter_by(
                post_id=post_id,
                user_id=current_user.user_id
            ).first()
            
            if duplicate_check:
                # Another request already added the like, just return current state
                post.likes_count = PostLike.query.filter_by(post_id=post_id).count()
                action = 'liked'
                user_has_liked = True
            else:
                # Like: add the like
                new_like = PostLike(
                    post_id=post_id,
                    user_id=current_user.user_id
                )
                db.session.add(new_like)
                post.likes_count = post.likes_count + 1
                action = 'liked'
                user_has_liked = True
        
        try:
            db.session.commit()
        except Exception as commit_error:
            # Handle unique constraint violation (race condition)
            db.session.rollback()
            # Re-query to get actual state
            existing_like_check = PostLike.query.filter_by(
                post_id=post_id,
                user_id=current_user.user_id
            ).first()
            
            if existing_like_check:
                # Like already exists, return current state
                post.likes_count = PostLike.query.filter_by(post_id=post_id).count()
                action = 'liked'
                user_has_liked = True
            else:
                # Like doesn't exist, try again
                new_like = PostLike(
                    post_id=post_id,
                    user_id=current_user.user_id
                )
                db.session.add(new_like)
                post.likes_count = PostLike.query.filter_by(post_id=post_id).count() + 1
                db.session.commit()
                action = 'liked'
                user_has_liked = True
        
        # Refresh likes count from database to ensure accuracy
        actual_likes_count = PostLike.query.filter_by(post_id=post_id).count()
        post.likes_count = actual_likes_count
        db.session.commit()
        
        # Emit Real time update via WebSocket if available
        try:
            from glconnect.book_platform_integration import socketio
            if socketio:
                socketio.emit('post_metrics_update', {
                    'post_id': post_id,
                    'impressions_count': post.impressions_count,
                    'likes_count': post.likes_count
                }, namespace='/', broadcast=True)
        except:
            pass
        
        return jsonify({
            'success': True,
            'action': action,
            'likes_count': post.likes_count,
            'user_has_liked': user_has_liked
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error liking post {post_id}: {e}")
        # Return current state even on error
        try:
            existing_like = PostLike.query.filter_by(
                post_id=post_id,
                user_id=current_user.user_id
            ).first()
            actual_likes_count = PostLike.query.filter_by(post_id=post_id).count()
            return jsonify({
                'success': False,
                'error': str(e),
                'likes_count': actual_likes_count,
                'user_has_liked': existing_like is not None
            }), 500
        except:
            return jsonify({'success': False, 'error': str(e)}), 500

@blog.route("/post/<int:post_id>/metrics")
def get_post_metrics(post_id):
    """Get current metrics for a post (for Real time updates)"""
    try:
        post = Post.query.get_or_404(post_id)
        
        # Check if user has liked
        user_has_liked = False
        if current_user.is_authenticated:
            user_like = PostLike.query.filter_by(post_id=post_id, user_id=current_user.user_id).first()
            user_has_liked = user_like is not None
        
        return jsonify({
            'success': True,
            'post_id': post_id,
            'likes_count': post.likes_count,
            'impressions_count': post.impressions_count,
            'user_has_liked': user_has_liked
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500