"""
Translation Service using Google Translate (FREE - No API Key Required)
Replaces OpenAI for translation functionality
"""
import json
from googletrans import Translator
from langdetect import detect, LangDetectException

# Initialize Google Translator (free, no API key needed)
translator = Translator()

# PHASE 3: Removed in-memory caches to prevent RAM overflow
# Translations are saved to database, no need for RAM cache

def clear_all_caches():
    """No-op - caches removed in Phase 3 to save RAM"""
    print("ℹ️ RAM caches removed (Phase 3) - no action needed")


def detect_language(text):
    """
    Detect the language of given text
    
    Args:
        text: Text to detect language for
    
    Returns:
        Language code (e.g., 'ar', 'en', 'fr')
    """
    if not text or len(text.strip()) < 3:
        return 'unknown'
    
    # Direct detection - no caching to save RAM
    try:
        detected = detect(text)
        return detected
    except LangDetectException as e:
        print(f"⚠️ Language detection error: {str(e)}")
        return 'unknown'
    except Exception as e:
        print(f"❌ Language detection error: {str(e)}")
        return 'unknown'


def translate_keyword(keyword_ar):
    """
    Translate Arabic keyword to 7 languages using Google Translate
    
    Args:
        keyword_ar: Arabic keyword
    
    Returns:
        Dict with translations: {en, fr, tr, ur, zh, ru, es}
    """
    print(f"🔤 Translating keyword: {keyword_ar}")
    
    # Direct translation - no caching to save RAM (saved to DB instead)
    
    target_languages = {
        'en': 'English',
        'fr': 'French', 
        'tr': 'Turkish',
        'ur': 'Urdu',
        'zh-cn': 'Chinese',
        'ru': 'Russian',
        'es': 'Spanish'
    }
    
    translations = {}
    
    try:
        for lang_code, lang_name in target_languages.items():
            try:
                # Translate using Google Translate
                result = translator.translate(keyword_ar, src='ar', dest=lang_code)
                
                # Store with simplified key (zh instead of zh-cn)
                key = 'zh' if lang_code == 'zh-cn' else lang_code
                translations[key] = result.text
                
                print(f"   ✅ {lang_name}: {result.text}")
                
            except Exception as e:
                print(f"   ⚠️ {lang_name} translation failed: {str(e)}")
                key = 'zh' if lang_code == 'zh-cn' else lang_code
                translations[key] = None
        
        # PHASE 3: Cache removed - translations saved to DB instead
        return translations
        
    except Exception as e:
        print(f"❌ Translation error: {str(e)}")
        # Return None for all languages
        return {
            'en': None,
            'fr': None,
            'tr': None,
            'ur': None,
            'zh': None,
            'ru': None,
            'es': None
        }


def translate_to_arabic(title, summary=None):
    """
    Translate article title and summary to Arabic using Google Translate
    
    Args:
        title: Article title (non-Arabic)
        summary: Article summary (non-Arabic, optional)
    
    Returns:
        Dict with {title_ar, summary_ar} or None on error
    """
    if not title:
        return None
    
    try:
        # Translate title
        title_result = translator.translate(title, src='auto', dest='ar')
        title_ar = title_result.text
        
        # Translate summary if provided
        summary_ar = title_ar  # Default to title if no summary
        if summary and summary.strip():
            summary_result = translator.translate(summary, src='auto', dest='ar')
            summary_ar = summary_result.text
        
        return {
            'title_ar': title_ar,
            'summary_ar': summary_ar
        }
        
    except Exception as e:
        print(f"❌ Article translation error: {str(e)}")
        return None


# Placeholder for sentiment analysis (removed, will be added in future update)
def analyze_sentiment(text_ar, keyword):
    """
    Sentiment analysis placeholder
    
    NOTE: Sentiment analysis disabled for now.
    Will be implemented in a future update with a suitable API.
    
    Args:
        text_ar: Arabic text (title + summary)
        keyword: Arabic keyword
    
    Returns:
        Tuple of (sentiment_label, sentiment_score)
        Currently returns ('محايد', None) for all
    """
    # Default to neutral sentiment
    return ('محايد', None)
