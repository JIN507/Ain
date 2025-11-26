/*
 * عين (Ain) - All Components in One File
 * 
 * This file contains all components for easy reference.
 * Split into individual files as needed:
 * - src/components/*.jsx
 * - src/pages/*.jsx
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  FileText, TrendingUp, AlertCircle, Globe as GlobeIcon, Search, Filter,
  ExternalLink, ThumbsUp, ThumbsDown, Minus, Plus, Trash2, RefreshCw,
  Play, Loader2, Check, X, Rss, Calendar
} from 'lucide-react'

// ============================================
// COMPONENTS
// ============================================

// ArticleCard Component
export function ArticleCard({ article }) {
  const sentimentConfig = {
    'إيجابي': { class: 'badge-positive', icon: ThumbsUp },
    'سلبي': { class: 'badge-negative', icon: ThumbsDown },
    'محايد': { class: 'badge-neutral', icon: Minus }
  }

  const config = sentimentConfig[article.sentiment] || sentimentConfig['محايد']
  const SentimentIcon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02 }}
      className="card hover:shadow-xl transition-all duration-300"
    >
      <div className="p-5">
        {/* Header Badges */}
        <div className="flex flex-wrap gap-2 mb-3">
          <span className="badge bg-emerald-100 text-emerald-800 border border-emerald-200">
            🌍 {article.country}
          </span>
          <span className="badge bg-white text-emerald-700 border border-emerald-200">
            📰 {article.source_name}
          </span>
        </div>

        {/* Keyword */}
        <div className="mb-3">
          <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 px-3 py-1 rounded-full text-sm font-semibold">
            🔑 {article.keyword}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 mb-3 leading-relaxed">
          {article.title_ar}
        </h3>

        {/* Summary */}
        <p className="text-gray-700 mb-4 leading-relaxed">
          {article.summary_ar}
        </p>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-emerald-100">
          <div className="flex items-center gap-2">
            <span className={`badge ${config.class} flex items-center gap-1`}>
              <SentimentIcon className="w-3 h-3" />
              {article.sentiment}
            </span>
          </div>

          <div className="flex flex-col items-end gap-1">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-600 hover:text-emerald-800 font-semibold text-sm flex items-center gap-1 transition"
            >
              المقال الأصلي
              <ExternalLink className="w-4 h-4" />
            </a>
            <span className="text-xs text-gray-500">
              {article.published_at ? new Date(article.published_at).toLocaleDateString('ar-SA') : 'غير محدد'}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// StatsOverview Component
