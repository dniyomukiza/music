import os
import asyncio
import json
import re
import time
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

# Load Google API key from environment variables (no exit at import - allows app to start)
def _resolve_google_api_key() -> str:
    return (
        (os.getenv("GOOGLE_API_KEY") or "").strip()
        or (os.getenv("GEMINI_API_KEY") or "").strip()
    )


def _ensure_genai_configured() -> str:
    """Resolve API key at call time so glconfig/env loaded after import still works."""
    global google_api_key
    key = _resolve_google_api_key()
    if not key:
        raise RuntimeError("GOOGLE_API_KEY and GEMINI_API_KEY are not set")
    if key != google_api_key:
        google_api_key = key
        genai.configure(api_key=key)
        os.environ["GOOGLE_API_KEY"] = key
    return key


google_api_key = _resolve_google_api_key()
if not google_api_key:
    print("WARNING: GOOGLE_API_KEY/GEMINI_API_KEY not set. News scripts will use fallback copy until configured.")

# Get TTS credentials path from environment variables
tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
print(f"DEBUG: GOOGLE_APPLICATION_CREDENTIALS from config: {tts_credentials_path}")
print(f"DEBUG: Using TTS credentials path: {tts_credentials_path}")

# Configure Google AI SDK only if key is present
import google.generativeai as genai
if google_api_key:
    genai.configure(api_key=google_api_key)
    os.environ['GOOGLE_API_KEY'] = google_api_key

NEWS_GEMINI_MODEL = (os.getenv("NEWS_GEMINI_MODEL") or "gemini-3.6-flash").strip()
NEWS_GEMINI_MODEL_FALLBACKS = [
    NEWS_GEMINI_MODEL,
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
]


def _gemini_model_candidates():
    seen = []
    for name in NEWS_GEMINI_MODEL_FALLBACKS:
        if name and name not in seen:
            seen.append(name)
    return seen


_last_gemini_meta = {}


def _classify_model_error(exc) -> str:
    text = str(exc or "")
    lower = text.lower()
    if "404" in text or "not found" in lower or "no longer available" in lower:
        return "model_unavailable"
    if "429" in text or "resource_exhausted" in lower or "quota" in lower:
        return "quota_exhausted"
    if "not set" in lower and ("google_api_key" in lower or "gemini_api_key" in lower or "api key" in lower):
        return "missing_api_key"
    if "403" in text or "permission" in lower or "api key" in lower:
        return "permission_denied"
    if "json" in lower and "decode" in lower:
        return "invalid_json"
    if "empty" in lower:
        return "empty_response"
    return type(exc).__name__ if exc is not None else "unknown"


def _clip_trace_text(value, limit=300):
    if value is None:
        return None
    text = str(value).replace("\n", " ").strip()
    if len(text) > limit:
        return text[:limit] + "..."
    return text


class NewsPipelineTrace:
    """Structured breadcrumb trail for one news broadcast run."""

    def __init__(self, topics, task_id=None):
        self.task_id = task_id
        self.topics = list(topics or [])
        self.started_at = datetime.utcnow().isoformat() + "Z"
        self.stages = []
        self.warnings = []
        self.used_fallback = False

    def stage(self, name, status="ok", warning=None, **details):
        event = {"stage": name, "status": status}
        for key, value in details.items():
            if value is not None:
                event[key] = value
        if warning:
            event["warning"] = warning
            self.warnings.append(warning)
        self.stages.append(event)
        if status in ("fallback", "partial_fallback"):
            self.used_fallback = True
        parts = [f"{key}={_clip_trace_text(value, 180)}" for key, value in event.items()]
        print("PIPELINE " + " | ".join(parts))
        return event

    def outcome(self, audio_ok):
        if not audio_ok:
            return "failed"
        if self.used_fallback:
            return "ok_with_fallback"
        return "ok"

    def to_dict(self, audio_ok=None):
        payload = {
            "task_id": self.task_id,
            "topics": self.topics,
            "started_at": self.started_at,
            "used_fallback": self.used_fallback,
            "warnings": list(self.warnings),
            "stages": list(self.stages),
        }
        if audio_ok is not None:
            payload["outcome"] = self.outcome(audio_ok)
        return payload


class NewsScriptUnavailable(RuntimeError):
    """Reporter scripts could not be written. Do not assemble audio or video."""

    def __init__(self, reason_code: str, message: str):
        super().__init__(message)
        self.reason_code = reason_code or "script_unavailable"


PLACEHOLDER_SCRIPT_MARK = "checking official statements and independent reporting"

_FATAL_SCRIPT_ERRORS = {
    "quota_exhausted",
    "model_unavailable",
    "permission_denied",
    "missing_api_key",
}

_SCRIPT_ABORT_MESSAGES = {
    "quota_exhausted": (
        "Gemini quota was exceeded, so reporter scripts could not be written. "
        "No audio or video bulletin was generated. Check usage at ai.dev/rate-limit, "
        "wait for the daily reset, or enable billing, then generate news again."
    ),
    "model_unavailable": (
        "The news script model is unavailable. Set NEWS_GEMINI_MODEL to a live Gemini model "
        "and generate news again. No bulletin was generated."
    ),
    "permission_denied": (
        "Gemini rejected the API key. Check GOOGLE_API_KEY or GEMINI_API_KEY, then generate news again. "
        "No bulletin was generated."
    ),
    "missing_api_key": (
        "Gemini API key is not set. Add GOOGLE_API_KEY or GEMINI_API_KEY, then generate news again. "
        "No bulletin was generated."
    ),
    "invalid_json": (
        "The news model did not return usable reporter scripts. No bulletin was generated. Please try again."
    ),
    "empty_response": (
        "The news model returned empty reporter scripts. No bulletin was generated. Please try again."
    ),
}


def script_abort_message(reason_code: str, missing_count: int = 0, topic_count: int = 0) -> str:
    message = _SCRIPT_ABORT_MESSAGES.get(reason_code) or (
        "Reporter scripts could not be written because of an API or model error. "
        "No audio or video bulletin was generated. Please try again."
    )
    if missing_count and topic_count:
        return f"{message} Missing scripts: {missing_count}/{topic_count}."
    return message


def is_placeholder_reporter_script(script: str) -> bool:
    text = (script or "").strip().lower()
    if not text:
        return True
    return PLACEHOLDER_SCRIPT_MARK in text


def reporter_scripts_block_reason(scripts) -> str | None:
    """User-facing error if saved scripts are missing or placeholder copy."""
    reporters = (scripts or {}).get("reporters") if isinstance(scripts, dict) else None
    if not reporters:
        return "No reporter scripts were saved. Generate news again after Gemini is available."
    placeholders = [
        row for row in reporters
        if isinstance(row, dict) and is_placeholder_reporter_script(row.get("script") or "")
    ]
    if placeholders:
        names = ", ".join((row.get("name") or row.get("topic") or "reporter") for row in placeholders)
        return (
            "This broadcast only has placeholder reporter copy from an API, quota, or model failure. "
            f"Affected: {names}. Generate news again after Gemini is available. Video was not started."
        )
    return None


