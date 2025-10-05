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

# Task storage (keeping for backward compatibility, but using database as primary)
tasks = {}
_tasks_lock = threading.Lock()

# Database task management functions
def create_task_in_db(task_id, topics):
    """Create a new task in the database."""
    from glconnect.models import db, NewsTask
    from glconnect import create_app
    import json
    
    app = create_app()
    with app.app_context():
        try:
            task = NewsTask(
                task_id=task_id,
                status='running',
                topics=json.dumps(topics),
                progress=0,
                current_step='Initializing news generation...',
                last_heartbeat=datetime.now(),
                error=None  # Initialize error field
            )
            db.session.add(task)
            db.session.commit()
            print(f"DEBUG: Created task {task_id} in database")
            return True
        except Exception as e:
            print(f"ERROR: Failed to create task in database: {e}")
            import traceback
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return False

def update_task_in_db(task_id, **kwargs):
    """Update a task in the database and sync with in-memory tasks."""
    from glconnect.models import db, NewsTask
    from glconnect import create_app
    import json
    
    app = create_app()
    with app.app_context():
        try:
            task = NewsTask.query.filter_by(task_id=task_id).first()
            if not task:
                print(f"DEBUG: Task {task_id} not found in database")
                return False
            
            # Update fields
            for key, value in kwargs.items():
                if key in ['result', 'memory_usage', 'topics_processed'] and isinstance(value, (dict, list)):
                    setattr(task, key, json.dumps(value))
                elif key == 'last_heartbeat' and isinstance(value, str):
                    # Handle string datetime
                    from dateutil import parser
                    setattr(task, key, parser.parse(value))
                else:
                    setattr(task, key, value)
            
            db.session.commit()
            print(f"DEBUG: Updated task {task_id} in database")
            
            # Sync with in-memory tasks dictionary
            try:
                with _tasks_lock:
                    if task_id in tasks:
                        for key, value in kwargs.items():
                            tasks[task_id][key] = value
                        print(f"DEBUG: Synced task {task_id} with in-memory tasks")
            except Exception as e:
                print(f"DEBUG: Failed to sync with in-memory tasks: {e}")
            
            return True
        except Exception as e:
            print(f"ERROR: Failed to update task in database: {e}")
            db.session.rollback()
            return False

def get_task_from_db(task_id):
    """Get a task from the database."""
    from glconnect.models import db, NewsTask
    from glconnect import create_app
    import json
    
    app = create_app()
    with app.app_context():
        try:
            task = NewsTask.query.filter_by(task_id=task_id).first()
            if not task:
                return None
            
            # Convert to dictionary format
            task_dict = {
                'status': task.status,
                'created_at': task.created_at,
                'completed_at': task.completed_at,
                'failed_at': task.failed_at,
                'last_heartbeat': task.last_heartbeat,
                'progress': task.progress,
                'current_step': task.current_step,
                'error': task.error,
                'generation_time': task.generation_time
            }
            
            # Parse JSON fields
            if task.topics:
                task_dict['topics'] = json.loads(task.topics)
            if task.result:
                task_dict['result'] = json.loads(task.result)
            if task.memory_usage:
                task_dict['memory_usage'] = json.loads(task.memory_usage)
            if task.topics_processed:
                task_dict['topics_processed'] = json.loads(task.topics_processed)
            
            return task_dict
        except Exception as e:
            print(f"ERROR: Failed to get task from database: {e}")
            return None

def delete_task_from_db(task_id):
    """Delete a task from the database."""
    from glconnect.models import db, NewsTask
    from glconnect import create_app
    
    app = create_app()
    with app.app_context():
        try:
            task = NewsTask.query.filter_by(task_id=task_id).first()
            if task:
                db.session.delete(task)
                db.session.commit()
                print(f"DEBUG: Deleted task {task_id} from database")
                return True
            return False
        except Exception as e:
            print(f"ERROR: Failed to delete task from database: {e}")
            db.session.rollback()
            return False

def normalize_task_format(task):
    """Normalize task format from database to match memory format."""
    if not task:
        return None
    
    # If it's already in memory format, return as is
    if 'audio_file' in task or 'result' in task:
        return task
    
    # Convert database format to memory format
    normalized = {
        'status': task.get('status', 'running'),
        'created_at': task.get('created_at'),
        'completed_at': task.get('completed_at'),
        'failed_at': task.get('failed_at'),
        'last_heartbeat': task.get('last_heartbeat'),
        'progress': task.get('progress', 0),
        'current_step': task.get('current_step'),
        'error': task.get('error'),
        'generation_time': task.get('generation_time')
    }
    
    # Handle result field
    if 'result' in task and task['result']:
        if isinstance(task['result'], dict):
            normalized['result'] = task['result']
            # Extract audio_file if available
            if 'audio_file_path' in task['result']:
                audio_path = task['result']['audio_file_path']
                if audio_path.startswith('glconnect/static/audio/'):
                    filename = os.path.basename(audio_path)
                    normalized['audio_file'] = f"/routes2/news/audio/{filename}"
                else:
                    normalized['audio_file'] = audio_path
            if 'output_text' in task['result']:
                normalized['summary'] = task['result']['output_text']
    
    # Handle other fields
    if 'topics' in task:
        normalized['topics'] = task['topics']
    if 'memory_usage' in task:
        normalized['memory_usage'] = task['memory_usage']
    if 'topics_processed' in task:
        normalized['topics_processed'] = task['topics_processed']
    
    return normalized

