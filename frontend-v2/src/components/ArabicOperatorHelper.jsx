import { useState, useEffect, useCallback } from 'react'
import { AlertCircle } from 'lucide-react'

/**
 * Smart Query Parser - parses query into terms respecting quotes and operators
 */
function parseQueryTerms(query) {
  const terms = []
  let current = ''
  let inQuotes = false
  
  for (let i = 0; i < query.length; i++) {
    const char = query[i]
    
    if (char === '"') {
      if (inQuotes) {
        // End of quoted phrase
        current += char
        terms.push(current)
        current = ''
        inQuotes = false
      } else {
        // Start of quoted phrase
        if (current.trim()) {
          terms.push(current.trim())
        }
        current = char
        inQuotes = true
      }
    } else if (char === ' ' && !inQuotes) {
      if (current.trim()) {
        terms.push(current.trim())
      }
      current = ''
    } else {
      current += char
    }
  }
  
  if (current.trim()) {
    terms.push(current.trim())
  }
  
  return terms.filter(t => t.length > 0)
}

/**
 * Check if a term is an operator
 */
function isOperator(term) {
  const upper = term.toUpperCase()
  return upper === 'AND' || upper === 'OR' || upper === 'NOT'
}

/**
 * Check if query contains any operators
 */
function hasOperators(query) {
  const upper = query.toUpperCase()
  return /\b(AND|OR|NOT)\b/.test(upper)
}

/**
 * Check if query ends with an operator
 */
function endsWithOperator(query) {
  const trimmed = query.trim().toUpperCase()
  return trimmed.endsWith(' AND') || trimmed.endsWith(' OR') || trimmed.endsWith(' NOT') ||
         trimmed === 'AND' || trimmed === 'OR' || trimmed === 'NOT'
}

/**
 * Get non-operator terms from parsed terms
 */
function getNonOperatorTerms(terms) {
  return terms.filter(t => !isOperator(t))
}

/**
 * Normalize query - uppercase operators, clean spacing
 */
function normalizeQuery(query) {
  let result = query
    .replace(/\s+/g, ' ')
    .trim()
  
  // Uppercase operators
  result = result.replace(/\band\b/gi, 'AND')
  result = result.replace(/\bor\b/gi, 'OR')
  result = result.replace(/\bnot\b/gi, 'NOT')
  
  return result
}

/**
 * Check if parentheses are balanced
 */
function areParenthesesBalanced(query) {
  let count = 0
  for (const char of query) {
    if (char === '(') count++
    if (char === ')') count--
    if (count < 0) return false
  }
  return count === 0
}

/**
 * Validate query and return error message in Arabic if invalid
 */
function validateQuery(query) {
  if (!query.trim()) {
    return null // Empty is valid (just not searchable)
  }
  
  const normalized = normalizeQuery(query)
  
  if (endsWithOperator(normalized)) {
    return 'لا يمكن إنهاء البحث بعامل منطقي (AND/OR/NOT)'
  }
  
  if (!areParenthesesBalanced(normalized)) {
    return 'الأقواس غير متوازنة'
  }
  
  // Check for consecutive operators
  if (/\b(AND|OR|NOT)\s+(AND|OR)\b/i.test(normalized)) {
    return 'لا يمكن وضع عاملين منطقيين متتاليين'
  }
  
  // Check for operator at start (except NOT)
  if (/^\s*(AND|OR)\b/i.test(normalized)) {
    return 'لا يمكن بدء البحث بـ AND أو OR'
  }
  
  return null
}

/**
 * Smart Join Algorithms
 */
