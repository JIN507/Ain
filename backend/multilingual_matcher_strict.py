"""
Strict Multilingual Matching Service

STRICT LEXICAL MATCHING ONLY - No semantic/fuzzy matching.

An article matches a keyword if and only if:
- At least one normalized variant of the keyword appears in the normalized article text
- For Latin scripts: word-boundary matching (avoids "France" in "Francesco")
- For Arabic/CJK: substring matching after normalization

All keywords are tested against all articles.
No early exits that skip keywords.
"""
import re
import json
import logging
from typing import List, Dict, Tuple, Optional
from langdetect import detect, LangDetectException

from text_normalization import (
    normalize_text,
    normalize_keyword_variant,
    extract_searchable_text,
    is_latin_script,
    is_cjk_text,
    build_word_boundary_pattern,
    build_substring_pattern
)
from arabic_utils import is_arabic_text, normalize_arabic, build_arabic_pattern
from proper_noun_rules import get_proper_noun_forms, is_known_proper_noun

# Configure logging
logger = logging.getLogger(__name__)


def detect_article_language(title: str, summary: str = "", content: str = "") -> str:
    """
    Detect the language of an article from its text content.
    
    Uses title + summary + content (if available) for better detection.
    
    Args:
        title: Article title
        summary: Article summary/description
        content: Article content (optional)
        
    Returns:
        Language code (en, ar, fr, etc.) or 'unknown'
    """
    # Combine all text for better detection
    text_parts = [title, summary]
    if content:
        # Use first 500 chars of content to avoid overwhelming lang detection
        text_parts.append(content[:500])
    
    text = ' '.join(text_parts).strip()
    
    if not text:
        return 'unknown'
    
    # Quick check for Arabic (more reliable than langdetect for Arabic)
    if is_arabic_text(text):
        return 'ar'
    
    # Use langdetect for other languages
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return 'unknown'


def get_all_keyword_variants(keyword_expansion: dict, prefer_proper_nouns: bool = True) -> List[Tuple[str, str]]:
    """
    Get ALL variants of a keyword for comprehensive matching.
    
    IMPORTANT: Returns ALL language variants to ensure we don't miss matches
    when language detection is wrong or article is multilingual.
    
    Args:
        keyword_expansion: Expansion dict with translations
        prefer_proper_nouns: If True and keyword is a proper noun, use only proper noun forms
        
    Returns:
        List of (variant_text, language_code) tuples
    """
    variants = []
    
    original_ar = keyword_expansion.get('original_ar', '')
    normalized_ar = keyword_expansion.get('normalized_ar', '')
    
    # Check if this is a known proper noun
    proper_noun_forms = get_proper_noun_forms(original_ar)
    is_proper_noun = proper_noun_forms is not None
    
    # Add Arabic forms
    if original_ar:
        variants.append((original_ar, 'ar'))
    if normalized_ar and normalized_ar != original_ar:
        variants.append((normalized_ar, 'ar'))
    
    # Get translations
    translations = keyword_expansion.get('translations', {})
    
    if is_proper_noun and prefer_proper_nouns:
        # PROPER NOUN: Use only curated proper-name forms
        # This prevents "ترامب" from matching "trump card" articles
        logger.debug(f"Using proper noun forms for: {original_ar}")
        
        for lang_code, proper_form in proper_noun_forms.items():
            if proper_form:
                variants.append((proper_form, lang_code))
    
    else:
        # REGULAR WORD: Use all translations
        for lang_code, translation in translations.items():
            if translation:
                variants.append((translation, lang_code))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for variant, lang in variants:
        key = (variant.lower(), lang)
        if key not in seen:
            seen.add(key)
            unique_variants.append((variant, lang))
    
    return unique_variants