def _result_with_pipeline(result: dict, trace: NewsPipelineTrace) -> dict:
    audio_ok = bool(result.get("audio_file")) and "error" not in result
    pipeline = trace.to_dict(audio_ok=audio_ok)
    result = dict(result)
    result["pipeline"] = pipeline
    result["used_fallback"] = pipeline["used_fallback"]
    print("PIPELINE_SUMMARY " + json.dumps(pipeline, default=str))
    if pipeline.get("warnings"):
        print("PIPELINE_WARNINGS " + " || ".join(pipeline["warnings"]))
    return result


def _spoken_topic_rundown(topics: list) -> str:
    names = [str(topic or "").strip() for topic in (topics or []) if str(topic or "").strip()]
    if not names:
        return "today's top stories"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def _anchor_intro_text(timezone_info: str, topics: list) -> str:
    """Time check, GLC News welcome, then a rundown of this edition's topics."""
    clock = (timezone_info or "").strip().rstrip(".")
    rundown = _spoken_topic_rundown(topics)
    if clock.lower() == "welcome to glc news":
        return f"Welcome to GLC News. In this edition we are covering {rundown}."
    welcome = "" if "glc news" in clock.lower() else " Welcome to GLC News."
    return f"{clock}.{welcome} In this edition we are covering {rundown}."


def _anchor_handoff_text(assignment: dict, previous: dict = None) -> str:
    name = (assignment.get("name") or "our reporter").strip()
    topic = (assignment.get("topic") or "the next story").strip()
    if not previous:
        return f"Now let's go to {name}, who will tell us about {topic}."
    prev_name = (previous.get("name") or "our reporter").strip()
    if prev_name.lower() == name.lower():
        return f"Thanks {prev_name} for that report. {name} also has more, and will tell us about {topic}."
    return (
        f"Thanks {prev_name} for that report. Now let's switch to {name}, "
        f"who will tell us about {topic}."
    )


def _anchor_outro_text(assignments: list) -> str:
    last_name = ""
    if assignments:
        last_name = (assignments[-1].get("name") or "").strip()
    thanks = f"Thanks {last_name} for that report. " if last_name else ""
    return f"{thanks}That's all for this GLC News bulletin. Thank you for listening."


def _quota_retry_seconds(exc) -> float | None:
    text = str(exc or "")
    match = re.search(r"retry in ([0-9.]+)s", text, re.I)
    if match:
        return min(float(match.group(1)) + 1.0, 60.0)
    if "429" in text or "resource_exhausted" in text.lower():
        return 35.0
    return None


def _gemini_generate_text(prompt: str, generation_config=None) -> str:
    """Try current then fallback Gemini models. Raises the last error if all fail."""
    import google.generativeai as genai
    global _last_gemini_meta
    _ensure_genai_configured()
    attempts = []
    last_error = None
    for model_name in _gemini_model_candidates():
        kwargs = {}
        if generation_config is not None:
            kwargs["generation_config"] = generation_config
        model = genai.GenerativeModel(model_name, **kwargs)
        for attempt in range(2):
            try:
                response = model.generate_content(prompt)
                text = (getattr(response, "text", None) or "").strip()
                if text:
                    attempts.append({"model": model_name, "ok": True, "chars": len(text)})
                    _last_gemini_meta = {"ok": True, "model": model_name, "attempts": attempts}
                    print(f"DEBUG: Gemini text OK model={model_name} chars={len(text)}")
                    return text
                last_error = RuntimeError(f"{model_name} returned empty text")
                attempts.append({
                    "model": model_name,
                    "ok": False,
                    "error": "empty_response",
                    "detail": f"{model_name} returned empty text",
                })
                print(f"DEBUG: Gemini text failed model={model_name}: empty text")
                break
            except Exception as exc:
                last_error = exc
                classified = _classify_model_error(exc)
                attempts.append({
                    "model": model_name,
                    "ok": False,
                    "error": classified,
                    "detail": _clip_trace_text(exc, 240),
                })
                print(f"DEBUG: Gemini text failed model={model_name}: {classified}: {exc}")
                if attempt == 0 and classified == "quota_exhausted":
                    delay = _quota_retry_seconds(exc)
                    if delay:
                        print(f"DEBUG: Retrying {model_name} after quota delay ({delay:.0f}s)")
                        time.sleep(delay)
                        continue
                break
    _last_gemini_meta = {
        "ok": False,
        "model": None,
        "attempts": attempts,
        "error": _classify_model_error(last_error),
        "detail": _clip_trace_text(last_error, 240),
    }
    raise last_error or RuntimeError("No Gemini model produced text")

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
_last_async_error = None
_tts_client = None
_tts_credentials_checked = False
_tts_backend = None  # "google" or "elevenlabs"
_ELEVENLABS_VOICE_MAP = {
    "en-US-Studio-O": "EXAVITQu4vr4xnSDxMaL",  # Sarah — studio anchor only
    "en-US-Neural2-D": "pNInz6obpgDQGcFmaJgB",  # Adam — Ernest
    "en-US-Neural2-C": "21m00Tcm4TlvDq8ikWAM",  # Rachel — Edith
    "en-US-Standard-F": "MF3mGyEYCl7XYWbV9V6O",  # Elli — Isabella
    "en-GB-Standard-B": "JBFqnCBsd6RMkjVDRZzb",  # George — Mark
    "en-US-Neural2-F": "AZnzlk1XvdvUeBnXmlld",  # Domi — Clara
    "en-US-Neural2-A": "TxGEqnHWrfWFTfGW9XjX",  # Josh — James
}
_ELEVENLABS_DEFAULT_VOICE = "TxGEqnHWrfWFTfGW9XjX"  # James — never reuse anchor Sarah


def _resolve_tts_credentials_path() -> str:
    """Resolve the Google Cloud TTS service-account file path."""
    raw = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json") or "tts.json"
    path = raw.strip().strip('"').strip("'")
    if os.path.isabs(path) and os.path.exists(path):
        return path
    if os.path.exists(path):
        return os.path.abspath(path)
    for candidate in (
        os.path.join(os.getcwd(), path),
        os.path.join(os.path.dirname(__file__), "..", path),
        os.path.abspath("tts.json"),
    ):
        if os.path.exists(candidate):
            return os.path.abspath(candidate)
    return os.path.abspath(path)


