"""
Gemini AI Integration for Book Platform
Alternative AI integration using Google's Gemini instead of OpenAI
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import google.generativeai as genai
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
gemini_bp = Blueprint('gemini_ai', __name__, url_prefix='/mybook/ai')

class GeminiWritingAssistant:
    """Gemini-powered writing assistant for the book platform"""
    
    def __init__(self, api_key: str):
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            raise Exception(f"Failed to initialize Gemini model: {str(e)}")
    
    def generate_content(self, prompt: str, context: str = "", max_tokens: int = 500) -> Dict:
        """Generate content based on prompt and context"""
        try:
            full_prompt = f"""You are a professional writing assistant helping authors create compelling content. 
            Context: {context}
            
            Guidelines:
            - Write in a clear, engaging style
            - Maintain consistency with the author's voice
            - Provide creative and original content
            - Focus on storytelling and character development
            - Ensure proper grammar and flow
            
            Prompt: {prompt}"""
            
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40
                ),
                safety_settings=[
                    {
                        "category": genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                    },
                    {
                        "category": genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                    },
                    {
                        "category": genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                    },
                    {
                        "category": genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        "threshold": genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                    }
                ]
            )
            
            # Check if response has content
            if response.parts and len(response.parts) > 0:
                content = response.text
                return {
                    "success": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": len(full_prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(full_prompt.split()) + len(content.split())
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"No content generated. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def improve_text(self, text: str, improvement_type: str = "general") -> Dict:
        """Improve existing text based on type"""
        prompts = {
            "general": "As a professional writing assistant, improve this text for clarity, flow, and engagement while maintaining the original meaning and tone:",
            "grammar": "As a professional editor, fix grammar, punctuation, and sentence structure in this text:",
            "style": "As a writing coach, improve the writing style and make it more engaging:",
            "clarity": "As a communication expert, make this text clearer and easier to understand:",
            "dialogue": "As a dialogue specialist, improve this dialogue to make it more natural and engaging:",
            "description": "As a creative writing expert, enhance this description to make it more vivid and immersive:"
        }
        
        prompt = prompts.get(improvement_type, prompts["general"])
        full_prompt = f"{prompt}\n\nText to improve:\n{text}\n\nPlease provide the improved version:"
        
        try:
            print(f"DEBUG: Sending prompt to Gemini: {full_prompt[:100]}...")
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.5,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            print(f"DEBUG: Gemini response: {response}")
            print(f"DEBUG: Response parts: {response.parts}")
            print(f"DEBUG: Response text: {response.text if hasattr(response, 'text') else 'No text attribute'}")
            
            # Check if response has content
            if response.parts and len(response.parts) > 0:
                try:
                    content = response.text
                    print(f"DEBUG: Generated content: {content}")
                    return {
                        "success": True,
                        "content": content,
                        "usage": {
                            "prompt_tokens": len(full_prompt.split()),
                            "completion_tokens": len(content.split()),
                            "total_tokens": len(full_prompt.split()) + len(content.split())
                        }
                    }
                except Exception as text_error:
                    print(f"DEBUG: Error accessing response.text: {text_error}")
                    print(f"DEBUG: Response candidates: {response.candidates}")
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                        print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                    return {
                        "success": False,
                        "error": f"Error accessing response text: {str(text_error)}"
                    }
            else:
                print("DEBUG: No content generated - response.parts is empty")
                print(f"DEBUG: Response candidates: {response.candidates}")
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                    print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                return {
                    "success": False,
                    "error": f"No content generated. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                }
            
        except Exception as e:
            print(f"DEBUG: Exception in improve_text: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_ideas(self, genre: str, theme: str = "", character: str = "") -> Dict:
        """Generate creative ideas for stories"""
        prompt = f"""Write 5 story ideas for a {genre} book"""
        if theme:
            prompt += f" about {theme}"
        if character:
            prompt += f" with a character like {character}"

        prompt += """. Each idea should have a title, main character, and basic plot."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,  # Increased from 800
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40
                )
            )

            # Check if response has content
            try:
                content = response.text
                return {
                    "success": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(prompt.split()) + len(content.split())
                    }
                }
            except Exception as text_error:
                print(f"DEBUG: Error accessing response.text in generate_ideas: {text_error}")
                print(f"DEBUG: Response candidates: {response.candidates}")
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                    print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")

                    # Handle MAX_TOKENS case
                    if candidate.finish_reason == 2:  # MAX_TOKENS
                        return {
                            "success": False,
                            "error": "Response was truncated due to token limit. Please try with a shorter prompt or increase max_tokens."
                        }

                return {
                    "success": False,
                    "error": f"Error accessing response text: {str(text_error)}"
                }

        except Exception as e:
            print(f"DEBUG: Exception in generate_ideas: {e}")
            return {"success": False, "error": str(e)}
    
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
            
            # Gemini-powered analysis with simplified prompt
            analysis_prompt = f"""Analyze this text briefly:

{text[:500]}

Analysis:"""
            
            ai_analysis = self.model.generate_content(
                analysis_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Check if response has content
            if ai_analysis.parts and len(ai_analysis.parts) > 0:
                try:
                    analysis_content = ai_analysis.text
                    return {
                        "success": True,
                        "metrics": {
                            "word_count": word_count,
                            "character_count": char_count,
                            "sentence_count": sentence_count,
                            "paragraph_count": paragraph_count,
                            "avg_words_per_sentence": round(avg_words_per_sentence, 2)
                        },
                        "ai_analysis": analysis_content,
                        "usage": {
                            "prompt_tokens": len(analysis_prompt.split()),
                            "completion_tokens": len(analysis_content.split()),
                            "total_tokens": len(analysis_prompt.split()) + len(analysis_content.split())
                        }
                    }
                except Exception as text_error:
                    print(f"DEBUG: Error accessing response.text in analyze_text: {text_error}")
                    print(f"DEBUG: Response candidates: {ai_analysis.candidates}")
                    if ai_analysis.candidates and len(ai_analysis.candidates) > 0:
                        candidate = ai_analysis.candidates[0]
                        print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                        print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                    return {
                        "success": False,
                        "error": f"Error accessing response text: {str(text_error)}"
                    }
            else:
                print("DEBUG: No content generated in analyze_text - response.parts is empty")
                print(f"DEBUG: Response candidates: {ai_analysis.candidates}")
                if ai_analysis.candidates and len(ai_analysis.candidates) > 0:
                    candidate = ai_analysis.candidates[0]
                    print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                    print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                return {
                    "success": False,
                    "error": f"No content generated. Finish reason: {ai_analysis.candidates[0].finish_reason if ai_analysis.candidates else 'Unknown'}"
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def proofread(self, text: str) -> Dict:
        """Comprehensive proofreading"""
        prompt = f"""Proofread and correct this text. Return only the corrected version:

{text}

Corrected text:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.2,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Check if response has content
            if response.parts and len(response.parts) > 0:
                try:
                    content = response.text
                    return {
                        "success": True,
                        "content": content,
                        "usage": {
                            "prompt_tokens": len(prompt.split()),
                            "completion_tokens": len(content.split()),
                            "total_tokens": len(prompt.split()) + len(content.split())
                        }
                    }
                except Exception as text_error:
                    print(f"DEBUG: Error accessing response.text in proofread: {text_error}")
                    print(f"DEBUG: Response candidates: {response.candidates}")
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                        print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                    return {
                        "success": False,
                        "error": f"Error accessing response text: {str(text_error)}"
                    }
            else:
                print("DEBUG: No content generated in proofread - response.parts is empty")
                print(f"DEBUG: Response candidates: {response.candidates}")
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                    print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                return {
                    "success": False,
                    "error": f"No content generated. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                }
            
        except Exception as e:
            print(f"DEBUG: Exception in proofread: {e}")
            return {"success": False, "error": str(e)}
    
    def suggest_improvements(self, text: str) -> Dict:
        """Suggest specific improvements for text"""
        prompt = f"""Suggest improvements for this text. Be specific and concise:

{text}

Suggestions:"""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=0.5,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            # Check if response has content
            if response.parts and len(response.parts) > 0:
                try:
                    content = response.text
                    return {
                        "success": True,
                        "content": content,
                        "usage": {
                            "prompt_tokens": len(prompt.split()),
                            "completion_tokens": len(content.split()),
                            "total_tokens": len(prompt.split()) + len(content.split())
                        }
                    }
                except Exception as text_error:
                    print(f"DEBUG: Error accessing response.text in suggest_improvements: {text_error}")
                    print(f"DEBUG: Response candidates: {response.candidates}")
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                        print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                    return {
                        "success": False,
                        "error": f"Error accessing response text: {str(text_error)}"
                    }
            else:
                print("DEBUG: No content generated in suggest_improvements - response.parts is empty")
                print(f"DEBUG: Response candidates: {response.candidates}")
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    print(f"DEBUG: Candidate finish reason: {candidate.finish_reason}")
                    print(f"DEBUG: Candidate safety ratings: {candidate.safety_ratings}")
                return {
                    "success": False,
                    "error": f"No content generated. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'Unknown'}"
                }
            
        except Exception as e:
            print(f"DEBUG: Exception in suggest_improvements: {e}")
            return {"success": False, "error": str(e)}

# Initialize Gemini assistant
def get_gemini_assistant():
    """Get Gemini assistant instance"""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        return None
    return GeminiWritingAssistant(api_key)

# Gemini Routes (same endpoints as OpenAI version)
@gemini_bp.route('/status')
def ai_status():
    """Check AI assistant status"""
    try:
        api_key = current_app.config.get('GEMINI_API_KEY')
        
        if not api_key:
            return jsonify({
                'enabled': False,
                'provider': 'Gemini',
                'error': 'API key not configured'
            })
        
        # Test API key by creating a simple assistant instance
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({
                'enabled': False,
                'provider': 'Gemini',
                'error': 'Failed to initialize Gemini assistant'
            })
        
        return jsonify({
            'enabled': True,
            'provider': 'AI Assistant',
            'model': 'gemini-2.5-flash',
            'features': {
                'content_generation': True,
                'text_improvement': True,
                'text_analysis': True,
                'proofreading': True,
                'idea_generation': True,
                'dialogue_generation': True,
                'scene_expansion': True,
                'suggestions': True
            }
        })
        
    except Exception as e:
        return jsonify({
            'enabled': False,
            'provider': 'Gemini',
            'error': str(e)
        })

@gemini_bp.route('/generate-content', methods=['POST'])
@login_required
def generate_content():
    """Generate AI content using Gemini"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        context = data.get('context', '')
        max_tokens = data.get('max_tokens', 500)
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400
        
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500
        
        result = assistant.generate_content(prompt, context, max_tokens)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/improve-text', methods=['POST'])
@login_required
def improve_text():
    """Improve existing text using Gemini"""
    try:
        data = request.get_json()
        text = data.get('text')
        improvement_type = data.get('type', 'general')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500
        
        result = assistant.improve_text(text, improvement_type)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/analyze-text', methods=['POST'])
@login_required
def analyze_text():
    """Analyze text for metrics and insights using Gemini"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500
        
        result = assistant.analyze_text(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/generate-ideas', methods=['POST'])
@login_required
def generate_ideas():
    """Generate creative story ideas using Gemini"""
    try:
        data = request.get_json()
        theme = data.get('theme', '')

        if not theme:
            return jsonify({'success': False, 'error': 'Theme is required'}), 400

        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500

        result = assistant.generate_ideas('fiction', theme, '')
        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/proofread', methods=['POST'])
@login_required
def proofread():
    """AI-powered proofreading using Gemini"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500
        
        result = assistant.proofread(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gemini_bp.route('/suggest-improvements', methods=['POST'])
@login_required
def suggest_improvements():
    """Suggest specific improvements using Gemini"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({'success': False, 'error': 'Text is required'}), 400
        
        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({'success': False, 'error': 'Gemini AI service not configured'}), 500
        
        result = assistant.suggest_improvements(text)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Export the blueprint
__all__ = ['gemini_bp', 'GeminiWritingAssistant']

