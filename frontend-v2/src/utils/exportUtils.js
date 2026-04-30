/**
 * Export utilities for generating PDF and XLSX reports
 * Shared across Dashboard, DirectSearch, TopHeadlines
 */
import * as XLSX from 'xlsx'

// ─── XLSX Export ────────────────────────────────────────────────

export function generateXLSX(articles, meta = {}) {
  const rows = articles.map((a, i) => ({
    '#': i + 1,
    'العنوان': a.title_ar || a.title || a.title_original || '',
    'الملخص': a.summary_ar || a.description || a.summary_original || '',
    'المصدر': a.source_name || a.source_id || '',
    'الدولة': Array.isArray(a.country) ? a.country.join(', ') : (a.country || ''),
    'الكلمة المفتاحية': a.keyword_original || a.keyword || '',
    'الرابط': a.url || a.link || '',
    'تاريخ النشر': a.published_at || a.pubDate || '',
  }))

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(rows)

  // Set RTL and column widths
  ws['!cols'] = [
    { wch: 5 },   // #
    { wch: 50 },  // title
    { wch: 70 },  // summary
    { wch: 20 },  // source
    { wch: 15 },  // country
    { wch: 20 },  // keyword
    { wch: 40 },  // url
    { wch: 18 },  // date
  ]

  XLSX.utils.book_append_sheet(wb, ws, 'الأخبار')

  const buf = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
  return new Blob([buf], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
}


// ─── PDF Export (HTML → real PDF via print) ─────────────────────

export function buildReportHTML(articles, { title, stats, filters, keywords, countries } = {}) {
  const reportTitle = title || 'تقرير أخبار عين'
  const now = new Date()

  return `<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>${reportTitle}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif; direction: rtl; padding: 0; background: #fff; color: #1a1a1a; line-height: 1.8; }
    .report-header { border: 3px solid #059669; border-radius: 12px; padding: 30px; margin: 40px; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); box-shadow: 0 4px 6px rgba(0,0,0,0.1); page-break-after: avoid; }
    .logo-section { text-align: center; margin-bottom: 20px; padding-bottom: 20px; border-bottom: 2px solid #059669; }
    h1 { font-family: 'Amiri', serif; color: #065f46; font-size: 42px; font-weight: 800; margin-bottom: 10px; text-align: center; }
    .subtitle { text-align: center; color: #047857; font-size: 18px; font-weight: 600; margin-bottom: 20px; }
    .report-info { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 20px; padding: 20px; background: white; border-radius: 8px; border: 1px solid #059669; }
    .info-item { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #374151; }
    .info-label { font-weight: 700; color: #059669; }
    .stats-container { margin: 30px 40px; padding: 25px; border: 2px solid #d1d5db; border-radius: 12px; background: #f9fafb; }
    .stats-title { font-size: 20px; font-weight: 700; color: #111827; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #059669; }
    .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
    .stat-card { padding: 20px; background: white; border: 2px solid #e5e7eb; border-radius: 10px; text-align: center; }
    .stat-value { font-size: 40px; font-weight: 800; margin-bottom: 8px; }
    .stat-label { font-size: 14px; color: #6b7280; font-weight: 600; }
    .articles-container { margin: 30px 40px; }
    .articles-title { font-size: 22px; font-weight: 700; margin-bottom: 20px; padding: 15px 20px; background: linear-gradient(90deg, #059669 0%, #10b981 100%); color: white; border-radius: 8px; text-align: center; }
    .article { background: white; border: 2px solid #d1d5db; border-right: 5px solid #059669; border-radius: 10px; padding: 0; margin-bottom: 25px; page-break-inside: avoid; box-shadow: 0 2px 8px rgba(0,0,0,0.08); position: relative; overflow: hidden; }
    .article-image { width: 100%; height: 200px; object-fit: cover; background: #f3f4f6; }
    .article-content { padding: 25px; }
    .article::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #059669, #10b981, #34d399); border-radius: 10px 10px 0 0; }
    .article-number { position: absolute; top: -10px; right: 20px; background: #059669; color: white; padding: 5px 15px; border-radius: 20px; font-size: 12px; font-weight: 700; }
    .article-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb; }
    .article-badges { display: flex; gap: 8px; flex-wrap: wrap; }
    .badge { padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 600; border: 1px solid; }
    .badge-country { background: #dbeafe; color: #1e40af; border-color: #93c5fd; }
    .badge-source { background: #fef3c7; color: #92400e; border-color: #fde68a; }
    .badge-keyword { background: #e0e7ff; color: #3730a3; border-color: #c7d2fe; }
    .article-title { font-size: 20px; font-weight: 700; color: #111827; margin-bottom: 12px; line-height: 1.6; }
    .article-summary { font-size: 15px; color: #374151; line-height: 1.8; margin-bottom: 15px; text-align: justify; }
    .article-summary mark { background-color: #fef08a; font-weight: bold; padding: 2px 4px; border-radius: 3px; color: #374151; }
    .match-context-indicator { font-size: 12px; color: #059669; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 4px; }
    .article-footer { display: flex; justify-content: space-between; align-items: flex-start; padding-top: 15px; border-top: 1px solid #e5e7eb; margin-top: 15px; }
    .article-link-section { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; }
    .article-link { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: #059669; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: 600; }
    .article-date { font-size: 11px; color: #9ca3af; margin-top: 5px; margin-right: 5px; }
    .sentiment { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; border: 2px solid; }
    .sentiment.positive { background: #d1fae5; color: #065f46; border-color: #10b981; }
    .sentiment.negative { background: #fee2e2; color: #991b1b; border-color: #ef4444; }
    .sentiment.neutral { background: #f3f4f6; color: #374151; border-color: #9ca3af; }
    .report-footer { margin: 40px; padding: 20px; border: 2px solid #d1d5db; border-radius: 8px; background: #f9fafb; text-align: center; font-size: 12px; color: #6b7280; }
    @media print {
      body { padding: 0; }
      .report-header { margin: 20px; padding: 20px; }
      .stats-container { margin: 20px; }
      .articles-container { margin: 20px; }
      .article { page-break-inside: avoid; box-shadow: none; }
      .article-link { background: #059669 !important; color: white !important; }
      mark { background-color: #fef08a !important; font-weight: bold !important; padding: 2px 4px !important; border-radius: 3px !important; color: #374151 !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div class="logo-section">
      <h1>${reportTitle}</h1>
    </div>
    <div class="report-info">
      <div class="info-item"><span class="info-label">تاريخ التقرير:</span><span>${now.toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' })}</span></div>
      <div class="info-item"><span class="info-label">وقت الإصدار:</span><span>${now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span></div>
      <div class="info-item"><span class="info-label">عدد المصادر:</span><span>${countries?.length || '—'} دولة</span></div>
      <div class="info-item"><span class="info-label">عدد الأخبار:</span><span>${articles.length}</span></div>
    </div>
  </div>

  ${stats ? `
  <div class="stats-container">
    <div class="stats-title">ملخص إحصائي للأخبار</div>
    <div class="stats">
      <div class="stat-card"><div class="stat-value" style="color:#059669">${stats.total || articles.length}</div><div class="stat-label">إجمالي الأخبار</div></div>
      <div class="stat-card"><div class="stat-value" style="color:#10b981">${stats.positive || 0}</div><div class="stat-label">أخبار إيجابية</div></div>
      <div class="stat-card"><div class="stat-value" style="color:#ef4444">${stats.negative || 0}</div><div class="stat-label">أخبار سلبية</div></div>
      <div class="stat-card"><div class="stat-value" style="color:#6b7280">${stats.neutral || 0}</div><div class="stat-label">أخبار محايدة</div></div>
    </div>
  </div>` : ''}

  <div class="articles-container">
    <div class="articles-title">الأخبار المرصودة (${articles.length} خبر)</div>
    ${articles.map((a, i) => {
      const hasCtx = a.match_context && a.match_context.full_snippet_ar
      const text = hasCtx ? a.match_context.full_snippet_ar : (a.summary_ar || a.description || a.summary_original || '')
      const hl = text.replace(/\*\*([^*]+)\*\*/g, '<mark>$1</mark>')
      return `
      <div class="article">
        <span class="article-number">خبر ${i + 1}</span>
        ${a.image_url ? `<img src="${a.image_url}" class="article-image" onerror="this.style.display='none'">` : ''}
        <div class="article-content">
          <div class="article-header"><div class="article-badges">
            <span class="badge badge-source">${a.source_name || a.source_id || ''}</span>
            ${a.keyword_original || a.keyword ? `<span class="badge badge-keyword">${a.keyword_original || a.keyword}</span>` : ''}
            ${a.country ? `<span class="badge badge-country">${Array.isArray(a.country) ? a.country.join(', ') : a.country}</span>` : ''}
          </div></div>
          <h2 class="article-title">${a.title_ar || a.title || a.title_original || ''}</h2>
          ${hasCtx ? '<div class="match-context-indicator"><span>🎯</span><span>سياق المطابقة:</span></div>' : ''}
          <p class="article-summary">${hl}</p>
          <div class="article-footer">
            <div class="article-link-section">
              <a href="${a.url || a.link || ''}" target="_blank" class="article-link">المقال الأصلي ↗</a>
              <div class="article-date">${a.published_at || a.pubDate ? new Date(a.published_at || a.pubDate).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }) : ''}</div>
            </div>
            <span class="sentiment ${a.sentiment === 'إيجابي' ? 'positive' : a.sentiment === 'سلبي' ? 'negative' : 'neutral'}">
              ${a.sentiment === 'إيجابي' ? '✓' : a.sentiment === 'سلبي' ? '✗' : '○'} ${a.sentiment || 'محايد'}
            </span>
          </div>
        </div>
      </div>`
    }).join('')}
  </div>

  <div class="report-footer">
    <p><strong>نظام أخبار عين</strong></p>
    <p style="margin-top:10px">تم إنشاء هذا التقرير تلقائياً • جميع الحقوق محفوظة © ${now.getFullYear()}</p>
  </div>
</body>
</html>`
}


// Max articles per PDF file
export const PDF_MAX_ARTICLES = 50

export async function generatePDFBlob(articles, apiFetch, { title, stats, brief } = {}) {
  // Enforce 50-article limit per PDF file
  const limited = articles.slice(0, PDF_MAX_ARTICLES)
  // Server-side PDF generation using reportlab (pure Python, guaranteed to work)
  const res = await apiFetch('/api/exports/generate-pdf', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ articles: limited, title, stats, brief }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || 'فشل إنشاء ملف PDF')
  }
  return await res.blob()
}


// ─── Upload helper ──────────────────────────────────────────────

export async function uploadExport(apiFetch, blob, filename, { articleCount, filters, sourceType } = {}) {
  const formData = new FormData()
  formData.append('file', blob, filename)
  formData.append('filters', JSON.stringify(filters || {}))
  formData.append('article_count', String(articleCount || 0))
  formData.append('source_type', sourceType || 'dashboard')

  try {
    await apiFetch('/api/exports', { method: 'POST', body: formData })
  } catch (e) {
    console.error('Failed to save export:', e)
  }
}
