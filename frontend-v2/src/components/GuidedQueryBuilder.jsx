import { useState, useEffect, useCallback, useMemo } from 'react'
import { X, Plus, ChevronDown, ChevronUp, Copy, Check, AlertCircle, Lightbulb, Search } from 'lucide-react'

/**
 * compileToQ - Compile structured query state into a valid boolean search string
 * 
 * Rules:
 * - MUST terms join with AND
 * - ANY terms join with OR  
 * - Exclude terms become NOT (term1 OR term2 ...)
 * - If both MUST and ANY exist: (MUST_ANDS AND (ANY_ORS))
 * - Proper parentheses for precedence
 * 
 * @param {Object} builder - { must: string[], any: string[], exclude: string[] }
 * @returns {string} - Compiled query string
 */
export function compileToQ(builder) {
  const { must = [], any = [], exclude = [] } = builder
  
  // Sanitize and deduplicate terms
  const sanitize = (term) => {
    let cleaned = term.trim()
    // Escape quotes if term contains spaces and isn't already quoted
    if (cleaned.includes(' ') && !cleaned.startsWith('"')) {
      cleaned = `"${cleaned.replace(/"/g, '')}"`
    }
    return cleaned
  }
  
  const dedupe = (arr) => [...new Set(arr.map(sanitize).filter(Boolean))]
  
  const mustTerms = dedupe(must)
  const anyTerms = dedupe(any)
  const excludeTerms = dedupe(exclude)
  
  // Build query parts
  let queryParts = []
  
  // Handle MUST (AND) terms
  if (mustTerms.length > 0) {
    const mustPart = mustTerms.join(' AND ')
    queryParts.push(mustTerms.length > 1 ? `(${mustPart})` : mustPart)
  }
  
  // Handle ANY (OR) terms
  if (anyTerms.length > 0) {
    const anyPart = anyTerms.join(' OR ')
    const anyWrapped = anyTerms.length > 1 ? `(${anyPart})` : anyPart
    
    if (queryParts.length > 0) {
      // Combine with MUST using AND
      queryParts[0] = `(${queryParts[0]} AND ${anyWrapped})`
    } else {
      queryParts.push(anyWrapped)
    }
  }
  
  // Handle EXCLUDE (NOT) terms
  if (excludeTerms.length > 0) {
    const excludePart = excludeTerms.join(' OR ')
    const excludeWrapped = excludeTerms.length > 1 ? `(${excludePart})` : excludePart
    
    if (queryParts.length > 0) {
      queryParts.push(`NOT ${excludeWrapped}`)
    }
    // Note: NOT alone without positive terms is invalid - handled in validation
  }
  
  return queryParts.join(' ').trim()
}

/**
 * Validate query state
 * @returns {Object} - { valid: boolean, error: string|null }
 */
export function validateQuery(builder, basicText = '') {
  const { must = [], any = [], exclude = [] } = builder
  const hasPositive = must.length > 0 || any.length > 0 || basicText.trim().length > 0
  const hasOnlyExclude = exclude.length > 0 && !hasPositive
  
  if (hasOnlyExclude) {
    return { 
      valid: false, 
      error: 'أضف كلمة بحث واحدة على الأقل قبل الاستبعاد' 
    }
  }
  
  return { valid: true, error: null }
}