def match_variant_in_text(
    variant: str,
    variant_lang: str,
    article_text_normalized: str,
    article_lang: str
) -> Optional[Tuple[str, int]]:
    """
    Check if a single variant appears in the normalized article text.
    
    Uses appropriate matching strategy based on script:
    - Latin scripts: word boundary matching
    - Arabic: Arabic-aware pattern with clitics
    - CJK: substring matching
    
    Args:
        variant: Keyword variant to search for
        variant_lang: Language code of the variant
        article_text_normalized: Normalized article text
        article_lang: Detected language of article
        
    Returns:
        Tuple of (matched_text, position) if found, None otherwise
    """
    if not variant or not article_text_normalized:
        return None
    
    # Normalize the variant using same pipeline as article text
    variant_normalized = normalize_keyword_variant(variant, variant_lang)
    
    if not variant_normalized:
        return None
    
    # Strategy 1: Arabic matching (Arabic-aware pattern)
    if variant_lang == 'ar' or is_arabic_text(variant):
        # Use Arabic-aware pattern that handles clitics and definite articles
        pattern = build_arabic_pattern(variant_normalized)
        if pattern:
            match = pattern.search(article_text_normalized)
            if match:
                return (match.group(), match.start())
    
    # Strategy 2: Latin script matching (word boundaries)
    elif is_latin_script(variant):
        # Use word boundary pattern to avoid partial matches
        # Example: "France" won't match inside "Francesco"
        pattern = build_word_boundary_pattern(variant_normalized)
        match = pattern.search(article_text_normalized)
        if match:
            return (match.group(), match.start())
    
    # Strategy 3: CJK or other scripts (substring matching)
    else:
        # For CJK and other scripts without word boundaries
        pattern = build_substring_pattern(variant_normalized)
        match = pattern.search(article_text_normalized)
        if match:
            return (match.group(), match.start())
    
    return None


def match_article_against_keywords(
    article: dict,
    keyword_expansions: List[dict],
    source_name: str = ""
) -> List[dict]:
    """
    Match an article against ALL expanded keywords using STRICT lexical matching.
    
    STRICT RULES:
    - Only matches if keyword variant literally appears in article text
    - Tests ALL keywords (no early exit after first match)
    - Uses title + description + content for matching
    - No semantic/fuzzy matching
    
    Args:
        article: Article dict with 'title', 'summary'/'description', 'content'
        keyword_expansions: List of expansion dicts
        source_name: Source name for logging
        
    Returns:
        List of matched keywords with details:
        [
            {
                'keyword_ar': str,
                'matched_variants': List[str],  # All variants that matched
                'matched_lang': str,             # Primary language of match
                'detected_lang': str             # Detected article language
            },
            ...
        ]
    """
    # Extract all searchable text from article
    searchable_text = extract_searchable_text(article)
    
    if not searchable_text:
        logger.debug("Article has no searchable text, skipping")
        return []
    
    # Detect article language
    title = article.get('title', '')
    summary = article.get('summary', '') or article.get('description', '')
    content = article.get('content', '')
    detected_lang = detect_article_language(title, summary, content)
    
    # Normalize the entire article text
    article_text_normalized = normalize_text(searchable_text, detected_lang)
    
    if not article_text_normalized:
        logger.debug("Article text is empty after normalization")
        return []
    
    # Test ALL keywords (CRITICAL: no early exit)
    matches = []
    
    for expansion in keyword_expansions:
        keyword_ar = expansion.get('original_ar', 'Unknown')
        
        # Get ALL variants for this keyword
        variants = get_all_keyword_variants(expansion)
        
        if not variants:
            logger.debug(f"No variants for keyword: {keyword_ar}")
            continue
        
        # Test each variant
        matched_variants = []
        matched_positions = []
        
        for variant, variant_lang in variants:
            match_result = match_variant_in_text(
                variant,
                variant_lang,
                article_text_normalized,
                detected_lang
            )
            
            if match_result:
                matched_text, position = match_result
                matched_variants.append({
                    'text': variant,
                    'lang': variant_lang,
                    'matched_at': position,
                    'matched_form': matched_text
                })
        
        # If any variant matched, record this keyword as a match
        if matched_variants:
            # Determine primary match language (use first match)
            primary_lang = matched_variants[0]['lang']
            
            matches.append({
                'keyword_ar': keyword_ar,
                'matched_variants': matched_variants,
                'matched_lang': primary_lang,
                'detected_lang': detected_lang
            })
            
            # Log match for debugging
            logger.debug(json.dumps({
                'event': 'keyword_match',
                'keyword': keyword_ar,
                'article_title': title[:80],
                'article_url': article.get('url', '')[:80],
                'detected_lang': detected_lang,
                'matched_variants': [
                    f"{v['text']} ({v['lang']})" for v in matched_variants
                ]
            }, ensure_ascii=False))
    
    # Log comprehensive match result for article
    if matches:
        logger.debug(json.dumps({
            'event': 'article_matched',
            'source': source_name,
            'url': article.get('url', '')[:80],
            'title': title[:60],
            'detected_lang': detected_lang,
            'matched_keywords': [m['keyword_ar'] for m in matches],
            'total_matches': len(matches)
        }, ensure_ascii=False))
    
    return matches


