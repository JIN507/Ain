import { useState, useEffect } from 'react'
import { Newspaper, ChevronDown, Download, Loader2, FileSpreadsheet } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
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
  
  const formatLastFetch = () => {
    if (!lastFetch) return ''
    const now = new Date()
    const diff = Math.floor((now - lastFetch) / 1000)
    
    if (diff < 60) return 'منذ لحظات'
    if (diff < 120) return 'منذ دقيقة'
    return `منذ ${Math.floor(diff / 60)} دقيقة`
  }

  const exportToPDF = async () => {
    if (!headlines.length || !selectedCountry) return
    setExporting(true)
    try {
      const allArticles = headlines.flatMap(source =>
        (source.articles || []).map(a => ({ ...a, source_name: source.source_name, country: selectedCountry }))
      )
      // Max 50 per file enforced in generatePDFBlob
      const pdfBlob = await generatePDFBlob(allArticles, apiFetch, { title: `عين — أهم العناوين — ${selectedCountry}` })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const count = Math.min(allArticles.length, 50)
      const filename = `أهم_العناوين_${selectedCountry}_${count}خبر_${timestamp}.pdf`

      const url = URL.createObjectURL(pdfBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, pdfBlob, filename, {
        articleCount: count, filters: { country: selectedCountry, type: 'top_headlines' }, sourceType: 'top_headlines',
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
    if (!headlines.length || !selectedCountry) return
    setExportingXlsx(true)
    try {
      const allArticles = headlines.flatMap(source =>
        (source.articles || []).map(a => ({ ...a, source_name: source.source_name, country: selectedCountry }))
      )
      const xlsxBlob = generateXLSX(allArticles)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `تقرير_أهم_العناوين_${selectedCountry}_${timestamp}.xlsx`

      const url = URL.createObjectURL(xlsxBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      await uploadExport(apiFetch, xlsxBlob, filename, {
        articleCount: allArticles.length, filters: { country: selectedCountry, type: 'top_headlines' }, sourceType: 'top_headlines',
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
      <div className="card p-5">
        <label className="block text-xs font-medium text-slate-500 mb-2">
          اختر الدولة {countries.length > 0 && `(${countries.length} دولة)`}
        </label>
        
        <div className="flex gap-3 items-center">
          <div className="flex-1 relative">
            <select
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              className="input w-full"
              disabled={countries.length === 0}
            >
              <option value="">اختر دولة</option>
              {countries.map((country) => (
                <option key={country.name} value={country.name}>
                  {country.name} ({country.count} مصدر)
                </option>
              ))}
            </select>
          </div>
          
          <button
            onClick={fetchHeadlines}
            disabled={loading || !selectedCountry}
            className="btn"
          >
            {loading ? 'جاري...' : 'تحديث'}
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
          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span className="font-semibold">
              📰 {headlines.length} مصدر
            </span>
            <span>•</span>
            <span className="font-semibold">
              📊 {getTotalArticles()} خبر
            </span>
          </div>
          
          {/* Headlines by Source */}
          <div className="space-y-8">
            {headlines.map((source, index) => (
              <div key={`${source.source_name}-${index}`} className="space-y-4">
                {/* Source Header */}
                <div className="flex items-center gap-3 pb-3 border-b-2 border-emerald-200">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-md">
                    <Newspaper className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">
                      {source.source_name}
                    </h2>
                    <p className="text-sm text-gray-600">
                      {source.articles.length} خبر
                      {source.error && (
                        <span className="text-red-600 mr-2">
                          • {source.error}
                        </span>
                      )}
                    </p>
                  </div>
                </div>
                
                {/* Articles Grid */}
                {source.articles.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {source.articles.map((article, idx) => (
                      <ArticleCard 
                        key={`${article.url}-${idx}`} 
                        article={{
                          ...article,
                          source_name: source.source_name,
                          country: selectedCountry
                        }} 
                      />
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    لا توجد أخبار من هذا المصدر
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      ) : null}
      
      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-800">
          💡 يتم جلب آخر 5 أخبار من كل مصدر في الدولة المختارة
        </p>
      </div>
    </div>
  )
}
