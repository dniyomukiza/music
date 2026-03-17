"""
Community Dictionary Manager
Handles community-contributed words in a separate dictionary file
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class CommunityDictionaryManager:
    def __init__(self, file_path: str = "glconnect/static/data/community_dictionary.json"):
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """Ensure the community dictionary file exists with proper structure"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        if not os.path.exists(self.file_path):
            initial_data = {
                "dictionary": [],
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "description": "Community-contributed Kinyarwanda dictionary",
                    "total_words": 0,
                    "last_updated": None
                }
            }
            self.save_data(initial_data)
    
    def load_data(self) -> Dict[str, Any]:
        """Load community dictionary data from JSON file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading community dictionary file: {e}")
            return {"dictionary": [], "metadata": {"total_words": 0}}
    
    def save_data(self, data: Dict[str, Any]):
        """Save community dictionary data to JSON file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving community dictionary file: {e}")
            raise
    
    def add_word(self, word_data: Dict[str, Any]) -> bool:
        """Add a new word to the community dictionary"""
        try:
            data = self.load_data()
            
            # Check if word already exists
            existing_words = [word['word'] for word in data['dictionary']]
            if word_data.get('word', '').lower() in [w.lower() for w in existing_words]:
                return False  # Word already exists
            
            # Add word with metadata
            word_entry = {
                "id": len(data["dictionary"]) + 1,
                "word": word_data.get("word", ""),
                "meaning": word_data.get("meaning", ""),
                "example_sentence": word_data.get("example_sentence", ""),
                "part_of_speech": word_data.get("part_of_speech", ""),
                "phonetics": word_data.get("phonetics", ""),
                "contributor_name": word_data.get("contributor_name", "Anonymous"),
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "approved_by": word_data.get("approved_by", "Admin")
            }
            
            data["dictionary"].append(word_entry)
            data["metadata"]["total_words"] = len(data["dictionary"])
            data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            self.save_data(data)
            return True
            
        except Exception as e:
            print(f"Error adding word to community dictionary: {e}")
            return False
    
    def get_all_words(self) -> List[Dict[str, Any]]:
        """Get all words from the community dictionary"""
        data = self.load_data()
        return data.get("dictionary", [])
    
    def get_word_by_id(self, word_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific word by ID"""
        words = self.get_all_words()
        for word in words:
            if word.get("id") == word_id:
                return word
        return None
    
    def search_words(self, query: str) -> List[Dict[str, Any]]:
        """Search words by word or meaning"""
        words = self.get_all_words()
        query_lower = query.lower()
        
        results = []
        for word in words:
            if (query_lower in word.get("word", "").lower() or 
                query_lower in word.get("meaning", "").lower()):
                results.append(word)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get community dictionary statistics"""
        data = self.load_data()
        words = data.get("dictionary", [])
        
        return {
            "total_words": len(words),
            "last_updated": data.get("metadata", {}).get("last_updated"),
            "version": data.get("metadata", {}).get("version", "1.0"),
            "created": data.get("metadata", {}).get("created")
        }
    
    def get_words_by_contributor(self, contributor_name: str) -> List[Dict[str, Any]]:
        """Get all words contributed by a specific person"""
        words = self.get_all_words()
        return [word for word in words if word.get("contributor_name", "").lower() == contributor_name.lower()]
    
    def get_recent_words(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recently added words"""
        words = self.get_all_words()
        # Sort by approved_at date (most recent first)
        sorted_words = sorted(words, key=lambda x: x.get("approved_at", ""), reverse=True)
        return sorted_words[:limit]

# Global instance
community_dictionary_manager = CommunityDictionaryManager()

