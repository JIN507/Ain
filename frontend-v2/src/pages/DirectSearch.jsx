import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { 
  Search, ChevronDown, ChevronUp, Loader as LoaderIcon, Download, Loader2, 
  Filter, Calendar, Globe, Languages, Tag, Clock, AlertCircle, RefreshCw,
  FileText, Image, Video, ArrowUpDown, Zap, BarChart3, CheckCircle2,
  XCircle, Info, Sparkles, BookOpen, ExternalLink, Bookmark, FileSpreadsheet
} from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import GuidedQueryBuilder, { compileToQ, validateQuery } from '../components/GuidedQueryBuilder'
import { apiFetch } from '../apiClient'
import { generateXLSX, generatePDFBlob, uploadExport } from '../utils/exportUtils'

// Error messages mapping (Arabic)
const ERROR_MESSAGES = {
  400: 'الطلب غير مكتمل أو يحتوي قيم غير صحيحة',
  401: 'تعذّر التحقق من صلاحية الوصول. حاول مرة أخرى لاحقاً',
  403: 'غير متاح حالياً',
  409: 'تم تكرار قيمة في الفلاتر',
  415: 'صيغة الطلب غير مدعومة',
  422: 'تعذّر معالجة الطلب بسبب تعارض في الفلاتر',
  429: 'تم تجاوز حد الطلبات، حاول بعد قليل',
  500: 'حدث خلل مؤقت. حاول مرة أخرى'
}

// Sort options
const SORT_OPTIONS = [
  { value: '', label: 'الأحدث أولاً (افتراضي)' },
  { value: 'relevancy', label: 'الأكثر صلة' },
  { value: 'pubdateasc', label: 'الأقدم أولاً' },
  { value: 'source', label: 'حسب المصدر' }
]

// Search mode options (mutually exclusive q types)
const SEARCH_MODES = [
  { value: 'full', label: 'بحث شامل', desc: 'العنوان والمحتوى' },
  { value: 'title', label: 'العنوان فقط', desc: 'أسرع وأدق' },
  { value: 'meta', label: 'البيانات الوصفية', desc: 'العنوان والوصف والكلمات المفتاحية' }
]

