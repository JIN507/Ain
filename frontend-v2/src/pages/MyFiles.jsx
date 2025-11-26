import { useEffect, useState } from 'react'

export default function MyFiles() {
  const [exportsList, setExportsList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadExports = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/exports')
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">ملفاتي</h1>
          <p className="text-gray-600 mt-1">سجل ملفات PDF التي قمت بتصديرها من لوحة المتابعة</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      <div className="card p-4 overflow-x-auto">
        {loading ? (
          <div className="text-sm text-gray-500">جاري التحميل...</div>
        ) : exportsList.length === 0 ? (
          <div className="text-sm text-gray-500">لم تقم بتصدير أي ملفات حتى الآن.</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="py-2 px-3 text-right font-semibold text-gray-700">التاريخ والوقت</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">عدد الأخبار</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">المرشحات</th>
              </tr>
            </thead>
            <tbody>
              {exportsList.map((rec) => (
                <tr key={rec.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-3 whitespace-nowrap">{formatDateTime(rec.created_at)}</td>
                  <td className="py-2 px-3">{rec.article_count}</td>
                  <td className="py-2 px-3 text-gray-700">{summarizeFilters(rec.filters)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
