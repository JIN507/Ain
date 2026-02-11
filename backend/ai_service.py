"""
AI Service for Ain News Monitor
Uses Google Gemini 2.0 Flash for:
  - Daily Brief (ملخص ذكي): Summarize all day's articles into one concise paragraph
  - Deep Sentiment (لماذا؟): Explain why an article is positive/negative
"""
import os
import json
import requests

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-2.0-flash'
GEMINI_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'


def _call_gemini(prompt, max_tokens=1024):
    """Call Gemini API and return the text response."""
    if not GEMINI_API_KEY:
        raise ValueError('GEMINI_API_KEY not configured')

    payload = {
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {
            'maxOutputTokens': max_tokens,
            'temperature': 0.4,
        },
    }

    resp = requests.post(
        GEMINI_URL,
        params={'key': GEMINI_API_KEY},
        headers={'Content-Type': 'application/json'},
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        error_msg = resp.text[:500]
        print(f'[AI] ❌ Gemini API error {resp.status_code}: {error_msg}')
        raise Exception(f'Gemini API error: {resp.status_code}')

    data = resp.json()
    try:
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise Exception('Unexpected Gemini response format')


def generate_daily_brief(articles):
    """
    Generate a concise Arabic daily brief from a list of articles.
    Sends only titles + sentiment + source to minimize tokens.
    Groups by keyword for better structure.
    """
    if not articles:
        return 'لا توجد مقالات لتلخيصها اليوم.'

    # Group articles by keyword
    keyword_groups = {}
    for a in articles:
        kw = a.get('keyword_original', 'عام')
        if not kw:
            kw = 'عام'
        if kw not in keyword_groups:
            keyword_groups[kw] = []
        keyword_groups[kw].append(a)

    # Build compact article list (titles + sentiment only — saves tokens)
    lines = []
    for kw, group in keyword_groups.items():
        lines.append(f'\n## كلمة مفتاحية: {kw} ({len(group)} مقال)')
        for a in group[:50]:  # Cap at 50 per keyword to control token usage
            title = a.get('title_ar', a.get('title_original', ''))
            sentiment = a.get('sentiment', a.get('sentiment_label', ''))
            source = a.get('source_name', '')
            lines.append(f'- [{sentiment}] {title} ({source})')

    article_text = '\n'.join(lines)

    prompt = f"""أنت محلل أخبار محترف. لديك قائمة بأهم الأخبار التي تم رصدها اليوم.

اكتب ملخصاً ذكياً باللغة العربية يتضمن:
1. أبرز المواضيع والاتجاهات الرئيسية
2. النقاط الإيجابية والسلبية البارزة
3. توصية أو ملاحظة مهمة

اكتب بأسلوب مهني ومختصر. لا تتجاوز 3 فقرات. لا تذكر أسماء المصادر إلا إذا كانت مهمة جداً.

الأخبار المرصودة:
{article_text}

الملخص الذكي:"""

    return _call_gemini(prompt, max_tokens=800)


def explain_sentiment(title, summary, sentiment, source_name='', country=''):
    """
    Explain why an article has a certain sentiment label.
    On-demand — called only when user clicks "لماذا؟"
    """
    prompt = f"""أنت محلل مشاعر إخباري. اشرح بإيجاز (3-4 جمل) باللغة العربية لماذا هذا الخبر يُصنف كـ "{sentiment}".

العنوان: {title}
الملخص: {summary or 'غير متوفر'}
المصدر: {source_name}
الدولة: {country}

اشرح التصنيف بناءً على:
- الكلمات والعبارات المؤثرة في النص
- السياق العام للخبر
- التأثير المحتمل على القارئ

التحليل:"""

    return _call_gemini(prompt, max_tokens=300)
