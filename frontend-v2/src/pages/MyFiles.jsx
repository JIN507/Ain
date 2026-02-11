import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { apiFetch } from '../apiClient'
import { Download, FileText, Trash2, RefreshCw, Eye, Loader2 } from 'lucide-react'

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
      a.download = filename || `export_${exportId}`
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
      const res = await apiFetch(`/api/exports/${exportId}/download?view=1`)
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
    return parts.join(' \u00B7 ')
  }

  const getSourceColor = (sourceType) => {
    switch (sourceType) {
      case 'direct_search': return { bg: 'rgba(59,130,246,0.08)', color: '#2563eb', label: 'البحث المباشر' }
      case 'top_headlines':  return { bg: 'rgba(139,92,246,0.08)', color: '#7c3aed', label: 'أهم العناوين' }
      default:               return { bg: 'rgba(15,118,110,0.08)', color: '#0f766e', label: 'لوحة المتابعة' }
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">ملفاتي</h1>
          <p className="text-sm text-slate-500 mt-0.5">الملفات المصدّرة من النظام</p>
        </div>
        <button onClick={loadExports} disabled={loading} className="btn-outline !py-2">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          تحديث
        </button>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="rounded-xl px-4 py-3 text-sm"
          style={{ background: 'rgba(225,29,72,0.06)', color: '#e11d48' }}>
          {error}
        </motion.div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
        </div>
      ) : exportsList.length === 0 ? (
        <div className="card p-16 text-center">
          <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.04)' }}>
            <FileText className="w-7 h-7 text-slate-300" />
          </div>
          <p className="text-slate-500 text-sm">لم تقم بتصدير أي ملفات حتى الآن</p>
          <p className="text-xs text-slate-400 mt-1">عند تصدير تقرير PDF أو Excel، سيظهر هنا</p>
        </div>
      ) : (
        <div className="space-y-3">
          {exportsList.map((rec, idx) => {
            const src = getSourceColor(rec.source_type)
            return (
              <motion.div
                key={rec.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
                className="card p-4 flex items-center gap-4"
              >
                {/* Icon */}
                <div className="w-10 h-10 rounded-xl flex-shrink-0 flex items-center justify-center"
                  style={{ background: src.bg }}>
                  <FileText className="w-5 h-5" style={{ color: src.color }} />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h3 className="text-sm font-semibold text-slate-900">تقرير {rec.article_count} خبر</h3>
                    <span className="badge" style={{ background: src.bg, color: src.color }}>{src.label}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-400">
                    <span>{formatDateTime(rec.created_at)}</span>
                    <span>\u00B7</span>
                    <span className="truncate">{summarizeFilters(rec.filters)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {rec.has_file && (
                    <>
                      <button onClick={() => handleView(rec.id)}
                        className="btn-ghost !px-2.5 !py-1.5" style={{ color: '#0f766e' }}>
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => handleDownload(rec.id, rec.filename)}
                        className="btn-ghost !px-2.5 !py-1.5" style={{ color: '#2563eb' }}>
                        <Download className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                  <button onClick={() => handleDelete(rec.id)}
                    className="btn-ghost !px-2.5 !py-1.5"
                    style={{ color: '#94a3b8' }}
                    onMouseEnter={(e) => e.currentTarget.style.color = '#e11d48'}
                    onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}>
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}

