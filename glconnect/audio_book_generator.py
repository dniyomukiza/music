"""
Audio Book Generator - Converts extracted text to audio using Google Cloud Text-to-Speech
Integrates with the existing TTS infrastructure used for news broadcasts
"""

import os
import tempfile
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import threading
import time

# Google Cloud TTS
try:
    from google.cloud import texttospeech
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

logger = logging.getLogger(__name__)

class AudioBookGenerator:
    """Generates audio books from text using Google Cloud Text-to-Speech"""
    
    def __init__(self):
        self.client = None
        self.max_chunk_size = 5000  # Characters per chunk to stay within TTS limits
        self.audio_dir = os.path.join(os.getcwd(), 'glconnect', 'static', 'audio', 'audiobooks')
        self.preview_dir = os.path.join(os.getcwd(), 'glconnect', 'static', 'audio', 'previews')
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.preview_dir, exist_ok=True)
        
        # In-memory cache for voices
        self._voices_cache = {
            'data': None,
            'timestamp': None,
            'ttl': 86400  # 24 hours
        }
        
        if TTS_AVAILABLE:
            # Don't initialize client at startup - use lazy initialization in _ensure_client()
            # This allows server to start even if credentials file is missing
            self.client = None
            logger.info("TTS available - client will be initialized on first use")
    
    def generate_audiobook(self, text: str, book_id: int, voice_name: str = 'en-US-Standard-A') -> Dict[str, Any]:
        """
        Generate audio book from text
        
        Args:
            text: Extracted text from digital book
            book_id: Book project ID
            voice_name: TTS voice to use
            
        Returns:
            Dictionary with generation results
        """
        if not self._ensure_client():
            return {
                'success': False,
                'error': 'TTS client not available. Please check Google Cloud credentials.',
                'audio_file_path': None,
                'duration': 0
            }
        
        try:
            # Split text into manageable chunks
            chunks = self._split_text_into_chunks(text)
            
            if not chunks:
                return {
                    'success': False,
                    'error': 'No text content to convert to audio',
                    'audio_file_path': None,
                    'duration': 0
                }
            
            # Generate audio for each chunk
            audio_files = []
            total_duration = 0
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Generating audio for chunk {i+1}/{len(chunks)}")
                
                chunk_result = self._generate_chunk_audio(chunk, book_id, i, voice_name)
                
                if chunk_result['success']:
                    audio_files.append(chunk_result['audio_file'])
                    total_duration += chunk_result.get('duration', 0)
                else:
                    logger.error(f"Failed to generate audio for chunk {i+1}: {chunk_result['error']}")
                    return {
                        'success': False,
                        'error': f"Failed to generate audio for chunk {i+1}: {chunk_result['error']}",
                        'audio_file_path': None,
                        'duration': 0
                    }
            
            # Combine all audio chunks into final audiobook
            final_audio_path = self._combine_audio_files(audio_files, book_id)
            
            if final_audio_path:
                # Clean up individual chunk files
                self._cleanup_chunk_files(audio_files)
                
                return {
                    'success': True,
                    'audio_file_path': final_audio_path,
                    'duration': total_duration,
                    'chunks_processed': len(chunks)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to combine audio chunks',
                    'audio_file_path': None,
                    'duration': 0
                }
                
        except Exception as e:
            logger.error(f"Error generating audiobook for book {book_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'audio_file_path': None,
                'duration': 0
            }
    
    def _split_text_into_chunks(self, text: str) -> list:
        """Split text into chunks suitable for TTS processing"""
        chunks = []
        
        # Split by sentences first
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed the limit, save current chunk
            if len(current_chunk) + len(sentence) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > self.max_chunk_size:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                chunks.append(word)  # Single word is too long
                        else:
                            temp_chunk += " " + word if temp_chunk else word
                    current_chunk = temp_chunk
            else:
                current_chunk += ". " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _generate_chunk_audio(self, text: str, book_id: int, chunk_index: int, voice_name: str) -> Dict[str, Any]:
        """Generate audio for a single text chunk"""
        try:
            # Set up voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_name.split('-')[0] + '-' + voice_name.split('-')[1],
                name=voice_name
            )
            
            # Set up audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Perform the synthesis
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save the audio file
            filename = f"book_{book_id}_chunk_{chunk_index}.mp3"
            audio_path = os.path.join(self.audio_dir, filename)
            
            with open(audio_path, 'wb') as out:
                out.write(response.audio_content)
            
            # Estimate duration (rough calculation: ~150 words per minute)
            word_count = len(text.split())
            estimated_duration = int((word_count / 150) * 60)  # seconds
            
            return {
                'success': True,
                'audio_file': audio_path,
                'duration': estimated_duration
            }
            
        except Exception as e:
            logger.error(f"Error generating audio for chunk {chunk_index}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'audio_file': None,
                'duration': 0
            }
    
    def _combine_audio_files(self, audio_files: list, book_id: int) -> Optional[str]:
        """Combine multiple audio files into a single audiobook"""
        try:
            import subprocess
            
            # Create final output path
            final_filename = f"audiobook_{book_id}_{int(time.time())}.mp3"
            final_path = os.path.join(self.audio_dir, final_filename)
            
            # Use FFmpeg to combine files (similar to news broadcast combination)
            cmd = ['ffmpeg', '-y']  # -y to overwrite output file
            
            # Add all input files
            for audio_file in audio_files:
                cmd.extend(['-i', audio_file])
            
            # Build filter_complex string
            num_inputs = len(audio_files)
            filter_inputs = ''.join([f'[{i}:0]' for i in range(num_inputs)])
            filter_complex = f'{filter_inputs}concat=n={num_inputs}:v=0:a=1[out]'
            
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-c:a', 'libmp3lame',
                '-b:a', '128k',
                '-ar', '44100',
                '-ac', '2',
                final_path
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Successfully combined audio files into {final_path}")
                return final_path
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error combining audio files: {str(e)}")
            return None
    
    def _cleanup_chunk_files(self, audio_files: list):
        """Clean up individual chunk audio files"""
        for audio_file in audio_files:
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup chunk file {audio_file}: {str(e)}")
    
    def get_audio_duration(self, audio_file_path: str) -> int:
        """Get actual duration of audio file using FFprobe"""
        try:
            import subprocess
            
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return int(duration)
            else:
                logger.warning(f"Failed to get audio duration: {result.stderr}")
                return 0
                
        except Exception as e:
            logger.warning(f"Error getting audio duration: {str(e)}")
            return 0
    
    def _ensure_client(self):
        """Ensure TTS client is initialized, try to initialize if not"""
        if self.client:
            return True
        
        if not TTS_AVAILABLE:
            logger.error("TTS library not available. Please install google-cloud-texttospeech")
            return False
        
        try:
            # Initialize TTS client using service account credentials (same as news_agent.py)
            from google.oauth2 import service_account
            
            # Get TTS credentials path from environment variables
            tts_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "tts.json")
            logger.debug(f"Loading TTS credentials from: {tts_credentials_path}")
            
            # Try multiple possible locations
            possible_paths = [
                tts_credentials_path,
                "tts.json",
                os.path.join(os.getcwd(), "tts.json"),
                os.path.join(os.getcwd(), "glconnect", "tts.json"),
                os.path.join(os.path.dirname(__file__), "..", "tts.json"),
                os.path.join(os.path.dirname(__file__), "tts.json")
            ]
            
            found_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    found_path = abs_path
                    logger.info(f"Found TTS credentials at: {found_path}")
                    break
            
            if not found_path:
                logger.error(f"TTS credentials file not found. Searched in: {possible_paths}")
                logger.error("Please ensure tts.json exists in the project root or set GOOGLE_APPLICATION_CREDENTIALS environment variable")
                return False
            
            tts_credentials_path = found_path
            
            # Load credentials from file
            credentials = service_account.Credentials.from_service_account_file(tts_credentials_path)
            self.client = texttospeech.TextToSpeechClient(credentials=credentials)
            logger.info("TTS client initialized successfully with service account credentials")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {str(e)}", exc_info=True)
            self.client = None
            return False
    
    def get_available_voices(self, language_filter: str = 'en') -> Dict[str, Any]:
        """
        Get available English voices from Google TTS API with caching
        
        Args:
            language_filter: Language code prefix to filter (default: 'en' for English)
            
        Returns:
            Dictionary with grouped voices by type
        """
        if not self._ensure_client():
            return {
                'success': False,
                'error': 'TTS client not available. Please ensure tts.json credentials file exists in the project root. The voice preview feature requires Google Cloud Text-to-Speech credentials.',
                'voices': {}
            }
        
        try:
            # Check cache
            current_time = time.time()
            cache = self._voices_cache
            
            if cache['data'] and cache['timestamp']:
                age = current_time - cache['timestamp']
                if age < cache['ttl']:
                    # Return cached data, but filter for requested language
                    cached_voices = cache['data']
                    filtered_voices = self._filter_voices_by_language(cached_voices, language_filter)
                    return {
                        'success': True,
                        'voices': filtered_voices,
                        'cached': True
                    }
            
            # Fetch from API
            response = self.client.list_voices()
            
            # Group voices by type and filter for English
            voices_by_type = {
                'Standard': [],
                'WaveNet': [],
                'Neural2': [],
                'Studio': [],
                'Chirp3': []
            }
            
            for voice in response.voices:
                # Check if voice supports English
                if any(lang.startswith(language_filter) for lang in voice.language_codes):
                    voice_name = voice.name
                    voice_type = self._get_voice_type(voice_name)
                    
                    voice_info = {
                        'name': voice_name,
                        'gender': voice.ssml_gender.name if hasattr(voice.ssml_gender, 'name') else str(voice.ssml_gender),
                        'language_codes': list(voice.language_codes),
                        'sample_rate': voice.natural_sample_rate_hertz
                    }
                    
                    if voice_type in voices_by_type:
                        voices_by_type[voice_type].append(voice_info)
                    else:
                        voices_by_type['Standard'].append(voice_info)  # Default fallback
            
            # Update cache
            self._voices_cache['data'] = voices_by_type
            self._voices_cache['timestamp'] = current_time
            
            return {
                'success': True,
                'voices': voices_by_type,
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"Error fetching voices: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'voices': {}
            }
    
    def _get_voice_type(self, voice_name: str) -> str:
        """Determine voice type from voice name (case-insensitive)"""
        voice_lower = voice_name.lower()
        if 'chirp' in voice_lower:
            return 'Chirp3'
        elif 'studio' in voice_lower:
            return 'Studio'
        elif 'neural2' in voice_lower:
            return 'Neural2'
        elif 'wavenet' in voice_lower:
            return 'WaveNet'
        else:
            return 'Standard'
    
    def _filter_voices_by_language(self, voices_by_type: dict, language_filter: str) -> dict:
        """Filter cached voices by language"""
        filtered = {
            'Standard': [],
            'WaveNet': [],
            'Neural2': [],
            'Studio': [],
            'Chirp3': []
        }
        
        for voice_type, voices in voices_by_type.items():
            for voice in voices:
                if any(lang.startswith(language_filter) for lang in voice.get('language_codes', [])):
                    filtered[voice_type].append(voice)
        
        return filtered
    
    def generate_preview_audio(self, voice_name: str, sample_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a short preview audio sample for a voice
        
        Args:
            voice_name: Name of the voice to preview
            sample_text: Optional custom sample text (default uses standard sample)
            
        Returns:
            Dictionary with preview audio file path or error
        """
        if not self._ensure_client():
            return {
                'success': False,
                'error': 'TTS client not available. Please ensure tts.json credentials file exists in the project root. The voice preview feature requires Google Cloud Text-to-Speech credentials.',
                'audio_url': None
            }
        
        # Default sample text
        if not sample_text:
            sample_text = "This is a sample of how your audiobook will sound with this voice. Listen carefully to the tone, pace, and clarity."
        
        # Limit sample text length
        if len(sample_text) > 500:
            sample_text = sample_text[:500] + "..."
        
        try:
            # Check if preview already exists
            safe_voice_name = voice_name.replace('/', '_').replace('\\', '_')
            preview_filename = f"preview_{safe_voice_name}_{hash(sample_text) % 10000}.mp3"
            preview_path = os.path.join(self.preview_dir, preview_filename)
            
            if os.path.exists(preview_path):
                # Return existing preview
                relative_path = f"audio/previews/{preview_filename}"
                return {
                    'success': True,
                    'audio_url': f"/static/{relative_path}",
                    'cached': True
                }
            
            # Extract language code from voice name (e.g., "en-US-Standard-A" -> "en-US")
            parts = voice_name.split('-')
            if len(parts) >= 2:
                language_code = f"{parts[0]}-{parts[1]}"
            else:
                language_code = "en-US"  # Default fallback
            
            # Set up voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name
            )
            
            # Set up audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            # Create synthesis input
            synthesis_input = texttospeech.SynthesisInput(text=sample_text)
            
            # Perform the synthesis
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Save the preview file
            with open(preview_path, 'wb') as out:
                out.write(response.audio_content)
            
            relative_path = f"audio/previews/{preview_filename}"
            
            logger.info(f"Generated preview audio for voice {voice_name}")
            
            return {
                'success': True,
                'audio_url': f"/static/{relative_path}",
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"Error generating preview audio for voice {voice_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'audio_url': None
            }

# Global generator instance
audio_book_generator = AudioBookGenerator()
