import os
import uuid
import threading
import json
import re
import glob
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from flask import Blueprint, render_template, request, jsonify
from .news_agent import generate_broadcast

# Create blueprint for news routes
news_bp = Blueprint('news_bp', __name__)

# Task storage
tasks = {}
_tasks_lock = threading.Lock()

# Analytics data storage
analytics_data = {
    'search_history': [],  # List of all searches with timestamps
    'category_counts': defaultdict(int),  # Count of searches per category
    'topic_counts': defaultdict(int),  # Count of individual topics
    'daily_searches': defaultdict(int),  # Searches per day
    'category_topics': defaultdict(list)  # Topics grouped by category
}
_analytics_lock = threading.Lock()

class AudioFilePathNotFound(Exception):
    pass

def cleanup_old_audio_files():
    """Clean up old audio files, keeping only jingle.wav and the most recent final_news_broadcast*.mp3"""
    print("DEBUG: Audio cleanup disabled for debugging - keeping all files")
    return  # Disabled for debugging
    
    try:
        audio_dir = "glconnect/static/audio"
        if not os.path.exists(audio_dir):
            return
        
        # Get all files in the audio directory
        all_files = glob.glob(os.path.join(audio_dir, "*"))
        
        # Keep jingle.wav
        files_to_keep = []
        if os.path.exists(os.path.join(audio_dir, "jingle.wav")):
            files_to_keep.append(os.path.join(audio_dir, "jingle.wav"))
        
        # Keep the most recent final_news_broadcast*.mp3
        final_broadcast_files = glob.glob(os.path.join(audio_dir, "final_news_broadcast*.mp3"))
        if final_broadcast_files:
            # Sort by modification time and keep the most recent
            most_recent = max(final_broadcast_files, key=os.path.getmtime)
            files_to_keep.append(most_recent)
        
        # Delete all other files (including .txt files from TTS fallback)
        for file_path in all_files:
            if file_path not in files_to_keep:
                try:
                    os.remove(file_path)
                    print(f"Cleaned up old audio file: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {e}")
        
        print(f"Audio cleanup completed. Kept {len(files_to_keep)} files.")
        
    except Exception as e:
        print(f"Error during audio cleanup: {e}")

# --- Topic Relevance Filtering ---
def is_relevant_topic(topic: str) -> bool:
    """
    Determines if a topic is relevant for news reporting using intelligent validation.
    This function is more permissive and relies on common sense rather than rigid keywords.
    """
    t = topic.strip().lower()
    if not t:
        return False
    
    # Always allow topics that are clearly news-related by common patterns
    news_indicators = [
        # Geographic/country names (common in news)
        'venezuela', 'ukraine', 'russia', 'china', 'iran', 'israel', 'palestine', 'syria', 'afghanistan',
        'north korea', 'cuba', 'mexico', 'canada', 'france', 'germany', 'uk', 'japan', 'india', 'brazil',
        'australia', 'south korea', 'taiwan', 'turkey', 'saudi arabia', 'egypt', 'nigeria', 'south africa',
        
        # News event types
        'tensions', 'crisis', 'conflict', 'war', 'peace', 'talks', 'negotiations', 'summit', 'meeting',
        'protest', 'protests', 'demonstration', 'strike', 'election', 'vote', 'referendum', 'coup',
        'sanctions', 'embargo', 'trade war', 'diplomacy', 'treaty', 'agreement', 'deal',
        
        # Economic indicators
        'recession', 'inflation', 'unemployment', 'gdp', 'growth', 'decline', 'market crash', 'boom',
        'currency', 'dollar', 'euro', 'pound', 'yen', 'cryptocurrency', 'bitcoin',
        
        # Social/political issues
        'immigration', 'refugee', 'border', 'security', 'terrorism', 'attack', 'bombing', 'shooting',
        'corruption', 'scandal', 'investigation', 'arrest', 'trial', 'verdict', 'sentence',
        'human rights', 'freedom', 'democracy', 'authoritarian', 'dictator', 'regime',
        
        # Natural disasters and emergencies
        'earthquake', 'hurricane', 'flood', 'drought', 'wildfire', 'tsunami', 'volcano',
        'pandemic', 'outbreak', 'epidemic', 'disease', 'virus', 'health emergency',
        
        # Technology and science
        'breakthrough', 'discovery', 'research', 'study', 'innovation', 'invention',
        'space', 'nasa', 'mars', 'moon', 'satellite', 'rocket', 'launch',
        'climate change', 'global warming', 'carbon', 'emissions', 'renewable energy',
        
        # Sports and entertainment
        'olympics', 'world cup', 'championship', 'tournament', 'awards', 'oscar', 'grammy',
        'celebrity', 'actor', 'singer', 'artist', 'movie', 'film', 'music',
        
        # Generic news terms
        'breaking', 'latest', 'update', 'developing', 'urgent', 'important', 'major',
        'announcement', 'statement', 'press conference', 'briefing', 'report'
    ]
    
    # Check if topic contains any news indicators
    for indicator in news_indicators:
        if indicator in t:
            return True
    
    # Allow topics that are 2+ words (likely to be descriptive news topics)
    if len(t.split()) >= 2:
        return True
    
    # Allow single words that are clearly news-related
    clear_news_words = {
        'politics', 'economy', 'sports', 'technology', 'health', 'world', 'local', 'national',
        'international', 'business', 'finance', 'science', 'education', 'entertainment',
        'crime', 'law', 'military', 'defense', 'security', 'environment', 'climate'
    }
    
    if t in clear_news_words:
        return True
    
    # If we get here, it's likely not a news topic
    return False

