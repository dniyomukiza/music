from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, JSON
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

# Initialize the database instance
db = SQLAlchemy()

class Song(db.Model):
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=True)
    local_path = db.Column(db.String(200), nullable=True)
    spotify_id = db.Column(db.String(100), nullable=True)
    is_available_on_spotify = db.Column(db.Boolean, default=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.artist_id'), nullable=True)
    cover_image = db.Column(db.String(200), nullable=True)
    

class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    # New fields for filtering and translation
    category = db.Column(db.String(100), nullable=True)  # e.g., News, Features, Opinion, Investigative
    language = db.Column(db.String(50), nullable=True, default='en')  # ISO language code (en, es, fr, etc.)
    country = db.Column(db.String(100), nullable=True)  # Country name or code
    # Metrics for freelancer awards
    likes_count = db.Column(db.Integer, default=0, nullable=False)  # Total number of likes
    impressions_count = db.Column(db.Integer, default=0, nullable=False)  # Total number of views/impressions
    # Relationships
    translations = db.relationship('StoryTranslation', backref='original_post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('PostLike', backref='post', lazy=True, cascade='all, delete-orphan')
    views = db.relationship('PostView', backref='post', lazy=True, cascade='all, delete-orphan')

class StoryTranslation(db.Model):
    """Store translated versions of blog posts/stories"""
    __tablename__ = 'story_translations'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    language = db.Column(db.String(50), nullable=False)  # Target language code (e.g., 'es', 'fr', 'de')
    translated_title = db.Column(db.String(255), nullable=False)
    translated_content = db.Column(db.Text, nullable=False)
    translated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    translation_method = db.Column(db.String(50), default='gemini')  # 'gemini', 'manual', etc.
    
    # Index for faster lookups
    __table_args__ = (db.Index('idx_post_language', 'post_id', 'language'),)

class PostLike(db.Model):
    """Track user likes on blog posts/stories"""
    __tablename__ = 'post_likes'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    liked_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Ensure one like per user per post
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id', name='unique_post_like'),)
    
    # Relationships
    user = db.relationship('User', backref='post_likes')

class PostView(db.Model):
    """Track unique impressions/views on blog posts/stories"""
    __tablename__ = 'post_views'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=True)  # Nullable for anonymous views
    ip_address = db.Column(db.String(45), nullable=True)  # Store IP for anonymous tracking
    viewed_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    session_id = db.Column(db.String(255), nullable=True)  # Track by session for better uniqueness
    
    # Index for faster lookups and uniqueness checks
    __table_args__ = (
        db.Index('idx_post_user_view', 'post_id', 'user_id'),
        db.Index('idx_post_ip_view', 'post_id', 'ip_address'),
        db.Index('idx_post_session_view', 'post_id', 'session_id'),
    )

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(50), nullable=False, default='other') 
    posts = db.relationship('Post', backref='author', lazy=True, foreign_keys='Post.user_id')


    def get_id(self):
     return str(self.user_id)

    def set_password(self, password):
        # Hash the password before saving it
        self.password = generate_password_hash(password)

    def check_password(self, password):
        # Compare the hashed password with the provided password
        return check_password_hash(self.password, password)

class WordsData(db.Model):
    __tablename__ = 'words_data'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String)
    umuzi_root = db.Column(db.String)
    basoma_phonetics = db.Column(JSON)
    bandika_writing = db.Column(db.String)
    icyiciro_pos = db.Column(JSON)
    igisobanuro_meaning = db.Column(JSON)


class SlangWords(db.Model):
    __tablename__ = 'slang'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slang = Column(String, nullable=False, unique=True) 
    original= Column(String, nullable=False)  
    current= Column(String, nullable=False)   
    example = Column(String, nullable=False)       
    created_by = Column(String, nullable=True)      
    created_at = Column(String, nullable=False)
    approved = Column(Integer, default=0)

class WordContribution(db.Model):
    __tablename__ = 'word_contributions'
    
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.Text, nullable=False)
    example_sentence = db.Column(db.Text, nullable=True)
    part_of_speech = db.Column(db.String(50), nullable=True)
    phonetics = db.Column(db.String(100), nullable=True)
    contributor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    contributor_name = db.Column(db.String(100), nullable=True)  # For anonymous contributions
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    
    # Relationships
    contributor = db.relationship('User', foreign_keys=[contributor_id], backref='word_contributions')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_contributions') 
       
class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    added_on = db.Column(db.DateTime, default=db.func.now())

class Artist(db.Model):
    __tablename__ = 'artists'
    
    artist_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True, nullable=True)
    artist_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_pic= db.Column(db.String(200), nullable=True, default="static/uploads/default.jpg")
    user = db.relationship("User", backref=db.backref("artist_profile", uselist=False))

    def __repr__(self):
        return f"<Artist {self.artist_name}>"

class Writer(db.Model):
    __tablename__ = 'writers'
    
    writer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=True)  # Allow multiple writers for the same user
    writer_name = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True, default="static/uploads/default_writer.jpg")

    user = db.relationship("User", backref=db.backref("writer_profiles", lazy=True))  # One-to-many relationship with User

    def __repr__(self):
        return f"<Writer {self.writer_name}>"

