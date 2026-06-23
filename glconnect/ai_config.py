"""
AI Configuration for Ink Studio
Configuration settings for AI integration
"""

import os
from typing import Dict, List, Optional

class AIConfig:
    """AI configuration settings"""
    
    # Gemini Configuration (text model — change here if you need a different ID)
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = "gemini-2.5-flash"
    GEMINI_MAX_TOKENS = int(os.getenv('GEMINI_MAX_TOKENS', '1000'))
    GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.7'))
    
    # AI Features Configuration
    AI_FEATURES = {
        'content_generation': {
            'enabled': True,
            'max_tokens': 1000,
            'temperature': 0.7,
            'models': ['gpt-4', 'gpt-3.5-turbo']
        },
        'text_improvement': {
            'enabled': True,
            'max_tokens': 800,
            'temperature': 0.5,
            'improvement_types': [
                'general', 'grammar', 'style', 'clarity',
                'description', 'flow'
            ]
        },
        'author_review': {
            'enabled': True,
            'max_tokens': 2000,
            'temperature': 0.3,
            'categories': [
                'grammar_punctuation',
                'spelling',
                'linguistic_errors',
                'plot_continuity',
                'pacing_tension',
                'narrative_style',
            ],
        },
        'text_analysis': {
            'enabled': True,
            'max_tokens': 600,
            'temperature': 0.3,
            'analysis_types': [
                'plot_continuity', 'pacing_tension', 'narrative_style',
                'readability', 'character_development'
            ]
        },
        'proofreading': {
            'enabled': True,
            'max_tokens': 1000,
            'temperature': 0.2,
            'check_types': [
                'grammar_punctuation', 'spelling', 'linguistic_errors',
                'punctuation', 'sentence_structure'
            ]
        },
        'idea_generation': {
            'enabled': True,
            'max_tokens': 800,
            'temperature': 0.8,
            'genres': [
                'fiction', 'non-fiction', 'mystery', 'romance',
                'sci-fi', 'fantasy', 'thriller', 'biography',
                'self-help', 'business', 'history'
            ]
        }
    }
    
    # Rate Limiting
    RATE_LIMITS = {
        'requests_per_minute': 60,
        'requests_per_hour': 1000,
        'tokens_per_minute': 40000,
        'tokens_per_hour': 200000
    }
    
    # User Preferences
    DEFAULT_USER_PREFERENCES = {
        'ai_enabled': True,
        'auto_suggestions': False,
        'auto_proofread': False,
        'preferred_style': 'professional',
        'writing_goals': [],
        'excluded_features': []
    }
    
    # Content Guidelines
    CONTENT_GUIDELINES = {
        'max_content_length': 10000,
        'min_content_length': 10,
        'forbidden_topics': [
            'explicit_violence', 'hate_speech', 'illegal_activities',
            'harmful_content', 'misinformation'
        ],
        'content_filters': True,
        'safety_checks': True
    }
    
    # Integration Settings
    INTEGRATION_SETTINGS = {
        'auto_save_ai_content': False,
        'ai_content_attribution': True,
        'collaborative_ai': True,
        'ai_suggestions_frequency': 'on_demand',
        'real_time_assistance': False
    }
    
    @classmethod
    def get_feature_config(cls, feature_name: str) -> Dict:
        """Get configuration for a specific AI feature"""
        return cls.AI_FEATURES.get(feature_name, {})
    
    @classmethod
    def is_feature_enabled(cls, feature_name: str) -> bool:
        """Check if an AI feature is enabled"""
        feature_config = cls.get_feature_config(feature_name)
        return feature_config.get('enabled', False)
    
    @classmethod
    def get_model_settings(cls, feature_name: str) -> Dict:
        """Get model settings for a specific feature"""
        feature_config = cls.get_feature_config(feature_name)
        return {
            'model': cls.GEMINI_MODEL,
            'max_tokens': feature_config.get('max_tokens', cls.GEMINI_MAX_TOKENS),
            'temperature': feature_config.get('temperature', cls.GEMINI_TEMPERATURE)
        }
    
    @classmethod
    def validate_api_key(cls) -> bool:
        """Validate Gemini API key"""
        return bool(cls.GEMINI_API_KEY and len(cls.GEMINI_API_KEY) > 10)
    
    @classmethod
    def get_user_limits(cls, user_id: int) -> Dict:
        """Get AI usage limits for a user"""
        # This could be extended to check user subscription level, etc.
        return {
            'daily_requests': 100,
            'monthly_requests': 2000,
            'max_tokens_per_request': 2000,
            'premium_features': False
        }