def categorize_topic(topic: str) -> str:
    """
    Categorizes a topic into one of the main news categories.
    Returns the category name.
    """
    t = topic.strip().lower()
    
    # Politics and government
    politics_keywords = ['politics', 'government', 'election', 'policy', 'diplomacy', 'congress', 
                        'parliament', 'senate', 'house', 'president', 'prime minister', 'mayor',
                        'vote', 'voting', 'campaign', 'candidate', 'party', 'democracy', 'authoritarian',
                        'dictator', 'regime', 'coup', 'referendum', 'treaty', 'agreement', 'summit']
    
    # Economy and finance
    economy_keywords = ['economy', 'economic', 'finance', 'financial', 'market', 'markets', 'stocks',
                       'stock', 'business', 'industry', 'trade', 'inflation', 'gdp', 'unemployment',
                       'recession', 'boom', 'currency', 'dollar', 'euro', 'pound', 'yen', 'bitcoin',
                       'cryptocurrency', 'banking', 'investment', 'revenue', 'profit', 'debt']
    
    # Sports
    sports_keywords = ['sports', 'football', 'soccer', 'basketball', 'baseball', 'tennis', 'golf',
                      'cricket', 'hockey', 'olympics', 'nfl', 'nba', 'mlb', 'nhl', 'uefa', 'fifa',
                      'championship', 'tournament', 'athlete', 'team', 'coach', 'stadium', 'arena']
    
    # Technology
    tech_keywords = ['technology', 'tech', 'ai', 'artificial intelligence', 'software', 'hardware',
                    'internet', 'cybersecurity', 'startup', 'gadgets', 'innovation', 'invention',
                    'breakthrough', 'discovery', 'research', 'study', 'digital', 'online', 'app',
                    'smartphone', 'computer', 'robot', 'automation', 'blockchain', 'data']
    
    # Health and science
    health_keywords = ['health', 'medicine', 'medical', 'covid', 'pandemic', 'vaccine', 'public health',
                      'hospital', 'doctor', 'patient', 'disease', 'virus', 'outbreak', 'epidemic',
                      'science', 'space', 'nasa', 'climate', 'environment', 'weather', 'earthquake',
                      'hurricane', 'wildfire', 'tsunami', 'volcano', 'global warming', 'carbon']
    
    # World and international
    world_keywords = ['world', 'international', 'geopolitics', 'war', 'conflict', 'military', 'defense',
                     'security', 'terrorism', 'un', 'nato', 'sanctions', 'embargo', 'diplomacy',
                     'immigration', 'refugee', 'border', 'attack', 'bombing', 'shooting', 'crisis',
                     'tensions', 'peace', 'talks', 'negotiations', 'summit', 'meeting']
    
    # Crime and law
    crime_keywords = ['crime', 'law', 'legal', 'court', 'lawsuit', 'police', 'trial', 'verdict',
                     'supreme court', 'arrest', 'sentence', 'prison', 'jail', 'corruption', 'scandal',
                     'investigation', 'evidence', 'witness', 'jury', 'judge', 'lawyer', 'attorney']
    
    # Entertainment
    entertainment_keywords = ['entertainment', 'movies', 'film', 'music', 'culture', 'festival', 'awards',
                             'oscar', 'grammy', 'celebrity', 'actor', 'singer', 'artist', 'director',
                             'producer', 'album', 'song', 'concert', 'theater', 'broadway', 'tv', 'show']
    
    # Check each category
    for keyword in politics_keywords:
        if keyword in t:
            return 'Politics'
    
    for keyword in economy_keywords:
        if keyword in t:
            return 'Economy'
    
    for keyword in sports_keywords:
        if keyword in t:
            return 'Sports'
    
    for keyword in tech_keywords:
        if keyword in t:
            return 'Technology'
    
    for keyword in health_keywords:
        if keyword in t:
            return 'Health & Science'
    
    for keyword in world_keywords:
        if keyword in t:
            return 'World & International'
    
    for keyword in crime_keywords:
        if keyword in t:
            return 'Crime & Law'
    
    for keyword in entertainment_keywords:
        if keyword in t:
            return 'Entertainment'
    
    # Default to "Other" if no category matches
    return 'Other'

