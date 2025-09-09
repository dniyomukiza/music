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

# Load Google API key from glconfig.json
with open('/etc/glconfig.json') as json_file:
    config = json.load(json_file)

# Get Google API key from glconfig.json
google_api_key = config.get("GOOGLE_API_KEY")
if not google_api_key:
    print("Error: GOOGLE_API_KEY not found in glconfig.json")
    exit(1)

# Get TTS credentials path from glconfig.json
tts_credentials_path = config.get("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS from config: {config.get('GOOGLE_APPLICATION_CREDENTIALS')}")
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
    Gets the current time in Los Angeles, New York City, Brussels, and Central Time.
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
        brussels_tz = pytz.timezone('Europe/Brussels')
        central_tz = pytz.timezone('America/Chicago')
        
        # Get current UTC time - ensure we get the current time
        utc_now = datetime.now(pytz.UTC)
        print(f"DEBUG: Getting timezone info at UTC time: {utc_now.strftime('%H:%M:%S')}")
        
        # Convert to each timezone
        la_time = utc_now.astimezone(la_tz)
        ny_time = utc_now.astimezone(ny_tz)
        brussels_time = utc_now.astimezone(brussels_tz)
        central_time = utc_now.astimezone(central_tz)
        
        print(f"DEBUG: LA time: {la_time.strftime('%H:%M')} -> {la_time.strftime('%I:%M %p')}")
        print(f"DEBUG: NY time: {ny_time.strftime('%H:%M')} -> {ny_time.strftime('%I:%M %p')}")
        print(f"DEBUG: Brussels time: {brussels_time.strftime('%H:%M')} -> {brussels_time.strftime('%I:%M %p')}")
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
        
        la_formatted = format_time_for_anchor(la_time)
        ny_formatted = format_time_for_anchor(ny_time)
        brussels_formatted = format_time_for_anchor(brussels_time)
        central_formatted = format_time_for_anchor(central_time)
        
        timezone_info = f"It's {la_formatted} in Los Angeles, it's {ny_formatted} in New York City, it's {brussels_formatted} in Brussels and it's {central_formatted} central time"
        
        print(f"DEBUG: Final timezone info: {timezone_info}")
        print("=" * 50)
        print("DEBUG: TIMEZONE TOOL COMPLETED!")
        print("=" * 50)
        
        return {"timezone_info": timezone_info}
    except Exception as e:
        print(f"Error getting timezone info: {e}")
        return {"timezone_info": "Welcome to GLC News"}


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
    # Clean the text before processing
    clean_text = clean_text_for_speech(text)
    
    # Load credentials from file and pass to client
    from google.oauth2 import service_account
    
    # Get TTS credentials path from glconfig.json
    tts_credentials_path = config.get("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
    print(f"DEBUG: Loading TTS credentials from: {tts_credentials_path}")
    print(f"DEBUG: Credentials file exists: {os.path.exists(tts_credentials_path)}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Environment: {config.get('FLASK_ENV', 'production')}")
    
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

def combine_audio_files(file_paths: list[str], output_filename: str = "final_news_broadcast.mp3") -> dict:
    """
    Combines multiple MP3 audio files into a single MP3 file in the given order,
    preceding and ending it with a 'jingle.wav' sound.
    Args:
        file_paths: A list of paths to the audio files in the desired order.
        output_filename: The name of the output combined audio file.
    Returns:
        A dictionary with 'combined_audio_filepath': The full path to the combined audio file.
    """
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
            - After getting the search results, synthesize the information into a professional news report.
            - You must end your news report with the following signature: 'I am {agent_name.replace("_", " ")}, for GLC News'.
            - Your final output must be ONLY the news report content, exactly as a reporter would deliver it.
            - You must output your news report in JSON format with the key '{output_key}'.
            - Example output format: {{"{output_key}": "Your news report content here..."}}
            - Do not introduce yourself beyond your signature within the report.
            - No titles nor subtitles are needed in your script.
            - Never ever include special character in your script such as asterisks or other symbols.
            - Do not ask any questions or engage in conversation. Proceed directly with the report after the search.
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
            - After getting the search results for all topics, synthesize the information into a single comprehensive news report.
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
            This tool will give you the current time in Los Angeles, New York City, Brussels, and Central Time.
            Use the EXACT time information returned by this tool - do not make up or guess times.

            Your output MUST be a JSON object with three keys: 'intro', 'transitions', and 'outro'.
            - 'intro': Start with the EXACT timezone information from the get_timezone_info tool, then introduce yourself as the anchor, and briefly introduce the main topics. Format: "It's [X:XX AM/PM] in Los Angeles, [X:XX AM/PM] in New York City, [X:XX AM/PM] in Brussels and [X:XX AM/PM] central time, I am your anchor today, in this edition we are covering..."
            - 'transitions': A list of strings, where each string is an introduction for a reporter. For example: ["First up, we have Ernest with the latest on sports.", "Next, Isabella brings us updates on finance."]
            - 'outro': A brief summary of the news covered, thanking the listeners. End with "Thanks for listening to GLC News."

            Example JSON output (use the ACTUAL current time from get_timezone_info tool):
            ```json
            {{
                "intro": "It's 6:20 PM in Los Angeles, 9:20 PM in New York City, 3:20 AM in Brussels and 8:20 PM central time, I am your anchor today, in this edition we are covering the latest in sports and finance.",
                "transitions": [
                    "First up, we have Ernest with the latest on sports.",
                    "Next, Isabella brings us updates on finance."
                ],
                "outro": "That's all for today. Thanks for listening to GLC News."
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

def generate_broadcast(topics: list[str]) -> dict:
    if not topics:
        print("No topics entered. Exiting.")
        return

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

    categorized_topics_json = asyncio.run(run_agent(categorization_agent, str(topics)))
    print(f"DEBUG: Raw categorization output: {categorized_topics_json}")
    
    # Clean up the JSON response
    categorized_topics_json = categorized_topics_json.strip()
    if categorized_topics_json.startswith('```json'):
        categorized_topics_json = categorized_topics_json[7:]  # Remove ```json
    if categorized_topics_json.endswith('```'):
        categorized_topics_json = categorized_topics_json[:-3]  # Remove ```
    categorized_topics_json = categorized_topics_json.strip()
    print(f"DEBUG: Cleaned categorization JSON: {categorized_topics_json}")
    
    categorized_topics = json.loads(categorized_topics_json)
    print(f"DEBUG: Parsed categories: {categorized_topics}")

    # Group topics by category
    topics_by_category = {}
    for topic, category in categorized_topics.items():
        if category not in topics_by_category:
            topics_by_category[category] = []
        topics_by_category[category].append(topic)
    
    print(f"DEBUG: Topics grouped by category: {topics_by_category}")

    # Create agents for each category (one reporter per category)
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

    # Note: TTS agents for anchor parts will be created after we have the anchor script

    # Create transition TTS agents after we have the anchor script
    transition_tts_agents = []

    # Orchestration
    text_generation_phase = ParallelAgent(
        name="text_generation_phase",
        description="Generates all news reports concurrently.",
        sub_agents=news_agents
    )

    # Execute text generation first to get reporter scripts
    print("DEBUG: Executing text generation phase...")
    text_generation_output = asyncio.run(run_agent(text_generation_phase, ""))
    print(f"DEBUG: Text generation output: {text_generation_output[:200]}...")

    # Extract reporter scripts from the output
    reporter_scripts = []
    
    # Look for JSON patterns in the output
    json_pattern = r'\{[^{}]*"[^"]*script[^"]*"[^{}]*\}'
    json_matches = re.findall(json_pattern, text_generation_output)
    
    print(f"DEBUG: Found {len(json_matches)} JSON matches in text generation output")
    
    for script_key in reporter_script_keys:
        script_found = False
        
        # First try to find in JSON matches
        for json_match in json_matches:
            if script_key in json_match:
                # Extract the value after the script key - improved regex to handle escaped quotes
                pattern = f'"{script_key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"'
                match = re.search(pattern, json_match)
                if match:
                    # Clean up the extracted text - remove any unwanted characters
                    script_text = match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                    # Apply comprehensive text cleaning for speech
                    script_text = clean_text_for_speech(script_text)
                    reporter_scripts.append(script_text)
                    script_found = True
                    print(f"DEBUG: Found {script_key} in JSON: {script_text[:50]}...")
                    break
        
        # If not found in JSON, try to find the script key in the raw output
        if not script_found:
            pattern = f'"{script_key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"'
            match = re.search(pattern, text_generation_output)
            if match:
                # Clean up the extracted text - remove any unwanted characters
                script_text = match.group(1).replace('\\"', '"').replace('\\n', ' ').replace('\\t', ' ')
                # Apply comprehensive text cleaning for speech
                script_text = clean_text_for_speech(script_text)
                reporter_scripts.append(script_text)
                script_found = True
                print(f"DEBUG: Found {script_key} in raw output: {script_text[:50]}...")
        
        if not script_found:
            # Create a placeholder script
            topic = script_key.replace('_script', '')
            reporter_scripts.append(f"Here's the latest report on {topic}.")
            print(f"DEBUG: Created placeholder for {script_key}")

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
    anchor_output = asyncio.run(run_agent(anchor_agent, anchor_input))
    print(f"DEBUG: Anchor output: {anchor_output[:200]}...")
    
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

    # Execute TTS phase
    print("DEBUG: Executing TTS phase...")
    tts_output = asyncio.run(run_agent(tts_phase, ""))

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
    final_output = asyncio.run(run_agent(final_output_phase, ""))
    return final_output




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
