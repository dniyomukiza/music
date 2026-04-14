"""
Languages supported for uploaded ebooks: TTS voice defaults and translation targets.

Only languages listed here appear on the list-ebook form so audiobook voice selection
and optional AI-translated editions stay aligned with Google Cloud TTS coverage.
"""

from typing import Dict, List, Tuple

# ISO 639-1 (or BCP-47 where needed) -> (human label, default Neural2 voice name)
TTS_BOOK_LANGUAGES: Dict[str, Tuple[str, str]] = {
    "en": ("English", "en-US-Neural2-A"),
    "es": ("Spanish", "es-ES-Neural2-A"),
    "fr": ("French", "fr-FR-Neural2-A"),
    "de": ("German", "de-DE-Neural2-A"),
    "it": ("Italian", "it-IT-Neural2-A"),
    "pt": ("Portuguese", "pt-BR-Neural2-A"),
    "ru": ("Russian", "ru-RU-Neural2-A"),
    "ja": ("Japanese", "ja-JP-Neural2-A"),
    "ko": ("Korean", "ko-KR-Neural2-A"),
    "nl": ("Dutch", "nl-NL-Neural2-A"),
    "pl": ("Polish", "pl-PL-Neural2-A"),
    "sv": ("Swedish", "sv-SE-Neural2-A"),
    "da": ("Danish", "da-DK-Neural2-A"),
    "fi": ("Finnish", "fi-FI-Neural2-A"),
    "ar": ("Arabic", "ar-XA-Neural2-A"),
    "hi": ("Hindi", "hi-IN-Neural2-A"),
    "zh": ("Chinese (Mandarin)", "cmn-CN-Neural2-A"),
    "tr": ("Turkish", "tr-TR-Neural2-A"),
}


def book_language_select_choices() -> List[Tuple[str, str]]:
    """WTForms choices: (value, label)."""
    return [(code, label) for code, (label, _) in sorted(TTS_BOOK_LANGUAGES.items(), key=lambda x: x[1][0])]


def default_voice_for_language(code: str) -> str:
    if not code:
        return "en-US-Neural2-A"
    entry = TTS_BOOK_LANGUAGES.get((code or "").lower().strip())
    return entry[1] if entry else "en-US-Neural2-A"


def language_label(code: str) -> str:
    entry = TTS_BOOK_LANGUAGES.get((code or "").lower().strip())
    return entry[0] if entry else (code or "Other").title()


def tts_voice_list_prefix(iso_code: str) -> str:
    """
    Map our ebook ISO codes to prefixes used in Google Cloud TTS voice.language_codes
    (list_voices / filtering). Example: Mandarin uses cmn-, not zh-.
    """
    c = (iso_code or "en").lower().strip()
    if c == "zh":
        return "cmn"
    if c == "no":
        return "nb"
    return c
