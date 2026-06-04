import { Search, RefreshCw } from 'lucide-react'
import SearchableSelect from './SearchableSelect'

export default function FilterBar({ filters, setFilters, onReset, countries, keywords }) {
  // Build option lists for the searchable selects.
  const countryOptions = (countries || []).map(c => ({
    value: c.name_ar,
    label: c.name_ar,
    count: c.article_count,
  }))
  const keywordOptions = (keywords || []).map(k => ({
    value: k.text_ar,
    label: k.text_ar,
  }))

  return (
    <div className="card p-4 relative z-40">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
        {/* Search */}
        <div className="relative lg:col-span-1">
          <Search className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="ابحث في الأخبار..."
            value={filters.search || ''}
            onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            className="input !pr-10"
          />
        </div>

        {/* Country — searchable */}
        <SearchableSelect
          value={filters.country || ''}
          onChange={(v) => setFilters({ ...filters, country: v })}
          options={countryOptions}
          placeholder={`جميع الدول (${countries?.length || 0})`}
          allLabel="جميع الدول"
          searchPlaceholder="ابحث عن دولة..."
        />

        {/* Keyword — searchable */}
        <SearchableSelect
          value={filters.keyword || ''}
          onChange={(v) => setFilters({ ...filters, keyword: v })}
          options={keywordOptions}
          placeholder="جميع الكلمات"
          allLabel="جميع الكلمات"
          searchPlaceholder="ابحث عن كلمة..."
        />

        {/* Sort Order */}
        <select
          value={filters.sortBy || 'newest'}
          onChange={(e) => setFilters({ ...filters, sortBy: e.target.value })}
          className="input"
        >
          <option value="newest">الأحدث</option>
          <option value="oldest">الأقدم</option>
        </select>

        {/* Reset */}
        <button onClick={onReset} className="btn-outline !py-2.5">
          <RefreshCw className="w-3.5 h-3.5" />
          إعادة تعيين
        </button>
      </div>
    </div>
  )
}
 