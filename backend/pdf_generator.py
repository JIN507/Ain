"""
PDF Report Generator for Ain News Monitor — Professional Card Layout
Uses reportlab + arabic-reshaper + python-bidi (100% pure Python, zero system deps)

Produces a PDF that mirrors the app's dark-teal UI theme with card-style articles,
colored badges, sentiment indicators, and page-numbered footers.
"""
import os
import io
import requests
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False
    print("[PDF] ⚠️ arabic-reshaper/python-bidi not installed — Arabic text may render incorrectly")

# ─── Font management ────────────────────────────────────────────

FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')

FONT_URLS = {
    'Amiri': 'https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf',
    'Amiri-Bold': 'https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Bold.ttf',
}

_fonts_ready = False


def _ensure_fonts():
    """Download Arabic font if needed and register with reportlab."""
    global _fonts_ready
    if _fonts_ready:
        return True

    os.makedirs(FONTS_DIR, exist_ok=True)

    for name, url in FONT_URLS.items():
        path = os.path.join(FONTS_DIR, f'{name}.ttf')
        if not os.path.exists(path):
            try:
                print(f'[PDF] Downloading font {name}...')
                r = requests.get(url, timeout=15)
                r.raise_for_status()
                with open(path, 'wb') as f:
                    f.write(r.content)
                print(f'[PDF] ✅ Font {name} downloaded ({len(r.content)} bytes)')
            except Exception as e:
                print(f'[PDF] ❌ Failed to download font {name}: {e}')
                return False
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            print(f'[PDF] ❌ Failed to register font {name}: {e}')
            return False

    _fonts_ready = True
    print('[PDF] ✅ All fonts ready')
    return True


# ─── Arabic text processing ─────────────────────────────────────

def _ar(text):
    """Reshape Arabic text for correct PDF rendering and escape for XML."""
    if not text:
        return ''
    text = str(text)
    safe = escape(text)
    if not HAS_BIDI:
        return safe
    try:
        reshaped = arabic_reshaper.reshape(text)
        bidi = get_display(reshaped)
        return escape(bidi)
    except Exception:
        return safe


# ─── Theme colors (matching app UI) ─────────────────────────────

TEAL_PRIMARY  = colors.HexColor('#0f766e')
TEAL_LIGHT    = colors.HexColor('#14b8a6')
TEAL_MINT     = colors.HexColor('#99f6e4')
GREEN_PRIMARY = colors.HexColor('#059669')
GREEN_BG      = colors.HexColor('#ecfdf5')
SLATE_900     = colors.HexColor('#0f172a')
SLATE_700     = colors.HexColor('#334155')
SLATE_500     = colors.HexColor('#64748b')
SLATE_400     = colors.HexColor('#94a3b8')
SLATE_200     = colors.HexColor('#e2e8f0')
SLATE_100     = colors.HexColor('#f1f5f9')
WHITE         = colors.white

# Badge palette
BADGE_COUNTRY_BG  = colors.HexColor('#dbeafe')
BADGE_COUNTRY_FG  = colors.HexColor('#1e40af')
BADGE_SOURCE_BG   = colors.HexColor('#fef3c7')
BADGE_SOURCE_FG   = colors.HexColor('#92400e')
BADGE_KEYWORD_BG  = colors.HexColor('#e0e7ff')
BADGE_KEYWORD_FG  = colors.HexColor('#3730a3')

# Sentiment palette
SENT_POS_BG = colors.HexColor('#d1fae5')
SENT_POS_FG = colors.HexColor('#065f46')
SENT_NEG_BG = colors.HexColor('#fee2e2')
SENT_NEG_FG = colors.HexColor('#991b1b')
SENT_NEU_BG = colors.HexColor('#f3f4f6')
SENT_NEU_FG = colors.HexColor('#374151')


# ─── PDF generation ──────────────────────────────────────────────

