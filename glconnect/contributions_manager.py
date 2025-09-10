"""
Word Contributions Manager
Handles approved word contributions stored in JSON format
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class ContributionsManager:
    def __init__(self, file_path: str = "glconnect/static/data/word_contributions.json"):
        self.file_path = file_path
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """Ensure the contributions file exists with proper structure"""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        if not os.path.exists(self.file_path):
            initial_data = {
                "contributions": [],
                "metadata": {
                    "version": "1.0",
                    "created": datetime.now(timezone.utc).isoformat(),
                    "description": "Approved word contributions from users",
                    "total_contributions": 0
                }
            }
            self.save_data(initial_data)
    
    def load_data(self) -> Dict[str, Any]:
        """Load contributions data from JSON file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading contributions file: {e}")
            return {"contributions": [], "metadata": {"total_contributions": 0}}
    
    def save_data(self, data: Dict[str, Any]):
        """Save contributions data to JSON file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving contributions file: {e}")
            raise
    
    def add_contribution(self, word_data: Dict[str, Any]) -> bool:
        """Add a new approved contribution to the JSON file"""
        try:
            data = self.load_data()
            
            # Add contribution with metadata
            contribution = {
                "id": len(data["contributions"]) + 1,
                "word": word_data.get("word", ""),
                "meaning": word_data.get("meaning", ""),
                "example_sentence": word_data.get("example_sentence", ""),
                "part_of_speech": word_data.get("part_of_speech", ""),
                "phonetics": word_data.get("phonetics", ""),
                "contributor_name": word_data.get("contributor_name", "Anonymous"),
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "approved_by": word_data.get("approved_by", "Admin")
            }
            
            data["contributions"].append(contribution)
            data["metadata"]["total_contributions"] = len(data["contributions"])
            data["metadata"]["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            self.save_data(data)
            return True
            
        except Exception as e:
            print(f"Error adding contribution: {e}")
            return False
    
    def get_all_contributions(self) -> List[Dict[str, Any]]:
        """Get all approved contributions"""
        data = self.load_data()
        return data.get("contributions", [])
    
    def get_contribution_by_id(self, contribution_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific contribution by ID"""
        contributions = self.get_all_contributions()
        for contrib in contributions:
            if contrib.get("id") == contribution_id:
                return contrib
        return None
    
    def get_contributions_for_game(self, limit: int = 6) -> List[Dict[str, Any]]:
        """Get random contributions suitable for the game"""
        import random
        contributions = self.get_all_contributions()
        
        if len(contributions) < limit:
            return contributions
        
        return random.sample(contributions, limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get contribution statistics"""
        data = self.load_data()
        contributions = data.get("contributions", [])
        
        return {
            "total_contributions": len(contributions),
            "last_updated": data.get("metadata", {}).get("last_updated"),
            "version": data.get("metadata", {}).get("version", "1.0")
        }
    
    def search_contributions(self, query: str) -> List[Dict[str, Any]]:
        """Search contributions by word or meaning"""
        contributions = self.get_all_contributions()
        query_lower = query.lower()
        
        results = []
        for contrib in contributions:
            if (query_lower in contrib.get("word", "").lower() or 
                query_lower in contrib.get("meaning", "").lower()):
                results.append(contrib)
        
        return results

# Global instance
contributions_manager = ContributionsManager()