// Chip component
const Chip = ({ text, onRemove, color = 'emerald' }) => {
  const colors = {
    emerald: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    blue: 'bg-blue-100 text-blue-800 border-blue-300',
    red: 'bg-red-100 text-red-800 border-red-300',
  }
  
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${colors[color]} transition-all hover:shadow-sm`}>
      {text}
      <button
        onClick={onRemove}
        className="hover:bg-black/10 rounded-full p-0.5 transition-colors"
        aria-label="إزالة"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </span>
  )
}

// Chip input component
const ChipInput = ({ value, onChange, onAdd, placeholder, color, chips, onRemoveChip }) => {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && value.trim()) {
      e.preventDefault()
      onAdd()
    }
  }
  
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {chips.map((chip, i) => (
          <Chip 
            key={i} 
            text={chip} 
            color={color} 
            onRemove={() => onRemoveChip(i)} 
          />
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="input flex-1 text-sm"
        />
        <button
          onClick={onAdd}
          disabled={!value.trim()}
          className="btn-outline px-3 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="إضافة"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

/**
 * GuidedQueryBuilder - Progressive visual query builder
 * 
 * Props:
 * - onQueryChange: (query: string, isValid: boolean) => void
 * - onBuilderChange: (builder: Object) => void
 * - maxLength: number
 */
export default function GuidedQueryBuilder({ 
  onQueryChange, 
  onBuilderChange,
  maxLength = 512,
  initialBasicText = ''
}) {
  // Basic search text
  const [basicText, setBasicText] = useState(initialBasicText)
  
  // Builder state
  const [builder, setBuilder] = useState({
    must: [],
    any: [],
    exclude: []
  })
  
  // Input states
  const [mustInput, setMustInput] = useState('')
  const [anyInput, setAnyInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')
  
  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [copied, setCopied] = useState(false)
  
  // Compile query
  const compiledQuery = useMemo(() => {
    const builderQuery = compileToQ(builder)
    
    // If basic text exists and builder is empty, use basic text
    if (basicText.trim() && !builderQuery) {
      return basicText.trim()
    }
    
    // If both exist, combine them
    if (basicText.trim() && builderQuery) {
      return `${basicText.trim()} AND ${builderQuery}`
    }
    
    return builderQuery
  }, [basicText, builder])
  
  // Validation
  const validation = useMemo(() => {
    return validateQuery(builder, basicText)
  }, [builder, basicText])
  
  const queryLength = compiledQuery.length
  const isOverLimit = queryLength > maxLength
  const isValid = validation.valid && !isOverLimit && queryLength > 0
  
  // Notify parent of changes
  useEffect(() => {
    onQueryChange?.(compiledQuery, isValid)
  }, [compiledQuery, isValid, onQueryChange])
  
  useEffect(() => {
    onBuilderChange?.(builder)
  }, [builder, onBuilderChange])
  
  // Chip handlers
  const addChip = (type, value, inputSetter) => {
    const trimmed = value.trim()
    if (!trimmed) return
    
    setBuilder(prev => ({
      ...prev,
      [type]: [...prev[type], trimmed]
    }))
    inputSetter('')
  }
  
  const removeChip = (type, index) => {
    setBuilder(prev => ({
      ...prev,
      [type]: prev[type].filter((_, i) => i !== index)
    }))
  }
  
  // Copy query
  const copyQuery = async () => {
    if (compiledQuery) {
      await navigator.clipboard.writeText(compiledQuery)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  
  // Clear all
  const clearAll = () => {
    setBuilder({ must: [], any: [], exclude: [] })
    setBasicText('')
  }
  
  // Check if builder has content
  const hasBuilderContent = builder.must.length > 0 || builder.any.length > 0 || builder.exclude.length > 0
  
  return (
    <div className="space-y-4">
      {/* Basic Search Bar */}
      <div className="relative">
        <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={basicText}
          onChange={(e) => setBasicText(e.target.value)}
          placeholder="ابحث عن أخبار..."
          className="input pr-10 w-full text-base"
          maxLength={200}
        />
      </div>
      
      {/* Advanced Builder Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className={`flex items-center gap-2 text-sm font-medium transition-colors ${
          showAdvanced || hasBuilderContent 
            ? 'text-emerald-600' 
            : 'text-gray-600 hover:text-gray-900'
        }`}
      >
        {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        <span>بناء استعلام متقدم</span>
        {hasBuilderContent && (
          <span className="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs rounded-full">
            {builder.must.length + builder.any.length + builder.exclude.length} كلمة
          </span>
        )}
      </button>
      
      {/* Advanced Builder Panel */}
      {showAdvanced && (
        <div className="space-y-5 p-4 bg-gray-50 rounded-xl border border-gray-200">
          {/* Must Include (AND) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <label className="text-sm font-semibold text-gray-800">
                يجب أن يحتوي على <span className="text-emerald-600 font-normal">(جميعها)</span>
              </label>
            </div>
            <p className="text-xs text-gray-500 mb-2">
              النتائج ستحتوي على كل هذه الكلمات معاً
            </p>
            <ChipInput
              value={mustInput}
              onChange={setMustInput}
              onAdd={() => addChip('must', mustInput, setMustInput)}
              placeholder="مثال: السعودية"
              color="emerald"
              chips={builder.must}
              onRemoveChip={(i) => removeChip('must', i)}
            />
          </div>
          
          {/* Any Of (OR) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <label className="text-sm font-semibold text-gray-800">
                أي من هذه <span className="text-blue-600 font-normal">(واحدة على الأقل)</span>
              </label>
            </div>
            <p className="text-xs text-gray-500 mb-2">
              النتائج ستحتوي على واحدة أو أكثر من هذه الكلمات
            </p>
            <ChipInput
              value={anyInput}
              onChange={setAnyInput}
              onAdd={() => addChip('any', anyInput, setAnyInput)}
              placeholder="مثال: الاقتصاد، النفط، الاستثمار"
              color="blue"
              chips={builder.any}
              onRemoveChip={(i) => removeChip('any', i)}
            />
          </div>
          
          {/* Exclude (NOT) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <label className="text-sm font-semibold text-gray-800">
                استبعاد <span className="text-red-600 font-normal">(لا تظهر)</span>
              </label>
            </div>
            <p className="text-xs text-gray-500 mb-2">
              النتائج لن تحتوي على أي من هذه الكلمات
            </p>
            <ChipInput
              value={excludeInput}
              onChange={setExcludeInput}
              onAdd={() => addChip('exclude', excludeInput, setExcludeInput)}
              placeholder="مثال: رياضة، ترفيه"
              color="red"
              chips={builder.exclude}
              onRemoveChip={(i) => removeChip('exclude', i)}
            />
          </div>
          
          {/* Clear Button */}
          {hasBuilderContent && (
            <button
              onClick={clearAll}
              className="text-sm text-gray-500 hover:text-red-600 transition-colors"
            >
              مسح الكل
            </button>
          )}
        </div>
      )}
      
      {/* Validation Error */}
      {!validation.valid && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 text-amber-800 text-sm rounded-lg border border-amber-200">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{validation.error}</span>
        </div>
      )}
      
      {/* Query Preview */}
      {compiledQuery && (
        <div className="p-3 bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-amber-500" />
              <span className="text-xs font-medium text-gray-600">معاينة البحث</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs ${isOverLimit ? 'text-red-600 font-medium' : 'text-gray-400'}`}>
                {queryLength}/{maxLength}
              </span>
              <button
                onClick={copyQuery}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                title="نسخ"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-600" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>
          <code className="block text-sm text-gray-700 break-all leading-relaxed" dir="auto">
            {compiledQuery}
          </code>
        </div>
      )}
      
      {/* Over Limit Warning */}
      {isOverLimit && (
        <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 text-sm rounded-lg border border-red-200">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>الاستعلام طويل جداً. قم بإزالة بعض الكلمات.</span>
        </div>
      )}
    </div>
  )
}
