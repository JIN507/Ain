import { useState, useEffect, useRef } from 'react'
import { Search, ChevronDown, ChevronUp, Loader as LoaderIcon } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'

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
      
      const response = await fetch(`/api/direct-search?${params}`)
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
          {/* Results Count */}
          <div className="text-sm text-gray-600">
            النتائج: {results.length} خبر
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
