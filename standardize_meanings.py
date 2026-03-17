#!/usr/bin/env python3
"""
Standardize meaning order in words_data table to [Kinyarwanda, French, English]
"""

import os
import sys
import json
import re

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, WordsData

def detect_language(text):
    """Detect if text is Kinyarwanda, French, or English"""
    text_lower = text.lower()
    
    # English indicators
    english_words = ['the', 'a', 'an', 'and', 'or', 'of', 'in', 'to', 'for', 'with', 'by', 'from', 'at', 'on', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'pain', 'love', 'time', 'arms', 'directions', 'bellow', 'loudly', 'same', 'maternal', 'compassion', 'generous', 'person', 'postpartum', 'beans', 'maize', 'grown', 'marshes', 'during', 'long', 'dry', 'season', 'rope', 'used', 'attach', 'skin', 'bellows', 'rods']
    
    # French indicators
    french_words = ['le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'dans', 'sur', 'avec', 'pour', 'par', 'sans', 'sous', 'entre', 'chez', 'dont', 'que', 'qui', 'où', 'quand', 'comment', 'pourquoi', 'trop', 'généreuse', 'puerpérales', 'cultivés', 'marais', 'saison', 'sèche', 'corde', 'soufflet', 'bâtonnets']
    
    # Kinyarwanda indicators (common patterns)
    kinyarwanda_patterns = ['mu ', 'ku ', 'ni ', 'na ', 'cya', 'rya', 'rwa', 'kwa', 'twa', 'bwa', 'gwa', 'hwa', 'mwa', 'nwa', 'pwa', 'rwa', 'swa', 'twa', 'vwa', 'wya', 'zya']
    
    english_score = sum(1 for word in english_words if word in text_lower)
    french_score = sum(1 for word in french_words if word in text_lower)
    kinyarwanda_score = sum(1 for pattern in kinyarwanda_patterns if pattern in text_lower)
    
    if english_score > french_score and english_score > kinyarwanda_score:
        return 'english'
    elif french_score > kinyarwanda_score:
        return 'french'
    else:
        return 'kinyarwanda'

def standardize_meanings():
    """Standardize all meanings to [Kinyarwanda, French, English] order"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Starting meaning standardization...")
            
            # Get all words with meanings
            words = WordsData.query.filter(WordsData.igisobanuro_meaning.isnot(None)).all()
            print(f"Found {len(words)} words with meanings")
            
            updated_count = 0
            
            for word in words:
                try:
                    meanings = word.igisobanuro_meaning
                    
                    if not meanings:
                        continue
                    
                    # Handle different data structures
                    if isinstance(meanings, str):
                        try:
                            meanings = json.loads(meanings)
                        except:
                            continue
                    
                    if not isinstance(meanings, list) or len(meanings) == 0:
                        continue
                    
                    # Flatten nested structures
                    flat_meanings = []
                    for item in meanings:
                        if isinstance(item, list):
                            flat_meanings.extend(item)
                        else:
                            flat_meanings.append(item)
                    
                    if len(flat_meanings) < 2:
                        continue
                    
                    # Detect language for each meaning
                    detected = []
                    for meaning in flat_meanings:
                        if isinstance(meaning, str):
                            lang = detect_language(meaning)
                            detected.append((meaning, lang))
                    
                    # Group by language
                    kinyarwanda = [m for m, l in detected if l == 'kinyarwanda']
                    french = [m for m, l in detected if l == 'french']
                    english = [m for m, l in detected if l == 'english']
                    
                    # Create standardized order: [Kinyarwanda, French, English]
                    standardized = []
                    
                    # Add Kinyarwanda (first available)
                    if kinyarwanda:
                        standardized.append(kinyarwanda[0])
                    elif french:
                        standardized.append(french[0])  # Fallback
                    elif english:
                        standardized.append(english[0])  # Fallback
                    
                    # Add French (second)
                    if french and len(standardized) < 2:
                        standardized.append(french[0])
                    elif english and len(standardized) < 2:
                        standardized.append(english[0])  # Fallback
                    
                    # Add English (third)
                    if english and len(standardized) < 3:
                        standardized.append(english[0])
                    elif french and len(standardized) < 3:
                        standardized.append(french[0])  # Fallback
                    
                    # Only update if we have at least 2 meanings and they're different from original
                    if len(standardized) >= 2 and standardized != flat_meanings:
                        word.igisobanuro_meaning = standardized
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            print(f"Updated {updated_count} words...")
                
                except Exception as e:
                    print(f"Error processing word {word.word}: {e}")
                    continue
            
            # Commit all changes
            db.session.commit()
            print(f"✅ Standardization complete! Updated {updated_count} words")
            
        except Exception as e:
            print(f"❌ Error in standardization: {e}")
            db.session.rollback()

if __name__ == "__main__":
    standardize_meanings()