def track_search_analytics(topics: list[str]):
    """
    Tracks search analytics for the given topics.
    """
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')
    
    with _analytics_lock:
        for topic in topics:
            # Add to search history
            analytics_data['search_history'].append({
                'topic': topic,
                'timestamp': current_time.isoformat(),
                'date': current_date
            })
            
            # Categorize the topic
            category = categorize_topic(topic)
            
            # Update counts
            analytics_data['category_counts'][category] += 1
            analytics_data['topic_counts'][topic] += 1
            analytics_data['daily_searches'][current_date] += 1
            
            # Add to category topics
            if topic not in analytics_data['category_topics'][category]:
                analytics_data['category_topics'][category].append(topic)

def extract_audio_path_from_output(output_text):
    """Extract audio file path from agent output text."""
    if not output_text:
        return None
    
    # Look for the audio file path in the output using regex
    # Pattern to match: glconnect/static/audio/final_news_broadcast_*.mp3
    match = re.search(r'glconnect/static/audio/final_news_broadcast[^\s]*\.mp3', output_text)
    if match:
        return match.group(0)
    
    # Fallback: look for any .mp3 file path
    match = re.search(r'[^\s]*\.mp3', output_text)
    if match:
        return match.group(0)
    
    return None

def run_generate_broadcast(task_id, topics):
    """Wrapper function to run generate_broadcast and store the result."""
    try:
        # Use the ADK agent system for sophisticated news generation
        print("Using ADK agent system with Google Cloud TTS...")
        print("Following pattern: jingle → intro → transition → report → thank you → outro → jingle")
        
        # Run the ADK agent system directly (no threading needed)
        print(f"Starting ADK agent news generation for topics: {topics}")
        output = generate_broadcast(topics)
        print("ADK agent system completed successfully")
        
        # The agent returns a string, not a dictionary
        if isinstance(output, str):
            print(f"Output from generate_broadcast: {output}")
            # Extract the audio file path from the string output
            audio_file_path = extract_audio_path_from_output(output)
            print(f"Extracted audio file path: {audio_file_path}")
            
            if not audio_file_path:
                # If we can't find the path in the output, check if any audio files exist
                # Look for the default filename first
                default_path = "glconnect/static/audio/final_news_broadcast.mp3"
                if os.path.exists(default_path):
                    audio_file_path = default_path
                else:
                    # Look for timestamped versions of the audio file
                    audio_dir = "glconnect/static/audio"
                    if os.path.exists(audio_dir):
                        import glob
                        # Look for any files matching the pattern
                        pattern = os.path.join(audio_dir, "final_news_broadcast*.mp3")
                        matching_files = glob.glob(pattern)
                        if matching_files:
                            # Get the most recent file
                            audio_file_path = max(matching_files, key=os.path.getctime)
                        else:
                            raise AudioFilePathNotFound("Audio file path not found in output and no audio files exist")
                    else:
                        raise AudioFilePathNotFound("Audio file path not found in output and audio directory doesn't exist")
            
            # Convert the file path to a URL that can be served by Flask
            filename = os.path.basename(audio_file_path)
            audio_url = f"/routes2/news/audio/{filename}"
            
            # Store the result with the extracted audio path
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['audio_file'] = audio_url
                tasks[task_id]['summary'] = ""
            
            # Clean up old audio files after successful generation
            cleanup_old_audio_files()
            print("ADK agent system completed successfully!")
            return
        else:
            # Handle dictionary output (if the agent ever returns one)
            audio_file_path = output.get('final_broadcast_audio_output', {}).get('combined_audio_filepath')
            if not audio_file_path:
                raise AudioFilePathNotFound("Audio file path not found in output")
            
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['result'] = output
            
            # Clean up old audio files after successful generation
            cleanup_old_audio_files()
            print("ADK agent system completed successfully!")
            return
            
    except Exception as e:
        print(f"Error in ADK agent news generation: {e}")
        with _tasks_lock:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = f"News generation failed: {e}"

@news_bp.route('/')
def index():
    return render_template('newsgen.html')

