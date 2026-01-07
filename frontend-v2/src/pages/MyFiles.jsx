import { useEffect, useState } from 'react'
import { apiFetch } from '../apiClient'
import { Download, FileText, Trash2, RefreshCw, Eye } from 'lucide-react'

export default function MyFiles() {
  const [exportsList, setExportsList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadExports = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/exports')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل تحميل السجلات')
      }
      const data = await res.json()
      setExportsList(data)
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadExports()
  }, [])

  const handleDownload = async (exportId, filename) => {
    try {
      const res = await apiFetch(`/api/exports/${exportId}/download`)
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل تحميل الملف')
      }
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename || `export_${exportId}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const handleView = async (exportId) => {
    try {
      const res = await apiFetch(`/api/exports/${exportId}/download`)
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل عرض الملف')
      }
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      window.open(url, '_blank')
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const handleDelete = async (exportId) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا السجل؟')) return
    try {
      const res = await apiFetch(`/api/exports/${exportId}`, { method: 'DELETE' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل حذف السجل')
      }
      await loadExports()
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const formatDateTime = (iso) => {
    if (!iso) return ''
    try {
      const d = new Date(iso)
      return `${d.toLocaleDateString('en-GB')} - ${d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`
    } catch {
      return iso
    }
  }

  const summarizeFilters = (filters) => {
    if (!filters) return 'بدون مرشحات'
    const parts = []
    if (filters.country) parts.push(`الدولة: ${filters.country}`)
    if (filters.keyword) parts.push(`الكلمة: ${filters.keyword}`)
    if (filters.sentiment) parts.push(`المزاج: ${filters.sentiment}`)
    if (filters.sortBy) parts.push(`الترتيب: ${filters.sortBy === 'newest' ? 'الأحدث' : 'الأقدم'}`)
    if (parts.length === 0) return 'كل الأخبار'
    return parts.join(' • ')
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">ملفاتي</h1>
          <p className="text-gray-600 mt-1">سجل الملفات التي قمت بتصديرها من لوحة المتابعة</p>
        </div>
        <button
          onClick={loadExports}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-semibold text-sm disabled:opacity-60"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          تحديث
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      <div className="card p-4">
        {loading ? (
          <div className="text-sm text-gray-500 text-center py-8">جاري التحميل...</div>
        ) : exportsList.length === 0 ? (
          <div className="text-sm text-gray-500 text-center py-8">
            <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p>لم تقم بتصدير أي ملفات حتى الآن</p>
            <p className="text-xs mt-1">عند تصدير تقرير PDF من لوحة المتابعة، سيظهر هنا</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {exportsList.map((rec) => (
              <div
                key={rec.id}
                className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition bg-white"
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <FileText className="w-10 h-10 text-red-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-gray-900">
                      تقرير {rec.article_count} خبر
                    </h3>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatDateTime(rec.created_at)}
                    </p>
                    <p className="text-xs text-gray-600 mt-1 truncate" title={summarizeFilters(rec.filters)}>
                      {summarizeFilters(rec.filters)}
                    </p>
                    {rec.user_name && (
                      <p className="text-xs text-blue-600 mt-1 font-medium">
                        👤 {rec.user_name}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
                  {rec.has_file && (
                    <>
                      <button
                        onClick={() => handleView(rec.id)}
                        className="flex-1 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold hover:bg-emerald-100"
                      >
                        <Eye className="w-3 h-3" />
                        عرض
                      </button>
                      <button
                        onClick={() => handleDownload(rec.id, rec.filename)}
                        className="flex-1 inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-xs font-semibold hover:bg-blue-100"
                      >
                        <Download className="w-3 h-3" />
                        تحميل
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleDelete(rec.id)}
                    className="inline-flex items-center justify-center px-3 py-1.5 rounded-lg bg-red-50 text-red-700 border border-red-200 text-xs font-semibold hover:bg-red-100"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
