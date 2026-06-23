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

AUTHOR_REVIEW_CATEGORIES = {
    "grammar_punctuation": {
        "mode": "correct",
        "label": "Grammar & punctuation",
        "instruction": (
            "You are a professional copy editor. Fix grammar and punctuation only in the passage below. "
            "Preserve the author's voice, word choice, and meaning. Do not rewrite for style or clarity "
            "unless a change is required for grammatical correctness. Return only the corrected passage."
        ),
    },
    "spelling": {
        "mode": "correct",
        "label": "Spelling",
        "instruction": (
            "You are a proofreader. Correct misspellings and obvious typos only. "
            "Do not change grammar, punctuation, wording, or sentence structure unless a typo cannot be "
            "fixed without it. Return only the corrected passage."
        ),
    },
    "linguistic_errors": {
        "mode": "feedback",
        "label": "Common linguistic errors",
        "instruction": (
            "You are a copy editor helping an author. Review the passage for common linguistic errors such as "
            "wrong-word usage (e.g. affect/effect), tense shifts, subject-verb disagreement, pronoun ambiguity, "
            "dangling or misplaced modifiers, redundant phrasing, and awkward idioms. "
            "For each issue: quote the problematic phrase, explain the error briefly, and give a concrete fix. "
            "If no issues are found, say so clearly. Do not rewrite the whole passage."
        ),
    },
    "plot_continuity": {
        "mode": "feedback",
        "label": "Plot continuity",
        "instruction": (
            "You are a developmental editor focused on continuity. Using the manuscript context provided "
            "(book title, section title, and any summary notes), check the passage for plot and story continuity "
            "issues: timeline contradictions, character knowledge or motivation gaps, inconsistent names or details, "
            "geography or setting slips, and events that contradict earlier setup. "
            "Cite specific lines or phrases. Rate severity (minor / moderate / major) for each finding. "
            "If context is limited, note assumptions and still flag internal inconsistencies within the passage."
        ),
    },
    "pacing_tension": {
        "mode": "feedback",
        "label": "Pacing & tension",
        "instruction": (
            "You are a fiction coach analyzing pacing and tension. Evaluate how the passage builds and releases "
            "tension, scene rhythm, hook strength, stakes clarity, and whether beats land too fast or drag. "
            "Give specific, actionable notes tied to sentences or paragraphs. "
            "Suggest one or two high-impact revisions without rewriting the full text."
        ),
    },
    "narrative_style": {
        "mode": "feedback",
        "label": "Narrative style",
        "instruction": (
            "You are a writing coach focused on narrative style. Assess point of view consistency, tone, voice, "
            "sentence rhythm, show-vs-tell balance, and whether the prose fits the apparent genre. "
            "Highlight what works and what feels uneven. Give targeted suggestions; do not rewrite the entire passage."
        ),
    },
}

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
            
            analysis_prompt = f"""You are an editorial coach for authors. Analyze this passage for readability,
pacing, tone, and structure. Note strengths and give 3–5 specific improvement suggestions.

{text[:4000]}

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
    
    def author_review(self, text: str, category: str, context: str = "") -> Dict:
        """Focused author review: copy edits or craft feedback by category."""
        meta = AUTHOR_REVIEW_CATEGORIES.get(category)
        if not meta:
            return {"success": False, "error": f"Unknown review category: {category}"}

        context_block = ""
        if context.strip():
            context_block = f"\nManuscript context:\n{context.strip()}\n"

        prompt = (
            f"{meta['instruction']}\n"
            f"{context_block}\n"
            f"Passage to review:\n{text}\n"
        )
        if meta["mode"] == "correct":
            prompt += "\nCorrected passage:"
        else:
            prompt += "\nEditorial notes:"

        temperature = 0.2 if meta["mode"] == "correct" else 0.4
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2000,
                    temperature=temperature,
                    top_p=0.8,
                    top_k=40,
                ),
            )
            if response.parts and len(response.parts) > 0:
                content = response.text
                return {
                    "success": True,
                    "content": content,
                    "category": category,
                    "review_mode": meta["mode"],
                    "label": meta["label"],
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(prompt.split()) + len(content.split()),
                    },
                }
            finish = (
                response.candidates[0].finish_reason
                if response.candidates
                else "Unknown"
            )
            return {"success": False, "error": f"No content generated (finish: {finish})"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def proofread(self, text: str) -> Dict:
        """Comprehensive proofreading (grammar, spelling, punctuation)"""
        prompt = f"""You are a professional proofreader for fiction and nonfiction manuscripts.