def _load_tts_credentials():
    """Load Google Cloud TTS credentials from file or inline JSON env var."""
    from google.oauth2 import service_account

    inline_json = os.getenv("GOOGLE_TTS_CREDENTIALS_JSON", "").strip()
    if inline_json:
        info = json.loads(inline_json)
        return service_account.Credentials.from_service_account_info(info)

    credentials_path = _resolve_tts_credentials_path()
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            "Google Cloud TTS credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS "
            f"to a valid service-account JSON file (looked for {credentials_path}) or set "
            "GOOGLE_TTS_CREDENTIALS_JSON with the JSON contents."
        )
    return service_account.Credentials.from_service_account_file(credentials_path)


def validate_tts_credentials():
    """Return an error message when TTS is not configured, otherwise None."""
    global _tts_credentials_checked, _tts_client, _tts_backend
    try:
        credentials = _load_tts_credentials()
        _tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
        _tts_backend = "google"
        _tts_credentials_checked = True
        print("DEBUG: Using Google Cloud TTS")
        return None
    except (FileNotFoundError, json.JSONDecodeError, Exception) as google_exc:
        eleven_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
        if eleven_key:
            _tts_backend = "elevenlabs"
            _tts_credentials_checked = True
            print(f"DEBUG: Google Cloud TTS unavailable ({google_exc}); using ElevenLabs fallback")
            return None
        if isinstance(google_exc, FileNotFoundError):
            return str(google_exc)
        if isinstance(google_exc, json.JSONDecodeError):
            return "GOOGLE_TTS_CREDENTIALS_JSON is set but contains invalid JSON."
        return f"TTS credentials could not be loaded: {google_exc}"


def _get_tts_client():
    global _tts_client, _tts_credentials_checked
    if _tts_backend is None:
        error = validate_tts_credentials()
        if error:
            raise RuntimeError(error)
    if _tts_backend != "google":
        raise RuntimeError("Google Cloud TTS client requested but ElevenLabs fallback is active")
    return _tts_client


def _elevenlabs_audio_bytes(text: str, voice_name: str) -> bytes:
    from elevenlabs.client import ElevenLabs

    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    client = ElevenLabs(api_key=api_key)
    voice_id = _ELEVENLABS_VOICE_MAP.get(voice_name, _ELEVENLABS_DEFAULT_VOICE)
    chunks = []
    max_chars = 2400
    remaining = text.strip()
    while remaining:
        piece = remaining[:max_chars]
        if len(remaining) > max_chars:
            split_at = max(piece.rfind(". "), piece.rfind("? "), piece.rfind("! "))
            if split_at > 400:
                piece = remaining[: split_at + 1]
        remaining = remaining[len(piece):].lstrip()
        audio = client.text_to_speech.convert(
            voice_id=voice_id,
            text=piece,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        if isinstance(audio, (bytes, bytearray)):
            chunks.append(bytes(audio))
        else:
            chunks.append(b"".join(audio))
    return b"".join(chunks)


def _run_direct_tts_phase(
    intro_text: str,
    outro_text: str,
    transitions: list[str],
    reporter_segments: list[tuple[str, str, str]],
    task_id=None,
) -> None:
    """Convert all broadcast scripts to audio without Gemini tool-calling."""
    total_segments = 2 + len(transitions) + len(reporter_segments)
    completed = 0

    def _convert(label: str, text: str, filename: str, voice: str) -> None:
        nonlocal completed
        if task_id:
            try:
                from glconnect.news_routes import update_task_in_db
                update_task_in_db(
                    task_id,
                    progress=min(70 + int((completed / max(total_segments, 1)) * 15), 84),
                    current_step=f"Converting {label} to speech ({completed + 1}/{total_segments})...",
                    last_heartbeat=datetime.now(),
                )
            except Exception:
                pass
        text_to_speech(text, filename, voice)
        completed += 1

    _convert("intro", intro_text, "intro_audio.mp3", ANCHOR_VOICE)
    _convert("outro", outro_text, "outro_audio.mp3", ANCHOR_VOICE)

    for index, transition_text in enumerate(transitions):
        _convert(
            f"transition {index + 1}",
            transition_text,
            f"transition_audio_{index}.mp3",
            ANCHOR_VOICE,
        )

    for segment_id, script_content, voice in reporter_segments:
        safe_voice = _sanitize_reporter_voice(voice)
        _convert(
            f"{segment_id} report",
            script_content,
            f"{segment_id}_audio.mp3",
            safe_voice,
        )


# --- Define the Text to Speech Tool (as a callable function) ---
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
    
    # Clean the text before processing. Keep enough context in logs to identify
    # the exact segment when ParallelAgent runs several TTS calls at once.
    clean_text = clean_text_for_speech(text)
    is_reporter_segment = (
        output_filename.startswith("report_") and output_filename.endswith("_audio.mp3")
    )
    if is_reporter_segment and _reporter_voice_collides_with_anchor(voice_name):
        print(
            f"WARNING: Blocked anchor voice on reporter segment {output_filename!r}; "
            f"using {JAMES_VOICE!r}"
        )
        voice_name = _sanitize_reporter_voice(voice_name)
    print(
        f"TTS_START segment={output_filename!r} voice={voice_name!r} "
        f"text_chars={len(clean_text)}"
    )
    
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
    
    if _tts_backend is None:
        error = validate_tts_credentials()
        if error:
            raise RuntimeError(error)

    try:
        print(
            f"DEBUG: TTS confirmed for {output_filename} "
            f"voice={voice_name} chars={len(clean_text)} backend={_tts_backend}"
        )

        if _tts_backend == "elevenlabs":
            audio_content = _elevenlabs_audio_bytes(clean_text, voice_name)
        else:
            client = _get_tts_client()
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
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice_params, audio_config=audio_config
            )
            audio_content = response.audio_content

        print(f"DEBUG: TTS response received, audio content length: {len(audio_content) if audio_content else 'None'}")
        
        if not audio_content:
            print(f"ERROR: TTS returned empty audio content for {output_filename}")
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
                bytes_written = out.write(audio_content)
                print(f"DEBUG: Bytes written to file: {bytes_written}")
                out.flush()  # Force flush to disk
                os.fsync(out.fileno())  # Force sync to filesystem
        except Exception as e:
            print(f"DEBUG: Error writing file: {e}")
            # Try alternative approach
            try:
                with open(full_path, "wb") as out:
                    out.write(audio_content)
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
            print(f"DEBUG: Response audio_content type: {type(audio_content)}")
            print(f"DEBUG: Response audio_content length: {len(audio_content) if audio_content else 'None'}")
            raise Exception(f"Audio file created but is empty (0 bytes) for {output_filename}")
        
        # Cache the result for future use
        _tts_cache[cache_key] = full_path
        print(f"DEBUG: Cached TTS result for key: {cache_key[:50]}...")
            
        return {"audio_filepath": full_path}
    except Exception as e:
        import traceback
        print(
            f"TTS_FAILURE segment={output_filename!r} voice={voice_name!r} "
            f"exception_type={type(e).__name__} message={e!s}"
        )
        traceback.print_exc()
        # Instead of returning an error string, raise the exception to be handled by the calling function
        raise Exception(f"TTS failed for {output_filename}: {e}")

