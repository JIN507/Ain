import { useState, useEffect, useRef } from 'react'
import { Globe, Plus, Edit2, Trash2, CheckCircle, XCircle, Loader2, AlertTriangle, Search, ChevronDown, ChevronUp } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Countries() {
  const [countries, setCountries] = useState([])
  const [sources, setSources] = useState([])
  const [editingSource, setEditingSource] = useState(null)
  const [addingSource, setAddingSource] = useState(false)
  const [testingSource, setTestingSource] = useState(null)
  const [sourceStatuses, setSourceStatuses] = useState({})
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedCountries, setExpandedCountries] = useState({})
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
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">الدول</h1>
          <p className="text-gray-600 mt-1">إدارة مصادر الأخبار حسب الدولة</p>
        </div>
        <button className="btn" onClick={() => setAddingSource(true)}>
          <Plus className="w-5 h-5" />
          إضافة مصدر مخصص
        </button>
      </div>

      {/* Search Bar */}
      <div className="card p-4">
        <div className="relative">
          <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="ابحث عن مصدر معين (الاسم، الرابط، أو الدولة)..."
            className="w-full pr-12 pl-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>
        {searchQuery && (
          <div className="mt-2 text-sm text-gray-600">
            🔍 تم العثور على {filteredSources.length} مصدر من أصل {sources.length}
          </div>
        )}
      </div>

      {/* Countries Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {countries.map((country) => {
          const countrySources = sources.filter(s => s.country_name === country.name_ar)
          
          return (
            <div
              key={country.id}
              className={`card p-6 transition-all duration-300 ${
                country.enabled ? 'border-emerald-400' : 'border-gray-300'
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <Globe className="w-6 h-6 text-emerald-600" />
                  <h3 className="text-xl font-bold text-gray-900">{country.name_ar}</h3>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={country.enabled}
                    onChange={() => toggleCountry(country.id)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-emerald-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:right-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
              </div>

              {/* Source Count */}
              <div className="mb-3">
                <span className="text-sm text-gray-600">
                  {countrySources.length} مصدر
                </span>
              </div>

              {/* Sources Preview */}
              <div className="space-y-2">
                {(expandedCountries[country.id] ? countrySources : countrySources.slice(0, 3)).map((source) => (
                  <div key={source.id} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className={source.enabled ? "text-emerald-600" : "text-gray-400"}>📡</span>
                    <span className="truncate flex-1">{source.name}</span>
                    {!source.enabled && (
                      <span className="text-xs text-gray-400">(معطل)</span>
                    )}
                  </div>
                ))}
              </div>

              {/* Show More/Less Button */}
              {countrySources.length > 3 && (
                <button
                  onClick={() => toggleCountryExpanded(country.id)}
                  className="w-full mt-3 px-3 py-2 text-sm font-semibold text-emerald-600 hover:text-emerald-800 hover:bg-emerald-50 rounded-lg transition-all flex items-center justify-center gap-2"
                >
                  {expandedCountries[country.id] ? (
                    <>
                      <ChevronUp className="w-4 h-4" />
                      اخفِ المصادر
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4" />
                      اظهر المزيد ({countrySources.length - 3} مصدر إضافي)
                    </>
                  )}
                </button>
              )}

              {/* Status Badge */}
              {country.enabled && (
                <div className="mt-3">
                  <span className="badge bg-green-100 text-green-800 border border-green-200">
                    مفعل
                  </span>
                </div>
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
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edit Source Modal */}
      {editingSource && (
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

      {/* Add Source Modal */}
      {addingSource && (
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
