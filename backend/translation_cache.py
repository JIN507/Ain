"""
Translation Caching Service
Caches article translations to Arabic to avoid redundant API calls
"""
import hashlib
from datetime import datetime, timedelta
from googletrans import Translator
from arabic_utils import is_arabic_text
import os

# Configuration
TRANSLATION_TTL_DAYS = int(os.getenv('TRANSLATION_TTL_DAYS', '30'))
TRANSLATION_TIMEOUT_S = int(os.getenv('TRANSLATION_TIMEOUT_S', '8'))

# Initialize translator
translator = Translator()

# In-memory cache for translations
_translation_cache = {}


def get_text_hash(text):
    """
    Generate a hash for text to use as cache key
    
    Args:
        text: Text to hash
        
    Returns:
        MD5 hash string
    """
    if not text:
        return None
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def translate_to_arabic_cached(text, source_lang='auto'):
    """
    Translate text to Arabic with caching
    
    Args:
        text: Text to translate
        source_lang: Source language code (default: auto-detect)
        
    Returns:
        dict: {
            'original': str,
            'translated': str,
            'source_lang': str,
            'translation_status': 'cached' | 'success' | 'failed' | 'skipped',
            'updated_at': str
        }
    """
    if not text or not text.strip():
        return {
            'original': text,
            'translated': text,
            'source_lang': 'unknown',
            'translation_status': 'skipped',
            'updated_at': datetime.utcnow().isoformat()
        }
    
    # Check if already Arabic
    if is_arabic_text(text):
        return {
            'original': text,
            'translated': text,
            'source_lang': 'ar',
            'translation_status': 'skipped',
            'updated_at': datetime.utcnow().isoformat()
        }
    
    # Check cache
    text_hash = get_text_hash(text)
    cache_key = f"{text_hash}_ar"
    
    if cache_key in _translation_cache:
        cached = _translation_cache[cache_key]
        cache_time = datetime.fromisoformat(cached['updated_at'])
        if datetime.utcnow() - cache_time < timedelta(days=TRANSLATION_TTL_DAYS):
            cached['translation_status'] = 'cached'
            return cached
    
    # Translate
    try:
        result = translator.translate(text, src=source_lang, dest='ar')
        
        if result and result.text:
            translation_result = {
                'original': text,
                'translated': result.text,
                'source_lang': result.src if hasattr(result, 'src') else source_lang,
                'translation_status': 'success',
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Cache it
            _translation_cache[cache_key] = translation_result
            
            return translation_result
        else:
            return {
                'original': text,
                'translated': text,  # Fallback to original
                'source_lang': source_lang,
                'translation_status': 'failed',
                'updated_at': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        print(f"   ❌ Translation failed: {str(e)[:50]}")
        return {
            'original': text,
            'translated': text,  # Fallback to original
            'source_lang': source_lang,
            'translation_status': 'failed',
            'error': str(e)[:100],
            'updated_at': datetime.utcnow().isoformat()
        }


def translate_article_to_arabic(title, summary, detected_lang='auto'):
    """
    Translate article title and summary to Arabic
    
    Args:
        title: Article title
        summary: Article summary
        detected_lang: Detected language code
        
    Returns:
        dict: {
            'title_ar': str,
            'summary_ar': str,
            'title_status': str,
            'summary_status': str,
            'overall_status': 'success' | 'partial' | 'failed'
        }
    """
    # Translate title
    title_result = translate_to_arabic_cached(title, detected_lang)
    
    # Translate summary
    summary_result = translate_to_arabic_cached(summary, detected_lang) if summary else {
        'translated': '',
        'translation_status': 'skipped'
    }
    
    # Determine overall status
    title_status = title_result['translation_status']
    summary_status = summary_result['translation_status']
    
    if title_status in ['success', 'cached', 'skipped'] and summary_status in ['success', 'cached', 'skipped']:
        overall_status = 'success'
    elif title_status == 'failed' and summary_status == 'failed':
        overall_status = 'failed'
    else:
        overall_status = 'partial'
    
    return {
        'title_ar': title_result['translated'],
        'summary_ar': summary_result['translated'],
        'title_status': title_status,
        'summary_status': summary_status,
        'overall_status': overall_status,
        'detected_lang': title_result.get('source_lang', detected_lang)
    }


def clear_translation_cache():
    """Clear the translation cache"""
    _translation_cache.clear()
    print("🧹 Cleared translation cache")


def get_cache_stats():
    """Get cache statistics"""
    return {
        'total_entries': len(_translation_cache),
        'cache_size_kb': len(str(_translation_cache)) / 1024
    }


# Test function
if __name__ == "__main__":
    print("=" * 80)
    print("TRANSLATION CACHING TEST")
    print("=" * 80)
    
    test_articles = [
        {
            'title': 'Trump announces new policy',
            'summary': 'The president made an announcement about immigration.',
            'lang': 'en'
        },
        {
            'title': 'France dévoile son plan',
            'summary': 'Le gouvernement français a présenté un nouveau plan économique.',
            'lang': 'fr'
        },
        {
            'title': 'السعودية تعلن عن مشروع جديد',
            'summary': 'أعلنت المملكة العربية السعودية عن مشروع ضخم.',
            'lang': 'ar'
        }
    ]
    
    for article in test_articles:
        print(f"\nTranslating: {article['title']}")
        result = translate_article_to_arabic(
            article['title'],
            article['summary'],
            article['lang']
        )
        print(f"   Title AR: {result['title_ar']}")
        print(f"   Summary AR: {result['summary_ar'][:80]}...")
        print(f"   Status: {result['overall_status']}")
    
    print(f"\nCache stats: {get_cache_stats()}")
