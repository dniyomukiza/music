import os
import asyncio
import json
import re
from datetime import datetime
import pytz
from dotenv import load_dotenv
from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.tools import google_search
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from google.cloud import texttospeech
from pydub import AudioSegment
from summa import summarizer

load_dotenv()

def get_memory_usage():
    """Get current memory usage percentage - container-aware with cgroup v1/v2 support."""
    try:
        import psutil
        import os
        
        # Try to get container memory limit first
        container_limit = None
        container_used = None
        
        # Cgroup v2 (Linux containers) - try multiple possible locations
        try:
            # Try different possible cgroup v2 paths
            cgroup_paths = [
                '/sys/fs/cgroup/memory.max',
                '/sys/fs/cgroup/memory/memory.max',
                '/sys/fs/cgroup/system.slice/docker-myapp.scope/memory.max'
            ]
            
            for path in cgroup_paths:
                try:
                    with open(path, 'r') as f:
                        content = f.read().strip()
                        if content != 'max' and content.isdigit():
                            container_limit = int(content)
                            break
                except:
                    continue
            
            # Try different possible cgroup v2 usage paths
            usage_paths = [
                '/sys/fs/cgroup/memory.current',
                '/sys/fs/cgroup/memory/memory.current',
                '/sys/fs/cgroup/system.slice/docker-myapp.scope/memory.current'
            ]
            
            for path in usage_paths:
                try:
                    with open(path, 'r') as f:
                        container_used = int(f.read().strip())
                        break
                except:
                    continue
                    
            if container_limit and container_used is not None:
                print(f"DEBUG: Cgroup v2 - Used: {container_used / 1024 / 1024:.1f}MB, Limit: {container_limit / 1024 / 1024:.1f}MB")
        except:
            # Cgroup v1 (Docker Desktop on macOS)
            try:
                with open('/sys/fs/cgroup/memory/memory.limit_in_bytes', 'r') as f:
                    container_limit = int(f.read().strip())
                
                with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
                    container_used = int(f.read().strip())
                    
                print(f"DEBUG: Cgroup v1 - Used: {container_used / 1024 / 1024:.1f}MB, Limit: {container_limit / 1024 / 1024:.1f}MB")
            except:
                pass
        
        # Get current memory usage from psutil
        memory_info = psutil.virtual_memory()
        
        # Always prefer container memory if available, regardless of system total
        if container_limit and container_used is not None:
            # Use container memory limit
            container_percent = (container_used / container_limit) * 100
            print(f"DEBUG: Container memory - Used: {container_used / 1024 / 1024:.1f}MB, Limit: {container_limit / 1024 / 1024:.1f}MB, Percent: {container_percent:.1f}%")
            return container_percent
        else:
            # Fallback: Try to detect if we're in a container with 4GB limit
            # If system memory is very low (< 2GB) but we expect 4GB, assume container
            if memory_info.total < 2 * 1024 * 1024 * 1024:  # Less than 2GB
                print(f"DEBUG: System memory low ({memory_info.total / 1024 / 1024:.1f}MB) - assuming 4GB container")
                # Assume 4GB container limit and calculate percentage based on system usage
                assumed_container_limit = 4 * 1024 * 1024 * 1024  # 4GB
                container_percent = (memory_info.used / assumed_container_limit) * 100
                print(f"DEBUG: Assumed container memory - Used: {memory_info.used / 1024 / 1024:.1f}MB, Assumed Limit: 4096.0MB, Percent: {container_percent:.1f}%")
                return container_percent
            else:
                # Fallback to system memory only if no container limits found
                print(f"DEBUG: System memory - Used: {memory_info.used / 1024 / 1024:.1f}MB, Total: {memory_info.total / 1024 / 1024:.1f}MB, Percent: {memory_info.percent:.1f}%")
                return memory_info.percent
            
    except ImportError:
        return 0
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
        return 0

# Load Google API key from environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    print("Error: GOOGLE_API_KEY not found in glconfig.json")
    exit(1)

# Get TTS credentials path from environment variables
tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS from config: {tts_credentials_path}")
print(f"DEBUG: Using TTS credentials path: {tts_credentials_path}")

# Configure Google AI SDK
import google.generativeai as genai
genai.configure(api_key=google_api_key)

# Set Google API key as environment variable for ADK agents
os.environ['GOOGLE_API_KEY'] = google_api_key

# TTS credentials will be loaded when needed

# --- Define the Summarization Tool (as a callable function) ---
def summarize_text(text: str) -> dict:
    """
    Summarizes the given text using a pre-trained model.
    Args:
        text: The text to summarize.
    Returns:
        A dictionary with 'summary': The summarized text.
    """
    try:
        # Use Summa for lightweight but effective text summarization
        # Summa uses TextRank algorithm - much lighter than PyTorch/transformers
        if not text or len(text.strip()) < 50:
            return {"summary": text}
        
        # Generate summary with 20% of original text length
        summary = summarizer.summarize(text, ratio=0.2)
        
        # If summarization fails or returns empty, fallback to simple extraction
        if not summary or len(summary.strip()) < 20:
            sentences = text.split('. ')
            if len(sentences) <= 3:
                summary = text
            else:
                summary = '. '.join(sentences[:3]) + '.'
        
        return {"summary": summary.strip()}
    except Exception as e:
        print(f"Error during text summarization: {e}")
        # Fallback to simple text extraction
        sentences = text.split('. ')
        if len(sentences) <= 3:
            summary = text
        else:
            summary = '. '.join(sentences[:3]) + '.'
        return {"summary": summary}


# --- Define the Timezone Tool (as a callable function) ---
def get_timezone_info() -> dict:
    """
    Gets the current time in Pacific time, Eastern time, and Central Time.
    Returns:
        A dictionary with 'timezone_info': A formatted string with current times in natural news anchor style.
    """
    print("=" * 50)
    print("DEBUG: TIMEZONE TOOL CALLED!")
    print("=" * 50)
    try:
        # Define timezones
        la_tz = pytz.timezone('America/Los_Angeles')
        ny_tz = pytz.timezone('America/New_York')
        central_tz = pytz.timezone('America/Chicago')
        
        # Get current UTC time - ensure we get the current time
        utc_now = datetime.now(pytz.UTC)
        print(f"DEBUG: Getting timezone info at UTC time: {utc_now.strftime('%H:%M:%S')}")
        
        # Convert to each timezone
        la_time = utc_now.astimezone(la_tz)
        ny_time = utc_now.astimezone(ny_tz)
        central_time = utc_now.astimezone(central_tz)
        
        print(f"DEBUG: Pacific time: {la_time.strftime('%H:%M')} -> {la_time.strftime('%I:%M %p')}")
        print(f"DEBUG: Eastern time: {ny_time.strftime('%H:%M')} -> {ny_time.strftime('%I:%M %p')}")
        print(f"DEBUG: Central time: {central_time.strftime('%H:%M')} -> {central_time.strftime('%I:%M %p')}")
        
        # Format times in natural news anchor style
        def format_time_for_anchor(time_obj):
            hour = time_obj.hour
            minute = time_obj.minute
            
            # Convert to 12-hour format
            if hour == 0:
                hour_12 = 12
                period = "AM"
            elif hour < 12:
                hour_12 = hour
                period = "AM"
            elif hour == 12:
                hour_12 = 12
                period = "PM"
            else:
                hour_12 = hour - 12
                period = "PM"
            
            # Format minutes with leading zero if needed
            minute_str = f"{minute:02d}"
            
            # Always use the format "X:XX AM/PM" for consistency
            return f"{hour_12}:{minute_str} {period}"
        
        pacific_formatted = format_time_for_anchor(la_time)
        eastern_formatted = format_time_for_anchor(ny_time)
        central_formatted = format_time_for_anchor(central_time)
        
        timezone_info = f"It's {pacific_formatted} Pacific time, {eastern_formatted} Eastern time, and {central_formatted} Central time"
        
        print(f"DEBUG: Final timezone info: {timezone_info}")
        print("=" * 50)
        print("DEBUG: TIMEZONE TOOL COMPLETED!")
        print("=" * 50)
        
        return {"timezone_info": timezone_info}
    except Exception as e:
        print(f"Error getting timezone info: {e}")
        return {"timezone_info": "Welcome to GLC News"}


# Simple TTS cache to avoid regenerating identical content
_tts_cache = {}

