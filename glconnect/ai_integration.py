"""
AI Integration for Book Platform
This module provides AI-powered features for writing, editing, and enhancing books
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import openai
import requests
import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

# Import models
from glconnect.models import db
from glconnect.book_platform_models import (
    BookProject, BookChapter, BookPlatformUser, BookComment
)

# Create AI blueprint
ai_bp = Blueprint('ai_features', __name__, url_prefix='/mybook/ai')

class AIWritingAssistant:
    """AI-powered writing assistant for the book platform"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def generate_content(self, prompt: str, context: str = "", max_tokens: int = 500) -> Dict:
        """Generate content based on prompt and context"""
        try:
            system_prompt = f"""You are a professional writing assistant helping authors create compelling content. 
            Context: {context}
            
            Guidelines:
            - Write in a clear, engaging style
            - Maintain consistency with the author's voice
            - Provide creative and original content
            - Focus on storytelling and character development
            - Ensure proper grammar and flow"""
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "usage": response.usage.dict() if response.usage else None
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def improve_text(self, text: str, improvement_type: str = "general") -> Dict:
        """Improve existing text based on type"""
        prompts = {
            "general": "Improve this text for clarity, flow, and engagement while maintaining the original meaning:",
            "grammar": "Fix grammar, punctuation, and sentence structure in this text:",
            "style": "Improve the writing style and make it more engaging:",
            "clarity": "Make this text clearer and easier to understand:",
            "dialogue": "Improve this dialogue to make it more natural and engaging:",
            "description": "Enhance this description to make it more vivid and immersive:"
        }
        
        prompt = prompts.get(improvement_type, prompts["general"])
        return self.generate_content(f"{prompt}\n\n{text}")
    
    def generate_ideas(self, genre: str, theme: str = "", character: str = "") -> Dict:
        """Generate creative ideas for stories"""
        prompt = f"""Generate 5 creative story ideas for a {genre} book"""
        if theme:
            prompt += f" with the theme: {theme}"
        if character:
            prompt += f" featuring a character like: {character}"
        
        prompt += """. Each idea should include:
        - A compelling hook
        - Main conflict
        - Character motivation
        - Potential plot points"""
        
        return self.generate_content(prompt, max_tokens=800)
    
    def analyze_text(self, text: str) -> Dict:
        """Analyze text for various metrics"""
        try:
            # Basic analysis
            word_count = len(text.split())
            char_count = len(text)
            sentence_count = len(re.split(r'[.!?]+', text))
            paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
            
            # Readability analysis (simplified)
            avg_words_per_sentence = word_count / sentence_count if sentence_count > 0 else 0
            
            # AI-powered analysis
            analysis_prompt = f"""Analyze this text and provide insights on:
            1. Writing style and tone
            2. Strengths and areas for improvement
            3. Character development (if applicable)
            4. Plot structure (if applicable)
            5. Overall assessment
            
            Text: {text[:1000]}..."""
            
            ai_analysis = self.generate_content(analysis_prompt, max_tokens=600)
            
            return {
                "success": True,
                "metrics": {
                    "word_count": word_count,
                    "character_count": char_count,
                    "sentence_count": sentence_count,
                    "paragraph_count": paragraph_count,
                    "avg_words_per_sentence": round(avg_words_per_sentence, 2)
                },
                "ai_analysis": ai_analysis.get("content", "") if ai_analysis.get("success") else "Analysis unavailable"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def suggest_improvements(self, text: str) -> Dict:
        """Suggest specific improvements for text"""
        prompt = f"""Review this text and suggest specific improvements. For each suggestion, provide:
        1. The specific issue
        2. Why it's a problem
        3. How to fix it
        4. An example of the improved version
        
        Text: {text}"""
        
        return self.generate_content(prompt, max_tokens=800)
    
    def generate_dialogue(self, character1: str, character2: str, context: str, mood: str = "neutral") -> Dict:
        """Generate realistic dialogue between characters"""
        prompt = f"""Write a natural dialogue between {character1} and {character2}.
        Context: {context}
        Mood: {mood}
        
        Make the dialogue:
        - Natural and realistic
        - Character-appropriate
        - Engaging and purposeful
        - Properly formatted"""
        
        return self.generate_content(prompt, max_tokens=600)
    
    def expand_scene(self, scene_description: str, target_length: int = 500) -> Dict:
        """Expand a brief scene description into detailed prose"""
        prompt = f"""Expand this scene description into detailed, engaging prose of approximately {target_length} words:
        
        Scene: {scene_description}
        
        Include:
        - Vivid descriptions
        - Character emotions and thoughts
        - Sensory details
        - Smooth transitions
        - Engaging narrative flow"""
        
        return self.generate_content(prompt, max_tokens=target_length + 100)

class AIEditor:
    """AI-powered editing assistant"""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def proofread(self, text: str) -> Dict:
        """Comprehensive proofreading"""
        prompt = f"""Proofread this text and provide corrections for:
        1. Grammar errors
        2. Spelling mistakes
        3. Punctuation issues
        4. Sentence structure problems
        5. Word choice improvements
        
        Return the corrected text and a list of changes made.
        
        Text: {text}"""
        
        return self.generate_content(prompt, max_tokens=1000)
    
    def check_consistency(self, text: str, style_guide: str = "") -> Dict:
        """Check for consistency in writing style, character names, etc."""
        prompt = f"""Check this text for consistency issues:
        1. Character name consistency
        2. Timeline consistency
        3. Style consistency
        4. Tone consistency
        5. Factual consistency
        
        Style guide: {style_guide}
        
        Text: {text}"""
        
        return self.generate_content(prompt, max_tokens=800)
    
    def suggest_alternatives(self, text: str, word_or_phrase: str) -> Dict:
        """Suggest alternative ways to express something"""
        prompt = f"""Suggest 5 alternative ways to express this phrase: "{word_or_phrase}"
        
        In the context of this text: {text}
        
        Provide alternatives that:
        - Maintain the same meaning
        - Fit the context
        - Vary in style and tone
        - Are grammatically correct"""
        
        return self.generate_content(prompt, max_tokens=600)

# Initialize AI assistants
def get_ai_assistant():
    """Get AI assistant instance"""
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        return None
    return AIWritingAssistant(api_key)

def get_ai_editor():
    """Get AI editor instance"""
    api_key = current_app.config.get('OPENAI_API_KEY')
    if not api_key:
        return None
    return AIEditor(api_key)

# AI Routes
@ai_bp.route('/generate-content', methods=['POST'])
@login_required
def generate_content():
    """Generate AI content"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        context = data.get('context', '')
        max_tokens = data.get('max_tokens', 500)
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.generate_content(prompt, context, max_tokens)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/improve-text', methods=['POST'])
@login_required
def improve_text():
    """Improve existing text"""
    try:
        data = request.get_json()
        text = data.get('text')
        improvement_type = data.get('type', 'general')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.improve_text(text, improvement_type)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/analyze-text', methods=['POST'])
@login_required
def analyze_text():
    """Analyze text for metrics and insights"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.analyze_text(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/generate-ideas', methods=['POST'])
@login_required
def generate_ideas():
    """Generate creative story ideas"""
    try:
        data = request.get_json()
        genre = data.get('genre', 'fiction')
        theme = data.get('theme', '')
        character = data.get('character', '')
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.generate_ideas(genre, theme, character)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/proofread', methods=['POST'])
@login_required
def proofread():
    """AI-powered proofreading"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        editor = get_ai_editor()
        if not editor:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = editor.proofread(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/generate-dialogue', methods=['POST'])
@login_required
def generate_dialogue():
    """Generate dialogue between characters"""
    try:
        data = request.get_json()
        character1 = data.get('character1')
        character2 = data.get('character2')
        context = data.get('context', '')
        mood = data.get('mood', 'neutral')
        
        if not character1 or not character2:
            return jsonify({'success': False, 'error': 'Both characters are required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.generate_dialogue(character1, character2, context, mood)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/expand-scene', methods=['POST'])
@login_required
def expand_scene():
    """Expand a scene description"""
    try:
        data = request.get_json()
        scene_description = data.get('scene_description')
        target_length = data.get('target_length', 500)
        
        if not scene_description:
            return jsonify({'success': False, 'error': 'Scene description is required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.expand_scene(scene_description, target_length)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ai_bp.route('/suggest-improvements', methods=['POST'])
@login_required
def suggest_improvements():
    """Suggest specific improvements"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_ai_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'AI service not configured'}), 500
        
        result = assistant.suggest_improvements(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# AI Integration with existing book platform
def integrate_ai_with_chapter(chapter_id: int, ai_feature: str, **kwargs) -> Dict:
    """Integrate AI features with existing chapter editing"""
    try:
        chapter = BookChapter.query.get_or_404(chapter_id)
        
        if ai_feature == 'analyze':
            assistant = get_ai_assistant()
            if assistant:
                result = assistant.analyze_text(chapter.content)
                return result
        
        elif ai_feature == 'improve':
            improvement_type = kwargs.get('type', 'general')
            assistant = get_ai_assistant()
            if assistant:
                result = assistant.improve_text(chapter.content, improvement_type)
                if result.get('success'):
                    # Optionally auto-update chapter content
                    # chapter.content = result['content']
                    # db.session.commit()
                    pass
                return result
        
        elif ai_feature == 'proofread':
            editor = get_ai_editor()
            if editor:
                result = editor.proofread(chapter.content)
                return result
        
        return {'success': False, 'error': 'AI feature not implemented'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# Export the blueprint
__all__ = ['ai_bp', 'AIWritingAssistant', 'AIEditor', 'integrate_ai_with_chapter']




