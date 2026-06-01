"""
AI Service for Ain News Monitor
Uses OpenAI GPT-4o-mini for:
  - Daily Brief (ملخص ذكي): Summarize all day's articles into one concise paragraph
  - Deep Sentiment (لماذا؟): Explain why an article is positive/negative
"""
import os
import requests

OPENAI_API_KEY = ''

# Load from .env file first (local dev), then fall back to environment
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path, encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('OPENAI_API_KEY='):
                OPENAI_API_KEY = line.strip().split('=', 1)[1].strip()
                break

if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

OPENAI_MODEL = 'gpt-4o-mini'
OPENAI_URL = 'https://api.openai.com/v1/chat/completions'


def _call_llm(prompt, max_tokens=1024):
    """Call OpenAI API and return the text response."""
    if not OPENAI_API_KEY:
        raise ValueError('OPENAI_API_KEY not configured')

    payload = {
        'model': OPENAI_MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': max_tokens,
        'temperature': 0.4,
    }

    resp = requests.post(
        OPENAI_URL,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OPENAI_API_KEY}',
        },
        json=payload,
        timeout=30,
    )

    if resp.status_code != 200:
        error_msg = resp.text[:500]
        print(f'[AI] ❌ OpenAI API error {resp.status_code}: {error_msg}')
        raise Exception(f'OpenAI API error: {resp.status_code}')

    data = resp.json()
    try:
        return data['choices'][0]['message']['content']
    except (KeyError, IndexError):
        raise Exception('Unexpected OpenAI response format')


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

    prompt = f"""أنت محلل أخبار محترف تكتب من منظور سعودي. لديك قائمة بأهم الأخبار التي تم رصدها اليوم.

اكتب ملخصاً ذكياً باللغة العربية يتضمن:
1. أبرز المواضيع والاتجاهات الرئيسية، مع تفسير أهميتها وانعكاسها على السعودية ومصالحها الإقليمية أو الاقتصادية أو السياسية أو الاجتماعية
2. النقاط الإيجابية والسلبية البارزة من زاوية سعودية، وليس من زاوية الدولة التي تتناولها الأخبار
3.  توصية أو ملاحظة مهمة تساعد القارئ     أو المهتم بالشأن العام على فهم دلالة الأخبار و والاسترسال في مجمل الاخبار بتلخصيها بشكل مناسب واضح وشامل تأثيرها على المملكة

التزم دائماً بالمنظور السعودي عند تحليل أي دولة أو حدث، حتى لو كانت الأخبار محلية لدولة أخرى. لا تتبنَّ خطاب أو أولوية الدولة المذكورة في الأخبار، بل قيّم الحدث بناءً على أثره المحتمل على السعودية، مكانتها، اقتصادها، أمنها، علاقاتها، صورتها، أو مصالح مواطنيها.

اكتب بأسلوب مهني ومختصر ومحايد. لا تتجاوز 3 فقرات. لا تذكر أسماء المصادر إلا إذا كانت مهمة جداً.

الأخبار المرصودة:
{article_text}

الملخص الذكي:"""

    return _call_llm(prompt, max_tokens=800)


def explain_sentiment(title, summary, sentiment, source_name='', country='', keyword=''):
    """
    Analyze article sentiment relative to its keyword.
    On-demand — called only when user clicks "حلل المشاعر"
    """
    prompt = f"""أنت محلل أخبار متخصص تكتب من منظور سعودي. حلل مشاعر هذا الخبر بالنسبة للكلمة المفتاحية "{keyword or 'الموضوع الرئيسي'}"، مع تقييم الخبر بناءً على أثره المحتمل على السعودية ومصالحها، وليس بناءً على منظور الدولة المذكورة في الخبر.

العنوان: {title}
الملخص: {summary or 'غير متوفر'}
الكلمة المفتاحية: {keyword or 'غير محددة'}
الدولة: {country}

المطلوب:
1. هل هذا الخبر إيجابي أم سلبي أم محايد بالنسبة لـ "{keyword or 'الموضوع'}" من زاوية سعودية؟
2. اشرح السبب في 2-3 جمل مختصرة، مع ربط التحليل بتأثير الخبر على السعودية أو مصالحها السياسية أو الاقتصادية أو الأمنية أو الاجتماعية أو صورتها العامة.
3. ما التأثير المحتمل على "{keyword or 'الموضوع'}" داخل السياق السعودي أو على علاقة السعودية بالدولة/الملف المذكور؟

التزم دائماً بالمنظور السعودي حتى لو كان الخبر محلياً لدولة أخرى. لا تتبنَّ خطاب الدولة المذكورة أو أولوياتها الداخلية، ولا تحلل الخبر كما لو أن القارئ من تلك الدولة. قيّم الخبر من حيث انعكاسه على السعودية، أمنها، اقتصادها، علاقاتها، مكانتها الإقليمية والدولية، مصالح مواطنيها، أو استقرار المنطقة.

اكتب الإجابة باللغة العربية بشكل مختصر ومباشر. لا تستخدم عناوين أو ترقيم."""


    return _call_llm(prompt, max_tokens=300)
