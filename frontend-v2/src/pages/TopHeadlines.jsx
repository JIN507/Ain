import { useState, useEffect } from 'react'
import { Newspaper, ChevronDown, Download, Loader2, FileSpreadsheet, BarChart3, Info } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import SearchableSelect from '../components/SearchableSelect'
import Loader from '../components/Loader'
import { apiFetch } from '../apiClient'
import { generateXLSX, generatePDFBlob, uploadExport } from '../utils/exportUtils'

export default function TopHeadlines() {
  const [countries, setCountries] = useState([])
  const [selectedCountry, setSelectedCountry] = useState('')
  const [headlines, setHeadlines] = useState([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [lastFetch, setLastFetch] = useState(null)
  // The country the currently displayed headlines were actually fetched for.
  // This is the source of truth for labeling cards/exports — NOT `selectedCountry`,
  // which tracks the live dropdown and can drift away from the displayed results.
  const [fetchedCountry, setFetchedCountry] = useState('')
  // Map of source index -> true when that source section is collapsed
  const [collapsed, setCollapsed] = useState({})
  
  // Fetch available countries on mount (does NOT auto-load headlines)
  useEffect(() => {
    fetchCountries()
  }, [])
  
  const fetchCountries = async () => {
    try {
      console.log('🔍 Fetching countries from /api/sources/countries...')
      const response = await apiFetch('/api/sources/countries')
      
      if (!response.ok) {
        console.error('❌ Response not OK:', response.status)
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      
      const data = await response.json()
      console.log('✅ Countries data received:', data)
      
      setCountries(data.countries || [])
      
      // Auto-select first country if available
      if (data.countries && data.countries.length > 0) {
        console.log('✅ Auto-selecting first country:', data.countries[0].name)
        setSelectedCountry(data.countries[0].name)
      } else {
        console.warn('⚠️ No countries returned from API')
      }
    } catch (err) {
      console.error('❌ Failed to fetch countries:', err)
      setError('فشل في جلب الدول: ' + err.message)
    }
  }
  
  const fetchHeadlines = async () => {
    if (!selectedCountry) {
      setError('الرجاء اختيار دولة')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const response = await apiFetch(
        `/api/headlines/top?country=${encodeURIComponent(selectedCountry)}&per_source=5&translate=true`
      )
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || 'فشل في جلب العناوين')
      }
      
      setHeadlines(data.sources || [])
      // Use the country echoed back by the API as the label source of truth.
      setFetchedCountry(data.country || selectedCountry)
      setCollapsed({}) // reset: all sections expanded on a fresh fetch
      setLastFetch(new Date())
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  // NOTE: We intentionally DO NOT auto-fetch when the country changes.
  // Headlines are only loaded when the user clicks the "تحديث" button.
  
  const getTotalArticles = () => {
    return headlines.reduce((sum, source) => sum + source.articles.length, 0)
  }

  const toggleCollapse = (index) => {
    setCollapsed((prev) => ({ ...prev, [index]: !prev[index] }))
  }

  // Jump to a source section from the nav chips; expand it first if collapsed.
  const scrollToSource = (index) => {
    setCollapsed((prev) => ({ ...prev, [index]: false }))
    // Defer so the section is expanded before we scroll to it.
    setTimeout(() => {
      document.getElementById(`source-${index}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }, 0)
  }

  const collapseAll = () => {
    const all = {}
    headlines.forEach((_, i) => { all[i] = true })
    setCollapsed(all)
  }

  const expandAll = () => setCollapsed({})

  const allCollapsed = headlines.length > 0 && headlines.every((_, i) => collapsed[i])
  
  const formatLastFetch = () => {
    if (!lastFetch) return ''
    const now = new Date()
    const diff = Math.floor((now - lastFetch) / 1000)
    
    if (diff < 60) return 'منذ لحظات'
    if (diff < 120) return 'منذ دقيقة'
    return `منذ ${Math.floor(diff / 60)} دقيقة`
  }

  const exportToPDF = async () => {
    if (!headlines.length || !fetchedCountry) return
    setExporting(true)
    try {
      const allArticles = headlines.flatMap(source =>
        (source.articles || []).map(a => ({ ...a, source_name: source.source_name, country: fetchedCountry }))
      )
      // Max 50 per file enforced in generatePDFBlob
      const pdfBlob = await generatePDFBlob(allArticles, apiFetch, { title: `عين — أهم العناوين — ${fetchedCountry}` })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const count = Math.min(allArticles.length, 50)
      const filename = `أهم_العناوين_${fetchedCountry}_${count}خبر_${timestamp}.pdf`

      const url = URL.createObjectURL(pdfBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, pdfBlob, filename, {
        articleCount: count, filters: { country: fetchedCountry, type: 'top_headlines' }, sourceType: 'top_headlines',
      })
    } catch (error) {
      console.error('Error exporting headlines PDF:', error)
      alert('خطأ في تصدير PDF: ' + error.message)
    } finally {
      setExporting(false)
    }
  }

  const [exportingXlsx, setExportingXlsx] = useState(false)

  const exportToXLSX = async () => {
    if (!headlines.length || !fetchedCountry) return
    setExportingXlsx(true)
    try {
      const allArticles = headlines.flatMap(source =>
        (source.articles || []).map(a => ({ ...a, source_name: source.source_name, country: fetchedCountry }))
      )
      const xlsxBlob = generateXLSX(allArticles)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `تقرير_أهم_العناوين_${fetchedCountry}_${timestamp}.xlsx`

      const url = URL.createObjectURL(xlsxBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, xlsxBlob, filename, {
        articleCount: allArticles.length, filters: { country: fetchedCountry, type: 'top_headlines' }, sourceType: 'top_headlines',
      })
    } catch (error) {
      console.error('Error exporting headlines XLSX:', error)
    } finally {
      setExportingXlsx(false)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">أهم العناوين</h1>
          <p className="text-sm text-slate-500 mt-0.5">آخر الأخبار من المصادر في كل دولة</p>
        </div>
        {headlines.length > 0 && (
          <div className="flex items-center gap-2">
            <button onClick={exportToPDF} disabled={exporting} className="btn">
              {exporting ? <><Loader2 className="w-4 h-4 animate-spin" /> PDF...</> : <><Download className="w-4 h-4" /> PDF</>}
            </button>
            <button onClick={exportToXLSX} disabled={exportingXlsx} className="btn-outline">
              {exportingXlsx ? <><Loader2 className="w-4 h-4 animate-spin" /> Excel...</> : <><FileSpreadsheet className="w-4 h-4" /> Excel</>}
            </button>
          </div>
        )}
      </div>
      
      {/* Country Selector */}
      <div className="card p-5 relative z-40">
        <label className="block text-xs font-medium text-slate-500 mb-2">
          اختر الدولة {countries.length > 0 && `(${countries.length} دولة)`}
        </label>
        
        <div className="flex gap-3 items-center">
          <div className="flex-1 relative">
            <SearchableSelect
              value={selectedCountry}
              onChange={(v) => setSelectedCountry(v)}
              options={countries.map((c) => ({ value: c.name, label: c.name, count: c.count }))}
              placeholder="اختر دولة"
              allLabel="اختر دولة"
              searchPlaceholder="ابحث عن دولة..."
            />
          </div>
          
          <button
            onClick={fetchHeadlines}
            disabled={loading || !selectedCountry}
            className="btn flex-shrink-0"
          >
            {loading ? 'جاري...' : 'إبحث'}
          </button>
        </div>
        
        {lastFetch && (
          <div className="mt-2 text-[11px] text-slate-400">
            آخر تحديث: {formatLastFetch()}
          </div>
        )}
      </div>
      
      {/* Error Message */}
      {error && (
        <div className="card p-4 bg-red-50 border-red-200">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}
      
      {/* Loading State */}
      {loading ? (
        <Loader text="جاري جلب أهم العناوين..." />
      ) : headlines.length === 0 && selectedCountry ? (
        <div className="card p-12 text-center">
          <Newspaper className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لا توجد عناوين</h3>
          <p className="text-gray-600">لم نتمكن من جلب أخبار من هذه الدولة</p>
        </div>
      ) : headlines.length > 0 ? (
        <>
          {/* Stats + source jump navigation (sticky) */}
          <div className="card p-4 sticky top-2 z-30 space-y-3">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div className="flex items-center gap-4 text-sm text-slate-600">
                <span className="flex items-center gap-1.5 font-semibold">
                  <Newspaper className="w-4 h-4" style={{ color: '#0f766e' }} />
                  {headlines.length} مصدر
                </span>
                <span className="text-slate-300">•</span>
                <span className="flex items-center gap-1.5 font-semibold">
                  <BarChart3 className="w-4 h-4" style={{ color: '#0f766e' }} />
                  {getTotalArticles()} خبر
                </span>
              </div>
              <button
                onClick={allCollapsed ? expandAll : collapseAll}
                className="text-xs font-medium px-3 py-1.5 rounded-full transition-all flex items-center gap-1.5"
                style={{
                  background: 'rgba(15,118,110,0.06)',
                  color: '#0f766e',
                  border: '1px solid rgba(20,184,166,0.18)',
                }}
              >
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${allCollapsed ? '' : 'rotate-180'}`} />
                {allCollapsed ? 'توسيع الكل' : 'طيّ الكل'}
              </button>
            </div>

            {/* Jump-nav chips */}
            <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-100">
              {headlines.map((source, index) => (
                <button
                  key={`nav-${source.source_name}-${index}`}
                  onClick={() => scrollToSource(index)}
                  className="inline-flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-full transition-all hover:shadow-sm"
                  style={{
                    background: 'white',
                    color: '#334155',
                    border: '1px solid rgba(0,0,0,0.08)',
                  }}
                  title={`الانتقال إلى ${source.source_name}`}
                >
                  <span className="truncate max-w-[140px]">{source.source_name}</span>
                  <span
                    className="text-[10px] px-1 rounded"
                    style={{ background: 'rgba(15,118,110,0.08)', color: '#0f766e' }}
                  >
                    {source.articles.length}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Headlines by Source */}
          <div className="space-y-8">
            {headlines.map((source, index) => {
              const isCollapsed = !!collapsed[index]
              return (
                <div
                  key={`${source.source_name}-${index}`}
                  id={`source-${index}`}
                  className="space-y-4 scroll-mt-24"
                >
                  {/* Source Header — click to collapse/expand */}
                  <button
                    onClick={() => toggleCollapse(index)}
                    className="w-full flex items-center gap-3 pb-3 border-b-2 text-right transition-colors"
                    style={{ borderColor: 'rgba(20,184,166,0.3)' }}
                  >
                    <div
                      className="w-10 h-10 rounded-lg flex items-center justify-center shadow-md flex-shrink-0"
                      style={{ background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)' }}
                    >
                      <Newspaper className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h2 className="text-xl font-bold text-slate-900 truncate">
                        {source.source_name}
                      </h2>
                      <p className="text-sm text-slate-500">
                        {source.articles.length} خبر
                        {source.error && (
                          <span className="text-rose-500 mr-2">
                            • {source.error}
                          </span>
                        )}
                      </p>
                    </div>
                    <ChevronDown
                      className={`w-5 h-5 text-slate-400 flex-shrink-0 transition-transform ${isCollapsed ? '' : 'rotate-180'}`}
                    />
                  </button>

                  {/* Articles Grid — hidden when collapsed */}
                  {!isCollapsed && (
                    source.articles.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {source.articles.map((article, idx) => (
                          <ArticleCard
                            key={`${article.url}-${idx}`}
                            article={{
                              ...article,
                              source_name: source.source_name,
                              country: fetchedCountry
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-slate-400 text-sm">
                        لا توجد أخبار من هذا المصدر
                      </div>
                    )
                  )}
                </div>
              )
            })}
          </div>
        </>
      ) : null}
      
      {/* Info note — subtle one-liner */}
      <div className="flex items-center gap-1.5 text-[11px] text-slate-400 px-1">
        <Info className="w-3.5 h-3.5 flex-shrink-0" />
        يتم جلب آخر 5 أخبار من كل مصدر في الدولة المختارة
      </div>
    </div>
  )
}
