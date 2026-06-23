import os
import json
from glconnect.forms import *
from flask import render_template, request, Blueprint, send_from_directory
from glconnect.search import SongSearcher
from google.cloud import texttospeech
import google.generativeai as genai

# Load Gemini / Google API key (same precedence as book covers and news validation)
def _get_google_api_key():
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

def _ensure_genai_configured():
    """Configure Gemini only when needed; raises if key missing."""
    key = _get_google_api_key()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY not set. Add one to .env or glconfig.json."
        )
    genai.configure(api_key=key)

bp2 = Blueprint('routes2', __name__)

# Get TTS credentials path from environment variables
tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")

# Create the text to speech client (lazy initialization)
client = None

def generate_news_with_gemini(topic: str) -> str:
    """Generate news content using Gemini API for a single topic."""
    try:
        _ensure_genai_configured()
        # Configure model with memory-efficient settings
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
        You are an experienced news reporter assistant that summarizes the latest news regarding certain topics.
        
        Provide a balanced article of the latest news about {topic} with an analytical perspective and potential impact. 
        Never include any header titles, intro, and subtitles.
        
        Write as a professional news reporter would deliver it on air.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating news with Gemini: {e}")
        return f"Error generating news content: {str(e)}"
@bp2.route("/news", methods=["GET", "POST"])
def news():
    form = KeywordForm()
    audio_file_path = None
    news_file_path = None
    validation_error = None
    
    if form.validate_on_submit():
        keyword = form.keyword.data
        print(f"Form keyword: {form.keyword.data}")
        
        # Step 0: Validate topic using NewsTopicValidationAgent
        try:
            from .news_routes import get_validation_agent
            validation_agent = get_validation_agent()
            is_valid, error_message = validation_agent.validate_topic(keyword)
            
            if not is_valid:
                validation_error = f"This topic does not seem to be a news topic: {error_message}"
                print(f"❌ Topic validation failed: {error_message}")
                # Return early with error message
                return render_template(
                    "newsgen.html",
                    form=form,
                    validation_error=validation_error,
                    audio_file=None,
                    audio_file_path=None,
                    news_file_path=None
                )
            else:
                print(f"✅ Topic validation passed: {keyword}")
                # Topic is valid - show success message and clear form
                success_message = f"Topic '{keyword}' added successfully! You can add more topics or generate news when ready."
                return render_template(
                    "newsgen.html",
                    form=form,
                    success_message=success_message,
                    audio_file=None,
                    audio_file_path=None,
                    news_file_path=None
                )
                
        except Exception as e:
            print(f"Error during topic validation: {e}")
            validation_error = f"Validation error: {str(e)}"
            return render_template(
                "newsgen.html",
                form=form,
                validation_error=validation_error,
                audio_file=None,
                audio_file_path=None,
                news_file_path=None
            )
    
    # Render template for GET requests or when no form submission
    return render_template(
        "newsgen.html",
        form=form,
        audio_file=None,
        audio_file_path=None,
        news_file_path=None
    )

@bp2.route('/static/<filename>')
def serve_audio(filename):
    """Serve audio files from the static directory"""
    static_folder = os.path.join(os.getcwd(), 'glconnect/static')
    return send_from_directory(static_folder, filename)

