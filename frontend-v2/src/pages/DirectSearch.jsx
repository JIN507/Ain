import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, ChevronDown, ChevronUp, Loader as LoaderIcon, Download, Loader2, Newspaper, Archive, Filter } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import QueryBuilder from '../components/QueryBuilder'
import ArabicOperatorHelper, { validateQuery, normalizeQuery } from '../components/ArabicOperatorHelper'
import { apiFetch } from '../apiClient'

export default function DirectSearch() {
  // Search mode: 'simple' or 'builder'
  const [searchMode, setSearchMode] = useState('simple')
  
  // Endpoint selection
  const [endpoint, setEndpoint] = useState('latest')
  
  // Search state
  const [keyword, setKeyword] = useState('')
  const [builtQuery, setBuiltQuery] = useState('')
  const [titleOnly, setTitleOnly] = useState(false)
  const [timeframe, setTimeframe] = useState('')
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedLanguages, setSelectedLanguages] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Extended filters
  const [selectedCategories, setSelectedCategories] = useState([])
  const [excludeCountries, setExcludeCountries] = useState([])
  const [domain, setDomain] = useState('')
  const [excludeDomain, setExcludeDomain] = useState('')
  const [hasImage, setHasImage] = useState(false)
  const [hasVideo, setHasVideo] = useState(false)
  const [removeDuplicate, setRemoveDuplicate] = useState(true)
  const [sentiment, setSentiment] = useState('')
  
  // Archive-specific
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  
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
  const searchInputRef = useRef(null)
  
  // Query preview from last search
  const [queryPreview, setQueryPreview] = useState('')
  
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
    { code: 'tr', name: 'تركيا' },
    { code: 'in', name: 'الهند' },
    { code: 'br', name: 'البرازيل' },
    { code: 'au', name: 'أستراليا' },
    { code: 'ca', name: 'كندا' }
  ]
  
  const availableLanguages = [
    { code: 'ar', name: 'العربية' },
    { code: 'en', name: 'الإنجليزية' },
    { code: 'fr', name: 'الفرنسية' },
    { code: 'zh', name: 'الصينية' },
    { code: 'ru', name: 'الروسية' },
    { code: 'ja', name: 'اليابانية' },
    { code: 'de', name: 'الألمانية' },
    { code: 'es', name: 'الإسبانية' },
    { code: 'pt', name: 'البرتغالية' },
    { code: 'it', name: 'الإيطالية' },
    { code: 'hi', name: 'الهندية' },
    { code: 'ko', name: 'الكورية' }
  ]
  
  const availableCategories = [
    { code: 'business', name: 'أعمال' },
    { code: 'entertainment', name: 'ترفيه' },
    { code: 'environment', name: 'بيئة' },
    { code: 'food', name: 'طعام' },
    { code: 'health', name: 'صحة' },
    { code: 'politics', name: 'سياسة' },
    { code: 'science', name: 'علوم' },
    { code: 'sports', name: 'رياضة' },
    { code: 'technology', name: 'تقنية' },
    { code: 'top', name: 'أهم الأخبار' },
    { code: 'world', name: 'عالمي' }
  ]
  
  const endpoints = [
    { id: 'latest', name: 'آخر الأخبار', icon: Newspaper, description: 'آخر 48 ساعة' },
    { id: 'archive', name: 'الأرشيف', icon: Archive, description: 'البحث التاريخي' }
  ]
  
  const sentimentOptions = [
    { value: '', name: 'الكل' },
    { value: 'positive', name: 'إيجابي' },
    { value: 'negative', name: 'سلبي' },
    { value: 'neutral', name: 'محايد' }
  ]
  
  // Handle query builder changes
  const handleQueryChange = useCallback((query) => {
    setBuiltQuery(query)
  }, [])
  
  const handleSearch = async (isLoadMore = false) => {
    // Determine which query to use
    const searchQuery = searchMode === 'builder' ? builtQuery : keyword.trim()
    
    if (!searchQuery && !isLoadMore) {
      setError('الرجاء إدخال كلمة البحث')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      // Build query params for the new advanced API
      const params = new URLSearchParams()
      params.append('endpoint', endpoint)
      
      if (!isLoadMore) {
        // Query
        if (searchQuery) params.append('q', searchQuery)
        if (titleOnly) params.append('qInTitle', searchQuery)
        
        // Basic filters
        if (timeframe) params.append('timeframe', timeframe)
        if (selectedCountries.length > 0) {
          params.append('country', selectedCountries.join(','))
        }
        if (selectedLanguages.length > 0) {
          params.append('language', selectedLanguages.join(','))
        }
        if (selectedCategories.length > 0) {
          params.append('category', selectedCategories.join(','))
        }
        
        // Extended filters
        if (excludeCountries.length > 0) {
          params.append('excludeCountry', excludeCountries.join(','))
        }
        if (domain) params.append('domain', domain)
        if (excludeDomain) params.append('excludeDomain', excludeDomain)
        if (hasImage) params.append('image', 'true')
        if (hasVideo) params.append('video', 'true')
        if (removeDuplicate) params.append('removeDuplicate', 'true')
        if (sentiment) params.append('sentiment', sentiment)
        
        // Archive-specific
        if (endpoint === 'archive') {
          if (fromDate) params.append('fromDate', fromDate)
          if (toDate) params.append('toDate', toDate)
        }
        
        
        setSearchPerformed(true)
      } else {
        if (nextPage) {
          params.append('page', nextPage)
          params.append('endpoint', endpoint)
        }
      }
      
      // Use new advanced API endpoint
      const response = await apiFetch(`/api/newsdata/search?${params}`)
      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (response.status === 429) {
          throw new Error('قلّل سرعة الطلبات - حاول مرة أخرى بعد قليل')
        }
        throw new Error(data.error || 'فشل البحث')
      }
      
      if (isLoadMore) {
        setResults([...results, ...data.results])
      } else {
        setResults(data.results)
        setQueryPreview(data.query_preview || searchQuery)
      }
      
      setNextPage(data.nextPage || null)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  const toggleCategory = (code) => {
    setSelectedCategories(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
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
      // Use Google Fonts link instead of @import for better compatibility
      const printContent = `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>نتائج البحث - ${keyword}</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Cairo', 'Segoe UI', Tahoma, Arial, sans-serif;
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
      display: flex;
      flex-wrap: wrap;
      gap: 15px;
      margin-top: 20px;
      padding: 20px;
      background: white;
      border-radius: 8px;
      border: 1px solid #3b82f6;
    }
    .info-item {
      flex: 1 1 45%;
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
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
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
    <div class="search-term">
      ${queryPreview ? `الاستعلام: <code dir="ltr">${queryPreview}</code>` : `كلمة البحث: "${searchMode === 'builder' ? builtQuery : keyword}"`}
    </div>
    <div class="report-info">
      <div class="info-item">
        <span class="info-label">نقطة النهاية:</span>
        <span>${endpoints.find(e => e.id === endpoint)?.name || endpoint}</span>
      </div>
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
      ${selectedCountries.length > 0 ? `<div class="info-item"><span class="info-label">الدول:</span><span>${selectedCountries.join(', ')}</span></div>` : ''}
      ${selectedCategories.length > 0 ? `<div class="info-item"><span class="info-label">التصنيفات:</span><span>${selectedCategories.join(', ')}</span></div>` : ''}
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

      // Open print preview window
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
        const filename = `بحث_${keyword}_${timestamp}.pdf`
        
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
      
      {/* Endpoint Tabs */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-2">
          {endpoints.map(ep => {
            const Icon = ep.icon
            return (
              <button
                key={ep.id}
                onClick={() => setEndpoint(ep.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  endpoint === ep.id
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="font-medium">{ep.name}</span>
                <span className="text-xs opacity-75">({ep.description})</span>
              </button>
            )
          })}
        </div>
      </div>
      
      {/* Search Box */}
      <div className="card p-6 space-y-4">
        {/* Search Mode Toggle */}
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium text-gray-700">وضع البحث:</span>
          <div className="flex gap-2">
            <button
              onClick={() => setSearchMode('simple')}
              className={`px-3 py-1 rounded text-sm ${
                searchMode === 'simple'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              بسيط
            </button>
            <button
              onClick={() => setSearchMode('builder')}
              className={`px-3 py-1 rounded text-sm ${
                searchMode === 'builder'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              منشئ الاستعلام (AND/OR/NOT)
            </button>
          </div>
        </div>
        
        {/* Simple Search Mode */}
        {searchMode === 'simple' ? (
          <div className="space-y-3">
            {/* Arabic Operator Helper - Smart Join */}
            <ArabicOperatorHelper
              query={keyword}
              onQueryChange={setKeyword}
              inputRef={searchInputRef}
            />
            
            {/* Search Input Row */}
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="اكتب كلمات البحث ثم استخدم أدوات البحث أعلاه..."
                  className="input pr-10 w-full"
                  maxLength={512}
                />
              </div>
              <button
                onClick={() => handleSearch(false)}
                disabled={loading || !keyword.trim() || !!validateQuery(keyword)}
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
          </div>
        ) : (
          /* Query Builder Mode */
          <div className="space-y-4">
            <QueryBuilder onQueryChange={handleQueryChange} maxLength={512} />
            <button
              onClick={() => handleSearch(false)}
              disabled={loading || !builtQuery.trim()}
              className="btn disabled:opacity-50 disabled:cursor-not-allowed w-full"
            >
              {loading && !nextPage ? (
                <>
                  <LoaderIcon className="w-4 h-4 animate-spin" />
                  جاري البحث...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  ابحث باستخدام الاستعلام المُنشأ
                </>
              )}
            </button>
          </div>
        )}
        
        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
        >
          <Filter className="w-4 h-4" />
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          فلاتر متقدمة
        </button>
        
        {/* Advanced Filters */}
        {showAdvanced && (
          <div className="border-t pt-4 space-y-4">
            {/* Archive Date Range */}
            {endpoint === 'archive' && (
              <div className="grid grid-cols-2 gap-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
                <div>
                  <label className="block text-sm font-medium text-purple-700 mb-1">من تاريخ</label>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="input w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-purple-700 mb-1">إلى تاريخ</label>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="input w-full"
                  />
                </div>
              </div>
            )}
            
            {/* Title Only Toggle */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={titleOnly}
                onChange={(e) => setTitleOnly(e.target.checked)}
                className="w-4 h-4"
              />
              <span className="text-sm text-gray-700">البحث في العنوان فقط</span>
            </label>
            
            {/* Timeframe */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">الإطار الزمني</label>
              <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="input">
                <option value="">الافتراضي (48 ساعة)</option>
                <option value="1">ساعة واحدة</option>
                <option value="6">6 ساعات</option>
                <option value="12">12 ساعة</option>
                <option value="24">24 ساعة</option>
                <option value="48">48 ساعة</option>
              </select>
            </div>
            
            {/* Categories */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                التصنيفات {selectedCategories.length > 0 && `(${selectedCategories.length} محدد)`}
              </label>
              <div className="flex flex-wrap gap-2">
                {availableCategories.map(cat => (
                  <button
                    key={cat.code}
                    onClick={() => toggleCategory(cat.code)}
                    className={`px-3 py-1 rounded-full text-sm transition-colors ${
                      selectedCategories.includes(cat.code)
                        ? 'bg-purple-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
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
