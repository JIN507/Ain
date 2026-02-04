import { useState, useCallback, useMemo } from 'react'
import { Search, ChevronDown, ChevronUp, Loader as LoaderIcon, Download, Loader2, Filter, Calendar, Globe, Languages, Tag, Clock, AlertCircle } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import GuidedQueryBuilder from '../components/GuidedQueryBuilder'
import { apiFetch } from '../apiClient'

export default function DirectSearch() {
  // Query state from builder
  const [searchQuery, setSearchQuery] = useState('')
  const [isQueryValid, setIsQueryValid] = useState(false)
  
  // Filters
  const [titleOnly, setTitleOnly] = useState(false)
  const [timeframe, setTimeframe] = useState('')
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedLanguages, setSelectedLanguages] = useState([])
  const [selectedCategories, setSelectedCategories] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  
  // Date range (for archive)
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  
  // Auto-detect endpoint based on date
  const endpoint = useMemo(() => {
    if (fromDate) {
      const from = new Date(fromDate)
      const now = new Date()
      const hoursDiff = (now - from) / (1000 * 60 * 60)
      return hoursDiff > 48 ? 'archive' : 'latest'
    }
    return 'latest'
  }, [fromDate])
  
  // Results state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [nextPage, setNextPage] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [totalResults, setTotalResults] = useState(0)
  
  const availableCountries = [
    { code: 'sa', name: 'السعودية' },
    { code: 'ae', name: 'الإمارات' },
    { code: 'eg', name: 'مصر' },
    { code: 'qa', name: 'قطر' },
    { code: 'kw', name: 'الكويت' },
    { code: 'bh', name: 'البحرين' },
    { code: 'om', name: 'عمان' },
    { code: 'us', name: 'أمريكا' },
    { code: 'gb', name: 'بريطانيا' },
    { code: 'fr', name: 'فرنسا' },
    { code: 'de', name: 'ألمانيا' },
    { code: 'ru', name: 'روسيا' },
    { code: 'cn', name: 'الصين' },
    { code: 'jp', name: 'اليابان' },
    { code: 'tr', name: 'تركيا' },
    { code: 'in', name: 'الهند' }
  ]
  
  const availableLanguages = [
    { code: 'ar', name: 'العربية' },
    { code: 'en', name: 'الإنجليزية' },
    { code: 'fr', name: 'الفرنسية' },
    { code: 'de', name: 'الألمانية' },
    { code: 'es', name: 'الإسبانية' },
    { code: 'ru', name: 'الروسية' },
    { code: 'zh', name: 'الصينية' },
    { code: 'ja', name: 'اليابانية' },
    { code: 'tr', name: 'التركية' }
  ]
  
  const availableCategories = [
    { code: 'politics', name: 'سياسة' },
    { code: 'business', name: 'اقتصاد' },
    { code: 'technology', name: 'تقنية' },
    { code: 'sports', name: 'رياضة' },
    { code: 'entertainment', name: 'ترفيه' },
    { code: 'health', name: 'صحة' },
    { code: 'science', name: 'علوم' },
    { code: 'world', name: 'عالمي' }
  ]
  
  // Handle query change from builder
  const handleQueryChange = useCallback((query, isValid) => {
    setSearchQuery(query)
    setIsQueryValid(isValid)
  }, [])
  
  // Check if search can be performed
  const canSearch = useMemo(() => {
    const hasQuery = searchQuery.trim().length > 0
    const hasFilters = selectedCountries.length > 0 || selectedLanguages.length > 0 || selectedCategories.length > 0
    return (hasQuery || hasFilters) && isQueryValid
  }, [searchQuery, selectedCountries, selectedLanguages, selectedCategories, isQueryValid])
  
  // Perform search
  const handleSearch = async (isLoadMore = false) => {
    if (!canSearch && !isLoadMore) {
      setError('أدخل كلمة بحث أو اختر فلتر واحد على الأقل')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const params = new URLSearchParams()
      params.append('endpoint', endpoint)
      
      if (!isLoadMore) {
        // Query
        if (searchQuery) {
          if (titleOnly) {
            params.append('qInTitle', searchQuery)
          } else {
            params.append('q', searchQuery)
          }
        }
        
        // Filters
        if (timeframe) params.append('timeframe', timeframe)
        if (selectedCountries.length > 0) {
          params.append('country', selectedCountries.slice(0, 5).join(','))
        }
        if (selectedLanguages.length > 0) {
          params.append('language', selectedLanguages.join(','))
        }
        if (selectedCategories.length > 0) {
          params.append('category', selectedCategories.join(','))
        }
        
        // Archive date range
        if (endpoint === 'archive') {
          if (fromDate) params.append('from_date', fromDate)
          if (toDate) params.append('to_date', toDate)
        }
        
        params.append('removeDuplicate', 'true')
        setSearchPerformed(true)
      } else {
        if (nextPage) {
          params.append('page', nextPage)
        }
      }
      
      const response = await apiFetch(`/api/newsdata/search?${params}`)
      const data = await response.json()
      
      if (!response.ok || !data.success) {
        if (response.status === 429) {
          throw new Error('تم تجاوز حد الطلبات. حاول مرة أخرى بعد دقيقة.')
        }
        throw new Error(data.error || 'فشل البحث')
      }
      
      if (isLoadMore) {
        setResults(prev => [...prev, ...data.results])
      } else {
        setResults(data.results)
        setTotalResults(data.totalResults || data.results.length)
      }
      
      setNextPage(data.nextPage || null)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  // Toggle handlers
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
  
  const toggleCategory = (code) => {
    setSelectedCategories(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : [...prev, code]
    )
  }
  
  // Export to PDF
  const exportToPDF = async () => {
    if (!results.length) return
    setExporting(true)
    
    try {
      const printContent = `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>نتائج البحث - عين</title>
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Cairo', sans-serif;
      direction: rtl;
      padding: 40px;
      background: #fff;
      color: #1a1a1a;
      line-height: 1.8;
    }
    .header {
      text-align: center;
      margin-bottom: 40px;
      padding-bottom: 20px;
      border-bottom: 3px solid #10b981;
    }
    h1 { color: #10b981; font-size: 28px; margin-bottom: 10px; }
    .search-info { color: #666; font-size: 14px; }
    .article {
      background: #f9fafb;
      border-right: 4px solid #10b981;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
      page-break-inside: avoid;
    }
    .article-title { font-size: 16px; font-weight: 700; color: #111; margin-bottom: 10px; }
    .article-desc { font-size: 14px; color: #444; margin-bottom: 10px; }
    .article-meta { font-size: 12px; color: #888; display: flex; gap: 20px; flex-wrap: wrap; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📰 عين - نتائج البحث</h1>
    <p class="search-info">عدد النتائج: ${results.length} | التاريخ: ${new Date().toLocaleDateString('ar-SA')}</p>
  </div>
  ${results.map(article => `
    <div class="article">
      <div class="article-title">${article.title || 'بدون عنوان'}</div>
      ${article.description ? `<div class="article-desc">${article.description}</div>` : ''}
      <div class="article-meta">
        <span>📰 ${article.source_name || article.source_id || 'غير معروف'}</span>
        ${article.country ? `<span>🌍 ${article.country}</span>` : ''}
        ${article.pubDate ? `<span>📅 ${new Date(article.pubDate).toLocaleDateString('ar-SA')}</span>` : ''}
      </div>
    </div>
  `).join('')}
</body>
</html>`

      const printWindow = window.open('', '_blank')
      printWindow.document.write(printContent)
      printWindow.document.close()
      
      setTimeout(() => {
        printWindow.print()
      }, 500)
      
    } catch (err) {
      console.error('Export error:', err)
    } finally {
      setExporting(false)
    }
  }
  
  // Count active filters
  const activeFiltersCount = selectedCountries.length + selectedLanguages.length + selectedCategories.length + (fromDate ? 1 : 0) + (titleOnly ? 1 : 0)
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          ابحث الآن
        </h1>
        <p className="text-gray-600">
          ابحث في الأخبار العالمية من مصادر متعددة
        </p>
      </div>
      
      {/* Search Box */}
      <div className="card p-6 space-y-4">
        {/* Query Builder */}
        <GuidedQueryBuilder
          onQueryChange={handleQueryChange}
          maxLength={512}
        />
        
        {/* Filters Toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 text-sm font-medium transition-colors ${
            showFilters || activeFiltersCount > 0
              ? 'text-emerald-600'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          <Filter className="w-4 h-4" />
          {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          <span>فلاتر إضافية</span>
          {activeFiltersCount > 0 && (
            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
              {activeFiltersCount}
            </span>
          )}
        </button>
        
        {/* Filters Panel */}
        {showFilters && (
          <div className="space-y-5 p-4 bg-gray-50 rounded-xl border border-gray-200">
            {/* Date Range */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 text-gray-500" />
                <label className="text-sm font-semibold text-gray-800">نطاق التاريخ</label>
                {endpoint === 'archive' && (
                  <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">أرشيف</span>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">من</label>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="input w-full text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">إلى</label>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="input w-full text-sm"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {endpoint === 'archive' 
                  ? '📚 سيتم البحث في الأرشيف (أكثر من 48 ساعة)'
                  : '⚡ سيتم البحث في آخر 48 ساعة'
                }
              </p>
            </div>
            
            {/* Timeframe */}
            {endpoint === 'latest' && !fromDate && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  <label className="text-sm font-semibold text-gray-800">الإطار الزمني</label>
                </div>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="input w-full text-sm"
                >
                  <option value="">الكل (48 ساعة)</option>
                  <option value="1">ساعة واحدة</option>
                  <option value="6">6 ساعات</option>
                  <option value="12">12 ساعة</option>
                  <option value="24">24 ساعة</option>
                </select>
              </div>
            )}
            
            {/* Title Only */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={titleOnly}
                onChange={(e) => setTitleOnly(e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded"
              />
              <span className="text-sm text-gray-700">البحث في العنوان فقط</span>
            </label>
            
            {/* Countries */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Globe className="w-4 h-4 text-gray-500" />
                <label className="text-sm font-semibold text-gray-800">
                  الدول
                  {selectedCountries.length > 0 && (
                    <span className="text-gray-500 font-normal mr-1">({selectedCountries.length})</span>
                  )}
                </label>
              </div>
              {selectedCountries.length > 5 && (
                <p className="text-xs text-amber-600 mb-2">⚠️ سيتم استخدام أول 5 دول فقط</p>
              )}
              <div className="flex flex-wrap gap-2">
                {availableCountries.map(country => (
                  <button
                    key={country.code}
                    onClick={() => toggleCountry(country.code)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedCountries.includes(country.code)
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : 'bg-white text-gray-700 border border-gray-200 hover:border-emerald-400'
                    }`}
                  >
                    {country.name}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Languages */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Languages className="w-4 h-4 text-gray-500" />
                <label className="text-sm font-semibold text-gray-800">
                  اللغات
                  {selectedLanguages.length > 0 && (
                    <span className="text-gray-500 font-normal mr-1">({selectedLanguages.length})</span>
                  )}
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableLanguages.map(lang => (
                  <button
                    key={lang.code}
                    onClick={() => toggleLanguage(lang.code)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedLanguages.includes(lang.code)
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'bg-white text-gray-700 border border-gray-200 hover:border-blue-400'
                    }`}
                  >
                    {lang.name}
                  </button>
                ))}
              </div>
            </div>
            
            {/* Categories */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Tag className="w-4 h-4 text-gray-500" />
                <label className="text-sm font-semibold text-gray-800">
                  التصنيفات
                  {selectedCategories.length > 0 && (
                    <span className="text-gray-500 font-normal mr-1">({selectedCategories.length})</span>
                  )}
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableCategories.map(cat => (
                  <button
                    key={cat.code}
                    onClick={() => toggleCategory(cat.code)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedCategories.includes(cat.code)
                        ? 'bg-purple-600 text-white shadow-sm'
                        : 'bg-white text-gray-700 border border-gray-200 hover:border-purple-400'
                    }`}
                  >
                    {cat.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        
        {/* Search Button */}
        <button
          onClick={() => handleSearch(false)}
          disabled={loading || !canSearch}
          className="btn w-full py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading && !nextPage ? (
            <>
              <LoaderIcon className="w-5 h-5 animate-spin" />
              جاري البحث...
            </>
          ) : (
            <>
              <Search className="w-5 h-5" />
              ابحث
            </>
          )}
        </button>
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}
      
      {/* Results */}
      {loading && results.length === 0 ? (
        <Loader text="جاري البحث في الأخبار..." />
      ) : searchPerformed && results.length === 0 ? (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لا توجد نتائج</h3>
          <p className="text-gray-600">جرّب كلمات مختلفة أو وسّع نطاق البحث</p>
        </div>
      ) : results.length > 0 ? (
        <>
          {/* Results Header */}
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{results.length}</span> نتيجة
              {totalResults > results.length && (
                <span className="text-gray-400"> من {totalResults}</span>
              )}
            </div>
            <button
              onClick={exportToPDF}
              disabled={exporting}
              className="btn-outline text-sm disabled:opacity-50"
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
              <ArticleCard key={`${article.article_id || article.link}-${index}`} article={article} />
            ))}
          </div>
          
          {/* Load More */}
          {nextPage && (
            <div className="flex justify-center">
              <button
                onClick={() => handleSearch(true)}
                disabled={loading}
                className="btn-outline disabled:opacity-50"
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
    </div>
  )
}