class Book(db.Model):
    __tablename__ = 'books'

    book_id = db.Column(db.Integer, primary_key=True)
    writer_id = db.Column(db.Integer, db.ForeignKey('writers.writer_id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    publication_year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    purchase_link = db.Column(db.String(300), nullable=True)
    cover_image = db.Column(db.String(200), nullable=True, default="static/uploads/default_cover.jpg")

    writer = db.relationship("Writer", backref=db.backref("books", lazy=True, cascade='all, delete-orphan'))

    def __repr__(self):
        return f"<Book {self.title} by {self.writer.writer_name}>"

class Song_upload(db.Model):
    __tablename__ = 'song_upload'
    upload_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name_song = db.Column(db.String(100), nullable=False)
    name_artist = db.Column(db.String(100), nullable=True)
    local_path = db.Column(db.String(200), nullable=True)
    cover_image = db.Column(db.String(200), nullable=True)
    twitter_link = db.Column(db.String(255), nullable=True)
    instagram_link = db.Column(db.String(255), nullable=True)
    spotify_link = db.Column(db.String(255), nullable=True)
    apple_music_link = db.Column(db.String(255), nullable=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.artist_id'), nullable=True)
    artist = db.relationship('Artist', backref='songs')

class PictureGameItem(db.Model):
    __tablename__ = 'picture_game_items'
    
    id = db.Column(db.Integer, primary_key=True)
    kinyarwanda_word = db.Column(db.String(255), nullable=False)
    english_meaning = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(500), nullable=False)  # Path to image in static/pictures/
    word_id = db.Column(db.Integer, db.ForeignKey('words_data.id'), nullable=True)  # Link to words_data table
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    used_count = db.Column(db.Integer, default=0)  # Track how many times this item has been used
    is_active = db.Column(db.Boolean, default=True)  # For soft deletion
    last_used = db.Column(db.DateTime, nullable=True)  # Track when it was last used in a game
    
    # Enhanced fields for text-to-image with interleaved text
    image_type = db.Column(db.String(50), default='text_overlay')  # 'text_overlay', 'simple', 'enhanced'
    pronunciation_guide = db.Column(db.String(255), nullable=True)  # Optional pronunciation hint
    context_hint = db.Column(db.Text, nullable=True)  # Optional context or usage hint
    text_overlay_data = db.Column(db.Text, nullable=True)  # JSON data about text positioning and styling
    generation_prompt = db.Column(db.Text, nullable=True)  # Store the prompt used for generation
    
    # Relationship to words_data table
    word_data = db.relationship('WordsData', backref='picture_game_items')

# Analytics Models for persistent data storage
class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD format
    category = db.Column(db.String(100), nullable=True)
    confidence = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class CategoryCount(db.Model):
    __tablename__ = 'category_counts'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False, unique=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class TopicCount(db.Model):
    __tablename__ = 'topic_counts'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False, unique=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class DailySearchCount(db.Model):
    __tablename__ = 'daily_search_counts'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), nullable=False, unique=True)  # YYYY-MM-DD format
    count = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class CategoryTopic(db.Model):
    __tablename__ = 'category_topics'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Ensure unique combination of category and topic
    __table_args__ = (db.UniqueConstraint('category', 'topic', name='unique_category_topic'),)

class CategorizationConfidence(db.Model):
    __tablename__ = 'categorization_confidence'
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

# Task persistence model for news generation
class NewsTask(db.Model):
    __tablename__ = 'news_tasks'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(36), nullable=False, unique=True)  # UUID
    status = db.Column(db.String(20), nullable=False, default='running')  # running, completed, failed
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime, nullable=True)
    failed_at = db.Column(db.DateTime, nullable=True)
    last_heartbeat = db.Column(db.DateTime, nullable=True)
    progress = db.Column(db.Integer, nullable=True, default=0)  # 0-100
    current_step = db.Column(db.String(255), nullable=True)
    topics = db.Column(db.Text, nullable=True)  # JSON string of topics
    result = db.Column(db.Text, nullable=True)  # JSON string of result
    error = db.Column(db.Text, nullable=True)  # Error message if failed
    generation_time = db.Column(db.Float, nullable=True)  # Time taken in seconds
    memory_usage = db.Column(db.Text, nullable=True)  # JSON string of memory info
    topics_processed = db.Column(db.Text, nullable=True)  # JSON string of processed topics

class PageAnalytics(db.Model):
    __tablename__ = 'page_analytics'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False)  # The URL path accessed
    method = db.Column(db.String(10), nullable=False)  # GET, POST, etc.
    ip_address = db.Column(db.String(50), nullable=True)
    browser = db.Column(db.String(50), nullable=True)
    device = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)
    is_authenticated = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    referer = db.Column(db.String(500), nullable=True)
    
    # Relationship
    user = db.relationship('User', backref='page_views')

class PageAnalyticsStats(db.Model):
    __tablename__ = 'page_analytics_stats'
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(500), nullable=False)
    total_views = db.Column(db.Integer, default=0)
    unique_visitors = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    __table_args__ = (db.UniqueConstraint('path', name='unique_path'),)
