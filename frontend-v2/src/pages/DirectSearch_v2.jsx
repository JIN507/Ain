import { useState, useRef } from 'react'
import { Search, ChevronDown, ChevronUp, X, AlertCircle } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import { apiFetch } from '../apiClient'

export default function DirectSearch() {
  // Search parameters
  const [keyword, setKeyword] = useState('')
  const [titleOnly, setTitleOnly] = useState(false)
  const [timeframe, setTimeframe] = useState('')
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedLanguages, setSelectedLanguages] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Results & UI state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [nextPage, setNextPage] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)
  
  // Refs for performance
  const abortControllerRef = useRef(null)
  
  // Countries list
  const availableCountries = [
    { code: 'us', name: 'أمريكا' },
    { code: 'gb', name: 'بريطانيا' },
    { code: 'fr', name: 'فرنسا' },
    { code: 'de', name: 'ألمانيا' },
    { code: 'cn', name: 'الصين' },
    { code: 'ru', name: 'روسيا' },
    { code: 'sa', name: 'السعودية' },
    { code: 'ae', name: 'الإمارات' },
    { code: 'eg', name: 'مصر' },
    { code: 'qa', name: 'قطر' },
    { code: 'tr', name: 'تركيا' },
    { code: 'jp', name: 'اليابان' }
  ]
  
  // Languages list
  const availableLanguages = [
    { code: 'ar', name: 'العربية' },
    { code: 'en', name: 'الإنجليزية' },
    { code: 'fr', name: 'الفرنسية' },
    { code: 'zh', name: 'الصينية' },
    { code: 'ru', name: 'الروسية' },
    { code: 'de', name: 'الألمانية' },
    { code: 'es', name: 'الإسبانية' }
  ]
  
  // Toggle country selection
  const toggleCountry = (code) => {
    setSelectedCountries(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    )
  }
  
  // Toggle language selection
  const toggleLanguage = (code) => {
    setSelectedLanguages(prev =>
      prev.includes(code) ? prev.filter(l => l !== code) : [...prev, code]
    )
  }
  
  // Main search function
  const handleSearch = async (isLoadMore = false) => {
    // Validate
    if (!keyword.trim() && !isLoadMore) {
      setError('الرجاء إدخال كلمة البحث')
      return
    }
    
    // Cancel previous request if exists
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    setLoading(true)
    setError('')
    if (!isLoadMore) {
      setSearchPerformed(false)
    }
    
    try {
      // Create new abort controller
      abortControllerRef.current = new AbortController()
      
      // Build query params
      const params = new URLSearchParams()
      
      if (isLoadMore && nextPage) {
        params.append('page', nextPage)
      } else {
        params.append('q', keyword.trim())
        if (titleOnly) params.append('qInTitle', 'true')
        if (timeframe) params.append('timeframe', timeframe)
        if (selectedCountries.length > 0) {
          params.append('country', selectedCountries.join(','))
        }
        if (selectedLanguages.length > 0) {
          params.append('language', selectedLanguages.join(','))
        }
      }
      
      // Fetch with timeout
      const response = await apiFetch(`/api/direct-search?${params}`, {
        signal: abortControllerRef.current.signal
      })
      
      const data = await response.json()
      
      // Handle errors gracefully
      if (data.error) {
        setError(data.error)
        if (!isLoadMore) {
          setResults([])
        }
        setLoading(false)
        setSearchPerformed(true)
        return
      }
      
      // Update results
      if (isLoadMore) {
        setResults(prev => [...prev, ...(data.results || [])])
      } else {
        setResults(data.results || [])
      }
      
      setNextPage(data.nextPage || null)
      setSearchPerformed(true)
      
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Request aborted')
        return
      }
      
      setError(err.message || 'حدث خطأ أثناء البحث')
      if (!isLoadMore) {
        setResults([])
      }
    } finally {
      setLoading(false)
    }
  }
  
  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !loading && keyword.trim()) {
      handleSearch(false)
    }
  }
  
  // Clear search
  const handleClear = () => {
    setKeyword('')
    setResults([])
    setError('')
    setNextPage(null)
    setSearchPerformed(false)
    setSelectedCountries([])
    setSelectedLanguages([])
    setTimeframe('')
    setTitleOnly(false)
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-2">
          <Search className="w-8 h-8 text-emerald-600" />
          <h1 className="text-2xl font-bold text-gray-900">
            ابحث بكلمة مباشرة
          </h1>
        </div>
        <p className="text-gray-600">
          ابحث في الأخبار العالمية مباشرةً - جميع النتائج مترجمة إلى العربية
        </p>
      </div>
      
      {/* Search Box */}
      <div className="card p-6">
        <div className="space-y-4">
          {/* Keyword Input */}
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="اكتب كلمة البحث بالعربية أو الإنجليزية..."
                className="input w-full"
                maxLength={100}
                disabled={loading}
              />
              {keyword && (
                <button
                  onClick={handleClear}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
            
            <button
              onClick={() => handleSearch(false)}
              disabled={loading || !keyword.trim()}
              className="btn disabled:opacity-50 disabled:cursor-not-allowed min-w-[120px]"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  جاري البحث...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Search className="w-5 h-5" />
                  ابحث
                </span>
              )}
            </button>
          </div>
          
          {/* Advanced Filters Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-emerald-700 hover:text-emerald-900 font-semibold"
          >
            {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            خيارات متقدمة
          </button>
          
          {/* Advanced Filters */}
          {showAdvanced && (
            <div className="space-y-4 pt-4 border-t border-gray-200">
              {/* Title Only Toggle */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={titleOnly}
                  onChange={(e) => setTitleOnly(e.target.checked)}
                  className="w-4 h-4 text-emerald-600 rounded focus:ring-emerald-500"
                />
                <span className="text-sm font-medium text-gray-700">بحث في العنوان فقط</span>
              </label>
              
              {/* Timeframe */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  الإطار الزمني
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="input w-full md:w-auto"
                >
                  <option value="">كل الأوقات</option>
                  <option value="6">آخر 6 ساعات</option>
                  <option value="12">آخر 12 ساعة</option>
                  <option value="24">آخر 24 ساعة</option>
                  <option value="48">آخر 48 ساعة</option>
                </select>
              </div>
              
              {/* Countries */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  الدول {selectedCountries.length > 0 && `(${selectedCountries.length} محدد)`}
                </label>
                {selectedCountries.length > 5 && (
                  <div className="mb-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                    ⚠️ سيتم استخدام أول 5 دول فقط
                  </div>
                )}
                <div className="flex flex-wrap gap-2">
                  {availableCountries.map(country => (
                    <button
                      key={country.code}
                      onClick={() => toggleCountry(country.code)}
                      className={`px-3 py-1 rounded-full text-sm transition-colors ${
                        selectedCountries.includes(country.code)
                          ? 'bg-emerald-600 text-white'
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
                  اللغات {selectedLanguages.length > 0 && `(${selectedLanguages.length} محدد)`}
                </label>
                <div className="flex flex-wrap gap-2">
                  {availableLanguages.map(lang => (
                    <button
                      key={lang.code}
                      onClick={() => toggleLanguage(lang.code)}
                      className={`px-3 py-1 rounded-full text-sm transition-colors ${
                        selectedLanguages.includes(lang.code)
                          ? 'bg-blue-600 text-white'
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
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-200">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="w-5 h-5" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        </div>
      )}
      
      {/* Loading State */}
      {loading && !results.length && (
        <Loader text="جاري البحث في الأخبار..." />
      )}
      
      {/* Results */}
      {searchPerformed && results.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-900">
              النتائج ({results.length})
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((article, index) => (
              <ArticleCard 
                key={article.id || index} 
                article={{
                  ...article,
                  keyword: article.keyword_original
                }} 
              />
            ))}
          </div>
          
          {/* Load More */}
          {nextPage && (
            <div className="flex justify-center">
              <button
                onClick={() => handleSearch(true)}
                disabled={loading}
                className="btn disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'جاري التحميل...' : 'عرض المزيد'}
              </button>
            </div>
          )}
        </>
      )}
      
      {/* Empty State */}
      {searchPerformed && !loading && results.length === 0 && !error && (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لم يتم العثور على نتائج</h3>
          <p className="text-gray-600">حاول استخدام كلمات مفتاحية مختلفة أو قم بتوسيع معايير البحث</p>
        </div>
      )}
      
      {/* Initial State */}
      {!searchPerformed && !loading && (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">ابدأ البحث</h3>
          <p className="text-gray-600">اكتب كلمة البحث أعلاه واضغط على زر "ابحث" للحصول على النتائج</p>
          <div className="mt-4 text-sm text-gray-500">
            💡 جميع النتائج ستُترجم تلقائياً إلى العربية
          </div>
        </div>
      )}
    </div>
  )
}