def clean_text_for_speech(text: str) -> str:
    """
    Cleans text to make it suitable for text to speech conversion.
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
        
        content = _gemini_generate_text(prompt, generation_config=generation_config)
        
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
        
        # Configure Gemini with memory-efficient settings
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=1024,  # Limit output length
            temperature=0.7,  # Balanced creativity
            top_p=0.8,  # Focus on most likely tokens
            top_k=40  # Limit token selection
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
        
        content = _gemini_generate_text(prompt, generation_config=generation_config)
        
        # Validate the generated content
        is_valid, cleaned_content = validate_news_content(content, topic)
        
        if is_valid:
            print(f"DEBUG: Generated intelligent fallback for {topic} (category: {analysis.get('category', 'unknown')})")
            return cleaned_content
        else:
            # If AI generated content fails validation, use a generic professional template
            return generate_generic_fallback(topic)
            
    except Exception as e:
        print(f"DEBUG: AI fallback generation failed for {topic}: {e}")
        return generate_generic_fallback(topic)

def generate_generic_fallback(topic: str) -> str:
    """Last-resort spoken copy when Gemini is unavailable. Always names the actual story."""
    return _deterministic_reporter_script(topic, _categorize_topic_locally(topic))


_CATEGORY_KEYWORDS = {
    "sports": ("fifa", "infantino", "football", "soccer", "nba", "nfl", "mlb", "tennis", "olympic", "world cup"),
    "tech": ("stripe", "openrouter", "openai", "google", "apple", "microsoft", "crypto", "software", "startup", "ai "),
    "politics": ("oman", "bombing", "war", "election", "president", "minister", "nato", "sanctions", "congress"),
    "finance": ("fed", "inflation", "stock", "market", "bank", "interest rate", "wall street"),
    "health": ("covid", "vaccine", "who", "hospital", "outbreak", "fda"),
}


def _categorize_topic_locally(topic: str) -> str:
    text = (topic or "").lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "other"


def _category_for_topic(topic: str, categorized_topics: dict) -> str:
    if isinstance(categorized_topics, dict):
        if topic in categorized_topics:
            return _normalize_category(categorized_topics[topic])
        topic_l = str(topic).lower()
        for key, value in categorized_topics.items():
            if str(key).lower() == topic_l:
                return _normalize_category(value)
    return _categorize_topic_locally(topic)


def _voice_for_category(category: str) -> str:
    return _reporter_for_category(category)["voice"]


def _reporter_display_name(category: str) -> str:
    return _reporter_for_category(category)["name"]


def _deterministic_reporter_script(topic: str, category: str) -> str:
    reporter = _reporter_for_category(category)
    name = reporter["name"]
    desk = reporter["desk"]
    return (
        f"We are covering {topic}. "
        f"Our {desk} team is checking official statements and independent reporting on {topic}, "
        f"and we will bring you the next confirmed details as soon as they are available. "
        f"I am {name}, for GLC News."
    )


def _broadcast_summary(topics: list, reporter_scripts: list) -> str:
    """One unique line per topic so TextRank cannot collapse cloned boilerplate."""
    lines = []
    for topic, script in zip(topics, reporter_scripts):
        first = ""
        for sentence in re.split(r"(?<=[.!?])\s+", (script or "").strip()):
            if sentence and topic.lower() in sentence.lower():
                first = sentence.rstrip(".")
                break
        if not first:
            first = f"Coverage of {topic}"
        lines.append(f"{topic}: {first}.")
    return "\n".join(lines)


def _strip_json_fence(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_reporter_payload(raw: str) -> dict:
    """Parse Gemini reporter JSON, tolerating fences and alternate field names."""
    cleaned = _strip_json_fence(raw)
    data = None
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise json.JSONDecodeError("No reporter JSON object found", raw or "", 0)

    generated = {}
    reports = data.get("reports") or data.get("items") or []
    if isinstance(reports, dict):
        reports = [{"topic": key, "script": value} for key, value in reports.items()]
    for item in reports:
        if not isinstance(item, dict):
            continue
        topic = (item.get("topic") or item.get("title") or "").strip()
        script = (
            item.get("script")
            or item.get("content")
            or item.get("report")
            or item.get("text")
            or ""
        ).strip()
        if topic and len(script) > 40:
            generated[topic] = script
    return generated


def _reporter_json_generation_config():
    import google.generativeai as genai
    return genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=0.7,
        max_output_tokens=4096,
    )


def _gemini_reporter_script_single(topic: str, assignment: dict, research: dict | None = None) -> str:
    """Generate one reporter script when the batch call misses or fails a topic."""
    name = (assignment.get("name") or "our reporter").strip()
    desk = (assignment.get("desk") or "news").strip()
    from glconnect.parallel_news_search import format_research_block

    packet = format_research_block(research)
    research_rule = (
        "Use only facts from the research packet. Do not invent names, numbers, or quotes. "
        if packet
        else "No live research packet was available; use careful general knowledge of the topic. "
    )
    prompt = (
        f"Write a spoken radio news report about {topic!r}. "
        f"You are {name} on the {desk} desk. "
        f"{research_rule}"
        "Use 4 to 6 sentences with concrete details about the story. "
        f'Sign off exactly: "I am {name}, for GLC News." '
        "Return only the spoken script text.\n"
        f"{packet}"
    )
    try:
        raw = _gemini_generate_text(prompt)
        script = clean_text_for_speech(_strip_json_fence(raw))
        if len(script) > 40:
            return script
    except Exception as exc:
        print(f"DEBUG: Single-topic Gemini script failed for {topic!r}: {exc}")
    return ""


def _gemini_reporter_scripts(
    topics: list,
    assignments: list = None,
    trace: NewsPipelineTrace = None,
    research: dict | None = None,
) -> dict:
    """One Gemini call for all reporter scripts. Returns {topic: script} or {}."""
    if not topics:
        return {}
    try:
        assignment_lines = []
        for item in assignments or []:
            assignment_lines.append(
                f'- Topic {item["topic"]!r}: reporter {item["name"]} on the {item["desk"]} desk. '
                f'Sign off exactly: "I am {item["name"]}, for GLC News."'
            )
        assignment_block = "\n".join(assignment_lines) if assignment_lines else ""
        from glconnect.parallel_news_search import format_research_block

        research_blocks = []
        for topic in topics:
            block = format_research_block((research or {}).get(topic))
            if block:
                research_blocks.append(block)
        research_section = "\n\n".join(research_blocks)
        research_rule = (
            "Use only facts from the research packets below. Do not invent names, numbers, or quotes. "
            if research_section
            else "No live research packets were available; use careful general knowledge of each topic. "
        )
        prompt = (
            "Write spoken radio news reports. Return ONLY JSON:\n"
            '{"reports": [{"topic": "<exact topic>", "script": "<4 to 6 spoken sentences, no titles, '
            'no asterisks>"}]}\n'
            f"Topics: {json.dumps(list(topics))}\n"
            f"Assigned reporters:\n{assignment_block}\n"
            f"{research_rule}"
            "Each script must cover that exact topic only, be spoken by that assigned reporter, "
            "and must not reuse sentences across reports. "
            "The studio anchor is a different person and must not file these reports.\n"
            f"{research_section}"
        )
        raw = _gemini_generate_text(prompt, generation_config=_reporter_json_generation_config())
        gemini_meta = dict(_last_gemini_meta)
        try:
            generated = _parse_reporter_payload(raw)
        except json.JSONDecodeError as exc:
            warning = f"Reporter JSON parse failed: {_clip_trace_text(exc, 160)}"
            if trace:
                trace.stage(
                    "scripts_generate",
                    status="fallback",
                    warning=warning,
                    model=gemini_meta.get("model"),
                    attempts=gemini_meta.get("attempts"),
                    error="invalid_json",
                    chars=len(raw or ""),
                )
            print(f"DEBUG: Gemini reporter scripts failed: {exc}")
            return {}
        matched = {}
        for topic in topics:
            if topic in generated:
                matched[topic] = generated[topic]
                continue
            for key, script in generated.items():
                if key.lower() == topic.lower() or topic.lower() in key.lower() or key.lower() in topic.lower():
                    matched[topic] = script
                    break
        unmatched = [topic for topic in topics if topic not in matched]
        print(f"DEBUG: Gemini reporter scripts matched {len(matched)}/{len(topics)} topics")
        if trace:
            status = "ok"
            warning = None
            if unmatched:
                status = "partial_fallback" if matched else "fallback"
                warning = (
                    f"Gemini scripts matched {len(matched)}/{len(topics)}; "
                    f"unmatched={unmatched}; generated_keys={list(generated.keys())}"
                )
            trace.stage(
                "scripts_generate",
                status=status,
                warning=warning,
                model=gemini_meta.get("model"),
                attempts=gemini_meta.get("attempts"),
                matched=f"{len(matched)}/{len(topics)}",
                generated_keys=list(generated.keys()),
                unmatched=unmatched or None,
            )
        return matched
    except Exception as exc:
        classified = _classify_model_error(exc)
        warning = f"Gemini reporter scripts failed ({classified}): {_clip_trace_text(exc, 200)}"
        print(f"DEBUG: {warning}")
        if trace:
            trace.stage(
                "scripts_generate",
                status="fallback",
                warning=warning,
                model=_last_gemini_meta.get("model"),
                attempts=_last_gemini_meta.get("attempts"),
                error=classified,
                detail=_clip_trace_text(exc, 240),
            )
        return {}


def _build_reporter_segments(topics: list, categorized_topics: dict, trace: NewsPipelineTrace = None):
    """One reporter audio segment per user topic, with a distinct script."""
    assignments = []
    for topic in topics:
        category = _category_for_topic(topic, categorized_topics)
        reporter = _reporter_for_category(category)
        assignments.append({
            "topic": topic,
            "category": category,
            "name": reporter["name"],
            "desk": reporter["desk"],
            "voice": reporter["voice"],
        })
    from glconnect.parallel_news_monitor import recent_event_packets
    from glconnect.parallel_news_search import search_topics_for_news

    research = search_topics_for_news(topics, trace=trace)
    monitored = recent_event_packets(topics)
    for topic, items in monitored.items():
        packet = research.setdefault(
            topic, {"topic": topic, "source": "monitor", "items": []}
        )
        packet["items"] = list(items) + list(packet.get("items") or [])
        packet["source"] = "parallel+monitor" if packet["items"] else packet.get("source")
    if trace and monitored:
        trace.stage(
            "parallel_monitor_inbox",
            topics_with_events=f"{len(monitored)}/{len(topics)}",
        )
    generated = _gemini_reporter_scripts(
        topics, assignments=assignments, trace=trace, research=research
    )
    script_api_error = (_last_gemini_meta or {}).get("error")
    skip_single = script_api_error in _FATAL_SCRIPT_ERRORS
    script_keys = []
    scripts = []
    segments = []
    reporter_trace = []
    fallback_count = 0
    for index, assignment in enumerate(assignments):
        topic = assignment["topic"]
        category = assignment["category"]
        script = generated.get(topic)
        source = "gemini"
        if script and not is_placeholder_reporter_script(script):
            print(f"DEBUG: Reporter {index} using Gemini script for topic={topic!r}")
        elif skip_single:
            source = "deterministic_fallback"
            fallback_count += 1
            script = ""
            print(f"DEBUG: Reporter {index} stopping on {script_api_error} for topic={topic!r}")
        else:
            script = _gemini_reporter_script_single(topic, assignment, research.get(topic))
            if script and not is_placeholder_reporter_script(script):
                source = "gemini_single"
                print(f"DEBUG: Reporter {index} using single-topic Gemini script for topic={topic!r}")
            else:
                source = "deterministic_fallback"
                fallback_count += 1
                script = ""
                print(f"DEBUG: Reporter {index} missing usable script for topic={topic!r}")
        if fallback_count and not script:
            reporter_trace.append({
                "index": index,
                "topic": topic,
                "category": category,
                "source": source,
                "voice": assignment["voice"],
                "reporter": assignment["name"],
                "desk": assignment["desk"],
                "chars": 0,
            })
            continue
        segment_id = f"report_{index}"
        script_keys.append(f"{segment_id}_script")
        scripts.append(script)
        segments.append((segment_id, clean_text_for_speech(script), assignment["voice"]))
        reporter_trace.append({
            "index": index,
            "topic": topic,
            "category": category,
            "source": source,
            "voice": assignment["voice"],
            "reporter": assignment["name"],
            "desk": assignment["desk"],
            "anchor_collision": _reporter_voice_collides_with_anchor(assignment["voice"]),
            "chars": len(script),
        })
        print(
            f"DEBUG: Reporter {index} name={assignment['name']} category={category} "
            f"topic={topic!r} voice={assignment['voice']} chars={len(script)}"
        )
    if fallback_count:
        reason = script_api_error or "empty_response"
        message = script_abort_message(reason, fallback_count, len(topics))
        if trace:
            trace.stage(
                "scripts_assign",
                status="failed",
                error=reason,
                warning=message,
                fallback_count=fallback_count,
                reporters=reporter_trace,
            )
        print(f"PIPELINE_ABORT reason={reason} message={message}")
        raise NewsScriptUnavailable(reason, message)
    if trace:
        collisions = [row["topic"] for row in reporter_trace if row.get("anchor_collision")]
        warning = None
        if collisions:
            warning = f"Reporter voice collides with studio anchor for: {collisions}"
        trace.stage(
            "scripts_assign",
            status="ok",
            warning=warning,
            fallback_count=0,
            reporters=reporter_trace,
        )
    return script_keys, scripts, segments, assignments

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
        
        # Build dynamic FFmpeg command based on actual file paths
        cmd = ['ffmpeg', '-y']  # -y to overwrite output file
        
        # Add all input files to the command
        input_files = []
        for file_path in file_paths:
            if isinstance(file_path, dict) and 'audio_filepath' in file_path:
                file_path = file_path['audio_filepath']
            
            # Convert relative paths to absolute paths
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            
            if os.path.exists(file_path) and not file_path.startswith("Error:"):
                cmd.extend(['-i', file_path])
                input_files.append(file_path)
                print(f"DEBUG: Added input file to FFmpeg: {file_path}")
        
        # Build filter_complex string dynamically
        num_inputs = len(input_files)
        if num_inputs == 0:
            return {"combined_audio_filepath": "Error: No valid input files found"}
        
        # Create filter_complex string: [0:0][1:0][2:0]...concat=n=N:v=0:a=1[out]
        filter_inputs = ''.join([f'[{i}:0]' for i in range(num_inputs)])
        filter_complex = f'{filter_inputs}concat=n={num_inputs}:v=0:a=1[out]'
        
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[out]',
            '-c:a', 'libmp3lame',
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '2',
            output_path
        ])
        
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

        # DO NOT clean up intermediate files here - they will be cleaned up after final broadcast verification
        print(f"DEBUG: Skipping intermediate file cleanup - will be done after final broadcast verification")

        return {"combined_audio_filepath": full_path}
    except Exception as e:
        print(f"Critical error during combine_audio_files: {e}")
        return {"combined_audio_filepath": f"Error: Critical failure in audio combination. {e}"}

# --- Define Voices ---
# Studio-O is the desk anchor only. Field reporters must use a different voice
# or the same person appears to both host the bulletin and file a report.
ANCHOR_VOICE = 'en-US-Studio-O'
ERNEST_VOICE = 'en-US-Neural2-D'
EDITH_VOICE = 'en-US-Neural2-C'
ISABELLA_VOICE = 'en-US-Standard-F'
MARK_VOICE = 'en-GB-Standard-B'
CLARA_VOICE = 'en-US-Neural2-F'
JAMES_VOICE = 'en-US-Neural2-A'

_REPORTER_ROSTER = {
    "sports": {"name": "Ernest", "desk": "sports", "voice": ERNEST_VOICE},
    "finance": {"name": "Isabella", "desk": "finance", "voice": ISABELLA_VOICE},
    "tech": {"name": "Mark", "desk": "tech", "voice": MARK_VOICE},
    "politics": {"name": "Edith", "desk": "politics", "voice": EDITH_VOICE},
    "health": {"name": "Clara", "desk": "health", "voice": CLARA_VOICE},
    "other": {"name": "James", "desk": "news", "voice": JAMES_VOICE},
}

_CATEGORY_ALIASES = {
    "political": "politics",
    "economy": "finance",
    "business": "finance",
    "technology": "tech",
    "science": "health",
    "health & science": "health",
    "world": "other",
    "world & international": "other",
    "international": "other",
    "news": "other",
}


def _normalize_category(category: str) -> str:
    text = (category or "other").strip().lower()
    text = _CATEGORY_ALIASES.get(text, text)
    return text if text in _REPORTER_ROSTER else "other"


def _reporter_for_category(category: str) -> dict:
    reporter = dict(_REPORTER_ROSTER[_normalize_category(category)])
    reporter["voice"] = _sanitize_reporter_voice(reporter["voice"])
    return reporter


def _reporter_voice_collides_with_anchor(voice: str) -> bool:
    """True when TTS would sound like the studio anchor (Google name or ElevenLabs id)."""
    if not voice or voice == ANCHOR_VOICE:
        return True
    anchor_id = _ELEVENLABS_VOICE_MAP.get(ANCHOR_VOICE)
    reporter_id = _ELEVENLABS_VOICE_MAP.get(voice)
    return bool(anchor_id and reporter_id and anchor_id == reporter_id)


def _sanitize_reporter_voice(voice: str) -> str:
    """Hard guard: field reporters must never use the anchor voice."""
    if not _reporter_voice_collides_with_anchor(voice):
        return voice
    print(
        f"WARNING: Reporter voice {voice!r} collides with anchor {ANCHOR_VOICE!r}; "
        f"using fallback {JAMES_VOICE!r}"
    )
    return JAMES_VOICE


def _validate_reporter_roster() -> None:
    """Fail fast at import if roster config would let a reporter sound like the anchor."""
    for category, reporter in _REPORTER_ROSTER.items():
        if _reporter_voice_collides_with_anchor(reporter["voice"]):
            raise ValueError(
                f"Reporter roster misconfigured: {category} voice {reporter['voice']!r} "
                f"matches studio anchor {ANCHOR_VOICE!r}"
            )
    if _ELEVENLABS_DEFAULT_VOICE == _ELEVENLABS_VOICE_MAP.get(ANCHOR_VOICE):
        raise ValueError(
            "ElevenLabs default voice must not be the studio anchor voice"
        )


_validate_reporter_roster()

def create_news_reporter_agent(topic: str, voice: str, agent_name: str, output_key: str) -> Agent:
    """Creates a news reporter agent for a specific topic."""
    return Agent(
        model=NEWS_GEMINI_MODEL,
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
        model=NEWS_GEMINI_MODEL,
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
        model=NEWS_GEMINI_MODEL,
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
        model=NEWS_GEMINI_MODEL,
        name=agent_name,
        description=f"Converts the {script_key} to audio using the specified voice.",
        instruction=instruction,
        output_key=output_key,
        tools=[text_to_speech]
    )


async def run_agent(agent, input_text):
    agent_name = getattr(agent, "name", agent.__class__.__name__)
    print(f"AGENT_START name={agent_name!r}")
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
    
    try:
        async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=Content(role="user", parts=[Part(text=input_text)])):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
        print(f"AGENT_SUCCESS name={agent_name!r}")
        return final_response
    except Exception as e:
        import traceback
        print(
            f"AGENT_FAILURE name={agent_name!r} exception_type={type(e).__name__} "
            f"message={e!s}"
        )
        traceback.print_exc()
        raise

def generate_broadcast_memory_optimized(topics: list[str], task_id: str = None) -> dict:
    """
    Memory-optimized news generation that processes topics sequentially.
    This version uses much less memory by avoiding parallel processing.
    """
    import gc
    import psutil
    import os
    
    print("DEBUG: Using memory optimized sequential processing")
    
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
        return {
            "error": (
                "Memory-optimized fallback does not generate reporter scripts. "
                "No bulletin was generated."
            )
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
    trace = NewsPipelineTrace(topics, task_id=task_id)
    trace.stage(
        "start",
        default_model=NEWS_GEMINI_MODEL,
        model_candidates=_gemini_model_candidates(),
        topic_count=len(topics or []),
    )
    
    if not topics:
        print("No topics entered. Exiting.")
        trace.stage("start", status="failed", error="No topics provided")
        return _result_with_pipeline({"error": "No topics provided"}, trace)

    tts_error = validate_tts_credentials()
    if tts_error:
        print(f"ERROR: TTS preflight failed: {tts_error}")
        trace.stage("tts_preflight", status="failed", error=tts_error)
        return _result_with_pipeline({"error": tts_error}, trace)
    trace.stage("tts_preflight", backend=_tts_backend)
    
    # Check memory before starting
    try:
        import psutil
        memory_info = psutil.virtual_memory()
        print(f"DEBUG: Memory at start - Used: {memory_info.used / 1024 / 1024:.1f}MB, Percent: {memory_info.percent}%")
        if memory_info.percent > 90:  # More appropriate threshold for 4GB containers
            print(f"ERROR: Memory usage too high ({memory_info.percent}%) - aborting")
            trace.stage("memory", status="failed", error=f"Memory usage too high ({memory_info.percent}%)")
            return _result_with_pipeline(
                {"error": f"Memory usage too high ({memory_info.percent}%) - please try again later"},
                trace,
            )
    except Exception as e:
        print(f"DEBUG: Memory check failed: {e}")
    
    # Use the original workflow but with memory optimizations
    try:
        return _generate_broadcast_attempt(topics, task_id, trace)
    except NewsScriptUnavailable as exc:
        print(f"ERROR: Aborting news bulletin: {exc}")
        return _result_with_pipeline(
            {"error": str(exc), "audio_file": None, "reason": exc.reason_code},
            trace,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        trace.stage(
            "pipeline",
            status="failed",
            error=type(exc).__name__,
            detail=_clip_trace_text(exc, 240),
        )
        return _result_with_pipeline(
            {"error": f"News generation failed: {exc}", "audio_file": None},
            trace,
        )

def _run_async_safely(coro_factory, max_retries=3, retry_delay=2, raise_on_failure=False):
    """Safely run async coroutine in a thread, handling interpreter shutdown gracefully with retry logic."""
    import asyncio
    import inspect
    import sys
    import time
    
    global _last_async_error
    last_error = None
    _last_async_error = None

    if callable(coro_factory) and not inspect.iscoroutine(coro_factory):
        get_coro = coro_factory
    elif inspect.iscoroutine(coro_factory):
        spent_coro = coro_factory
        get_coro = lambda: spent_coro
        max_retries = 1
    else:
        get_coro = lambda: coro_factory

    for attempt in range(max_retries):
        coro = get_coro()
        if inspect.iscoroutine(coro) is False and coro is None:
            _last_async_error = "Async factory returned None instead of a coroutine"
            break
        try:
            # Check if the interpreter is shutting down
            if sys.is_finalizing():
                _last_async_error = "RuntimeError: Python interpreter is finalizing"
                print(f"DEBUG: Interpreter is finalizing, cannot run async operation (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                if raise_on_failure:
                    raise RuntimeError(_last_async_error)
                return None
            
            # Check if there's a closed event loop set as the current loop
            try:
                current_loop = asyncio.get_event_loop()
                if current_loop.is_closed():
                    _last_async_error = "RuntimeError: current asyncio event loop is closed"
                    print(f"DEBUG: Current event loop is closed, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    if raise_on_failure:
                        raise RuntimeError(_last_async_error)
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
                    last_error = e
                    _last_async_error = f"{type(e).__name__}: {e}"
                    print(f"DEBUG: Interpreter is shutting down, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        print(f"DEBUG: Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    if raise_on_failure:
                        raise e
                    return None
                elif "Event loop is closed" in str(e):
                    last_error = e
                    _last_async_error = f"{type(e).__name__}: {e}"
                    print(f"DEBUG: Event loop is closed, cannot run async operation (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        print(f"DEBUG: Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    if raise_on_failure:
                        raise e
                    return None
                else:
                    raise e
        except Exception as e:
            import traceback
            last_error = e
            print(
                f"ASYNC_FAILURE attempt={attempt + 1}/{max_retries} "
                f"exception_type={type(e).__name__} message={e!s}"
            )
            traceback.print_exc()
            err_text = str(e)
            if attempt < max_retries - 1:
                wait_s = max(retry_delay, 15) if ("RESOURCE_EXHAUSTED" in err_text or "429" in err_text) else retry_delay
                print(f"DEBUG: Retrying in {wait_s} seconds...")
                time.sleep(wait_s)
                continue
            if raise_on_failure:
                raise last_error
            return None
    
    if last_error:
        _last_async_error = f"{type(last_error).__name__}: {last_error}"
        print(
            f"ASYNC_FINAL_FAILURE exception_type={type(last_error).__name__} "
            f"message={last_error!s}"
        )
    else:
        _last_async_error = "Interpreter shutdown or closed event loop"
        print("ASYNC_FINAL_FAILURE reason=interpreter_shutdown_or_closed_event_loop")
    print(f"DEBUG: All {max_retries} attempts failed in _run_async_safely")
    if raise_on_failure:
        raise RuntimeError(_last_async_error or "Async operation failed without a captured exception")
    return None

def _generate_broadcast_attempt(topics: list[str], task_id: str = None, trace: NewsPipelineTrace = None) -> dict:
    import gc
    import psutil
    import os
    if trace is None:
        trace = NewsPipelineTrace(topics, task_id=task_id)
    
    # Check memory at start and abort if too high using container-aware monitoring
    try:
        memory_percent = get_memory_usage()
        print(f"DEBUG: Memory at start of broadcast generation - Percent: {memory_percent:.1f}%")
        
        if memory_percent > 90:  # Abort only under real memory pressure
            print(f"ERROR: Memory usage too high ({memory_percent:.1f}%) - aborting broadcast generation")
            trace.stage("memory", status="failed", error=f"Memory usage too high ({memory_percent:.1f}%)")
            return _result_with_pipeline(
                {"error": f"Memory usage too high ({memory_percent:.1f}%) - please try again later"},
                trace,
            )
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
        model=NEWS_GEMINI_MODEL,
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

    categorized_topics_json = _run_async_safely(lambda: run_agent(categorization_agent, str(topics)))
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
        warning = f"Categorization agent failed, using local keyword categories: {_clip_trace_text(_last_async_error, 200)}"
        print(f"DEBUG: {warning}")
        categorized_topics = {topic: _categorize_topic_locally(topic) for topic in topics}
        trace.stage(
            "categorize",
            status="ok",
            source="local_keywords",
            warning=warning,
            categories=categorized_topics,
            error=_clip_trace_text(_last_async_error, 200),
        )
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
            trace.stage(
                "categorize",
                source="adk_agent",
                model=NEWS_GEMINI_MODEL,
                categories=categorized_topics,
            )
        except json.JSONDecodeError as e:
            warning = f"Categorization JSON decode failed, using local keyword categories: {e}"
            print(f"DEBUG: {warning}")
            categorized_topics = {topic: _categorize_topic_locally(topic) for topic in topics}
            trace.stage(
                "categorize",
                status="ok",
                source="local_keywords",
                warning=warning,
                categories=categorized_topics,
                preview=_clip_trace_text(categorized_topics_json, 200),
            )
    print(f"DEBUG: Parsed categories: {categorized_topics}")

    # Group topics by category
    topics_by_category = {}
    for topic, category in categorized_topics.items():
        if category not in topics_by_category:
            topics_by_category[category] = []
        topics_by_category[category].append(topic)
    
    print(f"DEBUG: Topics grouped by category: {topics_by_category}")

    try:
        reporter_script_keys, reporter_scripts, reporter_segments, reporter_assignments = _build_reporter_segments(
            topics, categorized_topics, trace=trace
        )
    except NewsScriptUnavailable as exc:
        print(f"ERROR: Aborting news bulletin: {exc}")
        if task_id:
            try:
                from glconnect.news_routes import update_task_in_db
                update_task_in_db(
                    task_id,
                    current_step=str(exc)[:250],
                    last_heartbeat=datetime.now(),
                )
            except Exception:
                pass
        return _result_with_pipeline(
            {"error": str(exc), "audio_file": None, "reason": exc.reason_code},
            trace,
        )

    timezone = get_timezone_info().get("timezone_info", "Welcome to GLC News")
    intro_text = _anchor_intro_text(timezone, topics)
    transitions = [
        _anchor_handoff_text(
            assignment,
            previous=reporter_assignments[index - 1] if index else None,
        )
        for index, assignment in enumerate(reporter_assignments)
    ]
    outro_text = _anchor_outro_text(reporter_assignments)
    persisted_scripts = {
        "intro": intro_text,
        "outro": outro_text,
        "reporters": [
            {
                "topic": assignment["topic"],
                "desk": assignment["desk"],
                "name": assignment["name"],
                "category": assignment["category"],
                "script": reporter_scripts[index],
                "handoff": transitions[index],
            }
            for index, assignment in enumerate(reporter_assignments)
        ],
    }
    print(
        f"DEBUG: Persisted video scripts intro={len(intro_text)} "
        f"outro={len(outro_text)} reporters={len(persisted_scripts['reporters'])}"
    )
    print(f"DEBUG: Built {len(reporter_segments)} reporter segments")

    if task_id:
        try:
            from glconnect.news_routes import update_task_in_db
            update_task_in_db(
                task_id,
                progress=55,
                current_step=f'Writing {len(reporter_segments)} reporter scripts...',
                last_heartbeat=datetime.now(),
            )
        except Exception:
            pass

    final_audio_paths = [
        "glconnect/static/audio/jingle.wav",
        "glconnect/static/audio/intro_audio.mp3",
    ]
    for i, (segment_id, _script, _voice) in enumerate(reporter_segments):
        final_audio_paths.append(f"glconnect/static/audio/transition_audio_{i}.mp3")
        final_audio_paths.append(f"glconnect/static/audio/{segment_id}_audio.mp3")
    final_audio_paths.extend([
        "glconnect/static/audio/outro_audio.mp3",
        "glconnect/static/audio/jingle.wav",
    ])
    summarized_text_input = " ".join(reporter_scripts)

    # Convert all scripts to audio directly (more reliable than Gemini tool-calling)
    print("DEBUG: Executing direct TTS phase...")
    if task_id:
        try:
            from glconnect.news_routes import update_task_in_db
            update_task_in_db(
                task_id,
                progress=70,
                current_step='Converting text segments to speech...',
                last_heartbeat=datetime.now(),
            )
        except Exception:
            pass

    try:
        _run_direct_tts_phase(
            intro_text=intro_text,
            outro_text=outro_text,
            transitions=transitions,
            reporter_segments=reporter_segments,
            task_id=task_id,
        )
    except Exception as exc:
        print(f"DEBUG: Direct TTS phase failed: {exc}")
        import traceback
        traceback.print_exc()
        trace.stage(
            "tts",
            status="failed",
            backend=_tts_backend,
            error=_classify_model_error(exc),
            detail=_clip_trace_text(exc, 240),
        )
        return _result_with_pipeline(
            {
                "audio_file": None,
                "summary": f"News generation failed: TTS conversion failed. Root cause: {exc}",
            },
            trace,
        )
    trace.stage("tts", backend=_tts_backend, segments=len(reporter_segments))

    gc.collect()

    if task_id:
        try:
            from glconnect.news_routes import update_task_in_db
            update_task_in_db(
                task_id,
                progress=85,
                current_step='TTS conversion completed, assembling final audio...',
                last_heartbeat=datetime.now(),
            )
        except Exception:
            pass

    print("DEBUG: Assembling final broadcast audio...")
    combine_result = combine_audio_files(final_audio_paths, output_filename="final_news_broadcast.mp3")
    combined_path = combine_result.get("combined_audio_filepath", "")
    if not combined_path or str(combined_path).startswith("Error"):
        trace.stage("assemble", status="failed", error=_clip_trace_text(combined_path, 240))
        return _result_with_pipeline(
            {
                "audio_file": None,
                "summary": f"News generation failed: audio assembly failed. Root cause: {combined_path}",
            },
            trace,
        )
    trace.stage("assemble", path=combined_path)

    broadcast_summary = _broadcast_summary(topics, reporter_scripts)
    if not broadcast_summary.strip():
        summary_result = summarize_text(summarized_text_input)
        broadcast_summary = summary_result.get("summary", "")
    
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
        return _result_with_pipeline(
            {
                "audio_file": web_path,
                "summary": broadcast_summary,
                "topics": list(topics),
                "scripts": persisted_scripts,
            },
            trace,
        )
    else:
        print("DEBUG: No audio files found")
        trace.stage("finalize", status="failed", error="Final audio file was not found")
        return _result_with_pipeline(
            {
                "audio_file": None,
                "summary": broadcast_summary or "News generation completed but final audio file was not found.",
                "topics": list(topics),
            },
            trace,
        )




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
