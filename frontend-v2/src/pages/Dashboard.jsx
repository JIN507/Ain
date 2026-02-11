import { useState, useEffect, useRef } from 'react'
import { FileText, Download, Loader2, AlertCircle, RotateCcw, Radio, AlertTriangle, FileSpreadsheet, Sparkles, RefreshCw } from 'lucide-react'
import StatsOverview from '../components/StatsOverview'
import FilterBar from '../components/FilterBar'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'
import { apiFetch } from '../apiClient'
import { generateXLSX, generatePDFBlob, uploadExport } from '../utils/exportUtils'

export default function Dashboard({ initialKeywordFilter, onFilterApplied }) {
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [resetResult, setResetResult] = useState(null)
  const [articles, setArticles] = useState([])
  const [stats, setStats] = useState({ total: 0, positive: 0, negative: 0, neutral: 0 })
  const [monitorStatus, setMonitorStatus] = useState(null)
  const [cleanupStatus, setCleanupStatus] = useState(null)
  const [bookmarkedUrls, setBookmarkedUrls] = useState({})
  const [bookmarkLoading, setBookmarkLoading] = useState(null)
  const [dailyBrief, setDailyBrief] = useState(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const prevArticleCount = useRef(0)
  // Initialize filters with keyword if provided from navigation
  const [filters, setFilters] = useState(() => 
    initialKeywordFilter ? { keyword: initialKeywordFilter } : {}
  )
  const [countries, setCountries] = useState([])
  const [keywords, setKeywords] = useState([])
  const [keywordsLoaded, setKeywordsLoaded] = useState(false)

  // Clear the navigation state after initial render (to allow re-navigation)
  useEffect(() => {
    if (initialKeywordFilter) {
      // Small delay to ensure filter is applied before clearing navigation state
      const timer = setTimeout(() => onFilterApplied?.(), 100)
      return () => clearTimeout(timer)
    }
  }, [])

  useEffect(() => {
    loadArticles()
    loadStats()
    loadKeywords()
    loadCleanupStatus()
  }, [filters])

  // Check which articles are bookmarked
  useEffect(() => {
    if (articles.length === 0) return
    const urls = articles.map(a => a.url).filter(Boolean)
    if (urls.length === 0) return
    apiFetch('/api/bookmarks/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ urls }),
    }).then(r => r.json()).then(d => setBookmarkedUrls(d.bookmarked || {})).catch(() => {})
  }, [articles])

  const handleBookmark = async (article) => {
    setBookmarkLoading(article.url)
    try {
      const res = await apiFetch('/api/bookmarks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article_id: article.id,
          title_ar: article.title_ar,
          title_original: article.title_original,
          summary_ar: article.summary_ar,
          url: article.url,
          image_url: article.image_url,
          source_name: article.source_name,
          country: article.country,
          keyword_original: article.keyword_original,
          sentiment: article.sentiment,
          published_at: article.published_at,
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setBookmarkedUrls(prev => ({ ...prev, [article.url]: data.id }))
      }
    } catch (e) { console.error('Bookmark error:', e) }
    finally { setBookmarkLoading(null) }
  }

  const handleUnbookmark = async (article) => {
    const bookmarkId = bookmarkedUrls[article.url]
    if (!bookmarkId) return
    setBookmarkLoading(article.url)
    try {
      const res = await apiFetch(`/api/bookmarks/${bookmarkId}`, { method: 'DELETE' })
      if (res.ok) {
        setBookmarkedUrls(prev => { const n = { ...prev }; delete n[article.url]; return n })
      }
    } catch (e) { console.error('Unbookmark error:', e) }
    finally { setBookmarkLoading(null) }
  }

  const loadDailyBrief = async (force = false) => {
    setBriefLoading(true)
    try {
      const res = await apiFetch('/api/ai/daily-brief', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force }),
      })
      if (res.ok) {
        const data = await res.json()
        setDailyBrief(data)
      }
    } catch (e) { console.error('Daily brief error:', e) }
    finally { setBriefLoading(false) }
  }

  // Load cleanup status to show warning
  const loadCleanupStatus = async () => {
    try {
      const res = await apiFetch('/api/system/cleanup-status')
      const data = await res.json()
      setCleanupStatus(data)
    } catch (error) {
      console.error('Error loading cleanup status:', error)
    }
  }

  // Load monitor status only when keywords exist, clear when none
  useEffect(() => {
    if (keywordsLoaded) {
      if (keywords.length > 0) {
        loadMonitorStatus()
      } else {
        // No keywords = clear monitor status completely
        setMonitorStatus(null)
      }
    }
  }, [keywordsLoaded, keywords.length])

  // Poll monitor status every 30 seconds (only if keywords exist)
  useEffect(() => {
    // Wait until keywords are loaded, then check if any exist
    if (!keywordsLoaded) return
    if (keywords.length === 0) return // Don't poll if no keywords
    
    const interval = setInterval(() => {
      loadMonitorStatus()
      // If monitoring is executing, also refresh articles/stats
      if (monitorStatus?.executing) {
        loadArticles()
        loadStats()
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [keywordsLoaded, keywords.length, monitorStatus?.executing])

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

  const loadMonitorStatus = async () => {
    try {
      const res = await apiFetch('/api/monitor/status')
      if (res.ok) {
        const data = await res.json()
        setMonitorStatus(data)
      }
    } catch (error) {
      console.error('Error loading monitor status:', error)
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
      setKeywordsLoaded(true)
    } catch (error) {
      console.error('Error loading keywords:', error)
      setKeywordsLoaded(true)
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
      
      // Download the file via apiFetch (ensures auth cookies are sent)
      if (data.download_url) {
        try {
          const dlRes = await apiFetch(data.download_url)
          if (dlRes.ok) {
            const blob = await dlRes.blob()
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = data.filename || 'export.xlsx'
            document.body.appendChild(a)
            a.click()
            a.remove()
            URL.revokeObjectURL(url)
          }
        } catch (dlErr) {
          console.error('Download failed:', dlErr)
        }
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

  const exportPDF = async () => {
    setExporting(true)
    try {
      const sorted = [...articles].sort((a, b) => {
        const sortBy = filters.sortBy || 'newest'
        return sortBy === 'newest' ? b.id - a.id : a.id - b.id
      })
      // Generate real PDF on the server (sends article data, backend builds PDF)
      const pdfBlob = await generatePDFBlob(sorted, apiFetch, { title: 'تقرير أخبار عين', stats })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `تقرير_أخبار_عين_${timestamp}.pdf`

      // Download to user
      const url = URL.createObjectURL(pdfBlob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)

      // Store in ملفاتي
      await uploadExport(apiFetch, pdfBlob, filename, {
        articleCount: articles.length, filters, sourceType: 'dashboard',
      })
    } catch (error) {
      console.error('Error exporting PDF:', error)
      alert('خطأ في تصدير PDF: ' + error.message)
    } finally {
      setExporting(false)
    }
  }

  const [exportingXlsx, setExportingXlsx] = useState(false)

  const exportXLSX = async () => {
    setExportingXlsx(true)
    try {
      const sorted = [...articles].sort((a, b) => {
        const sortBy = filters.sortBy || 'newest'
        return sortBy === 'newest' ? b.id - a.id : a.id - b.id
      })
      const xlsxBlob = generateXLSX(sorted)
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
      const filename = `تقرير_أخبار_عين_${timestamp}.xlsx`

      // Download to user
      const url = URL.createObjectURL(xlsxBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)

      // Store in ملفاتي
      await uploadExport(apiFetch, xlsxBlob, filename, {
        articleCount: articles.length, filters, sourceType: 'dashboard',
      })
    } catch (error) {
      console.error('Error exporting XLSX:', error)
    } finally {
      setExportingXlsx(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Monitoring Status Indicator */}
      {keywords.length === 0 ? (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm"
          style={{ background: 'rgba(234,88,12,0.06)', color: '#c2410c' }}>
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="font-medium">أضف كلمة مفتاحية واحدة على الأقل لبدء المراقبة</span>
        </div>
      ) : monitorStatus && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm"
          style={{
            background: monitorStatus.executing ? 'rgba(20,184,166,0.06)' : 'rgba(0,0,0,0.02)',
            color: monitorStatus.executing ? '#0f766e' : '#64748b',
          }}>
          {monitorStatus.executing ? (
            <>
              <div className="relative">
                <Radio className="w-4 h-4" />
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-teal-500 rounded-full animate-ping" />
              </div>
              <span className="font-medium">جاري جلب الأخبار...</span>
            </>
          ) : (
            <>
              <Radio className="w-4 h-4" />
              <span>
                المراقبة التلقائية كل 30 دقيقة
                {monitorStatus.next_run && (
                  <> · القادم: {new Date(monitorStatus.next_run).toLocaleTimeString('ar-EG')}</>
                )}
              </span>
            </>
          )}
        </div>
      )}

      {/* Monthly Reset Warning - shows 3 days before the 1st */}
      {cleanupStatus?.show_warning && articles.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-3.5 rounded-xl"
          style={{ background: 'rgba(225,29,72,0.06)' }}>
          <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-rose-700">إعادة تعيين شهرية قريباً</p>
            <p className="text-xs text-rose-500 mt-0.5">
              سيتم حذف جميع المقالات ({cleanupStatus.article_count}) في بداية الشهر القادم ({cleanupStatus.next_reset}). صدّر البيانات المهمة الآن.
            </p>
          </div>
          <span className="text-lg font-bold text-rose-600 px-3 py-1 rounded-lg"
            style={{ background: 'rgba(225,29,72,0.08)' }}>
            {cleanupStatus.days_remaining} يوم
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">الخلاصة</h1>
          <p className="text-sm text-slate-500 mt-0.5">جميع الأخبار المرصودة</p>
        </div>
        {articles.length > 0 && (
          <div className="flex items-center gap-2">
            <button 
              onClick={exportPDF}
              disabled={exporting}
              className="btn"
            >
              {exporting ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> PDF...</>
              ) : (
                <><Download className="w-4 h-4" /> PDF</>
              )}
            </button>
            <button 
              onClick={exportXLSX}
              disabled={exportingXlsx}
              className="btn-outline"
            >
              {exportingXlsx ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Excel...</>
              ) : (
                <><FileSpreadsheet className="w-4 h-4" /> Excel</>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Stats */}
      <StatsOverview stats={stats} keywordCount={keywords.length} />

      {/* AI Daily Brief — ملخص ذكي */}
      {articles.length > 0 && (
        <div className="card p-5" style={{ borderRight: '4px solid #8b5cf6' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-violet-500" />
              <h3 className="font-bold text-slate-900">ملخص ذكي</h3>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                style={{ background: 'rgba(139,92,246,0.1)', color: '#7c3aed' }}>AI</span>
            </div>
            <button
              onClick={() => loadDailyBrief(!!dailyBrief)}
              disabled={briefLoading}
              className="btn-ghost !text-xs !px-2.5 !py-1 flex items-center gap-1"
              style={{ color: '#7c3aed' }}
            >
              {briefLoading
                ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> جاري التحليل...</>
                : dailyBrief
                  ? <><RefreshCw className="w-3.5 h-3.5" /> تحديث</>
                  : <><Sparkles className="w-3.5 h-3.5" /> إنشاء الملخص</>
              }
            </button>
          </div>
          {dailyBrief?.content ? (
            <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {dailyBrief.content}
              <div className="mt-3 flex items-center gap-3 text-[11px] text-slate-400">
                <span>📊 {dailyBrief.article_count} مقال</span>
                <span>📅 {dailyBrief.date}</span>
                {dailyBrief.cached && <span>⚡ من الذاكرة</span>}
              </div>
            </div>
          ) : !briefLoading ? (
            <p className="text-sm text-slate-400">اضغط "إنشاء الملخص" للحصول على تحليل ذكي لأخبار اليوم</p>
          ) : null}
        </div>
      )}

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
        <div className="card p-16 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.04)' }}>
            <FileText className="w-7 h-7 text-slate-300" />
          </div>
          <h3 className="text-lg font-bold text-slate-900 mb-1">لا توجد أخبار</h3>
          <p className="text-sm text-slate-400">أضف كلمات مفتاحية لبدء الرصد التلقائي</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
              <ArticleCard
                key={article.id}
                article={article}
                isBookmarked={!!bookmarkedUrls[article.url]}
                onBookmark={handleBookmark}
                onUnbookmark={handleUnbookmark}
                bookmarkLoading={bookmarkLoading === article.url}
              />
            ))
          }
        </div>
      )}

      {/* Reset Section */}
      {articles.length > 0 && (
        <div className="card p-5" style={{ borderColor: 'rgba(234,88,12,0.15)' }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(234,88,12,0.08)' }}>
                <RotateCcw className="w-4 h-4" style={{ color: '#ea580c' }} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-slate-900">إعادة تهيئة النظام</h3>
                <p className="text-xs text-slate-400">تصدير Excel ثم حذف جميع البيانات</p>
              </div>
            </div>
            <button
              onClick={exportAndReset}
              disabled={resetting}
              className="btn-outline !text-xs !px-4 !py-2"
              style={{ color: '#ea580c', borderColor: 'rgba(234,88,12,0.25)' }}
            >
              {resetting ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> جاري...</>
              ) : (
                'حفظ وإعادة تهيئة'
              )}
            </button>
          </div>

          {resetResult && !resetResult.error && (
            <div className="mt-3 rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(20,184,166,0.06)', color: '#0f766e' }}>
              تم تصدير {resetResult.article_count} مقالة بنجاح
            </div>
          )}
          {resetResult && resetResult.error && (
            <div className="mt-3 rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(225,29,72,0.06)', color: '#e11d48' }}>
              {resetResult.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
