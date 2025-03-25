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
    

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

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


    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

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
       
class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    added_on = db.Column(db.DateTime, default=db.func.now())
