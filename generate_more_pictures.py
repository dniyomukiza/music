#!/usr/bin/env python3
"""
Generate additional pictures for the picture-word matching game
Run this to create more pictures when the pool is running low
"""

import os
import sys
import json
import random
from datetime import datetime, timezone
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, PictureGameItem, WordsData
import google.generativeai as genai

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

def create_placeholder_image(word, meaning):
    """Create a placeholder image file for the word"""
    try:
        # Create a simple text-based image representation
        image_content = f"""
        Kinyarwanda Word: {word}
        English Meaning: {meaning}
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        # Create filename
        safe_word = "".join(c for c in word if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_word}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join("glconnect", "static", "pictures", filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write placeholder content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(image_content)
        
        return filename
        
    except Exception as e:
        print(f"Error creating placeholder image for {word}: {str(e)}")
        return None

def generate_more_pictures(count=20):
    """Generate additional pictures for the game pool"""
    app = create_app()
    
    with app.app_context():
        try:
            print(f"Generating {count} additional pictures...")
            
            # Get words that don't already have picture game items
            existing_word_ids = db.session.query(PictureGameItem.word_id).filter(
                PictureGameItem.is_active == True
            ).subquery()
            
            words = WordsData.query.filter(
                WordsData.id.notin_(existing_word_ids),
                WordsData.word.isnot(None),
                WordsData.igisobanuro_meaning.isnot(None)
            ).limit(count * 2).all()  # Get more than needed for variety
            
            if len(words) < count:
                # If not enough unused words, get any words
                words = WordsData.query.filter(
                    WordsData.word.isnot(None),
                    WordsData.igisobanuro_meaning.isnot(None)
                ).limit(count * 2).all()
            
            # Randomly select the required number
            selected_words = random.sample(words, min(count, len(words)))
            
            generated_count = 0
            
            for word_data in selected_words:
                try:
                    # Extract the word and meaning
                    kinyarwanda_word = word_data.word
                    english_meaning = extract_english_meaning(word_data.igisobanuro_meaning)
                    
                    print(f"Processing word: {kinyarwanda_word} -> {english_meaning}")
                    
                    # Create placeholder image file
                    image_filename = create_placeholder_image(kinyarwanda_word, english_meaning)
                    
                    if image_filename:
                        # Save to database
                        picture_item = PictureGameItem(
                            kinyarwanda_word=kinyarwanda_word,
                            english_meaning=english_meaning,
                            image_filename=image_filename,
                            word_id=word_data.id,
                            created_at=datetime.now(timezone.utc),
                            used_count=0,
                            is_active=True
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
            
            print(f"Additional picture generation completed. Generated {generated_count} pictures.")
            
        except Exception as e:
            print(f"❌ Error in additional picture generation: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Generate additional pictures for the game')
    parser.add_argument('--count', type=int, default=20, help='Number of pictures to generate (default: 20)')
    args = parser.parse_args()
    
    generate_more_pictures(args.count)
