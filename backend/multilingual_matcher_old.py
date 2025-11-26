"""
Multilingual Matching Service
Matches articles against expanded keywords in multiple languages
"""
from langdetect import detect, LangDetectException
from arabic_utils import normalize_arabic, extract_text_for_matching, is_arabic_text, build_arabic_pattern
from proper_noun_rules import get_proper_noun_forms
import re
import json
import logging

# Configure logging for match debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def detect_article_language(title, summary=""):
    """
    Detect the language of an article
    
    Args:
        title: Article title
        summary: Article summary/description
        
    Returns:
        Language code (en, ar, fr, etc.) or 'unknown'
    """
    # Combine title and summary for better detection
    text = f"{title} {summary}".strip()
    
    if not text:
        return 'unknown'
    
    # Quick check for Arabic
    if is_arabic_text(text):
        return 'ar'
    
    # Use langdetect for other languages
    try:
        lang = detect(text)
        return lang
    except LangDetectException:
        return 'unknown'


def build_match_set(keyword_expansion, detected_lang):
    """
    Build the set of terms to match against, based on article language
    
    Args:
        keyword_expansion: Expansion dict with translations
        detected_lang: Detected language of the article
        
    Returns:
        List of (term, lang_code) tuples to match
    """
    # Get proper noun forms from centralized map (if keyword is a known proper noun)
    
    match_terms = []
    
    # Always include normalized Arabic
    normalized_ar = keyword_expansion.get('normalized_ar', '')
    if normalized_ar:
        match_terms.append((normalized_ar, 'ar'))
    
    # Include original Arabic (for non-normalized matches)
    original_ar = keyword_expansion.get('original_ar', '')
    if original_ar:
        match_terms.append((original_ar, 'ar'))
    
    # Get translations from Google Translate
    translations = keyword_expansion.get('translations', {})
    
    # Map common language codes to our translation keys
    lang_mapping = {
        'zh': 'zh-cn',
        'zh-tw': 'zh-cn',
        'zh-hans': 'zh-cn',
        'zh-hant': 'zh-cn'
    }
    
    mapped_lang = lang_mapping.get(detected_lang, detected_lang)
    
    # PRIORITY 1: Add detected language (highest priority)
    if detected_lang and detected_lang != 'ar' and detected_lang in translations:
        match_terms.append((translations[detected_lang], detected_lang))
    
    # PRIORITY 2: Add mapped language if different
    if mapped_lang and mapped_lang != detected_lang and mapped_lang in translations:
        match_terms.append((translations[mapped_lang], mapped_lang))
    
    # PRIORITY 3: Always include English as universal fallback
    if 'en' in translations:
        match_terms.append((translations['en'], 'en'))
    
    # PRIORITY 4: Add ALL other translations as fallback (in case detection was wrong!)
    # This ensures we match articles even if language detection fails
    priority_langs = {detected_lang, mapped_lang, 'en', 'ar'}  # Already added
    
    for lang_code, translation in translations.items():
        if lang_code not in priority_langs and translation:
            match_terms.append((translation, lang_code))
    
    # ADD PROPER NOUN HANDLING: If this is a known proper noun, add correct forms
    proper_noun_forms = get_proper_noun_forms(original_ar)
    if proper_noun_forms:
        # Add the proper noun form for detected language
        if detected_lang and detected_lang in proper_noun_forms:
            match_terms.append((proper_noun_forms[detected_lang], detected_lang))
        
        # Also add mapped language form if different
        if mapped_lang and mapped_lang in proper_noun_forms:
            match_terms.append((proper_noun_forms[mapped_lang], mapped_lang))
        
        # Always add English proper noun form as fallback
        if 'en' in proper_noun_forms:
            match_terms.append((proper_noun_forms['en'], 'en'))
    
    return match_terms


