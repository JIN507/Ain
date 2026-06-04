import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Sparkles, Send, Square, Loader2, RefreshCw, Search, Newspaper,
  ChevronDown, ExternalLink, Flame, AlertCircle, Globe, Archive,
} from 'lucide-react'
import { apiFetch } from '../apiClient'

// ── Modes ─────────────────────────────────────────────────────────────────
// Two scopes: 'web' (live world news via API) and 'personal' (user's own corpus).
// Each mode has its own theme, sample questions, and behavioral hints.
const MODES = {
  web: {
    id: 'web',
    label: 'بحث واسع',
    description: 'يبحث في الأخبار الحيّة من الويب',
    icon: Globe,
    accent: '#0f766e',
    accentSoft: 'rgba(15,118,110,0.08)',
    accentBorder: 'rgba(20,184,166,0.32)',
    ring: 'rgba(20,184,166,0.45)',
    samples: [
      'ما الجديد عن الاقتصاد العالمي خلال 24 ساعة؟',
      'ما أبرز تطورات الشرق الأوسط الآن؟',
      'لخّص أخبار السياسة العالمية هذا الأسبوع.',
    ],
  },
  personal: {
    id: 'personal',
    label: 'من بياناتي',
    description: 'يبحث داخل أخبارك المجمّعة فقط',
    icon: Archive,
    accent: '#1e3a8a',
    accentSoft: 'rgba(30,58,138,0.08)',
    accentBorder: 'rgba(30,58,138,0.28)',
    ring: 'rgba(30,58,138,0.42)',
    samples: [
      'ما أهم 5 أخبار في نتائجي اليوم؟',
      'ما هي أبرز الأخبار عن المملكة العربية السعودية؟',
      'لخّص لي أعلى المصادر في نتائجي وموقفها العام.',
    ],
  },
}
const MODE_ORDER = ['web', 'personal']
const DEFAULT_MODE = 'web'
const MODE_STORAGE_KEY = 'ain_ai_mode'

const TOOL_LABEL = {
  fetch_live_news: 'يبحث في الأخبار الحيّة',
  search_my_articles: 'يبحث في بياناتك',
}

// ── Streaming SSE parser ───────────────────────────────────────────────────
async function* readSSE(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const line = chunk.split('\n').find(l => l.startsWith('data:'))
      if (!line) continue
      const data = line.slice(5).trim()
      if (!data) continue
      try { yield JSON.parse(data) } catch { /* ignore malformed */ }
    }
  }
}

// ── Render markdown-ish text + inline [n] citations ────────────────────────
function MessageContent({ text, citations, onCitationClick }) {
  const segments = useMemo(() => {
    if (!text) return []
    const parts = []
    const re = /\[(\d+)\]/g
    let last = 0, m
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parts.push({ kind: 'text', value: text.slice(last, m.index) })
      parts.push({ kind: 'cite', n: parseInt(m[1], 10) })
      last = m.index + m[0].length
    }
    if (last < text.length) parts.push({ kind: 'text', value: text.slice(last) })
    return parts
  }, [text])

  const citationMap = useMemo(() => {
    const map = {}
    ;(citations || []).forEach(c => { if (c?.n) map[c.n] = c })
    return map
  }, [citations])

  return (
    <span className="whitespace-pre-wrap break-words leading-relaxed">
      {segments.map((s, i) => {
        if (s.kind === 'text') return <span key={i}>{s.value}</span>
        const exists = !!citationMap[s.n]
        return (
          <button
            key={i}
            onClick={() => exists && onCitationClick?.(s.n)}
            disabled={!exists}
            className="inline-flex items-center justify-center align-super mx-0.5 text-[10px] font-bold rounded px-1 transition-colors"
            style={{
              minWidth: 18, height: 16, lineHeight: '14px',
              background: exists ? 'rgba(15,118,110,0.12)' : 'rgba(0,0,0,0.05)',
              color: exists ? '#0f766e' : '#94a3b8',
              cursor: exists ? 'pointer' : 'default',
            }}
            title={exists ? citationMap[s.n].title : ''}
          >
            {s.n}
          </button>
        )
      })}
    </span>
  )
}

