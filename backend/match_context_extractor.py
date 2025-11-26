"""
Match Context Extractor

Extracts surrounding context around keyword matches to show users
exactly why an article matched a keyword.

Returns: N lines before match + matched text + N lines after match
"""
import re
from typing import Optional, Dict, List
from text_normalization import normalize_text


def translate_snippet_preserve_keyword(
    snippet: str,
    keyword_marker: str,
    source_lang: str,
    target_lang: str = 'ar',
    keyword_ar: str = None
) -> str:
    """
    Translate a snippet while preserving/replacing the keyword with Arabic version.
    
    Args:
        snippet: Text with **keyword** marker
        keyword_marker: The exact keyword text to preserve (inside **)
        source_lang: Source language code
        target_lang: Target language code
        keyword_ar: Arabic version of keyword to use in translated text
        
    Returns:
        Translated snippet with keyword highlighted
    """
    if not snippet or source_lang == target_lang:
        return snippet
    
    try:
        from translation_cache import translate_to_arabic_cached
        
        # Split the snippet by **keyword** markers
        parts = snippet.split('**')
        
        if len(parts) < 3:
            # No keyword markers, translate as is
            result = translate_to_arabic_cached(snippet, source_lang)
            return result.get('translated', snippet) if isinstance(result, dict) else snippet
        
        # parts[0] = text before keyword
        # parts[1] = keyword
        # parts[2] = text after keyword
        # parts[3+] = additional markers if any
        
        translated_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # Odd index = keyword (inside ** markers)
                # Replace with Arabic keyword if provided, otherwise keep original
                if keyword_ar and source_lang != 'ar':
                    translated_parts.append(f"**{keyword_ar}**")
                else:
                    translated_parts.append(f"**{part}**")
            else:
                # Even index = regular text
                if part.strip():
                    result = translate_to_arabic_cached(part, source_lang)
                    # Extract the 'translated' field from the result dict
                    translated_text = result.get('translated', part) if isinstance(result, dict) else part
                    translated_parts.append(translated_text)
                else:
                    translated_parts.append(part)
        
        return ' '.join(translated_parts)
        
    except Exception as e:
        print(f"      ⚠️  Translation error: {e}")
        return snippet  # Return original if translation fails