export function StatsOverview({ stats }) {
  const statCards = [
    {
      label: 'إجمالي المقالات',
      value: stats.total,
      icon: FileText,
      gradient: 'from-emerald-500 to-emerald-700'
    },
    {
      label: 'مشاعر إيجابية',
      value: stats.positive,
      icon: TrendingUp,
      gradient: 'from-green-500 to-green-700'
    },
    {
      label: 'مشاعر سلبية',
      value: stats.negative,
      icon: AlertCircle,
      gradient: 'from-red-500 to-pink-600'
    },
    {
      label: 'الدول المراقبة',
      value: stats.countries || 0,
      icon: GlobeIcon,
      gradient: 'from-blue-500 to-indigo-600'
    }
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((stat, idx) => {
        const Icon = stat.icon
        return (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="card p-5"
          >
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg`}>
                <Icon className="w-7 h-7 text-white" />
              </div>
              <div>
                <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
                <div className="text-sm text-gray-600">{stat.label}</div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

// FilterBar Component
export function FilterBar({ filters, setFilters, onReset }) {
  return (
    <div className="card p-5">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="ابحث في الأخبار..."
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="input pr-10"
          />
        </div>

        {/* Country */}
        <select
          value={filters.country || ''}
          onChange={(e) => setFilters({ ...filters, country: e.target.value })}
          className="input"
        >
          <option value="">جميع الدول</option>
          {/* Options populated dynamically */}
        </select>

        {/* Keyword */}
        <select
          value={filters.keyword || ''}
          onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
          className="input"
        >
          <option value="">جميع الكلمات</option>
          {/* Options populated dynamically */}
        </select>

        {/* Sentiment */}
        <select
          value={filters.sentiment || ''}
          onChange={(e) => setFilters({ ...filters, sentiment: e.target.value })}
          className="input"
        >
          <option value="">جميع المشاعر</option>
          <option value="إيجابي">إيجابي</option>
          <option value="سلبي">سلبي</option>
          <option value="محايد">محايد</option>
        </select>

        {/* Reset */}
        <button onClick={onReset} className="btn-outline">
          <RefreshCw className="w-4 h-4" />
          إعادة تعيين
        </button>
      </div>
    </div>
  )
}

// Skeleton Component
export function Skeleton({ className }) {
  return <div className={`skeleton rounded ${className}`} />
}

// Loader Component
export function Loader({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="w-12 h-12 text-emerald-600 animate-spin mb-4" />
      {text && <p className="text-gray-600">{text}</p>}
    </div>
  )
}

// ============================================
// PAGES
// ============================================

// Dashboard Page
export function Dashboard() {
  const [loading, setLoading] = useState(false)
  const [articles, setArticles] = useState([])
  const [stats, setStats] = useState({ total: 0, positive: 0, negative: 0, neutral: 0 })
  const [filters, setFilters] = useState({})

  useEffect(() => {
    loadArticles()
    loadStats()
  }, [filters])

  const loadArticles = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams(filters)
      const res = await fetch(`/api/articles?${params}`)
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
      const res = await fetch('/api/articles/stats')
      const data = await res.json()
      setStats(data)
    } catch (error) {
      console.error('Error loading stats:', error)
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الخلاصة</h1>
          <p className="text-gray-600 mt-1">جميع الأخبار المراقبة</p>
        </div>
        {articles.length > 0 && (
          <button className="btn">
            📄 تصدير PDF
          </button>
        )}
      </div>

      {/* Stats */}
      <StatsOverview stats={stats} />

      {/* Filters */}
      <FilterBar 
        filters={filters}
        setFilters={setFilters}
        onReset={() => setFilters({})}
      />

      {/* Articles Grid */}
      {loading ? (
        <Loader text="جاري تحميل الأخبار..." />
      ) : articles.length === 0 ? (
        <div className="card p-12 text-center">
          <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لا توجد أخبار</h3>
          <p className="text-gray-600">اذهب إلى الإعدادات لتشغيل المراقبة</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {articles.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      )}

      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-800">
          💡 يتم تحديث الأخبار عند تشغيل المراقبة من صفحة الإعدادات
        </p>
      </div>
    </div>
  )
}

// Countries Page (Simplified)
export function Countries() {
  const [countries, setCountries] = useState([])

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الدول</h1>
        <p className="text-gray-600 mt-1">إدارة مصادر الأخبار حسب الدولة</p>
      </div>

      <div className="card p-8 text-center">
        <GlobeIcon className="w-16 h-16 text-emerald-600 mx-auto mb-4" />
        <h3 className="text-xl font-bold text-gray-900 mb-2">قريباً</h3>
        <p className="text-gray-600">إدارة الدول والمصادر</p>
      </div>
    </div>
  )
}

// Keywords Page (Simplified)
export function Keywords() {
  const [keywords, setKeywords] = useState([])
  const [newKeyword, setNewKeyword] = useState('')
  const [loading, setLoading] = useState(false)

  const addKeyword = async () => {
    if (!newKeyword.trim()) return

    setLoading(true)
    try {
      const res = await fetch('/api/keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text_ar: newKeyword })
      })

      if (res.ok) {
        setNewKeyword('')
        loadKeywords()
      }
    } catch (error) {
      console.error('Error adding keyword:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadKeywords = async () => {
    try {
      const res = await fetch('/api/keywords')
      const data = await res.json()
      setKeywords(data)
    } catch (error) {
      console.error('Error loading keywords:', error)
    }
  }

  useEffect(() => {
    loadKeywords()
  }, [])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الكلمات المفتاحية</h1>
        <p className="text-gray-600 mt-1">إدارة الكلمات المفتاحية للبحث</p>
      </div>

      {/* Add Keyword */}
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
        <p className="text-sm text-gray-600 mt-2">
          💡 سيتم ترجمة الكلمة تلقائياً إلى 5 لغات باستخدام Gemini AI
        </p>
      </div>

      {/* Keywords List */}
      <div className="space-y-4">
        {keywords.map((keyword) => (
          <div key={keyword.id} className="card p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-gray-900">{keyword.text_ar}</span>
                <span className="badge bg-green-100 text-green-800">نشط</span>
              </div>
              <button className="text-red-600 hover:text-red-700">
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
            {keyword.translations && (
              <div className="mt-4 p-4 bg-emerald-50 rounded-lg">
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
                  {Object.entries(JSON.parse(keyword.translations)).map(([lang, trans]) => (
                    <div key={lang}>
                      <div className="text-xs text-emerald-700 font-semibold mb-1">{lang}</div>
                      <div className="text-gray-800">{trans}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// Settings Page
export function Settings() {
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)

  const runMonitoring = async () => {
    setRunning(true)
    setProgress(0)
    setResult(null)

    try {
      const res = await fetch('/api/monitor/run', { method: 'POST' })
      const data = await res.json()
      setResult(data)
    } catch (error) {
      console.error('Error running monitoring:', error)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الإعدادات</h1>
        <p className="text-gray-600 mt-1">تشغيل المراقبة وإدارة النظام</p>
      </div>

      {/* Info Alert */}
      <div className="card p-4 bg-blue-50 border-blue-200">
        <p className="text-sm text-blue-800">
          ℹ️ يتم جلب الأخبار عند الضغط على زر التشغيل. العملية قد تستغرق بضع دقائق.
        </p>
      </div>

      {/* Run Button */}
      <div className="card p-8 text-center">
        <button
          onClick={runMonitoring}
          disabled={running}
          className="btn text-lg px-8 py-4 mx-auto"
        >
          {running ? (
            <>
              <Loader2 className="w-6 h-6 animate-spin" />
              جاري مراقبة المصادر...
            </>
          ) : (
            <>
              <Play className="w-6 h-6" />
              تشغيل المراقبة الآن
            </>
          )}
        </button>

        {running && (
          <div className="mt-6">
            <div className="w-full bg-gray-200 rounded-full h-3">
              <div className="bg-emerald-500 h-3 rounded-full transition-all duration-300" style={{ width: '100%' }} />
            </div>
          </div>
        )}

        {result && (
          <div className="mt-6 grid grid-cols-3 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{result.total_fetched}</div>
              <div className="text-sm text-blue-800">تم الفحص</div>
            </div>
            <div className="p-4 bg-emerald-50 rounded-lg">
              <div className="text-2xl font-bold text-emerald-600">{result.total_processed}</div>
              <div className="text-sm text-emerald-800">تمت المعالجة</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">
                <Check className="w-6 h-6 inline" />
              </div>
              <div className="text-sm text-green-800">اكتمل</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