@news_bp.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files from the glconnect/static/audio directory."""
    from flask import send_from_directory
    import os
    audio_dir = os.path.join(os.getcwd(), 'glconnect', 'static', 'audio')
    return send_from_directory(audio_dir, filename)

@news_bp.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    # Handle both string and list inputs
    if isinstance(data['topics'], str):
        topics = [topic.strip() for topic in data['topics'].split(',')]
    else:
        topics = [topic.strip() for topic in data['topics']]
    # Filter to only relevant topics
    relevant_topics = [t for t in topics if is_relevant_topic(t)]

    if not relevant_topics:
        return jsonify({'error': 'No relevant news topics detected. Please enter news-related topics like politics, economy, sports, technology, health, world, etc.'}), 400

    # Track analytics for the search
    track_search_analytics(relevant_topics)

    task_id = str(uuid.uuid4())
    with _tasks_lock:
        tasks[task_id] = {'status': 'running'}

    thread = threading.Thread(target=run_generate_broadcast, args=(task_id, relevant_topics))
    thread.start()

    return jsonify({'task_id': task_id})

@news_bp.route('/status/<task_id>')
def task_status(task_id):
    with _tasks_lock:
        task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task['status'] == 'completed':
        # Handle the new task structure with direct audio_file and summary
        if 'audio_file' in task:
            return jsonify({
                'status': 'completed',
                'audio_file': task['audio_file'],
                'summary': task.get('summary', '')
            })
        # Fallback for old structure
        elif 'result' in task:
            result = task['result']
        
        # Handle the new result structure
        if isinstance(result, dict) and 'audio_file_path' in result:
            audio_file_path = result['audio_file_path']
            output_text = result.get('output_text', '')
            
            # Extract summary from the output text if available
            summary = ""
            if output_text:
                # Look for summary in the output
                lines = output_text.split('\n')
                for line in lines:
                    if 'summary' in line.lower() and ':' in line:
                        summary = line.split(':', 1)[1].strip()
                        break
            
            # Verify the audio file exists before returning it
            if not os.path.exists(audio_file_path):
                return jsonify({'status': 'failed', 'error': f'Audio file not found: {audio_file_path}'})
            
            return jsonify({
                'status': 'completed',
                'audio_file': audio_file_path,
                'summary': summary
            })
        else:
            # Handle old dictionary structure (if any)
            audio_output = result.get('final_broadcast_audio_output', {})
            audio_file_path = audio_output.get('combined_audio_filepath')
            
            if not audio_file_path:
                return jsonify({'status': 'failed', 'error': 'Audio file path not found in task result.'})
            
            # Verify the audio file exists
            if not os.path.exists(audio_file_path):
                return jsonify({'status': 'failed', 'error': f'Audio file not found: {audio_file_path}'})
            
            return jsonify({
                'status': 'completed',
                'audio_file': audio_file_path,
                'summary': result.get('summary_output', {}).get('summary', '')
            })
            
    elif task['status'] == 'failed':
        return jsonify({'status': 'failed', 'error': task.get('error', 'Unknown error')})
    else:
        return jsonify({'status': 'running'})

@news_bp.route('/analytics')
def analytics():
    """Main analytics page showing dominant topics by category."""
    with _analytics_lock:
        # Get category counts sorted by frequency
        category_data = dict(analytics_data['category_counts'])
        sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
        
        # Get total searches
        total_searches = sum(analytics_data['category_counts'].values())
        
        # Get recent searches (last 10)
        recent_searches = analytics_data['search_history'][-10:]
        
        # Get daily search trends (last 7 days)
        daily_trends = []
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            count = analytics_data['daily_searches'].get(date, 0)
            daily_trends.append({'date': date, 'count': count})
        daily_trends.reverse()
        
        return render_template('analytics.html', 
                             categories=sorted_categories,
                             total_searches=total_searches,
                             recent_searches=recent_searches,
                             daily_trends=daily_trends)

@news_bp.route('/analytics/category/<category>')
def category_details(category):
    """Detailed view of topics within a specific category."""
    with _analytics_lock:
        # Get topics for this category
        category_topics = analytics_data['category_topics'].get(category, [])
        
        # Get topic counts for this category
        topic_counts = {}
        for search in analytics_data['search_history']:
            if categorize_topic(search['topic']) == category:
                topic = search['topic']
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # Sort topics by frequency
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Get recent searches for this category
        recent_category_searches = [
            search for search in analytics_data['search_history'][-20:]
            if categorize_topic(search['topic']) == category
        ]
        
        return render_template('category_details.html',
                             category=category,
                             topics=sorted_topics,
                             recent_searches=recent_category_searches)

@news_bp.route('/api/analytics/summary')
def analytics_summary():
    """API endpoint for analytics summary data."""
    with _analytics_lock:
        return jsonify({
            'total_searches': sum(analytics_data['category_counts'].values()),
            'category_counts': dict(analytics_data['category_counts']),
            'top_topics': dict(Counter(analytics_data['topic_counts']).most_common(10)),
            'daily_searches': dict(analytics_data['daily_searches'])
        })
