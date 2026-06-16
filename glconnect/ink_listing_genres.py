"""Ink Studio listing categories for uploaded ebooks (real experiences only)."""

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


def ink_upload_genre_label(value: str) -> str:
    if not value:
        return ""
    return INK_UPLOAD_GENRE_LABELS.get(str(value).strip(), str(value).replace("-", " ").title())


def is_valid_ink_upload_genre(value: str) -> bool:
    return bool(value) and str(value).strip() in INK_UPLOAD_GENRE_VALUES
