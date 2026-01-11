import { useState, useEffect, useCallback } from 'react'
import { Play, Square, Loader2, Check, AlertCircle, Download, RefreshCw, Clock } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Settings() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [exportResult, setExportResult] = useState(null)

  // Fetch scheduler status
  const fetchStatus = useCallback(async () => {
    try {
      const res = await apiFetch('/api/monitor/status')
      if (res.ok) {
        const data = await res.json()
        setStatus(data)
      }
    } catch (error) {
      console.error('Error fetching status:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Poll status every 30 seconds when running
  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  const startMonitoring = async () => {
    setActionLoading(true)
    try {
      const res = await apiFetch('/api/monitor/start', { method: 'POST' })
      if (res.ok) {
        await fetchStatus()
      }
    } catch (error) {
      console.error('Error starting monitoring:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const stopMonitoring = async () => {
    setActionLoading(true)
    try {
      const res = await apiFetch('/api/monitor/stop', { method: 'POST' })
      if (res.ok) {
        await fetchStatus()
      }
    } catch (error) {
      console.error('Error stopping monitoring:', error)
    } finally {
      setActionLoading(false)
    }
  }

  const exportAndReset = async () => {
    if (!confirm('هل أنت متأكد من حفظ البيانات وإعادة تهيئة النظام؟\n\nسيتم:\n1. تصدير جميع الأخبار إلى ملف Excel\n2. حذف جميع الأخبار\n3. حذف جميع الكلمات المفتاحية\n\nهذا الإجراء لا يمكن التراجع عنه!')) {
      return
    }

    setExporting(true)
    setExportResult(null)

    try {
      const res = await apiFetch('/api/articles/export-and-reset', { method: 'POST' })
      
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'فشل التصدير')
      }

      const data = await res.json()
      setExportResult(data)
      
      // Download the file
      if (data.download_url) {
        window.location.href = data.download_url
      }

      // Refresh page after 2 seconds
      setTimeout(() => {
        window.location.reload()
      }, 2000)

    } catch (error) {
      console.error('Error exporting and resetting:', error)
      setExportResult({ error: error.message })
    } finally {
      setExporting(false)
    }
  }

  const formatDate = (isoString) => {
    if (!isoString) return '--'
    const date = new Date(isoString)
    return date.toLocaleString('ar-SA', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">تشغيل وإيقاف النظام</h1>
        <p className="text-gray-600 mt-1">المراقبة المستمرة للأخبار كل 10 دقائق</p>
      </div>

      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">نظام المراقبة المستمرة:</p>
            <ul className="list-disc list-inside space-y-1 mr-3">
              <li>عند التشغيل، يتم البحث تلقائياً كل <strong>10 دقائق</strong></li>
              <li>يعمل النظام في الخلفية حتى عند إغلاق المتصفح</li>
              <li>يمكن لعدة مستخدمين الوصول للنتائج في نفس الوقت</li>
              <li>يتم حفظ جميع النتائج في قاعدة البيانات</li>
              <li>يمكنك إيقاف النظام في أي وقت</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Main Control Card */}
      <div className="card p-8">
        {loading ? (
          <div className="text-center py-8">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-emerald-600" />
            <p className="text-gray-600 mt-2">جاري تحميل حالة النظام...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Status Indicator */}
            <div className="flex items-center justify-center gap-4">
              <div className={`w-4 h-4 rounded-full ${status?.running ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
              <span className={`text-2xl font-bold ${status?.running ? 'text-green-600' : 'text-gray-600'}`}>
                {status?.running ? 'النظام يعمل' : 'النظام متوقف'}
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-center gap-4">
              {!status?.running ? (
                <button
                  onClick={startMonitoring}
                  disabled={actionLoading}
                  className="btn text-lg px-8 py-4 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      جاري التشغيل...
                    </>
                  ) : (
                    <>
                      <Play className="w-6 h-6" />
                      تشغيل نظام عين
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={stopMonitoring}
                  disabled={actionLoading}
                  className="btn text-lg px-8 py-4 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {actionLoading ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      جاري الإيقاف...
                    </>
                  ) : (
                    <>
                      <Square className="w-6 h-6" />
                      إيقاف النظام
                    </>
                  )}
                </button>
              )}
              
              <button
                onClick={fetchStatus}
                className="btn text-lg px-4 py-4 bg-gray-200 hover:bg-gray-300 text-gray-700"
                title="تحديث الحالة"
              >
                <RefreshCw className="w-6 h-6" />
              </button>
            </div>

            {/* Running Status Details */}
            {status?.running && (
              <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
                <div className="flex items-center justify-center gap-2 text-green-700">
                  <Clock className="w-5 h-5" />
                  <span>يتم الفحص كل <strong>{status.interval_minutes}</strong> دقيقة</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* System Statistics */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-gray-900">إحصائيات النظام</h3>
          {status?.running && (
            <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold">
              يعمل الآن
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="text-sm text-blue-600">عدد الفحوصات</div>
            <div className="text-3xl font-bold text-blue-700">{status?.run_count || 0}</div>
          </div>
          <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-200">
            <div className="text-sm text-emerald-600">آخر فحص</div>
            <div className="text-lg font-bold text-emerald-700">{formatDate(status?.last_run)}</div>
          </div>
          <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
            <div className="text-sm text-purple-600">الفحص القادم</div>
            <div className="text-lg font-bold text-purple-700">{formatDate(status?.next_run)}</div>
          </div>
          <div className="p-4 bg-orange-50 rounded-lg border border-orange-200">
            <div className="text-sm text-orange-600">الأخطاء</div>
            <div className="text-3xl font-bold text-orange-700">{status?.error_count || 0}</div>
          </div>
        </div>

        {/* Last Result */}
        {status?.last_result && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-700 mb-2">نتيجة آخر فحص:</h4>
            {status.last_result.success ? (
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-blue-600">{status.last_result.total_fetched || 0}</div>
                  <div className="text-sm text-gray-600">تم جلبها</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-emerald-600">{status.last_result.total_matches || 0}</div>
                  <div className="text-sm text-gray-600">مطابقة</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">{status.last_result.total_saved || 0}</div>
                  <div className="text-sm text-gray-600">تم حفظها</div>
                </div>
              </div>
            ) : status.last_result.skipped ? (
              <p className="text-yellow-700">⚠️ تم تخطي الفحص: {status.last_result.reason}</p>
            ) : (
              <p className="text-red-700">❌ خطأ: {status.last_result.error}</p>
            )}
          </div>
        )}
      </div>

      {/* Export & Reset */}
      <div className="card p-6 border-2 border-orange-200">
        <div className="flex items-start gap-3 mb-4">
          <AlertCircle className="w-6 h-6 text-orange-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">حفظ البيانات وإعادة تهيئة</h3>
            <p className="text-sm text-gray-600 mb-3">
              تصدير جميع الأخبار إلى ملف Excel ثم حذف جميع البيانات من النظام
            </p>
            <ul className="text-sm text-gray-600 space-y-1 mr-5 list-disc">
              <li>سيتم تصدير جميع الأخبار إلى ملف Excel</li>
              <li>سيتم التحقق من سلامة التصدير قبل الحذف</li>
              <li>سيتم حذف جميع الأخبار والكلمات المفتاحية</li>
              <li>سيتم تنزيل ملف Excel تلقائياً</li>
            </ul>
          </div>
        </div>

        <button
          onClick={exportAndReset}
          disabled={exporting}
          className="btn bg-orange-600 hover:bg-orange-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {exporting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              جاري التصدير وإعادة التهيئة...
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              حفظ البيانات وإعادة تهيئة
            </>
          )}
        </button>

        {/* Export Result */}
        {exportResult && !exportResult.error && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg border border-green-200">
            <p className="text-green-800 font-semibold">✅ تم التصدير وإعادة التهيئة بنجاح!</p>
            <p className="text-sm text-green-700 mt-1">
              تم تصدير {exportResult.article_count} مقالة إلى {exportResult.filename}
            </p>
            <p className="text-sm text-green-700">جاري تحديث الصفحة...</p>
          </div>
        )}

        {/* Export Error */}
        {exportResult && exportResult.error && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg border border-red-200">
            <p className="text-red-800">❌ {exportResult.error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