# AI Prompt Templates
class AIPrompts:
    """Predefined prompt templates for AI features"""
    
    CONTENT_GENERATION = {
        'story_continuation': """Continue this story in a compelling way that maintains the established tone and style:

{context}

Continue from: "{text}"

Guidelines:
- Maintain character consistency
- Advance the plot naturally
- Keep the same writing style
- End at a natural stopping point""",
        
        'character_description': """Create a vivid character description for:

Character: {character_name}
Role: {character_role}
Setting: {setting}

Include:
- Physical appearance
- Personality traits
- Background
- Motivations
- Unique characteristics""",
        
        'scene_setting': """Describe a detailed scene setting for:

Location: {location}
Time: {time_period}
Mood: {mood}
Genre: {genre}

Include:
- Visual details
- Sensory elements
- Atmosphere
- Relevant objects
- Environmental factors"""
    }
    
    TEXT_IMPROVEMENT = {
        'general': """Improve this text for clarity, flow, and engagement while maintaining the original meaning and style:

{text}

Focus on:
- Sentence structure
- Word choice
- Flow and transitions
- Clarity and precision
- Engaging language""",
        
        'dialogue': """Improve this dialogue to make it more natural, engaging, and character-appropriate:

{text}

Consider:
- Natural speech patterns
- Character voice
- Subtext and implications
- Realistic conversation flow
- Emotional authenticity""",
        
        'description': """Enhance this description to make it more vivid and immersive:

{text}

Improve:
- Sensory details
- Specific imagery
- Emotional impact
- Reader engagement
- Visual clarity"""
    }
    
    AUTHOR_REVIEW = {
        'grammar_punctuation': """Fix grammar and punctuation only. Preserve voice and meaning. Return only the corrected passage:

{text}""",
        'spelling': """Correct misspellings and typos only. Do not change grammar or wording unless required by the typo:

{text}""",
        'linguistic_errors': """List common linguistic errors (wrong words, tense shifts, agreement, modifiers) with brief fixes. Do not rewrite the whole passage:

{text}""",
        'plot_continuity': """Review plot continuity using this context:

{context}

Passage:

{text}""",
        'pacing_tension': """Analyze pacing and tension with specific, actionable notes:

{text}""",
        'narrative_style': """Assess narrative style (POV, voice, tone, show vs tell) with targeted suggestions:

{text}""",
    }
    
    ANALYSIS = {
        'writing_style': """Analyze the writing style of this text:

{text}

Evaluate:
- Tone and voice
- Sentence structure
- Word choice
- Rhythm and flow
- Overall effectiveness
- Areas for improvement""",
        
        'character_development': """Analyze the character development in this text:

{text}

Assess:
- Character consistency
- Personality traits
- Motivations
- Growth and change
- Dialogue authenticity
- Character depth""",
        
        'plot_structure': """Analyze the plot structure of this text:

{text}

Examine:
- Story progression
- Conflict and tension
- Pacing
- Plot points
- Resolution
- Overall structure"""
    }

# AI Usage Tracking
class AIUsageTracker:
    """Track AI usage for analytics and limits"""
    
    def __init__(self):
        self.usage_stats = {}
    
    def track_request(self, user_id: int, feature: str, tokens_used: int):
        """Track an AI request"""
        if user_id not in self.usage_stats:
            self.usage_stats[user_id] = {
                'daily_requests': 0,
                'monthly_requests': 0,
                'total_tokens': 0,
                'feature_usage': {}
            }
        
        stats = self.usage_stats[user_id]
        stats['daily_requests'] += 1
        stats['monthly_requests'] += 1
        stats['total_tokens'] += tokens_used
        
        if feature not in stats['feature_usage']:
            stats['feature_usage'][feature] = 0
        stats['feature_usage'][feature] += 1
    
    def get_usage_stats(self, user_id: int) -> Dict:
        """Get usage statistics for a user"""
        return self.usage_stats.get(user_id, {})
    
    def check_limits(self, user_id: int) -> Dict:
        """Check if user has exceeded limits"""
        stats = self.get_usage_stats(user_id)
        limits = AIConfig.get_user_limits(user_id)
        
        return {
            'daily_limit_exceeded': stats.get('daily_requests', 0) >= limits['daily_requests'],
            'monthly_limit_exceeded': stats.get('monthly_requests', 0) >= limits['monthly_requests'],
            'token_limit_exceeded': stats.get('total_tokens', 0) >= limits['max_tokens_per_request']
        }

# Global AI usage tracker instance
ai_usage_tracker = AIUsageTracker()