def generate_report_pdf(articles, title='تقرير أخبار عين', stats=None, brief=None):
    """
    Generate a professional PDF report matching the Ain app UI theme.
    Returns PDF bytes.
    """
    has_fonts = _ensure_fonts()
    fn = 'Amiri' if has_fonts else 'Helvetica'
    fb = 'Amiri-Bold' if has_fonts else 'Helvetica-Bold'
    ar = _ar if has_fonts else (lambda t: escape(str(t)) if t else '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=20 * mm,
    )
    pw = A4[0] - 30 * mm  # usable page width
    now = datetime.utcnow()

    # ── Shared styles ──
    s_logo = ParagraphStyle(
        'Logo', fontName=fb, fontSize=36, alignment=TA_CENTER,
        textColor=WHITE, leading=44,
    )
    s_brand = ParagraphStyle(
        'Brand', fontName=fn, fontSize=12, alignment=TA_CENTER,
        textColor=TEAL_MINT, leading=16,
    )
    s_report_title = ParagraphStyle(
        'ReportTitle', fontName=fb, fontSize=16, alignment=TA_CENTER,
        textColor=TEAL_PRIMARY, leading=24, spaceBefore=2 * mm,
    )
    s_meta_center = ParagraphStyle(
        'MetaCenter', fontName=fn, fontSize=9, alignment=TA_CENTER,
        textColor=SLATE_500, leading=14,
    )
    s_section = ParagraphStyle(
        'Section', fontName=fb, fontSize=13, alignment=TA_CENTER,
        textColor=WHITE, leading=20,
    )
    s_page_footer = ParagraphStyle(
        'PageFooter', fontName=fn, fontSize=9, alignment=TA_CENTER,
        textColor=SLATE_400, spaceBefore=8 * mm,
    )

    elements = []

    # ══════════════════════════════════════════════════════════════
    # HEADER BANNER  (teal background with logo)
    # ══════════════════════════════════════════════════════════════
    header_rows = [
        [Paragraph(ar('عين'), s_logo)],
        [Paragraph(ar('نظام رصد الأخبار'), s_brand)],
    ]
    header = Table(header_rows, colWidths=[pw])
    header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TEAL_PRIMARY),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (0, 0), 18),
        ('BOTTOMPADDING', (0, -1), (0, -1), 14),
        ('TOPPADDING',    (0, 1), (0, 1), 0),
    ]))
    elements.append(header)

    # Info strip (light green background below banner)
    meta_text = (
        f'{now.strftime("%Y-%m-%d")}'
        f'&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'
        f'{now.strftime("%H:%M")} UTC'
        f'&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;'
        f'{len(articles)} {ar("خبر")}'
    )
    info_rows = [
        [Paragraph(ar(title), s_report_title)],
        [Paragraph(meta_text, s_meta_center)],
    ]
    info = Table(info_rows, colWidths=[pw])
    info.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GREEN_BG),
        ('BOX',           (0, 0), (-1, -1), 1.5, TEAL_PRIMARY),
        ('TOPPADDING',    (0, 0), (0, 0), 6),
        ('BOTTOMPADDING', (0, -1), (0, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 15),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 15),
    ]))
    elements.append(info)
    elements.append(Spacer(1, 8 * mm))

    # ══════════════════════════════════════════════════════════════
    # AI BRIEF (ملخص ذكي)
    # ══════════════════════════════════════════════════════════════
    if brief and isinstance(brief, str) and brief.strip():
        s_brief_title = ParagraphStyle(
            'BriefTitle', fontName=fb, fontSize=13, alignment=TA_RIGHT,
            textColor=WHITE, leading=20,
        )
        s_brief_body = ParagraphStyle(
            'BriefBody', fontName=fn, fontSize=11, alignment=TA_RIGHT,
            textColor=SLATE_700, leading=20, spaceBefore=2 * mm,
        )
        # Section header
        brief_header = Table(
            [[Paragraph(ar('ملخص ذكي'), s_brief_title)]],
            colWidths=[pw],
        )
        brief_header.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), TEAL_PRIMARY),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('TOPPADDING',    (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(brief_header)
        # Brief content box
        brief_paragraphs = []
        for line in brief.strip().split('\n'):
            line = line.strip()
            if line:
                brief_paragraphs.append(Paragraph(ar(line), s_brief_body))
        if not brief_paragraphs:
            brief_paragraphs.append(Paragraph(ar(brief.strip()), s_brief_body))
        brief_box = Table(
            [[p] for p in brief_paragraphs],
            colWidths=[pw],
        )
        brief_box.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), colors.HexColor('#f0fdfa')),
            ('BOX',           (0, 0), (-1, -1), 1, TEAL_LIGHT),
            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
            ('TOPPADDING',    (0, 0), (0, 0), 10),
            ('BOTTOMPADDING', (0, -1), (0, -1), 10),
        ]))
        elements.append(brief_box)
        elements.append(Spacer(1, 8 * mm))

    # ══════════════════════════════════════════════════════════════
    # SECTION TITLE BAR
    # ══════════════════════════════════════════════════════════════
    section_t = Table(
        [[Paragraph(ar(f'الأخبار المرصودة ({len(articles)} خبر)'), s_section)]],
        colWidths=[pw],
    )
    section_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), TEAL_PRIMARY),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(section_t)
    elements.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════
    # ARTICLE CARDS
    # ══════════════════════════════════════════════════════════════
    for i, article in enumerate(articles):
        card = _build_article_card(article, i, pw, fn, fb, ar)
        elements.append(KeepTogether([card, Spacer(1, 5 * mm)]))

    # ══════════════════════════════════════════════════════════════
    # REPORT FOOTER
    # ══════════════════════════════════════════════════════════════
    elements.append(Spacer(1, 4 * mm))
    foot_t = Table(
        [[Paragraph(
            ar('نظام أخبار عين — تم إنشاء هذا التقرير تلقائياً') +
            f'&nbsp;&nbsp;© {now.strftime("%Y")}',
            s_page_footer,
        )]],
        colWidths=[pw],
    )
    foot_t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), SLATE_100),
        ('BOX',           (0, 0), (-1, -1), 0.5, SLATE_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(foot_t)

    # ── Build with page-number footer ──
    def _on_page(canvas, doc_obj):
        canvas.saveState()
        # Divider line
        canvas.setStrokeColor(SLATE_200)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, 14 * mm, A4[0] - 15 * mm, 14 * mm)
        # Page number
        canvas.setFont(fn, 8)
        canvas.setFillColor(SLATE_400)
        canvas.drawCentredString(A4[0] / 2, 9 * mm, str(doc_obj.page))
        canvas.restoreState()

    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    buffer.seek(0)
    return buffer.getvalue()