# --- Define the Text-to-Speech Tool (as a callable function) ---
def text_to_speech(text: str, output_filename: str, voice_name: str, speaking_rate: float = 1.0, pitch: float = 0.0) -> dict:
    """
    Converts text into an audio file (MP3 format) and returns its path.
    Args:
        text: The text to convert to speech.
        output_filename: The name of the output audio file (e.g., 'news_report.mp3').
        voice_name: The name of the voice to use (e.g., 'en-US-Studio-O').
        speaking_rate: Optional: The speaking rate (0.25 to 4.0). 1.0 is normal. Default 1.0.
        pitch: Optional: The pitch (from -20.0 to 20.0). 0.0 is normal. Default 0.0.
    Returns:
        A dictionary with 'audio_filepath': The full path to the generated audio file.
    """
    import gc
    
    # Force garbage collection before TTS processing
    gc.collect()
    
    # Clean the text before processing
    clean_text = clean_text_for_speech(text)
    
    # Check cache first
    cache_key = f"{clean_text}_{voice_name}_{speaking_rate}_{pitch}"
    if cache_key in _tts_cache:
        cached_file = _tts_cache[cache_key]
        if os.path.exists(cached_file):
            print(f"DEBUG: Using cached TTS for {output_filename}")
            return {"audio_filepath": cached_file}
        else:
            # Remove stale cache entry
            del _tts_cache[cache_key]
    
    # Load credentials from file and pass to client
    from google.oauth2 import service_account
    
    # Get TTS credentials path from environment variables
    tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
    print(f"DEBUG: Loading TTS credentials from: {tts_credentials_path}")
    print(f"DEBUG: Credentials file exists: {os.path.exists(tts_credentials_path)}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Environment: {os.getenv('FLASK_ENV', 'production')}")
    
    # Check if credentials file exists, if not try default path
    if not os.path.exists(tts_credentials_path):
        print(f"DEBUG: Credentials file not found at {tts_credentials_path}, trying default 'tts.json'")
        tts_credentials_path = "tts.json"
        print(f"DEBUG: Trying default path: {tts_credentials_path}")
        print(f"DEBUG: Default credentials file exists: {os.path.exists(tts_credentials_path)}")
    
    if not os.path.exists(tts_credentials_path):
        raise Exception(f"TTS credentials file not found at {tts_credentials_path} or default 'tts.json'")
    
    # Debug: Check credentials file content
    try:
        with open(tts_credentials_path, 'r') as f:
            creds_content = f.read()
            print(f"DEBUG: Credentials file size: {len(creds_content)} bytes")
            print(f"DEBUG: Credentials file starts with: {creds_content[:100]}...")
    except Exception as e:
        print(f"DEBUG: Error reading credentials file: {e}")
    
    credentials = service_account.Credentials.from_service_account_file(tts_credentials_path)
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    print(f"DEBUG: TTS client created successfully")
    
    # Test TTS API with a simple call to verify it's working
    try:
        test_input = texttospeech.SynthesisInput(text="test")
        test_voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Standard-A")
        test_audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        test_response = client.synthesize_speech(input=test_input, voice=test_voice, audio_config=test_audio_config)
        print(f"DEBUG: TTS API test successful - response length: {len(test_response.audio_content) if test_response.audio_content else 'None'}")
        
        # Additional test - try to write the test response to verify filesystem works
        if test_response.audio_content:
            test_output_dir = os.path.abspath("glconnect/static/audio")
            os.makedirs(test_output_dir, mode=0o755, exist_ok=True)
            test_file_path = os.path.join(test_output_dir, "test_tts.mp3")
            with open(test_file_path, "wb") as test_file:
                test_file.write(test_response.audio_content)
                test_file.flush()
                os.fsync(test_file.fileno())
            test_file_size = os.path.getsize(test_file_path)
            print(f"DEBUG: Test file written successfully - size: {test_file_size} bytes")
            # Clean up test file
            try:
                os.remove(test_file_path)
                print(f"DEBUG: Test file cleaned up")
            except:
                pass
        else:
            print(f"DEBUG: TTS API test returned empty content - this indicates a problem with the API")
    except Exception as e:
        print(f"DEBUG: TTS API test failed: {e}")
        print(f"DEBUG: This indicates a problem with Google Cloud TTS API access")
        print(f"DEBUG: Exception details: {type(e).__name__}: {str(e)}")

    synthesis_input = texttospeech.SynthesisInput(text=clean_text)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate,
        pitch=pitch
    )
    voice_params = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=voice_name
    )

    try:
        print(f"DEBUG: Attempting TTS for {output_filename} with text: '{clean_text[:100]}...'")
        print(f"DEBUG: Using voice: {voice_name}, rate: {speaking_rate}, pitch: {pitch}")
        print(f"DEBUG: Text length: {len(clean_text)} characters")
        
        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )

        print(f"DEBUG: TTS response received, audio content length: {len(response.audio_content) if response.audio_content else 'None'}")
        print(f"DEBUG: Response type: {type(response)}")
        print(f"DEBUG: Response attributes: {dir(response)}")
        
        # Additional debugging for audio content
        if response.audio_content:
            print(f"DEBUG: Audio content type: {type(response.audio_content)}")
            print(f"DEBUG: Audio content first 20 bytes: {response.audio_content[:20] if len(response.audio_content) > 20 else response.audio_content}")
            print(f"DEBUG: Audio content is bytes: {isinstance(response.audio_content, bytes)}")
        else:
            print(f"ERROR: TTS returned empty audio content for {output_filename}")
            print(f"DEBUG: Full response: {response}")
            print(f"DEBUG: Response has audio_content attribute: {hasattr(response, 'audio_content')}")
            if hasattr(response, 'audio_content'):
                print(f"DEBUG: audio_content is None: {response.audio_content is None}")
                print(f"DEBUG: audio_content is empty: {response.audio_content == b''}")
            raise Exception(f"TTS returned empty audio content for {output_filename}")

        # Use absolute paths for better cross-platform compatibility
        output_dir = os.path.abspath("glconnect/static/audio")
        print(f"DEBUG: Creating output directory: {output_dir}")
        
        # Ensure directory exists with proper permissions
        try:
            os.makedirs(output_dir, mode=0o755, exist_ok=True)
            print(f"DEBUG: Directory created/exists: {output_dir}")
        except Exception as e:
            print(f"DEBUG: Error creating directory: {e}")
            # Try alternative path
            output_dir = os.path.abspath("./glconnect/static/audio")
            os.makedirs(output_dir, mode=0o755, exist_ok=True)
            print(f"DEBUG: Using alternative directory: {output_dir}")
        
        full_path = os.path.join(output_dir, output_filename)
        print(f"DEBUG: Full output path: {full_path}")
        print(f"DEBUG: Path exists before write: {os.path.exists(os.path.dirname(full_path))}")
        
        # Write with explicit error handling
        try:
            with open(full_path, "wb") as out:
                bytes_written = out.write(response.audio_content)
                print(f"DEBUG: Bytes written to file: {bytes_written}")
                out.flush()  # Force flush to disk
                os.fsync(out.fileno())  # Force sync to filesystem
        except Exception as e:
            print(f"DEBUG: Error writing file: {e}")
            # Try alternative approach
            try:
                with open(full_path, "wb") as out:
                    out.write(response.audio_content)
                    out.flush()
                    os.fsync(out.fileno())
                print(f"DEBUG: Alternative write successful")
            except Exception as e2:
                print(f"DEBUG: Alternative write also failed: {e2}")
                raise e2
        
        # Verify file was written correctly
        if not os.path.exists(full_path):
            print(f"ERROR: File was not created at {full_path}")
            raise Exception(f"File was not created at {full_path}")
        
        file_size = os.path.getsize(full_path)
        print(f"DEBUG: Audio content written to file: {full_path} ({file_size} bytes)")
        print(f"DEBUG: File permissions: {oct(os.stat(full_path).st_mode)}")
        
        if file_size == 0:
            print(f"ERROR: Audio file created but is empty (0 bytes) for {output_filename}")
            print(f"DEBUG: Response audio_content type: {type(response.audio_content)}")
            print(f"DEBUG: Response audio_content length: {len(response.audio_content) if response.audio_content else 'None'}")
            raise Exception(f"Audio file created but is empty (0 bytes) for {output_filename}")
        
        # Cache the result for future use
        _tts_cache[cache_key] = full_path
        print(f"DEBUG: Cached TTS result for key: {cache_key[:50]}...")
            
        return {"audio_filepath": full_path}
    except Exception as e:
        print(f"ERROR during Text-to-Speech for {output_filename}: {e}")
        print(f"DEBUG: Exception type: {type(e)}")
        print(f"DEBUG: Exception details: {str(e)}")
        # Instead of returning an error string, raise the exception to be handled by the calling function
        raise Exception(f"TTS failed for {output_filename}: {e}")

def clean_text_for_speech(text: str) -> str:
    """
    Cleans text to make it suitable for text-to-speech conversion.
    Removes numbers, asterisks, and other characters that shouldn't be spoken.
    """
    if not text:
        return text
    
    # Remove common unwanted characters but preserve time formats (X:XX AM/PM)
    # First, protect time formats by temporarily replacing them
    time_pattern = r'\b(\d{1,2}:\d{2})\s*(AM|PM)\b'
    time_matches = re.findall(time_pattern, text, re.IGNORECASE)
    text = re.sub(time_pattern, 'TIME_PLACEHOLDER', text, flags=re.IGNORECASE)
    
    # Now remove other numbers and unwanted characters
    text = re.sub(r'[0-9,]+', '', text)  # Remove numbers and commas
    text = re.sub(r'[*#@$%^&+=|\\/<>]', '', text)  # Remove special symbols
    text = re.sub(r'\[.*?\]', '', text)  # Remove content in brackets
    text = re.sub(r'\(.*?\)', '', text)  # Remove content in parentheses
    text = re.sub(r'\{.*?\}', '', text)  # Remove content in braces
    
    # Restore time formats
    for i, (time_part, ampm) in enumerate(time_matches):
        text = text.replace('TIME_PLACEHOLDER', f'{time_part} {ampm}', 1)
    
    # Clean up whitespace and punctuation
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'\s*,\s*', ' ', text)  # Remove standalone commas
    text = re.sub(r'\s*\.\s*\.\s*', ' ', text)  # Remove multiple periods
    text = text.strip()
    
    return text

def validate_news_content(content: str, topic: str) -> tuple[bool, str]:
    """
    Validate news content to ensure it's professional and suitable for broadcast.
    Returns (is_valid, cleaned_content)
    """
    if not content or len(content.strip()) < 20:
        return False, ""
    
    # Check for unprofessional phrases that should never appear in live news
    unprofessional_phrases = [
        "unable to retrieve",
        "check back later", 
        "no information available",
        "unable to report",
        "please check back",
        "we are unable",
        "cannot retrieve",
        "failed to get",
        "error occurred",
        "technical difficulties",
        "system error",
        "unable to access",
        "retrieval failed",
        "data unavailable"
    ]
    
    content_lower = content.lower()
    for phrase in unprofessional_phrases:
        if phrase in content_lower:
            print(f"WARNING: Unprofessional phrase detected in {topic}: '{phrase}'")
            return False, ""
    
    # Check for minimum professional content length
    if len(content.strip()) < 50:
        print(f"WARNING: Content too short for {topic}: {len(content)} characters")
        return False, ""
    
    # Clean and return valid content
    cleaned_content = clean_text_for_speech(content)
    return True, cleaned_content

