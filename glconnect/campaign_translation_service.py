"""
AI translation for book campaign pages so patrons can read projects in their language.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import bleach

logger = logging.getLogger(__name__)

TRANSLATION_LANGUAGE_NAMES: dict[str, str] = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese',
    'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
    'sw': 'Swahili', 'rw': 'Kinyarwanda', 'nl': 'Dutch', 'pl': 'Polish',
    'tr': 'Turkish', 'vi': 'Vietnamese', 'th': 'Thai', 'id': 'Indonesian',
    'cs': 'Czech', 'sv': 'Swedish', 'da': 'Danish', 'fi': 'Finnish',
    'no': 'Norwegian', 'he': 'Hebrew', 'uk': 'Ukrainian', 'ro': 'Romanian',
    'hu': 'Hungarian', 'el': 'Greek', 'bg': 'Bulgarian', 'hr': 'Croatian',
    'sk': 'Slovak', 'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian',
    'lt': 'Lithuanian', 'mt': 'Maltese', 'ga': 'Irish', 'cy': 'Welsh',
}


def _clean_translated_text(value: Any) -> str:
    return bleach.clean(str(value or ''), tags=[], strip=True)


def _clean_translated_html(value: Any) -> str:
    from glconnect.project_description_media import ProjectDescriptionError, sanitize_project_description

    raw = str(value or '')
    try:
        return sanitize_project_description(raw, book_id=None)
    except ProjectDescriptionError:
        logger.warning('Translated campaign HTML exceeded project description constraints; stripping tags.')
        return bleach.clean(raw, tags=[], strip=True)


def _sanitize_translation_fields(values: dict[str, Any]) -> dict[str, str]:
    return {
        'translated_title': _clean_translated_text(values.get('translated_title')),
        'translated_book_title': _clean_translated_text(values.get('translated_book_title')),
        'translated_author_bio': _clean_translated_text(values.get('translated_author_bio')),
        'translated_book_description': _clean_translated_html(values.get('translated_book_description')),
        'translated_campaign_description': _clean_translated_html(values.get('translated_campaign_description')),
        'translated_tentative_timeline': _clean_translated_text(values.get('translated_tentative_timeline')),
    }


def campaign_translation_language_choices() -> list[dict[str, str]]:
    return [
        {'code': code, 'name': name}
        for code, name in sorted(TRANSLATION_LANGUAGE_NAMES.items(), key=lambda item: item[1])
    ]


def normalize_language_code(code: str | None) -> str:
    if not code:
        return 'en'
    raw = code.strip().lower()
    if raw in TRANSLATION_LANGUAGE_NAMES:
        return raw
    short = raw.split('-')[0][:2]
    if short in TRANSLATION_LANGUAGE_NAMES:
        return short
    for lang_code, name in TRANSLATION_LANGUAGE_NAMES.items():
        if name.lower() == raw:
            return lang_code
    return 'en'


def campaign_source_language(book: Any) -> str:
    return normalize_language_code(getattr(book, 'language', None) if book else None)


def campaign_translation_context(book: Any) -> dict[str, Any]:
    source = campaign_source_language(book)
    return {
        'campaign_source_language': source,
        'campaign_source_language_name': TRANSLATION_LANGUAGE_NAMES.get(source, source.upper()),
        'campaign_translation_languages': campaign_translation_language_choices(),
    }


def _get_gemini_model():
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    except Exception as exc:
        logger.error('Gemini init failed for campaign translation: %s', exc)
        return None


def _translation_payload(record: Any) -> dict[str, str]:
    values = _sanitize_translation_fields({
        'translated_title': record.translated_title,
        'translated_book_title': record.translated_book_title,
        'translated_author_bio': record.translated_author_bio,
        'translated_book_description': record.translated_book_description,
        'translated_campaign_description': record.translated_campaign_description,
        'translated_tentative_timeline': record.translated_tentative_timeline,
    })
    return {
        'title': values['translated_title'],
        'book_title': values['translated_book_title'],
        'author_bio': values['translated_author_bio'],
        'book_description': values['translated_book_description'],
        'campaign_description': values['translated_campaign_description'],
        'tentative_timeline': values['translated_tentative_timeline'],
    }


def get_cached_campaign_translation(campaign_id: int, language: str, db: Any):
    from glconnect.book_platform_models import CampaignTranslation

    lang = normalize_language_code(language)
    return CampaignTranslation.query.filter_by(campaign_id=campaign_id, language=lang).first()


def list_campaign_translation_languages(campaign_id: int, db: Any) -> list[str]:
    from glconnect.book_platform_models import CampaignTranslation

    rows = CampaignTranslation.query.filter_by(campaign_id=campaign_id).all()
    return [row.language for row in rows]


def translate_campaign(
    campaign: Any,
    book: Any,
    author: Any,
    target_language: str,
    db: Any,
) -> dict[str, Any]:
    """Translate campaign page content; returns cached or freshly generated translation."""
    from glconnect.book_platform_models import CampaignTranslation

    lang = normalize_language_code(target_language)
    if lang not in TRANSLATION_LANGUAGE_NAMES:
        return {'success': False, 'error': 'Unsupported language'}

    source_lang = campaign_source_language(book)
    if lang == source_lang:
        return {
            'success': True,
            'language': lang,
            'source_language': source_lang,
            'cached': True,
            'is_original': True,
            'translations': {},
        }

    cached = get_cached_campaign_translation(campaign.id, lang, db)
    if cached:
        return {
            'success': True,
            'language': lang,
            'source_language': source_lang,
            'cached': True,
            'is_original': False,
            'translations': _translation_payload(cached),
        }

    model = _get_gemini_model()
    if not model:
        return {'success': False, 'error': 'Translation service is not available right now.'}

    source_name = TRANSLATION_LANGUAGE_NAMES.get(source_lang, source_lang)
    target_name = TRANSLATION_LANGUAGE_NAMES.get(lang, lang)

    author_bio = (getattr(author, 'bio', None) or '') if author else ''
    book_description = getattr(book, 'description', None) or ''
    campaign_description = getattr(campaign, 'description', None) or ''
    tentative_timeline = getattr(campaign, 'tentative_timeline', None) or ''

    prompt = f"""Translate this book campaign page from {source_name} to {target_name}.
