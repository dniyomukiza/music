"""Ink Studio listing categories — nonfiction only."""

INK_UPLOAD_GENRE_CHOICES = [
    ("nonfiction", "Nonfiction"),
]

INK_UPLOAD_GENRE_VALUES = frozenset({"nonfiction"})

INK_UPLOAD_GENRE_LABELS = {
    "nonfiction": "Nonfiction",
}

# Ink Studio write-in-app flow (create / edit chapters) — nonfiction only
INK_STUDIO_GENRE_CHOICES = [
    ("nonfiction", "Nonfiction"),
]

INK_STUDIO_GENRE_VALUES = frozenset({"nonfiction"})

INK_STUDIO_GENRE_LABELS = {value: label for value, label in INK_STUDIO_GENRE_CHOICES}


def ink_upload_genre_label(value: str) -> str:
    if not value:
        return ""
    return INK_UPLOAD_GENRE_LABELS.get(str(value).strip(), str(value).replace("-", " ").title())


def ink_studio_genre_label(value: str) -> str:
    if not value:
        return ""
    key = str(value).strip()
    return INK_STUDIO_GENRE_LABELS.get(key, key.replace("-", " ").title())


def is_valid_ink_upload_genre(value: str) -> bool:
    return bool(value) and str(value).strip() in INK_UPLOAD_GENRE_VALUES


def is_valid_ink_studio_genre(value: str) -> bool:
    return bool(value) and str(value).strip() in INK_STUDIO_GENRE_VALUES
