"""
OpenAI Service for Translation and Sentiment Analysis
Uses GPT-4o-mini for keyword translation and article processing
"""
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from langdetect import detect, LangDetectException

# Load environment variables
load_dotenv()

# Get and clean API key (remove any whitespace/newlines)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    OPENAI_API_KEY = OPENAI_API_KEY.strip()

# Initialize OpenAI client
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        # Quick validation test
        # (Will be caught on first actual API call if key is invalid)
    except Exception as e:
        print(f"⚠️ Failed to initialize OpenAI client: {str(e)}")
        client = None
else:
    print("⚠️ OPENAI_API_KEY not found in environment")

# In-memory cache for session
_translation_cache = {}
_language_detection_cache = {}

def clear_all_caches():
    """Clear all in-memory caches"""
    global _translation_cache, _language_detection_cache
    _translation_cache.clear()
    _language_detection_cache.clear()
    print("🧹 Cleared all in-memory caches")

def analyze_article_with_gemini(title, summary, keyword):
    """
    Use OpenAI to translate and analyze article
    
    Args:
        title: Article title (any language)
        summary: Article summary (any language)
        keyword: Arabic keyword
    
    Returns:
        Dict with {title_ar, summary_ar, sentiment} or None on error
    """
    if not OPENAI_API_KEY or not client:
        print("⚠️ OPENAI_API_KEY not set. Skipping AI analysis.")
        return None
    
    try:
        # Build prompt
        prompt = f"""أنت محلل أخبار محترف متخصص في الترجمة وتحليل المشاعر.

**المقال الأصلي:**
العنوان: {title}
الملخص: {summary if summary else "غير متوفر"}

**الكلمة المفتاحية:** {keyword}

**المطلوب منك:**
1. ترجم العنوان إلى العربية (إذا لم يكن بالعربية أصلاً).
2. اكتب ملخصاً موجزاً للمقال في 2-3 جمل بالعربية الفصحى.
3. حلل المشاعر في المقال تجاه الكلمة المفتاحية "{keyword}":
   - إيجابي: إذا كان المقال يتحدث بشكل إيجابي عن الموضوع
   - سلبي: إذا كان المقال ينتقد أو يتحدث بشكل سلبي
   - محايد: إذا كان المقال إخباري بحت بدون رأي

**الرد يجب أن يكون JSON فقط بهذا الشكل:**
{{
  "title_ar": "العنوان المترجم بالعربية",
  "summary_ar": "ملخص موجز 2-3 جمل بالعربية",
  "sentiment": "إيجابي" أو "سلبي" أو "محايد"
}}

لا تضف أي نص آخر، فقط JSON."""

        # Generate response using OpenAI
        print(f"   🤖 Calling OpenAI API (gpt-4o-mini)...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت محلل أخبار محترف. أجب دائماً بتنسيق JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        print(f"   ✅ OpenAI response received")
        
        if not response or not response.choices:
            print("⚠️ Empty response from OpenAI")
            return None
        
        # Parse JSON response
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        # Validate result
        if 'title_ar' not in result or 'summary_ar' not in result or 'sentiment' not in result:
            print(f"⚠️ Invalid response format: {result}")
            return None
        
        # Normalize sentiment
        sentiment = result['sentiment'].strip()
        if sentiment not in ['إيجابي', 'سلبي', 'محايد']:
            # Try to map common variants
            if 'إيجاب' in sentiment or 'positive' in sentiment.lower():
                sentiment = 'إيجابي'
            elif 'سلب' in sentiment or 'negative' in sentiment.lower():
                sentiment = 'سلبي'
            else:
                sentiment = 'محايد'
        
        result['sentiment'] = sentiment
        
        print(f"✅ OpenAI analysis complete: {sentiment}")
        return result
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Response was: {result_text if 'result_text' in locals() else 'None'}")
        return None
    
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return None

def translate_keyword(keyword_ar, target_langs=['en', 'fr', 'tr', 'ur', 'zh', 'ru', 'es']):
    """
    Translate Arabic keyword to multiple languages using OpenAI
    
    Args:
        keyword_ar: Arabic keyword
        target_langs: List of target language codes (en, fr, tr, ur, zh, ru, es)
    
    Returns:
        Dict of {lang_code: translation} or empty dict on error
    """
    if not OPENAI_API_KEY or not client:
        print("⚠️ OPENAI_API_KEY not set. Cannot translate keywords.")
        return {}
    
    try:
        lang_names = {
            'en': 'English',
            'fr': 'French',
            'tr': 'Turkish',
            'ur': 'Urdu',
            'zh': 'Chinese',
            'ru': 'Russian',
            'es': 'Spanish'
        }
        
        langs_str = ', '.join([lang_names[l] for l in target_langs if l in lang_names])
        
        prompt = f"""ترجم الكلمة المفتاحية التالية من العربية إلى اللغات التالية: {langs_str}

الكلمة: {keyword_ar}

مهم جداً: احتفظ بالمعنى الدقيق للكلمة في جميع الترجمات. إذا كانت الكلمة تتكون من عدة كلمات، ترجم المعنى الكامل.

الرد يجب أن يكون JSON فقط بهذا الشكل:
{{
  "en": "translation in English",
  "fr": "translation in French",
  "tr": "translation in Turkish",
  "ur": "translation in Urdu",
  "zh": "translation in Chinese",
  "ru": "translation in Russian",
  "es": "translation in Spanish"
}}

لا تضف أي نص آخر، فقط JSON."""

        print(f"🔤 Translating keyword: {keyword_ar}")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت مترجم محترف متخصص في ترجمة الكلمات المفتاحية. أجب دائماً بتنسيق JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        if not response or not response.choices:
            return {}
        
        result_text = response.choices[0].message.content.strip()
        translations = json.loads(result_text)
        
        print(f"✅ Translated '{keyword_ar}':")
        for lang, trans in translations.items():
            print(f"   {lang}: {trans}")
        
        return translations
    
    except Exception as e:
        print(f"❌ Translation error: {str(e)}")
        return {}

def detect_language(text):
    """
    Detect language of text
    
    Args:
        text: Text to detect language
    
    Returns:
        Language code (en, ar, fr, etc.) or 'unknown'
    """
    try:
        if not text or len(text.strip()) < 10:
            return 'unknown'
        
        lang = detect(text)
        return lang
    except LangDetectException:
        return 'unknown'
    except Exception as e:
        print(f"❌ Language detection error: {str(e)}")
        return 'unknown'

def translate_to_arabic(title, summary):
    """
    Translate article title and summary to Arabic using OpenAI
    
    Args:
        title: Article title (non-Arabic)
        summary: Article summary (non-Arabic)
    
    Returns:
        Dict with {title_ar, summary_ar} or None on error
    """
    if not OPENAI_API_KEY or not client:
        print("⚠️ OPENAI_API_KEY not set. Cannot translate article.")
        return None
    
    try:
        prompt = f"""ترجم المقال التالي إلى العربية الفصحى:

العنوان: {title}
الملخص: {summary if summary else "غير متوفر"}

يجب أن تكون الترجمة:
1. دقيقة وتحافظ على المعنى الأصلي
2. بالعربية الفصحى
3. طبيعية وسلسة

الرد يجب أن يكون JSON فقط بهذا الشكل:
{{
  "title_ar": "العنوان المترجم بالعربية",
  "summary_ar": "الملخص المترجم بالعربية"
}}

لا تضف أي نص آخر، فقط JSON."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت مترجم محترف. أجب دائماً بتنسيق JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        if not response or not response.choices:
            return None
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        if 'title_ar' not in result or 'summary_ar' not in result:
            return None
        
        return result
    
    except Exception as e:
        print(f"❌ Article translation error: {str(e)}")
        return None

def analyze_sentiment(text_ar, keyword):
    """
    Analyze sentiment of Arabic text towards a keyword
    
    Args:
        text_ar: Arabic text (title + summary)
        keyword: Arabic keyword
    
    Returns:
        Tuple of (sentiment_label, sentiment_score)
        - sentiment_label: 'إيجابي', 'سلبي', or 'محايد' (Arabic)
        - sentiment_score: confidence score (0-100) or None
    """
    if not OPENAI_API_KEY or not client:
        print("⚠️ OPENAI_API_KEY not set. Cannot analyze sentiment.")
        return ('محايد', None)
    
    try:
        prompt = f"""حلل مشاعر النص التالي تجاه الكلمة المفتاحية "{keyword}":

النص: {text_ar}

حدد المشاعر:
- إيجابي: إذا كان النص يتحدث بشكل إيجابي عن الموضوع
- سلبي: إذا كان النص ينتقد أو يتحدث بشكل سلبي
- محايد: إذا كان النص إخباري بحت بدون رأي

أيضاً حدد درجة الثقة (confidence) من 0 إلى 100.

الرد يجب أن يكون JSON فقط بهذا الشكل:
{{
  "sentiment": "إيجابي" أو "سلبي" أو "محايد",
  "confidence": 85
}}

لا تضف أي نص آخر، فقط JSON."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "أنت محلل مشاعر محترف. أجب دائماً بتنسيق JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        if not response or not response.choices:
            return ('محايد', None)
        
        result_text = response.choices[0].message.content.strip()
        result = json.loads(result_text)
        
        sentiment = result.get('sentiment', 'محايد').strip()
        confidence = result.get('confidence')
        
        # Normalize sentiment to Arabic
        if sentiment in ['إيجابي', 'ايجابي', 'positive', 'pos']:
            sentiment = 'إيجابي'
        elif sentiment in ['سلبي', 'negative', 'neg']:
            sentiment = 'سلبي'
        else:
            sentiment = 'محايد'
        
        # Format confidence score
        score = f"{confidence}%" if confidence else None
        
        return (sentiment, score)
    
    except Exception as e:
        print(f"❌ Sentiment analysis error: {str(e)}")
        return ('محايد', None)