def match_articles_with_keywords_with_stats(
    articles: List[dict],
    keyword_expansions: List[dict],
    max_per_source: int = None
) -> Tuple[List[Tuple], Dict]:
    """
    Match all articles against all keywords and collect statistics.
    
    STRICT MATCHING: Only articles with explicit keyword variants are matched.
    
    Args:
        articles: List of article dicts
        keyword_expansions: List of keyword expansion dicts
        max_per_source: Optional limit per source (not per keyword)
        
    Returns:
        Tuple of:
        - matches: List of (article, source, matched_keywords) tuples
        - keyword_stats: Dict of keyword_ar -> match_count
    """
    matches = []
    keyword_stats = {exp.get('original_ar', 'Unknown'): 0 for exp in keyword_expansions}
    
    # Group articles by source if limiting
    if max_per_source:
        from collections import defaultdict
        articles_by_source = defaultdict(list)
        for article in articles:
            source_name = article.get('source_name', 'Unknown')
            articles_by_source[source_name].append(article)
        
        # Limit per source
        limited_articles = []
        for source_name, source_articles in articles_by_source.items():
            limited_articles.extend(source_articles[:max_per_source])
        
        articles = limited_articles
    
    # Match each article against ALL keywords
    for article in articles:
        source_name = article.get('source_name', 'Unknown')
        
        # Create source dict for compatibility
        source = {
            'name': source_name,
            'country_name': article.get('country_name', '')
        }
        
        # Match against all keywords
        matched_keywords = match_article_against_keywords(
            article,
            keyword_expansions,
            source_name
        )
        
        # If any keywords matched, add to results
        if matched_keywords:
            matches.append((article, source, matched_keywords))
            
            # Update stats for each matched keyword
            for match_info in matched_keywords:
                keyword_ar = match_info.get('keyword_ar', 'Unknown')
                if keyword_ar in keyword_stats:
                    keyword_stats[keyword_ar] += 1
    
    return matches, keyword_stats


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("STRICT MULTILINGUAL MATCHING TEST")
    print("=" * 80)
    
    # Test articles
    test_articles = [
        {
            "title": "Trump announces new policy",
            "summary": "The president made an announcement today...",
            "content": "Donald Trump announced a new policy regarding...",
            "url": "http://example.com/1"
        },
        {
            "title": "Trumpet player wins award",
            "summary": "A famous trumpet player received an award...",
            "content": "The trumpet player, known for his jazz performances...",
            "url": "http://example.com/2"
        },
        {
            "title": "السعودية تعلن عن مشروع جديد",
            "summary": "أعلنت المملكة العربية السعودية عن مشروع...",
            "content": "في الرياض، أعلنت السعودية...",
            "url": "http://example.com/3"
        },
        {
            "title": "France and Italy reach agreement",
            "summary": "France and Italy signed a new agreement...",
            "content": "Francesco, the Italian minister, met with French officials...",
            "url": "http://example.com/4"
        }
    ]
    
    # Test keywords
    test_keywords = [
        {
            'original_ar': 'ترامب',
            'normalized_ar': 'ترامب',
            'translations': {
                'en': 'Trump',
                'fr': 'Trump',
                'es': 'Trump'
            }
        },
        {
            'original_ar': 'السعودية',
            'normalized_ar': 'السعودية',
            'translations': {
                'en': 'Saudi Arabia',
                'fr': 'Arabie Saoudite'
            }
        },
        {
            'original_ar': 'فرنسا',
            'normalized_ar': 'فرنسا',
            'translations': {
                'en': 'France',
                'fr': 'France',
                'it': 'Francia'
            }
        }
    ]
    
    print("\n1. Testing Strict Matching:")
    print("-" * 80)
    
    for article in test_articles:
        print(f"\nArticle: {article['title']}")
        matches = match_article_against_keywords(article, test_keywords)
        
        if matches:
            print(f"✅ MATCHED:")
            for match in matches:
                print(f"   - Keyword: {match['keyword_ar']}")
                print(f"   - Variants: {[v['text'] for v in match['matched_variants']]}")
        else:
            print(f"❌ NO MATCH")
    
    print("\n" + "=" * 80)
    print("Expected Results:")
    print("- Article 1 (Trump policy): Should MATCH 'ترامب' ✅")
    print("- Article 2 (Trumpet player): Should NOT MATCH 'ترامب' ❌")
    print("- Article 3 (السعودية): Should MATCH 'السعودية' ✅")
    print("- Article 4 (France/Francesco): Should MATCH 'فرنسا' (France) but NOT inside 'Francesco' ✅")
    print("=" * 80)
