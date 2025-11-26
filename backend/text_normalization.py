"""Text normalization utilities for multilingual matching.

This module provides a minimal implementation of the helpers required by
`multilingual_matcher.py`:

- normalize_text
- normalize_keyword_variant
- extract_searchable_text
- is_latin_script
- is_cjk_text
- build_word_boundary_pattern
- build_substring_pattern

The goal is to keep behavior simple and safe so the matching pipeline can run
without crashing, while preserving strict lexical matching semantics.
"""

from __future__ import annotations

import re
from typing import Dict


# ------------------------- Script Detection -------------------------

LATIN_RANGE = re.compile(r"[A-Za-z]")
CJK_RANGE = re.compile(r"[\u4e00-\u9fff]\u3400-\u4dbf\uf900-\ufaff")


def is_latin_script(text: str) -> bool:
    """Return True if the text appears to be primarily Latin-script.

    Very simple heuristic: presence of any ASCII letter.
    """
    if not text:
        return False
    return bool(LATIN_RANGE.search(text))


def is_cjk_text(text: str) -> bool:
    """Return True if the text appears to contain CJK characters.

    Used to decide when to fall back to substring-based matching.
    """
    if not text:
        return False
    return bool(re.search(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]", text))


# -------------------------- Normalization ---------------------------

_PUNCT_PATTERN = re.compile(r"[\u200b\u200c\u200d\u200e\u200f]")  # zero-width, bidi


def _basic_normalize(text: str) -> str:
    """Basic normalization shared by article text and keyword variants.

    - strip() whitespace
    - remove zero‑width / bidi control characters
    - collapse internal whitespace to single spaces
    - lowercase (for non-Arabic / non-CJK text this is usually fine)
    """
    if not text:
        return ""

    # Remove zero-width / bidi controls
    text = _PUNCT_PATTERN.sub("", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Lowercase for case-insensitive matching (Latin mostly)
    return text.lower()


def normalize_text(text: str, lang: str | None = None) -> str:
    """Normalize full article text for matching.

    For now we apply a simple, language-agnostic normalization. Arabic-specific
    normalization is handled in `arabic_utils.normalize_arabic` which is called
    from `multilingual_matcher` for Arabic.
    """
    return _basic_normalize(text)


def normalize_keyword_variant(variant: str, lang: str | None = None) -> str:
    """Normalize a keyword variant using the same pipeline as article text.

    Keeping both article text and variant on the same normalization path ensures
    that strict lexical matching remains consistent.
    """
    return _basic_normalize(variant)


# --------------------------- Article Text ---------------------------

def extract_searchable_text(article: Dict) -> str:
    """Extract combined searchable text from an article dict.

    Uses the standard fields that the matcher expects:
    - title
    - summary / description
    - content
    """
    if not article:
        return ""

    title = article.get("title") or article.get("title_original") or ""
    summary = (
        article.get("summary")
        or article.get("description")
        or article.get("summary_original")
        or ""
    )
    content = article.get("content") or ""

    combined = " \n ".join([str(title), str(summary), str(content)])
    return _basic_normalize(combined)


# --------------------------- Regex Patterns -------------------------

def build_word_boundary_pattern(term: str) -> re.Pattern:
    """Build a case-insensitive word-boundary regex pattern for Latin terms.

    Example: "France" will *not* match inside "Francesco".
    """
    if not term:
        # Match nothing
        return re.compile(r"^$")

    escaped = re.escape(term)
    pattern = rf"\b{escaped}\b"
    return re.compile(pattern, re.IGNORECASE)


def build_substring_pattern(term: str) -> re.Pattern:
    """Build a simple case-insensitive substring regex pattern.

    Used for CJK and other scripts where word boundaries are not trivial.
    """
    if not term:
        return re.compile(r"^$")

    escaped = re.escape(term)
    return re.compile(escaped, re.IGNORECASE)
