import { useState, useEffect, useRef } from 'react'
import { Search, ChevronDown, ChevronUp, Loader as LoaderIcon, Download, Loader2 } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import { apiFetch } from '../apiClient'

export default function DirectSearch() {
  // Search state
  const [keyword, setKeyword] = useState('')
  const [titleOnly, setTitleOnly] = useState(false)
  const [timeframe, setTimeframe] = useState('')
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedLanguages, setSelectedLanguages] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Results state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [nextPage, setNextPage] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)
  const [exporting, setExporting] = useState(false)
  
  // Performance optimization
  const searchButtonRef = useRef(null)
  const abortControllerRef = useRef(null)
  
  const availableCountries = [
    { code: 'us', name: 'أمريكا' },
    { code: 'gb', name: 'بريطانيا' },
    { code: 'fr', name: 'فرنسا' },
    { code: 'de', name: 'ألمانيا' },
    { code: 'cn', name: 'الصين' },
    { code: 'ru', name: 'روسيا' },
    { code: 'jp', name: 'اليابان' },
    { code: 'sa', name: 'السعودية' },
    { code: 'ae', name: 'الإمارات' },
    { code: 'eg', name: 'مصر' },
    { code: 'qa', name: 'قطر' },
    { code: 'tr', name: 'تركيا' }
  ]
  
  const availableLanguages = [
    { code: 'ar', name: 'العربية' },
    { code: 'en', name: 'الإنجليزية' },
    { code: 'fr', name: 'الفرنسية' },
    { code: 'zh', name: 'الصينية' },
    { code: 'ru', name: 'الروسية' },
    { code: 'ja', name: 'اليابانية' },
    { code: 'de', name: 'الألمانية' },
    { code: 'es', name: 'الإسبانية' }
  ]
  
  const handleSearch = async (isLoadMore = false) => {
    if (!keyword.trim() && !isLoadMore) {
      setError('الرجاء إدخال كلمة البحث')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      // Build query params
      const params = new URLSearchParams()
      
      if (!isLoadMore) {
        params.append('q', keyword.trim())
        if (titleOnly) params.append('qInTitle', 'true')
        if (timeframe) params.append('timeframe', timeframe)
        if (selectedCountries.length > 0) {
          params.append('country', selectedCountries.join(','))
        }
        if (selectedLanguages.length > 0) {
          params.append('language', selectedLanguages.join(','))
        }
      } else {
        if (nextPage) {
          params.append('page', nextPage)
        }
      }
      
      const response = await apiFetch(`/api/direct-search?${params}`)
      const data = await response.json()
      
      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('قلّل سرعة الطلبات - حاول مرة أخرى بعد قليل')
        }
        throw new Error(data.error || 'فشل البحث')
      }
      
      if (isLoadMore) {
        setResults([...results, ...data.results])
      } else {
        setResults(data.results)
      }
      
      setNextPage(data.nextPage || null)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }
  
  const toggleCountry = (code) => {
    setSelectedCountries(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
  }
  
  const toggleLanguage = (code) => {
    setSelectedLanguages(prev =>
      prev.includes(code)
        ? prev.filter(l => l !== code)
        : [...prev, code]
    )
  }

  const exportToPDF = async () => {
    if (!results.length) return
    setExporting(true)
    
    try {
      const printContent = `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>نتائج البحث - ${keyword}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Cairo', sans-serif;
      direction: rtl;
      padding: 0;
      background: #ffffff;
      color: #1a1a1a;
      line-height: 1.8;
    }
    .report-header {
      border: 3px solid #3b82f6;
      border-radius: 12px;
      padding: 30px;
      margin: 40px;
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      page-break-after: avoid;
    }
    .logo-section {
      text-align: center;
      margin-bottom: 20px;
      padding-bottom: 20px;
      border-bottom: 2px solid #3b82f6;
    }
    h1 {
      color: #1e40af;
      font-size: 32px;
      font-weight: 800;
      margin-bottom: 10px;
      text-align: center;
    }
    .search-term {
      text-align: center;
      color: #3b82f6;
      font-size: 20px;
      font-weight: 600;
      margin: 15px 0;
      padding: 10px;
      background: white;
      border-radius: 8px;
    }
    .report-info {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin-top: 20px;
      padding: 20px;
      background: white;
      border-radius: 8px;
      border: 1px solid #3b82f6;
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
      color: #3b82f6;
    }
    .articles-container { margin: 30px 40px; }
    .article {
      background: white;
      border: 2px solid #e5e7eb;
      border-right: 5px solid #3b82f6;
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 20px;
      page-break-inside: avoid;
    }
    .article-title {
      font-size: 18px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 10px;
      line-height: 1.6;
    }
    .article-summary {
      font-size: 14px;
      color: #374151;
      line-height: 1.8;
      margin-bottom: 15px;
    }
    .article-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 10px;
      border-top: 1px solid #e5e7eb;
      font-size: 12px;
      color: #6b7280;
    }
    .article-source {
      background: #3b82f6;
      color: white;
      padding: 4px 12px;
      border-radius: 20px;
      font-weight: 600;
    }
    .article-link {
      color: #3b82f6;
      text-decoration: none;
    }
    .report-footer {
      margin: 40px;
      padding: 20px;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      background: #f9fafb;
      text-align: center;
      font-size: 12px;
      color: #6b7280;
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div class="logo-section">
      <h1>🔍 نتائج البحث المباشر</h1>
    </div>
    <div class="search-term">كلمة البحث: "${keyword}"</div>
    <div class="report-info">
      <div class="info-item">
        <span class="info-label">تاريخ التقرير:</span>
        <span>${new Date().toLocaleDateString('ar-SA', { timeZone: 'Asia/Riyadh', year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label">وقت الإصدار:</span>
        <span>${new Date().toLocaleTimeString('ar-SA', { timeZone: 'Asia/Riyadh', hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label">عدد النتائج:</span>
        <span>${results.length} خبر</span>
      </div>
      <div class="info-item">
        <span class="info-label">المصدر:</span>
        <span>NewsData.io</span>
      </div>
    </div>
  </div>

  <div class="articles-container">
    ${results.map((article, index) => `
      <div class="article">
        <h2 class="article-title">${article.title_ar || article.title || ''}</h2>
        <p class="article-summary">${article.summary_ar || article.description || article.content || ''}</p>
        <div class="article-meta">
          <span class="article-source">${article.source_name || article.source?.name || 'مصدر غير معروف'}</span>
          <span>${article.published_at ? new Date(article.published_at).toLocaleDateString('ar-SA') : ''}</span>
          ${article.url ? `<a href="${article.url}" class="article-link">المقال الأصلي</a>` : ''}
        </div>
      </div>
    `).join('')}
  </div>

  <div class="report-footer">
    <p><strong>نظام أخبار عين - البحث المباشر</strong></p>
    <p style="margin-top: 10px;">تم إنشاء هذا التقرير تلقائياً • جميع الحقوق محفوظة © ${new Date().getFullYear()}</p>
  </div>
</body>
</html>
      `

      // Open print preview window
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(printContent)
        printWindow.document.close()
        setTimeout(() => {
          try { printWindow.print() } catch (e) { console.error('Print error:', e) }
        }, 500)
      }

      // Generate PDF and upload to server
      let iframe = null
      try {
        iframe = document.createElement('iframe')
        iframe.style.cssText = 'position:fixed;top:0;left:0;width:210mm;height:297mm;opacity:0;pointer-events:none;z-index:-1;'
        document.body.appendChild(iframe)
        
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document
        if (!iframeDoc) throw new Error('Cannot access iframe document')
        
        iframeDoc.open()
        iframeDoc.write(printContent)
        iframeDoc.close()
        
        await new Promise(resolve => setTimeout(resolve, 2000))
        
        const html2pdf = (await import('html2pdf.js')).default
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
        const filename = `بحث_${keyword}_${timestamp}.pdf`
        
        const pdfBlob = await html2pdf()
          .set({
            margin: [10, 10, 10, 10],
            filename: filename,
            image: { type: 'jpeg', quality: 0.95 },
            html2canvas: { 
              scale: 2, 
              useCORS: true,
              logging: false,
              allowTaint: true,
              windowWidth: 794,
              windowHeight: 1123
            },
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
            pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
          })
          .from(iframeDoc.body)
          .outputPdf('blob')
        
        // Upload to server
        const formData = new FormData()
        formData.append('file', pdfBlob, filename)
        formData.append('filters', JSON.stringify({ keyword, type: 'direct_search' }))
        formData.append('article_count', results.length.toString())
        formData.append('source_type', 'direct_search')
        
        await apiFetch('/api/exports', {
          method: 'POST',
          body: formData,
        })
      } catch (e) {
        console.error('Failed to save export:', e)
      } finally {
        // Always cleanup iframe
        if (iframe && iframe.parentNode) {
          iframe.parentNode.removeChild(iframe)
        }
      }

    } catch (error) {
      console.error('Error exporting PDF:', error)
    } finally {
      setExporting(false)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          ابحث بكلمة مباشرة
        </h1>
        <p className="text-gray-600">
          ابحث في الأخبار العالمية مباشرة باستخدام NewsData.io
        </p>
      </div>
      
      {/* Search Box */}
      <div className="card p-6 space-y-4">
        {/* Main Search */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="اكتب كلمة البحث بالعربية..."
              className="input pr-10 w-full"
              maxLength={100}
            />
          </div>
          <button
            onClick={() => handleSearch(false)}
            disabled={loading || !keyword.trim()}
            className="btn disabled:opacity-50 disabled:cursor-not-allowed min-w-[120px]"
          >
            {loading && !nextPage ? (
              <>
                <LoaderIcon className="w-4 h-4 animate-spin" />
                جاري البحث...
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                ابحث
              </>
            )}
          </button>
        </div>
        
        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          خيارات متقدمة
        </button>
        
        {/* Advanced Filters */}
        {showAdvanced && (
          <div className="border-t pt-4 space-y-4">
            {/* Title Only Toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={titleOnly}
                onChange={(e) => setTitleOnly(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-700">العنوان فقط (qInTitle)</span>
            </label>
            
            {/* Timeframe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                الإطار الزمني
              </label>
              <select
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="input"
              >
                <option value="">البحث في اخر 48 ساعة</option>
              </select>
            </div>
            
            {/* Countries */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                الدول {selectedCountries.length > 0 && `(${selectedCountries.length} محدد)`}
              </label>
              {selectedCountries.length > 5 && (
                <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                  ⚠️ سيتم استخدام أول 5 دول فقط (حد NewsData.io)
                </div>
              )}
              <div className="flex flex-wrap gap-2">
                {availableCountries.map(country => (
                  <button
                    key={country.code}
                    onClick={() => toggleCountry(country.code)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      selectedCountries.includes(country.code)
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {country.name}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Languages */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                اللغات
              </label>
              <div className="flex flex-wrap gap-2">
                {availableLanguages.map(lang => (
                  <button
                    key={lang.code}
                    onClick={() => toggleLanguage(lang.code)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      selectedLanguages.includes(lang.code)
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {lang.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-200">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      
      {/* Results */}
      {loading && results.length === 0 ? (
        <Loader text="جاري البحث في الأخبار العالمية..." />
      ) : results.length === 0 && keyword ? (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لا توجد نتائج للبحث</h3>
          <p className="text-gray-600">جرّب صياغة أخرى أو زمن أوسع</p>
        </div>
      ) : results.length > 0 ? (
        <>
          {/* Results Count and Export Button */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              النتائج: {results.length} خبر
            </div>
            <button
              onClick={exportToPDF}
              disabled={exporting}
              className="btn disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exporting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  جاري التصدير...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  تصدير PDF
                </>
              )}
            </button>
          </div>
          
          {/* Results Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((article, index) => (
              <ArticleCard key={`${article.url}-${index}`} article={article} />
            ))}
          </div>
          
          {/* Load More */}
          {nextPage && (
            <div className="flex justify-center">
              <button
                onClick={() => handleSearch(true)}
                disabled={loading}
                className="btn-outline disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <LoaderIcon className="w-4 h-4 animate-spin" />
                    جاري التحميل...
                  </>
                ) : (
                  'عرض المزيد'
                )}
              </button>
            </div>
          )}
        </>
      ) : null}
      
      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-800">
          💡 يتم البحث في الأخبار العالمية من آخر 48 ساعة باستخدام NewsData.io
        </p>
      </div>
    </div>
  )
}
