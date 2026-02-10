import { Search, RefreshCw } from 'lucide-react'

export default function FilterBar({ filters, setFilters, onReset, countries, keywords }) {
  return (
    <div className="card p-4">
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

        {/* Country */}
        <select
          value={filters.country || ''}
          onChange={(e) => setFilters({ ...filters, country: e.target.value })}
          className="input"
        >
          <option value="">جميع الدول ({countries?.length || 0})</option>
          {countries && countries.map((country) => (
            <option key={country.name_ar} value={country.name_ar}>
              {country.name_ar} {country.article_count ? `(${country.article_count})` : ''}
            </option>
          ))}
        </select>

        {/* Keyword */}
        <select
          value={filters.keyword || ''}
          onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
          className="input"
        >
          <option value="">جميع الكلمات</option>
          {keywords && keywords.map((keyword) => (
            <option key={keyword.id} value={keyword.text_ar}>
              {keyword.text_ar}
            </option>
          ))}
        </select>

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
 