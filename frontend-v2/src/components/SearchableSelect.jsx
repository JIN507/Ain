import { useState, useRef, useEffect, useMemo } from 'react'
import { ChevronDown, Search, X } from 'lucide-react'

/**
 * SearchableSelect — accessible searchable dropdown (combobox).
 *
 * Props:
 *   value          : currently selected value (string), or '' for none
 *   onChange(value): called when user picks an option
 *   options        : Array<{ value: string, label: string, count?: number }>
 *   placeholder    : label shown when no value is selected
 *   allLabel       : label for the "all / clear" option (defaults to "الكل")
 *   searchPlaceholder
 *   className      : extra classes for the trigger button
 */
export default function SearchableSelect({
  value = '',
  onChange,
  options = [],
  placeholder = 'اختر...',
  allLabel = 'الكل',
  searchPlaceholder = 'ابحث...',
  className = '',
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const rootRef = useRef(null)
  const inputRef = useRef(null)
  const listRef = useRef(null)

  // Close on outside click
  useEffect(() => {
    if (!open) return
    const onDoc = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  // Focus the search input when opening
  useEffect(() => {
    if (open && inputRef.current) {
      // small timeout so the focus lands after the popover renders
      const t = setTimeout(() => inputRef.current?.focus(), 0)
      return () => clearTimeout(t)
    }
  }, [open])

  // Reset highlight when query changes
  useEffect(() => { setActiveIndex(0) }, [query, open])

  // Filter options by query (case-insensitive, includes match).
  // Arabic input works naturally since we just compare strings.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return options
    return options.filter(opt => (opt.label || '').toLowerCase().includes(q))
  }, [options, query])

  const selected = options.find(o => o.value === value)
  const triggerLabel = selected ? selected.label : placeholder

  const pick = (val) => {
    onChange?.(val)
    setOpen(false)
    setQuery('')
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(i => Math.min(i + 1, filtered.length)) // +1 because of "all" row
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (activeIndex === 0) pick('')
      else pick(filtered[activeIndex - 1]?.value)
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setOpen(false)
      setQuery('')
    }
  }

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="input flex items-center justify-between gap-2 w-full text-right"
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={`truncate ${selected ? 'text-slate-800' : 'text-slate-400'}`}>
          {triggerLabel}
        </span>
        <span className="flex items-center gap-1 flex-shrink-0">
          {selected && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); pick('') }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); pick('') } }}
              className="text-slate-400 hover:text-slate-600 p-0.5 rounded"
              title="مسح"
            >
              <X className="w-3.5 h-3.5" />
            </span>
          )}
          <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {/* Popover */}
      {open && (
        <div
          className="absolute z-50 mt-1 w-full bg-white rounded-xl shadow-lg overflow-hidden"
          style={{ border: '1px solid rgba(0,0,0,0.08)' }}
        >
          {/* Search input */}
          <div className="p-2 border-b border-slate-100 relative">
            <Search className="absolute right-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={searchPlaceholder}
              className="input !pr-9 !py-2 text-sm"
            />
          </div>

          {/* Options list */}
          <ul
            ref={listRef}
            role="listbox"
            className="max-h-64 overflow-y-auto py-1"
          >
            {/* "All" / clear option */}
            <li
              role="option"
              aria-selected={value === ''}
              onClick={() => pick('')}
              onMouseEnter={() => setActiveIndex(0)}
              className={`px-3 py-2 text-sm cursor-pointer flex items-center justify-between gap-2 ${
                activeIndex === 0 ? 'bg-slate-50' : ''
              } ${value === '' ? 'font-bold text-teal-700' : 'text-slate-700'}`}
            >
              <span>{allLabel}</span>
              <span className="text-[10px] text-slate-400">{options.length}</span>
            </li>

            {filtered.length === 0 ? (
              <li className="px-3 py-3 text-xs text-slate-400 text-center">
                لا توجد نتائج
              </li>
            ) : (
              filtered.map((opt, i) => {
                const isActive = activeIndex === i + 1
                const isSelected = opt.value === value
                return (
                  <li
                    key={opt.value}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => pick(opt.value)}
                    onMouseEnter={() => setActiveIndex(i + 1)}
                    className={`px-3 py-2 text-sm cursor-pointer flex items-center justify-between gap-2 ${
                      isActive ? 'bg-slate-50' : ''
                    } ${isSelected ? 'font-bold text-teal-700' : 'text-slate-700'}`}
                  >
                    <span className="truncate">{opt.label}</span>
                    {typeof opt.count === 'number' && (
                      <span className="text-[10px] text-slate-400 flex-shrink-0">
                        {opt.count}
                      </span>
                    )}
                  </li>
                )
              })
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
