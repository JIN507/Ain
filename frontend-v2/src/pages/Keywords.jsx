import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Plus, Loader2, Trash2, ExternalLink, AlertCircle } from 'lucide-react'
import { apiFetch } from '../apiClient'

const MAX_KEYWORDS = 20

export default function Keywords({ onKeywordClick }) {
  const [keywords, setKeywords] = useState([])
  const [newKeyword, setNewKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState(0)

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
    
    // Check limit before sending (allow up to 5)
    if (keywords.length > MAX_KEYWORDS) {
      setError(`الحد الأقصى ${MAX_KEYWORDS} كلمات.`)
      setTimeout(() => setError(''), 5000)
      return
    }

    setLoading(true)
    setError('')
    setProgress(0)
    
    // Smooth progress animation during API call
    let currentProgress = 0
    const progressInterval = setInterval(() => {
      if (currentProgress < 30) currentProgress += 2
      else if (currentProgress < 60) currentProgress += 1
      else if (currentProgress < 85) currentProgress += 0.5
      setProgress(Math.min(currentProgress, 85))
    }, 100)
    
    try {
      const res = await apiFetch('/api/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_ar: newKeyword })
      })

      clearInterval(progressInterval)
      const data = await res.json()
      
      if (res.ok) {
        setProgress(100)
        setNewKeyword('')
        setSuccess('تمت إضافة الكلمة المفتاحية بنجاح')
        setTimeout(() => setSuccess(''), 3000)
        await loadKeywords()
      } else {
        setProgress(0)
        setError(data.error || 'حدث خطأ أثناء إضافة الكلمة')
        setTimeout(() => setError(''), 5000)
      }
    } catch (err) {
      clearInterval(progressInterval)
      setProgress(0)
      console.error('Error adding keyword:', err)
      setError('حدث خطأ في الاتصال')
      setTimeout(() => setError(''), 5000)
    } finally {
      setLoading(false)
      setTimeout(() => setProgress(0), 500)
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

  const isOverLimit = keywords.length > MAX_KEYWORDS
  const canAdd = keywords.length < MAX_KEYWORDS

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">الكلمات المفتاحية</h1>
          <p className="text-sm text-slate-500 mt-0.5">إدارة كلمات الرصد والمتابعة</p>
        </div>

      </div>

      {/* Alerts */}
      {success && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl px-4 py-3 text-sm font-medium"
          style={{ background: 'rgba(20,184,166,0.08)', color: '#0f766e' }}>
          {success}
        </motion.div>
      )}
      {error && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-xl px-4 py-3 text-sm font-medium flex items-center gap-2"
          style={{ background: 'rgba(225,29,72,0.06)', color: '#e11d48' }}>
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </motion.div>
      )}

      {/* Add Keyword */}
      <div className="card p-5">
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
          <button onClick={addKeyword} disabled={loading || !canAdd} className="btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            إضافة
          </button>
        </div>
        
        {/* Progress Bar */}
        {loading && (
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-medium" style={{ color: '#0f766e' }}>جاري ترجمة الكلمة إلى 33 لغة...</span>
              <span className="text-xs font-semibold" style={{ color: '#0f766e' }}>{Math.round(progress)}%</span>
            </div>
            <div className="w-full rounded-full h-1.5 overflow-hidden" style={{ background: 'rgba(0,0,0,0.06)' }}>
              <div 
                className="h-1.5 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #0f766e, #14b8a6)' }}
              />
            </div>
          </div>
        )}
        
        {!loading && (
          <p className="text-xs text-slate-400 mt-3">
            يتم ترجمة الكلمة تلقائياً إلى 33 لغة للرصد الشامل
          </p>
        )}
      </div>

      {/* Keywords List */}
      <div className="space-y-3">
        {keywords.length === 0 ? (
          <div className="card p-12 text-center">
            <p className="text-slate-400 text-sm">لا توجد كلمات مفتاحية. أضف كلمة للبدء.</p>
          </div>
        ) : (
          keywords.map((keyword, idx) => (
            <motion.div
              key={keyword.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="card p-5"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <button
                    onClick={() => onKeywordClick?.(keyword.text_ar)}
                    className="text-lg font-bold text-slate-900 hover:text-teal-700 transition-colors cursor-pointer flex items-center gap-2 group"
                    title="عرض نتائج هذه الكلمة"
                  >
                    {keyword.text_ar}
                    <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity text-teal-600" />
                  </button>
                  <span className="badge" style={{ background: 'rgba(20,184,166,0.1)', color: '#0f766e' }}>نشط</span>
                </div>
                <button 
                  onClick={() => deleteKeyword(keyword.id)}
                  className="p-2 rounded-lg transition-all duration-200 hover:scale-105"
                  style={{ color: '#94a3b8' }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = '#e11d48'; e.currentTarget.style.background = 'rgba(225,29,72,0.06)' }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = '#94a3b8'; e.currentTarget.style.background = 'transparent' }}
                  title="حذف"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Translations */}
              {keyword.translations && (
                <div className="rounded-xl p-3.5" style={{ background: 'rgba(0,0,0,0.02)' }}>
                  <div className="grid grid-cols-3 md:grid-cols-5 gap-3 text-sm">
                    {Object.entries(JSON.parse(keyword.translations)).map(([lang, trans]) => (
                      <div key={lang}>
                        <div className="text-[10px] text-slate-400 font-semibold mb-0.5 uppercase">{lang}</div>
                        <div className="text-slate-700 font-medium text-xs">{trans}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          ))
        )}
      </div>
    </div>
  )
}
