import { useState, useEffect, useCallback } from 'react'
import { X, Plus, Eye, Code, AlertCircle } from 'lucide-react'

/**
 * QueryBuilder - Build NewsData.io search queries with AND/OR/NOT operators
 * 
 * Props:
 * - onQueryChange: (query: string) => void - Called when query changes
 * - initialQuery: string - Initial raw query (for advanced mode)
 * - maxLength: number - Max query length (default 512)
 */
export default function QueryBuilder({ onQueryChange, initialQuery = '', maxLength = 512 }) {
  // Builder state
  const [mustInclude, setMustInclude] = useState([])
  const [anyOf, setAnyOf] = useState([])
  const [exactPhrase, setExactPhrase] = useState('')
  const [exclude, setExclude] = useState([])
  
  // Input states for adding chips
  const [mustIncludeInput, setMustIncludeInput] = useState('')
  const [anyOfInput, setAnyOfInput] = useState('')
  const [excludeInput, setExcludeInput] = useState('')
  
  // Mode toggle
  const [isAdvanced, setIsAdvanced] = useState(false)
  const [advancedQuery, setAdvancedQuery] = useState(initialQuery)
  
  // Build query string from structured inputs
  const buildQuery = useCallback(() => {
    if (isAdvanced) {
      // Normalize operators to uppercase in advanced mode
      let q = advancedQuery
      q = q.replace(/\s+and\s+/gi, ' AND ')
      q = q.replace(/\s+or\s+/gi, ' OR ')
      q = q.replace(/\s+not\s+/gi, ' NOT ')
      return q.trim()
    }
    
    const parts = []
    
    // Must include (AND-joined)
    if (mustInclude.length > 0) {
      parts.push(mustInclude.join(' AND '))
    }
    
    // Any of (OR-joined, parenthesized if multiple)
    if (anyOf.length > 0) {
      const orGroup = anyOf.length === 1 
        ? anyOf[0] 
        : `(${anyOf.join(' OR ')})`
      
      if (parts.length > 0) {
        parts.push(`AND ${orGroup}`)
      } else {
        parts.push(orGroup)
      }
    }
    
    // Exact phrase (quoted)
    if (exactPhrase.trim()) {
      const phrase = exactPhrase.trim().replace(/"/g, '')
      const quoted = `"${phrase}"`
      
      if (parts.length > 0) {
        parts.push(`AND ${quoted}`)
      } else {
        parts.push(quoted)
      }
    }
    
    // Exclude terms (NOT)
    if (exclude.length > 0) {
      const notPart = exclude.length === 1
        ? `NOT ${exclude[0]}`
        : `NOT (${exclude.join(' OR ')})`
      
      if (parts.length > 0) {
        parts.push(notPart)
      } else {
        parts.push(notPart)
      }
    }
    
    return parts.join(' ').trim()
  }, [isAdvanced, advancedQuery, mustInclude, anyOf, exactPhrase, exclude])
  
  // Update parent when query changes
  useEffect(() => {
    const query = buildQuery()
    onQueryChange?.(query)
  }, [buildQuery, onQueryChange])
  
  const query = buildQuery()
  const queryLength = query.length
  const isValid = queryLength <= maxLength && queryLength > 0
  
  // Chip handlers
  const addChip = (value, setter, inputSetter) => {
    const trimmed = value.trim()
    if (trimmed) {
      setter(prev => [...prev, trimmed])
      inputSetter('')
    }
  }
  
  const removeChip = (index, setter) => {
    setter(prev => prev.filter((_, i) => i !== index))
  }
  
  const handleKeyPress = (e, value, setter, inputSetter) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addChip(value, setter, inputSetter)
    }
  }
  
  // Chip component
  const Chip = ({ text, onRemove, color = 'blue' }) => {
    const colors = {
      blue: 'bg-blue-100 text-blue-800 border-blue-200',
      green: 'bg-green-100 text-green-800 border-green-200',
      purple: 'bg-purple-100 text-purple-800 border-purple-200',
      red: 'bg-red-100 text-red-800 border-red-200',
    }
    
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm border ${colors[color]}`}>
        {text}
        <button
          onClick={onRemove}
          className="hover:bg-black/10 rounded-full p-0.5"
        >
          <X className="w-3 h-3" />
        </button>
      </span>
    )
  }
  
  return (
    <div className="space-y-4">
      {/* Mode Toggle */}
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-700">منشئ الاستعلام</label>
        <button
          onClick={() => setIsAdvanced(!isAdvanced)}
          className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900"
        >
          {isAdvanced ? (
            <>
              <Eye className="w-4 h-4" />
              الوضع البسيط
            </>
          ) : (
            <>
              <Code className="w-4 h-4" />
              الوضع المتقدم
            </>
          )}
        </button>
      </div>
      
      {isAdvanced ? (
        /* Advanced Mode - Raw Query Input */
        <div className="space-y-2">
          <textarea
            value={advancedQuery}
            onChange={(e) => setAdvancedQuery(e.target.value)}
            placeholder="social AND pizza NOT pasta"
            className="input w-full h-24 font-mono text-sm"
            dir="ltr"
          />
          <p className="text-xs text-gray-500">
            استخدم AND و OR و NOT (بالأحرف الكبيرة) لبناء الاستعلام
          </p>
        </div>
      ) : (
        /* Simple Mode - Structured Inputs */
        <div className="space-y-4">
          {/* Must Include (AND) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              يجب أن يحتوي على (جميع الكلمات) <span className="text-blue-600">AND</span>
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {mustInclude.map((term, i) => (
                <Chip key={i} text={term} color="blue" onRemove={() => removeChip(i, setMustInclude)} />
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={mustIncludeInput}
                onChange={(e) => setMustIncludeInput(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, mustIncludeInput, setMustInclude, setMustIncludeInput)}
                placeholder="أضف كلمة..."
                className="input flex-1"
              />
              <button
                onClick={() => addChip(mustIncludeInput, setMustInclude, setMustIncludeInput)}
                className="btn-outline px-3"
                disabled={!mustIncludeInput.trim()}
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Any Of (OR) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              أي من الكلمات <span className="text-green-600">OR</span>
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {anyOf.map((term, i) => (
                <Chip key={i} text={term} color="green" onRemove={() => removeChip(i, setAnyOf)} />
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={anyOfInput}
                onChange={(e) => setAnyOfInput(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, anyOfInput, setAnyOf, setAnyOfInput)}
                placeholder="أضف كلمة..."
                className="input flex-1"
              />
              <button
                onClick={() => addChip(anyOfInput, setAnyOf, setAnyOfInput)}
                className="btn-outline px-3"
                disabled={!anyOfInput.trim()}
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Exact Phrase */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              عبارة محددة <span className="text-purple-600">"..."</span>
            </label>
            <input
              type="text"
              value={exactPhrase}
              onChange={(e) => setExactPhrase(e.target.value)}
              placeholder='مثال: "رئيس الوزراء"'
              className="input w-full"
            />
          </div>
          
          {/* Exclude (NOT) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              استبعاد <span className="text-red-600">NOT</span>
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {exclude.map((term, i) => (
                <Chip key={i} text={term} color="red" onRemove={() => removeChip(i, setExclude)} />
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={excludeInput}
                onChange={(e) => setExcludeInput(e.target.value)}
                onKeyPress={(e) => handleKeyPress(e, excludeInput, setExclude, setExcludeInput)}
                placeholder="أضف كلمة للاستبعاد..."
                className="input flex-1"
              />
              <button
                onClick={() => addChip(excludeInput, setExclude, setExcludeInput)}
                className="btn-outline px-3"
                disabled={!excludeInput.trim()}
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Query Preview */}
      <div className="p-3 bg-gray-50 rounded-lg border">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600">معاينة الاستعلام:</span>
          <span className={`text-xs ${queryLength > maxLength ? 'text-red-600' : 'text-gray-500'}`}>
            {queryLength}/{maxLength}
          </span>
        </div>
        <code className="block text-sm font-mono text-gray-800 break-all" dir="ltr">
          {query || <span className="text-gray-400">لم يتم إنشاء استعلام بعد</span>}
        </code>
      </div>
      
      {/* Validation Warning */}
      {queryLength > maxLength && (
        <div className="flex items-center gap-2 p-2 bg-red-50 text-red-700 text-sm rounded border border-red-200">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>الاستعلام طويل جداً ({queryLength} حرف). الحد الأقصى {maxLength} حرف.</span>
        </div>
      )}
    </div>
  )
}
