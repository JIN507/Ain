"""
Translation Service for Articles
Translates article text to Arabic using Google Translate

PHASE 3 UPDATE: Removed in-memory cache to reduce RAM usage.
Translations are saved directly to Article model (title_ar, summary_ar).
No need for RAM cache since articles are stored in database.
"""
from datetime import datetime
from googletrans import Translator
from arabic_utils import is_arabic_text
import os

# Configuration
TRANSLATION_TIMEOUT_S = int(os.getenv('TRANSLATION_TIMEOUT_S', '8'))

# Initialize translator
translator = Translator()


def translate_to_arabic(text, source_lang='auto'):
    """
    Translate text to Arabic (no caching - saves RAM)
    
    Args:
        text: Text to translate
        source_lang: Source language code (default: auto-detect)
        
    Returns:
        dict: {
            'original': str,
            'translated': str,
            'source_lang': str,
            'translation_status': 'success' | 'failed' | 'skipped',
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
    
    # Check if already Arabic - no translation needed
    if is_arabic_text(text):
        return {
            'original': text,
            'translated': text,
            'source_lang': 'ar',
            'translation_status': 'skipped',
            'updated_at': datetime.utcnow().isoformat()
        }
    
    # Translate directly (no cache)
    try:
        result = translator.translate(text, src=source_lang, dest='ar')
        
        if result and result.text:
            return {
                'original': text,
                'translated': result.text,
                'source_lang': result.src if hasattr(result, 'src') else source_lang,
                'translation_status': 'success',
                'updated_at': datetime.utcnow().isoformat()
            }
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


# Backward compatibility alias
def translate_to_arabic_cached(text, source_lang='auto'):
    """Alias for backward compatibility - now just calls translate_to_arabic"""
    return translate_to_arabic(text, source_lang)


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
    title_result = translate_to_arabic(title, detected_lang)
    
    # Translate summary
    summary_result = translate_to_arabic(summary, detected_lang) if summary else {
        'translated': '',
        'translation_status': 'skipped'
    }
    
    # Determine overall status
    title_status = title_result['translation_status']
    summary_status = summary_result['translation_status']
    
    if title_status in ['success', 'skipped'] and summary_status in ['success', 'skipped']:
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
    """No-op - cache removed in Phase 3"""
    print("ℹ️ Translation cache removed (Phase 3) - no action needed")


def get_cache_stats():
    """Return empty stats - cache removed in Phase 3"""
    return {
        'total_entries': 0,
        'cache_size_kb': 0,
        'note': 'RAM cache removed in Phase 3 - translations saved directly to articles'
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
