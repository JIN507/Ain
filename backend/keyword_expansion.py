"""
Keyword Expansion Service
Translates Arabic keywords to multiple languages using Google Translate
Includes caching to avoid redundant translations
"""
import os
from datetime import datetime, timedelta
from googletrans import Translator
from arabic_utils import normalize_arabic
from proper_noun_rules import get_proper_noun_forms, is_known_proper_noun
import json

# Configuration from environment
# Expanded to cover ALL major languages from our sources (30+ languages)
TRANSLATE_TARGETS = os.getenv(
    'TRANSLATE_TARGETS', 
    'en,fr,es,de,ru,zh-cn,ja,hi,id,pt,tr,ar,ko,it,nl,pl,vi,th,uk,ro,el,cs,sv,hu,fi,da,no,sk,bg,hr,ms,fa,ur'
).split(',')
EXPANSION_TTL_DAYS = int(os.getenv('EXPANSION_TTL_DAYS', '7'))
TRANSLATION_TIMEOUT_S = int(os.getenv('TRANSLATION_TIMEOUT_S', '8'))

# Initialize Google Translator
translator = Translator()

# In-memory cache for expansions
_expansion_cache = {}


def expand_keyword(keyword_ar):
    """
    Expand Arabic keyword to multiple languages
    
    Args:
        keyword_ar: Arabic keyword to expand
        
    Returns:
        dict: {
            'original_ar': str,
            'normalized_ar': str,
            'translations': {'en': '...', 'ru': '...', ...},
            'updated_at': str (ISO8601),
            'status': 'success' | 'partial' | 'failed'
        }
    """
    # Check cache first
    cache_key = keyword_ar
    if cache_key in _expansion_cache:
        cached = _expansion_cache[cache_key]
        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cached['updated_at'])
        if datetime.utcnow() - cache_time < timedelta(days=EXPANSION_TTL_DAYS):
            print(f"   📦 Using cached expansion for: {keyword_ar}")
            return cached
    
    print(f"   🔄 Expanding keyword: {keyword_ar}")
    
    # Normalize Arabic
    normalized_ar = normalize_arabic(keyword_ar)
    
    # Check if this is a known proper noun
    proper_noun_forms = get_proper_noun_forms(keyword_ar)
    is_known_proper_noun = proper_noun_forms is not None
    
    # Auto-detect if keyword looks like a proper noun (capitalized, starts with capital, etc.)
    # For now, rely on the manual map but could add heuristics
    # TODO: Add automatic proper noun detection for names not in map
    
    if is_known_proper_noun:
        print(f"   📌 Known proper noun - using curated translations")
    
    # Translate to target languages
    translations = {}
    failed_langs = []
    
    for target_lang in TRANSLATE_TARGETS:
        try:
            # Clean target lang code
            lang_code = target_lang.strip().lower()
            
            # Use proper noun form if available, otherwise use Google Translate
            if is_known_proper_noun and lang_code in proper_noun_forms:
                translations[lang_code] = proper_noun_forms[lang_code]
                print(f"      ✅ {lang_code.upper()}: {proper_noun_forms[lang_code]} (curated)")
            else:
                # Use Google Translate for non-proper nouns
                # WARNING: For proper nouns not in our map, Google Translate may give
                # generic translations (e.g., "ترامب" → "Atout" in French meaning "trump card")
                # To fix: Add the proper noun to proper_noun_rules.py
                result = translator.translate(keyword_ar, src='ar', dest=lang_code)
                
                if result and result.text:
                    translations[lang_code] = result.text
                    print(f"      ✅ {lang_code.upper()}: {result.text}")
                else:
                    failed_langs.append(lang_code)
                    print(f"      ❌ {lang_code.upper()}: No result")
                
        except Exception as e:
            failed_langs.append(target_lang)
            print(f"      ❌ {target_lang.upper()}: {str(e)[:50]}")
    
    # Determine status
    if len(translations) == len(TRANSLATE_TARGETS):
        status = 'success'
    elif len(translations) > 0:
        status = 'partial'
    else:
        status = 'failed'
    
    # Create expansion result
    expansion = {
        'original_ar': keyword_ar,
        'normalized_ar': normalized_ar,
        'translations': translations,
        'updated_at': datetime.utcnow().isoformat(),
        'status': status,
        'failed_langs': failed_langs if failed_langs else None
    }
    
    # Cache the result
    _expansion_cache[cache_key] = expansion
    
    print(f"   ✅ Expansion complete: {status} ({len(translations)}/{len(TRANSLATE_TARGETS)} languages)")
    
    return expansion


def get_cached_expansion(keyword_ar):
    """
    Get cached expansion if available and valid
    
    Args:
        keyword_ar: Arabic keyword
        
    Returns:
        Cached expansion or None
    """
    if keyword_ar in _expansion_cache:
        cached = _expansion_cache[keyword_ar]
        cache_time = datetime.fromisoformat(cached['updated_at'])
        if datetime.utcnow() - cache_time < timedelta(days=EXPANSION_TTL_DAYS):
            return cached
    return None


def get_all_expansions():
    """
    Get all cached expansions
    
    Returns:
        list of expansion dicts
    """
    # Filter out expired entries
    valid_expansions = []
    now = datetime.utcnow()
    
    for keyword_ar, expansion in _expansion_cache.items():
        cache_time = datetime.fromisoformat(expansion['updated_at'])
        if now - cache_time < timedelta(days=EXPANSION_TTL_DAYS):
            valid_expansions.append(expansion)
    
    return valid_expansions


def clear_expansion_cache():
    """Clear the expansion cache"""
    _expansion_cache.clear()
    print("🧹 Cleared expansion cache")


def load_expansions_from_keywords(keywords):
    """
    Load cached expansions for keywords - NEVER translates during runtime!
    
    CRITICAL: This function is called during monitoring and must be FAST.
    It ONLY loads pre-cached expansions. If expansion is missing, it skips
    the keyword with a warning.
    
    Translation/expansion happens ONLY when adding keywords via /api/keywords.
    
    Args:
        keywords: List of Keyword objects with text_ar field
        
    Returns:
        List of cached expansions (skips keywords without cache)
    """
    expansions = []
    skipped = []
    
    for kw in keywords:
        keyword_ar = kw.text_ar
        
        # ONLY load from cache - NEVER translate during runtime!
        expansion = get_cached_expansion(keyword_ar)
        
        if expansion:
            expansions.append(expansion)
        else:
            # Skip keyword if not cached (should have been expanded when added)
            skipped.append(keyword_ar)
            print(f"⚠️  WARNING: Keyword '{keyword_ar}' has no cached expansion (skipping)")
            print(f"   → Add this keyword again via frontend to generate expansion")
    
    if skipped:
        print(f"\n⚠️  {len(skipped)} keywords skipped (no cached expansions)")
        print(f"   Skipped: {', '.join(skipped[:3])}")
        if len(skipped) > 3:
            print(f"   ... and {len(skipped) - 3} more")
        print(f"   → To fix: Re-add these keywords via frontend\n")
    
    return expansions


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("KEYWORD EXPANSION TEST")
    print("=" * 80)
    
    test_keywords = [
        "السعودية",
        "الرياض",
        "ترامب",
        "النفط"
    ]
    
    for keyword in test_keywords:
        print(f"\nExpanding: {keyword}")
        expansion = expand_keyword(keyword)
        print(json.dumps(expansion, ensure_ascii=False, indent=2))
        print("-" * 80)