const smartJoin = {
  /**
   * AND helper - joins terms with AND
   */
  and: (query, selectionStart, selectionEnd) => {
    const trimmed = query.trim()
    
    // If there's a selection, wrap it with AND logic
    if (selectionStart !== selectionEnd && selectionStart !== null) {
      const before = query.substring(0, selectionStart)
      const selected = query.substring(selectionStart, selectionEnd)
      const after = query.substring(selectionEnd)
      
      const selectedTerms = parseQueryTerms(selected)
      if (selectedTerms.length >= 2) {
        const nonOps = getNonOperatorTerms(selectedTerms)
        if (nonOps.length >= 2) {
          const joined = nonOps.join(' AND ')
          return { query: before + joined + after, error: null }
        }
      }
    }
    
    const terms = parseQueryTerms(trimmed)
    const nonOpTerms = getNonOperatorTerms(terms)
    
    if (nonOpTerms.length < 2) {
      return { query: trimmed, error: 'اكتب كلمتين على الأقل ثم اضغط "و"' }
    }
    
    if (endsWithOperator(trimmed)) {
      return { query: trimmed, error: 'لا يمكن إنهاء البحث بعامل منطقي' }
    }
    
    if (!hasOperators(trimmed)) {
      // No operators yet - join all terms with AND
      return { query: nonOpTerms.join(' AND '), error: null }
    }
    
    // Has operators - find last consecutive bare terms and join them
    const lastTerms = []
    for (let i = terms.length - 1; i >= 0; i--) {
      if (isOperator(terms[i])) break
      lastTerms.unshift(terms[i])
    }
    
    if (lastTerms.length >= 2) {
      const prefix = terms.slice(0, terms.length - lastTerms.length).join(' ')
      const joined = lastTerms.join(' AND ')
      return { query: (prefix ? prefix + ' ' : '') + joined, error: null }
    }
    
    return { query: trimmed, error: 'لا توجد كلمات متتالية لربطها بـ AND' }
  },
  
  /**
   * OR helper - joins terms with OR
   */
  or: (query, selectionStart, selectionEnd) => {
    const trimmed = query.trim()
    
    // If there's a selection
    if (selectionStart !== selectionEnd && selectionStart !== null) {
      const before = query.substring(0, selectionStart)
      const selected = query.substring(selectionStart, selectionEnd)
      const after = query.substring(selectionEnd)
      
      const selectedTerms = parseQueryTerms(selected)
      if (selectedTerms.length >= 2) {
        const nonOps = getNonOperatorTerms(selectedTerms)
        if (nonOps.length >= 2) {
          const joined = nonOps.length >= 3 
            ? `(${nonOps.join(' OR ')})` 
            : nonOps.join(' OR ')
          return { query: before + joined + after, error: null }
        }
      }
    }
    
    const terms = parseQueryTerms(trimmed)
    const nonOpTerms = getNonOperatorTerms(terms)
    
    if (nonOpTerms.length < 2) {
      return { query: trimmed, error: 'اكتب كلمتين على الأقل ثم اضغط "أو"' }
    }
    
    if (endsWithOperator(trimmed)) {
      return { query: trimmed, error: 'لا يمكن إنهاء البحث بعامل منطقي' }
    }
    
    if (!hasOperators(trimmed)) {
      // No operators yet - join all with OR
      const joined = nonOpTerms.length >= 3
        ? `(${nonOpTerms.join(' OR ')})`
        : nonOpTerms.join(' OR ')
      return { query: joined, error: null }
    }
    
    // Has operators - apply OR to last consecutive terms
    const lastTerms = []
    for (let i = terms.length - 1; i >= 0; i--) {
      if (isOperator(terms[i])) break
      lastTerms.unshift(terms[i])
    }
    
    if (lastTerms.length >= 2) {
      const prefix = terms.slice(0, terms.length - lastTerms.length).join(' ')
      const joined = lastTerms.length >= 3
        ? `(${lastTerms.join(' OR ')})`
        : lastTerms.join(' OR ')
      return { query: (prefix ? prefix + ' ' : '') + joined, error: null }
    }
    
    return { query: trimmed, error: 'لا توجد كلمات متتالية لربطها بـ OR' }
  },
  
  /**
   * NOT helper - excludes terms
   */
  not: (query, selectionStart, selectionEnd) => {
    const trimmed = query.trim()
    
    // If there's a selection, apply NOT to it
    if (selectionStart !== selectionEnd && selectionStart !== null) {
      const before = query.substring(0, selectionStart)
      const selected = query.substring(selectionStart, selectionEnd).trim()
      const after = query.substring(selectionEnd)
      
      if (selected) {
        const wrapped = selected.includes(' ') || hasOperators(selected)
          ? `NOT (${selected})`
          : `NOT ${selected}`
        return { query: before + wrapped + after, error: null }
      }
    }
    
    const terms = parseQueryTerms(trimmed)
    const nonOpTerms = getNonOperatorTerms(terms)
    
    if (nonOpTerms.length < 2) {
      return { query: trimmed, error: 'اكتب كلمتين على الأقل: الأولى للبحث والثانية للاستبعاد' }
    }
    
    if (endsWithOperator(trimmed)) {
      return { query: trimmed, error: 'لا يمكن إنهاء البحث بعامل منطقي' }
    }
    
    if (!hasOperators(trimmed)) {
      // No operators yet
      if (nonOpTerms.length === 2) {
        return { query: `${nonOpTerms[0]} NOT ${nonOpTerms[1]}`, error: null }
      }
      // More than 2 terms: AND the first ones, NOT the last
      const toSearch = nonOpTerms.slice(0, -1)
      const toExclude = nonOpTerms[nonOpTerms.length - 1]
      const searchPart = toSearch.length > 1 ? `(${toSearch.join(' AND ')})` : toSearch[0]
      return { query: `${searchPart} NOT ${toExclude}`, error: null }
    }
    
    // Has operators - apply NOT to last term
    const lastTerm = terms[terms.length - 1]
    if (!isOperator(lastTerm)) {
      const prefix = terms.slice(0, -1).join(' ')
      return { query: `${prefix} NOT ${lastTerm}`, error: null }
    }
    
    return { query: trimmed, error: 'لا يمكن تطبيق الاستثناء' }
  },
  
  /**
   * Parentheses helper - groups terms
   */
  group: (query, selectionStart, selectionEnd) => {
    const trimmed = query.trim()
    
    // If there's a selection, wrap it
    if (selectionStart !== selectionEnd && selectionStart !== null) {
      const before = query.substring(0, selectionStart)
      const selected = query.substring(selectionStart, selectionEnd).trim()
      const after = query.substring(selectionEnd)
      
      if (selected && !selected.startsWith('(')) {
        return { query: before + `(${selected})` + after, error: null }
      }
    }
    
    // Find OR group without parentheses and wrap it
    const orMatch = trimmed.match(/([^()]+\s+OR\s+[^()]+)(?!\))/)
    if (orMatch) {
      const wrapped = trimmed.replace(orMatch[1], `(${orMatch[1].trim()})`)
      return { query: wrapped, error: null }
    }
    
    return { query: trimmed, error: 'حدد نصاً لتجميعه أو أضف OR بدون أقواس' }
  },
  
  /**
   * Exact match helper - wraps in quotes
   */
  exact: (query, selectionStart, selectionEnd) => {
    const trimmed = query.trim()
    
    // If there's a selection, wrap it in quotes
    if (selectionStart !== selectionEnd && selectionStart !== null) {
      const before = query.substring(0, selectionStart)
      const selected = query.substring(selectionStart, selectionEnd).trim()
      const after = query.substring(selectionEnd)
      
      if (selected && !selected.startsWith('"')) {
        return { query: before + `"${selected}"` + after, error: null }
      }
    }
    
    // Check if last term has spaces (unlikely without quotes)
    const terms = parseQueryTerms(trimmed)
    if (terms.length > 0) {
      const lastTerm = terms[terms.length - 1]
      if (!lastTerm.startsWith('"') && terms.length >= 2) {
        // Wrap last two terms as exact phrase
        const prefix = terms.slice(0, -2).join(' ')
        const phrase = terms.slice(-2).join(' ')
        return { query: (prefix ? prefix + ' ' : '') + `"${phrase}"`, error: null }
      }
    }
    
    return { query: trimmed, error: 'حدد نصاً لتحويله إلى عبارة مطابقة' }
  }
}

