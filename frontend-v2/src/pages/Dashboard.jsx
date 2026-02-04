import { useState, useEffect } from 'react'
import { FileText, Download, Loader2, AlertCircle, RotateCcw } from 'lucide-react'
import StatsOverview from '../components/StatsOverview'
import FilterBar from '../components/FilterBar'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import { apiFetch } from '../apiClient'

export default function Dashboard({ initialKeywordFilter, onFilterApplied }) {
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetResult, setResetResult] = useState(null)
  const [articles, setArticles] = useState([])
  const [stats, setStats] = useState({ total: 0, positive: 0, negative: 0, neutral: 0 })
  const [filters, setFilters] = useState({})
  const [countries, setCountries] = useState([])
  const [keywords, setKeywords] = useState([])

  // Apply initial keyword filter from navigation
  useEffect(() => {
    if (initialKeywordFilter) {
      setFilters(prev => ({ ...prev, keyword: initialKeywordFilter }))
      onFilterApplied?.()
    }
  }, [initialKeywordFilter, onFilterApplied])

  useEffect(() => {
    loadArticles()
    loadStats()
    loadKeywords()
  }, [filters])

  // Load countries dynamically whenever articles change
  useEffect(() => {
    loadCountriesFromArticles()
  }, [articles])

  const loadArticles = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams(filters)
      const res = await apiFetch(`/api/articles?${params}`)
      const data = await res.json()
      setArticles(data)
    } catch (error) {
      console.error('Error loading articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const res = await apiFetch('/api/articles/stats')
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  const loadCountriesFromArticles = async () => {
    // SINGLE SOURCE OF TRUTH: /api/articles/countries endpoint only
    // No fallback to avoid conflicts
    try {
      const res = await apiFetch('/api/articles/countries')
      if (res.ok) {
        const data = await res.json()
        setCountries(data)
        
        // DEBUG LOGGING
        console.log('DBG countries:', data)
        console.log(`✅ Loaded ${data.length} countries from /api/articles/countries`)
        
        // Additional debug: Check distinct countries in articles array
        if (articles.length > 0) {
          const distinctCountries = Array.from(new Set(articles.map(a => a.country).filter(Boolean)))
          console.log('DBG distinct countries in /api/articles:', distinctCountries)
          console.log(`   Articles array has ${distinctCountries.length} distinct countries`)
        }
        
        return
      } else {
        console.error(`❌ /api/articles/countries returned ${res.status}`)
        setCountries([])
      }
    } catch (error) {
      console.error('❌ Failed to load countries from /api/articles/countries:', error)
      setCountries([])
    }
  }

  const loadKeywords = async () => {
    try {
      const res = await apiFetch('/api/keywords')
      const data = await res.json()
      setKeywords(data)
    } catch (error) {
      console.error('Error loading keywords:', error)
    }
  }

  const handleResetFilters = () => {
    setFilters({})
  }

  const exportAndReset = async () => {
    if (!confirm('هل أنت متأكد من حفظ البيانات وإعادة تهيئة النظام؟\n\nسيتم:\n1. تصدير جميع الأخبار إلى ملف Excel\n2. حذف جميع الأخبار\n3. حذف جميع الكلمات المفتاحية\n\nهذا الإجراء لا يمكن التراجع عنه!')) {
      return
    }

    setResetting(true)
    setResetResult(null)

    try {
      const res = await apiFetch('/api/articles/export-and-reset', { method: 'POST' })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'فشل التصدير')
      }

      const data = await res.json()
      setResetResult(data)
      
      if (data.download_url) {
        window.location.href = data.download_url
      }

      setTimeout(() => {
        window.location.reload()
      }, 2000)

    } catch (error) {
      console.error('Error exporting and resetting:', error)
      setResetResult({ error: error.message })
    } finally {
      setResetting(false)
    }
  }

  const exportToPDF = async () => {
    setExporting(true)
    try {
      // Create a formal, presentable PDF version
      const printContent = `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>تقرير أخبار عين</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap" rel="stylesheet">
  <style>
    * { 
      margin: 0; 
      padding: 0; 
      box-sizing: border-box; 
    }
    
    body { 
      font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif; 
      direction: rtl; 
      padding: 0;
      background: #ffffff;
      color: #1a1a1a;
      line-height: 1.8;
    }
    
    /* Formal Header with Border */
    .report-header {
      border: 3px solid #059669;
      border-radius: 12px;
      padding: 30px;
      margin: 40px;
      background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      page-break-after: avoid;
    }
    
    .logo-section {
      text-align: center;
      margin-bottom: 20px;
      padding-bottom: 20px;
      border-bottom: 2px solid #059669;
    }
    
    h1 { 
      font-family: 'Amiri', serif;
      color: #065f46; 
      font-size: 42px; 
      font-weight: 800;
      margin-bottom: 10px;
      text-align: center;
      text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .subtitle {
      text-align: center;
      color: #047857;
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 20px;
    }
    
    .report-info {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin-top: 20px;
      padding: 20px;
      background: white;
      border-radius: 8px;
      border: 1px solid #059669;
    }
    
    .info-item {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: #374151;
    }
    
    .info-label {
      font-weight: 700;
      color: #059669;
    }
    
    /* Stats Section with Fancy Borders */
    .stats-container {
      margin: 30px 40px;
      padding: 25px;
      border: 2px solid #d1d5db;
      border-radius: 12px;
      background: #f9fafb;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    .stats-title {
      font-size: 20px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 20px;
      padding-bottom: 10px;
      border-bottom: 2px solid #059669;
    }
    
    .stats { 
      display: grid; 
      grid-template-columns: repeat(4, 1fr); 
      gap: 20px;
    }
    
    .stat-card { 
      padding: 20px;
      background: white;
      border: 2px solid #e5e7eb;
      border-radius: 10px;
      text-align: center;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      transition: transform 0.2s;
    }
    
    .stat-value { 
      font-size: 40px; 
      font-weight: 800;
      margin-bottom: 8px;
      font-family: 'Cairo', sans-serif;
    }
    
    .stat-label { 
      font-size: 14px;
      color: #6b7280;
      font-weight: 600;
    }
    
    /* Articles Section */
    .articles-container {
      margin: 30px 40px;
    }
    
    .articles-title {
      font-size: 22px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 20px;
      padding: 15px 20px;
      background: linear-gradient(90deg, #059669 0%, #10b981 100%);
      color: white;
      border-radius: 8px;
      text-align: center;
    }
    
    .article { 
      background: white;
      border: 2px solid #d1d5db;
      border-right: 5px solid #059669;
      border-radius: 10px;
      padding: 0;
      margin-bottom: 25px;
      page-break-inside: avoid;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      position: relative;
      overflow: hidden;
    }
    
    .article-image {
      width: 100%;
      height: 200px;
      object-fit: cover;
      background: #f3f4f6;
    }
    
    .article-content {
      padding: 25px;
    }
    
    .article::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, #059669, #10b981, #34d399);
      border-radius: 10px 10px 0 0;
    }
    
    .article-number {
      position: absolute;
      top: -10px;
      right: 20px;
      background: #059669;
      color: white;
      padding: 5px 15px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
    }
    
    .article-header { 
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .article-badges {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    
    .badge {
      padding: 5px 12px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      border: 1px solid;
    }
    
    .badge-country {
      background: #dbeafe;
      color: #1e40af;
      border-color: #93c5fd;
    }
    
    .badge-source {
      background: #fef3c7;
      color: #92400e;
      border-color: #fde68a;
    }
    
    .badge-keyword {
      background: #e0e7ff;
      color: #3730a3;
      border-color: #c7d2fe;
    }
    
    .article-title { 
      font-size: 20px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 12px;
      line-height: 1.6;
    }
    
    .article-summary { 
      font-size: 15px;
      color: #374151;
      line-height: 1.8;
      margin-bottom: 15px;
      text-align: justify;
    }
    
    .article-summary mark {
      background-color: #fef08a;
      font-weight: bold;
      padding: 2px 4px;
      border-radius: 3px;
      color: #374151;
    }
    
    .match-context-indicator {
      font-size: 12px;
      color: #059669;
      font-weight: 600;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    
    .article-footer {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding-top: 15px;
      border-top: 1px solid #e5e7eb;
      margin-top: 15px;
    }
    
    .article-link-section {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 5px;
    }
    
    .article-link {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: #059669;
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      transition: background 0.2s;
      border: none;
    }
    
    .article-link:hover {
      background: #047857;
    }
    
    .article-link svg {
      width: 14px;
      height: 14px;
    }
    
    .article-date {
      font-size: 11px;
      color: #9ca3af;
      margin-top: 5px;
      margin-right: 5px;
    }
    
    .sentiment { 
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 700;
      border: 2px solid;
    }
    
    .sentiment.positive { 
      background: #d1fae5;
      color: #065f46;
      border-color: #10b981;
    }
    
    .sentiment.negative { 
      background: #fee2e2;
      color: #991b1b;
      border-color: #ef4444;
    }
    
    .sentiment.neutral { 
      background: #f3f4f6;
      color: #374151;
      border-color: #9ca3af;
    }
    
    /* Footer */
    .report-footer {
      margin: 40px;
      padding: 20px;
      border: 2px solid #d1d5db;
      border-radius: 8px;
      background: #f9fafb;
      text-align: center;
      font-size: 12px;
      color: #6b7280;
    }
    
    @media print {
      body { padding: 0; }
      .report-header { margin: 20px; padding: 20px; }
      .stats-container { margin: 20px; }
      .articles-container { margin: 20px; }
      .article { 
        page-break-inside: avoid;
        box-shadow: none;
      }
      .article-link {
        background: #059669 !important;
        color: white !important;
        text-decoration: none !important;
      }
      mark {
        background-color: #fef08a !important;
        font-weight: bold !important;
        padding: 2px 4px !important;
        border-radius: 3px !important;
        color: #374151 !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
      .match-context-indicator {
        display: flex !important;
        color: #059669 !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
    }
  </style>
</head>
<body>
  <!-- Formal Header -->
  <div class="report-header">
    <div class="logo-section">
      <h1> تقرير أخبار عين</h1>
    </div>
    <div class="report-info">
      <div class="info-item">
        <span class="info-label"> تاريخ التقرير:</span>
        <span>${new Date().toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label"> وقت الإصدار:</span>
        <span>${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label"> عدد المصادر:</span>
        <span>${countries.length} دولة</span>
      </div>
      <div class="info-item">
        <span class="info-label"> الكلمات المفتاحية:</span>
        <span>${keywords.filter(k => k.enabled).length} كلمة</span>
      </div>
    </div>
  </div>
  
  <!-- Stats Section -->
  <div class="stats-container">
    <div class="stats-title"> ملخص إحصائي للأخبار</div>
    <div class="stats">
      <div class="stat-card">
        <div class="stat-value" style="color: #059669;">${stats.total}</div>
        <div class="stat-label">إجمالي الأخبار</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: #10b981;">${stats.positive}</div>
        <div class="stat-label">أخبار إيجابية</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: #ef4444;">${stats.negative}</div>
        <div class="stat-label">أخبار سلبية</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: #6b7280;">${stats.neutral}</div>
        <div class="stat-label">أخبار محايدة</div>
      </div>
    </div>
  </div>

  <!-- Articles Section -->
  <div class="articles-container">
    <div class="articles-title"> الأخبار المرصودة (${articles.length} خبر)</div>
    
    ${[...articles].sort((a, b) => {
      const sortBy = filters.sortBy || 'newest';
      return sortBy === 'newest' ? b.id - a.id : a.id - b.id;
    }).map((article, index) => {
      // Extract match context (SAME AS ArticleCard.jsx)
      const hasMatchContext = article.match_context && article.match_context.full_snippet_ar;
      const displayText = hasMatchContext 
        ? article.match_context.full_snippet_ar 
        : (article.summary_ar || article.summary_original || '');
      
      // Replace **keyword** markers with highlighted spans
      const highlightedText = displayText.replace(/\*\*([^*]+)\*\*/g, '<mark style="background-color: #fef08a; font-weight: bold; padding: 2px 4px; border-radius: 3px;">$1</mark>');
      
      return `
      <div class="article">
        <span class="article-number">خبر ${index + 1}</span>
        ${article.image_url ? `<img src="${article.image_url}" alt="صورة المقال" class="article-image" onerror="this.style.display='none'">` : ''}
        <div class="article-content">
          <div class="article-header">
            <div class="article-badges">
              <span class="badge badge-source">📰 ${article.source_name}</span>
              <span class="badge badge-keyword">🔑 ${article.keyword_original || article.keyword || ''}</span>
              <span class="badge badge-country">🌍 ${article.country}</span>
            </div>
          </div>
          <h2 class="article-title">${article.title_ar}</h2>
          ${hasMatchContext ? '<div style="font-size: 12px; color: #059669; font-weight: 600; margin-bottom: 8px; display: flex; align-items: center; gap: 4px;"><span>🎯</span><span>سياق المطابقة:</span></div>' : ''}
          <p class="article-summary">${highlightedText}</p>
          <div class="article-footer">
            <div class="article-link-section">
              <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="article-link">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                المقال الأصلي
              </a>
              <div class="article-date">📅 ${article.published_at ? new Date(article.published_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }) : 'غير محدد'}</div>
            </div>
            <span class="sentiment ${article.sentiment === 'إيجابي' ? 'positive' : article.sentiment === 'سلبي' ? 'negative' : 'neutral'}">
              ${article.sentiment === 'إيجابي' ? '✓' : article.sentiment === 'سلبي' ? '✗' : '○'} ${article.sentiment}
            </span>
          </div>
        </div>
      </div>
      `;
    }).join('')}
  </div>
  
  <!-- Formal Footer -->
  <div class="report-footer">
    <p><strong>نظام أخبار عين</strong></p>
    <p style="margin-top: 10px;">تم إنشاء هذا التقرير تلقائياً • جميع الحقوق محفوظة © ${new Date().getFullYear()}</p>
  </div>
</body>
</html>
      `
      
      // Create hidden iframe for PDF generation (maintains full document context)
      const pdfIframe = document.createElement('iframe')
      pdfIframe.style.cssText = 'position:fixed;left:-9999px;top:0;width:210mm;height:297mm;border:none;'
      document.body.appendChild(pdfIframe)
      
      const iframeDoc = pdfIframe.contentDocument || pdfIframe.contentWindow?.document
      if (iframeDoc) {
        iframeDoc.open()
        iframeDoc.write(printContent)
        iframeDoc.close()
      }
      
      // Open print preview window for user to review
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(printContent)
        printWindow.document.close()
        setTimeout(() => {
          try { printWindow.print() } catch (e) { console.error('Print error:', e) }
        }, 500)
      }
      
      // Generate PDF from iframe
      try {
        const html2pdf = (await import('html2pdf.js')).default
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const filename = `تقرير_أخبار_عين_${timestamp}.pdf`
        
        // Wait for content to render
        await new Promise(resolve => setTimeout(resolve, 1000))
        
        if (iframeDoc && iframeDoc.body) {
          const pdfBlob = await html2pdf()
            .set({
              margin: [10, 10, 10, 10],
              filename: filename,
              image: { type: 'jpeg', quality: 0.98 },
              html2canvas: { 
                scale: 2, 
                useCORS: true,
                logging: false,
                allowTaint: true,
                backgroundColor: '#ffffff',
                windowWidth: pdfIframe.contentWindow?.innerWidth || 794
              },
              jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
              pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
            })
            .from(iframeDoc.body)
            .outputPdf('blob')
          
          // Upload PDF to server with user context
          const formData = new FormData()
          formData.append('file', pdfBlob, filename)
          formData.append('filters', JSON.stringify(filters))
          formData.append('article_count', articles.length.toString())
          formData.append('source_type', 'dashboard')
          
          await apiFetch('/api/exports', {
            method: 'POST',
            body: formData,
          })
        }
      } catch (e) {
        console.error('Failed to save export:', e)
      } finally {
        // Cleanup
        if (pdfIframe.parentNode) {
          pdfIframe.parentNode.removeChild(pdfIframe)
        }
      }

    } catch (error) {
      console.error('Error exporting PDF:', error)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الخلاصة</h1>
          <p className="text-gray-600 mt-1">جميع الأخبار المراقبة</p>
        </div>
        {articles.length > 0 && (
          <button 
            onClick={exportToPDF}
            disabled={exporting}
            className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {exporting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                جاري التصدير...
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                تصدير PDF
              </>
            )}
          </button>
        )}
      </div>

      {/* Stats */}
      <StatsOverview stats={stats} />

      {/* Filters */}
      <FilterBar 
        filters={filters}
        setFilters={setFilters}
        onReset={handleResetFilters}
        countries={countries}
        keywords={keywords}
      />

      {/* Articles Grid */}
      {loading ? (
        <Loader text="جاري تحميل الأخبار..." />
      ) : articles.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لا توجد أخبار</h3>
          <p className="text-gray-600">اذهب إلى الإعدادات لتشغيل المراقبة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...articles]
            .sort((a, b) => {
              const sortBy = filters.sortBy || 'newest'
              if (sortBy === 'newest') {
                return b.id - a.id // الأحدث أولاً (ID كبير → صغير)
              } else {
                return a.id - b.id // الأقدم أولاً (ID صغير → كبير)
              }
            })
            .map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))
          }
        </div>
      )}

      {/* Reset Section */}
      {articles.length > 0 && (
        <div className="card p-6 border-2 border-orange-200">
          <div className="flex items-start gap-3 mb-4">
            <AlertCircle className="w-6 h-6 text-orange-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">إعادة تهيئة النظام</h3>
              <p className="text-sm text-gray-600">
                تصدير جميع الأخبار إلى ملف Excel ثم حذف جميع البيانات والكلمات المفتاحية
              </p>
            </div>
          </div>

          <button
            onClick={exportAndReset}
            disabled={resetting}
            className="btn bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resetting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                جاري التصدير وإعادة التهيئة...
              </>
            ) : (
              <>
                <RotateCcw className="w-5 h-5" />
                حفظ البيانات وإعادة تهيئة
              </>
            )}
          </button>

          {resetResult && !resetResult.error && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-green-800 font-semibold">✅ تم التصدير وإعادة التهيئة بنجاح!</p>
              <p className="text-sm text-green-700 mt-1">
                تم تصدير {resetResult.article_count} مقالة إلى {resetResult.filename}
              </p>
            </div>
          )}

          {resetResult && resetResult.error && (
            <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-red-800">❌ {resetResult.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
