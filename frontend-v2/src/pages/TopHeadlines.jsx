import { useState, useEffect } from 'react'
import { Newspaper, ChevronDown, Download, Loader2 } from 'lucide-react'
import ArticleCard from '../components/ArticleCard'
import Loader from '../components/Loader'

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
      const response = await fetch('/api/sources/countries')
      
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
      const response = await fetch(
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
      const totalArticles = getTotalArticles()

      const printContent = `
<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
  <meta charset="UTF-8">
  <title>تقرير أهم العناوين - ${selectedCountry}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Amiri:wght@400;700&display=swap');
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Cairo', 'Amiri', sans-serif;
      direction: rtl;
      padding: 0;
      background: #ffffff;
      color: #1a1a1a;
      line-height: 1.8;
    }
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
      font-size: 38px;
      font-weight: 800;
      margin-bottom: 10px;
      text-align: center;
      text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    .subtitle {
      text-align: center;
      color: #047857;
      font-size: 16px;
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
    .articles-container { margin: 30px 40px; }
    .articles-title {
      font-size: 20px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 20px;
      padding: 15px 20px;
      background: linear-gradient(90deg, #059669 0%, #10b981 100%);
      color: white;
      border-radius: 8px;
      text-align: center;
    }
    .source-block { margin-bottom: 30px; page-break-inside: avoid; }
    .source-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 2px solid #d1d5db;
    }
    .source-title {
      font-size: 18px;
      font-weight: 700;
      color: #111827;
    }
    .source-meta {
      font-size: 12px;
      color: #6b7280;
    }
    .article {
      background: white;
      border: 2px solid #d1d5db;
      border-right: 5px solid #059669;
      border-radius: 10px;
      padding: 0;
      margin-bottom: 20px;
      page-break-inside: avoid;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      position: relative;
      overflow: hidden;
    }
    .article-content { padding: 22px; }
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
      margin-bottom: 10px;
      text-align: justify;
    }
    .article-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 10px;
      border-top: 1px solid #e5e7eb;
      margin-top: 10px;
      font-size: 12px;
      color: #6b7280;
    }
    .article-link {
      color: #059669;
      text-decoration: none;
      font-weight: 600;
    }
    .article-link:hover { text-decoration: underline; }
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
      .articles-container { margin: 20px; }
      .article { box-shadow: none; page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="report-header">
    <div class="logo-section">
      <h1>تقرير أهم العناوين</h1>
      <div class="subtitle">${selectedCountry}</div>
    </div>
    <div class="report-info">
      <div class="info-item">
        <span class="info-label">تاريخ التقرير:</span>
        <span>${new Date().toLocaleDateString('en-GB', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label">وقت الإصدار:</span>
        <span>${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
      <div class="info-item">
        <span class="info-label">عدد المصادر:</span>
        <span>${headlines.length} مصدر</span>
      </div>
      <div class="info-item">
        <span class="info-label">عدد الأخبار:</span>
        <span>${totalArticles} خبر</span>
      </div>
    </div>
  </div>

  <div class="articles-container">
    <div class="articles-title">أهم العناوين حسب المصدر</div>
    ${headlines.map((source) => {
      const safeName = source.source_name || 'مصدر غير معروف';
      const count = (source.articles || []).length;
      return `
      <div class="source-block">
        <div class="source-header">
          <div class="source-title">${safeName}</div>
          <div class="source-meta">${count} خبر${count === 1 ? '' : ''}</div>
        </div>
        ${(source.articles || []).map((article, idx) => {
          const title = article.title_ar || article.title_original || '';
          const summary = article.summary_ar || article.summary_original || '';
          const url = article.url || article.link || '';
          const date = article.published_at || article.pubDate || '';
          return `
          <div class="article">
            <div class="article-content">
              <div class="article-title">${title}</div>
              ${summary ? `<div class="article-summary">${summary}</div>` : ''}
              <div class="article-footer">
                <span>${date ? `📅 ${new Date(date).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' })}` : ''}</span>
                ${url ? `<a href="${url}" class="article-link" target="_blank" rel="noopener noreferrer">المقال الأصلي</a>` : ''}
              </div>
            </div>
          </div>
          `;
        }).join('')}
      </div>
      `;
    }).join('')}
  </div>

  <div class="report-footer">
    <p><strong>نظام أخبار عين</strong></p>
    <p style="margin-top: 10px;">تم إنشاء هذا التقرير تلقائياً • جميع الحقوق محفوظة © ${new Date().getFullYear()}</p>
  </div>
</body>
</html>
      `

      const printWindow = window.open('', '_blank')
      printWindow.document.write(printContent)
      printWindow.document.close()
      setTimeout(() => {
        printWindow.print()
      }, 500)
    } catch (error) {
      console.error('Error exporting headlines PDF:', error)
      alert('فشل تصدير PDF')
    } finally {
      setExporting(false)
    }
  }
  
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between gap-3 mb-2">
          <div className="flex items-center gap-3">
            <Newspaper className="w-8 h-8 text-emerald-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                أهم العناوين
              </h1>
              <p className="text-gray-600">
                آخر الأخبار من المصادر المفضلة لديك في كل دولة
              </p>
            </div>
          </div>
          {headlines.length > 0 && (
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
      </div>
      
      {/* Country Selector */}
      <div className="card p-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          اختر الدولة {countries.length > 0 && `(${countries.length} دولة متاحة)`}
        </label>
        
        {countries.length === 0 && !error && (
          <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
            ⚠️ جاري تحميل الدول...
          </div>
        )}
        
        <div className="flex gap-3 items-center">
          <div className="flex-1 relative">
            <select
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              className="input w-full appearance-none"
              disabled={countries.length === 0}
            >
              <option value="">-- اختر دولة --</option>
              {countries.map((country) => (
                <option key={country.name} value={country.name}>
                  {country.name} ({country.count} مصدر)
                </option>
              ))}
            </select>
            <ChevronDown className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
          </div>
          
          <button
            onClick={fetchHeadlines}
            disabled={loading || !selectedCountry}
            className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'جاري التحميل...' : 'تحديث'}
          </button>
        </div>
        
        {lastFetch && (
          <div className="mt-3 text-xs text-gray-500">
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
