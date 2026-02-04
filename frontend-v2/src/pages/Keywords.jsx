import { useState, useEffect } from 'react'
import { Plus, Loader2, Trash2, RefreshCw, ExternalLink } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Keywords({ onKeywordClick }) {
  const [keywords, setKeywords] = useState([])
  const [newKeyword, setNewKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')

  useEffect(() => {
    loadKeywords()
  }, [])

  const loadKeywords = async () => {
    try {
      const res = await apiFetch('/api/keywords')
      const data = await res.json()
      setKeywords(data)
    } catch (error) {
      console.error('Error loading keywords:', error)
    }
  }

  const addKeyword = async () => {
    if (!newKeyword.trim()) return

    setLoading(true)
    try {
      const res = await apiFetch('/api/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_ar: newKeyword })
      })

      if (res.ok) {
        setNewKeyword('')
        setSuccess('تمت إضافة الكلمة المفتاحية بنجاح')
        setTimeout(() => setSuccess(''), 3000)
        loadKeywords()
      }
    } catch (error) {
      console.error('Error adding keyword:', error)
    } finally {
      setLoading(false)
    }
  }

  const deleteKeyword = async (id) => {
    if (!confirm('هل تريد حذف هذه الكلمة المفتاحية؟')) return

    try {
      await apiFetch(`/api/keywords/${id}`, { method: 'DELETE' })
      loadKeywords()
    } catch (error) {
      console.error('Error deleting keyword:', error)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الكلمات المفتاحية</h1>
        <p className="text-gray-600 mt-1">إدارة الكلمات المفتاحية للبحث</p>
      </div>

      {/* Success Alert */}
      {success && (
        <div className="card p-4 bg-emerald-50 border-emerald-200">
          <p className="text-sm text-emerald-800">✅ {success}</p>
        </div>
      )}

      {/* Add Keyword Card */}
      <div className="card p-6">
        <div className="flex gap-3">
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addKeyword()}
            placeholder="اكتب الكلمة المفتاحية بالعربية..."
            className="input flex-1"
            disabled={loading}
          />
          <button onClick={addKeyword} disabled={loading} className="btn">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            إضافة
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-3">
          💡 قد يستغرق الأمر بعض الوقت لترجمة الكلمة تلقائياً إلى 33 لغة باستخدام Google Translate
        </p>
      </div>

      {/* Keywords List */}
      <div className="space-y-4">
        {keywords.length === 0 ? (
          <div className="card p-12 text-center">
            <p className="text-gray-600">لا توجد كلمات مفتاحية. أضف كلمة للبدء.</p>
          </div>
        ) : (
          keywords.map((keyword) => (
            <div key={keyword.id} className="card p-6 hover:shadow-xl transition-all duration-300">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => onKeywordClick?.(keyword.text_ar)}
                    className="text-2xl font-bold text-gray-900 hover:text-emerald-600 transition-colors cursor-pointer flex items-center gap-2 group"
                    title="عرض نتائج هذه الكلمة"
                  >
                    {keyword.text_ar}
                    <ExternalLink className="w-5 h-5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                  <span className="badge bg-green-100 text-green-800 border border-green-200">نشط</span>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => loadKeywords()}
                    className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition"
                    title="تحديث"
                  >
                    <RefreshCw className="w-5 h-5" />
                  </button>
                  <button 
                    onClick={() => deleteKeyword(keyword.id)}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                    title="حذف"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Translations */}
              {keyword.translations && (
                <div className="p-4 bg-emerald-50 rounded-lg border border-emerald-100">
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                    {Object.entries(JSON.parse(keyword.translations)).map(([lang, trans]) => (
                      <div key={lang}>
                        <div className="text-xs text-emerald-700 font-semibold mb-1 uppercase">{lang}</div>
                        <div className="text-gray-800 font-medium">{trans}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