export default function DirectSearch() {
  // Query builder state
  const [builder, setBuilder] = useState({ must: [], any: [], exclude: [] })
  const [basicText, setBasicText] = useState('')
  
  // Search mode (q, qInTitle, qInMeta - mutually exclusive)
  const [searchMode, setSearchMode] = useState('full')
  
  // Filters
  const [selectedCountries, setSelectedCountries] = useState([])
  const [selectedLanguages, setSelectedLanguages] = useState([])
  const [selectedCategories, setSelectedCategories] = useState([])
  const [showFilters, setShowFilters] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  
  // Time range
  const [timeMode, setTimeMode] = useState('latest') // 'latest' or 'archive'
  const [timeframe, setTimeframe] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  
  // Advanced filters
  const [sortBy, setSortBy] = useState('')
  const [removeDuplicate, setRemoveDuplicate] = useState(true)
  const [fullContent, setFullContent] = useState(false)
  const [imageOnly, setImageOnly] = useState(false)
  const [videoOnly, setVideoOnly] = useState(false)
  const [priorityDomain, setPriorityDomain] = useState('')
  
  // Credit-aware state
  const [countPreview, setCountPreview] = useState(null)
  const [countLoading, setCountLoading] = useState(false)
  const [skipCount, setSkipCount] = useState(false)
  
  // Results state
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [errorDetails, setErrorDetails] = useState('')
  const [nextPage, setNextPage] = useState(null)
  const [searchPerformed, setSearchPerformed] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [totalResults, setTotalResults] = useState(0)
  const [lastUpdated, setLastUpdated] = useState(null)
  
  // Auto-refresh
  const [autoRefresh, setAutoRefresh] = useState(false)
  const autoRefreshRef = useRef(null)
  
  // Request deduplication
  const pendingRequestRef = useRef(null)
  
  // Data
  const availableCountries = [
    { code: 'sa', name: 'السعودية' },
    { code: 'ae', name: 'الإمارات' },
    { code: 'eg', name: 'مصر' },
    { code: 'qa', name: 'قطر' },
    { code: 'kw', name: 'الكويت' },
    { code: 'bh', name: 'البحرين' },
    { code: 'om', name: 'عمان' },
    { code: 'jo', name: 'الأردن' },
    { code: 'lb', name: 'لبنان' },
    { code: 'us', name: 'أمريكا' },
    { code: 'gb', name: 'بريطانيا' },
    { code: 'fr', name: 'فرنسا' },
    { code: 'de', name: 'ألمانيا' },
    { code: 'ru', name: 'روسيا' },
    { code: 'cn', name: 'الصين' },
    { code: 'tr', name: 'تركيا' }
  ]
  
  const availableLanguages = [
    { code: 'ar', name: 'العربية' },
    { code: 'en', name: 'الإنجليزية' },
    { code: 'fr', name: 'الفرنسية' },
    { code: 'de', name: 'الألمانية' },
    { code: 'es', name: 'الإسبانية' },
    { code: 'ru', name: 'الروسية' },
    { code: 'tr', name: 'التركية' }
  ]
  
  const availableCategories = [
    { code: 'top', name: 'أهم الأخبار' },
    { code: 'politics', name: 'سياسة' },
    { code: 'business', name: 'اقتصاد' },
    { code: 'technology', name: 'تقنية' },
    { code: 'health', name: 'صحة' },
    { code: 'science', name: 'علوم' },
    { code: 'sports', name: 'رياضة' },
    { code: 'world', name: 'عالمي' },
    { code: 'entertainment', name: 'ترفيه' }
  ]
  
  // Compile query from builder
  const compiledQuery = useMemo(() => {
    const builderQuery = compileToQ(builder)
    if (basicText.trim() && !builderQuery) return basicText.trim()
    if (basicText.trim() && builderQuery) return `${basicText.trim()} AND ${builderQuery}`
    return builderQuery
  }, [basicText, builder])
  
  // Query validation
  const queryValidation = useMemo(() => {
    return validateQuery(builder, basicText)
  }, [builder, basicText])
  
  // Query length check
  const queryLength = compiledQuery.length
  const isOverLimit = queryLength > 512
  
  // Can search check
  const canSearch = useMemo(() => {
    const hasQuery = compiledQuery.length > 0
    const hasFilters = selectedCountries.length > 0 || selectedLanguages.length > 0 || selectedCategories.length > 0
    return (hasQuery || hasFilters) && queryValidation.valid && !isOverLimit
  }, [compiledQuery, selectedCountries, selectedLanguages, selectedCategories, queryValidation, isOverLimit])
  
  // Auto-detect endpoint based on time settings
  const endpoint = useMemo(() => {
    if (timeMode === 'archive') return 'archive'
    if (fromDate) {
      const from = new Date(fromDate)
      const now = new Date()
      const hoursDiff = (now - from) / (1000 * 60 * 60)
      return hoursDiff > 48 ? 'archive' : 'latest'
    }
    return 'latest'
  }, [timeMode, fromDate])
  
  // Build search params
  const buildSearchParams = useCallback((forCount = false) => {
    const params = new URLSearchParams()
    params.append('endpoint', endpoint)
    
    // Query (mutually exclusive)
    if (compiledQuery) {
      if (searchMode === 'title') {
        params.append('qInTitle', compiledQuery)
      } else if (searchMode === 'meta') {
        params.append('qInMeta', compiledQuery)
      } else {
        params.append('q', compiledQuery)
      }
    }
    
    // Filters (max 5 each)
    if (selectedCountries.length > 0) {
      params.append('country', selectedCountries.slice(0, 5).join(','))
    }
    if (selectedLanguages.length > 0) {
      params.append('language', selectedLanguages.slice(0, 5).join(','))
    }
    if (selectedCategories.length > 0) {
      params.append('category', selectedCategories.slice(0, 5).join(','))
    }
    
    // Time
    if (endpoint === 'latest' && timeframe) {
      params.append('timeframe', timeframe)
    }
    if (endpoint === 'archive') {
      if (fromDate) params.append('fromDate', fromDate)
      if (toDate) params.append('toDate', toDate)
    }
    
    // Advanced (skip for count)
    if (!forCount) {
      if (sortBy) params.append('sort', sortBy)
      if (removeDuplicate) params.append('removeDuplicate', 'true')
      if (fullContent) params.append('fullContent', 'true')
      if (imageOnly) params.append('image', 'true')
      if (videoOnly) params.append('video', 'true')
      if (priorityDomain) params.append('prioritydomain', priorityDomain)
      params.append('size', '50')
    }
    
    return params
  }, [compiledQuery, searchMode, selectedCountries, selectedLanguages, selectedCategories, endpoint, timeframe, fromDate, toDate, sortBy, removeDuplicate, fullContent, imageOnly, videoOnly, priorityDomain])
  
  // Get count preview
  const getCountPreview = async () => {
    if (!canSearch) return
    
    setCountLoading(true)
    setCountPreview(null)
    
    try {
      const params = buildSearchParams(true)
      const response = await apiFetch(`/api/newsdata/count?${params}`)
      const data = await response.json()
      
      if (response.ok && data.success) {
        setCountPreview({
          count: data.count,
          health: data.health,
          health_ar: data.health_ar
        })
      }
    } catch (err) {
      console.error('Count preview error:', err)
    } finally {
      setCountLoading(false)
    }
  }
  
  // Perform search
  const handleSearch = async (isLoadMore = false) => {
    if (!canSearch && !isLoadMore) {
      setError('أدخل كلمة بحث أو اختر فلتر واحد على الأقل')
      return
    }
    
    // Request deduplication
    if (pendingRequestRef.current) {
      return
    }
    
    setLoading(true)
    setError('')
    setErrorDetails('')
    
    const requestId = Date.now()
    pendingRequestRef.current = requestId
    
    try {
      const params = buildSearchParams(false)
      
      if (isLoadMore && nextPage) {
        params.append('page', nextPage)
      }
      
      const response = await apiFetch(`/api/newsdata/search?${params}`)
      const data = await response.json()
      
      // Check if this request is still valid
      if (pendingRequestRef.current !== requestId) return
      
      if (!response.ok || !data.success) {
        const errorMsg = ERROR_MESSAGES[response.status] || data.error || 'فشل البحث'
        throw new Error(errorMsg)
      }
      
      if (isLoadMore) {
        setResults(prev => [...prev, ...data.results])
      } else {
        setResults(data.results)
        setTotalResults(data.totalResults || data.results.length)
        setSearchPerformed(true)
      }
      
      setNextPage(data.nextPage || null)
      setLastUpdated(new Date())
      
    } catch (err) {
      if (pendingRequestRef.current === requestId) {
        setError(err.message)
        if (err.message.includes('429')) {
          setAutoRefresh(false)
        }
      }
    } finally {
      if (pendingRequestRef.current === requestId) {
        setLoading(false)
        pendingRequestRef.current = null
      }
    }
  }
  
  // Credit-aware search flow
  const handleSmartSearch = async () => {
    if (skipCount) {
      handleSearch(false)
      return
    }
    
    // Get count first
    await getCountPreview()
  }
  
  // Confirm search after count
  const confirmSearch = () => {
    setCountPreview(null)
    handleSearch(false)
  }
  
  // Toggle handlers
  const toggleCountry = (code) => {
    setSelectedCountries(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : prev.length < 5 ? [...prev, code] : prev
    )
  }
  
  const toggleLanguage = (code) => {
    setSelectedLanguages(prev =>
      prev.includes(code)
        ? prev.filter(l => l !== code)
        : prev.length < 5 ? [...prev, code] : prev
    )
  }
  
  const toggleCategory = (code) => {
    setSelectedCategories(prev =>
      prev.includes(code)
        ? prev.filter(c => c !== code)
        : prev.length < 5 ? [...prev, code] : prev
    )
  }
  
  // Auto-refresh effect
  useEffect(() => {
    if (autoRefresh && searchPerformed && endpoint === 'latest') {
      autoRefreshRef.current = setInterval(() => {
        handleSearch(false)
      }, 5 * 60 * 1000) // 5 minutes
    }
    
    return () => {
      if (autoRefreshRef.current) {
        clearInterval(autoRefreshRef.current)
      }
    }
  }, [autoRefresh, searchPerformed, endpoint])
  
  // Export to PDF
  const exportToPDF = async () => {
    if (!results.length) return
    setExporting(true)
    try {
      const pdfBlob = await generatePDFBlob(results, apiFetch, { title: 'عين - نتائج البحث' })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `نتائج_البحث_عين_${timestamp}.pdf`

      const url = URL.createObjectURL(pdfBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, pdfBlob, filename, {
        articleCount: results.length, filters: { type: 'direct_search', query: compiledQuery }, sourceType: 'direct_search',
      })
    } catch (err) { console.error('Export error:', err); alert('خطأ في تصدير PDF: ' + err.message) }
    finally { setExporting(false) }
  }

  const [exportingXlsx, setExportingXlsx] = useState(false)

  const exportToXLSX = async () => {
    if (!results.length) return
    setExportingXlsx(true)
    try {
      const xlsxBlob = generateXLSX(results)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `نتائج_البحث_عين_${timestamp}.xlsx`

      const url = URL.createObjectURL(xlsxBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, xlsxBlob, filename, {
        articleCount: results.length, filters: { type: 'direct_search', query: compiledQuery }, sourceType: 'direct_search',
      })
    } catch (err) { console.error('Export error:', err) }
    finally { setExportingXlsx(false) }
  }
  
  // Active filters count
  const activeFiltersCount = selectedCountries.length + selectedLanguages.length + selectedCategories.length + (fromDate ? 1 : 0) + (timeframe ? 1 : 0)
  
  // Time since last update
  const timeSinceUpdate = useMemo(() => {
    if (!lastUpdated) return null
    const diff = Math.floor((Date.now() - lastUpdated.getTime()) / 1000 / 60)
    if (diff < 1) return 'الآن'
    if (diff === 1) return 'منذ دقيقة'
    if (diff < 60) return `منذ ${diff} دقيقة`
    return `منذ ${Math.floor(diff / 60)} ساعة`
  }, [lastUpdated])
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">ابحث الآن</h1>
          <p className="text-sm text-slate-500 mt-0.5">ابحث في ملايين الأخبار من مصادر عالمية</p>
        </div>
        {lastUpdated && (
          <div className="text-[11px] text-slate-400 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {timeSinceUpdate}
          </div>
        )}
      </div>
      
      {/* Search Box */}
      <div className="card p-5 space-y-4">
        {/* Search Mode Selector */}
        <div className="flex items-center gap-2 pb-3" style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
          <span className="text-xs text-slate-500">نطاق البحث:</span>
          <div className="flex gap-1">
            {SEARCH_MODES.map(mode => (
              <button
                key={mode.value}
                onClick={() => setSearchMode(mode.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  searchMode === mode.value
                    ? 'text-white'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
                style={searchMode === mode.value ? { background: 'linear-gradient(135deg, #0f766e, #14b8a6)' } : { background: 'rgba(0,0,0,0.03)' }}
                title={mode.desc}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>
        
        {/* Query Builder */}
        <GuidedQueryBuilder
          builder={builder}
          setBuilder={setBuilder}
          basicText={basicText}
          setBasicText={setBasicText}
          maxLength={512}
        />
        
        {/* Query Length Warning */}
        {queryLength > 400 && (
          <div className={`flex items-center gap-2 text-sm ${isOverLimit ? 'text-red-600' : 'text-amber-600'}`}>
            <AlertCircle className="w-4 h-4" />
            <span>
              {isOverLimit 
                ? `تجاوزت الحد المسموح (${queryLength}/512 حرف)` 
                : `اقتربت من الحد المسموح (${queryLength}/512 حرف)`}
            </span>
          </div>
        )}
        
        {/* Time Mode Toggle */}
        <div className="flex items-center gap-3 py-3" style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
          <span className="text-xs text-slate-500">الفترة:</span>
          <div className="flex gap-1">
            <button
              onClick={() => { setTimeMode('latest'); setFromDate(''); setToDate(''); }}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                timeMode === 'latest' ? 'text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
              style={timeMode === 'latest' ? { background: 'linear-gradient(135deg, #0f766e, #14b8a6)' } : { background: 'rgba(0,0,0,0.03)' }}
            >
              <Zap className="w-3.5 h-3.5" />
              آخر 48 ساعة
            </button>
            <button
              onClick={() => setTimeMode('archive')}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all flex items-center gap-1.5 ${
                timeMode === 'archive' ? 'text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
              style={timeMode === 'archive' ? { background: 'linear-gradient(135deg, #7c3aed, #a78bfa)' } : { background: 'rgba(0,0,0,0.03)' }}
            >
              <BookOpen className="w-3.5 h-3.5" />
              أرشيف (6 أشهر)
            </button>
          </div>
        </div>
        
        {/* Archive Date Range */}
        {timeMode === 'archive' && (
          <div className="grid grid-cols-2 gap-3 p-3 rounded-xl" style={{ background: 'rgba(139,92,246,0.04)' }}>
            <div>
              <label className="block text-[11px] font-medium text-slate-500 mb-1">من تاريخ</label>
              <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input w-full" />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-slate-500 mb-1">إلى تاريخ</label>
              <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input w-full" />
            </div>
          </div>
        )}
        
        {/* Latest Timeframe */}
        {timeMode === 'latest' && (
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-gray-400" />
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="input text-sm flex-1"
            >
              <option value="">كل آخر 48 ساعة</option>
              <option value="1">ساعة واحدة</option>
              <option value="6">6 ساعات</option>
              <option value="12">12 ساعة</option>
              <option value="24">24 ساعة</option>
            </select>
          </div>
        )}
        
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
          <span>الفلاتر الأساسية</span>
          {activeFiltersCount > 0 && (
            <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
              {activeFiltersCount}
            </span>
          )}
        </button>
        
        {/* Primary Filters */}
        {showFilters && (
          <div className="space-y-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
            {/* Countries */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Globe className="w-4 h-4 text-gray-500" />
                <label className="text-sm font-semibold text-gray-800">
                  الدول <span className="text-gray-400 font-normal">(حد أقصى 5)</span>
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableCountries.map(country => (
                  <button
                    key={country.code}
                    onClick={() => toggleCountry(country.code)}
                    disabled={!selectedCountries.includes(country.code) && selectedCountries.length >= 5}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedCountries.includes(country.code)
                        ? 'bg-emerald-600 text-white shadow-sm'
                        : selectedCountries.length >= 5
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
                  اللغات <span className="text-gray-400 font-normal">(حد أقصى 5)</span>
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableLanguages.map(lang => (
                  <button
                    key={lang.code}
                    onClick={() => toggleLanguage(lang.code)}
                    disabled={!selectedLanguages.includes(lang.code) && selectedLanguages.length >= 5}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedLanguages.includes(lang.code)
                        ? 'bg-blue-600 text-white shadow-sm'
                        : selectedLanguages.length >= 5
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
                  التصنيفات <span className="text-gray-400 font-normal">(حد أقصى 5)</span>
                </label>
              </div>
              <div className="flex flex-wrap gap-2">
                {availableCategories.map(cat => (
                  <button
                    key={cat.code}
                    onClick={() => toggleCategory(cat.code)}
                    disabled={!selectedCategories.includes(cat.code) && selectedCategories.length >= 5}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedCategories.includes(cat.code)
                        ? 'bg-purple-600 text-white shadow-sm'
                        : selectedCategories.length >= 5
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
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
        
        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`flex items-center gap-2 text-sm font-medium transition-colors ${
            showAdvanced ? 'text-purple-600' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          <span>خيارات متقدمة</span>
        </button>
        
        {/* Advanced Filters */}
        {showAdvanced && (
          <div className="space-y-4 p-4 bg-purple-50 rounded-xl border border-purple-200">
            {/* Sort */}
            <div className="flex items-center gap-3">
              <ArrowUpDown className="w-4 h-4 text-purple-500" />
              <label className="text-sm font-medium text-gray-700 w-24">الترتيب</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="input text-sm flex-1"
              >
                {SORT_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            
            {/* Priority Domain */}
            <div className="flex items-center gap-3">
              <BarChart3 className="w-4 h-4 text-purple-500" />
              <label className="text-sm font-medium text-gray-700 w-24">أولوية المصادر</label>
              <select
                value={priorityDomain}
                onChange={(e) => setPriorityDomain(e.target.value)}
                className="input text-sm flex-1"
              >
                <option value="">الكل</option>
                <option value="top">كبرى فقط (10%)</option>
                <option value="medium">متوسطة وكبرى (30%)</option>
                <option value="low">موثوقة (50%)</option>
              </select>
            </div>
            
            {/* Boolean toggles */}
            <div className="grid grid-cols-2 gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={removeDuplicate}
                  onChange={(e) => setRemoveDuplicate(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded"
                />
                <span className="text-sm text-gray-700">إزالة المكرر</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={fullContent}
                  onChange={(e) => setFullContent(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded"
                />
                <span className="text-sm text-gray-700">المحتوى الكامل</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={imageOnly}
                  onChange={(e) => setImageOnly(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded"
                />
                <Image className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700">مع صور</span>
              </label>
              
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={videoOnly}
                  onChange={(e) => setVideoOnly(e.target.checked)}
                  className="w-4 h-4 text-purple-600 rounded"
                />
                <Video className="w-4 h-4 text-gray-500" />
                <span className="text-sm text-gray-700">مع فيديو</span>
              </label>
            </div>
          </div>
        )}
        
        {/* Search Actions */}
        <div className="flex gap-2 pt-2">
          <button
            onClick={handleSmartSearch}
            disabled={loading || !canSearch}
            className="btn flex-1 py-3 text-base disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <LoaderIcon className="w-5 h-5 animate-spin" />
                جاري البحث...
              </>
            ) : countLoading ? (
              <>
                <LoaderIcon className="w-5 h-5 animate-spin" />
                جاري التحقق...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                ابحث
              </>
            )}
          </button>
          
          <label className="flex items-center gap-2 px-4 py-2 bg-gray-100 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors">
            <input
              type="checkbox"
              checked={skipCount}
              onChange={(e) => setSkipCount(e.target.checked)}
              className="w-4 h-4 text-emerald-600 rounded"
            />
            <Zap className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-gray-700">بحث سريع</span>
          </label>
        </div>
      </div>
      
      {/* Count Preview Modal */}
      {countPreview && (
        <div className="card p-5 bg-gradient-to-r from-emerald-50 to-blue-50 border-emerald-200">
          <div className="flex items-start gap-4">
            <div className={`p-3 rounded-full ${
              countPreview.health === 'narrow' ? 'bg-emerald-100' :
              countPreview.health === 'moderate' ? 'bg-blue-100' :
              countPreview.health === 'broad' ? 'bg-amber-100' : 'bg-gray-100'
            }`}>
              {countPreview.health === 'narrow' ? <CheckCircle2 className="w-6 h-6 text-emerald-600" /> :
               countPreview.health === 'moderate' ? <Info className="w-6 h-6 text-blue-600" /> :
               countPreview.health === 'broad' ? <AlertCircle className="w-6 h-6 text-amber-600" /> :
               <XCircle className="w-6 h-6 text-gray-600" />}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-2xl font-bold text-gray-900">{countPreview.count.toLocaleString()}</span>
                <span className="text-gray-600">نتيجة متوقعة</span>
              </div>
              <p className={`text-sm ${
                countPreview.health === 'narrow' ? 'text-emerald-700' :
                countPreview.health === 'moderate' ? 'text-blue-700' :
                countPreview.health === 'broad' ? 'text-amber-700' : 'text-gray-700'
              }`}>
                {countPreview.health_ar}
                {countPreview.health === 'broad' && ' - يُنصح بتضييق البحث لنتائج أدق'}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCountPreview(null)}
                className="btn-outline text-sm"
              >
                إلغاء
              </button>
              <button
                onClick={confirmSearch}
                className="btn text-sm"
              >
                متابعة البحث
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Error Message */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">{error}</p>
              {errorDetails && (
                <p className="text-xs text-red-600 mt-1">{errorDetails}</p>
              )}
            </div>
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
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600">
                <span className="font-semibold text-gray-900">{results.length}</span> نتيجة
                {totalResults > results.length && (
                  <span className="text-gray-400"> من {totalResults.toLocaleString()}</span>
                )}
              </div>
              
              {endpoint === 'latest' && (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    className="w-4 h-4 text-emerald-600 rounded"
                  />
                  <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'text-emerald-600 animate-spin' : 'text-gray-400'}`} />
                  <span className="text-sm text-gray-600">تحديث تلقائي</span>
                </label>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={exportToPDF}
                disabled={exporting}
                className="btn-outline text-sm disabled:opacity-50"
              >
                {exporting ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> PDF...</>
                ) : (
                  <><Download className="w-4 h-4" /> PDF</>
                )}
              </button>
              <button
                onClick={exportToXLSX}
                disabled={exportingXlsx}
                className="btn-outline text-sm disabled:opacity-50"
              >
                {exportingXlsx ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Excel...</>
                ) : (
                  <><FileSpreadsheet className="w-4 h-4" /> Excel</>
                )}
              </button>
            </div>
          </div>
          
          {/* Results Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {results.map((article, index) => (
              <ArticleCard key={`${article.article_id || article.link || article.url}-${index}`} article={article} />
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
