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
        os.makedirs(self.audio_dir, exist_ok=True)
        
        if TTS_AVAILABLE:
            try:
                self.client = texttospeech.TextToSpeechClient()
            except Exception as e:
                logger.error(f"Failed to initialize TTS client: {str(e)}")
                self.client = None
    
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
        if not self.client:
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

# Global generator instance
audio_book_generator = AudioBookGenerator()
