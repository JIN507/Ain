import { useState } from 'react'
import { motion } from 'framer-motion'
import { ExternalLink, ThumbsUp, ThumbsDown, Minus, ChevronDown, ChevronUp, Bookmark, Loader2 } from 'lucide-react'

export default function ArticleCard({ article, isBookmarked, onBookmark, onUnbookmark, bookmarkLoading }) {
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
            className="font-bold px-1 rounded"
            style={{ backgroundColor: 'rgba(20,184,166,0.12)', color: '#0f766e' }}
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
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="card h-full flex flex-col overflow-hidden group"
    >
      {/* Article Image */}
      {article.image_url && (
        <div className="w-full h-44 overflow-hidden bg-slate-50">
          <img 
            src={article.image_url} 
            alt={article.title_ar}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={(e) => { e.target.style.display = 'none' }}
          />
        </div>
      )}
      
      <div className="p-5 flex flex-col h-full">
        {/* Header Badges */}
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
          <span className="badge" style={{ background: 'rgba(15,118,110,0.08)', color: '#0f766e' }}>
            {article.country}
          </span>
          <span className="badge" style={{ background: 'rgba(0,0,0,0.04)', color: '#64748b' }}>
            {article.source_name}
          </span>
          {article.keyword_original && (
            <span className="badge" style={{ background: 'rgba(79,70,229,0.08)', color: '#4f46e5' }}>
              {article.keyword_original}
            </span>
          )}
        </div>

        {/* Title */}
        <h3 className="text-base font-bold text-slate-900 mb-3 leading-relaxed line-clamp-2">
          {article.title_ar}
        </h3>

        {/* Match Context or Summary with expand/collapse */}
        <div className="mb-4 flex-grow">
          {/* Show match context indicator if available */}
          {hasMatchContext && (
            <div className="mb-2 text-[11px] font-semibold flex items-center gap-1" style={{ color: '#0f766e' }}>
              <span className="w-1 h-1 rounded-full bg-teal-500"></span>
              سياق المطابقة
            </div>
          )}
          
          <div 
            className={`text-sm text-slate-600 leading-relaxed overflow-hidden transition-all duration-300 ease-in-out ${
              isExpanded ? 'max-h-[1000px]' : 'max-h-[100px]'
            }`}
            style={{
              display: '-webkit-box',
              WebkitLineClamp: isExpanded ? 'unset' : 4,
              WebkitBoxOrient: 'vertical',
              overflow: isExpanded ? 'visible' : 'hidden'
            }}
          >
            {renderHighlightedText(displayText)}
          </div>
          
          {/* Show gradient fade when collapsed and text is long */}
          {!isExpanded && shouldShowExpandButton && (
            <div className="h-6 -mt-6 relative" style={{ background: 'linear-gradient(to top, rgba(255,255,255,0.95), transparent)' }} />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 mt-auto" style={{ borderTop: '1px solid rgba(0,0,0,0.05)' }}>
          <div className="flex items-center gap-2">
            <span className={`badge ${config.class} flex items-center gap-1`}>
              <SentimentIcon className="w-3 h-3" />
              {article.sentiment}
            </span>
            <span className="text-[11px] text-slate-400">
              {article.published_at ? new Date(article.published_at).toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' }) : ''}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Bookmark button */}
            {onBookmark && (
              <button
                onClick={() => isBookmarked ? onUnbookmark?.(article) : onBookmark?.(article)}
                disabled={bookmarkLoading}
                className="btn-ghost !px-2 !py-1 !text-xs"
                style={{ color: isBookmarked ? '#f59e0b' : '#94a3b8' }}
                title={isBookmarked ? 'إزالة من المفضلة' : 'حفظ في المفضلة'}
              >
                {bookmarkLoading
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <Bookmark className="w-3.5 h-3.5" fill={isBookmarked ? '#f59e0b' : 'none'} />
                }
              </button>
            )}

            {/* Expand/Collapse button - only show if text is long */}
            {shouldShowExpandButton && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="btn-ghost !px-2 !py-1 !text-xs !gap-0.5"
                style={{ color: '#0f766e' }}
              >
                {isExpanded ? (
                  <>اخفِ <ChevronUp className="w-3.5 h-3.5" /></>
                ) : (
                  <>المزيد <ChevronDown className="w-3.5 h-3.5" /></>
                )}
              </button>
            )}
            
            {/* Original article link */}
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost !px-2 !py-1 !text-xs !gap-1"
              style={{ color: '#0f766e' }}
            >
              المصدر
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