def extract_match_context(
    article_text: str,
    matched_variant: str,
    match_position: int,
    words_before: int = 20,
    words_after: int = 20,
    max_chars_per_line: int = 100
) -> Dict[str, str]:
    """
    Extract context around a keyword match using WORD COUNT for better context.
    
    Args:
        article_text: Original article text (not normalized)
        matched_variant: The keyword variant that matched
        match_position: Position in NORMALIZED text where match occurred
        words_before: Number of WORDS before match (default: 20)
        words_after: Number of WORDS after match (default: 20)
        max_chars_per_line: Max characters per line (for splitting)
        
    Returns:
        Dict with:
        - before_context: Text before the match
        - matched_text: The actual matched text (highlighted)
        - after_context: Text after the match
        - full_snippet: Combined text with [...] markers
    """
    if not article_text or not matched_variant:
        return {
            'before_context': '',
            'matched_text': '',
            'after_context': '',
            'full_snippet': article_text[:200] if article_text else ''
        }
    
    # Find the keyword in the text (case-insensitive)
    matched_variant_lower = matched_variant.lower()
    article_text_lower = article_text.lower()
    
    keyword_start = article_text_lower.find(matched_variant_lower)
    
    if keyword_start == -1:
        # Fallback: keyword not found
        return {
            'before_context': '',
            'matched_text': matched_variant,
            'after_context': '',
            'full_snippet': article_text[:300] if len(article_text) > 300 else article_text
        }
    
    keyword_end = keyword_start + len(matched_variant)
    actual_matched_text = article_text[keyword_start:keyword_end]
    
    # Extract text before keyword
    text_before = article_text[:keyword_start]
    # Extract text after keyword
    text_after = article_text[keyword_end:]
    
    # Split into words (handles both Arabic and English)
    # For Arabic: split by spaces and Arabic punctuation
    # For English: split by spaces and punctuation
    def split_into_words(text):
        """Split text into words, preserving punctuation context"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Split by spaces
        words = text.split()
        return words
    
    words_before_list = split_into_words(text_before)
    words_after_list = split_into_words(text_after)
    
    # Take last N words before keyword
    if len(words_before_list) > words_before:
        selected_before = words_before_list[-words_before:]
        has_more_before = True
    else:
        selected_before = words_before_list
        has_more_before = False
    
    # Take first N words after keyword
    if len(words_after_list) > words_after:
        selected_after = words_after_list[:words_after]
        has_more_after = True
    else:
        selected_after = words_after_list
        has_more_after = False
    
    # Build contexts
    before_context = ' '.join(selected_before).strip()
    after_context = ' '.join(selected_after).strip()
    
    # Build full snippet with [...] markers
    parts = []
    
    if has_more_before:
        parts.append('[...]')
    
    if before_context:
        parts.append(before_context)
    
    # Add the keyword with ** markers for highlighting
    parts.append(f"**{actual_matched_text}**")
    
    if after_context:
        parts.append(after_context)
    
    if has_more_after:
        parts.append('[...]')
    
    full_snippet = ' '.join(parts)
    
    return {
        'before_context': before_context,
        'matched_text': actual_matched_text,
        'after_context': after_context,
        'full_snippet': full_snippet
    }


def extract_all_match_contexts(
    article: dict,
    matched_keywords: List[dict],
    words_before: int = 20,
    words_after: int = 20
) -> List[Dict]:
    """
    Extract context for all matched keywords in an article.
    
    Args:
        article: Article dict with title, summary, content
        matched_keywords: List of matched keyword dicts from matcher
        words_before: Number of WORDS before match (default: 20 = ~2 lines)
        words_after: Number of WORDS after match (default: 20 = ~2 lines)
        
    Returns:
        List of context dicts, one per matched keyword
    """
    # Combine all article text
    title = article.get('title', '')
    summary = article.get('summary', '') or article.get('description', '')
    content = article.get('content', '')
    
    # Build full text with all available content
    full_text = f"{title}. {summary}"
    if content:
        full_text += f" {content}"
    
    # Debug: print what text we have
    print(f"      📝 Extracting context from text length: {len(full_text)} chars")
    print(f"         - Title: {len(title)} chars")
    print(f"         - Summary: {len(summary)} chars")
    print(f"         - Content: {len(content)} chars")
    
    contexts = []
    
    for match_info in matched_keywords:
        keyword_ar = match_info.get('keyword_ar', '')
        matched_variants = match_info.get('matched_variants', [])
        
        if not matched_variants:
            continue
        
        # Use the first matched variant for context extraction
        first_variant = matched_variants[0]
        variant_text = first_variant.get('text', '')
        match_position = first_variant.get('matched_at', 0)
        
        print(f"      🔍 Looking for variant: '{variant_text}' (keyword: {keyword_ar})")
        
        context = extract_match_context(
            full_text,
            variant_text,
            match_position,
            words_before,
            words_after
        )
        
        context['keyword_ar'] = keyword_ar
        context['matched_variant'] = variant_text
        
        # Store original matched text for preserving during translation
        context['preserve_text'] = context.get('matched_text', variant_text)
        
        print(f"      ✅ Extracted snippet: {context['full_snippet'][:100]}...")
        
        contexts.append(context)
    
    return contexts


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("MATCH CONTEXT EXTRACTION TEST")
    print("=" * 80)
    
    # Test case 1: English article
    article_en = {
        'title': 'Trump Announces New Policy',
        'summary': 'President Trump made a significant announcement today. The new policy will affect trade relations. Many experts have praised the decision. The implementation will begin next month.',
        'content': ''
    }
    
    matched_keywords_en = [
        {
            'keyword_ar': 'ترامب',
            'matched_variants': [
                {'text': 'Trump', 'lang': 'en', 'matched_at': 10}
            ]
        }
    ]
    
    print("\n1. English Article Test:")
    contexts = extract_all_match_contexts(article_en, matched_keywords_en, words_before=10, words_after=10)
    for ctx in contexts:
        print(f"\nKeyword: {ctx['keyword_ar']}")
        print(f"Matched: {ctx['matched_variant']}")
        print(f"Context: {ctx['full_snippet']}")
    
    # Test case 2: Arabic article
    article_ar = {
        'title': 'السعودية تعلن عن مشروع جديد',
        'summary': 'أعلنت المملكة العربية السعودية عن مشروع ضخم. يهدف المشروع إلى تطوير البنية التحتية. سيستفيد الملايين من المواطنين. التنفيذ سيبدأ العام المقبل.',
        'content': ''
    }
    
    matched_keywords_ar = [
        {
            'keyword_ar': 'السعودية',
            'matched_variants': [
                {'text': 'السعودية', 'lang': 'ar', 'matched_at': 20}
            ]
        }
    ]
    
    print("\n2. Arabic Article Test:")
    contexts = extract_all_match_contexts(article_ar, matched_keywords_ar, words_before=10, words_after=10)
    for ctx in contexts:
        print(f"\nKeyword: {ctx['keyword_ar']}")
        print(f"Matched: {ctx['matched_variant']}")
        print(f"Context: {ctx['full_snippet']}")
    
    print("\n" + "=" * 80)
    print("✅ Context extraction tests complete")
