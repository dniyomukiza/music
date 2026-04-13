"""
Languages supported for uploaded ebooks: TTS voice defaults and translation targets.

Only languages listed here appear on the list-ebook form so audiobook voice selection
and optional AI-translated editions stay aligned with Google Cloud TTS coverage.
"""

from typing import Dict, List, Tuple

# ISO 639-1 (or BCP-47 where needed) -> (human label, default Standard voice name)
TTS_BOOK_LANGUAGES: Dict[str, Tuple[str, str]] = {
    "en": ("English", "en-US-Standard-A"),
    "es": ("Spanish", "es-ES-Standard-A"),
    "fr": ("French", "fr-FR-Standard-A"),
    "de": ("German", "de-DE-Standard-A"),
    "it": ("Italian", "it-IT-Standard-A"),
    "pt": ("Portuguese", "pt-BR-Standard-A"),
    "ru": ("Russian", "ru-RU-Standard-A"),
    "ja": ("Japanese", "ja-JP-Standard-A"),
    "ko": ("Korean", "ko-KR-Standard-A"),
    "nl": ("Dutch", "nl-NL-Standard-A"),
    "pl": ("Polish", "pl-PL-Standard-A"),
    "sv": ("Swedish", "sv-SE-Standard-A"),
    "da": ("Danish", "da-DK-Standard-A"),
    "fi": ("Finnish", "fi-FI-Standard-A"),
    "ar": ("Arabic", "ar-XA-Standard-A"),
    "hi": ("Hindi", "hi-IN-Standard-A"),
    "zh": ("Chinese (Mandarin)", "cmn-CN-Standard-A"),
    "tr": ("Turkish", "tr-TR-Standard-A"),
}


def book_language_select_choices() -> List[Tuple[str, str]]:
    """WTForms choices: (value, label)."""
    return [(code, label) for code, (label, _) in sorted(TTS_BOOK_LANGUAGES.items(), key=lambda x: x[1][0])]


def default_voice_for_language(code: str) -> str:
    if not code:
        return "en-US-Standard-A"
    entry = TTS_BOOK_LANGUAGES.get((code or "").lower().strip())
    return entry[1] if entry else "en-US-Standard-A"


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