// ── Single message bubble ──────────────────────────────────────────────────
function MessageBubble({ msg, isStreaming, onCitationClick }) {
  const [sourcesOpen, setSourcesOpen] = useState(true)

  if (msg.role === 'user') {
    const msgMode = msg.mode && MODES[msg.mode] ? MODES[msg.mode] : null
    const ModeIcon = msgMode?.icon
    // Bubble color follows the mode the question was asked in
    const bubbleGradient = msg.mode === 'personal'
      ? 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)'
      : 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)'
    const bubbleShadow = msg.mode === 'personal'
      ? '0 2px 10px rgba(30,58,138,0.22)'
      : '0 2px 10px rgba(15,118,110,0.2)'
    return (
      <div className="flex justify-start">
        <div
          className="max-w-[85%] rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm font-medium"
          style={{
            background: bubbleGradient,
            color: 'white',
            boxShadow: bubbleShadow,
          }}
        >
          {msgMode && (
            <div className="flex items-center gap-1 text-[10px] font-semibold opacity-80 mb-1.5">
              {ModeIcon && <ModeIcon className="w-3 h-3" />}
              <span>{msgMode.label}</span>
            </div>
          )}
          {msg.content}
        </div>
      </div>
    )
  }

  // Assistant
  const toolCalls = msg.toolCalls || []
  // Aggregate tool result counts to show as a tiny "استند إلى N خبراً" footer.
  // The mode is implicit from the user's pill choice — no need to label which tool ran.
  const totalToolCount = toolCalls.reduce((s, tc) => s + (tc.done ? (tc.count || 0) : 0), 0)
  const anyToolRunning = toolCalls.some(tc => !tc.done)
  const allToolsDone = toolCalls.length > 0 && toolCalls.every(tc => tc.done)

  return (
    <div className="flex flex-col items-end gap-2 w-full">
      {/* Main answer card */}
      <div
        className="max-w-[95%] w-full rounded-2xl rounded-tr-sm px-4 py-3 text-sm text-slate-800"
        style={{
          background: 'white',
          border: '1px solid rgba(0,0,0,0.06)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
        }}
      >
        {/* Silent activity indicator while a tool is running and no text has streamed yet */}
        {anyToolRunning && !msg.content && (
          <div className="inline-flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <span className="flex gap-0.5">
              <span className="w-1 h-1 rounded-full bg-slate-400 animate-pulse" style={{ animationDelay: '0ms' }} />
              <span className="w-1 h-1 rounded-full bg-slate-400 animate-pulse" style={{ animationDelay: '150ms' }} />
              <span className="w-1 h-1 rounded-full bg-slate-400 animate-pulse" style={{ animationDelay: '300ms' }} />
            </span>
            <span>يحلّل...</span>
          </div>
        )}

        {msg.content
          ? <MessageContent
              text={msg.content}
              citations={msg.citations}
              onCitationClick={onCitationClick}
            />
          : (isStreaming && !anyToolRunning)
            ? <span className="inline-flex items-center gap-2 text-slate-400 text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> يفكّر...
              </span>
            : (!anyToolRunning && <span className="text-slate-400 text-xs">لا توجد إجابة.</span>)
        }

        {/* Tiny footer: how many articles backed this answer */}
        {allToolsDone && totalToolCount > 0 && msg.content && (
          <div className="mt-2 text-[10px] text-slate-400">
            استند إلى {totalToolCount} خبراً
          </div>
        )}

        {/* Citations / sources block */}
        {msg.citations?.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-100">
            <button
              onClick={() => setSourcesOpen(o => !o)}
              className="w-full flex items-center justify-between text-xs font-bold text-slate-500 hover:text-slate-700 transition-colors"
            >
              <span className="flex items-center gap-1.5">
                <Newspaper className="w-3.5 h-3.5" />
                المصادر ({msg.citations.length})
              </span>
              <ChevronDown
                className="w-4 h-4 transition-transform"
                style={{ transform: sourcesOpen ? 'rotate(180deg)' : 'rotate(0)' }}
              />
            </button>
            <AnimatePresence initial={false}>
              {sourcesOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="pt-2 space-y-1.5">
                    {msg.citations.map(c => (
                      <a
                        key={c.n}
                        id={`cite-${c.n}`}
                        href={c.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start gap-2 p-2 rounded-lg hover:bg-slate-50 transition-colors group"
                      >
                        <span
                          className="flex-shrink-0 inline-flex items-center justify-center text-[10px] font-bold rounded px-1.5 mt-0.5"
                          style={{
                            minWidth: 22, height: 18,
                            background: 'rgba(15,118,110,0.12)', color: '#0f766e',
                          }}
                        >
                          {c.n}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-[12px] font-semibold text-slate-800 leading-snug truncate group-hover:text-teal-700">
                            {c.title || '(بدون عنوان)'}
                          </div>
                          <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                            {c.source && <span className="truncate max-w-[140px]">{c.source}</span>}
                            {c.country && <span className="uppercase">{c.country}</span>}
                            {c.published_at && (
                              <span dir="ltr">{c.published_at.slice(0, 10)}</span>
                            )}
                          </div>
                        </div>
                        <ExternalLink className="w-3.5 h-3.5 text-slate-300 flex-shrink-0 group-hover:text-teal-600" />
                      </a>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Discovery topic card ───────────────────────────────────────────────────
function TopicCard({ topic, onClick }) {
  return (
    <button
      onClick={() => onClick(topic)}
      className="text-right rounded-2xl p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md flex flex-col gap-2 min-w-[240px] flex-shrink-0"
      style={{
        background: 'linear-gradient(135deg, rgba(15,118,110,0.06) 0%, rgba(20,184,166,0.03) 100%)',
        border: '1px solid rgba(20,184,166,0.18)',
      }}
    >
      <div className="flex items-start gap-2">
        <Flame className="w-4 h-4 text-orange-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-slate-800 leading-snug line-clamp-2">
            {topic.title}
          </div>
          {topic.why_trending && (
            <div className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
              {topic.why_trending}
            </div>
          )}
        </div>
      </div>
      {topic.suggested_keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1">
          {topic.suggested_keywords.slice(0, 3).map((k, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
              style={{ background: 'rgba(15,118,110,0.1)', color: '#0f766e' }}
            >
              {k}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between mt-1 pt-2 border-t border-slate-200/60">
        <span className="text-[10px] text-slate-400">
          {topic.sample_articles?.length || 0} مصدر
        </span>
        <span className="text-[10px] font-bold text-teal-700">اسأل ←</span>
      </div>
    </button>
  )
}

// ── Personal-mode dashboard: "خلاصتك بالأرقام" ───────────────────────────
function MyStatsPanel({ stats, loading, error, onAsk, onRefresh, refreshing }) {
  const accent = MODES.personal.accent
  const accentSoft = MODES.personal.accentSoft
  const accentBorder = MODES.personal.accentBorder

  if (loading && !stats) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-[110px] rounded-2xl animate-pulse"
            style={{ background: 'rgba(0,0,0,0.04)' }} />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-rose-500 py-3">
        <AlertCircle className="w-4 h-4" />
        {error}
        <button
          onClick={onRefresh}
          className="text-xs px-2.5 py-1 rounded-full font-medium mr-2"
          style={{ background: accentSoft, color: accent, border: `1px solid ${accentBorder}` }}
        >
          إعادة المحاولة
        </button>
      </div>
    )
  }

  if (!stats || stats.total === 0) {
    return (
      <div className="flex flex-col items-start gap-2 py-3">
        <div className="text-xs text-slate-500">
          لم تجمع أي أخبار بعد في نظام عين. أضف كلمات مفتاحية من صفحة المراقبة لبدء استعراض نتائجك.
        </div>
      </div>
    )
  }

  const { total, count_24h, top_keywords, top_sources, sentiment } = stats
  const sentTotal = (sentiment?.['إيجابي'] || 0) + (sentiment?.['سلبي'] || 0) + (sentiment?.['محايد'] || 0)
  const pct = (n) => sentTotal > 0 ? Math.round((n / sentTotal) * 100) : 0

  const cardBase = {
    background: `linear-gradient(135deg, ${accentSoft} 0%, rgba(255,255,255,0.5) 100%)`,
    border: `1px solid ${accentBorder}`,
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* 1. Last 24h */}
      <button
        onClick={() => onAsk('ما الجديد في خلاصتي اليوم؟')}
        className="text-right rounded-2xl p-3 transition-all hover:-translate-y-0.5 hover:shadow-md flex flex-col justify-between min-h-[110px]"
        style={cardBase}
      >
        <div className="text-[11px] font-semibold" style={{ color: accent }}>آخر 24 ساعة</div>
        <div className="flex items-baseline gap-1">
          <div className="text-2xl font-bold text-slate-800">{count_24h}</div>
          <div className="text-[11px] text-slate-500">خبر جديد</div>
        </div>
        <div className="text-[10px] text-slate-400">من أصل {total} خبر في خلاصتك</div>
      </button>

      {/* 2. Top keywords */}
      <button
        onClick={() => {
          const top = top_keywords?.[0]?.keyword
          onAsk(top
            ? `حلّل أبرز الأخبار حول كلمة "${top}" في خلاصتي`
            : 'ما أكثر الكلمات المفتاحية تكراراً في خلاصتي؟')
        }}
        className="text-right rounded-2xl p-3 transition-all hover:-translate-y-0.5 hover:shadow-md flex flex-col gap-1.5 min-h-[110px]"
        style={cardBase}
      >
        <div className="text-[11px] font-semibold" style={{ color: accent }}>أكثر الكلمات تكراراً</div>
        <div className="flex flex-wrap gap-1">
          {(top_keywords || []).slice(0, 4).map((k, i) => (
            <span
              key={i}
              className="text-[10px] px-1.5 py-0.5 rounded font-semibold inline-flex items-center gap-1"
              style={{ background: 'white', color: accent, border: `1px solid ${accentBorder}` }}
            >
              <span className="line-clamp-1 max-w-[80px]">{k.keyword}</span>
              <span className="opacity-60">{k.count}</span>
            </span>
          ))}
          {(!top_keywords || top_keywords.length === 0) && (
            <span className="text-[10px] text-slate-400">لا توجد بيانات</span>
          )}
        </div>
      </button>

      {/* 3. Sentiment breakdown */}
      <button
        onClick={() => onAsk('ركّز على الأخبار السلبية في خلاصتي وحلّلها.')}
        className="text-right rounded-2xl p-3 transition-all hover:-translate-y-0.5 hover:shadow-md flex flex-col gap-2 min-h-[110px]"
        style={cardBase}
      >
        <div className="text-[11px] font-semibold" style={{ color: accent }}>توزيع المشاعر</div>
        {sentTotal > 0 ? (
          <>
            <div className="flex h-2 w-full rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
              <div style={{ width: `${pct(sentiment['إيجابي'])}%`, background: '#10b981' }} />
              <div style={{ width: `${pct(sentiment['محايد'])}%`, background: '#94a3b8' }} />
              <div style={{ width: `${pct(sentiment['سلبي'])}%`, background: '#f43f5e' }} />
            </div>
            <div className="flex justify-between text-[10px] font-semibold">
              <span style={{ color: '#10b981' }}>إيجابي {pct(sentiment['إيجابي'])}%</span>
              <span style={{ color: '#94a3b8' }}>محايد {pct(sentiment['محايد'])}%</span>
              <span style={{ color: '#f43f5e' }}>سلبي {pct(sentiment['سلبي'])}%</span>
            </div>
          </>
        ) : (
          <span className="text-[10px] text-slate-400">لا توجد بيانات</span>
        )}
      </button>

      {/* 4. Top sources */}
      <button
        onClick={() => {
          const top = top_sources?.[0]?.source
          onAsk(top
            ? `لخّص أحدث ما نشره مصدر "${top}" في خلاصتي`
            : 'ما أعلى المصادر ظهوراً في خلاصتي؟')
        }}
        className="text-right rounded-2xl p-3 transition-all hover:-translate-y-0.5 hover:shadow-md flex flex-col gap-1.5 min-h-[110px]"
        style={cardBase}
      >
        <div className="text-[11px] font-semibold" style={{ color: accent }}>أعلى المصادر</div>
        <div className="flex flex-col gap-0.5">
          {(top_sources || []).slice(0, 3).map((s, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-[11px]">
              <span className="text-slate-700 truncate flex-1">{s.source}</span>
              <span className="text-slate-400">{s.count}</span>
            </div>
          ))}
          {(!top_sources || top_sources.length === 0) && (
            <span className="text-[10px] text-slate-400">لا توجد بيانات</span>
          )}
        </div>
      </button>
    </div>
  )
}


// ── Main page ──────────────────────────────────────────────────────────────
export default function AinAI() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const [topics, setTopics] = useState([])
  const [topicsLoading, setTopicsLoading] = useState(true)
  const [topicsError, setTopicsError] = useState(null)
  const [topicsMeta, setTopicsMeta] = useState(null)

  // Personal-mode dashboard ("خلاصتك بالأرقام")
  const [myStats, setMyStats] = useState(null)
  const [myStatsLoading, setMyStatsLoading] = useState(false)
  const [myStatsError, setMyStatsError] = useState(null)

  // Active mode: 'web' (default for new visits) or 'personal'.
  // Persisted in localStorage so users return to their last-used mode.
  const [mode, setMode] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_MODE
    try {
      const stored = window.localStorage.getItem(MODE_STORAGE_KEY)
      return stored && MODES[stored] ? stored : DEFAULT_MODE
    } catch {
      return DEFAULT_MODE
    }
  })
  const activeMode = MODES[mode] || MODES[DEFAULT_MODE]

  // Persist mode changes
  useEffect(() => {
    try { window.localStorage.setItem(MODE_STORAGE_KEY, mode) } catch {}
  }, [mode])

  const abortRef = useRef(null)
  const scrollRef = useRef(null)
  const textareaRef = useRef(null)

  // Load discovery on mount
  const loadDiscovery = useCallback(async (force = false) => {
    setTopicsLoading(true)
    setTopicsError(null)
    try {
      const url = `/api/ain-ai/discover?language=ar${force ? '&force=1' : ''}`
      const res = await apiFetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTopics(data.topics || [])
      setTopicsMeta({
        generated_at_iso: data.generated_at_iso,
        source_article_count: data.source_article_count,
        fetch_error: data.fetch_error,
        cluster_error: data.cluster_error,
      })
    } catch (e) {
      console.error('[AinAI] discover error:', e)
      setTopicsError('تعذّر جلب المواضيع الساخنة.')
    } finally {
      setTopicsLoading(false)
    }
  }, [])

  useEffect(() => { loadDiscovery() }, [loadDiscovery])

  // Load personal-mode stats — fired the first time user enters personal mode,
  // and refetched on demand. Cheap (pure SQL aggregation).
  const loadMyStats = useCallback(async () => {
    setMyStatsLoading(true)
    setMyStatsError(null)
    try {
      const res = await apiFetch('/api/ain-ai/my-stats')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMyStats(data)
    } catch (e) {
      console.error('[AinAI] my-stats error:', e)
      setMyStatsError('تعذّر جلب إحصائيات بياناتك.')
    } finally {
      setMyStatsLoading(false)
    }
  }, [])

  // Lazy-load stats when first switching to personal mode
  useEffect(() => {
    if (mode === 'personal' && !myStats && !myStatsLoading) {
      loadMyStats()
    }
  }, [mode, myStats, myStatsLoading, loadMyStats])

  // Auto-scroll on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, streaming])

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 180) + 'px'
  }, [input])

  // Citation click: scroll to source
  const handleCitationClick = useCallback((n) => {
    const el = document.getElementById(`cite-${n}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.style.transition = 'background 0.4s'
      el.style.background = 'rgba(20,184,166,0.15)'
      setTimeout(() => { el.style.background = '' }, 1200)
    }
  }, [])

  // Send a message
  const send = useCallback(async (overrideText) => {
    const text = (overrideText ?? input).trim()
    if (!text || streaming) return

    // Snapshot the active mode at send-time so it's locked to this turn
    // even if the user toggles the pill while the stream is running.
    const sendMode = mode
    const userMsg = { role: 'user', content: text, mode: sendMode }
    const placeholder = {
      role: 'assistant', content: '', toolCalls: [], citations: [], mode: sendMode,
    }

    // Build the full history we'll send (omit per-message metadata)
    const historyForApi = [...messages.map(m => ({ role: m.role, content: m.content })), { role: 'user', content: text }]

    setMessages(prev => [...prev, userMsg, placeholder])
    setInput('')
    setError(null)
    setStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await apiFetch('/api/ain-ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: historyForApi, mode: sendMode }),
        signal: controller.signal,
      })

      if (!res.ok) {
        const errBody = await res.text().catch(() => '')
        throw new Error(`HTTP ${res.status}: ${errBody.slice(0, 200)}`)
      }

      // Drain SSE stream
      for await (const evt of readSSE(res)) {
        // Pure-functional updater — NEVER mutate prev.
        // React 18 StrictMode runs updaters twice; mutation causes double-apply.
        setMessages(prev => {
          if (prev.length === 0) return prev
          const lastIdx = prev.length - 1
          const last = prev[lastIdx]
          if (last.role !== 'assistant') return prev

          let updated
          if (evt.type === 'delta') {
            updated = { ...last, content: (last.content || '') + (evt.text || '') }
          } else if (evt.type === 'tool_call') {
            updated = {
              ...last,
              toolCalls: [
                ...(last.toolCalls || []),
                { name: evt.name, args: evt.args, done: false, count: 0 },
              ],
            }
          } else if (evt.type === 'tool_result') {
            const tcs = [...(last.toolCalls || [])]
            // Mark the most recent matching, not-yet-done tool call
            let patched = false
            for (let i = tcs.length - 1; i >= 0; i--) {
              if (tcs[i].name === evt.name && !tcs[i].done) {
                tcs[i] = { ...tcs[i], done: true, count: evt.count || 0, total: evt.total || 0 }
                patched = true
                break
              }
            }
            if (!patched) return prev
            updated = { ...last, toolCalls: tcs }
          } else if (evt.type === 'citations') {
            updated = { ...last, citations: evt.articles || [] }
          } else if (evt.type === 'error') {
            const sep = last.content ? '\n\n' : ''
            updated = { ...last, content: (last.content || '') + sep + `⚠ ${evt.message}` }
          } else {
            return prev
          }
          return [...prev.slice(0, lastIdx), updated]
        })
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        setMessages(prev => {
          if (prev.length === 0) return prev
          const lastIdx = prev.length - 1
          const last = prev[lastIdx]
          if (last.role !== 'assistant' || last.content) return prev
          return [...prev.slice(0, lastIdx), { ...last, content: '⏹ تم الإيقاف.' }]
        })
      } else {
        console.error('[AinAI] send error:', e)
        setError('تعذّر إكمال الطلب. حاول مرة أخرى.')
        setMessages(prev => {
          if (prev.length === 0) return prev
          const lastIdx = prev.length - 1
          const last = prev[lastIdx]
          if (last.role !== 'assistant') return prev
          const sep = last.content ? '\n\n' : ''
          return [...prev.slice(0, lastIdx), { ...last, content: (last.content || '') + sep + '⚠ حدث خطأ في الاتصال.' }]
        })
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }, [input, messages, streaming, mode])

  const stop = useCallback(() => {
    if (abortRef.current) abortRef.current.abort()
  }, [])

  const onTopicClick = useCallback((topic) => {
    const q = `أعطني تفاصيل ومصادر حول: ${topic.title}`
    setInput(q)
    if (textareaRef.current) textareaRef.current.focus()
  }, [])

  // Inject a pre-built question from the personal stats dashboard
  const onStatsAsk = useCallback((question) => {
    setInput(question)
    if (textareaRef.current) textareaRef.current.focus()
  }, [])

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div dir="rtl" className="flex flex-col gap-4 max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
              boxShadow: '0 4px 14px rgba(20,184,166,0.3)',
            }}
          >
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 leading-tight">عين AI</h1>
          </div>
        </div>
        <button
          onClick={() => mode === 'personal' ? loadMyStats() : loadDiscovery(true)}
          disabled={mode === 'personal' ? myStatsLoading : topicsLoading}
          className="text-xs px-3 py-1.5 rounded-full font-medium transition-all flex items-center gap-1.5 disabled:opacity-60"
          style={{
            background: activeMode.accentSoft,
            color: activeMode.accent,
            border: `1px solid ${activeMode.accentBorder}`,
          }}
        >
          <RefreshCw className={`w-3.5 h-3.5 ${(mode === 'personal' ? myStatsLoading : topicsLoading) ? 'animate-spin' : ''}`} />
          {(mode === 'personal' ? myStatsLoading : topicsLoading) ? 'جارٍ التحديث...' : 'تحديث'}
        </button>
      </div>

      {/* Mode-aware top panel: web → live trending; personal → "خلاصتك بالأرقام" */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-sm font-bold text-slate-800">
            {mode === 'personal' ? 'خلاصتك بالأرقام' : 'الأخبار الرائجة'}
          </h2>
          {mode === 'web' && topicsMeta?.generated_at_iso && (
            <span className="text-[10px] text-slate-400 mr-auto" dir="ltr">
              {topicsMeta.generated_at_iso.slice(0, 16).replace('T', ' ')} UTC
            </span>
          )}
        </div>
        {mode === 'personal' ? (
          <MyStatsPanel
            stats={myStats}
            loading={myStatsLoading}
            error={myStatsError}
            onAsk={onStatsAsk}
            onRefresh={loadMyStats}
            refreshing={myStatsLoading}
          />
        ) : topicsLoading ? (
          <div className="flex gap-3 overflow-x-auto pb-1">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="min-w-[240px] h-[120px] rounded-2xl animate-pulse"
                style={{ background: 'rgba(0,0,0,0.04)' }} />
            ))}
          </div>
        ) : topicsError ? (
          <div className="flex items-center gap-2 text-xs text-rose-500 py-3">
            <AlertCircle className="w-4 h-4" />
            {topicsError}
          </div>
        ) : topics.length === 0 ? (
          <div className="flex flex-col items-start gap-2 py-3">
            <div className="text-xs text-slate-500">
              لا توجد مواضيع متاحة حالياً.
              {topicsMeta?.cluster_error && (
                <span className="text-rose-400 mr-2">
                  (خطأ تحليل: {topicsMeta.cluster_error.slice(0, 80)})
                </span>
              )}
              {topicsMeta?.fetch_error && (
                <span className="text-rose-400 mr-2">
                  (خطأ جلب: {topicsMeta.fetch_error.slice(0, 80)})
                </span>
              )}
              {!topicsMeta?.cluster_error && !topicsMeta?.fetch_error &&
                topicsMeta?.source_article_count === 0 && (
                  <span className="text-slate-400 mr-2">(لم تُجلب أي مقالات)</span>
                )}
            </div>
            <button
              onClick={() => loadDiscovery(true)}
              className="text-xs px-3 py-1.5 rounded-full font-medium transition-all flex items-center gap-1.5"
              style={{
                background: 'rgba(15,118,110,0.06)',
                color: '#0f766e',
                border: '1px solid rgba(20,184,166,0.18)',
              }}
            >
              <RefreshCw className="w-3.5 h-3.5" />
              إعادة المحاولة
            </button>
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1 scroll-smooth">
            {topics.map((t, i) => (
              <TopicCard key={i} topic={t} onClick={onTopicClick} />
            ))}
          </div>
        )}
      </div>

      {/* Chat area */}
      <div
        className="card flex flex-col overflow-hidden"
        style={{ minHeight: '75vh' }}
      >
        {/* Messages */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
          style={{ scrollBehavior: 'smooth' }}
        >
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center py-10 px-4">
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
                style={{
                  background: `linear-gradient(135deg, ${activeMode.accentSoft} 0%, rgba(255,255,255,0.5) 100%)`,
                  border: `1px solid ${activeMode.accentBorder}`,
                }}
              >
                {(() => {
                  const Icon = activeMode.icon
                  return <Icon className="w-7 h-7" style={{ color: activeMode.accent }} />
                })()}
              </div>
              <h3 className="text-base font-bold text-slate-800 mb-1">
                {mode === 'personal' ? 'تحليل أرشيفك الشخصي' : 'تحليل الأخبار العالمية'}
              </h3>
              <p className="text-xs text-slate-500 max-w-md leading-relaxed mb-5">
                {mode === 'personal'
                  ? 'وكيل تحليل يبحث داخل الأخبار التي جمعتها في نظام عين ويستخرج الأنماط والاتجاهات.'
                  : 'وكيل تحليل يبحث في الأخبار الحيّة من الويب ويحلّل النتائج بأسلوب رصين مع الإشارة إلى المصادر.'}
              </p>
              <div className="flex flex-col gap-2 w-full max-w-sm">
                {activeMode.samples.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => send(q)}
                    className="text-right text-xs px-4 py-2.5 rounded-xl transition-all hover:shadow-sm"
                    style={{
                      background: 'white',
                      border: `1px solid ${activeMode.accentBorder}`,
                      color: '#334155',
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <MessageBubble
                key={i}
                msg={m}
                isStreaming={streaming && i === messages.length - 1 && m.role === 'assistant'}
                onCitationClick={handleCitationClick}
              />
            ))
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-slate-100 p-3">
          {error && (
            <div className="mb-2 text-xs text-rose-500 flex items-center gap-1.5 px-2">
              <AlertCircle className="w-3.5 h-3.5" />
              {error}
            </div>
          )}

          {/* Mode pills — explicit scope selector */}
          <div className="flex items-center gap-1.5 mb-2 px-1">
            {MODE_ORDER.map(mid => {
              const m = MODES[mid]
              const Icon = m.icon
              const active = mid === mode
              return (
                <button
                  key={mid}
                  type="button"
                  onClick={() => setMode(mid)}
                  title={m.description}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold transition-all active:scale-95"
                  style={{
                    background: active ? m.accent : 'white',
                    color: active ? 'white' : m.accent,
                    border: `1px solid ${active ? m.accent : m.accentBorder}`,
                    boxShadow: active ? `0 2px 8px ${m.accentSoft}` : 'none',
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{m.label}</span>
                </button>
              )
            })}
            <span className="text-[10px] text-slate-400 mr-auto pl-1 truncate">
              {activeMode.description}
            </span>
          </div>

          <div
            className="flex items-end gap-2 rounded-2xl px-3 py-2 transition-all"
            style={{
              background: 'rgba(248,250,252,0.7)',
              border: `1px solid ${activeMode.accentBorder}`,
              boxShadow: `0 0 0 3px ${activeMode.accentSoft}`,
            }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="اكتب سؤالك ..."
              rows={1}
              disabled={streaming}
              className="flex-1 bg-transparent outline-none resize-none text-sm text-slate-800 placeholder:text-slate-400 disabled:opacity-50"
              style={{ maxHeight: 220, minHeight: 24 }}
            />
            {streaming ? (
              <button
                onClick={stop}
                className="flex items-center justify-center w-9 h-9 rounded-xl transition-all hover:bg-rose-50 active:scale-95"
                style={{ background: 'rgba(244,63,94,0.08)', color: '#e11d48' }}
                title="إيقاف"
              >
                <Square className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => send()}
                disabled={!input.trim()}
                className="flex items-center justify-center w-9 h-9 rounded-xl transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                style={{
                  background: mode === 'personal'
                    ? 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)'
                    : 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
                  color: 'white',
                  boxShadow: mode === 'personal'
                    ? '0 2px 10px rgba(30,58,138,0.28)'
                    : '0 2px 10px rgba(15,118,110,0.25)',
                }}
                title="إرسال"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
