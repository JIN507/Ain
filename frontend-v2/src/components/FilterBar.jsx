import { Search, RefreshCw } from 'lucide-react'

export default function FilterBar({ filters, setFilters, onReset, countries, keywords }) {
  return (
    <div className="card p-5">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
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
          <option value="newest"> الأحدث في النظام</option>
          <option value="oldest"> الأقدم في النظام</option>
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
 