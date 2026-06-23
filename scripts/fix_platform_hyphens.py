#!/usr/bin/env python3
"""Remove hyphens and em dashes from user-facing platform copy."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLCONNECT = ROOT / "glconnect"

TARGET_FILES: list[Path] = []
TARGET_FILES.extend(GLCONNECT.rglob("templates/**/*.html"))
TARGET_FILES.extend(GLCONNECT.glob("*.py"))
TARGET_FILES.extend((GLCONNECT / "static").glob("*.js"))
TARGET_FILES = [p for p in TARGET_FILES if p.is_file() and "__pycache__" not in str(p)]

COMPOUNDS = [
    ("chapter-by-chapter", "chapter by chapter"),
    ("Chapter-by-chapter", "Chapter by chapter"),
    ("book-funding", "book funding"),
    ("AI-native", "AI native"),
    ("AI-narrated", "AI narrated"),
    ("AI-generated", "AI generated"),
    ("AI-assisted", "AI assisted"),
    ("AI-driven", "AI driven"),
    ("AI-Powered", "AI Powered"),
    ("end-to-end", "end to end"),
    ("End-to-end", "End to end"),
    ("author-editing", "author editing"),
    ("Author-editing", "Author editing"),
    ("Self-published", "Self published"),
    ("self-published", "self published"),
    ("Self-publishing", "Self publishing"),
    ("self-publishing", "self publishing"),
    ("Purpose-built", "Purpose built"),
    ("purpose-built", "Purpose built"),
    ("Co-founder", "Co founder"),
    ("co-founder", "Co founder"),
    ("Co-author", "Co author"),
    ("co-author", "Co author"),
    ("Nice-to-haves", "Nice to haves"),
    ("go-to-market", "go to market"),
    ("hands-free", "hands free"),
    ("Hands-free", "Hands free"),
    ("cross-format", "cross format"),
    ("Cross-format", "Cross format"),
    ("Multi-format", "Multi format"),
    ("multi-format", "Multi format"),
    ("show-vs-tell", "show vs tell"),
    ("wrong-word", "wrong word"),
    ("Auto-play", "Auto play"),
    ("auto-play", "Auto play"),
    ("Auto-refresh", "Auto refresh"),
    ("auto-refresh", "Auto refresh"),
    ("Double-check", "Double check"),
    ("double-check", "Double check"),
    ("value-add", "value add"),
    ("on-air", "on air"),
    ("in-manuscript", "in manuscript"),
    ("in-studio", "in studio"),
    ("Patron-funded", "Patron funded"),
    ("patron-funded", "Patron funded"),
    ("Community-funded", "Community funded"),
    ("re-deploy", "redeploy"),
    ("sci-fi", "sci fi"),
    ("Real-time", "Real time"),
    ("real-time", "Real time"),
    ("Multi-Language", "Multi Language"),
    ("long-form", "long form"),
    ("High-fidelity", "High fidelity"),
    ("high-fidelity", "High fidelity"),
    ("High-Fi", "High Fi"),
    ("Per-Sale", "Per Sale"),
    ("Full-stack", "Full stack"),
    ("full-stack", "Full stack"),
    ("E-book", "Ebook"),
    ("e-book", "Ebook"),
    ("pre-approved", "pre approved"),
    ("long-term", "long term"),
    ("remote-friendly", "remote friendly"),
    ("early-stage", "early stage"),
    ("growth-stage", "growth stage"),
    ("Picture-Word", "Picture Word"),
    ("back-cover", "back cover"),
    ("Text-to-Speech", "Text to Speech"),
    ("text-to-speech", "text to speech"),
    ("print-on-demand", "print on demand"),
    ("third-party", "third party"),
    ("non-infringing", "non infringing"),
    ("revenue-share", "revenue share"),
    ("image-only", "image only"),
    ("layout-heavy", "layout heavy"),
    ("distribution-ready", "distribution ready"),
    ("auto-generated", "auto generated"),
    ("memory-optimized", "memory optimized"),
    ("High-quality", "High quality"),
    ("One-time", "One time"),
    ("one-time", "One time"),
    ("cybersecurity-related", "cybersecurity related"),
    ("Comma-separated", "Comma separated"),
    ("comma-separated", "Comma separated"),
    ("Hands-on", "Hands on"),
    ("hands-on", "Hands on"),
    ("in-app", "in app"),
    ("fixed-layout", "fixed layout"),
    ("broadcast-style", "broadcast style"),
    ("book-review", "book review"),
    ("Auto-publicist", "Auto publicist"),
    ("auto-generates", "auto generates"),
    ("on-platform", "on platform"),
    ("non-compliant", "non compliant"),
    ("account-level", "account level"),
    ("re-upload", "re upload"),
    ("built-in", "built in"),
    ("logged-in", "logged in"),
    ("in-browser", "in browser"),
]

DISPLAY_ONLY = [
    (">Non-Fiction</option>", ">Nonfiction</option>"),
    (">Self-Help</option>", ">Self Help</option>"),
    (">Non-fiction</option>", ">Nonfiction</option>"),
    (">Sci-Fi</option>", ">Sci Fi</option>"),
    ('<title>Careers - Join Our Mission', "<title>Careers | Join Our Mission"),
]


def _fix_titles(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return match.group(0).replace(" - ", " | ").replace("—", ":")

    return re.sub(r"<title>[^<]*</title>", repl, text, flags=re.IGNORECASE)


def _fix_meta(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        inner = inner.replace(" — ", ", ")
        inner = inner.replace("—", ", ")
        inner = re.sub(r"(\S)—(\S)", r"\1, \2", inner)
        for old, new in COMPOUNDS:
            inner = inner.replace(old, new)
        return f'content="{inner}"'

    return re.sub(r'content="([^"]*)"', repl, text)


def clean_prose(text: str) -> str:
    for old, new in DISPLAY_ONLY:
        text = text.replace(old, new)
    for old, new in COMPOUNDS:
        text = text.replace(old, new)
    text = text.replace(" — ", ", ")
    text = re.sub(r"(\S)—(\S)", r"\1, \2", text)
    text = text.replace("—", ", ")
    text = _fix_titles(text)
    return text


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = clean_prose(original)
    if path.suffix == ".html":
        updated = _fix_meta(updated)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = []
    for path in sorted(TARGET_FILES):
        if process_file(path):
            changed.append(path.relative_to(ROOT))
    print(f"Updated {len(changed)} files")
    for rel in changed:
        print(f"  {rel}")


if __name__ == "__main__":
    main()