def cleanup_old_tasks():
    """Clean up old completed/failed tasks to prevent memory buildup."""
    try:
        current_time = datetime.now()
        print(f"DEBUG: Cleanup started at {current_time}")
        
        # Check memory usage before cleanup
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            print(f"DEBUG: Memory usage - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        except ImportError:
            print("DEBUG: psutil not available - skipping memory check")
        except Exception as e:
            print(f"DEBUG: Memory check failed: {e}")
        
        with _tasks_lock:
            print(f"DEBUG: Current tasks before cleanup: {len(tasks)}")
            # Only clean up if we have more than 10 tasks to prevent aggressive cleanup
            if len(tasks) <= 10:
                print(f"DEBUG: Skipping cleanup - only {len(tasks)} tasks in system")
                return
            
            tasks_to_remove = []
            for task_id, task_data in tasks.items():
                if 'created_at' in task_data:
                    task_age = current_time - task_data['created_at']
                    print(f"DEBUG: Task {task_id} age: {task_age.total_seconds():.1f}s, status: {task_data.get('status')}")
                    # Clean up tasks older than 4 hours AND not currently running (increased from 2 hours)
                    # OR clean up stuck running tasks (no heartbeat for 30 minutes)
                    is_old_task = task_age.total_seconds() > 14400 and task_data.get('status') not in ['running']
                    
                    # For running tasks, check heartbeat instead of creation time
                    is_stuck_running = False
                    if task_data.get('status') == 'running':
                        last_heartbeat = task_data.get('last_heartbeat')
                        if last_heartbeat:
                            heartbeat_age = (current_time - last_heartbeat).total_seconds()
                            is_stuck_running = heartbeat_age > 1800  # 30 minutes without heartbeat
                        else:
                            # Fallback to creation time if no heartbeat
                            is_stuck_running = task_age.total_seconds() > 1800
                    
                    if is_old_task or is_stuck_running:
                        tasks_to_remove.append(task_id)
                        print(f"DEBUG: Marking task {task_id} for cleanup (age: {task_age.total_seconds():.1f}s, status: {task_data.get('status')})")
                    else:
                        print(f"DEBUG: Keeping task {task_id} (age: {task_age.total_seconds():.1f}s, status: {task_data.get('status')})")
                elif task_data.get('status') in ['completed', 'failed']:
                    # For tasks without created_at but are completed/failed, 
                    # remove them if they're older than 4 hours (increased from 2 hours)
                    cleanup_timestamp = None
                    if 'completed_at' in task_data:
                        cleanup_timestamp = task_data['completed_at']
                    elif 'failed_at' in task_data:
                        cleanup_timestamp = task_data['failed_at']
                    
                    if cleanup_timestamp:
                        task_age = current_time - cleanup_timestamp
                        if task_age.total_seconds() > 14400:  # 4 hours instead of 2 hours
                            tasks_to_remove.append(task_id)
                            print(f"DEBUG: Marking completed task for cleanup: {task_id} (age: {task_age.total_seconds():.1f}s)")
                    else:
                        # If no timestamp at all, remove completed/failed tasks after 2 hours (increased from 1 hour)
                        if 'created_at' not in task_data:
                            # Only remove if it's been at least 2 hours since we can't determine exact completion time
                            tasks_to_remove.append(task_id)
                            print(f"DEBUG: Marking legacy task for cleanup: {task_id}")
            
            # Only remove tasks if we have more than 5 tasks remaining after cleanup
            if len(tasks) - len(tasks_to_remove) > 5:
                for task_id in tasks_to_remove:
                    task_info = tasks[task_id]
                    del tasks[task_id]
                    print(f"Cleaned up old task: {task_id} (status: {task_info.get('status')}, age: {task_info.get('created_at', 'no timestamp')})")
                
                if tasks_to_remove:
                    print(f"DEBUG: Cleanup removed {len(tasks_to_remove)} tasks. Remaining: {len(tasks)}")
                else:
                    print(f"DEBUG: No tasks cleaned up. Current tasks: {len(tasks)}")
            else:
                print(f"DEBUG: Skipping cleanup to maintain minimum task count. Would remove {len(tasks_to_remove)} tasks, leaving {len(tasks) - len(tasks_to_remove)}")
            
            # Check memory usage after cleanup
            try:
                import psutil
                memory_info = psutil.virtual_memory()
                print(f"DEBUG: Memory after cleanup - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
                
                # If memory usage is high, warn about potential issues
                if memory_info.percent > 80:
                    print(f"WARNING: High memory usage detected ({memory_info.percent}%) - this may cause worker crashes!")
            except ImportError:
                print("DEBUG: psutil not available - skipping memory check")
            except Exception as e:
                print(f"DEBUG: Memory check failed: {e}")
                
    except Exception as e:
        print(f"Error cleaning up tasks: {e}")

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

def cleanup_old_completed_tasks():
    """Clean up old completed tasks to free memory, preserving running tasks."""
    try:
        from datetime import datetime, timedelta
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)  # Keep tasks newer than 1 hour
        
        with _tasks_lock:
            # Get list of tasks to remove (completed and old)
            tasks_to_remove = []
            for task_id, task_data in tasks.items():
                if (task_data.get('status') in ['completed', 'failed'] and 
                    task_data.get('created_at', current_time) < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            # Remove old completed tasks
            for task_id in tasks_to_remove:
                del tasks[task_id]
                print(f"DEBUG: Removed old completed task: {task_id}")
            
            print(f"DEBUG: Task cleanup completed: {len(tasks_to_remove)} old tasks removed, {len(tasks)} tasks remaining")
            
    except Exception as e:
        print(f"Error during task cleanup: {e}")

def cleanup_old_audio_files():
    """Clean up old audio files, keeping only jingle.wav and the most recent final_news_broadcast*.mp3"""
    print("DEBUG: Audio cleanup disabled for debugging - keeping all files")
    print("DEBUG: PROTECTED FILES: jingle.wav and final_news_broadcast*.mp3 will NEVER be deleted")
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
def is_relevant_topic(topic: str) -> tuple[bool, float, str]:
    """
    Enhanced news topic validation using Gemini AI as primary validator.
    Returns (is_relevant, confidence_score, reason)
    """
    t = topic.strip().lower()
    if not t:
        print(f"DEBUG: Empty topic rejected")
        return False, 0.0, "Empty topic"
    
    print(f"DEBUG: Enhanced validation for: '{topic}'")
    
    # STRATEGY 1: Quick Rejection of Obviously Non-News
    if is_obviously_not_news(topic):
        print(f"DEBUG: Topic rejected as obviously non-news")
        return False, 0.95, "Obviously non-news content"
    
    # STRATEGY 2: Gemini AI Validation (Primary method)
    try:
        is_relevant, confidence = validate_topic_with_ai_enhanced(topic)
        if is_relevant is not None:
            print(f"DEBUG: Gemini validation result: {is_relevant} (confidence: {confidence})")
            if is_relevant:
                return True, confidence, "Gemini AI validation - Valid news topic"
            else:
                return False, confidence, "Gemini AI validation - Not a valid news topic"
    except Exception as e:
        print(f"DEBUG: Gemini validation failed: {e}, trying fallback methods")
    
    # STRATEGY 3: Fallback to Pattern-Based Validation
    try:
        is_relevant = validate_topic_with_patterns(topic)
        if is_relevant:
            return True, 0.8, "Pattern matching (fallback)"
    except Exception as e:
        print(f"DEBUG: Pattern validation failed: {e}")
    
    # STRATEGY 4: Fallback to Keyword-Based Validation
    try:
        is_relevant = validate_topic_with_keywords(topic)
        if is_relevant:
            return True, 0.7, "Keyword matching (fallback)"
    except Exception as e:
        print(f"DEBUG: Keyword validation failed: {e}")
    
    # STRATEGY 5: Learning-Based Validation (with fallback to acceptance)
    try:
        is_relevant, confidence = validate_topic_with_learning_enhanced(topic)
        if is_relevant is not None:
            print(f"DEBUG: Learning validation result: {is_relevant} (confidence: {confidence})")
            return is_relevant, confidence, "Learning-based"
    except Exception as e:
        print(f"DEBUG: Learning validation failed: {e}")
    
    # PROACTIVE STRATEGY 6: Default to ACCEPTANCE (Ultra-Permissive)
    # Only reject if we're absolutely certain it's not news
    return apply_proactive_default_rules(topic)

def is_obviously_not_news(topic: str) -> bool:
    """
    Only reject topics that are obviously not news-related.
    This is a very restrictive filter - only reject clear non-news.
    """
    t = topic.strip().lower()
    
    # Only reject very obvious non-news patterns
    obvious_non_news = [
        # Single characters or very short nonsense
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
        'ab', 'cd', 'ef', 'gh', 'ij', 'kl', 'mn', 'op', 'qr', 'st', 'uv', 'wx', 'yz',
        'abc', 'def', 'ghi', 'jkl', 'mno', 'pqr', 'stu', 'vwx', 'yz',
        'asdf', 'qwerty', 'zxcv', 'hjkl', 'fghj', 'tyui', 'uiop', 'asdf', 'qwer',
        
        # Very obvious non-news terms
        'hello', 'hi', 'hey', 'test', 'testing', '123', 'abc', 'xyz',
        'password', 'admin', 'login', 'logout', 'user', 'guest',
        'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur',
        
        # Pure gibberish
        'asdfasdf', 'qwertyuiop', 'zxcvbnm', 'hjklhjkl',
        'aaaaaaaa', 'bbbbbbbb', 'cccccccc', 'dddddddd',
        '11111111', '22222222', '33333333', '44444444',
    ]
    
    if t in obvious_non_news:
        return True
    
    # Reject pure numbers or symbols
    if t.isdigit() or not any(c.isalpha() for c in t):
        return True
    
    # Reject very short topics (less than 3 characters)
    if len(t) < 3:
        return True
    
    return False

def has_strong_news_indicators(topic: str) -> bool:
    """
    Quickly accept topics that have strong news indicators.
    This is a very permissive filter - accept anything that looks like news.
    """
    t = topic.strip().lower()
    
    # Strong news indicators - if any of these are present, accept immediately
    strong_indicators = [
        # Major companies and organizations
        'apple', 'google', 'microsoft', 'amazon', 'meta', 'facebook', 'tesla', 'spacex',
        'netflix', 'disney', 'warner', 'sony', 'nintendo', 'intel', 'nvidia', 'amd',
        'samsung', 'huawei', 'xiaomi', 'oneplus', 'oppo', 'vivo', 'realme',
        
        # Political figures and leaders
        'trump', 'biden', 'harris', 'putin', 'xi', 'jinping', 'modi', 'macron',
        'merkel', 'johnson', 'trudeau', 'moon', 'abe', 'kishida', 'erdogan',
        'president', 'prime minister', 'minister', 'senator', 'governor', 'mayor',
        'congress', 'parliament', 'senate', 'house', 'assembly', 'council',
        
        # Countries and regions
        'america', 'usa', 'united states', 'china', 'russia', 'ukraine', 'israel',
        'palestine', 'iran', 'north korea', 'south korea', 'japan', 'india',
        'brazil', 'mexico', 'canada', 'australia', 'germany', 'france', 'uk',
        'united kingdom', 'italy', 'spain', 'poland', 'turkey', 'saudi arabia',
        'egypt', 'nigeria', 'south africa', 'congo', 'democratic republic',
        'europe', 'asia', 'africa', 'middle east', 'latin america',
        
        # News events and actions
        'war', 'conflict', 'crisis', 'attack', 'bombing', 'shooting', 'explosion',
        'election', 'vote', 'referendum', 'summit', 'meeting', 'talks', 'negotiations',
        'protest', 'demonstration', 'strike', 'riot', 'coup', 'revolution',
        'outbreak', 'epidemic', 'pandemic', 'disaster', 'earthquake', 'hurricane',
        'flood', 'drought', 'wildfire', 'tsunami', 'volcano', 'tornado',
        
        # Economic terms
        'recession', 'inflation', 'unemployment', 'gdp', 'growth', 'decline',
        'market crash', 'boom', 'bust', 'currency', 'dollar', 'euro', 'pound',
        'yen', 'yuan', 'cryptocurrency', 'bitcoin', 'ethereum', 'crypto',
        'stock', 'shares', 'trading', 'investment', 'banking', 'finance',
        
        # Technology and innovation
        'ai', 'artificial intelligence', 'machine learning', 'blockchain',
        'quantum', 'nuclear', 'space', 'rocket', 'satellite', 'internet',
        'cyber', 'hack', 'breach', 'security', 'privacy', 'data',
        'unveiled', 'launched', 'released', 'announced', 'developed',
        'invented', 'discovered', 'breakthrough', 'innovation', 'patent',
        
        # Social and cultural
        'immigration', 'refugee', 'border', 'security', 'terrorism',
        'corruption', 'scandal', 'investigation', 'arrest', 'trial',
        'verdict', 'sentence', 'prison', 'jail', 'court', 'judge',
        'human rights', 'freedom', 'democracy', 'authoritarian', 'dictator',
        
        # Time indicators
        'breaking', 'urgent', 'developing', 'latest', 'recent', 'today',
        'yesterday', 'tomorrow', 'this week', 'this month', 'this year',
        'just in', 'live', 'ongoing', 'continuing', 'update',
        
        # Media and communication
        'reports', 'sources', 'officials', 'spokesperson', 'statement',
        'press conference', 'briefing', 'interview', 'exclusive',
        'confirmed', 'denied', 'warned', 'urged', 'called', 'said',
        'announced', 'declared', 'revealed', 'exposed', 'leaked',
    ]
    
    # Check if any strong indicator is present
    for indicator in strong_indicators:
        if indicator in t:
            return True
    
    # Check for news-like patterns
    import re
    news_patterns = [
        r'\w+\s+(announces?|declares?|confirms?|denies?|warns?|urges?|calls?|says?)',
        r'\w+\s+(unveiled?|launched?|released?|developed?|invented?|discovered?)',
        r'\w+\s+(dinned?|visited?|met|spoke|addressed?|attended?|participated?)',
        r'\w+\s+(crashes?|rises?|falls?|increases?|decreases?|grows?|shrinks?)',
        r'\w+\s+(hits?|strikes?|affects?|impacts?|influences?)',
        r'\w+\s+(outbreak|epidemic|pandemic|crisis|emergency)',
        r'\w+\s+(election|vote|referendum|summit|meeting|talks?)',
        r'\w+\s+(protest|demonstration|strike|riot)',
        r'\w+\s+(attack|bombing|shooting|explosion)',
        r'\w+\s+(discovery|breakthrough|invention|innovation)',
    ]
    
    for pattern in news_patterns:
        if re.search(pattern, t):
            return True
    
    return False

def apply_proactive_default_rules(topic: str) -> tuple[bool, float, str]:
    """
    Proactive default rules - DEFAULT TO ACCEPTANCE unless clearly non-news.
    This is the final fallback that should accept most legitimate topics.
    """
    t = topic.strip().lower()
    
    # Only reject if we're absolutely certain it's not news
    # This is a very permissive approach
    
    # Rule 1: Reject obvious non-news (already handled by is_obviously_not_news)
    # Rule 2: Reject very personal statements (but be careful not to reject news)
    personal_patterns = [
        # Very personal statements that are clearly not news
        r'\b(i am|i\'m|i will|i\'ll|i went|i go|i have|i\'ve|i want|i need|i like|i love|i hate)\b.*\b(going to|went to|coming from|leaving for|heading to)\b',
        r'\b(my cat|my dog|my car|my house|my family|my friend|my boyfriend|my girlfriend)\b',
        r'\b(this is|that is|here is|there is)\b.*\b(my|mine|me)\b',
        r'\b(what should i|how do i|where can i|when should i|why did i)\b',
        r'\b(can you help|do you know|is it ok|should i)\b',
        r'\b(how are you|what\'s up|hello|hi there|good morning|good evening|good night)\b',
        r'\b(thanks|thank you|please|sorry|excuse me)\b',
    ]
    
    import re
    for pattern in personal_patterns:
        if re.search(pattern, t, re.IGNORECASE):
            return False, 0.8, "Personal statement (not news)"
    
    # Rule 3: Accept anything else (ultra-permissive)
    # If we've made it this far, it's likely news or news-related
    return True, 0.7, "Default acceptance (proactive approach)"


def validate_topic_with_patterns(topic: str) -> bool:
    """
    Additional pattern-based validation for edge cases.
    """
    t = topic.strip().lower()
    
    # Pattern 1: News-like structure (Subject + Action/Event)
    # Examples: "Biden announces", "Stock market crashes", "Earthquake hits"
    import re
    news_patterns = [
        r'\w+\s+(announces?|declares?|confirms?|denies?|warns?|urges?|calls?|says?)',
        r'\w+\s+(crashes?|rises?|falls?|increases?|decreases?|grows?|shrinks?)',
        r'\w+\s+(hits?|strikes?|affects?|impacts?|influences?)',
        r'\w+\s+(outbreak|epidemic|pandemic|crisis|emergency)',
        r'\w+\s+(election|vote|referendum|summit|meeting|talks?)',
        r'\w+\s+(protest|demonstration|strike|riot)',
        r'\w+\s+(attack|bombing|shooting|explosion)',
        r'\w+\s+(discovery|breakthrough|invention|innovation)',
        # Technology and business patterns
        r'(apple|google|microsoft|amazon|meta|tesla)\s+(unveiled?|launched?|released?|announced?)',
        r'\w+\s+(unveiled?|launched?|released?|developed?|invented?|discovered?)',
        # Political and public figure patterns
        r'(trump|biden|president|minister|senator|governor)\s+(dinned?|visited?|met|spoke|addressed?)',
        r'\w+\s+(dinned?|visited?|met|spoke|addressed?|attended?|participated?)',
    ]
    
    for pattern in news_patterns:
        if re.search(pattern, t):
            print(f"DEBUG: Topic accepted - matched news pattern: '{pattern}'")
            return True
    
    # Pattern 2: Geographic + Event structure
    # Examples: "Ukraine war", "Congo outbreak", "China trade"
    geo_event_pattern = r'^\w+\s+(war|conflict|crisis|outbreak|election|protest|attack|disaster|breakthrough)'
    if re.search(geo_event_pattern, t):
        print(f"DEBUG: Topic accepted - matched geo-event pattern")
        return True
    
    # Pattern 3: Time-sensitive indicators
    time_indicators = ['latest', 'breaking', 'urgent', 'developing', 'recent', 'new', 'today', 'yesterday']
    for indicator in time_indicators:
        if indicator in t:
            print(f"DEBUG: Topic accepted - matched time indicator: '{indicator}'")
            return True
    
    return False

def validate_topic_with_learning(topic: str) -> bool:
    """
    Learning-based validation using historical data and user feedback.
    """
    # Check if similar topics were previously accepted
    # This could be expanded to use ML models trained on historical data
    
    # For now, return None to indicate no learning-based decision
    return None

def log_validation_feedback(topic: str, was_accepted: bool, user_feedback: str = None):
    """
    Log user feedback about topic validation for continuous improvement.
    """
    feedback_data = {
        'topic': topic,
        'was_accepted': was_accepted,
        'user_feedback': user_feedback,
        'timestamp': datetime.now().isoformat()
    }
    
    # Store feedback for analysis (could be saved to database)
    print(f"DEBUG: Validation feedback logged: {feedback_data}")
    
    # This could be used to improve the validation system over time
    # For example, if users consistently say a topic should be accepted/rejected,
    # we could adjust the validation logic accordingly

def get_validation_suggestions(topic: str) -> list[str]:
    """
    Provide suggestions for improving topic relevance if rejected.
    """
    suggestions = []
    t = topic.strip().lower()
    
    # Check if it's a personal statement
    personal_indicators = ['i am', 'i\'m', 'i will', 'i went', 'i go', 'my', 'me', 'going to', 'how are you']
    if any(indicator in t for indicator in personal_indicators):
        suggestions.append("This appears to be a personal statement. Try news topics like 'Ebola outbreak in Congo' or 'Ukraine war updates'")
        suggestions.append("Focus on public events, politics, economy, world affairs, disasters, or current events")
        return suggestions
    
    if len(t.split()) < 2:
        suggestions.append("Try adding more descriptive words (e.g., 'Biden announces new policy' instead of 'Biden')")
    
    if not any(word in t for word in ['outbreak', 'crisis', 'election', 'war', 'protest', 'disaster', 'breakthrough']):
        suggestions.append("Consider adding action words like 'outbreak', 'crisis', 'election', 'war', 'protest'")
    
    if not any(word in t for word in ['latest', 'breaking', 'urgent', 'developing', 'recent']):
        suggestions.append("Add time-sensitive words like 'latest', 'breaking', 'urgent', 'developing'")
    
    if not any(word in t for word in ['ukraine', 'china', 'russia', 'congo', 'nigeria', 'brazil']):
        suggestions.append("Include geographic context (e.g., 'Ukraine war', 'Congo outbreak')")
    
    return suggestions

def validate_topic_with_user_override(topic: str, user_override: bool = None) -> tuple[bool, float, str]:
    """
    Validate topic with optional user override for edge cases.
    """
    if user_override is not None:
        # User explicitly overrides the validation
        confidence = 0.8 if user_override else 0.2
        reason = "User override"
        print(f"DEBUG: User override applied: {user_override}")
        return user_override, confidence, reason
    
    # Use normal validation
    return is_relevant_topic(topic)

def get_topic_validation_info(topic: str) -> dict:
    """
    Get comprehensive validation information for a topic.
    """
    is_relevant, confidence, reason = is_relevant_topic(topic)
    
    return {
        'topic': topic,
        'is_relevant': is_relevant,
        'confidence': confidence,
        'reason': reason,
        'suggestions': get_validation_suggestions(topic) if not is_relevant else [],
        'can_override': confidence < 0.8,  # Allow override for uncertain cases
        'validation_timestamp': datetime.now().isoformat()
    }

class NewsTopicValidationAgent:
    """
    Dedicated agent for validating news topics using Gemini AI.
    Simple interface: returns True/False with clear error messages.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not found")
        
        from google import genai
        self.client = genai.Client(api_key=self.api_key)
    
    def validate_topic(self, topic: str) -> tuple[bool, str]:
        """
        Validates if a topic is suitable for news generation.
        Returns (is_valid, error_message)
        """
        try:
            # Clean and validate input
            topic = topic.strip()
            if not topic:
                return False, "Topic cannot be empty"
            
            if len(topic) < 3:
                return False, "Topic must be at least 3 characters long"
            
            # Call Gemini for validation
            prompt = f"""
            You are a news editor. Determine if this topic is suitable for news reporting.

            VALID NEWS TOPICS:
            - Current events, breaking news, ongoing stories
            - Politics, government, elections, policy changes  
            - Economy, business, markets, financial news
            - International affairs, conflicts, diplomacy
            - Natural disasters, emergencies, public safety
            - Health outbreaks, medical breakthroughs, public health
            - Technology developments, scientific discoveries
            - Sports events, entertainment news, cultural events
            - Social issues, protests, human rights
            - Environmental news, climate change
            - Crime, legal proceedings, court cases
            - Education, research, academic news

            INVALID TOPICS:
            - Personal statements ("I am going to school")
            - Personal opinions ("I like pizza")
            - Private matters ("My cat is cute")
            - Questions ("How are you?")
            - Nonsensical text
            - Single words without context
            - Personal conversations or greetings

            Topic: "{topic}"

            Respond with ONLY: YES or NO
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt],
            )
            
            result = response.candidates[0].content.parts[0].text.strip().upper()
            
            if result == "YES":
                print(f"✅ NewsTopicValidationAgent: '{topic}' is VALID")
                return True, ""
            elif result == "NO":
                error_msg = f"This does not seem to be a valid topic"
                print(f"❌ NewsTopicValidationAgent: '{topic}' is INVALID")
                return False, error_msg
            else:
                print(f"⚠️ NewsTopicValidationAgent: Unexpected response '{result}' for topic '{topic}'")
                return False, f"Unable to validate topic. Please try a different topic."
                
        except Exception as e:
            print(f"🚨 NewsTopicValidationAgent error for '{topic}': {e}")
            return False, f"Validation error. Please try again."

# Global validation agent instance
validation_agent = None

def get_validation_agent():
    """Get or create the validation agent instance."""
    global validation_agent
    if validation_agent is None:
        validation_agent = NewsTopicValidationAgent()
    return validation_agent

def validate_topic_with_ai_enhanced(topic: str) -> tuple[bool, float]:
    """
    Legacy function for backward compatibility.
    Now uses the NewsTopicValidationAgent.
    """
    try:
        agent = get_validation_agent()
        is_valid, error_msg = agent.validate_topic(topic)
        
        if is_valid:
            return True, 0.95
        else:
            return False, 0.95
            
    except Exception as e:
        print(f"DEBUG: Validation agent error: {e}")
        return None, 0.0

def validate_topic_with_learning_enhanced(topic: str) -> tuple[bool, float]:
    """
    Learning-based validation with confidence scoring.
    """
    # This could be enhanced to use ML models trained on historical data
    # For now, return None to indicate no learning-based decision
    return None, 0.0