Correct grammar, spelling, and punctuation while preserving the author's voice and meaning.
Return only the corrected passage — no commentary.

{text}

Corrected passage:"""
        
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
        prompt = f"""You are a developmental editor. Suggest concrete improvements for this passage covering
grammar, clarity, pacing, and narrative style. Use a numbered checklist; quote short phrases where helpful.
Do not rewrite the full passage.

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

    def chat(self, message: str, history: Optional[List[Dict]] = None) -> Dict:
        """Open-ended chat — general questions, not tied to the current book."""
        message = (message or "").strip()
        if not message:
            return {"success": False, "error": "Message is required"}

        history = history or []
        gemini_history = []
        for turn in history[-24:]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                gemini_history.append({"role": "user", "parts": [content]})
            elif role in ("assistant", "model"):
                gemini_history.append({"role": "model", "parts": [content]})

        system_instruction = (
            "You are a friendly, knowledgeable writing assistant in Ink Studio, a platform for authors. "
            "Help with craft questions: grammar and punctuation, spelling, common linguistic errors, "
            "plot continuity, pacing and tension, and narrative style — plus research, brainstorming, "
            "publishing, and general topics. Answer clearly and helpfully. "
            "For passage-level edits on their manuscript, suggest the dedicated Writing tools: "
            "Grammar & punctuation, Spelling, Linguistic errors, Plot continuity, Pacing & tension, "
            "and Narrative style."
        )

        try:
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=system_instruction,
            )
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(
                message,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=2048,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=40,
                ),
            )
            if response.parts and len(response.parts) > 0:
                content = response.text
                return {"success": True, "content": content}
            finish = (
                response.candidates[0].finish_reason
                if response.candidates
                else "Unknown"
            )
            return {"success": False, "error": f"No reply generated (finish: {finish})"}
        except Exception as e:
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
                'author_review': True,
                'author_review_categories': list(AUTHOR_REVIEW_CATEGORIES.keys()),
                'suggestions': True,
                'chat': True,
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

@gemini_bp.route('/author-review', methods=['POST'])
@login_required
def author_review():
    """Category-focused author review (copy edit or craft feedback)."""
    try:
        data = request.get_json() or {}
        text = data.get("text")
        category = data.get("category", "")
        context = data.get("context", "")

        if not text:
            return jsonify({"success": False, "error": "Text is required"}), 400
        if category not in AUTHOR_REVIEW_CATEGORIES:
            return jsonify({"success": False, "error": "Invalid review category"}), 400

        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({"success": False, "error": "Gemini AI service not configured"}), 500

        result = assistant.author_review(text, category, context)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

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

@gemini_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """General-purpose chat (not limited to the current book)."""
    try:
        data = request.get_json() or {}
        message = data.get("message")
        history = data.get("history") or []

        if not message or not str(message).strip():
            return jsonify({"success": False, "error": "Message is required"}), 400

        if not isinstance(history, list):
            history = []

        assistant = get_gemini_assistant()
        if not assistant:
            return jsonify({"success": False, "error": "Gemini AI service not configured"}), 500

        result = assistant.chat(str(message).strip(), history)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Export the blueprint
__all__ = ['gemini_bp', 'GeminiWritingAssistant']