def matches_keyword(article_text, keyword_expansion, detected_lang, article_url="", article_title="", source_name=""):
    """
    Check if article text matches the expanded keyword with Arabic-aware matching
    
    Args:
        article_text: Combined article text (title + summary)
        keyword_expansion: Expansion dict with translations
        detected_lang: Detected language of article
        article_url: URL for logging (optional)
        article_title: Title for logging (optional)
        source_name: Source name for logging (optional)
        
    Returns:
        (matches: bool, matched_term: str, matched_lang: str)
    """
    if not article_text:
        return (False, None, None)
    
    # Clean and normalize article text
    article_text_clean = extract_text_for_matching(article_text)
    
    # Normalize if Arabic
    is_arabic = detected_lang == 'ar' or is_arabic_text(article_text_clean)
    if is_arabic:
        article_text_normalized = normalize_arabic(article_text_clean)
    else:
        article_text_normalized = article_text_clean
    
    # Build match set based on article language
    match_terms = build_match_set(keyword_expansion, detected_lang)
    
    # Try to match each term
    for term, lang_code in match_terms:
        if not term:
            continue
        
        # Normalize term if it's Arabic
        if lang_code == 'ar':
            term_normalized = normalize_arabic(term)
            search_text = article_text_normalized
            
            # Use Arabic-aware pattern matching
            pattern = build_arabic_pattern(term_normalized)
            if pattern:
                match = pattern.search(search_text)
                if match:
                    # DEBUG logging for RT Arabic
                    if "arabic.rt.com" in source_name.lower() or "rt arabic" in source_name.lower():
                        logger.info(json.dumps({
                            "source": source_name,
                            "url": article_url[:80] if article_url else "",
                            "title_snippet": article_title[:60] if article_title else "",
                            "keyword": keyword_expansion.get('original_ar', term),
                            "matched": True,
                            "reason": f"Arabic pattern matched '{match.group()}' at position {match.start()}",
                            "pattern": pattern.pattern[:100]
                        }, ensure_ascii=False))
                    return (True, term, lang_code)
        else:
            # Non-Arabic: use simple case-insensitive substring match
            term_normalized = term
            search_text = article_text_clean
            if re.search(re.escape(term_normalized), search_text, re.IGNORECASE):
                return (True, term, lang_code)
    
    # DEBUG logging for RT Arabic non-matches
    if "arabic.rt.com" in source_name.lower() or "rt arabic" in source_name.lower():
        logger.info(json.dumps({
            "source": source_name,
            "url": article_url[:80] if article_url else "",
            "title_snippet": article_title[:60] if article_title else "",
            "keyword": keyword_expansion.get('original_ar', ''),
            "matched": False,
            "reason": "No pattern matched",
            "tested_terms": [t for t, _ in match_terms]
        }, ensure_ascii=False))
    
    return (False, None, None)


def match_article_against_keywords(article, keyword_expansions, source_name=""):
    """
    Match an article against all expanded keywords
    
    Args:
        article: Article dict with 'title', 'summary'/'description', 'url'
        keyword_expansions: List of expansion dicts
        source_name: Source name for logging (optional)
        
    Returns:
        List of matched keywords with details:
        [
            {
                'keyword_ar': str,
                'matched_term': str,
                'matched_lang': str
            },
            ...
        ]
    """
    # Extract article text
    title = article.get('title', '')
    summary = article.get('summary') or article.get('description', '')
    url = article.get('url', '')
    
    article_text = f"{title} {summary}"
    
    # Detect language
    detected_lang = detect_article_language(title, summary)
    
    # DEBUG: Log the call with article info
    logger.debug(f"MATCH_CALL: Testing {len(keyword_expansions)} keywords against article: {title[:80]}")
    
    # Try to match against each keyword
    matches = []
    
    for expansion in keyword_expansions:
        keyword_ar = expansion.get('original_ar', 'Unknown')
        
        # DEBUG: Log each keyword being tested
        logger.debug(f"  Testing keyword: {keyword_ar}")
        
        is_match, matched_term, matched_lang = matches_keyword(
            article_text, 
            expansion, 
            detected_lang,
            article_url=url,
            article_title=title,
            source_name=source_name
        )
        
        if is_match:
            logger.debug(f"  ✅ MATCHED: {keyword_ar} (term: {matched_term}, lang: {matched_lang})")
            matches.append({
                'keyword_ar': keyword_ar,
                'matched_term': matched_term,
                'matched_lang': matched_lang,
                'detected_lang': detected_lang
            })
    
    return matches


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("MULTILINGUAL MATCHING TEST")
    print("=" * 80)
    
    # Test language detection
    test_articles = [
        {"title": "Trump announces new policy", "summary": "The president made an announcement..."},
        {"title": "السعودية تعلن عن مشروع جديد", "summary": "أعلنت المملكة العربية السعودية..."},
        {"title": "France announces", "summary": "Le président français..."},
        {"title": "中国宣布新政策", "summary": "中国政府今天宣布..."},
    ]
    
    print("\n1. Language Detection Test:")
    for article in test_articles:
        lang = detect_article_language(article['title'], article.get('summary', ''))
        print(f"   {article['title'][:50]:50} → {lang}")
    
    # Test matching
    print("\n2. Matching Test:")
    
    sample_expansion = {
        'original_ar': 'ترامب',
        'normalized_ar': 'ترامب',
        'translations': {
            'en': 'Trump',
            'fr': 'Trump',
            'es': 'Trump',
            'ru': 'Трамп',
            'zh-cn': '特朗普'
        }
    }
    
    for article in test_articles:
        detected_lang = detect_article_language(article['title'], article.get('summary', ''))
        is_match, term, lang = matches_keyword(
            f"{article['title']} {article.get('summary', '')}",
            sample_expansion,
            detected_lang
        )
        print(f"   Article: {article['title'][:40]}")
        print(f"   Match: {is_match}, Term: {term}, Lang: {lang}")
        print()
