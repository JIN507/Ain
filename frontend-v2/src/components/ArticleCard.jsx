import { useState } from 'react'
import { motion } from 'framer-motion'
import { ExternalLink, ThumbsUp, ThumbsDown, Minus, ChevronDown, ChevronUp } from 'lucide-react'

export default function ArticleCard({ article }) {
  const [isExpanded, setIsExpanded] = useState(false)
  
  const sentimentConfig = {
    'إيجابي': { class: 'badge-positive', icon: ThumbsUp },
    'سلبي': { class: 'badge-negative', icon: ThumbsDown },
    'محايد': { class: 'badge-neutral', icon: Minus }
  }

  const config = sentimentConfig[article.sentiment] || sentimentConfig['محايد']
  const SentimentIcon = config.icon
  
  // Use match context if available, otherwise use full summary
  const hasMatchContext = article.match_context && article.match_context.full_snippet_ar
  const displayText = hasMatchContext 
    ? article.match_context.full_snippet_ar 
    : (article.summary_ar || '')
  
  // Check if text is long enough to show expand button
  const shouldShowExpandButton = displayText.length > 200
  
  // Helper function to render text with highlighted keywords
  const renderHighlightedText = (text) => {
    if (!text) return null
    
    // Split by **keyword** markers (bold markers from backend)
    const parts = text.split(/(\*\*[^*]+\*\*)/)
    
    return parts.map((part, index) => {
      // Check if this part is a keyword (wrapped in **)
      if (part.startsWith('**') && part.endsWith('**')) {
        const keyword = part.slice(2, -2) // Remove ** from both sides
        return (
          <span 
            key={index} 
            className="bg-yellow-200 font-bold px-1 rounded"
            style={{ backgroundColor: '#fef08a' }}
          >
            {keyword}
          </span>
        )
      }
      return <span key={index}>{part}</span>
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ scale: 1.02 }}
      className="card hover:shadow-xl transition-all duration-300 h-full flex flex-col overflow-hidden"
    >
      {/* Article Image */}
      {article.image_url && (
        <div className="w-full h-48 overflow-hidden bg-gray-100">
          <img 
            src={article.image_url} 
            alt={article.title_ar}
            className="w-full h-full object-cover"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
      )}
      
      <div className="p-5 flex flex-col h-full">
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
        {article.keyword_original && (
          <div className="mb-3">
            <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 px-3 py-1 rounded-full text-sm font-semibold">
              🔑 {article.keyword_original}
            </span>
          </div>
        )}

        {/* Title */}
        <h3 className="text-xl font-bold text-gray-900 mb-3 leading-relaxed">
          {article.title_ar}
        </h3>

        {/* Match Context or Summary with expand/collapse */}
        <div className="mb-4 flex-grow">
          {/* Show match context indicator if available */}
          {hasMatchContext && (
            <div className="mb-2 text-xs text-emerald-600 font-semibold flex items-center gap-1">
              <span>🎯</span>
              <span>سياق المطابقة:</span>
            </div>
          )}
          
          <div 
            className={`text-gray-700 leading-relaxed overflow-hidden transition-all duration-300 ease-in-out ${
              isExpanded ? 'max-h-[1000px]' : 'max-h-[120px]'
            }`}
            style={{
              display: '-webkit-box',
              WebkitLineClamp: isExpanded ? 'unset' : 5,
              WebkitBoxOrient: 'vertical',
              overflow: isExpanded ? 'visible' : 'hidden'
            }}
          >
            {renderHighlightedText(displayText)}
          </div>
          
          {/* Show gradient fade when collapsed and text is long */}
          {!isExpanded && shouldShowExpandButton && (
            <div className="h-8 bg-gradient-to-t from-white to-transparent -mt-8 relative" />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-emerald-100 mt-auto">
          <div className="flex items-center gap-2">
            <span className={`badge ${config.class} flex items-center gap-1`}>
              <SentimentIcon className="w-3 h-3" />
              {article.sentiment}
            </span>
          </div>

          <div className="flex flex-col items-end gap-2">
            {/* Buttons row */}
            <div className="flex items-center gap-2">
              {/* Expand/Collapse button - only show if text is long */}
              {shouldShowExpandButton && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-emerald-600 hover:text-emerald-800 font-semibold text-sm flex items-center gap-1 transition"
                >
                  {isExpanded ? (
                    <>
                      اخفِ النص
                      <ChevronUp className="w-4 h-4" />
                    </>
                  ) : (
                    <>
                      اظهر المزيد
                      <ChevronDown className="w-4 h-4" />
                    </>
                  )}
                </button>
              )}
              
              {/* Original article link */}
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-600 hover:text-emerald-800 font-semibold text-sm flex items-center gap-1 transition"
              >
                المقال الأصلي
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
            
            {/* Date */}
            <span className="text-xs text-gray-500">
              {article.published_at ? new Date(article.published_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }) : 'غير محدد'}
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