/**
 * Arabic Operator Helper Component
 */
export default function ArabicOperatorHelper({ 
  query, 
  onQueryChange, 
  inputRef,
  className = '' 
}) {
  const [error, setError] = useState(null)
  const [showPreview, setShowPreview] = useState(false)
  
  const normalizedQuery = normalizeQuery(query)
  const validationError = validateQuery(normalizedQuery)
  
  // Helper chips configuration
  const helpers = [
    { 
      id: 'and', 
      label: 'و', 
      hint: 'للبحث عن كلمتين معًا داخل نفس الخبر',
      color: 'bg-blue-100 text-blue-700 hover:bg-blue-200 border-blue-300'
    },
    { 
      id: 'or', 
      label: 'أو', 
      hint: 'للبحث عن أي كلمة من الكلمات',
      color: 'bg-green-100 text-green-700 hover:bg-green-200 border-green-300'
    },
    { 
      id: 'not', 
      label: 'استثناء', 
      hint: 'لاستبعاد كلمة من النتائج',
      color: 'bg-red-100 text-red-700 hover:bg-red-200 border-red-300'
    },
    { 
      id: 'group', 
      label: 'تجميع ( )', 
      hint: 'لتجميع جزء من البحث',
      color: 'bg-purple-100 text-purple-700 hover:bg-purple-200 border-purple-300'
    },
    { 
      id: 'exact', 
      label: 'مطابقة تامة " "', 
      hint: 'للبحث عن عبارة مطابقة تمامًا',
      color: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 border-yellow-300'
    }
  ]
  
  const handleHelperClick = useCallback((helperId) => {
    // Get selection from input
    let selectionStart = null
    let selectionEnd = null
    
    if (inputRef?.current) {
      selectionStart = inputRef.current.selectionStart
      selectionEnd = inputRef.current.selectionEnd
    }
    
    // Apply smart join
    const joinFn = smartJoin[helperId]
    if (joinFn) {
      const result = joinFn(query, selectionStart, selectionEnd)
      
      if (result.error) {
        setError(result.error)
        setTimeout(() => setError(null), 3000)
      } else {
        setError(null)
        onQueryChange(normalizeQuery(result.query))
      }
    }
  }, [query, onQueryChange, inputRef])
  
  return (
    <div className={`space-y-2 ${className}`}>
      {/* Helper Chips Row */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500 ml-2">أدوات البحث:</span>
        {helpers.map(helper => (
          <button
            key={helper.id}
            onClick={() => handleHelperClick(helper.id)}
            title={helper.hint}
            className={`px-3 py-1 rounded-full text-sm font-medium border transition-colors ${helper.color}`}
          >
            {helper.label}
          </button>
        ))}
      </div>
      
      {/* Error Message */}
      {(error || validationError) && (
        <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error || validationError}</span>
        </div>
      )}
      
      {/* Live Preview */}
      {normalizedQuery && !validationError && (
        <div className="text-xs bg-gray-50 px-3 py-2 rounded border">
          <span className="text-gray-500">الصيغة النهائية للبحث: </span>
          <code className="text-gray-800 font-mono" dir="ltr">{normalizedQuery}</code>
        </div>
      )}
    </div>
  )
}

// Export validation function for use in parent
export { validateQuery, normalizeQuery }