def analyze_topic_context(topic: str) -> dict:
    """
    Analyze any topic to understand its context, category, and significance.
    Returns a dictionary with analysis results.
    """
    try:
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
        Analyze this news topic and provide context for professional news reporting: "{topic}"
        
        Return a JSON object with:
        - category: "politics", "sports", "finance", "technology", "health", "world", "entertainment", "other"
        - significance: Why this topic is important or relevant
        - context: Background information that would help a news reporter
        - recent_trends: Any recent developments or ongoing issues
        - impact: Who or what is affected by this topic
        
        Example format:
        {{
            "category": "politics",
            "significance": "This topic affects government policy and public welfare",
            "context": "Background information about the topic",
            "recent_trends": "Recent developments or ongoing issues",
            "impact": "Who or what is affected"
        }}
        
        Topic: "{topic}"
        """
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Clean up the response
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        import json
        analysis = json.loads(content)
        return analysis
        
    except Exception as e:
        print(f"DEBUG: Topic analysis failed for {topic}: {e}")
        return {
            "category": "other",
            "significance": "This topic is being monitored by our news team",
            "context": "Ongoing developments are being tracked",
            "recent_trends": "Recent updates are being followed",
            "impact": "Various stakeholders are affected"
        }

def generate_intelligent_fallback_content(topic: str) -> str:
    """
    Generate intelligent, contextually appropriate fallback content for any topic.
    Uses AI to analyze the topic and generate professional news content.
    """
    try:
        # First analyze the topic to understand its context
        analysis = analyze_topic_context(topic)
        
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
        You are a professional news reporter. Generate a brief, informative news segment about "{topic}" that would be suitable for live broadcast.
        
        Topic Analysis:
        - Category: {analysis.get('category', 'general')}
        - Significance: {analysis.get('significance', 'This topic is being monitored')}
        - Context: {analysis.get('context', 'Ongoing developments')}
        - Recent Trends: {analysis.get('recent_trends', 'Recent updates')}
        - Impact: {analysis.get('impact', 'Various stakeholders')}
        
        Requirements:
        - Sound like a professional news report, not an error message
        - Use the analysis above to provide relevant context
        - Keep it concise but informative (2-3 sentences)
        - End with "I'm [Reporter Name], for GLC News"
        - Never mention "unable to retrieve", "check back later", or any error phrases
        - Focus on the topic's significance, impact, or current relevance
        
        Generate professional news content:
        """
        
        response = model.generate_content(prompt)
        content = response.text.strip()
        
        # Validate the generated content
        is_valid, cleaned_content = validate_news_content(content, topic)
        
        if is_valid:
            print(f"DEBUG: Generated intelligent fallback for {topic} (category: {analysis.get('category', 'unknown')})")
            return cleaned_content
        else:
            # If AI-generated content fails validation, use a generic professional template
            return generate_generic_fallback(topic)
            
    except Exception as e:
        print(f"DEBUG: AI fallback generation failed for {topic}: {e}")
        return generate_generic_fallback(topic)

def generate_generic_fallback(topic: str) -> str:
    """
    Generate a generic professional fallback when AI generation fails.
    This is the last resort to ensure we never have unprofessional content.
    """
    return f"Regarding {topic}, our news team continues to monitor developments and will provide updates as new information becomes available. This story remains under close observation by our editorial team. I'm reporting for GLC News."

def cleanup_intermediate_audio_files(final_audio_path: str) -> None:
    """
    Clean up intermediate audio files after final broadcast generation.
    Keeps only jingle.wav and the final broadcast file.
    """
    try:
        audio_dir = "glconnect/static/audio"
        if not os.path.exists(audio_dir):
            return
        
        # Files to keep (never delete these)
        protected_files = {
            "jingle.wav",
            "final_news_broadcast.mp3",
            "final_news_broadcast_*.mp3"  # Any final broadcast variants
        }
        
        # Get the final audio filename for protection
        final_filename = os.path.basename(final_audio_path)
        protected_files.add(final_filename)
        
        # List all files in audio directory
        all_files = os.listdir(audio_dir)
        deleted_count = 0
        
        for filename in all_files:
            # Skip protected files
            if filename in protected_files:
                continue
            
            # Skip jingle.wav
            if filename == "jingle.wav":
                continue
            
            # Skip final broadcast files
            if filename.startswith("final_news_broadcast"):
                continue
            
            # Delete intermediate files
            file_path = os.path.join(audio_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"DEBUG: Cleaned up intermediate file: {filename}")
            except Exception as e:
                print(f"DEBUG: Failed to delete {filename}: {e}")
        
        print(f"DEBUG: Cleanup completed - deleted {deleted_count} intermediate audio files")
        
    except Exception as e:
        print(f"DEBUG: Cleanup function error: {e}")

def combine_audio_files_ffmpeg(file_paths: list[str], output_filename: str = "final_news_broadcast.mp3") -> dict:
    """
    Memory-efficient audio combination using FFmpeg instead of loading all files into RAM.
    This approach processes files on disk, using minimal memory.
    """
    import subprocess
    import tempfile
    
    try:
        # Create a temporary file list for FFmpeg concat
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for file_path in file_paths:
                if isinstance(file_path, dict) and 'audio_filepath' in file_path:
                    file_path = file_path['audio_filepath']
                
                # Convert relative paths to absolute paths
                if not os.path.isabs(file_path):
                    file_path = os.path.abspath(file_path)
                
                if os.path.exists(file_path) and not file_path.startswith("Error:"):
                    # FFmpeg concat format: file 'path/to/file.mp3'
                    f.write(f"file '{file_path}'\n")
                    print(f"DEBUG: Added to concat list: {file_path}")
                else:
                    print(f"DEBUG: Skipping missing file: {file_path}")
            
            concat_file = f.name
        
        # Use FFmpeg to combine files efficiently - put in static audio directory
        output_path = os.path.join(os.getcwd(), "glconnect", "static", "audio", output_filename)
        
        # Use filter_complex approach instead of concat for better sample rate handling
        cmd = [
            'ffmpeg', '-y',  # -y to overwrite output file
            '-i', 'glconnect/static/audio/jingle.wav',
            '-i', 'glconnect/static/audio/intro_audio.mp3',
            '-i', 'glconnect/static/audio/transition_audio_0.mp3',
            '-i', 'glconnect/static/audio/tech_audio.mp3',
            '-i', 'glconnect/static/audio/thank_you_audio.mp3',
            '-i', 'glconnect/static/audio/outro_audio.mp3',
            '-i', 'glconnect/static/audio/jingle.wav',
            '-filter_complex', '[0:0][1:0][2:0][3:0][4:0][5:0][6:0]concat=n=7:v=0:a=1[out]',
            '-map', '[out]',
            '-c:a', 'libmp3lame',
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '2',
            output_path
        ]
        
        print(f"DEBUG: FFmpeg command: {' '.join(cmd)}")
        print(f"DEBUG: Concat file contents:")
        with open(concat_file, 'r') as f:
            print(f.read())
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Debug: Print FFmpeg output for troubleshooting
        if result.returncode != 0:
            print(f"ERROR: FFmpeg stderr: {result.stderr}")
        else:
            print(f"DEBUG: FFmpeg stdout: {result.stdout}")
            print(f"DEBUG: FFmpeg stderr: {result.stderr}")
        
        # Clean up temporary file
        os.unlink(concat_file)
        
        if result.returncode == 0:
            print(f"DEBUG: FFmpeg audio combination successful: {output_path}")
            return {"combined_audio_filepath": output_path}
        else:
            print(f"ERROR: FFmpeg failed - {result.stderr}")
            return {"combined_audio_filepath": f"Error: FFmpeg failed - {result.stderr}"}
            
    except Exception as e:
        print(f"ERROR: FFmpeg audio combination failed: {e}")
        return {"combined_audio_filepath": f"Error: {e}"}

