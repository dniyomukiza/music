#!/usr/bin/env python3
"""
Test script for the enhanced picture game with English text overlays
"""

import os
import sys
import json
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db, PictureGameItem, WordsData

def test_enhanced_picture_game():
    """Test the enhanced picture game functionality"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🎮 Testing Enhanced Picture Game with English Text Overlays")
            print("=" * 60)
            
            # Check if we have any picture game items
            items = PictureGameItem.query.filter(PictureGameItem.is_active == True).limit(5).all()
            
            if not items:
                print("❌ No picture game items found. Run generate_daily_pictures.py first.")
                return
            
            print(f"✅ Found {len(items)} picture game items")
            print()
            
            # Display sample items with their enhanced metadata
            for i, item in enumerate(items, 1):
                print(f"📸 Item {i}: {item.kinyarwanda_word}")
                print(f"   English: {item.english_meaning}")
                print(f"   Image: {item.image_filename}")
                print(f"   Type: {item.image_type}")
                
                # Parse text overlay data
                if item.text_overlay_data:
                    try:
                        overlay_data = json.loads(item.text_overlay_data)
                        print(f"   Text Overlay: {overlay_data}")
                    except:
                        print(f"   Text Overlay: {item.text_overlay_data}")
                
                print(f"   Used: {item.used_count} times")
                print(f"   Created: {item.created_at}")
                print()
            
            # Test the API response format
            print("🔍 Testing API Response Format:")
            print("-" * 40)
            
            # Simulate the API response creation
            game_data = []
            for item in items[:3]:  # Test with first 3 items
                text_overlay_data = {}
                if item.text_overlay_data:
                    try:
                        text_overlay_data = json.loads(item.text_overlay_data)
                    except:
                        text_overlay_data = {}
                
                image_data = {
                    'type': 'stored_image',
                    'image_url': f"/static/pictures/{item.image_filename}",
                    'description': item.english_meaning,
                    'is_noun': True,
                    'image_type': item.image_type or 'text_overlay',
                    'text_overlay': {
                        'english_meaning': text_overlay_data.get('english_meaning', item.english_meaning),
                        'text_position': text_overlay_data.get('text_position', 'bottom_overlay'),
                        'text_type': text_overlay_data.get('text_type', 'english_only'),
                        'font_size': text_overlay_data.get('font_size', 'medium')
                    },
                    'pronunciation_guide': item.pronunciation_guide,
                    'context_hint': item.context_hint
                }
                
                game_data.append({
                    'id': item.id,
                    'word': item.kinyarwanda_word,
                    'meaning': item.english_meaning,
                    'image': image_data,
                    'part_of_speech': 'noun'
                })
            
            # Display the API response
            api_response = {
                'success': True,
                'game_data': game_data,
                'source': 'pre_generated'
            }
            
            print(json.dumps(api_response, indent=2, default=str))
            print()
            
            print("✅ Enhanced Picture Game Test Completed!")
            print()
            print("🎯 Key Features:")
            print("   • Images show only English translation overlays")
            print("   • Clean, focused design for better matching")
            print("   • Text positioned at bottom of images")
            print("   • Enhanced metadata for future features")
            print()
            print("🚀 Next Steps:")
            print("   1. Run: python generate_daily_pictures.py")
            print("   2. Test the picture game in the web interface")
            print("   3. Images will now show English hints for easier matching")
            
        except Exception as e:
            print(f"❌ Error testing enhanced picture game: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_enhanced_picture_game()
