#!/usr/bin/env python3
"""
Migration script to add enhanced fields to picture_game_items table
"""

import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from glconnect import create_app
from glconnect.models import db

def add_enhanced_fields():
    """Add enhanced fields to picture_game_items table"""
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 Adding enhanced fields to picture_game_items table...")
            
            # Add new columns to the existing table
            db.engine.execute("""
                ALTER TABLE picture_game_items 
                ADD COLUMN IF NOT EXISTS image_type VARCHAR(50) DEFAULT 'text_overlay'
            """)
            
            db.engine.execute("""
                ALTER TABLE picture_game_items 
                ADD COLUMN IF NOT EXISTS pronunciation_guide VARCHAR(255)
            """)
            
            db.engine.execute("""
                ALTER TABLE picture_game_items 
                ADD COLUMN IF NOT EXISTS context_hint TEXT
            """)
            
            db.engine.execute("""
                ALTER TABLE picture_game_items 
                ADD COLUMN IF NOT EXISTS text_overlay_data TEXT
            """)
            
            db.engine.execute("""
                ALTER TABLE picture_game_items 
                ADD COLUMN IF NOT EXISTS generation_prompt TEXT
            """)
            
            print("✅ Enhanced fields added successfully!")
            print()
            print("📋 New fields added:")
            print("   • image_type: Type of image (text_overlay, simple, enhanced)")
            print("   • pronunciation_guide: Optional pronunciation hint")
            print("   • context_hint: Optional context or usage hint")
            print("   • text_overlay_data: JSON data about text positioning")
            print("   • generation_prompt: Store the prompt used for generation")
            
        except Exception as e:
            print(f"❌ Error adding enhanced fields: {str(e)}")
            print("Note: Some fields might already exist. This is normal if you've run this before.")

if __name__ == "__main__":
    add_enhanced_fields()