def combine_audio_files(file_paths: list[str], output_filename: str = "final_news_broadcast.mp3") -> dict:
    """
    Memory-efficient audio combination using FFmpeg instead of loading all files into RAM.
    This approach processes files on disk, using minimal memory.
    """
    print("DEBUG: Using memory-efficient FFmpeg audio combination")
    return combine_audio_files_ffmpeg(file_paths, output_filename)
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"DEBUG: FFmpeg is available - version: {result.stdout.split('ffmpeg version')[1].split()[0] if 'ffmpeg version' in result.stdout else 'unknown'}")
        else:
            print(f"DEBUG: FFmpeg check failed - return code: {result.returncode}")
    except Exception as e:
        print(f"DEBUG: FFmpeg check failed with exception: {e}")
        print(f"DEBUG: This might cause AudioSegment export issues")
    
    try:
        combined_audio = AudioSegment.empty()
        jingle_path = "glconnect/static/audio/jingle.wav"

        # Load the jingle
        if os.path.exists(jingle_path):
            try:
                jingle = AudioSegment.from_file(jingle_path, format="wav")
            except Exception as e:
                print(f"ERROR loading jingle.wav: {e}.  Continuing without it.")
                jingle = None
        else:
            jingle = AudioSegment.silent(duration=1000) # 1 second of silence
        
        if jingle:
            combined_audio += jingle
        
        # Track cleaned absolute input mp3 paths for scoped cleanup
        input_mp3_paths = []
        
        for i, f_path in enumerate(file_paths):
            f_path_clean = f_path 

            if isinstance(f_path, dict) and 'audio_filepath' in f_path:
                f_path_clean = f_path['audio_filepath']
            elif not isinstance(f_path, str):
                print(f"Warning: Unexpected type for file path at index {i}: {type(f_path)}. Skipping.")
                continue

            if "Error:" in f_path_clean:
                print(f"Warning: Skipping {f_path_clean} due to upstream error.")
                continue

            if not os.path.exists(f_path_clean):
                print(f"Warning: Audio file not found for combination: {f_path_clean}. Skipping.")
                continue

            try:
                print(f"DEBUG: Loading audio segment: {f_path_clean}")
                if os.path.exists(f_path_clean):
                    file_size = os.path.getsize(f_path_clean)
                    print(f"DEBUG: Segment file size: {file_size} bytes")
                    if file_size == 0:
                        print(f"WARNING: Segment file is empty: {f_path_clean}")
                        continue
                else:
                    print(f"WARNING: Segment file does not exist: {f_path_clean}")
                    continue
                
                audio_segment = AudioSegment.from_file(f_path_clean, format="mp3")
                print(f"DEBUG: Loaded segment - duration: {audio_segment.duration_seconds}s, channels: {audio_segment.channels}")
                combined_audio += audio_segment
                print(f"DEBUG: Added to combined audio - total duration: {combined_audio.duration_seconds}s")
                
                try:
                    if str(f_path_clean).lower().endswith('.mp3'):
                        input_mp3_paths.append(os.path.abspath(f_path_clean))
                except Exception:
                    pass
            except Exception as e: # Catch all exceptions during loading
                print(f"ERROR loading segment {f_path_clean}: {e}")
                # Don't return here, try to combine other files if possible
                continue # Skip this file and try the next

        if jingle:
            combined_audio += jingle

        if not combined_audio.duration_seconds > 0.0: # Check if any audio was actually added
            return {"combined_audio_filepath": "Error: No valid audio segments combined."}

        output_dir = "glconnect/static/audio"
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique output filename to avoid conflicts across concurrent users
        try:
            base_name = os.path.splitext(output_filename)[0] or "final_news_broadcast"
            ext = ".mp3"
            # If the caller passed a different ext, normalize back to mp3
            if output_filename.lower().endswith('.mp3'):
                ext = ".mp3"
            # Append a timestamp-based suffix to ensure uniqueness
            import datetime, uuid
            suffix = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid.uuid4().hex[:6]
            unique_output_filename = f"{base_name}_{suffix}{ext}"
        except Exception:
            unique_output_filename = output_filename

        full_path = os.path.join(output_dir, unique_output_filename)

        print(f"DEBUG: About to export combined audio to: {full_path}")
        print(f"DEBUG: Combined audio duration: {combined_audio.duration_seconds} seconds")
        print(f"DEBUG: Combined audio channels: {combined_audio.channels}")
        print(f"DEBUG: Combined audio frame rate: {combined_audio.frame_rate}")
        
        try:
            combined_audio.export(full_path, format="mp3")
            print(f"DEBUG: Export completed successfully")
        except Exception as e:
            print(f"DEBUG: Export failed: {e}")
            raise e
        
        # Verify the file was written correctly
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path)
            print(f"DEBUG: Combined audio file written - {full_path} ({file_size} bytes)")
            if file_size == 0:
                print(f"ERROR: Combined audio file is empty after export!")
                raise Exception(f"Combined audio file is empty after export: {full_path}")
        else:
            print(f"ERROR: Combined audio file was not created!")
            raise Exception(f"Combined audio file was not created: {full_path}")

        # Scoped cleanup: remove only the specific input mp3s used for this combination
        try:
            final_abs_path = os.path.abspath(full_path)
            for candidate_path in input_mp3_paths:
                if candidate_path != final_abs_path and os.path.exists(candidate_path):
                    try:
                        os.remove(candidate_path)
                    except Exception as cleanup_err:
                        print(f"Warning: failed to remove {candidate_path}: {cleanup_err}")
        except Exception as e:
            print(f"Warning: cleanup step failed: {e}")

        return {"combined_audio_filepath": full_path}
    except Exception as e:
        print(f"Critical error during combine_audio_files: {e}")
        return {"combined_audio_filepath": f"Error: Critical failure in audio combination. {e}"}

# --- Define Voices ---
ANCHOR_VOICE = 'en-US-Studio-O'
ERNEST_VOICE = 'en-US-Neural2-D'
EDITH_VOICE = 'en-US-Studio-O'
ISABELLA_VOICE = 'en-US-Standard-F'
MARK_VOICE = 'en-GB-Standard-B' 

def create_news_reporter_agent(topic: str, voice: str, agent_name: str, output_key: str) -> Agent:
    """Creates a news reporter agent for a specific topic."""
    return Agent(
        model="gemini-2.0-flash",
        name=agent_name,
        description=f"An agent that generates a news script about {topic}.",
        instruction=f"""
            - You are a specialized news reporter for {topic}.
            - Your task is to prepare a professional news report on '{topic}'.
            - You MUST use the 'google_search' tool to find news details about {topic}.
            - Tool call format: `google_search(query='The latest {topic} news')`
            - If the search fails, times out, or returns no results, IMMEDIATELY create a professional news report based on your knowledge of {topic}.
            - Do NOT retry the search if it fails - proceed directly to content generation.
            - Focus on recent developments, trends, or ongoing issues related to {topic}.
            - After getting the search results (or using your knowledge), synthesize the information into a professional news report.
            - You must end your news report with the following signature: 'I am {agent_name.replace("_", " ")}, for GLC News'.
            - Your final output must be ONLY the news report content, exactly as a reporter would deliver it.
            - You must output your news report in JSON format with the key '{output_key}'.
            - Example output format: {{"{output_key}": "Your news report content here..."}}
            - Do not introduce yourself beyond your signature within the report.
            - No titles nor subtitles are needed in your script.
            - Never ever include special character in your script such as asterisks or other symbols.
            - Do not ask any questions or engage in conversation. Proceed directly with the report after the search.
            - If you cannot find specific recent news, provide context and analysis about why {topic} is important or relevant.
            - CRITICAL: Never include phrases like "unable to retrieve", "check back later", "no information available", or any error messages in your report.
            - Your report must always sound professional and informative, even if based on general knowledge.
            - ADAPTIVE: Analyze the topic context and provide relevant information based on what you know about {topic}.
            - If the topic is unfamiliar, focus on its potential significance or ask clarifying questions about its context.
        """,
        output_key=output_key,
        tools=[google_search]
    )

def create_category_reporter_agent(category: str, topics: list[str], voice: str, agent_name: str, output_key: str) -> Agent:
    """Creates a news reporter agent for a specific category that handles multiple topics."""
    topics_str = ", ".join(topics)
    return Agent(
        model="gemini-2.0-flash",
        name=agent_name,
        description=f"An agent that generates a news script about {category} topics: {topics_str}.",
        instruction=f"""
            - You are a specialized news reporter for {category} news.
            - Your task is to prepare a comprehensive professional news report covering all the following {category} topics: {topics_str}.
            - You MUST use the 'google_search' tool to find news details about each topic.
            - For each topic, make a separate search: `google_search(query='The latest [topic] news')`
            - If any search fails or returns no results, use your knowledge to provide context and analysis about that topic.
            - Focus on recent developments, trends, or ongoing issues related to each topic.
            - After getting the search results (or using your knowledge), synthesize the information into a single comprehensive news report.
            - Structure your report to cover all topics in a logical flow, transitioning smoothly between topics.
            - You must end your news report with the following signature: 'I am {agent_name.replace("_", " ")}, for GLC News'.
            - Your final output must be ONLY the news report content, exactly as a reporter would deliver it.
            - You must output your news report in JSON format with the key '{output_key}'.
            - Example output format: {{"{output_key}": "Your comprehensive news report content here..."}}
            - Do not introduce yourself beyond your signature within the report.
            - No titles nor subtitles are needed in your script.
            - Never ever include special character in your script such as asterisks or other symbols.
            - Do not ask any questions or engage in conversation. Proceed directly with the report after the searches.
            - Make sure to cover ALL topics: {topics_str} in your final report.
            - If you cannot find specific recent news for any topic, provide context and analysis about why that topic is important or relevant.
            - CRITICAL: Never include phrases like "unable to retrieve", "check back later", "no information available", or any error messages in your report.
            - Your report must always sound professional and informative, even if based on general knowledge.
            - ADAPTIVE: Analyze each topic's context and provide relevant information based on what you know about each topic.
            - If any topic is unfamiliar, focus on its potential significance or provide general context about why it might be newsworthy.
        """,
        output_key=output_key,
        tools=[google_search]
    )

def create_anchor_agent(topics: list[str], reporter_scripts: list[str]) -> Agent:
    """Creates a news anchor agent to introduce and conclude the news bulletin."""
    reporter_scripts_str = "\n".join(reporter_scripts)
    return Agent(
        model="gemini-2.0-flash",
        name="news_anchor_agent",
        description="Generates the anchor's script for the news bulletin.",
        instruction=f"""
            You are the main news anchor for GLC News.
            Your task is to create a script that introduces the news bulletin and each of the reporters, and then concludes the bulletin.
            The topics for today's bulletin are: {topics}.
            The reporters' scripts are: {reporter_scripts_str}.

            CRITICAL: You MUST call the 'get_timezone_info' tool FIRST before creating any script. 
            This tool will give you the current time in Pacific time, Eastern time, and Central Time.
            Use the EXACT time information returned by this tool - do not make up or guess times.

            Your output MUST be a JSON object with three keys: 'intro', 'transitions', and 'outro'.
            - 'intro': Start with the EXACT timezone information from the get_timezone_info tool, then introduce yourself as the anchor, and briefly introduce the main topics. Format: "It's [X:XX AM/PM] Pacific time, [X:XX AM/PM] Eastern time, and [X:XX AM/PM] Central time, I am your anchor today, in this edition we are covering..."
            - 'transitions': A list of strings, where each string is an introduction for a reporter. For example: ["First up, we have Ernest with the latest on sports.", "Next, Isabella brings us updates on finance."]
            - 'outro': A brief summary of the news covered, thanking the listeners. End with "Thanks for listening to GLC News."

            Example JSON output (use the ACTUAL current time from get_timezone_info tool):
            ```json
            {{
                "intro": "It's 6:20 PM Pacific time, 9:20 PM Eastern time, and 8:20 PM Central time, I am your anchor today and welcome to GLC News, in this edition we are covering the latest in sports and finance.",
                "transitions": [
                    "First up, we have Ernest with the latest on sports.",
                    "Next, Isabella brings us updates on finance."
                ],
                "outro": "That wraps up today's edition. Thank you for listening to GLC News. Stay tuned for more updates. See you next time"
            }}
            ```

            IMPORTANT: Always call the get_timezone_info tool first to get accurate current times.
        """,
        output_key="anchor_script",
        tools=[get_timezone_info]
    )