# ─── Card builder ────────────────────────────────────────────────

def _build_article_card(article, index, pw, fn, fb, ar):
    """Build a single article as a card-style Table matching the app UI."""
    # ── Extract fields ──
    art_title = (
        article.get('title_ar')
        or article.get('title')
        or article.get('title_original')
        or 'بدون عنوان'
    )
    source    = article.get('source_name', article.get('source', ''))
    country   = article.get('country', '')
    if isinstance(country, list):
        country = ', '.join(country)
    keyword   = article.get('keyword_original', article.get('keyword', ''))
    sentiment = article.get('sentiment', 'محايد') or 'محايد'
    summary   = (
        article.get('summary_ar')
        or article.get('summary')
        or article.get('description')
        or article.get('summary_original')
        or ''
    )
    url       = article.get('url', article.get('link', ''))
    pub_date  = article.get('published_at', article.get('pub_date', ''))

    # Truncate summary
    if summary and len(str(summary)) > 350:
        summary = str(summary)[:350] + '...'

    # ── Per-card styles ──
    s_badge = ParagraphStyle('cb_%d' % index, fontName=fn, fontSize=8,
                             alignment=TA_RIGHT, leading=14, textColor=SLATE_500)
    s_title = ParagraphStyle('ct_%d' % index, fontName=fb, fontSize=11,
                             alignment=TA_RIGHT, textColor=SLATE_900, leading=17)
    s_body  = ParagraphStyle('cs_%d' % index, fontName=fn, fontSize=9,
                             alignment=TA_RIGHT, textColor=SLATE_700, leading=15)
    s_foot  = ParagraphStyle('cf_%d' % index, fontName=fn, fontSize=8,
                             alignment=TA_RIGHT, textColor=SLATE_500, leading=12)
    s_url   = ParagraphStyle('cu_%d' % index, fontName=fn, fontSize=7,
                             alignment=TA_RIGHT, textColor=TEAL_PRIMARY, leading=10)

    # ── Row 1: Article number + badges ──
    badge_parts = [
        f'<font backColor="#0f766e" color="#ffffff">&nbsp;'
        f'{ar("خبر " + str(index + 1))}&nbsp;</font>'
    ]
    if country:
        badge_parts.append(
            f'<font backColor="#dbeafe" color="#1e40af">'
            f'&nbsp;{ar(country)}&nbsp;</font>'
        )
    if source:
        badge_parts.append(
            f'<font backColor="#fef3c7" color="#92400e">'
            f'&nbsp;{ar(source)}&nbsp;</font>'
        )
    if keyword:
        badge_parts.append(
            f'<font backColor="#e0e7ff" color="#3730a3">'
            f'&nbsp;{ar(keyword)}&nbsp;</font>'
        )
    row_badges = Paragraph('&nbsp;&nbsp;'.join(badge_parts), s_badge)

    # ── Row 2: Title ──
    row_title = Paragraph(ar(art_title), s_title)

    # ── Row 3: Summary ──
    row_summary = Paragraph(ar(summary), s_body) if summary else None

    # ── Row 4: Footer — sentiment + date ──
    sent_map = {
        'إيجابي': ('#d1fae5', '#065f46'),
        'سلبي':   ('#fee2e2', '#991b1b'),
    }
    sbg, sfg = sent_map.get(sentiment, ('#f3f4f6', '#374151'))

    foot_parts = [
        f'<font backColor="{sbg}" color="{sfg}">'
        f'&nbsp;{ar(sentiment)}&nbsp;</font>'
    ]

    date_str = _format_date(pub_date)
    if date_str:
        foot_parts.append(f'<font color="#94a3b8">{escape(date_str)}</font>')

    row_footer = Paragraph(
        '&nbsp;&nbsp;|&nbsp;&nbsp;'.join(foot_parts), s_foot,
    )

    # ── Row 5: URL ──
    row_url = None
    if url:
        safe_url = escape(str(url))
        display  = safe_url[:80] + '...' if len(safe_url) > 80 else safe_url
        row_url  = Paragraph(
            f'<link href="{safe_url}">'
            f'<font color="#0f766e" size="7">{display}</font></link>',
            s_url,
        )

    # ── Assemble rows ──
    rows = [[row_badges], [row_title]]
    if row_summary:
        rows.append([row_summary])
    rows.append([row_footer])
    if row_url:
        rows.append([row_url])

    card = Table(rows, colWidths=[pw])

    # ── Card styling ──
    n = len(rows)
    footer_idx = n - 2 if row_url else n - 1

    style_cmds = [
        ('BACKGROUND',    (0, 0), (-1, -1), WHITE),
        ('BOX',           (0, 0), (-1, -1), 0.75, SLATE_200),
        ('LINEAFTER',     (0, 0), (0, -1),  4, TEAL_PRIMARY),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 15),
        ('TOPPADDING',    (0, 0), (0, 0),   10),
        ('BOTTOMPADDING', (0, -1),(0, -1),  10),
        ('TOPPADDING',    (0, 1), (0, -1),  4),
        ('BOTTOMPADDING', (0, 0), (0, -2),  4),
        # Separator line above the footer row
        ('LINEABOVE',     (0, footer_idx), (0, footer_idx), 0.5, SLATE_200),
        ('TOPPADDING',    (0, footer_idx), (0, footer_idx), 8),
    ]
    card.setStyle(TableStyle(style_cmds))
    return card


# ─── Helpers ─────────────────────────────────────────────────────

def _format_date(pub_date):
    """Best-effort date formatting → YYYY-MM-DD string or empty."""
    if not pub_date:
        return ''
    try:
        if isinstance(pub_date, str):
            clean = pub_date.replace('Z', '+00:00')
            if 'T' in clean:
                dt = datetime.fromisoformat(clean)
            else:
                dt = datetime.strptime(clean[:10], '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
        return str(pub_date)[:10]
    except Exception:
        return str(pub_date)[:10]
