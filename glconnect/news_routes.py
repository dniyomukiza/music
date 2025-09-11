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
                error_msg = f"'{topic}' is not a valid news topic. Please enter topics like politics, economy, sports, technology, health, world affairs, etc."
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
    
    # Configure Gemini
    genai.configure(api_key=config.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash')
    
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
            
            # Categorize the topic with confidence tracking
            category, confidence = categorize_topic_with_confidence(topic)
            
            # Update counts
            analytics_data['category_counts'][category] += 1
            analytics_data['topic_counts'][topic] += 1
            analytics_data['daily_searches'][current_date] += 1
            
            # Add to category topics with confidence
            if topic not in analytics_data['category_topics'][category]:
                analytics_data['category_topics'][category].append(topic)
            
            # Track categorization confidence for monitoring
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
    try:
        # Use the ADK agent system for sophisticated news generation
        print("Using ADK agent system with Google Cloud TTS...")
        print("Following pattern: jingle → intro → transition → report → thank you → outro → jingle")
        
        # Run the ADK agent system directly (no threading needed)
        print(f"Starting ADK agent news generation for topics: {topics}")
        output = generate_broadcast(topics)
        print("ADK agent system completed successfully")
        print(f"DEBUG: Output type: {type(output)}")
        print(f"DEBUG: Output content: {str(output)[:500]}...")
        
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
                tasks[task_id]['result'] = output
            
            # Clean up old audio files after successful generation
            cleanup_old_audio_files()
            print("ADK agent system completed successfully!")
            return
            
    except Exception as e:
        print(f"Error in ADK agent news generation: {e}")
        with _tasks_lock:
            tasks[task_id]['status'] = 'failed'
            tasks[task_id]['error'] = f"e : {e}"

@news_bp.route('/')
def index():
    from .forms import KeywordForm
    form = KeywordForm()
    return render_template('newsgen.html', form=form)

@news_bp.route('/audio/<filename>')
def serve_audio(filename):
    """Serve audio files from the glconnect/static/audio directory."""
    from flask import send_from_directory
    import os
    
    # Try multiple possible audio directory locations
    possible_dirs = [
        os.path.join(os.getcwd(), 'glconnect', 'static', 'audio'),
        os.path.abspath('glconnect/static/audio'),
        '/usr/src/appdir/glconnect/static/audio',  # Docker container path
        './glconnect/static/audio'
    ]
    
    print(f"DEBUG: Looking for audio file: {filename}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    
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
    
    print(f"ERROR: Audio file {filename} not found in any expected location")
    return "Audio file not found", 404

@news_bp.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    # Handle both string and list inputs
    if isinstance(data['topics'], str):
        topics = [topic.strip() for topic in data['topics'].split(',')]
    else:
        topics = [topic.strip() for topic in data['topics']]
    # Filter to only relevant topics
    relevant_topics = []
    for topic in topics:
        is_relevant, confidence, reason = is_relevant_topic(topic)
        if is_relevant:
            relevant_topics.append(topic)
        else:
            print(f"DEBUG: Topic '{topic}' rejected: {reason} (confidence: {confidence})")

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
    """Main analytics page showing dominant topics by category with LLM categorization."""
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
        
        # Get categorization confidence statistics
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
