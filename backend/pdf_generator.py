"""
PDF Report Generator for Ain News Monitor
Uses reportlab + arabic-reshaper + python-bidi (100% pure Python, zero system deps)
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
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER

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


# ─── PDF generation ──────────────────────────────────────────────

def generate_report_pdf(articles, title='تقرير أخبار عين', stats=None):
    """
    Generate a PDF report from article data.
    Returns PDF bytes (guaranteed non-blank).
    """
    has_fonts = _ensure_fonts()
    fn = 'Amiri' if has_fonts else 'Helvetica'
    fb = 'Amiri-Bold' if has_fonts else 'Helvetica-Bold'
    ar = _ar if has_fonts else (lambda t: escape(str(t)) if t else '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    # ── Styles ──
    s_title = ParagraphStyle(
        'RTitle', fontName=fb, fontSize=20,
        alignment=TA_CENTER, textColor=colors.HexColor('#059669'),
        spaceAfter=4 * mm, leading=28,
    )
    s_date = ParagraphStyle(
        'RDate', fontName=fn, fontSize=10,
        alignment=TA_CENTER, textColor=colors.HexColor('#6b7280'),
        spaceAfter=8 * mm,
    )
    s_section = ParagraphStyle(
        'RSection', fontName=fb, fontSize=14,
        alignment=TA_RIGHT, textColor=colors.HexColor('#059669'),
        spaceAfter=4 * mm, leading=20,
    )
    s_art_title = ParagraphStyle(
        'RArtTitle', fontName=fb, fontSize=12,
        alignment=TA_RIGHT, textColor=colors.HexColor('#1e293b'),
        spaceAfter=2 * mm, leading=18,
    )
    s_meta = ParagraphStyle(
        'RMeta', fontName=fn, fontSize=9,
        alignment=TA_RIGHT, textColor=colors.HexColor('#6b7280'),
        spaceAfter=2 * mm,
    )
    s_body = ParagraphStyle(
        'RBody', fontName=fn, fontSize=10,
        alignment=TA_RIGHT, textColor=colors.HexColor('#374151'),
        leading=16, spaceAfter=2 * mm,
    )
    s_url = ParagraphStyle(
        'RURL', fontName=fn, fontSize=8,
        alignment=TA_RIGHT, textColor=colors.HexColor('#059669'),
        spaceAfter=3 * mm,
    )
    s_footer = ParagraphStyle(
        'RFooter', fontName=fn, fontSize=9,
        alignment=TA_CENTER, textColor=colors.HexColor('#9ca3af'),
        spaceBefore=10 * mm,
    )

    elements = []

    # ── Title ──
    elements.append(Paragraph(ar(title), s_title))

    # ── Date ──
    now = datetime.utcnow()
    elements.append(Paragraph(now.strftime('%Y-%m-%d  %H:%M UTC'), s_date))

    # ── Stats table ──
    if stats and isinstance(stats, dict):
        header = [ar('محايد'), ar('سلبي'), ar('إيجابي'), ar('إجمالي')]
        values = [
            str(stats.get('neutral', 0)),
            str(stats.get('negative', 0)),
            str(stats.get('positive', 0)),
            str(stats.get('total', len(articles))),
        ]
        t = Table([header, values], colWidths=[42 * mm] * 4)
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), fb),
            ('FONTNAME', (0, 1), (-1, 1), fn),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f0fdf4')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#1e293b')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8 * mm))

    # ── Section header ──
    elements.append(Paragraph(ar(f'الأخبار ({len(articles)})'), s_section))

    # ── Articles ──
    for i, article in enumerate(articles):
        art_title = article.get('title', 'بدون عنوان')
        source = article.get('source_name', article.get('source', ''))
        pub_date = article.get('published_at', article.get('pub_date', ''))
        sentiment = article.get('sentiment', '')
        summary = article.get('summary', article.get('description', ''))
        url = article.get('url', article.get('link', ''))

        # Title
        elements.append(Paragraph(ar(art_title), s_art_title))

        # Meta
        meta_parts = [p for p in [source, pub_date, sentiment] if p]
        if meta_parts:
            elements.append(Paragraph(ar(' | '.join(meta_parts)), s_meta))

        # Summary
        if summary:
            if len(str(summary)) > 400:
                summary = str(summary)[:400] + '...'
            elements.append(Paragraph(ar(summary), s_body))

        # URL
        if url:
            safe_url = escape(str(url))
            display_url = safe_url[:90] + '...' if len(safe_url) > 90 else safe_url
            elements.append(Paragraph(
                f'<link href="{safe_url}">{display_url}</link>', s_url
            ))

        # Separator
        if i < len(articles) - 1:
            elements.append(HRFlowable(
                width='100%', thickness=0.5,
                color=colors.HexColor('#e5e7eb'),
                spaceAfter=3 * mm, spaceBefore=1 * mm,
            ))

    # ── Footer ──
    elements.append(Paragraph(
        ar('نظام أخبار عين — تم إنشاء هذا التقرير تلقائياً'),
        s_footer,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