def validate_topic_with_keywords(topic: str) -> bool:
    """
    Fallback keyword-based validation with enhanced patterns.
    """
    t = topic.strip().lower()
    
    # Enhanced news indicators (keeping some key ones for fallback)
    news_indicators = [
        # Geographic/country names (expanded)
        'venezuela', 'ukraine', 'russia', 'china', 'iran', 'israel', 'palestine', 'syria', 'afghanistan',
        'north korea', 'cuba', 'mexico', 'canada', 'france', 'germany', 'uk', 'japan', 'india', 'brazil',
        'australia', 'south korea', 'taiwan', 'turkey', 'saudi arabia', 'egypt', 'nigeria', 'south africa',
        'congo', 'democratic republic', 'drc', 'central africa', 'west africa', 'east africa',
        
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
        'ebola', 'malaria', 'cholera', 'measles', 'polio', 'tuberculosis', 'hiv', 'aids',
        'covid', 'coronavirus', 'sars', 'mers', 'zika', 'dengue', 'yellow fever',
        
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
            print(f"DEBUG: Topic accepted - matched news indicator: '{indicator}'")
            return True
    
    # Additional health-related pattern matching
    health_patterns = ['outbreak', 'epidemic', 'pandemic', 'disease', 'virus', 'health', 'medical', 'hospital', 'doctor']
    for pattern in health_patterns:
        if pattern in t:
            print(f"DEBUG: Topic accepted - matched health pattern: '{pattern}'")
            return True
    
    # Allow topics that are 2+ words (likely to be descriptive news topics)
    if len(t.split()) >= 2:
        print(f"DEBUG: Topic accepted - 2+ words: {len(t.split())} words")
        return True
    
    # Allow single words that are clearly news-related
    clear_news_words = {
        'politics',"war","war",'economy', 'sports', 'technology', 'health', 'world', 'local', 'national',
        'international', 'business', 'finance', 'science', 'education', 'entertainment',
        'crime', 'law', 'military', 'defense', 'security', 'environment', 'climate',"international","trade"
    }
    
    if t in clear_news_words:
        print(f"DEBUG: Topic accepted - clear news word: '{t}'")
        return True
    
    # If we get here, it's likely not a news topic
    print(f"DEBUG: Topic rejected - no matching patterns found for: '{topic}'")
    return False

def categorize_topic(topic: str) -> str:
    """
    Categorizes a topic into one of the main news categories using AI.
    Falls back to keyword matching if AI fails.
    Returns the category name.
    """
    try:
        # Try AI-powered categorization first
        return categorize_topic_ai(topic)
    except Exception as e:
        print(f"AI categorization failed for '{topic}': {e}")
        # Fallback to keyword-based categorization
        return categorize_topic_keywords(topic)

def categorize_topic_ai(topic: str) -> str:
    """
    AI-powered categorization using Google's Gemini model.
    More accurate and handles context better than keyword matching.
    """
    import google.generativeai as genai
    from glconnect import config
    
    # Configure Gemini with memory-efficient settings
    generation_config = genai.types.GenerationConfig(
        max_output_tokens=1024,  # Limit output length
        temperature=0.7,  # Balanced creativity
        top_p=0.8,  # Focus on most likely tokens
        top_k=40  # Limit token selection
    )
    
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config=generation_config
    )
    
    prompt = f"""
    Categorize this news topic into exactly one of these categories:
    - Politics
    - Economy  
    - Sports
    - Technology
    - Health & Science
    - World & International
    - Crime & Law
    - Entertainment
    - Other
    
    Topic: "{topic}"
    
    Consider the context and meaning, not just keywords. 
    Return only the category name, nothing else.
    """
    
    response = model.generate_content(prompt)
    category = response.text.strip()
    
    # Validate the response
    valid_categories = ['Politics', 'Economy', 'Sports', 'Technology', 
                       'Health & Science', 'World & International', 
                       'Crime & Law', 'Entertainment', 'Other']
    
    if category in valid_categories:
        return category
    else:
        raise ValueError(f"Invalid category returned: {category}")

def categorize_topic_keywords(topic: str) -> str:
    """
    Fallback keyword-based categorization (original method).
    """
    import re
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
                    'smartphone', 'computer', 'robot', 'automation', 'blockchain']
    
    # Health and science
    health_keywords = ['health', 'medicine', 'medical', 'covid', 'pandemic', 'vaccine', 'public health',
                      'hospital', 'doctor', 'patient', 'disease', 'virus', 'outbreak', 'epidemic',
                      'science', 'space', 'nasa', 'climate', 'environment', 'weather', 'earthquake',
                      'hurricane', 'wildfire', 'tsunami', 'volcano', 'global warming', 'carbon']
    
    # World and international
    world_keywords = ['world', 'international', 'geopolitics', 'war', 'conflict', 'military', 'defense',
                     'security', 'terrorism', 'un', 'nato', 'sanctions', 'embargo', 'diplomacy',
                     'immigration', 'refugee', 'refugees', 'border', 'attack', 'bombing', 'shooting', 'crisis',
                     'tensions', 'peace', 'talks', 'negotiations', 'summit', 'meeting', 'ukraine', 'ukrainian']
    
    # Crime and law
    crime_keywords = ['crime', 'law', 'legal', 'court', 'lawsuit', 'police', 'trial', 'verdict',
                     'supreme court', 'arrest', 'sentence', 'prison', 'jail', 'corruption', 'scandal',
                     'investigation', 'evidence', 'witness', 'jury', 'judge', 'lawyer', 'attorney', 'killed', 'murder']
    
    # Entertainment
    entertainment_keywords = ['entertainment', 'movies', 'film', 'music', 'culture', 'festival', 'awards',
                             'oscar', 'grammy', 'celebrity', 'actor', 'singer', 'artist', 'director',
                             'producer', 'album', 'song', 'concert', 'theater', 'broadway', 'tv', 'show']
    
    # Helper function to check for word boundaries
    def has_keyword(text, keyword):
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text))
    
    # Check each category with word boundary matching
    for keyword in politics_keywords:
        if has_keyword(t, keyword):
            return 'Politics'
    
    for keyword in economy_keywords:
        if has_keyword(t, keyword):
            return 'Economy'
    
    for keyword in sports_keywords:
        if has_keyword(t, keyword):
            return 'Sports'
    
    for keyword in tech_keywords:
        if has_keyword(t, keyword):
            return 'Technology'
    
    for keyword in health_keywords:
        if has_keyword(t, keyword):
            return 'Health & Science'
    
    for keyword in world_keywords:
        if has_keyword(t, keyword):
            return 'World & International'
    
    for keyword in crime_keywords:
        if has_keyword(t, keyword):
            return 'Crime & Law'
    
    for keyword in entertainment_keywords:
        if has_keyword(t, keyword):
            return 'Entertainment'
    
    # Default to "Other" if no category matches
    return 'Other'

def track_search_analytics(topics: list[str]):
    """
    Tracks search analytics for the given topics with improved categorization.
    Now uses database for persistent storage.
    """
    from glconnect.models import db, SearchHistory, CategoryCount, TopicCount, DailySearchCount, CategoryTopic, CategorizationConfidence
    from glconnect import create_app
    
    current_time = datetime.now()
    current_date = current_time.strftime('%Y-%m-%d')
    
    # Create app context for database operations
    app = create_app()
    with app.app_context():
        try:
            for topic in topics:
                # Categorize the topic with confidence tracking
                category, confidence = categorize_topic_with_confidence(topic)
                
                # Add to search history
                search_entry = SearchHistory(
                    topic=topic,
                    timestamp=current_time,
                    date=current_date,
                    category=category,
                    confidence=confidence
                )
                db.session.add(search_entry)
                
                # Update category count
                category_count = CategoryCount.query.filter_by(category=category).first()
                if category_count:
                    category_count.count += 1
                    category_count.last_updated = current_time
                else:
                    category_count = CategoryCount(category=category, count=1)
                    db.session.add(category_count)
                
                # Update topic count
                topic_count = TopicCount.query.filter_by(topic=topic).first()
                if topic_count:
                    topic_count.count += 1
                    topic_count.last_updated = current_time
                else:
                    topic_count = TopicCount(topic=topic, count=1)
                    db.session.add(topic_count)
                
                # Update daily search count
                daily_count = DailySearchCount.query.filter_by(date=current_date).first()
                if daily_count:
                    daily_count.count += 1
                    daily_count.last_updated = current_time
                else:
                    daily_count = DailySearchCount(date=current_date, count=1)
                    db.session.add(daily_count)
                
                # Add to category topics (check if combination already exists)
                existing_category_topic = CategoryTopic.query.filter_by(
                    category=category, topic=topic
                ).first()
                if not existing_category_topic:
                    category_topic = CategoryTopic(category=category, topic=topic)
                    db.session.add(category_topic)
                
                # Track categorization confidence
                confidence_entry = CategorizationConfidence(
                    topic=topic,
                    category=category,
                    confidence=confidence,
                    timestamp=current_time
                )
                db.session.add(confidence_entry)
            
            # Commit all changes
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error tracking analytics: {e}")
            # Fallback to in-memory storage if database fails
            with _analytics_lock:
                for topic in topics:
                    analytics_data['search_history'].append({
                        'topic': topic,
                        'timestamp': current_time.isoformat(),
                        'date': current_date
                    })
                    
                    category, confidence = categorize_topic_with_confidence(topic)
                    analytics_data['category_counts'][category] += 1
                    analytics_data['topic_counts'][topic] += 1
                    analytics_data['daily_searches'][current_date] += 1
                    
                    if topic not in analytics_data['category_topics'][category]:
                        analytics_data['category_topics'][category].append(topic)
                    
                    if 'categorization_confidence' not in analytics_data:
                        analytics_data['categorization_confidence'] = []
                    
                    analytics_data['categorization_confidence'].append({
                        'topic': topic,
                        'category': category,
                        'confidence': confidence,
                        'timestamp': current_time.isoformat()
                    })

def categorize_topic_with_confidence(topic: str) -> tuple[str, float]:
    """
    Categorizes a topic and returns both category and confidence score.
    """
    try:
        # Try AI categorization first
        category = categorize_topic_ai(topic)
        confidence = 0.9  # High confidence for AI categorization
        return category, confidence
    except Exception as e:
        print(f"AI categorization failed for '{topic}': {e}")
        # Fallback to keyword categorization
        category = categorize_topic_keywords(topic)
        confidence = 0.6  # Lower confidence for keyword matching
        return category, confidence

def extract_audio_path_from_output(output_text):
    """Extract audio file path from agent output text or filesystem."""
    if not output_text:
        return None
    
    print(f"DEBUG: Looking for audio path in output: {output_text}")
    
    # Look for final news broadcast audio file in glconnect/static/audio/
    patterns = [
        r'glconnect/static/audio/final_news_broadcast[^\s]*\.mp3',
        r'glconnect/static/audio/.*\.mp3',
        r'static/audio/.*\.mp3',
        r'final_news_broadcast[^\s]*\.mp3'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, output_text)
        if match:
            print(f"DEBUG: Found audio path with pattern {pattern}: {match.group(0)}")
            return match.group(0)
    
    # If no path found in output, check filesystem for generated files
    print("DEBUG: No audio path found in output, checking filesystem...")
    audio_dir = "glconnect/static/audio"
    if os.path.exists(audio_dir):
        # Look for final_news_broadcast files
        import glob
        final_broadcast_files = glob.glob(os.path.join(audio_dir, "final_news_broadcast*.mp3"))
        if final_broadcast_files:
            # Get the most recent file
            latest_file = max(final_broadcast_files, key=os.path.getctime)
            print(f"DEBUG: Found audio file in filesystem: {latest_file}")
            return latest_file
        
        # Look for any MP3 files as fallback
        mp3_files = glob.glob(os.path.join(audio_dir, "*.mp3"))
        if mp3_files:
            # Get the most recent file
            latest_file = max(mp3_files, key=os.path.getctime)
            print(f"DEBUG: Found MP3 file in filesystem: {latest_file}")
            return latest_file
    
    print("DEBUG: No audio path found in output or filesystem")
    return None

def cleanup_temp_audio_files():
    """Clean up temporary audio files, NEVER deleting jingle.wav or final_news_broadcast files."""
    audio_dir = "glconnect/static/audio"
    if not os.path.exists(audio_dir):
        return
    
    print("DEBUG: Cleaning up temporary audio files...")
    print("DEBUG: PROTECTED FILES: jingle.wav and final_news_broadcast*.mp3 will NEVER be deleted")
    files_deleted = 0
    
    for filename in os.listdir(audio_dir):
        file_path = os.path.join(audio_dir, filename)
        
        # NEVER delete jingle.wav - this is a protected file
        if filename == "jingle.wav":
            print(f"DEBUG: PROTECTED - Keeping jingle.wav")
            continue
            
        # NEVER delete final news broadcast files - these are protected files
        if filename.startswith("final_news_broadcast"):
            print(f"DEBUG: PROTECTED - Keeping final broadcast: {filename}")
            continue
            
        # Only delete temporary audio files (intro, outro, transition, thank_you, category-specific files)
        if (filename.endswith(('.mp3', '.wav', '.ogg', '.aiff')) and 
            any(pattern in filename for pattern in ['intro_', 'outro_', 'transition_', 'thank_you_', '_audio.mp3', 'sports_', 'politics_', 'tech_', 'health_', 'finance_'])):
            try:
                os.remove(file_path)
                print(f"DEBUG: Deleted temporary audio file: {filename}")
                files_deleted += 1
            except Exception as e:
                print(f"DEBUG: Error deleting {filename}: {e}")
        else:
            print(f"DEBUG: Skipping file (not a temporary file): {filename}")
    
    print(f"DEBUG: Cleaned up {files_deleted} temporary audio files")
    print("DEBUG: PROTECTED FILES REMAIN: jingle.wav and final_news_broadcast*.mp3")

