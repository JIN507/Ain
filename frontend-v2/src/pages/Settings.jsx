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
        <h1 className="text-2xl font-bold text-slate-900">إعدادات النظام</h1>
        <p className="text-sm text-slate-500 mt-0.5">التحكم في نظام المراقبة التلقائية</p>
      </div>

      {/* Main Control Card */}
      <div className="card p-6">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
          </div>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-3 h-3 rounded-full ${status?.running ? 'bg-teal-500 pulse-glow' : 'bg-slate-300'}`} />
              <div>
                <span className={`text-lg font-bold ${status?.running ? 'text-slate-900' : 'text-slate-500'}`}>
                  {status?.running ? 'النظام يعمل' : 'النظام متوقف'}
                </span>
                {status?.running && (
                  <p className="text-xs text-slate-400 mt-0.5">
                    <Clock className="w-3 h-3 inline ml-1" />
                    فحص كل {status.interval_minutes} دقيقة
                  </p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {!status?.running ? (
                <button onClick={startMonitoring} disabled={actionLoading} className="btn">
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  تشغيل
                </button>
              ) : (
                <button onClick={stopMonitoring} disabled={actionLoading} className="btn-danger">
                  {actionLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
                  إيقاف
                </button>
              )}
              <button onClick={fetchStatus} className="btn-ghost" title="تحديث">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* System Statistics */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">إحصائيات النظام</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-xl p-3" style={{ background: 'rgba(2,132,199,0.06)' }}>
            <div className="text-[11px] text-slate-400 font-medium">الفحوصات</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{status?.run_count || 0}</div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(15,118,110,0.06)' }}>
            <div className="text-[11px] text-slate-400 font-medium">آخر فحص</div>
            <div className="text-xs font-semibold text-slate-700 mt-1">{formatDate(status?.last_run)}</div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(139,92,246,0.06)' }}>
            <div className="text-[11px] text-slate-400 font-medium">القادم</div>
            <div className="text-xs font-semibold text-slate-700 mt-1">{formatDate(status?.next_run)}</div>
          </div>
          <div className="rounded-xl p-3" style={{ background: 'rgba(234,88,12,0.06)' }}>
            <div className="text-[11px] text-slate-400 font-medium">الأخطاء</div>
            <div className="text-xl font-bold text-slate-900 mt-1">{status?.error_count || 0}</div>
          </div>
        </div>

        {/* Last Result */}
        {status?.last_result && (
          <div className="mt-3 rounded-xl p-3" style={{ background: 'rgba(0,0,0,0.02)' }}>
            <h4 className="text-xs font-semibold text-slate-500 mb-2">آخر فحص:</h4>
            {status.last_result.success ? (
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <div className="text-lg font-bold text-slate-900">{status.last_result.total_fetched || 0}</div>
                  <div className="text-[11px] text-slate-400">جُلبت</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-slate-900">{status.last_result.total_matches || 0}</div>
                  <div className="text-[11px] text-slate-400">مطابقة</div>
                </div>
                <div>
                  <div className="text-lg font-bold text-slate-900">{status.last_result.total_saved || 0}</div>
                  <div className="text-[11px] text-slate-400">حُفظت</div>
                </div>
              </div>
            ) : status.last_result.skipped ? (
              <p className="text-xs text-amber-600">تم تخطي الفحص: {status.last_result.reason}</p>
            ) : (
              <p className="text-xs text-rose-600">خطأ: {status.last_result.error}</p>
            )}
          </div>
        )}
      </div>

      {/* Export & Reset */}
      <div className="card p-5" style={{ borderColor: 'rgba(234,88,12,0.15)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'rgba(234,88,12,0.08)' }}>
              <Download className="w-4 h-4" style={{ color: '#ea580c' }} />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">حفظ البيانات وإعادة تهيئة</h3>
              <p className="text-xs text-slate-400">تصدير Excel ثم حذف جميع البيانات</p>
            </div>
          </div>
          <button onClick={exportAndReset} disabled={exporting}
            className="btn-outline !text-xs !px-4 !py-2"
            style={{ color: '#ea580c', borderColor: 'rgba(234,88,12,0.25)' }}>
            {exporting ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> جاري...</> : 'حفظ وتهيئة'}
          </button>
        </div>
        {exportResult && !exportResult.error && (
          <div className="mt-3 rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(20,184,166,0.06)', color: '#0f766e' }}>
            تم تصدير {exportResult.article_count} مقالة بنجاح
          </div>
        )}
        {exportResult && exportResult.error && (
          <div className="mt-3 rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(225,29,72,0.06)', color: '#e11d48' }}>
            {exportResult.error}
          </div>
        )}
      </div>
    </div>
  )
}
