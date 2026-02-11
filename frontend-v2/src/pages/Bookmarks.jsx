import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Bookmark, Trash2, ExternalLink, ThumbsUp, ThumbsDown, Minus, Search, Loader2 } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Bookmarks() {
  const [bookmarks, setBookmarks] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [removing, setRemoving] = useState(null)

  useEffect(() => {
    loadBookmarks()
  }, [])

  const loadBookmarks = async () => {
    setLoading(true)
    try {
      const res = await apiFetch('/api/bookmarks')
      if (res.ok) {
        const data = await res.json()
        setBookmarks(data)
      }
    } catch (e) {
      console.error('Error loading bookmarks:', e)
    } finally {
      setLoading(false)
    }
  }

  const removeBookmark = async (id) => {
    setRemoving(id)
    try {
      const res = await apiFetch(`/api/bookmarks/${id}`, { method: 'DELETE' })
      if (res.ok) {
        setBookmarks(prev => prev.filter(b => b.id !== id))
      }
    } catch (e) {
      console.error('Error removing bookmark:', e)
    } finally {
      setRemoving(null)
    }
  }

  const sentimentConfig = {
    'إيجابي': { class: 'badge-positive', icon: ThumbsUp },
    'سلبي': { class: 'badge-negative', icon: ThumbsDown },
    'محايد': { class: 'badge-neutral', icon: Minus },
  }

  const filtered = searchQuery.trim()
    ? bookmarks.filter(b =>
        (b.title_ar || '').includes(searchQuery) ||
        (b.source_name || '').includes(searchQuery) ||
        (b.country || '').includes(searchQuery) ||
        (b.keyword_original || '').includes(searchQuery)
      )
    : bookmarks

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Bookmark className="w-6 h-6 text-amber-500" />
            المفضلة
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            المقالات المحفوظة — لا تُحذف عند إعادة التعيين الشهرية
          </p>
        </div>
        <span className="text-sm font-semibold px-3 py-1.5 rounded-lg"
          style={{ background: 'rgba(245,158,11,0.1)', color: '#d97706' }}>
          {bookmarks.length} محفوظ
        </span>
      </div>

      {/* Search */}
      {bookmarks.length > 0 && (
        <div className="relative">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ابحث في المفضلة..."
            className="w-full pr-10 pl-4 py-2.5 rounded-xl text-sm border"
            style={{ borderColor: 'rgba(0,0,0,0.08)', background: 'white' }}
          />
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
        </div>
      )}

      {/* Empty state */}
      {!loading && bookmarks.length === 0 && (
        <div className="text-center py-20">
          <Bookmark className="w-12 h-12 mx-auto text-slate-300 mb-4" />
          <p className="text-slate-500 font-medium">لا توجد مقالات محفوظة</p>
          <p className="text-sm text-slate-400 mt-1">
            اضغط على أيقونة الإشارة المرجعية في أي مقال لحفظه هنا
          </p>
        </div>
      )}

      {/* No results */}
      {!loading && bookmarks.length > 0 && filtered.length === 0 && (
        <div className="text-center py-12">
          <p className="text-slate-400">لا توجد نتائج لـ "{searchQuery}"</p>
        </div>
      )}

      {/* Bookmarks grid */}
      {!loading && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((b, i) => {
            const config = sentimentConfig[b.sentiment] || sentimentConfig['محايد']
            const SentimentIcon = config.icon
            return (
              <motion.div
                key={b.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.03 }}
                className="card flex flex-col overflow-hidden group"
              >
                {/* Image */}
                {b.image_url && (
                  <div className="w-full h-40 overflow-hidden bg-slate-50">
                    <img
                      src={b.image_url}
                      alt={b.title_ar}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      onError={(e) => { e.target.style.display = 'none' }}
                    />
                  </div>
                )}

                <div className="p-5 flex flex-col flex-1">
                  {/* Badges */}
                  <div className="flex flex-wrap items-center gap-1.5 mb-3">
                    {b.country && (
                      <span className="badge" style={{ background: 'rgba(15,118,110,0.08)', color: '#0f766e' }}>
                        {b.country}
                      </span>
                    )}
                    {b.source_name && (
                      <span className="badge" style={{ background: 'rgba(0,0,0,0.04)', color: '#64748b' }}>
                        {b.source_name}
                      </span>
                    )}
                    {b.keyword_original && (
                      <span className="badge" style={{ background: 'rgba(79,70,229,0.08)', color: '#4f46e5' }}>
                        {b.keyword_original}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h3 className="text-base font-bold text-slate-900 mb-2 leading-relaxed line-clamp-2">
                    {b.title_ar || b.title_original || 'بدون عنوان'}
                  </h3>

                  {/* Summary */}
                  {b.summary_ar && (
                    <p className="text-sm text-slate-600 leading-relaxed mb-4 line-clamp-3 flex-grow">
                      {b.summary_ar}
                    </p>
                  )}

                  {/* Footer */}
                  <div className="flex items-center justify-between pt-3 mt-auto"
                    style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                    <div className="flex items-center gap-2">
                      <span className={`badge ${config.class} flex items-center gap-1`}>
                        <SentimentIcon className="w-3 h-3" />
                        {b.sentiment || 'محايد'}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {b.published_at ? new Date(b.published_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }) : ''}
                      </span>
                    </div>

                    <div className="flex items-center gap-1">
                      {/* Remove bookmark */}
                      <button
                        onClick={() => removeBookmark(b.id)}
                        disabled={removing === b.id}
                        className="btn-ghost !px-2 !py-1 !text-xs"
                        style={{ color: '#ef4444' }}
                        title="إزالة من المفضلة"
                      >
                        {removing === b.id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Trash2 className="w-3.5 h-3.5" />
                        }
                      </button>

                      {/* Source link */}
                      <a
                        href={b.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost !px-2 !py-1 !text-xs !gap-1"
                        style={{ color: '#0f766e' }}
                      >
                        المصدر
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
