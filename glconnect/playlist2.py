from flask import Blueprint, request, jsonify, send_from_directory, send_file, current_app
from flask_login import current_user, login_required
from glconnect.models import Song, Playlist, db, Artist, Song_upload, DownloadedSong
import os

play = Blueprint('playlist2', __name__)

# Only list songs that are approved (or legacy null); hide pending/rejected from search and playlists
def _approved_songs_filter():
    return db.or_(Song.approval_status.is_(None), Song.approval_status == 'approved')

from flask import url_for

def check_song_file_exists(song):
    """
    Check if a song file actually exists on disk using the centralized logic.
    """
    return _get_song_file_path(song) is not None

def get_all_songs_by_artist(artist_id=None, artist_name=None, include_collaborations=False):
    """
    Get all songs by an artist from Song model (playlist-compatible songs).
    Note: Song_upload songs are not included as they can't be added to playlists directly.
    Returns a list of song dictionaries with id, name, and artist fields.
    
    Args:
        artist_id: Artist ID to search for
        artist_name: Artist name to search for
        include_collaborations: If True, also include songs where artist appears in collaborations (ft, featuring, etc.)
    """
    songs_data = []
    seen_song_ids = set()
    seen_song_keys = set()
    
    # Get the artist name if we have artist_id
    if artist_id and not artist_name:
        artist_obj = Artist.query.get(artist_id)
        if artist_obj:
            artist_name = artist_obj.artist_name
    
    # Get songs from Song model where artist_id matches (only approved songs)
    if artist_id:
        songs_from_song_model = Song.query.filter_by(artist_id=artist_id).filter(_approved_songs_filter()).all()
    elif artist_name:
        # Try to find artist by name first
        artist = Artist.query.filter(db.func.lower(Artist.artist_name) == artist_name.lower()).first()
        if artist:
            songs_from_song_model = Song.query.filter_by(artist_id=artist.artist_id).filter(_approved_songs_filter()).all()
        else:
            # Fallback: search by artist field in Song model
            songs_from_song_model = Song.query.filter(db.func.lower(Song.artist) == artist_name.lower()).filter(_approved_songs_filter()).all()
    else:
        songs_from_song_model = []
    
    # If include_collaborations is True, also search for songs where artist name appears in the artist field
    if include_collaborations and artist_name:
        # Search for songs where artist name appears anywhere in the artist field (for collaborations)
        collaboration_songs = Song.query.filter(
            db.func.lower(Song.artist).like(f'%{artist_name.lower()}%')
        ).filter(_approved_songs_filter()).all()
        
        # Combine both lists, avoiding duplicates
        all_songs = list(songs_from_song_model)
        for collab_song in collaboration_songs:
            if collab_song not in all_songs:
                all_songs.append(collab_song)
        songs_from_song_model = all_songs
    
    # Process songs from Song model (only these can be added to playlists)
    import re
    for song in songs_from_song_model:
        # Skip if we've already processed this song ID
        if song.id in seen_song_ids:
            continue
        
        artist_name_display = song.artist if song.artist else 'Unknown'
        if not artist_name_display or artist_name_display == 'Unknown':
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj:
                    artist_name_display = artist_obj.artist_name
        
        # Clean song name - handle cases where song.name contains "by [artist]" pattern
        song_name = song.name.strip() if song.name and song.name.strip() else ''
        
        # Check if song name contains "by [artist]" pattern (e.g., "by P.Square")
        by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
        if by_pattern.match(song_name):
            # Extract artist from song name if artist field is empty
            extracted_artist = by_pattern.match(song_name).group(1).strip()
            if not artist_name_display or artist_name_display == 'Unknown':
                artist_name_display = extracted_artist
            song_name = ''  # Clear it since it's not actually the song name
        
        # Final song name
        if not song_name:
            song_name = 'Untitled Track'
        
        # Deduplicate by name+artist combination
        song_key = f"{song_name.lower()}|{artist_name_display.lower()}"
        if song_key in seen_song_keys:
            continue
        
        # Check if song file actually exists before including it
        if not check_song_file_exists(song):
            continue  # Skip songs without playable files
        
        # Use the file serving route for reliable file access
        # This route handles all path resolution logic from the database
        from flask import url_for
        song_path = url_for('playlist2.serve_song_file', song_id=song.id)
        
        # Get artist profile picture if available
        artist_profile_pic = None
        if song.artist_id:
            artist_obj = Artist.query.get(song.artist_id)
            if artist_obj and artist_obj.profile_pic:
                # Handle path format: static/uploads/picname.jpg or just picname.jpg
                profile_pic_path = artist_obj.profile_pic
                if profile_pic_path.startswith('static/'):
                    artist_profile_pic = profile_pic_path.replace('static/', '')
                else:
                    artist_profile_pic = profile_pic_path
        
        # Get song cover image if available
        song_cover_image = None
        if song.cover_image:
            song_cover_image = song.cover_image
        
        seen_song_ids.add(song.id)
        seen_song_keys.add(song_key)
        songs_data.append({
            'id': song.id,
            'song_id': song.id,
            'download_id': None,
            'name': song_name,
            'artist': artist_name_display,
            'path': song_path,
            'cover_image': song_cover_image,
            'artist_profile_pic': artist_profile_pic
        })
    # Include YouTube-downloaded songs by same artist name (from downloaded_songs table)
    if artist_name:
        from flask import url_for
        downloads = DownloadedSong.query.filter(db.func.lower(DownloadedSong.artist) == artist_name.lower()).all()
        for d in downloads:
            song_key = f"{(d.name or '').strip().lower()}|{(d.artist or '').strip().lower()}"
            if song_key in seen_song_keys:
                continue
            seen_song_keys.add(song_key)
            name = (d.name or '').strip() or 'Untitled Track'
            artist = d.artist or 'Unknown'
            path = url_for('playlist2.serve_downloaded_song_file', download_id=d.id)
            songs_data.append({
                'id': d.id,
                'song_id': None,
                'download_id': d.id,
                'name': name,
                'artist': artist,
                'path': path,
                'cover_image': None,
                'artist_profile_pic': None
            })
    return songs_data