def run_generate_broadcast(task_id, topics):
    """Wrapper function to run generate_broadcast and store the result."""
    import time
    import threading
    import signal
    import sys
    
    # Import tasks and _tasks_lock at the function level
    from glconnect.news_routes import tasks, _tasks_lock
    
    print(f"DEBUG: run_generate_broadcast started for task {task_id} with topics: {topics}")
    print(f"DEBUG: Thread ID: {threading.current_thread().ident}, Main thread: {threading.main_thread().ident}")
    print(f"DEBUG: About to start signal handler setup...")
    
    # Set up graceful shutdown handling
    def signal_handler(signum, frame):
        print(f"DEBUG: Received signal {signum}, gracefully shutting down task {task_id}")
        try:
            update_task_in_db(task_id, 
                             status='failed',
                             progress=0,
                             current_step='Task cancelled due to system shutdown',
                             last_heartbeat=datetime.now())
        except:
            pass
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown (only in main thread)
    try:
        # Check if we're in the main thread before setting signal handlers
        import threading
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            print("DEBUG: Signal handlers registered successfully")
        else:
            print("DEBUG: Running in background thread - signal handlers not set")
    except (ValueError, AttributeError) as e:
        # Signal handlers can only be set in the main thread
        # This is expected when running in a background thread
        print(f"DEBUG: Signal handlers not set (running in background thread): {e}")
    except Exception as e:
        print(f"DEBUG: Error setting signal handlers: {e}")
    
    # Update task status with progress
    update_task_in_db(task_id, 
                     status='running',
                     progress=0,
                     current_step='Initializing news generation...',
                     last_heartbeat=datetime.now())
    
    with _tasks_lock:
        if task_id in tasks:
            tasks[task_id]['status'] = 'running'
            tasks[task_id]['progress'] = 0
            tasks[task_id]['current_step'] = 'Initializing news generation...'
    
    # Check memory usage at start of news generation
    try:
        import psutil
        import gc
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory at start of news generation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        
        # If memory usage is too high, try emergency cleanup first, then abort
        if memory_info.percent > 85:  # Conservative threshold for production stability
            print(f"WARNING: Memory usage too high ({memory_info.percent}%) - attempting emergency cleanup...")
            
            # Emergency cleanup sequence
            try:
                # Clear any cached data
                import sys
                if hasattr(sys, '_clear_type_cache'):
                    sys._clear_type_cache()
                
                # Force aggressive garbage collection multiple times
                for i in range(5):
                    gc.collect()
                    gc.collect()
                
                # Clear module caches
                import importlib
                for module_name in list(sys.modules.keys()):
                    if module_name.startswith('glconnect.') and 'cache' in module_name.lower():
                        try:
                            del sys.modules[module_name]
                        except:
                            pass
                
                # Try memory trimming on Linux
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                except:
                    pass
                
                # Clear any large objects in memory
                try:
                    from glconnect.news_routes import tasks
                    with _tasks_lock:
                        # Remove old completed tasks to free memory
                        current_time = datetime.now()
                        tasks_to_remove = []
                        for tid, task_data in tasks.items():
                            if (task_data.get('status') in ['completed', 'failed'] and 
                                task_data.get('created_at') and 
                                (current_time - task_data['created_at']).total_seconds() > 3600):  # 1 hour old
                                tasks_to_remove.append(tid)
                        
                        for tid in tasks_to_remove:
                            del tasks[tid]
                            print(f"DEBUG: Removed old task {tid} to free memory")
                except:
                    pass
                
            except Exception as e:
                print(f"DEBUG: Error during emergency cleanup: {e}")
            
            # Check memory again after cleanup
            memory_info_after = psutil.virtual_memory()
            print(f"DEBUG: Memory after emergency cleanup - Used: {memory_info_after.used / 1024 / 1024:.1f}MB, Percent: {memory_info_after.percent}%")
            
            if memory_info_after.percent > 98:  # Only abort if memory is critically high after cleanup
                print(f"ERROR: Memory usage still too high after emergency cleanup ({memory_info_after.percent}%) - aborting news generation")
                
                # Log memory state for debugging
                try:
                    process = psutil.Process(os.getpid())
                    process_memory = process.memory_info()
                    print(f"DEBUG: Process memory - RSS: {process_memory.rss / 1024 / 1024:.1f}MB, VMS: {process_memory.vms / 1024 / 1024:.1f}MB")
                except:
                    pass
                
                error_message = f'Memory usage too high ({memory_info_after.percent}%) - please try again later'
                update_task_in_db(task_id, 
                                 status='failed',
                                 progress=0,
                                 current_step=error_message,
                                 error=error_message,
                                 failed_at=datetime.now(),
                                 last_heartbeat=datetime.now())
                return
            else:
                print(f"INFO: Memory usage reduced to {memory_info_after.percent}% after emergency cleanup - proceeding")
        
        # Force garbage collection if memory is high
        if memory_info.percent > 80:
            print("DEBUG: High memory usage detected - forcing garbage collection")
            gc.collect()
            
    except ImportError:
        print("DEBUG: psutil not available - skipping memory check")
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
    
    # Set up timeout using threading (works in any thread)
    timeout_seconds = 600  # 10 minutes - increased for complex news generation
    timeout_occurred = threading.Event()
    
    def timeout_handler():
        time.sleep(timeout_seconds)
        timeout_occurred.set()
    
    # Start timeout thread
    timeout_thread = threading.Thread(target=timeout_handler)
    timeout_thread.daemon = True
    timeout_thread.start()
    
    try:
        # Update progress
        update_task_in_db(task_id, 
                         progress=10,
                         current_step='Categorizing topics...',
                         last_heartbeat=datetime.now())
        
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]['progress'] = 10
                tasks[task_id]['current_step'] = 'Categorizing topics...'
        
        # Use the ADK agent system for sophisticated news generation
        print("Using ADK agent system with Google Cloud TTS...")
        print("Following pattern: jingle → intro → transition → report → thank you → outro → jingle")
        
        # Run the ADK agent system directly (no threading needed)
        print(f"Starting ADK agent news generation for topics: {topics}")
        
        # Check for timeout before starting
        if timeout_occurred.is_set():
            raise TimeoutError("News generation timed out before starting")
        
        # Add periodic timeout checks during generation
        def check_timeout_periodically():
            while not timeout_occurred.is_set():
                time.sleep(30)  # Check every 30 seconds
                if timeout_occurred.is_set():
                    print("DEBUG: Timeout detected during generation, attempting graceful shutdown")
                    break
        
        # Check memory before generation
        try:
            memory_info = psutil.virtual_memory()
            if memory_info.percent > 85:  # Conservative threshold for production stability
                print(f"ERROR: Memory usage too high during generation ({memory_info.percent}%) - aborting")
                error_message = f'Memory usage too high ({memory_info.percent}%) - please try again later'
                update_task_in_db(task_id, 
                                 status='failed',
                                 progress=20,
                                 current_step=error_message,
                                 error=error_message,
                                 failed_at=datetime.now(),
                                 last_heartbeat=datetime.now())
                return
            elif memory_info.percent > 70:  # Lowered warning threshold
                print(f"WARNING: High memory usage during generation ({memory_info.percent}%) - forcing cleanup")
                # Force cleanup during generation
                gc.collect()
                gc.collect()
                gc.collect()
        except:
            pass
        
        # Update progress before generation
        update_task_in_db(task_id, 
                         progress=20,
                         current_step=f'Generating news content for {len(topics)} topics...',
                         last_heartbeat=datetime.now())
        
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]['progress'] = 20
                tasks[task_id]['current_step'] = f'Generating news content for {len(topics)} topics...'
                tasks[task_id]['last_heartbeat'] = datetime.now()  # Add heartbeat
        
        try:
            # Check timeout before each major operation
            if timeout_occurred.is_set():
                raise TimeoutError("News generation timed out during execution")
            
            print(f"DEBUG: About to call generate_broadcast with topics: {topics}, task_id: {task_id}")
            
            # Update progress before calling
            update_task_in_db(task_id, 
                             progress=10,
                             current_step='Starting memory-optimized news generation...',
                             last_heartbeat=datetime.now())
            
            output = generate_broadcast(topics, task_id=task_id)
            print(f"DEBUG: generate_broadcast completed, output type: {type(output)}")
            
            # Update progress after completion
            update_task_in_db(task_id, 
                             progress=90,
                             current_step='News generation completed',
                             last_heartbeat=datetime.now())
        except RuntimeError as e:
            if "cannot schedule new futures after interpreter shutdown" in str(e):
                print(f"DEBUG: Interpreter shutdown detected during news generation: {e}")
                raise Exception("News generation failed: Interpreter is shutting down")
            else:
                raise e
        
        # Check for timeout after generation
        if timeout_occurred.is_set():
            raise TimeoutError("News generation timed out during processing")
        
        # Force garbage collection after text generation
        try:
            import gc
            gc.collect()
            memory_info = psutil.virtual_memory()
            print(f"DEBUG: Memory after text generation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
            
            # Log memory usage to file for analysis
            try:
                with open('memory_usage.log', 'a') as f:
                    f.write(f"{datetime.now().isoformat()},text_generation,{memory_info.percent:.1f},{memory_info.used / 1024 / 1024:.1f}\n")
            except:
                pass
        except:
            pass
        
        # Update progress after generation
        update_task_in_db(task_id, 
                         progress=70,
                         current_step='Text generation completed, processing audio...',
                         last_heartbeat=datetime.now())
        
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]['progress'] = 70
                tasks[task_id]['current_step'] = 'Text generation completed, processing audio...'
                tasks[task_id]['last_heartbeat'] = datetime.now()  # Add heartbeat
        
        print("ADK agent system completed successfully")
        print(f"DEBUG: Output type: {type(output)}")
        print(f"DEBUG: Output content: {str(output)[:500]}...")
        print(f"DEBUG: Output is None: {output is None}")
        print(f"DEBUG: Output is dict: {isinstance(output, dict)}")
        print(f"DEBUG: Output keys: {list(output.keys()) if isinstance(output, dict) else 'Not a dict'}")
        
        # Handle both string and dictionary outputs
        if output is None:
            print("DEBUG: generate_broadcast returned None - no topics provided")
            with _tasks_lock:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['failed_at'] = datetime.now()
                tasks[task_id]['error'] = "No topics provided for news generation"
            return
        elif isinstance(output, dict):
            print(f"Output from generate_broadcast (dict): {output}")
            
            # Check for error first
            if 'error' in output:
                error_message = output['error']
                print(f"DEBUG: generate_broadcast returned error: {error_message}")
                with _tasks_lock:
                    tasks[task_id]['status'] = 'failed'
                    tasks[task_id]['failed_at'] = datetime.now()
                    tasks[task_id]['error'] = error_message
                return
            
            audio_file_path = output.get('audio_file')
            summary = output.get('summary', '')
            
            if not audio_file_path:
                print("DEBUG: No audio_file_path in output, trying fallback")
                # Fallback: look for audio files in filesystem
                audio_file_path = extract_audio_path_from_output("")
                if not audio_file_path:
                    print("DEBUG: Fallback failed - no audio file found")
                    raise AudioFilePathNotFound("Audio file path not found in output")
                else:
                    print(f"DEBUG: Fallback successful - found audio file: {audio_file_path}")
            else:
                print(f"DEBUG: Audio file path from output: {audio_file_path}")
            
            # Debug path information
            print(f"DEBUG: Current working directory: {os.getcwd()}")
            print(f"DEBUG: Audio file path to check: {audio_file_path}")
            print(f"DEBUG: Audio file path exists: {os.path.exists(audio_file_path)}")
            print(f"DEBUG: Audio file path is absolute: {os.path.isabs(audio_file_path)}")
            
            # Try to resolve the path if it's relative
            if not os.path.isabs(audio_file_path):
                abs_audio_file_path = os.path.abspath(audio_file_path)
                print(f"DEBUG: Resolved absolute path: {abs_audio_file_path}")
                print(f"DEBUG: Resolved path exists: {os.path.exists(abs_audio_file_path)}")
                if os.path.exists(abs_audio_file_path):
                    audio_file_path = abs_audio_file_path
                    print(f"DEBUG: Using resolved absolute path: {audio_file_path}")
            
            # Verify the audio file exists and has content before marking as completed
            # Add retry mechanism in case file is still being written
            max_retries = 10
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                if os.path.exists(audio_file_path):
                    file_size = os.path.getsize(audio_file_path)
                    if file_size > 0:
                        print(f"DEBUG: Audio file verified - {audio_file_path} ({file_size} bytes)")
                        break
                    else:
                        print(f"DEBUG: Audio file exists but is empty (0 bytes), attempt {attempt + 1}/{max_retries}")
                else:
                    print(f"DEBUG: Audio file does not exist yet, attempt {attempt + 1}/{max_retries}")
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
            else:
                # If we get here, all retries failed
                if not os.path.exists(audio_file_path):
                    raise AudioFilePathNotFound(f"Audio file does not exist after {max_retries} attempts: {audio_file_path}")
                else:
                    file_size = os.path.getsize(audio_file_path)
                    raise AudioFilePathNotFound(f"Audio file is empty (0 bytes) after {max_retries} attempts: {audio_file_path}")
            
            # Convert the file path to a URL that can be served by Flask
            filename = os.path.basename(audio_file_path)
            # Ensure filename doesn't contain path separators
            filename = filename.replace('\\', '/').split('/')[-1]
            audio_url = f"/routes2/news/audio/{filename}"
            print(f"DEBUG: Generated audio URL: {audio_url}")
            print(f"DEBUG: Audio filename: {filename}")
            print(f"DEBUG: Original audio_file_path: {audio_file_path}")
            
            # Store the result with the extracted audio path
            print(f"DEBUG: Storing result for task {task_id}")
            print(f"DEBUG: Audio file path: {audio_file_path}")
            print(f"DEBUG: Summary length: {len(summary) if summary else 'None'}")
            print(f"DEBUG: Audio file exists: {os.path.exists(audio_file_path) if audio_file_path else 'No path'}")
            
            # Update database
            update_task_in_db(task_id, 
                             status='completed',
                             completed_at=datetime.now(),
                             result={
                                 'audio_file_path': audio_file_path,
                                 'output_text': summary
                             })
            
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['completed_at'] = datetime.now()
                tasks[task_id]['result'] = {
                    'audio_file_path': audio_file_path,
                    'output_text': summary
                }
                tasks[task_id]['summary'] = summary
                # Also store the audio URL for the UI
                tasks[task_id]['audio_file'] = audio_url
                print(f"DEBUG: Result stored for task {task_id}")
                print(f"DEBUG: Stored result keys: {list(tasks[task_id]['result'].keys())}")
                print(f"DEBUG: Audio file path in result: {tasks[task_id]['result'].get('audio_file_path')}")
                print(f"DEBUG: Summary length: {len(tasks[task_id]['summary'])}")
            
            # Clean up old audio files after successful generation (but keep the current one)
            cleanup_old_audio_files()
            
            # Force garbage collection to free memory after task completion
            import gc
            gc.collect()
            print(f"DEBUG: Garbage collection completed for task {task_id}")
            
            # Clean up temporary audio files (jingle.wav and final_news_broadcast*.mp3 are NEVER deleted)
            cleanup_temp_audio_files()
            
            print("ADK agent system completed successfully!")
            return
        elif isinstance(output, str):
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
                    print(f"DEBUG: Using default audio path: {audio_file_path}")
                else:
                    # Look for any .mp3 file in the audio directory
                    audio_dir = "glconnect/static/audio"
                    if os.path.exists(audio_dir):
                        for file in os.listdir(audio_dir):
                            if file.endswith('.mp3') and file != "jingle.wav":
                                audio_file_path = os.path.join(audio_dir, file)
                                print(f"DEBUG: Found audio file: {audio_file_path}")
                                break
                
                if not audio_file_path:
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
            
            # Debug path information
            print(f"DEBUG: Current working directory: {os.getcwd()}")
            print(f"DEBUG: Audio file path to check: {audio_file_path}")
            print(f"DEBUG: Audio file path exists: {os.path.exists(audio_file_path)}")
            print(f"DEBUG: Audio file path is absolute: {os.path.isabs(audio_file_path)}")
            
            # Try to resolve the path if it's relative
            if not os.path.isabs(audio_file_path):
                abs_audio_file_path = os.path.abspath(audio_file_path)
                print(f"DEBUG: Resolved absolute path: {abs_audio_file_path}")
                print(f"DEBUG: Resolved path exists: {os.path.exists(abs_audio_file_path)}")
                if os.path.exists(abs_audio_file_path):
                    audio_file_path = abs_audio_file_path
                    print(f"DEBUG: Using resolved absolute path: {audio_file_path}")
            
            # Verify the audio file exists and has content before marking as completed
            # Add retry mechanism in case file is still being written
            max_retries = 10
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                if os.path.exists(audio_file_path):
                    file_size = os.path.getsize(audio_file_path)
                    if file_size > 0:
                        print(f"DEBUG: Audio file verified - {audio_file_path} ({file_size} bytes)")
                        break
                    else:
                        print(f"DEBUG: Audio file exists but is empty (0 bytes), attempt {attempt + 1}/{max_retries}")
                else:
                    print(f"DEBUG: Audio file does not exist yet, attempt {attempt + 1}/{max_retries}")
                
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
            else:
                # If we get here, all retries failed
                if not os.path.exists(audio_file_path):
                    raise AudioFilePathNotFound(f"Audio file does not exist after {max_retries} attempts: {audio_file_path}")
                else:
                    file_size = os.path.getsize(audio_file_path)
                    raise AudioFilePathNotFound(f"Audio file is empty (0 bytes) after {max_retries} attempts: {audio_file_path}")
            
            # Convert the file path to a URL that can be served by Flask
            filename = os.path.basename(audio_file_path)
            audio_url = f"/routes2/news/audio/{filename}"
            
            # Store the result with the extracted audio path
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['completed_at'] = datetime.now()
                tasks[task_id]['audio_file'] = audio_url
                tasks[task_id]['summary'] = ""
            
            # Clean up old audio files after successful generation (but keep the current one)
            cleanup_old_audio_files()
            
            # Clean up temporary audio files (jingle.wav and final_news_broadcast*.mp3 are NEVER deleted)
            cleanup_temp_audio_files()
            
            print("ADK agent system completed successfully!")
            return
        else:
            # Handle dictionary output (if the agent ever returns one)
            audio_file_path = output.get('final_broadcast_audio_output', {}).get('combined_audio_filepath')
            if not audio_file_path:
                raise AudioFilePathNotFound("Audio file path not found in output")
            
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['completed_at'] = datetime.now()
                tasks[task_id]['result'] = output
            
            # Clean up old audio files after successful generation
            cleanup_old_audio_files()
            print("ADK agent system completed successfully!")
            return
            
    except TimeoutError as e:
        print(f"TIMEOUT in news generation: {e}")
        print(f"Timeout occurred after {timeout_seconds} seconds")
        
        # Update task status for timeout
        update_task_in_db(task_id, 
                         status='failed',
                         failed_at=datetime.now(),
                         error=f"News generation timed out after {timeout_seconds} seconds. Please try again with fewer topics or simpler content.")
        
        with _tasks_lock:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['failed_at'] = datetime.now()
            tasks[task_id]['error'] = f"News generation timed out after {timeout_seconds} seconds. Please try again with fewer topics or simpler content."
            print(f"DEBUG: Task {task_id} marked as failed due to timeout")
        return
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        print(f"ERROR in ADK agent news generation: {error_message}")
        print(f"ERROR type: {error_type}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"ERROR traceback: {traceback_str}")
        
        # Create detailed error message
        detailed_error = f"{error_type}: {error_message}"
        
        # Try simple fallback generation before marking as failed
        try:
            print("DEBUG: Attempting simple fallback news generation...")
            from glconnect.news_agent import generate_intelligent_fallback_content
            
            fallback_content = []
            for topic in topics:
                content = generate_intelligent_fallback_content(topic)
                fallback_content.append(content)
            
            # Create a simple broadcast structure
            fallback_output = {
                "broadcast_script": "\n\n".join(fallback_content),
                "audio_files": [],
                "combined_audio_filepath": "fallback_generation.mp3",
                "generation_method": "fallback_simple"
            }
            
            # Store the fallback result
            with _tasks_lock:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['completed_at'] = datetime.now()
                tasks[task_id]['result'] = fallback_output
                tasks[task_id]['generation_method'] = 'fallback_simple'
                print(f"DEBUG: Task {task_id} completed with fallback generation")
            
            # Update database
            update_task_in_db(task_id, 
                             status='completed',
                             completed_at=datetime.now(),
                             result=fallback_output)
            
            print("DEBUG: Fallback generation successful")
            return
            
        except Exception as fallback_error:
            print(f"DEBUG: Fallback generation also failed: {fallback_error}")
            fallback_error_type = type(fallback_error).__name__
            fallback_error_message = str(fallback_error)
            
            # Create comprehensive error message
            comprehensive_error = f"Primary error: {detailed_error}. Fallback error: {fallback_error_type}: {fallback_error_message}"
            
            # Update database
            update_task_in_db(task_id, 
                             status='failed',
                             failed_at=datetime.now(),
                             error=comprehensive_error)
            
            with _tasks_lock:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['failed_at'] = datetime.now()
                tasks[task_id]['error'] = comprehensive_error
                print(f"DEBUG: Task {task_id} marked as failed due to: {comprehensive_error}")
    finally:
        # Cancel the timeout thread
        timeout_occurred.set()

@news_bp.route('/')
def index():
    from .forms import KeywordForm
    form = KeywordForm()
    return render_template('newsgen.html', form=form)

@news_bp.route('/memory-status')
def memory_status():
    """Endpoint to check current memory usage with container-aware monitoring"""
    try:
        from glconnect.news_agent import get_memory_usage
        memory_percent = get_memory_usage()
        
        # Determine status
        if memory_percent >= 85:
            status = 'critical'
            message = 'Memory critically high - news generation blocked'
        elif memory_percent >= 70:
            status = 'warning'
            message = 'Memory high - news generation may be limited'
        elif memory_percent >= 50:
            status = 'caution'
            message = 'Memory moderate - monitoring'
        else:
            status = 'healthy'
            message = 'Memory healthy - news generation available'
        
        return jsonify({
            'status': status,
            'memory_percent': f"{memory_percent:.1f}%",
            'message': message,
            'can_generate_news': memory_percent < 70,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@news_bp.route('/debug/tasks')
def debug_tasks():
    """Endpoint to check current task status for debugging"""
    try:
        with _tasks_lock:
            task_info = {}
            for task_id, task_data in tasks.items():
                task_info[task_id] = {
                    'status': task_data.get('status', 'unknown'),
                    'created_at': task_data.get('created_at', 'unknown'),
                    'progress': task_data.get('progress', 0),
                    'current_step': task_data.get('current_step', 'unknown')
                }
            
            return jsonify({
                'total_tasks': len(tasks),
                'tasks': task_info,
                'memory_cleanup_safe': True
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@news_bp.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files from the glconnect/static/audio directory."""
    from flask import send_from_directory
    import os
    
    # Try multiple possible audio directory locations
    possible_dirs = [
        '/usr/src/appdir/glconnect/static/audio',  # Docker container path (most likely)
        os.path.join(os.getcwd(), 'glconnect', 'static', 'audio'),
        os.path.abspath('glconnect/static/audio'),
        './glconnect/static/audio',
        'glconnect/static/audio',  # Relative path from current directory
        '/app/glconnect/static/audio',  # Alternative Docker path
        '/appdir/glconnect/static/audio'  # Another alternative
    ]
    
    print(f"DEBUG: Looking for audio file: {filename}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    
    # First, try the exact Docker path that was mentioned in the error
    docker_path = f"/usr/src/appdir/glconnect/static/audio/{filename}"
    if os.path.exists(docker_path):
        print(f"DEBUG: Found audio file at exact Docker path: {docker_path}")
        return send_from_directory("/usr/src/appdir/glconnect/static/audio", filename)
    
    for audio_dir in possible_dirs:
        print(f"DEBUG: Checking directory: {audio_dir}")
        if os.path.exists(audio_dir):
            full_path = os.path.join(audio_dir, filename)
            print(f"DEBUG: Checking file: {full_path}")
            if os.path.exists(full_path):
                print(f"DEBUG: Found audio file at: {full_path}")
                return send_from_directory(audio_dir, filename)
            else:
                print(f"DEBUG: File not found in {audio_dir}")
        else:
            print(f"DEBUG: Directory does not exist: {audio_dir}")
    
    # If not found in standard locations, try to find the file anywhere
    print(f"DEBUG: File not found in standard locations, searching for: {filename}")
    import glob
    search_patterns = [
        f"**/glconnect/static/audio/{filename}",
        f"**/static/audio/{filename}",
        f"**/{filename}",
        f"/usr/src/appdir/**/{filename}",  # Specific Docker path pattern
        f"/usr/src/appdir/glconnect/static/audio/{filename}"  # Exact Docker path
    ]
    
    for pattern in search_patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            match = matches[0]
            audio_dir = os.path.dirname(match)
            print(f"DEBUG: Found audio file via search at: {match}")
            return send_from_directory(audio_dir, filename)
    
    print(f"ERROR: Audio file {filename} not found in any expected location")
    return "Audio file not found", 404

@news_bp.route('/broadcast', methods=['POST'])
def broadcast():
    try:
        print("DEBUG: News generation request received")
        data = request.get_json()
        
        if not data or 'topics' not in data:
            return jsonify({'error': 'No topics provided in request'}), 400
        
        # Handle both string and list inputs
        if isinstance(data['topics'], str):
            topics = [topic.strip() for topic in data['topics'].split(',')]
        else:
            topics = [topic.strip() for topic in data['topics']]
        
        print(f"DEBUG: Topics received: {topics}")
        
        # Enforce maximum topic limit (reduced for memory safety)
        if len(topics) > 5:
            return jsonify({
                'error': 'Maximum 5 topics allowed due to server memory constraints. Please reduce the number of topics and try again.',
                'details': f'Received {len(topics)} topics, maximum allowed is 5'
            }), 400
        
        # Check server health before processing using container-aware memory
        try:
            from glconnect.news_agent import get_memory_usage
            memory_percent = get_memory_usage()
            print(f"DEBUG: Pre-processing memory check - Percent: {memory_percent:.1f}%")
            
            # Block if memory usage is too high to prevent 502 errors
            if memory_percent >= 85:  # More aggressive threshold for 2GB containers
                print(f"CRITICAL: Memory usage too high ({memory_percent:.1f}%) - blocking to prevent 502 errors")
                return jsonify({
                    'error': 'Server memory is critically high. Please wait a moment for memory to free up, then try again.',
                    'details': f'Memory usage: {memory_percent:.1f}%'
                }), 503
            elif memory_percent > 70:  # More aggressive threshold for 2GB containers
                print(f"WARNING: Very high memory usage ({memory_percent:.1f}%) - forcing safe cleanup before proceeding")
                # Force garbage collection (safe - doesn't affect tasks)
                import gc
                gc.collect()
                gc.collect()
                
                # Clean up old completed tasks only (preserve running tasks)
                try:
                    print(f"DEBUG: Before cleanup - {len(tasks)} tasks in memory")
                    cleanup_old_completed_tasks()
                    print(f"DEBUG: After cleanup - {len(tasks)} tasks in memory")
                except Exception as e:
                    print(f"DEBUG: Task cleanup failed: {e}")
                
                # Check memory again after cleanup
                memory_info = psutil.virtual_memory()
                print(f"DEBUG: Memory after cleanup - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
                if memory_info.percent >= 95:
                    return jsonify({
                        'error': 'Server memory is critically high even after cleanup. Please try again in a moment.',
                        'details': f'Memory usage: {memory_info.percent}% (Available: {memory_info.available / 1024 / 1024:.1f}MB)'
                    }), 503
            elif memory_info.percent > 80:
                print(f"INFO: High memory usage ({memory_info.percent}%) - monitoring")
        except ImportError:
            print("DEBUG: psutil not available - skipping memory check")
        except Exception as e:
            print(f"DEBUG: Memory check failed: {e}")
        
        # Filter to only relevant topics
        relevant_topics = []
        for topic in topics:
            try:
                is_relevant, confidence, reason = is_relevant_topic(topic)
                if is_relevant:
                    relevant_topics.append(topic)
                else:
                    print(f"DEBUG: Topic '{topic}' rejected: {reason} (confidence: {confidence})")
            except Exception as e:
                print(f"ERROR: Failed to check topic relevance for '{topic}': {str(e)}")
                # Include topic anyway if relevance check fails
                relevant_topics.append(topic)

        if not relevant_topics:
            return jsonify({'error': 'No relevant news topics detected. Please enter news-related topics like politics, economy, sports, technology, health, world, etc.'}), 400

        # Track analytics for the search
        try:
            track_search_analytics(relevant_topics)
        except Exception as e:
            print(f"WARNING: Failed to track analytics: {str(e)}")

        # Note: Cleanup is now handled automatically and less aggressively
        # No need to clean up before creating new tasks

        task_id = str(uuid.uuid4())
        
        # Create task in database
        if not create_task_in_db(task_id, relevant_topics):
            print(f"ERROR: Failed to create task {task_id} in database, falling back to memory")
        
        # Also create in memory for backward compatibility
        with _tasks_lock:
            tasks[task_id] = {
                'status': 'running',
                'created_at': datetime.now(),
                'error': None  # Initialize error field
            }
            print(f"DEBUG: Created news task {task_id}. Total tasks: {len(tasks)}")
            print(f"DEBUG: Task {task_id} created at: {datetime.now()}")
            print(f"DEBUG: All task IDs: {list(tasks.keys())}")
            
            # Check memory usage after task creation
            try:
                import psutil
                memory_info = psutil.virtual_memory()
                print(f"DEBUG: Memory after task creation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
            except ImportError:
                print("DEBUG: psutil not available - skipping memory check")
            except Exception as e:
                print(f"DEBUG: Memory check failed: {e}")

        # DIRECT EXECUTION - No threading to avoid worker restarts
        print(f"DEBUG: Starting DIRECT news generation for task {task_id}")
        
        try:
            # Call our memory-optimized function directly
            from glconnect.news_agent import generate_broadcast
            result = generate_broadcast(relevant_topics, task_id=task_id)
            
            print(f"DEBUG: Direct news generation completed for task {task_id}")
            print(f"DEBUG: Result type: {type(result)}")
            
            # Update task status based on result
            if result and 'error' not in result:
                # Success - store result in database
                update_task_in_db(task_id, 
                                 status='completed',
                                 progress=100,
                                 current_step='News generation completed successfully',
                                 result=result,  # Store the result
                                 last_heartbeat=datetime.now())
                
                with _tasks_lock:
                    if task_id in tasks:
                        tasks[task_id]['status'] = 'completed'
                        tasks[task_id]['result'] = result
                        tasks[task_id]['completed_at'] = datetime.now()
                
                print(f"DEBUG: Task {task_id} marked as completed with result stored")
            else:
                # Error
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                update_task_in_db(task_id, 
                                 status='failed',
                                 progress=0,
                                 current_step=f'News generation failed: {error_msg}',
                                 error=error_msg,
                                 failed_at=datetime.now(),
                                 last_heartbeat=datetime.now())
                
                with _tasks_lock:
                    if task_id in tasks:
                        tasks[task_id]['status'] = 'failed'
                        tasks[task_id]['error'] = error_msg
                        tasks[task_id]['failed_at'] = datetime.now()
                
                print(f"DEBUG: Task {task_id} marked as failed: {error_msg}")
                
        except Exception as e:
            print(f"ERROR: Direct news generation failed for task {task_id}: {e}")
            import traceback
            print(f"ERROR: Traceback: {traceback.format_exc()}")
            
            # Mark as failed
            update_task_in_db(task_id, 
                             status='failed',
                             progress=0,
                             current_step=f'News generation failed: {str(e)}',
                             error=str(e),
                             failed_at=datetime.now(),
                             last_heartbeat=datetime.now())
            
            with _tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['status'] = 'failed'
                    tasks[task_id]['error'] = str(e)
                    tasks[task_id]['failed_at'] = datetime.now()

        print(f"DEBUG: Direct execution completed for task {task_id}")
        
        return jsonify({'task_id': task_id})
        
    except Exception as e:
        print(f"CRITICAL ERROR in broadcast endpoint: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # Log system state during error
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            print(f"ERROR: System state - Memory: {memory_info.percent}%, Available: {memory_info.available / 1024 / 1024:.1f}MB")
        except:
            print("ERROR: Could not get system state")
        
        return jsonify({
            'error': 'Internal server error during news generation',
            'details': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@news_bp.route('/debug/emergency-memory-cleanup')
def emergency_memory_cleanup():
    """Emergency memory cleanup endpoint for production."""
    try:
        import gc
        import psutil
        import os
        import ctypes
        
        # Get memory before cleanup
        from glconnect.news_agent import get_memory_usage
        memory_before = get_memory_usage()
        print(f"DEBUG: Emergency cleanup - memory before: {memory_before:.1f}%")
        
        # Aggressive garbage collection
        collected_total = 0
        for i in range(5):  # Multiple passes
            collected = gc.collect()
            collected_total += collected
            print(f"DEBUG: Garbage collection pass {i+1} collected {collected} objects")
        
        # Linux memory trimming
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            print("DEBUG: Linux malloc_trim() completed")
        except:
            print("DEBUG: Linux malloc_trim() not available")
        
        # Clear old tasks
        with _tasks_lock:
            initial_count = len(tasks)
            tasks_to_remove = []
            current_time = datetime.now()
            
            for task_id, task in tasks.items():
                if task.get('status') in ['completed', 'failed']:
                    created_at = task.get('created_at')
                    if created_at:
                        age_seconds = (current_time - created_at).total_seconds()
                        if age_seconds > 300:  # 5 minutes old
                            tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del tasks[task_id]
            
            final_count = len(tasks)
            print(f"DEBUG: Cleaned up {initial_count - final_count} old tasks")
        
        # Get memory after cleanup
        memory_after = get_memory_usage()
        memory_freed = memory_before - memory_after
        
        return jsonify({
            'status': 'success',
            'memory_before': f"{memory_before:.1f}%",
            'memory_after': f"{memory_after:.1f}%",
            'memory_freed': f"{memory_freed:.1f}%",
            'objects_collected': collected_total,
            'tasks_cleaned': initial_count - final_count,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@news_bp.route('/debug/force-cleanup')
def force_cleanup():
    """Force cleanup of stuck tasks and memory to resolve server overload."""
    try:
        import gc
        import psutil
        import sys
        
        # Get memory before cleanup
        memory_before = psutil.virtual_memory()
        print(f"DEBUG: Memory before cleanup - Used: {memory_before.used / 1024 / 1024:.1f}MB, Percent: {memory_before.percent}%")
        
        with _tasks_lock:
            initial_count = len(tasks)
            print(f"DEBUG: Force cleanup - initial task count: {initial_count}")
            
            # Get stuck tasks (running for more than 5 minutes)
            stuck_tasks = []
            current_time = datetime.now()
            
            for task_id, task in tasks.items():
                if task.get('status') == 'running':
                    created_at = task.get('created_at')
                    if created_at:
                        age_seconds = (current_time - created_at).total_seconds()
                        if age_seconds > 1800:  # 30 minutes (increased for multi-topic processing)
                            stuck_tasks.append((task_id, age_seconds))
            
            print(f"DEBUG: Found {len(stuck_tasks)} stuck tasks")
            
            # Remove stuck tasks
            for task_id, age_seconds in stuck_tasks:
                print(f"DEBUG: Removing stuck task {task_id} (age: {age_seconds:.1f}s)")
                del tasks[task_id]
            
            final_count = len(tasks)
            print(f"DEBUG: Force cleanup completed - final task count: {final_count}")
        
        # Emergency memory cleanup
        collected_total = 0
        for i in range(3):  # Multiple passes
            collected = gc.collect()
            collected_total += collected
            print(f"DEBUG: Garbage collection pass {i+1} collected {collected} objects")
        
        # Clear any cached data
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
        
        # Clear module caches
        import importlib
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('glconnect.') and 'cache' in module_name.lower():
                try:
                    del sys.modules[module_name]
                except:
                    pass
        
        # Try memory trimming on Linux
        try:
            import ctypes
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            print("DEBUG: Memory trimmed successfully")
        except:
            print("DEBUG: Memory trim not available")
        
        # Get memory after cleanup
        memory_after = psutil.virtual_memory()
        print(f"DEBUG: Memory after cleanup - Used: {memory_after.used / 1024 / 1024:.1f}MB, Percent: {memory_after.percent}%")
        
        return jsonify({
            'success': True,
            'initial_tasks': initial_count,
            'final_tasks': final_count,
            'stuck_tasks_removed': len(stuck_tasks),
            'stuck_task_ids': [task_id for task_id, _ in stuck_tasks],
            'memory_before': {
                'used_mb': round(memory_before.used / 1024 / 1024, 1),
                'percent': round(memory_before.percent, 1)
            },
            'memory_after': {
                'used_mb': round(memory_after.used / 1024 / 1024, 1),
                'percent': round(memory_after.percent, 1)
            },
            'memory_freed_mb': round((memory_before.used - memory_after.used) / 1024 / 1024, 1),
            'objects_collected': collected_total,
            'message': f'Removed {len(stuck_tasks)} stuck tasks and freed {round((memory_before.used - memory_after.used) / 1024 / 1024, 1)}MB memory'
        })
        
    except Exception as e:
        print(f"ERROR in force cleanup: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@news_bp.route('/debug/health')
def debug_health():
    """Health check endpoint to verify server status and code version."""
    try:
        import psutil
        import os
        
        # Get system information
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get process information
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        # Check if server is healthy
        is_healthy = memory_info.percent < 90 and cpu_percent < 90
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'unhealthy',
            'code_version': '73bce23-comprehensive-fixes',
            'features': {
                'result_debugging': True,
                'cleanup_debugging': True,
                'enhanced_error_handling': True,
                'memory_optimization': True,
                'garbage_collection': True
            },
            'system_info': {
                'memory_usage_percent': memory_info.percent,
                'memory_available_mb': round(memory_info.available / 1024 / 1024, 1),
                'memory_used_mb': round(memory_info.used / 1024 / 1024, 1),
                'cpu_percent': cpu_percent,
                'process_memory_mb': round(process_memory.rss / 1024 / 1024, 1)
            },
            'memory_info': {
                'docker_memory_limit': '4GB',
                'docker_memory_reservation': '2GB'
            },
            'warnings': [
                f"Very high memory usage: {memory_info.percent}%" if memory_info.percent > 90 else f"High memory usage: {memory_info.percent}%" if memory_info.percent > 80 else None,
                f"High CPU usage: {cpu_percent}%" if cpu_percent > 80 else None
            ],
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        # Fallback when psutil is not available
        return jsonify({
            'status': 'unknown',
            'code_version': '73bce23-comprehensive-fixes',
            'features': {
                'result_debugging': True,
                'cleanup_debugging': True,
                'enhanced_error_handling': True,
                'memory_optimization': True,
                'garbage_collection': True
            },
            'system_info': {
                'memory_usage_percent': 'unknown',
                'memory_available_mb': 'unknown',
                'memory_used_mb': 'unknown',
                'cpu_percent': 'unknown',
                'process_memory_mb': 'unknown'
            },
            'memory_info': {
                'docker_memory_limit': '4GB',
                'docker_memory_reservation': '2GB'
            },
            'warnings': ['psutil not available - system monitoring limited'],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code_version': '73bce23-comprehensive-fixes',
            'timestamp': datetime.now().isoformat()
        }), 500

@news_bp.route('/debug/memory-dashboard')
def memory_dashboard():
    """Memory usage dashboard with detailed information and recommendations."""
    try:
        import psutil
        import os
        import gc
        
        # Get system information
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get process information
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        
        # Get container memory limit if available
        container_limit = None
        try:
            with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                container_limit = int(f.read().strip()) / 1024 / 1024 / 1024  # Convert to GB
        except:
            pass
        
        # Calculate memory efficiency
        memory_efficiency = (memory_info.available / memory_info.total) * 100
        
        # Get garbage collection stats
        gc_stats = gc.get_stats()
        
        # Determine status
        if memory_info.percent > 85:
            status = 'critical'
            status_color = '#ff4444'
        elif memory_info.percent > 85:
            status = 'warning'
            status_color = '#ffaa00'
        elif memory_info.percent > 70:
            status = 'caution'
            status_color = '#ffdd00'
        else:
            status = 'healthy'
            status_color = '#44ff44'
        
        # Generate recommendations
        recommendations = []
        if memory_info.percent > 80:
            recommendations.append("🚨 CRITICAL: Memory usage is extremely high - consider restarting the application")
        elif memory_info.percent > 80:
            recommendations.append("⚠️ WARNING: High memory usage detected - monitor closely")
            recommendations.append("💡 Consider running garbage collection")
        elif memory_info.percent > 70:
            recommendations.append("⚡ Memory usage is elevated - consider optimization")
        
        if process_memory.rss > 200 * 1024 * 1024:  # 200MB
            recommendations.append("🔧 Process memory is high - check for memory leaks")
        
        if not recommendations:
            recommendations.append("✅ Memory usage is within normal parameters")
        
        return jsonify({
            'status': status,
            'status_color': status_color,
            'timestamp': datetime.now().isoformat(),
            'system_memory': {
                'total_gb': round(memory_info.total / 1024 / 1024 / 1024, 2),
                'used_gb': round(memory_info.used / 1024 / 1024 / 1024, 2),
                'available_gb': round(memory_info.available / 1024 / 1024 / 1024, 2),
                'used_percent': round(memory_info.percent, 1),
                'efficiency_percent': round(memory_efficiency, 1)
            },
            'process_memory': {
                'rss_mb': round(process_memory.rss / 1024 / 1024, 1),
                'vms_mb': round(process_memory.vms / 1024 / 1024, 1),
                'percent': round(process.memory_percent(), 1)
            },
            'container_info': {
                'limit_gb': round(container_limit, 2) if container_limit else None,
                'usage_percent': round((memory_info.used / (container_limit * 1024 * 1024 * 1024)) * 100, 1) if container_limit else None
            },
            'cpu_info': {
                'usage_percent': round(cpu_percent, 1)
            },
            'garbage_collection': {
                'collections': gc_stats[0]['collections'] if gc_stats else 0,
                'collected': gc_stats[0]['collected'] if gc_stats else 0,
                'uncollectable': gc_stats[0]['uncollectable'] if gc_stats else 0
            },
            'recommendations': recommendations,
            'actions': {
                'force_gc': '/debug/force-cleanup',
                'restart_app': '/debug/restart-application',
                'memory_monitor': '/debug/memory-monitor'
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@news_bp.route('/debug/memory-dashboard-page')
def memory_dashboard_page():
    """Serve the memory dashboard HTML page."""
    try:
        from flask import render_template
        return render_template('memory_dashboard.html')
    except Exception as e:
        return f"Error loading memory dashboard: {e}", 500

@news_bp.route('/debug/server-status')
def debug_server_status():
    """Detailed server status for debugging task issues."""
    try:
        import psutil
        import os
        
        memory_info = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        process = psutil.Process(os.getpid())
        
        with _tasks_lock:
            task_count = len(tasks)
            running_tasks = sum(1 for task in tasks.values() if task.get('status') == 'running')
            completed_tasks = sum(1 for task in tasks.values() if task.get('status') == 'completed')
            failed_tasks = sum(1 for task in tasks.values() if task.get('status') == 'failed')
        
        return jsonify({
            'server_status': {
                'memory_percent': memory_info.percent,
                'memory_available_mb': round(memory_info.available / 1024 / 1024, 1),
                'cpu_percent': cpu_percent,
                'process_memory_mb': round(process.memory_info().rss / 1024 / 1024, 1)
            },
            'task_status': {
                'total_tasks': task_count,
                'running_tasks': running_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks
            },
            'health_indicators': {
                'memory_healthy': memory_info.percent < 80,
                'cpu_healthy': cpu_percent < 80,
                'tasks_healthy': task_count < 100
            },
            'potential_issues': [
                'Maximum memory usage may cause 502 errors' if memory_info.percent >= 100 else 'Very high memory usage may cause issues' if memory_info.percent > 90 else 'High memory usage' if memory_info.percent > 80 else None,
                'High CPU usage may cause timeouts' if cpu_percent > 80 else None,
                'Many tasks may cause memory issues' if task_count > 50 else None,
                'No tasks may indicate server restart' if task_count == 0 else None
            ],
            'timestamp': datetime.now().isoformat()
        })
    except ImportError:
        # Fallback when psutil is not available
        with _tasks_lock:
            task_count = len(tasks)
            running_tasks = sum(1 for task in tasks.values() if task.get('status') == 'running')
            completed_tasks = sum(1 for task in tasks.values() if task.get('status') == 'completed')
            failed_tasks = sum(1 for task in tasks.values() if task.get('status') == 'failed')
        
        return jsonify({
            'server_status': {
                'memory_percent': 'unknown',
                'memory_available_mb': 'unknown',
                'cpu_percent': 'unknown',
                'process_memory_mb': 'unknown'
            },
            'task_status': {
                'total_tasks': task_count,
                'running_tasks': running_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks
            },
            'health_indicators': {
                'memory_healthy': 'unknown',
                'cpu_healthy': 'unknown',
                'tasks_healthy': task_count < 100
            },
            'potential_issues': [
                'psutil not available - system monitoring limited',
                'Many tasks may cause memory issues' if task_count > 50 else None,
                'No tasks may indicate server restart' if task_count == 0 else None
            ],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@news_bp.route('/status/<task_id>')
def task_status(task_id):
    print(f"DEBUG: Checking status for task {task_id}")
    
    # Check server health before processing
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Server health check - Memory: {memory_info.percent}%, Available: {memory_info.available / 1024 / 1024:.1f}MB")
        
        # Check if server is under memory pressure
        if memory_info.percent >= 100:
            print(f"CRITICAL: Server memory at maximum ({memory_info.percent}%) - may cause 502 errors!")
            return jsonify({
                'error': 'Server temporarily unavailable due to maximum memory usage. Please try again in a moment.',
                'details': f'Server memory usage: {memory_info.percent}%'
            }), 503
        elif memory_info.percent > 80:
            print(f"WARNING: Very high memory usage ({memory_info.percent}%) - monitoring closely")
        elif memory_info.percent > 80:
            print(f"INFO: High memory usage ({memory_info.percent}%) - monitoring")
    except ImportError:
        print("DEBUG: psutil not available - skipping memory check")
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
    
    # First try to get task from database
    db_task = get_task_from_db(task_id)
    task = normalize_task_format(db_task)
    
    # If not found in database, check memory (for backward compatibility)
    if not task:
        with _tasks_lock:
            memory_task = tasks.get(task_id)
            print(f"DEBUG: Total tasks in memory: {len(tasks)}")
            print(f"DEBUG: Available task IDs in memory: {list(tasks.keys())}")
            
            # Log task details if found
            if memory_task:
                print(f"DEBUG: Task {task_id} found in memory - Status: {memory_task.get('status')}, Created: {memory_task.get('created_at')}")
                task = memory_task
            else:
                print(f"DEBUG: Task {task_id} NOT FOUND in memory")
    
    if not task:
        print(f"DEBUG: Task {task_id} not found in tasks dictionary. Total tasks: {len(tasks)}")
        print(f"DEBUG: Available task IDs: {list(tasks.keys())}")
        print(f"DEBUG: Current time: {datetime.now()}")
        print(f"DEBUG: This task may have been cleaned up due to age. Check cleanup logs above.")
        
        # Check if this is a recent task that shouldn't have been cleaned up
        if len(tasks) == 0:
            print(f"CRITICAL: No tasks in system - possible server restart or memory crash!")
            return jsonify({
                'error': 'Task not found - the news generation may have completed or been cancelled. Please try generating news again.',
                'details': 'No tasks found in system. This may indicate a server restart or memory issue.',
                'server_restart': True,
                'suggestion': 'Please try generating news again. If the problem persists, the server may need to be restarted.'
            }), 404
        else:
            # Check if there are any running tasks to provide better context
            running_tasks = [tid for tid, tdata in tasks.items() if tdata.get('status') == 'running']
            completed_tasks = [tid for tid, tdata in tasks.items() if tdata.get('status') == 'completed']
            
            return jsonify({
                'error': 'Task not found - the news generation may have completed or been cancelled. Please try generating news again.',
                'details': f'Task was not found in the system. Current system status: {len(tasks)} total tasks ({len(running_tasks)} running, {len(completed_tasks)} completed). This usually means the task was cleaned up due to age or the task ID is invalid.',
                'system_status': {
                    'total_tasks': len(tasks),
                    'running_tasks': len(running_tasks),
                    'completed_tasks': len(completed_tasks)
                },
                'suggestion': 'Please try generating news again. The task may have been cleaned up due to system maintenance.'
            }), 404
    
    if task['status'] == 'completed':
        # Handle the new task structure with direct audio_file and summary
        if 'audio_file' in task:
            # Verify the audio file still exists before returning it
            audio_file_path = task['audio_file']
            if audio_file_path.startswith('/routes2/news/audio/'):
                # Convert URL back to file path for verification
                filename = audio_file_path.replace('/routes2/news/audio/', '')
                actual_file_path = os.path.join('glconnect', 'static', 'audio', filename)
                
                if not os.path.exists(actual_file_path):
                    print(f"DEBUG: Audio file not found on disk: {actual_file_path}")
                    return jsonify({
                        'status': 'failed',
                        'error': 'Audio file not found on disk'
                    })
                
                file_size = os.path.getsize(actual_file_path)
                if file_size == 0:
                    print(f"DEBUG: Audio file is empty: {actual_file_path}")
                    return jsonify({
                        'status': 'failed',
                        'error': 'Audio file is empty'
                    })
                
                print(f"DEBUG: Audio file verified for UI - {actual_file_path} ({file_size} bytes)")
            
            return jsonify({
                'status': 'completed',
                'audio_file': task['audio_file'],
                'summary': task.get('summary', '')
            })
        # Fallback for old structure
        elif 'result' in task:
            result = task['result']
            print(f"DEBUG: Task {task_id} completed with result: {result}")
            print(f"DEBUG: Result type: {type(result)}")
            print(f"DEBUG: Result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            
            # Initialize variables
            audio_file_path = None
            summary = ""
            
            # Handle the memory-optimized result structure
            if isinstance(result, dict):
                # Check for memory-optimized structure first
                if 'audio_file' in result:
                    audio_file_path = result['audio_file']
                    summary = result.get('summary', '')
                    print(f"DEBUG: Found audio_file in result: {audio_file_path}")
                # Check for old structure
                elif 'audio_file_path' in result:
                    audio_file_path = result['audio_file_path']
                    summary = result.get('summary', '')
                    print(f"DEBUG: Found audio_file_path in result: {audio_file_path}")
                else:
                    print(f"DEBUG: No audio_file or audio_file_path found in result")
                
                # Extract summary from content if available
                if not summary and 'content' in result:
                    summary = f"Generated news content for {len(result['content'])} topics"
            
            # For memory-optimized version, we don't have actual audio files yet
            # Just return success with the summary
            if audio_file_path == 'simple_news_broadcast.mp3':
                return jsonify({
                    'status': 'completed',
                    'content': result.get('content', []),
                    'message': 'News generation completed successfully (memory-optimized version)'
                })
            
            # Verify the audio file exists before returning it (for old structure)
            if audio_file_path:
                # Convert web path to file path for verification
                if audio_file_path.startswith('/static/audio/'):
                    file_path = os.path.join('glconnect', 'static', 'audio', os.path.basename(audio_file_path))
                else:
                    file_path = audio_file_path
                
                if not os.path.exists(file_path):
                    return jsonify({'status': 'failed', 'error': f'Audio file not found: {audio_file_path}'})
            elif not audio_file_path:
                return jsonify({'status': 'failed', 'error': 'No audio file path found in result'})
            
            return jsonify({
                'status': 'completed',
                'audio_file': audio_file_path
            })
        else:
            # Handle old dictionary structure (if any) - but result is not defined here
            return jsonify({'status': 'failed', 'error': 'No valid result structure found in task'})
            
    elif task['status'] == 'failed':
        error_message = task.get('error')
        print(f"DEBUG: Task {task_id} failed - raw error: '{error_message}'")
        print(f"DEBUG: Task {task_id} full task data: {task}")
        
        if not error_message or error_message == 'Unknown error':
            # Try to get more specific error information
            if 'failed_at' in task and task['failed_at']:
                error_message = f"News generation failed at {task['failed_at']}. Please try again."
            else:
                error_message = "News generation failed due to an unknown error. Please try again."
        print(f"DEBUG: Task {task_id} failed with error: {error_message}")
        return jsonify({'status': 'failed', 'error': error_message})
    else:
        return jsonify({
            'status': 'running',
            'progress': task.get('progress', 0),
            'current_step': task.get('current_step', 'Processing...')
        })

@news_bp.route('/analytics')
def analytics():
    """Main analytics page showing dominant topics by category with LLM categorization."""
    from glconnect.models import db, SearchHistory, CategoryCount, TopicCount, DailySearchCount, CategoryTopic, CategorizationConfidence
    from glconnect import create_app
    
    app = create_app()
    with app.app_context():
        try:
            # Get category counts sorted by frequency
            category_counts = CategoryCount.query.all()
            sorted_categories = [(cat.category, cat.count) for cat in category_counts]
            sorted_categories.sort(key=lambda x: x[1], reverse=True)
            
            # Get total searches
            total_searches = sum(cat.count for cat in category_counts)
            
            # Get recent searches (last 10)
            recent_searches = SearchHistory.query.order_by(SearchHistory.timestamp.desc()).limit(10).all()
            recent_searches_data = [
                {
                    'topic': search.topic,
                    'timestamp': search.timestamp.isoformat(),
                    'date': search.date
                }
                for search in recent_searches
            ]
            
            # Get daily search trends (last 7 days)
            daily_trends = []
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                daily_count = DailySearchCount.query.filter_by(date=date).first()
                count = daily_count.count if daily_count else 0
                daily_trends.append({'date': date, 'count': count})
            daily_trends.reverse()
            
            # Get categorization confidence statistics
            confidence_stats = get_categorization_stats()
            
            return render_template('analytics.html', 
                                 categories=sorted_categories,
                                 total_searches=total_searches,
                                 recent_searches=recent_searches_data,
                                 daily_trends=daily_trends,
                                 confidence_stats=confidence_stats)
                                 
        except Exception as e:
            print(f"Error loading analytics from database: {e}")
            # Fallback to in-memory data if database fails
            with _analytics_lock:
                category_data = dict(analytics_data['category_counts'])
                sorted_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
                total_searches = sum(analytics_data['category_counts'].values())
                recent_searches = analytics_data['search_history'][-10:]
                
                daily_trends = []
                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                    count = analytics_data['daily_searches'].get(date, 0)
                    daily_trends.append({'date': date, 'count': count})
                daily_trends.reverse()
                
                confidence_stats = get_categorization_stats()
                
                return render_template('analytics.html', 
                                     categories=sorted_categories,
                                     total_searches=total_searches,
                                     recent_searches=recent_searches,
                                     daily_trends=daily_trends,
                                     confidence_stats=confidence_stats)

@news_bp.route('/analytics/category/<category>')
def category_details(category):
    """Detailed view of topics within a specific category with LLM categorization."""
    with _analytics_lock:
        # Get topics for this category
        category_topics = analytics_data['category_topics'].get(category, [])
        
        # Get topic counts for this category using LLM categorization
        topic_counts = {}
        for search in analytics_data['search_history']:
            # Use the new LLM categorization
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
        
        # Get confidence statistics for this category
        category_confidence = get_category_confidence_stats(category)
        
        return render_template('category_details.html',
                             category=category,
                             topics=sorted_topics,
                             recent_searches=recent_category_searches,
                             category_confidence=category_confidence)

def get_categorization_stats():
    """Get overall categorization statistics including confidence scores."""
    from glconnect.models import db, CategorizationConfidence
    from glconnect import create_app
    
    app = create_app()
    with app.app_context():
        try:
            confidences = CategorizationConfidence.query.all()
            total = len(confidences)
            
            if total == 0:
                return {
                    'total_categorizations': 0,
                    'ai_categorizations': 0,
                    'keyword_categorizations': 0,
                    'average_confidence': 0.0,
                    'high_confidence_count': 0,
                    'low_confidence_count': 0
                }
            
            ai_count = sum(1 for c in confidences if c.confidence >= 0.8)
            keyword_count = total - ai_count
            avg_confidence = sum(c.confidence for c in confidences) / total
            high_confidence = sum(1 for c in confidences if c.confidence >= 0.8)
            low_confidence = sum(1 for c in confidences if c.confidence < 0.7)
            
            return {
                'total_categorizations': total,
                'ai_categorizations': ai_count,
                'keyword_categorizations': keyword_count,
                'average_confidence': round(avg_confidence, 2),
                'high_confidence_count': high_confidence,
                'low_confidence_count': low_confidence
            }
            
        except Exception as e:
            print(f"Error getting categorization stats from database: {e}")
            # Fallback to in-memory data
            if 'categorization_confidence' not in analytics_data:
                return {
                    'total_categorizations': 0,
                    'ai_categorizations': 0,
                    'keyword_categorizations': 0,
                    'average_confidence': 0.0,
                    'high_confidence_count': 0,
                    'low_confidence_count': 0
                }
            
            confidences = analytics_data['categorization_confidence']
            total = len(confidences)
            
            if total == 0:
                return {
                    'total_categorizations': 0,
                    'ai_categorizations': 0,
                    'keyword_categorizations': 0,
                    'average_confidence': 0.0,
                    'high_confidence_count': 0,
                    'low_confidence_count': 0
                }
            
            ai_count = sum(1 for c in confidences if c['confidence'] >= 0.8)
            keyword_count = total - ai_count
            avg_confidence = sum(c['confidence'] for c in confidences) / total
            high_confidence = sum(1 for c in confidences if c['confidence'] >= 0.8)
            low_confidence = sum(1 for c in confidences if c['confidence'] < 0.7)
            
            return {
                'total_categorizations': total,
                'ai_categorizations': ai_count,
                'keyword_categorizations': keyword_count,
                'average_confidence': round(avg_confidence, 2),
                'high_confidence_count': high_confidence,
                'low_confidence_count': low_confidence
            }

def get_category_confidence_stats(category):
    """Get confidence statistics for a specific category."""
    if 'categorization_confidence' not in analytics_data:
        return {
            'category_total': 0,
            'category_avg_confidence': 0.0,
            'ai_categorizations': 0,
            'keyword_categorizations': 0
        }
    
    category_confidences = [
        c for c in analytics_data['categorization_confidence'] 
        if c['category'] == category
    ]
    
    if not category_confidences:
        return {
            'category_total': 0,
            'category_avg_confidence': 0.0,
            'ai_categorizations': 0,
            'keyword_categorizations': 0
        }
    
    total = len(category_confidences)
    avg_confidence = sum(c['confidence'] for c in category_confidences) / total
    ai_count = sum(1 for c in category_confidences if c['confidence'] >= 0.8)
    keyword_count = total - ai_count
    
    return {
        'category_total': total,
        'category_avg_confidence': round(avg_confidence, 2),
        'ai_categorizations': ai_count,
        'keyword_categorizations': keyword_count
    }

@news_bp.route('/api/analytics/summary')
def analytics_summary():
    """API endpoint for analytics summary data with LLM categorization stats."""
    from glconnect.models import db, SearchHistory, CategoryCount, TopicCount, DailySearchCount, CategoryTopic, CategorizationConfidence
    from glconnect import create_app
    from collections import Counter
    
    app = create_app()
    with app.app_context():
        try:
            confidence_stats = get_categorization_stats()
            
            # Get data from database
            category_counts = {cat.category: cat.count for cat in CategoryCount.query.all()}
            topic_counts = {topic.topic: topic.count for topic in TopicCount.query.all()}
            daily_counts = {daily.date: daily.count for daily in DailySearchCount.query.all()}
            
            return jsonify({
                'total_searches': sum(category_counts.values()),
                'category_counts': category_counts,
                'top_topics': dict(Counter(topic_counts).most_common(10)),
                'daily_searches': daily_counts,
                'categorization_stats': confidence_stats
            })
            
        except Exception as e:
            print(f"Error getting analytics summary from database: {e}")
            # Fallback to in-memory data
            with _analytics_lock:
                confidence_stats = get_categorization_stats()
                return jsonify({
                    'total_searches': sum(analytics_data['category_counts'].values()),
                    'category_counts': dict(analytics_data['category_counts']),
                    'top_topics': dict(Counter(analytics_data['topic_counts']).most_common(10)),
                    'daily_searches': dict(analytics_data['daily_searches']),
                    'categorization_stats': confidence_stats
                })

@news_bp.route('/api/validate-topic', methods=['POST'])
def validate_topic_api():
    """Simplified API endpoint using NewsTopicValidationAgent."""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        
        if not topic:
            return jsonify({
                'is_relevant': False,
                'reason': 'Topic is required',
                'error': 'Topic cannot be empty'
            }), 400
        
        # Use the validation agent
        agent = get_validation_agent()
        is_valid, error_message = agent.validate_topic(topic)
        
        if is_valid:
            return jsonify({
                'topic': topic,
                'is_relevant': True,
                'reason': 'Valid news topic',
                'confidence': 0.95,
                'validation_timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'topic': topic,
                'is_relevant': False,
                'reason': error_message,
                'confidence': 0.95,
                'validation_timestamp': datetime.now().isoformat()
            })
        
    except Exception as e:
        print(f"Validation API error: {e}")
        return jsonify({
            'is_relevant': False,
            'reason': 'Validation service unavailable',
            'error': f'Validation failed: {str(e)}'
        }), 500

@news_bp.route('/api/validate-news-topic', methods=['POST'])
def validate_news_topic_api():
    """
    Direct validation endpoint for news generation flow.
    Returns simple True/False with error message.
    """
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        
        if not topic:
            return jsonify({
                'valid': False,
                'error': 'Topic is required'
            }), 400
        
        # Use the validation agent
        agent = get_validation_agent()
        is_valid, error_message = agent.validate_topic(topic)
        
        if is_valid:
            return jsonify({
                'valid': True,
                'message': 'Topic is valid for news generation'
            })
        else:
            return jsonify({
                'valid': False,
                'error': error_message
            })
        
    except Exception as e:
        print(f"News topic validation error: {e}")
        return jsonify({
            'valid': False,
            'error': 'Validation service unavailable. Please try again.'
        }), 500

@news_bp.route('/api/override-topic', methods=['POST'])
def override_topic_api():
    """API endpoint for users to override topic validation decisions."""
    try:
        data = request.get_json()
        topic = data.get('topic', '').strip()
        override_decision = data.get('override_decision')  # True/False
        user_feedback = data.get('user_feedback', '')  # Optional explanation
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        if override_decision is None:
            return jsonify({'error': 'Override decision is required'}), 400
        
        # Log the override decision
        log_validation_feedback(topic, override_decision, user_feedback)
        
        # Re-validate with override
        is_relevant, confidence, reason = validate_topic_with_user_override(topic, override_decision)
        
        return jsonify({
            'topic': topic,
            'is_relevant': is_relevant,
            'confidence': confidence,
            'reason': reason,
            'override_applied': True,
            'user_feedback': user_feedback
        })
        
    except Exception as e:
        return jsonify({'error': f'Override failed: {str(e)}'}), 500

@news_bp.route('/api/audio-files')
def get_audio_files():
    """API endpoint to get list of available audio files."""
    try:
        import os
        from flask import current_app
        
        audio_files = []
        
        # Check static/audio directory
        static_audio_dir = os.path.join(current_app.static_folder, 'audio')
        if os.path.exists(static_audio_dir):
            for filename in os.listdir(static_audio_dir):
                if filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    # Skip jingle.wav - it's a system file that should never be revealed
                    if filename.lower() == 'jingle.wav':
                        continue
                        
                    file_path = os.path.join(static_audio_dir, filename)
                    file_size = os.path.getsize(file_path)
                    file_time = os.path.getmtime(file_path)
                    
                    audio_files.append({
                        'filename': filename,
                        'url': f'/routes2/news/audio/{filename}',
                        'size': file_size,
                        'modified': file_time,
                        'type': 'static'
                    })
        
        # Check for generated news broadcast files in other locations
        # Look for files with news broadcast patterns
        import glob
        broadcast_patterns = [
            'news_broadcast_*.mp3',
            'news_broadcast_*.wav',
            'broadcast_*.mp3',
            'broadcast_*.wav'
        ]
        
        for pattern in broadcast_patterns:
            for file_path in glob.glob(os.path.join(current_app.root_path, '..', pattern)):
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    file_size = os.path.getsize(file_path)
                    file_time = os.path.getmtime(file_path)
                    
                    # Create a URL for the file (you might need to adjust this based on your setup)
                    audio_files.append({
                        'filename': filename,
                        'url': f'/routes2/news/audio/{filename}',
                        'size': file_size,
                        'modified': file_time,
                        'type': 'generated'
                    })
        
        # Sort by modification time (newest first)
        audio_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'audio_files': audio_files,
            'count': len(audio_files)
        })
        
    except Exception as e:
        print(f"Error getting audio files: {e}")
        return jsonify({'error': 'Failed to get audio files'}), 500

@news_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """Transcribe audio file using Google's Gemini API with async processing."""
    try:
        data = request.get_json()
        audio_url = data.get('audio_url', '').strip()
        filename = data.get('filename', 'audio.mp3')
        
        if not audio_url:
            return jsonify({'error': 'Audio URL is required'}), 400
        
        # Convert URL to file path
        if audio_url.startswith('/routes2/news/audio/'):
            filename = audio_url.replace('/routes2/news/audio/', '')
            audio_file_path = os.path.join('glconnect', 'static', 'audio', filename)
        elif audio_url.startswith('/static/audio/'):
            filename = audio_url.replace('/static/audio/', '')
            audio_file_path = os.path.join('glconnect', 'static', 'audio', filename)
        else:
            return jsonify({'error': 'Invalid audio URL format'}), 400
        
        # Check if file exists
        if not os.path.exists(audio_file_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Check file size (limit to 10MB for transcription to accommodate news broadcasts)
        file_size = os.path.getsize(audio_file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit (increased for news broadcasts)
            return jsonify({'error': 'Audio file too large for transcription (max 10MB)'}), 400
        
        # Check if file is too short (less than 1 second)
        if file_size < 1000:  # Less than 1KB
            return jsonify({'error': 'Audio file too short for transcription'}), 400
        
        # Note: Cleanup is now handled automatically and less aggressively
        
        # Start transcription in a separate thread to prevent worker timeout
        task_id = str(uuid.uuid4())
        with _tasks_lock:
            tasks[task_id] = {
                'status': 'running', 
                'type': 'transcription',
                'created_at': datetime.now()
            }
        
        # Start transcription thread
        thread = threading.Thread(target=run_transcription, args=(task_id, audio_file_path, filename))
        thread.daemon = True  # Make it a daemon thread so it doesn't prevent app shutdown
        thread.start()
        
        return jsonify({
            'task_id': task_id,
            'status': 'processing',
            'message': 'Transcription started. This may take a few moments...'
        })
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return jsonify({'error': f'Transcription failed: {str(e)}'}), 500

def run_transcription(task_id, audio_file_path, filename):
    """Run transcription in a separate thread to prevent worker timeout."""
    import gc
    import time
    
    try:
        print(f"Starting transcription for {filename}")
        
        # Check file size again before processing
        file_size = os.path.getsize(audio_file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB limit (increased for news broadcasts)
            raise Exception("File too large for transcription (max 10MB)")
        
        # Use Google Gemini for transcription
        from google import genai
        
        # Get API key from environment
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise Exception("Google API key not configured")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Upload the audio file with timeout handling
        print(f"Uploading audio file for transcription: {audio_file_path}")
        try:
            myfile = client.files.upload(file=audio_file_path)
        except Exception as e:
            raise Exception(f"Failed to upload audio file: {str(e)}")
        
        # Generate transcription using Gemini with timeout
        print("Generating transcription...")
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Transcribe this audio file. Provide a clean, accurate transcription of all spoken content.", myfile]
            )
        except Exception as e:
            raise Exception(f"Failed to generate transcription: {str(e)}")
        
        transcript = response.text.strip()
        
        if not transcript:
            raise Exception("No transcription generated")
        
        print(f"Transcription completed successfully for {filename}")
        
        # Store the result
        with _tasks_lock:
            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['completed_at'] = datetime.now()
            tasks[task_id]['result'] = {
                'transcript': transcript,
                'filename': filename,
                'file_size': file_size
            }
        
        # Clean up memory
        del myfile
        del response
        del transcript
        gc.collect()
        
    except Exception as e:
        print(f"Transcription error: {e}")
        with _tasks_lock:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['failed_at'] = datetime.now()
            tasks[task_id]['error'] = str(e)
        
        # Clean up memory on error
        gc.collect()
    
    finally:
        # Force garbage collection
        gc.collect()
        print(f"Transcription thread completed for {filename}")

@news_bp.route('/transcribe/status/<task_id>')
def transcription_status(task_id):
    """Check the status of a transcription task."""
    with _tasks_lock:
        task = tasks.get(task_id)
    
    if not task:
        print(f"DEBUG: Transcription task {task_id} not found in tasks dictionary. Total tasks: {len(tasks)}")
        print(f"DEBUG: Available task IDs: {list(tasks.keys())}")
        return jsonify({'error': 'Task not found'}), 404
    
    if task['status'] == 'completed':
        return jsonify({
            'status': 'completed',
            'transcript': task['result']['transcript'],
            'filename': task['result']['filename'],
            'file_size': task['result']['file_size'],
            'download_url': f'/routes2/news/transcript/download/{task_id}'
        })
    elif task['status'] == 'failed':
        return jsonify({
            'status': 'failed',
            'error': task.get('error', 'Unknown error')
        })
    else:
        return jsonify({'status': 'processing'})

@news_bp.route('/transcript/download/<task_id>')
def download_transcript(task_id):
    """Download the transcript as a text file."""
    with _tasks_lock:
        task = tasks.get(task_id)
    
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    if task['status'] != 'completed':
        return jsonify({'error': 'Transcription not completed yet'}), 400
    
    if 'result' not in task or 'transcript' not in task['result']:
        return jsonify({'error': 'No transcript available'}), 400
    
    transcript = task['result']['transcript']
    filename = task['result'].get('filename', 'transcript.txt')
    
    # Create a response with the transcript as a downloadable file
    from flask import Response
    
    # Generate a clean filename
    clean_filename = filename.replace('.mp3', '_transcript.txt').replace('.wav', '_transcript.txt')
    if not clean_filename.endswith('.txt'):
        clean_filename += '_transcript.txt'
    
    response = Response(
        transcript,
        mimetype='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{clean_filename}"',
            'Content-Type': 'text/plain; charset=utf-8'
        }
    )
    
    return response

@news_bp.route('/languages')
def get_supported_languages():
    """Get list of supported languages and voices for TTS."""
    try:
        from google.cloud import texttospeech
        
        client = texttospeech.TextToSpeechClient()
        voices = client.list_voices()
        
        languages = {}
        for voice in voices.voices:
            for language_code in voice.language_codes:
                if language_code not in languages:
                    languages[language_code] = {
                        'code': language_code,
                        'name': get_language_name(language_code),
                        'voices': []
                    }
                
                languages[language_code]['voices'].append({
                    'name': voice.name,
                    'gender': voice.ssml_gender.name,
                    'sample_rate': voice.natural_sample_rate_hertz
                })
        
        # Sort languages by code
        sorted_languages = sorted(languages.values(), key=lambda x: x['code'])
        
        return jsonify({
            'languages': sorted_languages,
            'total_languages': len(sorted_languages)
        })
        
    except Exception as e:
        print(f"Error getting supported languages: {e}")
        return jsonify({'error': 'Failed to get supported languages'}), 500

def get_language_name(language_code):
    """Convert language code to readable name."""
    language_names = {
        'en-US': 'English (US)',
        'en-GB': 'English (UK)',
        'es-ES': 'Spanish (Spain)',
        'es-MX': 'Spanish (Mexico)',
        'fr-FR': 'French (France)',
        'de-DE': 'German (Germany)',
        'it-IT': 'Italian (Italy)',
        'pt-BR': 'Portuguese (Brazil)',
        'pt-PT': 'Portuguese (Portugal)',
        'ja-JP': 'Japanese (Japan)',
        'ko-KR': 'Korean (South Korea)',
        'zh-CN': 'Chinese (Simplified)',
        'zh-TW': 'Chinese (Traditional)',
        'ru-RU': 'Russian (Russia)',
        'ar-SA': 'Arabic (Saudi Arabia)',
        'hi-IN': 'Hindi (India)',
        'nl-NL': 'Dutch (Netherlands)',
        'sv-SE': 'Swedish (Sweden)',
        'no-NO': 'Norwegian (Norway)',
        'da-DK': 'Danish (Denmark)',
        'fi-FI': 'Finnish (Finland)',
        'pl-PL': 'Polish (Poland)',
        'tr-TR': 'Turkish (Turkey)',
        'cs-CZ': 'Czech (Czech Republic)',
        'hu-HU': 'Hungarian (Hungary)',
        'ro-RO': 'Romanian (Romania)',
        'bg-BG': 'Bulgarian (Bulgaria)',
        'hr-HR': 'Croatian (Croatia)',
        'sk-SK': 'Slovak (Slovakia)',
        'sl-SI': 'Slovenian (Slovenia)',
        'et-EE': 'Estonian (Estonia)',
        'lv-LV': 'Latvian (Latvia)',
        'lt-LT': 'Lithuanian (Lithuania)',
        'uk-UA': 'Ukrainian (Ukraine)',
        'el-GR': 'Greek (Greece)',
        'he-IL': 'Hebrew (Israel)',
        'th-TH': 'Thai (Thailand)',
        'vi-VN': 'Vietnamese (Vietnam)',
        'id-ID': 'Indonesian (Indonesia)',
        'ms-MY': 'Malay (Malaysia)',
        'tl-PH': 'Filipino (Philippines)',
        'ca-ES': 'Catalan (Spain)',
        'eu-ES': 'Basque (Spain)',
        'gl-ES': 'Galician (Spain)',
        'cy-GB': 'Welsh (UK)',
        'ga-IE': 'Irish (Ireland)',
        'mt-MT': 'Maltese (Malta)',
        'is-IS': 'Icelandic (Iceland)',
        'sq-AL': 'Albanian (Albania)',
        'mk-MK': 'Macedonian (Macedonia)',
        'sr-RS': 'Serbian (Serbia)',
        'bs-BA': 'Bosnian (Bosnia)',
        'me-ME': 'Montenegrin (Montenegro)',
        'af-ZA': 'Afrikaans (South Africa)',
        'sw-KE': 'Swahili (Kenya)',
        'am-ET': 'Amharic (Ethiopia)',
        'ha-NG': 'Hausa (Nigeria)',
        'ig-NG': 'Igbo (Nigeria)',
        'yo-NG': 'Yoruba (Nigeria)',
        'zu-ZA': 'Zulu (South Africa)',
        'xh-ZA': 'Xhosa (South Africa)',
        'st-ZA': 'Sesotho (South Africa)',
        'tn-ZA': 'Tswana (South Africa)',
        'ss-ZA': 'Swati (South Africa)',
        've-ZA': 'Venda (South Africa)',
        'ts-ZA': 'Tsonga (South Africa)',
        'nr-ZA': 'Ndebele (South Africa)',
        'nso-ZA': 'Northern Sotho (South Africa)',
        'zu-ZA': 'Zulu (South Africa)',
        'xh-ZA': 'Xhosa (South Africa)',
        'st-ZA': 'Sesotho (South Africa)',
        'tn-ZA': 'Tswana (South Africa)',
        'ss-ZA': 'Swati (South Africa)',
        've-ZA': 'Venda (South Africa)',
        'ts-ZA': 'Tsonga (South Africa)',
        'nr-ZA': 'Ndebele (South Africa)',
        'nso-ZA': 'Northern Sotho (South Africa)'
    }
    return language_names.get(language_code, language_code)

@news_bp.route('/regenerate-audio', methods=['POST'])
def regenerate_audio_in_language():
    """Regenerate news audio in a different language."""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        language_code = data.get('language_code', 'en-US')
        voice_name = data.get('voice_name')
        
        if not task_id:
            return jsonify({'error': 'Task ID is required'}), 400
        
        # Get the original task to extract the transcript
        with _tasks_lock:
            original_task = tasks.get(task_id)
        
        if not original_task:
            return jsonify({'error': 'Original task not found'}), 404
        
        if original_task['status'] != 'completed':
            return jsonify({'error': 'Original task not completed yet'}), 400
        
        # Get the transcript
        transcript = None
        if 'result' in original_task and 'transcript' in original_task['result']:
            transcript = original_task['result']['transcript']
        elif 'summary' in original_task:
            transcript = original_task['summary']
        else:
            return jsonify({'error': 'No transcript or summary available for regeneration'}), 400
        
        # Create a new task for the regenerated audio
        new_task_id = str(uuid.uuid4())
        with _tasks_lock:
            tasks[new_task_id] = {
                'status': 'running',
                'created_at': datetime.now(),
                'original_task_id': task_id,
                'language_code': language_code,
                'voice_name': voice_name
            }
        
        # Start regeneration in a separate thread
        thread = threading.Thread(target=regenerate_audio_worker, args=(new_task_id, transcript, language_code, voice_name))
        thread.start()
        
        return jsonify({
            'task_id': new_task_id,
            'message': f'Regenerating audio in {get_language_name(language_code)}...'
        })
        
    except Exception as e:
        print(f"Error starting audio regeneration: {e}")
        return jsonify({'error': f'Failed to start audio regeneration: {str(e)}'}), 500

def regenerate_audio_worker(task_id, transcript, language_code, voice_name):
    """Worker function to regenerate audio in different language."""
    try:
        from google.cloud import texttospeech
        import os
        
        print(f"DEBUG: Starting audio regeneration for task {task_id}")
        print(f"DEBUG: Language: {language_code}, Voice: {voice_name}")
        
        # Initialize TTS client
        client = texttospeech.TextToSpeechClient()
        
        # Set up voice selection
        if voice_name:
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
        else:
            # Get available voices for the language
            voices = client.list_voices()
            available_voices = []
            for v in voices.voices:
                if language_code in v.language_codes:
                    available_voices.append(v.name)
            
            if not available_voices:
                raise Exception(f"No voices available for language {language_code}")
            
            # Use the first available voice
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=available_voices[0]
            )
        
        # Set up audio config
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )
        
        # Create synthesis input
        synthesis_input = texttospeech.SynthesisInput(text=transcript)
        
        # Perform the synthesis
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        # Save the audio file
        filename = f"news_broadcast_{language_code}_{task_id[:8]}.mp3"
        audio_path = os.path.join('glconnect', 'static', 'audio', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        with open(audio_path, 'wb') as out:
            out.write(response.audio_content)
        
        print(f"DEBUG: Regenerated audio saved to: {audio_path}")
        
        # Update task status
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]['status'] = 'completed'
                tasks[task_id]['completed_at'] = datetime.now()
                tasks[task_id]['result'] = {
                    'audio_file_path': audio_path,
                    'audio_url': f'/routes2/news/audio/{filename}',
                    'language_code': language_code,
                    'voice_name': voice.name,
                    'transcript': transcript
                }
                print(f"DEBUG: Task {task_id} marked as completed")
        
        # Force garbage collection
        import gc
        gc.collect()
        print(f"DEBUG: Garbage collection completed for task {task_id}")
        
    except Exception as e:
        print(f"ERROR in audio regeneration: {e}")
        import traceback
        print(f"ERROR traceback: {traceback.format_exc()}")
        with _tasks_lock:
            if task_id in tasks:
                tasks[task_id]['status'] = 'failed'
                tasks[task_id]['failed_at'] = datetime.now()
                tasks[task_id]['error'] = f"Audio regeneration failed: {str(e)}"
                print(f"DEBUG: Task {task_id} marked as failed due to: {e}")
