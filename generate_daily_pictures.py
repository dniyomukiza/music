#!/usr/bin/env python3
"""
Daily Picture Generation Script for Picture-Word Matching Game
Generates 3 pictures daily using Gemini API and stores them locally
"""

import os
import sys
import json
import random
import requests
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, PictureGameItem, WordsData
from glconnect.book_cover_ai import iter_book_cover_image_models
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from PIL import Image
from io import BytesIO

def generate_image_with_gemini(word, meaning):
    """Generate an image with interleaved text using Gemini API for a Kinyarwanda word"""
    try:
        # Configure Gemini client
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        client = genai.Client(api_key=api_key)
        
        # Create a focused prompt for image generation with English text overlay only
        prompt = f"""
        Create an educational image for a Kinyarwanda language learning matching game with these specifications:
        
        Kinyarwanda word: "{word}"
        English meaning: "{meaning}"
        
        Image requirements:
        1. VISUAL ELEMENTS:
           - Clear, simple illustration representing the word/concept
           - Professional, clean design suitable for learning
           - Bright, engaging colors
           - Uncluttered composition
           - Focus on the main object/concept
           
        2. TEXT OVERLAY (integrated into the image):
           - ONLY show the English translation: "{meaning}"
           - Position the text at the bottom of the image
           - Make it clearly readable with good contrast
           - Use a clean, readable font
           - Add a subtle background behind the text for readability
           
        3. DESIGN SPECIFICATIONS:
           - Image size: 400x300 pixels (landscape orientation)
           - English text should be prominent but not overwhelming
           - Use white or light text with dark background, or dark text with light background
           - Professional, educational appearance
           - No decorative borders or frames
           - Text should be positioned to not interfere with the main visual
           
        4. CONTENT GUIDELINES:
           - Make the image immediately recognizable
           - Suitable for all ages
           - Culturally appropriate
           - Focus on the main concept so users can easily match with Kinyarwanda words
           - The English text should help users understand what the picture represents
        """
        
        print(f"Generating image for: {word} ({meaning})")

        response = None
        last_err = None
        for model_name in iter_book_cover_image_models():
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt],
                )
                print(f"  Using Gemini image model: {model_name}")
                break
            except genai_errors.ClientError as e:
                last_err = e
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    print(f"  Model {model_name} unavailable, trying next…")
                    continue
                raise
            except Exception as e:
                last_err = e
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    print(f"  Model {model_name} unavailable, trying next…")
                    continue
                raise
        if response is None:
            raise last_err or RuntimeError("No image model available")

        # Extract image data from response
        image_data = None
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_data = part.inline_data.data
                break
        
        if image_data:
            return {
                "success": True,
                "image_data": image_data,  # Actual image bytes
                "prompt_used": prompt,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise Exception("No image data received from Gemini")
        
    except Exception as e:
        print(f"Error generating image for {word}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "image_data": None
        }

def get_random_kinyarwanda_words(limit=10):
    """Get random Kinyarwanda words from the database"""
    try:
        # Get words that don't already have picture game items
        existing_word_ids = db.session.query(PictureGameItem.word_id).filter(
            PictureGameItem.is_active == True
        ).subquery()
        
        words = WordsData.query.filter(
            WordsData.id.notin_(existing_word_ids),
            WordsData.word.isnot(None),
            WordsData.igisobanuro_meaning.isnot(None)
        ).limit(limit * 2).all()  # Get more than needed for variety
        
        if len(words) < limit:
            # If not enough unused words, get any words
            words = WordsData.query.filter(
                WordsData.word.isnot(None),
                WordsData.igisobanuro_meaning.isnot(None)
            ).limit(limit * 2).all()
        
        # Randomly select the required number
        selected_words = random.sample(words, min(limit, len(words)))
        
        return selected_words
        
    except Exception as e:
        print(f"Error getting random words: {str(e)}")
        return []

def extract_english_meaning(meaning_data):
    """Extract English meaning from the JSON meaning data"""
    try:
        if isinstance(meaning_data, str):
            meaning_data = json.loads(meaning_data)
        
        if isinstance(meaning_data, list) and len(meaning_data) > 0:
            # Check if it's a simple list of strings
            if all(isinstance(item, str) for item in meaning_data):
                # Try to find English by looking for common English words
                import re
                for item in meaning_data:
                    # Check for English patterns
                    if re.search(r'\b(maternal|love|pain|arms|directions|waving|bellow|loudly|generous|someone|too)\b', item.lower()):
                        return item
                
                # If no English patterns found, return the last item
                return meaning_data[-1]
            
            # Check if it's a list of meaning arrays (complex format)
            elif isinstance(meaning_data[0], list):
                first_meaning_array = meaning_data[0]
                if len(first_meaning_array) > 0 and all(isinstance(item, str) for item in first_meaning_array):
                    # For [Kinyarwanda, French, English] format, English is last
                    return first_meaning_array[-1]
            
            # Fallback: return the last item
            return meaning_data[-1]
        
        return str(meaning_data) if meaning_data else "No meaning available"
        
    except Exception as e:
        print(f"Error extracting meaning: {str(e)}")
        return "No meaning available"

def save_image(word, meaning, image_data):
    """Save the generated image to the static/pictures directory"""
    try:
        # Create filename
        safe_word = "".join(c for c in word if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_word}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join("glconnect", "static", "pictures", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save the actual image using PIL
        image = Image.open(BytesIO(image_data))
        image.save(filepath, 'PNG')
        
        print(f"✅ Saved image: {filename}")
        return filename
        
    except Exception as e:
        print(f"Error saving image for {word}: {str(e)}")
        return None

def generate_daily_pictures():
    """Main function to generate 6 pictures daily (3 + pause + 3)"""
    import time
    
    app = create_app()
    
    with app.app_context():
        try:
            print(f"Starting daily picture generation at {datetime.now()}")
            print("Generating 6 pictures per day with 1-minute pause between batches")
            
            # First batch: 3 pictures
            print("\n=== BATCH 1: Generating first 3 pictures ===")
            words_batch1 = get_random_kinyarwanda_words(limit=3)
            
            if len(words_batch1) == 0:
                print("No words found in database")
                return
            
            print(f"Found {len(words_batch1)} words for batch 1")
            
            generated_count = 0
            
            # Process first batch
            for word_data in words_batch1:
                try:
                    # Extract the word and meaning
                    kinyarwanda_word = word_data.word
                    english_meaning = extract_english_meaning(word_data.igisobanuro_meaning)
                    
                    print(f"Processing word: {kinyarwanda_word} -> {english_meaning}")
                    
                    # Generate image (placeholder for now)
                    image_result = generate_image_with_gemini(kinyarwanda_word, english_meaning)
                    
                    if image_result["success"] and image_result.get("image_data"):
                        # Save actual image file
                        image_filename = save_image(kinyarwanda_word, english_meaning, image_result["image_data"])
                        
                        if image_filename:
                            # Save to database with enhanced metadata
                            picture_item = PictureGameItem(
                                kinyarwanda_word=kinyarwanda_word,
                                english_meaning=english_meaning,
                                image_filename=image_filename,
                                word_id=word_data.id,
                                created_at=datetime.now(timezone.utc),
                                used_count=0,
                                is_active=True,
                                image_type='text_overlay',
                                pronunciation_guide=None,  # Could be extracted from word_data if available
                                context_hint=None,  # Could be extracted from word_data if available
                                text_overlay_data=json.dumps({
                                    'english_meaning': english_meaning,
                                    'text_position': 'bottom_overlay',
                                    'text_type': 'english_only',
                                    'font_size': 'medium'
                                }),
                                generation_prompt=image_result.get('prompt_used', '')
                            )
                            
                            db.session.add(picture_item)
                            db.session.commit()
                            
                            generated_count += 1
                            print(f"✅ Successfully created picture item for: {kinyarwanda_word}")
                        else:
                            print(f"❌ Failed to create image file for: {kinyarwanda_word}")
                    else:
                        print(f"❌ Failed to generate image for: {kinyarwanda_word} - {image_result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    print(f"❌ Error processing word {word_data.word}: {str(e)}")
                    continue
            
            print(f"Batch 1 completed. Generated {generated_count} pictures.")
            
            # Pause for 1 minute between batches
            print("\n⏳ Pausing for 1 minute before batch 2...")
            time.sleep(60)  # 1 minute pause
            
            # Second batch: 3 more pictures
            print("\n=== BATCH 2: Generating next 3 pictures ===")
            words_batch2 = get_random_kinyarwanda_words(limit=3)
            
            if len(words_batch2) == 0:
                print("No words found for batch 2")
                print(f"Daily picture generation completed. Generated {generated_count} pictures total.")
                return
            
            print(f"Found {len(words_batch2)} words for batch 2")
            
            # Process second batch
            for word_data in words_batch2:
                try:
                    # Extract the word and meaning
                    kinyarwanda_word = word_data.word
                    english_meaning = extract_english_meaning(word_data.igisobanuro_meaning)
                    
                    print(f"Processing word: {kinyarwanda_word} -> {english_meaning}")
                    
                    # Generate image using Gemini
                    image_result = generate_image_with_gemini(kinyarwanda_word, english_meaning)
                    
                    if image_result["success"] and image_result.get("image_data"):
                        # Save actual image file
                        image_filename = save_image(kinyarwanda_word, english_meaning, image_result["image_data"])
                    
                    if image_filename:
                        # Save to database with enhanced metadata
                        picture_item = PictureGameItem(
                            kinyarwanda_word=kinyarwanda_word,
                            english_meaning=english_meaning,
                            image_filename=image_filename,
                            word_id=word_data.id,
                            created_at=datetime.now(timezone.utc),
                            used_count=0,
                            is_active=True,
                            image_type='text_overlay',
                            pronunciation_guide=None,  # Could be extracted from word_data if available
                            context_hint=None,  # Could be extracted from word_data if available
                            text_overlay_data=json.dumps({
                                'english_meaning': english_meaning,
                                'text_position': 'bottom_overlay',
                                'text_type': 'english_only',
                                'font_size': 'medium'
                            }),
                            generation_prompt=image_result.get('prompt_used', '')
                        )
                        
                        db.session.add(picture_item)
                        db.session.commit()
                        
                        generated_count += 1
                        print(f"✅ Successfully created picture item for: {kinyarwanda_word}")
                    else:
                        print(f"❌ Failed to create image file for: {kinyarwanda_word}")
                        
                except Exception as e:
                    print(f"❌ Error processing word {word_data.word}: {str(e)}")
                    continue
            
            print(f"Batch 2 completed. Generated {generated_count} pictures total.")
            print(f"🎉 Daily picture generation completed! Generated {generated_count} pictures total.")
            
        except Exception as e:
            print(f"❌ Error in daily picture generation: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    generate_daily_pictures()
