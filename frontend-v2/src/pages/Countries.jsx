import { useState, useEffect, useRef } from 'react'
import { Globe, Plus, Edit2, Trash2, CheckCircle, XCircle, Loader2, AlertTriangle, Search, ChevronDown, ChevronUp, Upload, Download, FileText } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Countries({ isAdmin = false }) {
  const [countries, setCountries] = useState([])
  const [sources, setSources] = useState([])
  const [editingSource, setEditingSource] = useState(null)
  const [addingSource, setAddingSource] = useState(false)
  const [testingSource, setTestingSource] = useState(null)
  const [sourceStatuses, setSourceStatuses] = useState({})
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCountries, setExpandedCountries] = useState({})
  // Bulk CSV import state
  const [bulkOpen, setBulkOpen] = useState(false)
  const [bulkFile, setBulkFile] = useState(null)
  const [bulkUploading, setBulkUploading] = useState(false)
  const [bulkResult, setBulkResult] = useState(null)
  const [bulkError, setBulkError] = useState('')
  const searchResultsRef = useRef(null)
  const firstResultRef = useRef(null)

  useEffect(() => {
    loadCountries()
    loadSources()
  }, [])

  const loadCountries = async () => {
    try {
      const res = await apiFetch('/api/countries')
      const data = await res.json()
      setCountries(data)
    } catch (error) {
      console.error('Error loading countries:', error)
    }
  }

  const loadSources = async () => {
    try {
      const res = await apiFetch('/api/sources')
      const data = await res.json()
      setSources(data)
    } catch (error) {
      console.error('Error loading sources:', error)
    }
  }

  const toggleCountry = async (id) => {
    try {
      await apiFetch(`/api/countries/${id}/toggle`, { method: 'POST' })
      loadCountries()
    } catch (error) {
      console.error('Error toggling country:', error)
    }
  }

  const toggleSource = async (id) => {
    try {
      await apiFetch(`/api/sources/${id}/toggle`, { method: 'POST' })
      loadSources()
    } catch (error) {
      console.error('Error toggling source:', error)
    }
  }

  const testSource = async (sourceId, url) => {
    setTestingSource(sourceId)
    try {
      // Use the existing diagnose endpoint by fetching all and finding our source
      const res = await apiFetch('/api/feeds/diagnose')
      const data = await res.json()
      
      if (data.success && data.feeds) {
        // Find the feed matching this URL
        const feedResult = data.feeds.find(f => f.url === url)
        
        if (feedResult) {
          setSourceStatuses(prev => ({
            ...prev,
            [sourceId]: feedResult.status
          }))
        } else {
          setSourceStatuses(prev => ({ ...prev, [sourceId]: 'error' }))
        }
      } else {
        setSourceStatuses(prev => ({ ...prev, [sourceId]: 'error' }))
      }
    } catch (error) {
      console.error('Error testing source:', error)
      setSourceStatuses(prev => ({ ...prev, [sourceId]: 'error' }))
    } finally {
      setTestingSource(null)
    }
  }

  const addSource = async (sourceData) => {
    try {
      const res = await apiFetch('/api/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sourceData)
      })
      
      if (res.ok) {
        loadSources()
        setAddingSource(false)
        alert('تم إضافة المصدر بنجاح')
      } else {
        const error = await res.json()
        throw new Error(error.error || 'Failed to add source')
      }
    } catch (error) {
      console.error('Error adding source:', error)
      alert('فشل إضافة المصدر: ' + error.message)
    }
  }

  const deleteSource = async (sourceId) => {
    if (!confirm('هل تريد حذف هذا المصدر؟')) return
    
    try {
      const res = await apiFetch(`/api/sources/${sourceId}`, {
        method: 'DELETE'
      })
      
      if (res.ok) {
        loadSources()
        alert('تم حذف المصدر بنجاح')
      } else {
        throw new Error('Failed to delete source')
      }
    } catch (error) {
      console.error('Error deleting source:', error)
      alert('فشل حذف المصدر')
    }
  }

  const updateSource = async (sourceId, updates) => {
    try {
      const res = await fetch(`/api/sources/${sourceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      
      if (res.ok) {
        loadSources()
        setEditingSource(null)
        alert('تم تحديث المصدر بنجاح')
      } else {
        throw new Error('Failed to update source')
      }
    } catch (error) {
      console.error('Error updating source:', error)
      alert('فشل تحديث المصدر')
    }
  }

  const getStatusBadge = (status) => {
    if (!status) return null
    
    const statusConfig = {
      ok: { icon: CheckCircle, text: 'يعمل', color: 'text-green-600 bg-green-50 border-green-200' },
      empty: { icon: AlertTriangle, text: 'فارغ', color: 'text-yellow-600 bg-yellow-50 border-yellow-200' },
      403: { icon: XCircle, text: '403', color: 'text-red-600 bg-red-50 border-red-200' },
      404: { icon: XCircle, text: '404', color: 'text-red-600 bg-red-50 border-red-200' },
      ssl: { icon: AlertTriangle, text: 'SSL', color: 'text-orange-600 bg-orange-50 border-orange-200' },
      dns: { icon: XCircle, text: 'DNS', color: 'text-red-600 bg-red-50 border-red-200' },
      timeout: { icon: AlertTriangle, text: 'بطيء', color: 'text-yellow-600 bg-yellow-50 border-yellow-200' },
      error: { icon: XCircle, text: 'خطأ', color: 'text-red-600 bg-red-50 border-red-200' },
    }

    const config = statusConfig[status] || statusConfig.error
    const Icon = config.icon

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold border ${config.color}`}>
        <Icon className="w-3 h-3" />
        {config.text}
      </span>
    )
  }

  // Toggle expanded state for a country
  const toggleCountryExpanded = (countryId) => {
    setExpandedCountries(prev => ({
      ...prev,
      [countryId]: !prev[countryId]
    }))
  }

  // Filter sources based on search query
  const filteredSources = sources.filter(source => {
    if (!searchQuery.trim()) return true
    
    const query = searchQuery.toLowerCase()
    return (
      source.name.toLowerCase().includes(query) ||
      source.url.toLowerCase().includes(query) ||
      source.country_name.toLowerCase().includes(query)
    )
  })

  // Auto-scroll to search results
  useEffect(() => {
    if (searchQuery && filteredSources.length > 0 && searchResultsRef.current) {
      // Small delay to ensure DOM is updated
      setTimeout(() => {
        searchResultsRef.current?.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'start' 
        })
      }, 100)
    }
  }, [searchQuery, filteredSources.length])

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">الدول</h1>
          <p className="text-sm text-slate-500 mt-0.5">إدارة مصادر الأخبار حسب الدولة</p>
        </div>
{isAdmin && (
        <div className="flex items-center gap-2">
          <button className="btn !bg-white !text-emerald-700 !border !border-emerald-600 hover:!bg-emerald-50" onClick={() => { setBulkOpen(true); setBulkResult(null); setBulkError(''); setBulkFile(null) }}>
            <Upload className="w-4 h-4" />
            رفع ملف CSV
          </button>
          <button className="btn" onClick={() => setAddingSource(true)}>
            <Plus className="w-4 h-4" />
            إضافة مصدر
          </button>
        </div>
        )}
      </div>

      {/* Search Bar */}
      <div className="card p-4">
        <div className="relative">
          <Search className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ابحث عن مصدر..."
            className="input !pr-10"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
            >
              ✕
            </button>
          )}
        </div>
        {searchQuery && (
          <div className="mt-2 text-[11px] text-slate-400">
            {filteredSources.length} مصدر من {sources.length}
          </div>
        )}
      </div>

      {/* Countries Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {countries.map((country) => {
          const countrySources = sources.filter(s => s.country_name === country.name_ar)
          
          return (
            <div
              key={country.id}
              className="card p-5 transition-all duration-300"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                    style={{ background: country.enabled ? 'rgba(15,118,110,0.08)' : 'rgba(0,0,0,0.04)' }}>
                    <Globe className="w-4 h-4" style={{ color: country.enabled ? '#0f766e' : '#94a3b8' }} />
                  </div>
                  <h3 className="text-base font-bold text-slate-900">{country.name_ar}</h3>
                </div>
{isAdmin ? (
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={country.enabled}
                    onChange={() => toggleCountry(country.id)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
                ) : (
                  <span className={`text-xs font-medium px-2 py-1 rounded-lg ${country.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                    {country.enabled ? 'مفعّل' : 'معطّل'}
                  </span>
                )}
              </div>

              {/* Source Count */}
              <div className="mb-3">
                <span className="text-xs text-slate-400">
                  {countrySources.length} مصدر
                </span>
              </div>

              {/* Sources Preview */}
              <div className="space-y-2">
                {(expandedCountries[country.id] ? countrySources : countrySources.slice(0, 3)).map((source) => (
                  <div key={source.id} className="flex items-center gap-2 text-xs text-slate-600">
                    <span className={`w-1 h-1 rounded-full flex-shrink-0 ${source.enabled ? 'bg-teal-500' : 'bg-slate-300'}`}></span>
                    <span className="truncate flex-1">{source.name}</span>
                    {!source.enabled && (
                      <span className="text-[10px] text-slate-400">(معطل)</span>
                    )}
                  </div>
                ))}
              </div>

              {/* Show More/Less Button */}
              {countrySources.length > 3 && (
                <button
                  onClick={() => toggleCountryExpanded(country.id)}
                  className="w-full mt-2 py-1.5 text-[11px] font-medium rounded-lg transition-all flex items-center justify-center gap-1"
                  style={{ color: '#0f766e' }}
                >
                  {expandedCountries[country.id] ? (
                    <>اخفِ <ChevronUp className="w-3 h-3" /></>
                  ) : (
                    <>المزيد ({countrySources.length - 3}) <ChevronDown className="w-3 h-3" /></>
                  )}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* No Results Message */}
      {searchQuery && filteredSources.length === 0 && (
        <div className="card p-12 text-center">
          <Search className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">لم يتم العثور على نتائج</h3>
          <p className="text-gray-600 mb-4">لم نجد أي مصدر يطابق "{searchQuery}"</p>
          <button
            onClick={() => setSearchQuery('')}
            className="btn"
          >
            مسح البحث
          </button>
        </div>
      )}

      {/* All Sources List with Management */}
      {filteredSources.length > 0 && (
        <div ref={searchResultsRef} className="card p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">
            {searchQuery ? `نتائج البحث (${filteredSources.length})` : 'جميع المصادر'}
          </h3>
          <div className="space-y-3">
            {filteredSources.map((source, index) => (
              <div 
                key={source.id} 
                ref={index === 0 && searchQuery ? firstResultRef : null}
                className={`flex items-center gap-3 p-4 rounded-lg border transition-all duration-300 ${
                  index === 0 && searchQuery 
                    ? 'bg-emerald-50 border-emerald-400 shadow-md scale-[1.02]' 
                    : 'bg-gray-50 border-gray-200 hover:border-emerald-300'
                }`}
              >
                {/* Source Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="font-semibold text-gray-900">{source.name}</h4>
                    {index === 0 && searchQuery && (
                      <span className="badge bg-emerald-100 text-emerald-800 border border-emerald-300 text-xs animate-pulse">
                        🎯 أول نتيجة
                      </span>
                    )}
                    {sourceStatuses[source.id] && getStatusBadge(sourceStatuses[source.id])}
                  </div>
                  <div className="text-xs text-gray-600 truncate">{source.url}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    🌍 {source.country_name}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center gap-2">
                  {isAdmin ? (
                    <>
                      {/* Toggle Switch */}
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={source.enabled}
                          onChange={() => toggleSource(source.id)}
                          className="sr-only peer"
                        />
                        <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                      </label>

                      {/* Test Button */}
                      <button
                        onClick={() => testSource(source.id, source.url)}
                        disabled={testingSource === source.id}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                        title="اختبار المصدر"
                      >
                        {testingSource === source.id ? (
                          <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                          <CheckCircle className="w-5 h-5" />
                        )}
                      </button>

                      {/* Edit Button */}
                      <button
                        onClick={() => setEditingSource(source)}
                        className="p-2 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                        title="تعديل المصدر"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>

                      {/* Delete Button */}
                      <button
                        onClick={() => deleteSource(source.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="حذف المصدر"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </>
                  ) : (
                    <span className={`text-xs font-medium px-2 py-1 rounded-lg ${source.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                      {source.enabled ? 'مفعّل' : 'معطّل'}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Source Modal */}
      {isAdmin && editingSource && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setEditingSource(null)}>
          <div className="card max-w-2xl w-full p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">تعديل المصدر</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.target)
                updateSource(editingSource.id, {
                  name: formData.get('name'),
                  url: formData.get('url'),
                })
              }}
              className="space-y-4"
            >
              {/* Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  اسم المصدر
                </label>
                <input
                  type="text"
                  name="name"
                  defaultValue={editingSource.name}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              {/* URL */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  رابط RSS
                </label>
                <input
                  type="url"
                  name="url"
                  defaultValue={editingSource.url}
                  required
                  dir="ltr"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              {/* Country (Read-only) */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  الدولة
                </label>
                <input
                  type="text"
                  value={editingSource.country_name}
                  disabled
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 cursor-not-allowed"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 justify-end pt-4">
                <button
                  type="button"
                  onClick={() => setEditingSource(null)}
                  className="px-6 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="btn"
                >
                  حفظ التعديلات
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk CSV Import Modal */}
      {isAdmin && bulkOpen && (
        <BulkImportModal
          file={bulkFile}
          setFile={setBulkFile}
          uploading={bulkUploading}
          result={bulkResult}
          error={bulkError}
          onClose={() => { if (!bulkUploading) setBulkOpen(false) }}
          onSubmit={async () => {
            if (!bulkFile) return
            setBulkUploading(true)
            setBulkError('')
            setBulkResult(null)
            try {
              const fd = new FormData()
              fd.append('file', bulkFile)
              const res = await apiFetch('/api/admin/sources/bulk-import', {
                method: 'POST',
                body: fd,
              })
              const data = await res.json()
              if (!res.ok) {
                setBulkError(data.error || 'فشل الاستيراد')
              } else {
                setBulkResult(data)
                // Refresh countries & sources so the page reflects new data
                loadCountries()
                loadSources()
              }
            } catch (e) {
              setBulkError(e.message || 'خطأ غير متوقع')
            } finally {
              setBulkUploading(false)
            }
          }}
        />
      )}

      {/* Add Source Modal */}
      {isAdmin && addingSource && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setAddingSource(false)}>
          <div className="card max-w-2xl w-full p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-2xl font-bold text-gray-900 mb-4">إضافة مصدر جديد</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.target)
                addSource({
                  country_name: formData.get('country_name'),
                  name: formData.get('name'),
                  url: formData.get('url'),
                })
              }}
              className="space-y-4"
            >
              {/* Country */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  الدولة
                </label>
                <select
                  name="country_name"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                >
                  <option value="">اختر الدولة</option>
                  {countries.map((country) => (
                    <option key={country.id} value={country.name_ar}>
                      {country.name_ar}
                    </option>
                  ))}
                </select>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  اسم المصدر
                </label>
                <input
                  type="text"
                  name="name"
                  placeholder="مثال: الجزيرة"
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              {/* URL */}
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  رابط RSS
                </label>
                <input
                  type="url"
                  name="url"
                  placeholder="https://example.com/rss"
                  required
                  dir="ltr"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 justify-end pt-4">
                <button
                  type="button"
                  onClick={() => setAddingSource(false)}
                  className="px-6 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                >
                  إلغاء
                </button>
                <button
                  type="submit"
                  className="btn"
                >
                  إضافة المصدر
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ──────────────────────────────────────────────────────────────────
// Bulk CSV Import Modal
// ──────────────────────────────────────────────────────────────────
function BulkImportModal({ file, setFile, uploading, result, error, onClose, onSubmit }) {
  const downloadTemplate = () => {
    const csv = '\uFEFF' + 'country_name,source_url,source_name\n' +
      'Saudi Arabia,https://www.example.com/rss,Example News\n' +
      'France,https://lemonde.fr/rss/une.xml,Le Monde\n' +
      'فيتنام,https://vnexpress.net/rss/tin-moi-nhat.rss,VnExpress\n'
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sources_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadReport = () => {
    if (!result || !result.details) return
    const rows = [['row_num','country_raw','country_ar','url','name','outcome','translation_source','message']]
    for (const d of result.details) {
      rows.push([d.row_num, d.country_raw, d.country_ar, d.url, d.name, d.outcome, d.translation_source, d.message])
    }
    const escape = (v) => {
      const s = (v == null ? '' : String(v))
      return /[,"\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s
    }
    const csv = '\uFEFF' + rows.map(r => r.map(escape).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'sources_import_report.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const outcomeStyle = (outcome) => {
    switch (outcome) {
      case 'added': return 'bg-green-50 text-green-700 border-green-200'
      case 'skipped_duplicate_url': return 'bg-amber-50 text-amber-700 border-amber-200'
      case 'skipped_duplicate_in_file': return 'bg-amber-50 text-amber-700 border-amber-200'
      case 'invalid_row': return 'bg-red-50 text-red-700 border-red-200'
      case 'error': return 'bg-red-50 text-red-700 border-red-200'
      default: return 'bg-slate-50 text-slate-700 border-slate-200'
    }
  }
  const outcomeLabel = (outcome) => ({
    added: 'مضاف',
    skipped_duplicate_url: 'مكرر في قاعدة البيانات',
    skipped_duplicate_in_file: 'مكرر داخل الملف',
    invalid_row: 'صف غير صالح',
    error: 'خطأ',
  }[outcome] || outcome)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div className="card max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-2xl font-bold text-gray-900">رفع ملف CSV لإضافة مصادر</h3>
          <button onClick={onClose} disabled={uploading} className="text-slate-400 hover:text-slate-600 disabled:opacity-50">✕</button>
        </div>

        {/* Instructions */}
        <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-4 text-sm text-slate-700 space-y-2">
          <div className="font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4" />
            تنسيق الملف المطلوب
          </div>
          <ul className="list-disc pr-6 space-y-1 text-xs">
            <li>الملف بصيغة <b>CSV</b> بترميز UTF-8</li>
            <li>الأعمدة بالترتيب: <b>اسم الدولة</b>، <b>رابط RSS</b>، <b>اسم المصدر</b></li>
            <li>الصف الأول كعناوين أعمدة <span className="text-slate-500">(اختياري — يكتشف تلقائياً)</span></li>
            <li>اسم الدولة يمكن أن يكون بأي لغة — سيتم ترجمته للعربية تلقائياً</li>
            <li>الروابط المكررة تُتجاهل تلقائياً مع تقرير مفصّل</li>
          </ul>
          <button type="button" onClick={downloadTemplate} className="inline-flex items-center gap-1.5 text-emerald-700 hover:text-emerald-800 text-xs font-semibold mt-1">
            <Download className="w-3.5 h-3.5" />
            تنزيل نموذج CSV
          </button>
        </div>

        {/* File picker */}
        {!result && (
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">اختر ملف CSV</label>
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={uploading}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-slate-700 file:mr-3 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-emerald-600 file:text-white hover:file:bg-emerald-700 file:cursor-pointer"
            />
            {file && (
              <div className="mt-2 text-xs text-slate-500">
                {file.name} — {(file.size / 1024).toFixed(1)} KB
              </div>
            )}
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">
            {error}
          </div>
        )}

        {/* Result summary */}
        {result && result.summary && (
          <div className="mb-4">
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 mb-3">
              <StatPill label="إجمالي" value={result.summary.total + result.summary.invalid_row} color="slate" />
              <StatPill label="مضاف" value={result.summary.added} color="green" />
              <StatPill label="دول جديدة" value={result.summary.countries_created} color="emerald" />
              <StatPill label="مكرر (DB)" value={result.summary.skipped_duplicate_url} color="amber" />
              <StatPill label="مكرر بالملف" value={result.summary.skipped_duplicate_in_file} color="amber" />
              <StatPill label="أخطاء" value={result.summary.invalid_row + result.summary.error} color="red" />
            </div>

            {/* Details table */}
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="max-h-80 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 sticky top-0">
                    <tr className="text-slate-600">
                      <th className="px-2 py-2 text-right font-semibold">صف</th>
                      <th className="px-2 py-2 text-right font-semibold">الدولة (الأصل)</th>
                      <th className="px-2 py-2 text-right font-semibold">الدولة (عربي)</th>
                      <th className="px-2 py-2 text-right font-semibold">المصدر</th>
                      <th className="px-2 py-2 text-right font-semibold">النتيجة</th>
                      <th className="px-2 py-2 text-right font-semibold">ملاحظة</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {result.details.map((d, i) => (
                      <tr key={i} className="hover:bg-slate-50">
                        <td className="px-2 py-1.5 text-slate-500 tabular-nums">{d.row_num}</td>
                        <td className="px-2 py-1.5 text-slate-700">{d.country_raw}</td>
                        <td className="px-2 py-1.5 text-slate-700">{d.country_ar}</td>
                        <td className="px-2 py-1.5 text-slate-700 truncate max-w-[160px]" title={d.name}>{d.name}</td>
                        <td className="px-2 py-1.5">
                          <span className={`inline-block px-2 py-0.5 rounded-full border text-[10px] font-semibold ${outcomeStyle(d.outcome)}`}>
                            {outcomeLabel(d.outcome)}
                          </span>
                        </td>
                        <td className="px-2 py-1.5 text-slate-500 truncate max-w-[200px]" title={d.message}>{d.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Buttons */}
        <div className="flex gap-3 justify-end pt-2">
          {result && (
            <button type="button" onClick={downloadReport} className="px-4 py-2 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg text-sm font-semibold">
              <Download className="w-4 h-4 inline -mt-0.5 ml-1" />
              تنزيل التقرير CSV
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            disabled={uploading}
            className="px-6 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            {result ? 'إغلاق' : 'إلغاء'}
          </button>
          {!result && (
            <button
              type="button"
              onClick={onSubmit}
              disabled={!file || uploading}
              className="btn disabled:opacity-50"
            >
              {uploading ? (
                <><Loader2 className="w-4 h-4 animate-spin" />جارٍ الاستيراد...</>
              ) : (
                <><Upload className="w-4 h-4" />استيراد</>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function StatPill({ label, value, color }) {
  const colorMap = {
    slate: 'bg-slate-50 text-slate-700 border-slate-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    red: 'bg-red-50 text-red-700 border-red-200',
  }
  return (
    <div className={`rounded-lg border px-3 py-2 ${colorMap[color] || colorMap.slate}`}>
      <div className="text-[10px] font-medium opacity-80">{label}</div>
      <div className="text-lg font-bold tabular-nums">{value || 0}</div>
    </div>
  )
}
