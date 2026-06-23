"""User-facing labels for Google Cloud TTS voices (API ids stay internal)."""

from typing import Any, Dict, Optional

VOICE_TYPE_LABELS = {
    "Neural2": "Natural",
    "Studio": "Professional",
    "Chirp3": "Expressive",
}


def enrich_voices_with_display_names(voices_by_type: Dict[str, Any]) -> Dict[str, Any]:
    """Add display_name to each voice: e.g. Male Natural 1, Female Expressive 2."""
    enriched: Dict[str, Any] = {}
    for voice_type, voices in (voices_by_type or {}).items():
        category = VOICE_TYPE_LABELS.get(voice_type, voice_type)
        counters = {"Male": 0, "Female": 0}
        sorted_voices = sorted(voices or [], key=lambda v: v.get("name", ""))
        enriched_list = []
        for voice in sorted_voices:
            gender_key = "Female" if voice.get("gender") == "FEMALE" else "Male"
            counters[gender_key] += 1
            display_name = f"{gender_key} {category} {counters[gender_key]}"
            enriched_list.append({**voice, "display_name": display_name})
        enriched[voice_type] = enriched_list
    return enriched


def lookup_display_name(voice_name: str, voices_by_type: Dict[str, Any]) -> Optional[str]:
    if not voice_name:
        return None
    for voices in (voices_by_type or {}).values():
        for voice in voices or []:
            if voice.get("name") == voice_name:
                return voice.get("display_name")
    return None