Preserve HTML tags in description fields. Keep book and person names unless a well-known localized form exists.
Return ONLY valid JSON with these keys (use empty string when source is empty):
{{
  "translated_title": "...",
  "translated_book_title": "...",
  "translated_author_bio": "...",
  "translated_book_description": "...",
  "translated_campaign_description": "...",
  "translated_tentative_timeline": "..."
}}

Campaign title: {campaign.title}
Book title: {getattr(book, 'title', '') or ''}
Author bio: {author_bio}
About the project (HTML allowed): {book_description}
Why backing (HTML allowed): {campaign_description}
Tentative timeline: {tentative_timeline}
"""

    try:
        import google.generativeai as genai

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8000,
                temperature=0.3,
                top_p=0.8,
                top_k=40,
            ),
        )
        if not response.parts:
            return {'success': False, 'error': 'Translation failed, empty AI response'}

        raw = response.text.strip()
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            return {'success': False, 'error': 'Translation failed, could not parse response'}
    except Exception as exc:
        logger.error('Campaign translation failed for campaign %s: %s', campaign.id, exc, exc_info=True)
        return {'success': False, 'error': 'Translation failed. Please try again.'}

    sanitized = _sanitize_translation_fields({
        'translated_title': data.get('translated_title') or campaign.title,
        'translated_book_title': data.get('translated_book_title') or (getattr(book, 'title', None) or ''),
        'translated_author_bio': data.get('translated_author_bio') or author_bio,
        'translated_book_description': data.get('translated_book_description') or book_description,
        'translated_campaign_description': data.get('translated_campaign_description') or campaign_description,
        'translated_tentative_timeline': data.get('translated_tentative_timeline') or tentative_timeline,
    })

    record = CampaignTranslation(
        campaign_id=campaign.id,
        language=lang,
        translated_title=sanitized['translated_title'],
        translated_book_title=sanitized['translated_book_title'],
        translated_author_bio=sanitized['translated_author_bio'],
        translated_book_description=sanitized['translated_book_description'],
        translated_campaign_description=sanitized['translated_campaign_description'],
        translated_tentative_timeline=sanitized['translated_tentative_timeline'],
        translation_method='gemini',
    )
    db.session.add(record)
    db.session.commit()

    return {
        'success': True,
        'language': lang,
        'source_language': source_lang,
        'cached': False,
        'is_original': False,
        'translations': _translation_payload(record),
    }
