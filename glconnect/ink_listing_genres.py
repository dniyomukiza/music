"""Ink Studio listing categories — real experiences / nonfiction only."""

INK_UPLOAD_GENRE_CHOICES = [
    ("", "Select a category"),
    ("real-life", "Real Life"),
    ("nonfiction", "Nonfiction"),
]

INK_UPLOAD_GENRE_VALUES = frozenset({"real-life", "nonfiction"})

INK_UPLOAD_GENRE_LABELS = {
    "real-life": "Real Life",
    "nonfiction": "Nonfiction",
}

# Ink Studio write-in-app flow (create / edit chapters) — nonfiction categories only
INK_STUDIO_GENRE_CHOICES = [
    ("", "Select a category"),
    ("real-life", "Real Life"),
    ("nonfiction", "Nonfiction"),
    ("memoir", "Memoir & Biography"),
    ("self-help", "Self-Help"),
    ("business", "Business"),
    ("history", "History"),
    ("true-crime", "True Crime"),
    ("science", "Science & Nature"),
    ("health", "Health & Wellness"),
    ("travel", "Travel"),
    ("politics", "Politics & Current Affairs"),
    ("spirituality", "Spirituality & Religion"),
    ("education", "Education & How-To"),
    ("other", "Other"),
]

INK_STUDIO_GENRE_VALUES = frozenset(v for v, _ in INK_STUDIO_GENRE_CHOICES if v)

INK_STUDIO_GENRE_LABELS = {value: label for value, label in INK_STUDIO_GENRE_CHOICES if value}


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