# In your route for fetching songs
@play.route('/playlist2', methods=['GET'])
def playlist2():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])

    # Track seen song IDs and name+artist combinations to prevent duplicates
    seen_song_ids = set()
    seen_song_keys = set()  # Track normalized name+artist combinations
    all_songs_data = []

    def add_song_if_unique(song_data):
        """Helper to add song only if we haven't seen this song ID or name+artist combination before"""
        song_id = song_data['id']
        song_name = (song_data.get('name') or '').strip().lower()
        artist_name = (song_data.get('artist') or '').strip().lower()
        song_key = f"{song_name}|{artist_name}"
        if song_id in seen_song_ids or song_key in seen_song_keys:
            return
        seen_song_ids.add(song_id)
        seen_song_keys.add(song_key)
        all_songs_data.append(song_data)

    # Include YouTube-downloaded songs matching the query (from downloaded_songs table)
    _downloads = DownloadedSong.query.filter(
        db.or_(
            db.func.lower(DownloadedSong.name).like(f'%{query}%'),
            db.func.lower(DownloadedSong.artist).like(f'%{query}%')
        )
    ).limit(20).all()
    for d in _downloads:
        name = (d.name or '').strip() or 'Untitled Track'
        artist = d.artist or 'Unknown'
        add_song_if_unique({
            'id': 2000000 + d.id,
            'song_id': None,
            'download_id': d.id,
            'name': name,
            'artist': artist,
            'path': url_for('playlist2.serve_downloaded_song_file', download_id=d.id),
            'cover_image': None,
            'artist_profile_pic': None
        })

    # 1. Exact match for artist (case-insensitive) - return all songs by that artist
    artist = Artist.query.filter(db.func.lower(Artist.artist_name) == query).first()
    if artist:
        songs_data = get_all_songs_by_artist(artist_id=artist.artist_id, artist_name=artist.artist_name, include_collaborations=True)
        if songs_data:
            for song_data in songs_data:
                add_song_if_unique(song_data)
            if all_songs_data:
                return jsonify(all_songs_data)
        # If no songs found by artist_id, also search Song.artist field for this exact name
        songs_by_name = Song.query.filter(db.func.lower(Song.artist) == query.lower()).filter(_approved_songs_filter()).all()
        if songs_by_name:
            import re
            for song in songs_by_name:
                artist_name = song.artist if song.artist else 'Unknown'
                song_name = song.name.strip() if song.name and song.name.strip() else ''
                
                by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
                if by_pattern.match(song_name):
                    extracted_artist = by_pattern.match(song_name).group(1).strip()
                    if not artist_name or artist_name == 'Unknown':
                        artist_name = extracted_artist
                    song_name = ''
                
                if not song_name:
                    song_name = 'Untitled Track'
                
                if not check_song_file_exists(song):
                    continue
                
                from flask import url_for
                song_path = url_for('playlist2.serve_song_file', song_id=song.id)
                
                # Get artist profile picture if available
                artist_profile_pic = None
                if song.artist_id:
                    artist_obj = Artist.query.get(song.artist_id)
                    if artist_obj and artist_obj.profile_pic:
                        profile_pic_path = artist_obj.profile_pic
                        if profile_pic_path.startswith('static/'):
                            artist_profile_pic = profile_pic_path.replace('static/', '')
                        else:
                            artist_profile_pic = profile_pic_path
                
                # Get song cover image if available
                song_cover_image = song.cover_image if song.cover_image else None
                
                song_data = {
                    'id': song.id,
                    'song_id': song.id,
                    'download_id': None,
                    'name': song_name,
                    'artist': artist_name,
                    'path': song_path,
                    'cover_image': song_cover_image,
                    'artist_profile_pic': artist_profile_pic
                }
                add_song_if_unique(song_data)
            
            if all_songs_data:
                return jsonify(all_songs_data)
        # If no songs found, continue to other search methods

    # 2. Search for songs matching the query (partial match for song name)
    songs = Song.query.filter(db.func.lower(Song.name).like(f'%{query}%')).filter(_approved_songs_filter()).limit(20).all()
    
    if songs:
        # If we found songs, get the artist from the first song and return ALL songs by that artist
        first_song = songs[0]
        artist_id = first_song.artist_id
        artist_name = first_song.artist
        
        # Get artist name if we have artist_id
        if artist_id:
            artist_obj = Artist.query.get(artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # If we don't have artist_name yet, try to get it from the song
        if not artist_name or artist_name == 'Unknown':
            artist_name = first_song.artist if first_song.artist else None
        
        # Get all songs by this artist
        if artist_id or artist_name:
            songs_data = get_all_songs_by_artist(artist_id=artist_id, artist_name=artist_name)
            if songs_data:
                for song_data in songs_data:
                    add_song_if_unique(song_data)
                if all_songs_data:
                    return jsonify(all_songs_data)
        
        # Fallback: return the songs we found (original behavior)
        import re
        for song in songs:
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            
            # Clean song name - handle cases where song.name contains "by [artist]" pattern
            song_name = song.name.strip() if song.name and song.name.strip() else ''
            
            # Check if song name contains "by [artist]" pattern (e.g., "by P.Square")
            by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
            if by_pattern.match(song_name):
                # Extract artist from song name if artist field is empty
                extracted_artist = by_pattern.match(song_name).group(1).strip()
                if not artist_name or artist_name == 'Unknown':
                    artist_name = extracted_artist
                song_name = ''  # Clear it since it's not actually the song name
            
            # Final song name
            if not song_name:
                song_name = 'Untitled Track'
            
            # Check if song file actually exists before including it
            if not check_song_file_exists(song):
                continue  # Skip songs without playable files
            
            # Use the file serving route for reliable file access
            from flask import url_for
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            
            # Get artist profile picture if available
            artist_profile_pic = None
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj and artist_obj.profile_pic:
                    profile_pic_path = artist_obj.profile_pic
                    if profile_pic_path.startswith('static/'):
                        artist_profile_pic = profile_pic_path.replace('static/', '')
                    else:
                        artist_profile_pic = profile_pic_path
            
            # Get song cover image if available
            song_cover_image = song.cover_image if song.cover_image else None
            
            song_data = {
                'id': song.id,
                'song_id': song.id,
                'download_id': None,
                'name': song_name,
                'artist': artist_name,
                'path': song_path,
                'cover_image': song_cover_image,
                'artist_profile_pic': artist_profile_pic
            }
            add_song_if_unique(song_data)
        
        if all_songs_data:
            return jsonify(all_songs_data)
    
    # 3. Search Song.artist field directly (for collaborations like "Artist ft Diamond Platnumz")
    # This catches all songs where the artist field contains the query, even if not in Artist table
    # Also handle cases where query might have extra words - search for all words in query
    query_words = query.split()
    songs_by_artist_field = []
    
    # First try exact match
    songs_exact = Song.query.filter(db.func.lower(Song.artist).like(f'%{query}%')).filter(_approved_songs_filter()).all()
    songs_by_artist_field.extend(songs_exact)
    
    # If query has multiple words, also try matching songs that contain all words (in any order)
    if len(query_words) > 1:
        # Build a query that matches all words
        conditions = [db.func.lower(Song.artist).like(f'%{word}%') for word in query_words if len(word) > 2]
        if conditions:
            songs_all_words = Song.query.filter(db.and_(*conditions)).filter(_approved_songs_filter()).all()
            # Add songs that aren't already in the list
            existing_ids = {s.id for s in songs_by_artist_field}
            for song in songs_all_words:
                if song.id not in existing_ids:
                    songs_by_artist_field.append(song)
    
    if songs_by_artist_field:
        # Group by artist to return all songs by matching artists
        artist_groups = {}
        for song in songs_by_artist_field:
            artist_name = song.artist if song.artist else 'Unknown'
            if artist_name not in artist_groups:
                artist_groups[artist_name] = []
            artist_groups[artist_name].append(song)
        
        # Return all songs from all matching artists
        import re
        for artist_name, artist_songs in artist_groups.items():
            for song in artist_songs:
                # Clean song name
                song_name = song.name.strip() if song.name and song.name.strip() else ''
                by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
                if by_pattern.match(song_name):
                    extracted_artist = by_pattern.match(song_name).group(1).strip()
                    if not artist_name or artist_name == 'Unknown':
                        artist_name = extracted_artist
                    song_name = ''
                
                if not song_name:
                    song_name = 'Untitled Track'
                
                # Include all songs from database, even if file doesn't exist
                # (File existence will be checked when trying to play)
                from flask import url_for
                song_path = url_for('playlist2.serve_song_file', song_id=song.id)
                
                # Get artist profile picture if available
                artist_profile_pic = None
                if song.artist_id:
                    artist_obj = Artist.query.get(song.artist_id)
                    if artist_obj and artist_obj.profile_pic:
                        profile_pic_path = artist_obj.profile_pic
                        if profile_pic_path.startswith('static/'):
                            artist_profile_pic = profile_pic_path.replace('static/', '')
                        else:
                            artist_profile_pic = profile_pic_path
                
                # Get song cover image if available
                song_cover_image = song.cover_image if song.cover_image else None
                
                song_data = {
                    'id': song.id,
                    'song_id': song.id,
                    'download_id': None,
                    'name': song_name,
                    'artist': artist_name,
                    'path': song_path,
                    'cover_image': song_cover_image,
                    'artist_profile_pic': artist_profile_pic
                }
                add_song_if_unique(song_data)
        
        if all_songs_data:
            return jsonify(all_songs_data)
    
    # 3b. Partial match for artist name in Artist table (fallback if Song.artist search found nothing)
    artist_partial = Artist.query.filter(db.func.lower(Artist.artist_name).like(f'%{query}%')).first()
    if artist_partial:
        # Get songs by this artist including collaborations
        songs_data = get_all_songs_by_artist(artist_id=artist_partial.artist_id, artist_name=artist_partial.artist_name, include_collaborations=True)
        if songs_data:
            for song_data in songs_data:
                add_song_if_unique(song_data)
            if all_songs_data:
                return jsonify(all_songs_data)
        
        # Also search Song.artist field for this artist name (in case songs aren't linked by artist_id)
        songs_by_artist_name = Song.query.filter(db.func.lower(Song.artist).like(f'%{artist_partial.artist_name.lower()}%')).filter(_approved_songs_filter()).all()
        if songs_by_artist_name:
            import re
            for song in songs_by_artist_name:
                artist_name = song.artist if song.artist else 'Unknown'
                song_name = song.name.strip() if song.name and song.name.strip() else ''
                
                by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
                if by_pattern.match(song_name):
                    extracted_artist = by_pattern.match(song_name).group(1).strip()
                    if not artist_name or artist_name == 'Unknown':
                        artist_name = extracted_artist
                    song_name = ''
                
                if not song_name:
                    song_name = 'Untitled Track'
                
                if not check_song_file_exists(song):
                    continue
                
                from flask import url_for
                song_path = url_for('playlist2.serve_song_file', song_id=song.id)
                
                # Get artist profile picture if available
                artist_profile_pic = None
                if song.artist_id:
                    artist_obj = Artist.query.get(song.artist_id)
                    if artist_obj and artist_obj.profile_pic:
                        profile_pic_path = artist_obj.profile_pic
                        if profile_pic_path.startswith('static/'):
                            artist_profile_pic = profile_pic_path.replace('static/', '')
                        else:
                            artist_profile_pic = profile_pic_path
                
                # Get song cover image if available
                song_cover_image = song.cover_image if song.cover_image else None
                
                song_data = {
                    'id': song.id,
                    'song_id': song.id,
                    'download_id': None,
                    'name': song_name,
                    'artist': artist_name,
                    'path': song_path,
                    'cover_image': song_cover_image,
                    'artist_profile_pic': artist_profile_pic
                }
                add_song_if_unique(song_data)
            
            if all_songs_data:
                return jsonify(all_songs_data)

    # 4. Exact match for song name (if no partial matches)
    song = Song.query.filter(db.func.lower(Song.name) == query).filter(_approved_songs_filter()).first()
    if song:
        artist_id = song.artist_id
        artist_name = song.artist
        
        # Get artist name if we have artist_id
        if artist_id:
            artist_obj = Artist.query.get(artist_id)
            if artist_obj:
                artist_name = artist_obj.artist_name
        
        # Get all songs by this artist
        if artist_id or artist_name:
            songs_data = get_all_songs_by_artist(artist_id=artist_id, artist_name=artist_name)
            if songs_data:
                for song_data in songs_data:
                    add_song_if_unique(song_data)
                if all_songs_data:
                    return jsonify(all_songs_data)

    # Return deduplicated results if we found any
    if all_songs_data:
        return jsonify(all_songs_data)

    # No match found
    return jsonify([])

@play.route('/suggestions', methods=['GET'])
def get_suggestions():
    """Get autocomplete suggestions for artists and songs as user types"""
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:  # Require at least 2 characters
        return jsonify({'artists': [], 'songs': []})
    
    suggestions = {'artists': [], 'songs': []}
    
    # Get artist suggestions (limit to 5)
    artists = Artist.query.filter(
        db.func.lower(Artist.artist_name).like(f'%{query}%')
    ).limit(5).all()
    
    for artist in artists:
        suggestions['artists'].append({
            'id': artist.artist_id,
            'name': artist.artist_name,
            'type': 'artist'
        })
    
    # Get song suggestions (limit to 5) - only approved songs
    songs = Song.query.filter(
        db.or_(
            db.func.lower(Song.name).like(f'%{query}%'),
            db.func.lower(Song.artist).like(f'%{query}%')
        )
    ).filter(_approved_songs_filter()).limit(5).all()
    
    seen_song_keys = set()
    for song in songs:
        # Get artist name
        artist_name = song.artist if song.artist else 'Unknown'
        if not artist_name or artist_name == 'Unknown':
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj:
                    artist_name = artist_obj.artist_name
        
        # Clean song name
        song_name = song.name.strip() if song.name and song.name.strip() else 'Untitled Track'
        
        # Deduplicate by name+artist
        song_key = f"{song_name.lower()}|{artist_name.lower()}"
        if song_key not in seen_song_keys:
            seen_song_keys.add(song_key)
            suggestions['songs'].append({
                'id': song.id,
                'song_id': song.id,
                'download_id': None,
                'name': song_name,
                'artist': artist_name,
                'type': 'song'
            })
    for d in DownloadedSong.query.filter(
        db.or_(
            db.func.lower(DownloadedSong.name).like(f'%{query}%'),
            db.func.lower(DownloadedSong.artist).like(f'%{query}%')
        )
    ).limit(5).all():
        name = (d.name or '').strip() or 'Untitled Track'
        artist = (d.artist or 'Unknown').strip()
        song_key = f"{name.lower()}|{artist.lower()}"
        if song_key not in seen_song_keys:
            seen_song_keys.add(song_key)
            suggestions['songs'].append({
                'id': d.id,
                'song_id': None,
                'download_id': d.id,
                'name': name,
                'artist': artist,
                'type': 'song'
            })
    return jsonify(suggestions)

@play.route('/artist-songs', methods=['GET'])
def get_artist_songs():
    """Get all songs by an artist including collaborations"""
    artist_id = request.args.get('artist_id', type=int)
    artist_name = request.args.get('artist_name', '').strip()
    
    if not artist_id and not artist_name:
        return jsonify([])
    
    # Get all songs including collaborations
    songs_data = get_all_songs_by_artist(
        artist_id=artist_id, 
        artist_name=artist_name, 
        include_collaborations=True
    )
    
    return jsonify(songs_data)

@play.route('/get_available_songs', methods=['GET'])
def get_available_songs():
    """Get list of available songs for display (artist uploads + downloaded songs)."""
    try:
        from flask import url_for
        import re
        songs = Song.query.filter(_approved_songs_filter()).order_by(Song.id.desc()).limit(12).all()
        downloads = DownloadedSong.query.order_by(DownloadedSong.id.desc()).limit(12).all()
        songs_data = []
        by_key = {}
        def add_song_item(song_id, download_id, name, artist, path, cover_image=None, artist_profile_pic=None):
            key = f"{name}|{artist}".lower()
            if key in by_key:
                return
            by_key[key] = True
            songs_data.append({
                'id': song_id or download_id,
                'song_id': song_id,
                'download_id': download_id,
                'name': name,
                'artist': artist,
                'path': path,
                'cover_image': cover_image,
                'artist_profile_pic': artist_profile_pic
            })
        for song in songs:
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            song_name = song.name.strip() if song.name and song.name.strip() else ''
            by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
            if by_pattern.match(song_name):
                extracted_artist = by_pattern.match(song_name).group(1).strip()
                if not artist_name or artist_name == 'Unknown':
                    artist_name = extracted_artist
                song_name = ''
            if not song_name:
                song_name = 'Untitled Track'
            if not check_song_file_exists(song):
                continue
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            artist_profile_pic = None
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj and artist_obj.profile_pic:
                    profile_pic_path = artist_obj.profile_pic
                    artist_profile_pic = profile_pic_path.replace('static/', '') if profile_pic_path.startswith('static/') else profile_pic_path
            add_song_item(song.id, None, song_name, artist_name, song_path, song.cover_image, artist_profile_pic)
        for d in downloads:
            name = (d.name or '').strip() or 'Untitled Track'
            artist = d.artist or 'Unknown'
            path = url_for('playlist2.serve_downloaded_song_file', download_id=d.id)
            add_song_item(None, d.id, name, artist, path)
        songs_data.sort(key=lambda x: -(x['song_id'] or x['download_id'] or 0))
        songs_data = songs_data[:12]
        return jsonify(songs_data)
    except Exception as e:
        print(f"Error fetching available songs: {e}")
        return jsonify([])



@play.route('/add_to_playlist', methods=['POST'])
@login_required
def add_to_playlist():
    from glconnect.playlist_logic import add_to_playlist_impl
    data = request.get_json()
    song_id = data.get('song_id')
    download_id = data.get('download_id')
    success, message, err_code = add_to_playlist_impl(db.session, current_user.user_id, song_id, download_id)
    if err_code:
        return jsonify({"status": "error", "message": message}), err_code
    return jsonify({"status": "success", "message": message})


# Define the function to get the user playlist
def get_user_playlist():
    user_id = current_user.user_id  # Using Flask-Login to get the current logged in user's ID
    if not user_id:
        return []  # No user is logged in, return an empty playlist

    # Fetch the user's playlist entries from the database
    playlist = Playlist.query.filter_by(user_id=user_id).all()

    # If no playlist entries are found, return an empty list
    if not playlist:
        return []

    # Prepare a list of songs from the user's playlist
    import re
    playlist_data = []
    from flask import url_for
    for entry in playlist:
        if not entry.song_id and not entry.download_id:
            continue
        if entry.song_id:
            song = Song.query.get(entry.song_id)
            if not song:
                continue
            # Get artist name - prefer artist field, fallback to artist_id lookup
            artist_name = song.artist if song.artist else 'Unknown'
            if not artist_name or artist_name == 'Unknown':
                if song.artist_id:
                    artist = Artist.query.get(song.artist_id)
                    if artist:
                        artist_name = artist.artist_name
            
            # Clean song name - handle cases where song.name contains "by [artist]" pattern
            song_name = song.name.strip() if song.name and song.name.strip() else ''
            
            # Check if song name contains "by [artist]" pattern (e.g., "by P.Square")
            by_pattern = re.compile(r'^\s*by\s+(.+)$', re.IGNORECASE)
            if by_pattern.match(song_name):
                # Extract artist from song name if artist field is empty
                extracted_artist = by_pattern.match(song_name).group(1).strip()
                if not artist_name or artist_name == 'Unknown':
                    artist_name = extracted_artist
                song_name = ''  # Clear it since it's not actually the song name
            
            # Final song name
            if not song_name:
                song_name = 'Untitled Track'
            
            # Use the file serving route for reliable file access
            # This route handles all path resolution logic from the database
            from flask import url_for
            song_path = url_for('playlist2.serve_song_file', song_id=song.id)
            
            # Get artist profile picture if available
            artist_profile_pic = None
            if song.artist_id:
                artist_obj = Artist.query.get(song.artist_id)
                if artist_obj and artist_obj.profile_pic:
                    profile_pic_path = artist_obj.profile_pic
                    if profile_pic_path.startswith('static/'):
                        artist_profile_pic = profile_pic_path.replace('static/', '')
                    else:
                        artist_profile_pic = profile_pic_path
            
            # Get song cover image if available
            song_cover_image = song.cover_image if song.cover_image else None
            
            playlist_data.append({
                'id': song.id,
                'song_id': song.id,
                'download_id': None,
                'name': song_name,
                'artist': artist_name,
                'path': song_path,
                'cover_image': song_cover_image,
                'artist_profile_pic': artist_profile_pic
            })
        elif entry.download_id:
            d = DownloadedSong.query.get(entry.download_id)
            if d:
                name = (d.name or '').strip() or 'Untitled Track'
                artist = d.artist or 'Unknown'
                path = url_for('playlist2.serve_downloaded_song_file', download_id=d.id)
                playlist_data.append({
                    'id': d.id,
                    'song_id': None,
                    'download_id': d.id,
                    'name': name,
                    'artist': artist,
                    'path': path,
                    'cover_image': None,
                    'artist_profile_pic': None
                })
    return playlist_data


@play.route('/view_playlist')
@login_required
def view_playlist():
    # Retrieve the playlist for the current logged in user
    user_playlist = get_user_playlist()
    return jsonify(user_playlist)  # Return the playlist data as JSON


@play.route('/delete_playlist', methods=['POST'])
@login_required
def delete_playlist():
    try:
        # Delete all entries from the playlist for the current user
        Playlist.query.filter_by(user_id=current_user.user_id).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Your playlist has been deleted successfully.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error deleting playlist: {str(e)}'}), 500

@play.route('/remove_song', methods=['POST'])
@login_required
def remove_song():
    from glconnect.playlist_logic import remove_from_playlist_impl
    data = request.get_json()
    song_id = data.get('song_id')
    download_id = data.get('download_id')
    success, message, err_code = remove_from_playlist_impl(db.session, current_user.user_id, song_id, download_id)
    if err_code:
        return jsonify({"status": "error", "message": message}), err_code
    return jsonify({"status": "success", "message": message})

def _get_song_file_path(song):
    """
    Determines the absolute path of a song file.
    Returns the path if found, otherwise None.
    """
    from flask import current_app
    import logging
    logger = logging.getLogger(__name__)

    # Base directories to search for songs
    base_dirs = [
        os.path.join(current_app.root_path, 'static', 'afro'),
        os.path.join(current_app.root_path, 'static', 'song_uploads'),
        '/usr/src/appdir/glconnect/static/afro',
        '/usr/src/appdir/glconnect/static/song_uploads',
    ]

    # 1. Check local_path if it's an absolute path
    if song.local_path and os.path.isabs(song.local_path):
        if os.path.exists(song.local_path):
            logger.info(f"Found song at absolute path: {song.local_path}")
            return song.local_path

    # 2. Construct filenames to check
    filenames = []
    if song.local_path:
        filenames.append(os.path.basename(song.local_path))

    artist_name = song.artist or 'Unknown'
    if song.artist_id:
        artist = Artist.query.get(song.artist_id)
        if artist:
            artist_name = artist.artist_name
    
    song_name = song.name or 'Untitled Track'
    
    # Add common filename formats
    filenames.extend([
        f"{artist_name} - {song_name}.mp3",
        f"{artist_name}-{song_name}.mp3",
        f"{song_name} - {artist_name}.mp3",
        f"{song_name}-{artist_name}.mp3",
    ])

    # Search for the file in the base directories
    for directory in base_dirs:
        for filename in filenames:
            if not filename: continue
            file_path = os.path.join(directory, filename)
            if os.path.exists(file_path):
                logger.info(f"Found song at: {file_path}")
                return file_path

    logger.warning(f"Song file not found for song_id={song.id}, name='{song.name}'")
    return None

@play.route('/song/<int:song_id>/file')
def serve_song_file(song_id):
    """Serve song file by ID (Song table / artist uploads)."""
    try:
        song = Song.query.get_or_404(song_id)
        file_path = _get_song_file_path(song)

        if file_path:
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            # Log detailed error information
            from flask import current_app
            error_info = {
                "song_id": song_id,
                "song_name": song.name,
                "artist": song.artist,
                "local_path": song.local_path,
                "app_root": current_app.root_path,
                "cwd": os.getcwd(),
            }
            current_app.logger.error(f"Song file not found. Details: {error_info}")
            return jsonify({"error": "Song file not found", "details": error_info}), 404
            
    except Exception as e:
        import traceback
        current_app.logger.error(f"Error serving song file: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def _get_downloaded_song_file_path(download):
    """
    Determines the absolute path of a downloaded song file.
    Returns the path if found, otherwise None.
    """
    from flask import current_app
    import logging
    logger = logging.getLogger(__name__)

    if not download.local_path:
        return None

    # Base directories to search for downloaded songs
    base_dirs = [
        os.path.join(current_app.root_path, 'static', 'ytauto'),
        '/usr/src/appdir/glconnect/static/ytauto',
    ]

    filename = os.path.basename(download.local_path)

    # Search for the file in the base directories
    for directory in base_dirs:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            logger.info(f"Found downloaded song at: {file_path}")
            return file_path

    logger.warning(f"Downloaded song file not found for download_id={download.id}, name='{download.name}'")
    return None

@play.route('/download/<int:download_id>/file')
def serve_downloaded_song_file(download_id):
    """Serve a YouTube-downloaded song file by download_id."""
    try:
        download = DownloadedSong.query.get_or_404(download_id)
        file_path = _get_downloaded_song_file_path(download)

        if file_path:
            return send_file(file_path, mimetype='audio/mpeg')
        else:
            from flask import current_app
            error_info = {
                "download_id": download_id,
                "download_name": download.name,
                "local_path": download.local_path,
                "app_root": current_app.root_path,
                "cwd": os.getcwd(),
            }
            current_app.logger.error(f"Downloaded song file not found. Details: {error_info}")
            return jsonify({"error": "Downloaded song file not found", "details": error_info}), 404

    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"Error serving downloaded song file: {e}\n{traceback.format_exc()}")
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