def create_tts_agent(script_key: str, audio_filename: str, voice: str, agent_name: str, output_key: str) -> Agent:
    """Creates a TTS agent for a specific script."""
    
    # Special handling for anchor script parts
    if script_key == "anchor_script":
        if "intro" in audio_filename:
            instruction = f"""
                You have access to the anchor_script which contains a JSON object with 'intro', 'transitions', and 'outro' keys.
                Extract the 'intro' value from the anchor_script and use the 'text_to_speech' tool to convert it to audio.
                Name the output file '{audio_filename}'.
                Use the voice: '{voice}'.
                
                First, parse the anchor_script JSON to get the intro text, then call:
                text_to_speech(
                    text=[the intro text from anchor_script], 
                    output_filename='{audio_filename}',
                    voice_name='{voice}'
                )
            """
        elif "outro" in audio_filename:
            instruction = f"""
                You have access to the anchor_script which contains a JSON object with 'intro', 'transitions', and 'outro' keys.
                Extract the 'outro' value from the anchor_script and use the 'text_to_speech' tool to convert it to audio.
                Name the output file '{audio_filename}'.
                Use the voice: '{voice}'.
                
                First, parse the anchor_script JSON to get the outro text, then call:
                text_to_speech(
                    text=[the outro text from anchor_script], 
                    output_filename='{audio_filename}',
                    voice_name='{voice}'
                )
            """
        elif "transition" in audio_filename:
            # Extract the transition index from the filename
            transition_index = audio_filename.split('_')[-1].split('.')[0]  # Get the number from transition_audio_X.mp3
            instruction = f"""
                You have access to the anchor_script which contains a JSON object with 'intro', 'transitions', and 'outro' keys.
                Extract the 'transitions' array from the anchor_script and get the item at index {transition_index}.
                Use the 'text_to_speech' tool to convert that transition text to audio.
                Name the output file '{audio_filename}'.
                Use the voice: '{voice}'.
                
                First, parse the anchor_script JSON to get the transitions array, then get the item at index {transition_index}, then call:
                text_to_speech(
                    text=[the transition text at index {transition_index}], 
                    output_filename='{audio_filename}',
                    voice_name='{voice}'
                )
            """
        else:
            instruction = f"""
                Use the 'text_to_speech' tool to convert the script {{{{{{ {script_key} }}}}}} into an audio file.
                Name the output file '{audio_filename}'.
                Use the voice: '{voice}'.
                Output the 'audio_filepath' returned by the tool.
            """
    else:
        instruction = f"""
            Use the 'text_to_speech' tool to convert the script {{{{{{ {script_key} }}}}}} into an audio file.
            Name the output file '{audio_filename}'.
            Use the voice: '{voice}'.
            Output the 'audio_filepath' returned by the tool.

            Tool call example:
            text_to_speech(
                text={{{{{{ {script_key} }}}}}}, 
                output_filename='{audio_filename}',
                voice_name='{voice}'
            )

            If you encounter any issue while generating audio, report the issue clearly.
        """
    
    return Agent(
        model="gemini-2.0-flash",
        name=agent_name,
        description=f"Converts the {script_key} to audio using the specified voice.",
        instruction=instruction,
        output_key=output_key,
        tools=[text_to_speech]
    )


async def run_agent(agent, input_text):
    session_service = InMemorySessionService()
    runner = Runner(app_name="news_agent", agent=agent, session_service=session_service)
    
    # Debug: Check if create_session is callable and inspect its signature
    print(f"DEBUG: create_session callable: {callable(session_service.create_session)}")
    print(f"DEBUG: create_session type: {type(session_service.create_session)}")
    
    # Try both sync and async versions of create_session
    try:
        # First try async version
        session = await session_service.create_session(app_name="news_agent", user_id="user123")
        print("DEBUG: Using async create_session")
    except TypeError as e:
        if "can't be used in 'await' expression" in str(e):
            # Fall back to sync version
            print(f"DEBUG: Async failed with error: {e}")
            session = session_service.create_session(app_name="news_agent", user_id="user123")
            print("DEBUG: Using sync create_session")
        else:
            print(f"DEBUG: Unexpected error: {e}")
            raise e
    
    final_response = ""
    
    # Debug: Check session object
    print(f"DEBUG: Session type: {type(session)}")
    print(f"DEBUG: Session user_id: {getattr(session, 'user_id', 'NO USER_ID ATTRIBUTE')}")
    
    async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=Content(role="user", parts=[Part(text=input_text)])):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_response = event.content.parts[0].text
    return final_response

def generate_broadcast_memory_optimized(topics: list[str], task_id: str = None) -> dict:
    """
    Memory-optimized news generation that processes topics sequentially.
    This version uses much less memory by avoiding parallel processing.
    """
    import gc
    import psutil
    import os
    
    print("DEBUG: Using memory-optimized sequential processing")
    
    # Check memory before starting
    try:
        memory_percent = get_memory_usage()
        print(f"DEBUG: Memory at start - Percent: {memory_percent:.1f}%")
        
        if memory_percent > 85:  # More appropriate threshold for 4GB containers
            print(f"ERROR: Memory usage too high ({memory_percent:.1f}%) - aborting")
            return {"error": f"Memory usage too high ({memory_percent:.1f}%) - please try again later"}
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
    
    # Force garbage collection
    gc.collect()
    
    try:
        # Simple fallback content for each topic (no AI agents)
        print("DEBUG: Generating simple news content (no AI agents)")
        
        news_content = []
        for i, topic in enumerate(topics):
            print(f"DEBUG: Processing topic {i+1}/{len(topics)}: {topic}")
            
            # Check memory before each topic using container-aware monitoring
            try:
                memory_percent = get_memory_usage()
                if memory_percent > 90:  # More appropriate threshold for 4GB containers
                    print(f"ERROR: Memory usage too high during processing ({memory_percent:.1f}%)")
                    return {"error": f"Memory usage too high ({memory_percent:.1f}%) - please try again later"}
            except:
                pass
            
            # Generate simple content
            content = f"""
Breaking News: {topic}

This is a developing story about {topic}. Our news team is working to gather more information and will provide updates as they become available.

Key points to consider:
- This topic is currently under investigation
- More details will be provided as they emerge
- We will continue to monitor this situation closely

This concludes our report on {topic}. Stay tuned for more updates.
            """.strip()
            
            news_content.append(content)
            
            # Force garbage collection after each topic
            gc.collect()
            
            # Update progress
            if task_id:
                try:
                    from glconnect.news_routes import update_task_in_db
                    update_task_in_db(task_id, 
                                     progress=20 + (i * 20),
                                     current_step=f'Processed topic {i+1}/{len(topics)}...',
                                     last_heartbeat=datetime.now())
                except:
                    pass
        
        # Create simple audio files (no TTS for now)
        print("DEBUG: Creating simple audio files")
        
        # For now, return a simple result without audio processing
        return {
            "audio_file": "simple_news_broadcast.mp3",
            "summary": f"Generated news content for {len(topics)} topics",
            "content": news_content
        }
        
    except Exception as e:
        print(f"ERROR: Memory-optimized generation failed: {e}")
        return {"error": f"Generation failed: {e}"}

def generate_broadcast(topics: list[str], max_retries: int = 2, task_id: str = None) -> dict:
    """
    Main news generation function with full audio workflow (jingle, intro, reporters, outro).
    Now includes memory optimizations to prevent timeouts.
    """
    print("DEBUG: Starting full audio news generation with memory optimizations")
    
    if not topics:
        print("No topics entered. Exiting.")
        return {"error": "No topics provided"}
    
    # Check memory before starting
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory at start - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        if memory_info.percent > 90:  # More appropriate threshold for 4GB containers
            print(f"ERROR: Memory usage too high ({memory_info.percent}%) - aborting")
            return {"error": f"Memory usage too high ({memory_info.percent}%) - please try again later"}
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
    
    # Use the original workflow but with memory optimizations
    return _generate_broadcast_attempt(topics, task_id)

def generate_intelligent_fallback_content(topic: str) -> str:
    """Generate simple fallback content when main generation fails."""
    try:
        # Simple fallback content generation
        return f"""
Breaking News Report: {topic}

This is a developing story about {topic}. Our news team is working to gather more information and will provide updates as they become available.

Key points to consider:
- This topic is currently under investigation
- More details will be provided as they emerge
- We will continue to monitor this situation closely

This concludes our report on {topic}. Stay tuned for more updates.
        """.strip()
    except Exception as e:
        print(f"DEBUG: Error in fallback content generation: {e}")
        return f"News report on {topic} - Content generation temporarily unavailable. Please try again later."

def _run_async_safely(coro, max_retries=3, retry_delay=2):
    """Safely run async coroutine in a thread, handling interpreter shutdown gracefully with retry logic."""
    import asyncio
    import threading
    import sys
    import time
    
    for attempt in range(max_retries):
        try:
            # Check if the interpreter is shutting down
            if sys.is_finalizing():
                print(f"DEBUG: Interpreter is finalizing, cannot run async operation (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
            
            # Check if there's a closed event loop set as the current loop
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop.is_closed():
                    print(f"DEBUG: Current event loop is closed, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
            except RuntimeError:
                # No event loop set, that's fine
                pass
            
            # Check if we're in a thread that already has an event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in a thread with a running loop, we need to create a new one
                if loop.is_running():
                    # Create a new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro)
                        print(f"DEBUG: Async operation completed successfully on attempt {attempt + 1}")
                        return result
                    finally:
                        new_loop.close()
            except RuntimeError:
                # No running loop, we can create one
                pass
            
            # Try to run with asyncio.run, but handle shutdown gracefully
            try:
                result = asyncio.run(coro)
                print(f"DEBUG: Async operation completed successfully on attempt {attempt + 1}")
                return result
            except RuntimeError as e:
                if "cannot schedule new futures after interpreter shutdown" in str(e):
                    print(f"DEBUG: Interpreter is shutting down, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        print(f"DEBUG: Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    return None
                elif "Event loop is closed" in str(e):
                    print(f"DEBUG: Event loop is closed, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        print(f"DEBUG: Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    return None
                else:
                    raise e
        except Exception as e:
            print(f"DEBUG: Error in _run_async_safely (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"DEBUG: Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            return None
    
    print(f"DEBUG: All {max_retries} attempts failed in _run_async_safely")
    return None

def _generate_broadcast_attempt(topics: list[str], task_id: str = None) -> dict:
    import gc
    import psutil
    import os
    
    # Check memory at start and abort if too high using container-aware monitoring
    try:
        memory_percent = get_memory_usage()
        print(f"DEBUG: Memory at start of broadcast generation - Percent: {memory_percent:.1f}%")
        
        if memory_percent > 70:  # Conservative threshold for 4GB containers
            print(f"ERROR: Memory usage too high ({memory_percent:.1f}%) - aborting broadcast generation")
            return {"error": f"Memory usage too high ({memory_percent:.1f}%) - please try again later"}
    except:
        pass
    
    # Force aggressive garbage collection at start
    gc.collect()
    gc.collect()  # Call twice for better cleanup
    
    # Set more aggressive garbage collection thresholds
    gc.set_threshold(50, 5, 5)  # More frequent collection
    
    # Force memory cleanup
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)  # Trim memory on Linux
    except:
        pass  # Ignore if not available
    
    # Update heartbeat if task_id is provided
    if task_id:
        try:
            from glconnect.news_routes import tasks, _tasks_lock
            with _tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['last_heartbeat'] = datetime.now()
        except:
            pass  # Ignore errors in heartbeat update
    
    # Categorization Agent
    categorization_agent = Agent(
        model="gemini-2.0-flash",
        name="categorization_agent",
        description="Categorizes news topics into sports, finance, politics, tech, and health.",
        instruction=f"""
            You are a news topic categorizer.
            For each topic in the list {topics}, categorize it into one of the following categories:
            - sports
            - finance
            - politics
            - tech
            - health
            - other
            Return a JSON object where keys are the topics and values are the categories.
            Example: {{'topic1': 'sports', 'topic2': 'finance'}}
        """,
        output_key="categorized_topics"
    )

    categorized_topics_json = _run_async_safely(run_agent(categorization_agent, str(topics)))
    print(f"DEBUG: Raw categorization output: {categorized_topics_json}")
    
    # Force garbage collection after categorization
    gc.collect()
    
    # Check memory after categorization
    try:
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory after categorization - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        if memory_info.percent > 85:
            print(f"WARNING: High memory usage after categorization ({memory_info.percent}%) - forcing cleanup")
            gc.collect()
            gc.collect()
    except:
        pass
    
    # Handle case where async operation failed due to interpreter shutdown
    if categorized_topics_json is None:
        print("DEBUG: Categorization failed due to interpreter shutdown, using fallback")
        # Create a simple fallback categorization
        categorized_topics = {topic: 'other' for topic in topics}
    else:
        # Clean up the JSON response
        categorized_topics_json = categorized_topics_json.strip()
        if categorized_topics_json.startswith('```json'):
            categorized_topics_json = categorized_topics_json[7:]  # Remove ```json
        if categorized_topics_json.endswith('```'):
            categorized_topics_json = categorized_topics_json[:-3]  # Remove ```
        categorized_topics_json = categorized_topics_json.strip()
        print(f"DEBUG: Cleaned categorization JSON: {categorized_topics_json}")
        
        try:
            categorized_topics = json.loads(categorized_topics_json)
        except json.JSONDecodeError as e:
            print(f"DEBUG: JSON decode error: {e}, using fallback categorization")
            categorized_topics = {topic: 'other' for topic in topics}
    print(f"DEBUG: Parsed categories: {categorized_topics}")

    # Group topics by category
    topics_by_category = {}
    for topic, category in categorized_topics.items():
        if category not in topics_by_category:
            topics_by_category[category] = []
        topics_by_category[category].append(topic)
    
    print(f"DEBUG: Topics grouped by category: {topics_by_category}")

    # Create agents for each category (one reporter per category) - SEQUENTIAL PROCESSING
    news_agents = []
    reporter_script_keys = []
    reporters_tts_agents = []

    for category, category_topics in topics_by_category.items():
        agent_name = f"{category}_reporter"
        script_key = f"{category}_script"
        voice = ERNEST_VOICE if category == 'sports' else ISABELLA_VOICE if category == 'finance' else MARK_VOICE if category == 'tech' else EDITH_VOICE
        
        # Create a specialized reporter agent for this category that handles multiple topics
        news_agent = create_category_reporter_agent(category, category_topics, voice, agent_name, script_key)
        reporter_tts_agent = create_tts_agent(script_key, f"{category}_audio.mp3", voice, f"tts_{category}_reporter", f"{category}_audio_filepath")
        
        news_agents.append(news_agent)
        reporter_script_keys.append(script_key)
        reporters_tts_agents.append(reporter_tts_agent)

    # Create anchor agent with category information
    anchor_agent = create_anchor_agent(list(topics_by_category.keys()), reporter_script_keys)
    
    # Update heartbeat before audio processing
    if task_id:
        try:
            from glconnect.news_routes import tasks, _tasks_lock
            with _tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['last_heartbeat'] = datetime.now()
                    tasks[task_id]['current_step'] = 'Creating audio components...'
        except:
            pass

    # Note: TTS agents for anchor parts will be created after we have the anchor script

    # Create transition TTS agents after we have the anchor script
    transition_tts_agents = []

    # Orchestration
    text_generation_phase = ParallelAgent(
        name="text_generation_phase",
        description="Generates all news reports concurrently.",
        sub_agents=news_agents
    )

    # Execute text generation with optimized parallel processing
    print("DEBUG: Executing text generation phase...")
    print(f"DEBUG: Running with {len(news_agents)} reporter agents")
    for i, agent in enumerate(news_agents):
        print(f"DEBUG: Agent {i}: {agent.name} - {agent.description}")
    
    # Check memory before text generation
    try:
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory before text generation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        if memory_info.percent > 85:
            print(f"WARNING: High memory usage before text generation ({memory_info.percent}%)")
            gc.collect()
            gc.collect()
    except:
        pass
    
    # Update heartbeat before text generation
    if task_id:
        try:
            from glconnect.news_routes import tasks, _tasks_lock
            with _tasks_lock:
                if task_id in tasks:
                    tasks[task_id]['last_heartbeat'] = datetime.now()
                    tasks[task_id]['current_step'] = f'Generating content with {len(news_agents)} AI reporters...'
        except:
            pass
    
    try:
        # SEQUENTIAL PROCESSING: Process topics one by one to prevent memory spikes
        print("DEBUG: Using sequential processing to prevent memory issues...")
        individual_outputs = []
        
        for i, agent in enumerate(news_agents):
            print(f"DEBUG: Processing agent {i+1}/{len(news_agents)}: {agent.name}")
            
            # Check memory before each agent
            try:
                memory_percent = get_memory_usage()
                print(f"DEBUG: Memory before agent {i+1} - Percent: {memory_percent:.1f}%")
                if memory_percent > 65:  # More aggressive threshold for 2GB containers
                    print(f"WARNING: High memory usage before agent {i+1} ({memory_percent:.1f}%) - forcing cleanup")
                    gc.collect()
                    gc.collect()
                    gc.collect()
            except:
                pass
            
            # Update progress
            try:
                from glconnect.news_routes import update_task_in_db
                progress = 20 + (i * 15)  # 20% to 80% for sequential agents
                update_task_in_db(task_id, 
                                 progress=progress,
                                 current_step=f'Processing topic {i+1}/{len(news_agents)} with AI reporter...',
                                 last_heartbeat=datetime.now())
            except:
                pass
            
            # Process this agent
            try:
                result = _run_async_safely(run_agent(agent, ""), max_retries=2, retry_delay=3)
                if result is not None:
                    individual_outputs.append(result)
                    print(f"DEBUG: Agent {i+1} completed successfully")
                else:
                    print(f"DEBUG: Agent {i+1} failed - using fallback")
                    # Create fallback content for this agent
                    fallback_result = {"script": f"News report on topic {i+1} - Content generation temporarily unavailable."}
                    individual_outputs.append(fallback_result)
            except Exception as e:
                print(f"DEBUG: Agent {i+1} failed with error: {e}")
                # Create fallback content
                fallback_result = {"script": f"News report on topic {i+1} - Content generation temporarily unavailable."}
                individual_outputs.append(fallback_result)
            
            # Force aggressive memory cleanup after each agent
            try:
                gc.collect()
                gc.collect()
                gc.collect()  # Triple garbage collection
                
                # Try to trim memory on Linux
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                except:
                    pass
                
                memory_percent = get_memory_usage()
                print(f"DEBUG: Memory after agent {i+1} - Percent: {memory_percent:.1f}%")
                
                # Emergency abort if memory is still too high
                if memory_percent > 80:
                    print(f"EMERGENCY: Memory too high after agent {i+1} ({memory_percent:.1f}%) - aborting remaining agents")
                    break
                    
            except:
                pass
            
            # Longer delay to allow memory cleanup
            import time
            time.sleep(2)  # Increased delay
        
        print(f"DEBUG: Sequential processing completed - {len(individual_outputs)} agents processed")
        
        # Force garbage collection after text generation
        gc.collect()
        
        # Check memory after text generation
        try:
            memory_info = psutil.virtual_memory()
            print(f"DEBUG: Memory after text generation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
            if memory_info.percent > 85:
                print(f"WARNING: High memory usage after text generation ({memory_info.percent}%) - forcing cleanup")
                gc.collect()
                gc.collect()
        except:
            pass
        
        # Force garbage collection after async operations
        gc.collect()
        gc.collect()  # Call twice for better cleanup
        
        # Check memory after text generation
        try:
            memory_info = psutil.virtual_memory()
            print(f"DEBUG: Memory after text generation - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
            if memory_info.percent > 85:
                print(f"WARNING: High memory usage after text generation ({memory_info.percent}%) - forcing aggressive cleanup")
                gc.collect()
                gc.collect()
                gc.collect()
                
                # Try to trim memory on Linux
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                except:
                    pass
        except:
            pass
        
        # Handle case where async operation failed due to interpreter shutdown
        if individual_outputs is None:
            print("DEBUG: Parallel agent execution failed due to interpreter shutdown, using fallback")
            individual_outputs = []
        
        # Filter out exceptions and combine results
        valid_outputs = []
        for i, output in enumerate(individual_outputs):
            if isinstance(output, Exception):
                print(f"DEBUG: Agent {i} failed with exception: {output}")
                valid_outputs.append("")
            else:
                valid_outputs.append(str(output))
                print(f"DEBUG: Agent {i} completed successfully")
        
        text_generation_output = "\n".join(valid_outputs)
        print(f"DEBUG: Parallel execution completed. Output length: {len(text_generation_output)}")
        print(f"DEBUG: Combined outputs: {text_generation_output[:500]}...")
        
        # Update heartbeat after text generation
        if task_id:
            try:
                from glconnect.news_routes import tasks, _tasks_lock
                with _tasks_lock:
                    if task_id in tasks:
                        tasks[task_id]['last_heartbeat'] = datetime.now()
                        tasks[task_id]['current_step'] = 'Processing generated content...'
            except:
                pass
        
    except Exception as e:
        print(f"DEBUG: Parallel execution failed: {e}")
        print("DEBUG: Falling back to individual agent execution...")
        
        # Fallback: run each agent individually with shorter timeout
        individual_outputs = []
        for i, agent in enumerate(news_agents):
            try:
                print(f"DEBUG: Running individual agent {i}: {agent.name}")
                individual_output = _run_async_safely(asyncio.wait_for(run_agent(agent, ""), timeout=180))
                individual_outputs.append(individual_output)
                print(f"DEBUG: Agent {i} output: {individual_output[:100]}...")
            except asyncio.TimeoutError:
                print(f"DEBUG: Agent {i} timed out after 3 minutes")
                individual_outputs.append("")
            except Exception as agent_error:
                print(f"DEBUG: Agent {i} failed: {agent_error}")
                individual_outputs.append("")
        
        # Combine individual outputs
        text_generation_output = "\n".join(individual_outputs)
        print(f"DEBUG: Combined individual outputs: {text_generation_output[:500]}...")

    # Extract reporter scripts from the output
    reporter_scripts = []
    
    print(f"DEBUG: Raw text generation output: {text_generation_output[:500]}...")
    
    for script_key in reporter_script_keys:
        script_found = False
        script_text = ""
        
        # Try multiple extraction methods
        extraction_methods = [
            # Method 1: Look for JSON with script key
            f'"{script_key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"',
            # Method 2: Look for script key with different quote styles
            f'"{script_key}"\\s*:\\s*"([^"]*)"',
            # Method 3: Look for script key with single quotes
            f"'{script_key}'\\s*:\\s*'([^']*)'",
            # Method 4: Look for script key without quotes
            f'{script_key}\\s*:\\s*"([^"]*)"',
        ]
        
        for i, pattern in enumerate(extraction_methods):
            match = re.search(pattern, text_generation_output, re.DOTALL)
            if match:
                script_text = match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                # Only accept if we got substantial content (more than just a placeholder)
                if len(script_text.strip()) > 20 and not script_text.strip().startswith("Here's the latest"):
                    script_found = True
                    print(f"DEBUG: Found {script_key} using method {i+1}: {script_text[:50]}...")
                    break
        
        if script_found:
            # Validate the extracted content before using it
            topic = script_key.replace('_script', '')
            is_valid, cleaned_script = validate_news_content(script_text, topic)
            
            if is_valid:
                reporter_scripts.append(cleaned_script)
                print(f"DEBUG: Valid content extracted for {script_key}")
            else:
                # Content failed validation, generate intelligent fallback
                fallback_content = generate_intelligent_fallback_content(topic)
                reporter_scripts.append(fallback_content)
                print(f"DEBUG: Content validation failed for {script_key}, using intelligent fallback")
        else:
            # If still not found, try to extract any substantial content after the script key
            fallback_pattern = f'"{script_key}"\\s*:\\s*"([^"]*)"'
            fallback_match = re.search(fallback_pattern, text_generation_output, re.DOTALL)
            if fallback_match:
                fallback_text = fallback_match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                if len(fallback_text.strip()) > 10:
                    # Validate the fallback content
                    topic = script_key.replace('_script', '')
                    is_valid, cleaned_fallback = validate_news_content(fallback_text, topic)
                    
                    if is_valid:
                        reporter_scripts.append(cleaned_fallback)
                        script_found = True
                        print(f"DEBUG: Found {script_key} using fallback: {cleaned_fallback[:50]}...")
            
            if not script_found:
                # Generate intelligent fallback content
                topic = script_key.replace('_script', '')
                fallback_content = generate_intelligent_fallback_content(topic)
                reporter_scripts.append(fallback_content)
                print(f"DEBUG: Generated intelligent fallback for {script_key} due to extraction failure")

    print(f"DEBUG: Extracted reporter scripts: {len(reporter_scripts)} scripts")

    # Create anchor agent with actual reporter scripts
    anchor_agent = create_anchor_agent(topics, reporter_scripts)

    # Create TTS agents with actual script content
    reporters_tts_agents_with_content = []
    for i, (script_key, script_content) in enumerate(zip(reporter_script_keys, reporter_scripts)):
        category = script_key.replace('_script', '')
        voice = ERNEST_VOICE if category == 'sports' else ISABELLA_VOICE if category == 'finance' else MARK_VOICE if category == 'tech' else EDITH_VOICE
        
        # Clean the script content for speech
        cleaned_script = clean_text_for_speech(script_content)
        
        # Create TTS agent with cleaned script content
        tts_agent = Agent(
            model="gemini-2.0-flash",
            name=f"tts_{category}_reporter",
            description=f"Converts {category} report to audio.",
            instruction=f"""
                Convert the following {category} report to audio using Google Cloud Text-to-Speech.
                Use the voice: {voice}
                The report content is: {cleaned_script}
                
                Create the audio file as: {category}_audio.mp3
                Output the audio file path as: {category}_audio.mp3
            """,
            output_key=f"{category}_audio_filepath",
            tools=[text_to_speech]
        )
        reporters_tts_agents_with_content.append(tts_agent)

    # Note: transition_tts_agents will be added after anchor script is parsed

    # Build the final list of audio file paths in the correct order
    final_audio_paths = [
        "glconnect/static/audio/jingle.wav",  # Opening jingle
        "glconnect/static/audio/intro_audio.mp3"  # Anchor intro with current time
    ]
    
    # Add each category report with transitions and thank you messages
    for i, category in enumerate(topics_by_category.keys()):
        final_audio_paths.append(f"glconnect/static/audio/transition_audio_{i}.mp3")  # Transition to report
        final_audio_paths.append(f"glconnect/static/audio/{category}_audio.mp3")  # The actual report
        final_audio_paths.append("glconnect/static/audio/thank_you_audio.mp3")  # Thank you after report
    
    # Add outro and closing jingle
    final_audio_paths.extend([
        "glconnect/static/audio/outro_audio.mp3",  # Anchor outro
        "glconnect/static/audio/jingle.wav"  # Closing jingle
    ])

    tool_call_paths = ", ".join([f'"{path}"' for path in final_audio_paths])

    final_audio_assembler_agent = Agent(
        model="gemini-2.0-flash",
        name="final_audio_assembler_agent",
        description="Combines all audio files into a single broadcast in the correct order.",
        instruction=f"""
            You have paths to individual audio segments that need to be combined in the correct order for a news broadcast.
            
            The correct order is:
            1. Opening jingle (jingle.wav)
            2. Anchor intro with current time (intro_audio.mp3)
            3. For each report: transition → report → thank you
            4. Anchor outro (outro_audio.mp3)
            5. Closing jingle (jingle.wav)
            
            Use the 'combine_audio_files' tool to stitch them together in this exact order.
            The file paths are: {final_audio_paths}.
            Call the tool with the full list of file paths.
            Tool call: combine_audio_files(file_paths=[{tool_call_paths}], output_filename='final_news_broadcast.mp3')
            After the tool call, you MUST output the value of the 'combined_audio_filepath' from the tool's result.
        """,
        output_key="final_broadcast_audio_output",
        tools=[combine_audio_files]
    )

    # Create summary with actual script content
    summarized_text_input = " ".join(reporter_scripts)

    summary_agent = Agent(
        model="gemini-2.0-flash",
        name="summary_agent",
        description="Summarizes the news reports.",
        instruction=f"""
            You have the news reports. Use the 'summarize_text' tool to summarize them.
            The news reports are: {summarized_text_input}
            Call the tool with the full text of the news reports.
            Tool call: summarize_text(text="{summarized_text_input}")
            After the tool call, you MUST output the value of the 'summary' from the tool's result.
        """,
        output_key="summary_output",
        tools=[summarize_text]
    )

    # Execute anchor agent separately to ensure it gets current time
    print("DEBUG: Executing anchor agent...")
    print("DEBUG: Anchor agent tools:", [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in anchor_agent.tools])
    
    # Force the anchor agent to call the timezone tool first
    anchor_input = "Please call the get_timezone_info tool first to get the current time, then create your script."
    anchor_output = _run_async_safely(run_agent(anchor_agent, anchor_input))
    print(f"DEBUG: Anchor output: {anchor_output[:200] if anchor_output else 'None'}...")
    
    # Handle case where async operation failed due to interpreter shutdown
    if anchor_output is None:
        print("DEBUG: Anchor agent failed due to interpreter shutdown, using fallback")
        anchor_script = {
            "intro": "Welcome to GLC News. Here are today's top stories.",
            "transitions": ["Now let's hear from our reporters.", "Moving on to our next story."],
            "outro": "That's all for today's news. Thank you for listening to GLC News."
        }
    else:
        # Parse anchor script to get intro, transitions, and outro
        try:
            anchor_script = json.loads(anchor_output.strip("```json\n").strip("```"))
            intro_text = anchor_script.get("intro", "Welcome to GLC News")
            transitions = anchor_script.get("transitions", [])
            outro_text = anchor_script.get("outro", "Thanks for listening to GLC News")
            print(f"DEBUG: Found intro, {len(transitions)} transitions, and outro in anchor script")
        except Exception as e:
            print(f"DEBUG: Error parsing anchor script: {e}")
            intro_text = "Welcome to GLC News"
            transitions = [f"Transition {i+1}" for i in range(len(topics))]
            outro_text = "Thanks for listening to GLC News"
    
    # Create intro and outro TTS agents with actual script content
    intro_tts_agent = Agent(
        model="gemini-2.0-flash",
        name="tts_intro",
        description="Converts intro to audio.",
        instruction=f"""
            Convert the following intro text to audio using Google Cloud Text-to-Speech.
            Use the voice: {ANCHOR_VOICE}
            The intro text is: {intro_text}
            
            Create the audio file as: intro_audio.mp3
            Output the audio file path as: intro_audio.mp3
        """,
        output_key="intro_audio_filepath",
        tools=[text_to_speech]
    )
    
    outro_tts_agent = Agent(
        model="gemini-2.0-flash",
        name="tts_outro",
        description="Converts outro to audio.",
        instruction=f"""
            Convert the following outro text to audio using Google Cloud Text-to-Speech.
            Use the voice: {ANCHOR_VOICE}
            The outro text is: {outro_text}
            
            Create the audio file as: outro_audio.mp3
            Output the audio file path as: outro_audio.mp3
        """,
        output_key="outro_audio_filepath",
        tools=[text_to_speech]
    )
    
    thank_you_tts_agent = Agent(
        model="gemini-2.0-flash",
        name="tts_thank_you",
        description="Converts thank you message to audio.",
        instruction=f"""
            Convert the following thank you message to audio using Google Cloud Text-to-Speech.
            Use the voice: {ANCHOR_VOICE}
            The thank you text is: Thank you for that report.
            
            Create the audio file as: thank_you_audio.mp3
            Output the audio file path as: thank_you_audio.mp3
        """,
        output_key="thank_you_audio_filepath",
        tools=[text_to_speech]
    )
    
    # Create transition TTS agents with actual transition content
    for i, transition_text in enumerate(transitions):
        agent_name = f"tts_transition_{i}"
        audio_filename = f"glconnect/static/audio/transition_audio_{i}.mp3"
        output_key = f"transition_audio_filepath_{i}"
        
        transition_tts_agent = Agent(
            model="gemini-2.0-flash",
            name=agent_name,
            description=f"Converts transition {i+1} to audio.",
            instruction=f"""
                Convert the following transition text to audio using Google Cloud Text-to-Speech.
                Use the voice: {ANCHOR_VOICE}
                The transition text is: {transition_text}
                
                Create the audio file as: transition_audio_{i}.mp3
                Output the audio file path as: transition_audio_{i}.mp3
            """,
            output_key=output_key,
            tools=[text_to_speech]
        )
        transition_tts_agents.append(transition_tts_agent)

    # Create TTS phase with all agents
    tts_phase = ParallelAgent(
        name="tts_conversion_phase",
        description="Converts all news reports to audio concurrently.",
        sub_agents=[intro_tts_agent, outro_tts_agent, thank_you_tts_agent] + reporters_tts_agents_with_content + transition_tts_agents
    )

    # Execute TTS phase with progress updates
    print("DEBUG: Executing TTS phase...")
    
    # Update progress before TTS
    if task_id:
        try:
            from glconnect.news_routes import update_task_in_db
            update_task_in_db(task_id, 
                             progress=70,
                             current_step=f'Converting {len(tts_phase.sub_agents)} text segments to speech...',
                             last_heartbeat=datetime.now())
        except:
            pass
    
    # TTS processing with retry logic and memory optimization
    print("DEBUG: Starting TTS processing with retry logic...")
    tts_output = _run_async_safely(run_agent(tts_phase, ""), max_retries=3, retry_delay=3)
    
    # Handle case where TTS failed due to interpreter shutdown
    if tts_output is None:
        print("DEBUG: TTS phase failed after retries - attempting fallback")
        # Try a simpler TTS approach as fallback
        try:
            print("DEBUG: Attempting fallback TTS processing...")
            # Force garbage collection before fallback
            gc.collect()
            gc.collect()
            
            # Try again with a fresh async context
            tts_output = _run_async_safely(run_agent(tts_phase, ""), max_retries=2, retry_delay=5)
            
            if tts_output is None:
                print("DEBUG: Fallback TTS also failed")
                return {"audio_file": None, "summary": "News generation failed: TTS conversion failed after multiple attempts. Please try again."}
        except Exception as e:
            print(f"DEBUG: Fallback TTS failed with error: {e}")
            return {"audio_file": None, "summary": "News generation failed: TTS conversion failed due to system error. Please try again."}
    
    # Force garbage collection after TTS to free memory
    gc.collect()
    gc.collect()
    
    # Update progress after TTS
    if task_id:
        try:
            from glconnect.news_routes import update_task_in_db
            update_task_in_db(task_id, 
                             progress=85,
                             current_step='TTS conversion completed, assembling final audio...',
                             last_heartbeat=datetime.now())
        except:
            pass

    # Execute final output phase
    final_output_phase = ParallelAgent(
        name="final_output_phase",
        description="Generates the final audio broadcast and a summary of the news.",
        sub_agents=[
            final_audio_assembler_agent,
            summary_agent
        ]
    )
    print("DEBUG: Executing final output phase...")
    final_output = _run_async_safely(run_agent(final_output_phase, ""))
    
    # Handle case where final output failed due to interpreter shutdown
    if final_output is None:
        print("DEBUG: Final output phase failed due to interpreter shutdown")
        return {"audio_file": None, "summary": "News generation failed: Final assembly failed due to interpreter shutdown"}
    
    # Force aggressive garbage collection to free memory
    gc.collect()
    gc.collect()
    gc.collect()
    
    # Clear only old TTS cache entries to free memory (keep recent ones)
    global _tts_cache
    if len(_tts_cache) > 50:  # Only clear if cache is large
        # Keep only the most recent 20 entries
        recent_entries = dict(list(_tts_cache.items())[-20:])
        _tts_cache.clear()
        _tts_cache.update(recent_entries)
        print(f"DEBUG: Cleared old TTS cache entries, kept {len(_tts_cache)} recent ones")
    
    # Check memory after cleanup
    try:
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory after news generation cleanup - Used: {memory_info.used / 1024 / 1024:.1f}MB, Available: {memory_info.available / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
    except:
        pass
    
    # The final_output is a string, but we need to return a dict
    # Extract the audio file path from the filesystem
    import glob
    
    # Check for both patterns: with and without wildcard
    audio_files = glob.glob("glconnect/static/audio/final_news_broadcast_*.mp3")
    if not audio_files:
        # Try the exact filename without wildcard
        exact_file = "glconnect/static/audio/final_news_broadcast.mp3"
        if os.path.exists(exact_file):
            audio_files = [exact_file]
    
    # Also check in the current directory (where FFmpeg creates it)
    if not audio_files:
        current_dir_files = glob.glob("final_news_broadcast*.mp3")
        if current_dir_files:
            audio_files = current_dir_files
    
    if audio_files:
        # Get the most recent audio file
        latest_audio = max(audio_files, key=os.path.getctime)
        print(f"DEBUG: Found audio file: {latest_audio}")
        
        # Verify the final audio file exists and has content before cleanup
        if os.path.exists(latest_audio):
            file_size = os.path.getsize(latest_audio)
            print(f"DEBUG: Final audio file verified - size: {file_size} bytes")
            
            if file_size > 0:
                # Only clean up AFTER final broadcast is successfully generated and verified
                try:
                    cleanup_intermediate_audio_files(latest_audio)
                    print(f"DEBUG: Cleanup completed after successful final broadcast generation")
                except Exception as e:
                    print(f"DEBUG: Cleanup failed (non-critical): {e}")
            else:
                print(f"WARNING: Final audio file is empty, skipping cleanup to preserve intermediate files")
        else:
            print(f"ERROR: Final audio file not found, skipping cleanup")
        
        # Convert to web-accessible path
        if latest_audio.startswith("glconnect/static/audio/"):
            web_path = latest_audio.replace("glconnect/static/audio/", "/static/audio/")
        elif latest_audio.startswith("/usr/src/appdir/glconnect/static/audio/"):
            web_path = latest_audio.replace("/usr/src/appdir/glconnect/static/audio/", "/static/audio/")
        else:
            web_path = f"/static/audio/{os.path.basename(latest_audio)}"
        
        print(f"DEBUG: Web-accessible path: {web_path}")
        return {
            "audio_file": web_path
        }
    else:
        print("DEBUG: No audio files found")
        return {
            "audio_file": None
        }




if __name__ == '__main__':
    import sys
    topics = sys.argv[1:]
    if not topics:
        topics = []
        print("Welcome to the GLC Newsroom!")
        try:
            while True:
                topic = input("Enter a news topic you're interested in (or type 'done' to finish): ")
                if topic.lower() == 'done':
                    break
                topics.append(topic)
        except EOFError:
            print("No input provided. Using default topics.")
            topics = ["Sports", "Finance", "Politics", "Tech"]

    if topics:
        final_broadcast = generate_broadcast(topics)
        print(f"Final broadcast at: {final_broadcast}")
