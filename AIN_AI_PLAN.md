# عين AI — Build Plan & Agreements

**Status:** Ship 1 in progress
**Owner:** decisions locked by user; implementation by Cascade
**Goal:** production-level feature, deployable to Render alongside existing app
**Last updated:** Ship 1 kickoff

---

## 1. Vision

A new tab in Ain News Monitor — **عين AI** — that combines two complementary AI experiences in one place:

- **Inward / corpus chat** (deferred to v2) — ask questions about the user's own gathered articles
- **Outward / live news agent** (Ship 1) — chat with an analytical agent that fetches fresh news from NewsData.io on demand
- **Discovery panel** (Ship 1) — auto-curated trending topics row above the chat, refreshed every 4h

User's framing: *"focus on openai and newsdata now, nothing about the user's data — quality and speed first."*

---

## 2. Naming, persona, scope

| Field | Value |
|---|---|
| **Name** | عين AI |
| **Tab label** | "عين AI" with `Sparkles` icon |
| **Persona** | Pure analyst — cold, numerical, citation-disciplined, news-wire tone |
| **Style rules** | Short sentences, zero filler, percentages and counts, `[n]` citations, no narrative interpretation |
| **Language** | Replies in same language as user's question (Arabic by default) |
| **Out-of-scope responses** | Politely refuses non-news questions |
| **Data sources (Ship 1)** | OpenAI (model decisions, summarization) + NewsData.io (only fact source) |
| **Data sources (later)** | + user's matched articles corpus (search, sentiment breakdown, profile) |

### System prompt (locked)

```
أنت "عين AI"، محلل بيانات إعلامية. مصدر بياناتك الوحيد هو أداة fetch_live_news.

# قواعد صارمة
- استدعِ الأداة قبل أي ادعاء. لا تخمّن أبداً.
- ركّز على الأرقام والنسب: "12 خبر من 5 مصادر، 60% منها إيجابي".
- جمل قصيرة. صفر حشو. صفر مقدمات.
- استشهد بـ [n] لكل ادعاء، واذكر قائمة المصادر في النهاية.
- إذا لم ترجع الأداة نتائج كافية، قل ذلك صراحةً برقم: "وجدت 0 نتائج".
- لا تردّ على أسئلة خارج نطاق الأخبار.
- ردّ بنفس لغة السؤال (افتراضياً عربي).

# سياق
- اليوم: {{TODAY}}
- لديك أداة واحدة فقط: fetch_live_news
```

---

## 3. Architecture

### Backend
```
backend/
├── ain_ai.py              [NEW] system prompt, agent loop, tool registry,
│                                OpenAI function-calling helper
├── ain_ai_cache.py        [NEW] discovery topics cache (file-based JSON)
├── ai_service.py          [reuse] existing _call_llm + OPENAI_API_KEY loader
├── newsdata_client.py     [reuse] existing search_latest with full param surface
└── app.py                 [extend] 3 new endpoints under /api/ain-ai/*
```

**Why no new DB tables in Ship 1:** chat is stateless (per user decision). Discovery is server-side cached to a JSON file. Zero migration risk.

### Frontend
```
frontend-v2/src/
├── pages/
│   ├── AinAI.jsx          [NEW] single-column page: discovery row + chat
│   └── ...
├── components/
│   └── Sidebar.jsx        [extend] add "عين AI" nav item
└── App.jsx                [extend] register /ain-ai route
```

---

## 4. The single agent tool

```python
fetch_live_news(
    query: str | None,        # main search term
    language: str = "ar",     # ar, en, fr, de, es, ...
    country: str | None,      # ISO-2 codes: sa, ae, eg, us, fr, ...
    category: str | None,     # politics, business, technology, sports, world, ...
    timeframe: str | None,    # NewsData format: "24" = 24h, "6" = 6h, "48h", "7d"
    size: int = 20,           # cap 50 (NewsData hard limit)
)
```

Wraps `newsdata_client.search_latest()`. Returns normalized articles (title, link, source, country, language, published_at, snippet, sentiment, image_url).

**Caching:** identical `(query, language, country, category, timeframe)` cached **15 min in-memory** to avoid burning NewsData quota on retries.

**Why one tool:** keeps the agent's decision space tight → fewer wrong-tool failures, faster, cheaper. More tools come in v2 (corpus search, sentiment breakdown, time-series, write-actions).

---

## 5. Discovery panel pipeline

Runs server-side, every 4h (lazy: refreshed on first request after staleness):

```
1. newsdata_client.search_latest(language="ar", size=50)
        ↓
2. GPT-4o-mini cluster prompt → JSON:
   [
     {
       "title": "تطورات الانتخابات الأمريكية",
       "why_trending": "ذكر في 12 مصدر اليوم",
       "suggested_keywords": ["ترامب", "بايدن", "الانتخابات"],
       "sample_article_ids": ["...", "..."]
     },
     ...6 themes total
   ]
        ↓
3. Save to backend/data/ain_ai_discovery.json with timestamp
        ↓
4. /api/ain-ai/discover serves the cache as-is
```

**User interaction:** clicking a topic card inserts a question into the chat composer (e.g. *"أخبرني المزيد عن تطورات الانتخابات الأمريكية"*). Topic acceptance / "add to my keywords" is a v2 feature.

---

## 6. API endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/ain-ai/chat` | `@login_required` | Streamed SSE chat. Body: `{ messages: [{role, content}, ...] }`. Stateless — client sends full history each time. |
| `GET` | `/api/ain-ai/discover` | `@login_required` | Returns cached trending topics. Auto-refreshes if older than 4h. |
| `POST` | `/api/ain-ai/discover/refresh` | `@admin_required` | Force-refresh the cache. |

CSRF: enforced via the global before-request hook (apiFetch already sends the token).

---

## 7. Cost & safety guards

| Guard | Value |
|---|---|
| OpenAI model | `gpt-4.1-mini-2025-04-14` (agent + clustering) |
| Per-message max tool iterations | 5 |
| Per-message max output tokens | 4000 |
| Per-user daily OpenAI tokens | 100,000 (~$0.10/day worst case @ gpt-4.1-mini) |
| Per-user daily NewsData calls | 30 |
| In-memory NewsData cache TTL | 15 minutes |
| Discovery cache TTL | 4 hours |
| Tool call inputs sanitized | yes (whitelist params, cap size to 50) |
| Prompt-injection guard | tool outputs wrapped in delimiters; system prompt instructs to treat as data only |
| User scoping | every endpoint `@login_required`; chat sees no user data in Ship 1 |

---

## 8. Cost math (worst case)

Per question (5k input + 600 output GPT-4o-mini):
- ~5000 × $0.00015 + ~600 × $0.00060 = **~$0.001**

100 active users × 30 questions/day × $0.001 = **$3/day**.
Discovery refresh: 6 runs/day × ~$0.002 = **$0.012/day** total (global, not per user).

NewsData: cached 15 min per query → real-world 5–10 calls/user/day. Discovery: 6/day global. Comfortable on most NewsData tiers.

---

## 9. UX details (locked)

### Layout
- **Single column** (no session sidebar — user explicitly chose this)
- **No session history persistence** — each visit = fresh chat, history lives in React state only
- **No follow-up suggestion chips** — clean composer, user drives
- **Discovery row above chat** — 4–6 trending topic cards, horizontal scroll on mobile
- **Empty state** — welcome card + 3 sample question buttons

### Message rendering
- User: right-aligned bubble (RTL)
- Agent:
  - Tool-call status pill streamed during agent work: `🔍 يبحث في NewsData...`
  - Markdown-rendered streaming text with inline `[1] [2]` citations
  - Bottom: collapsible "📄 المصادر (n)" expanding to clickable article cards
- Citations: clicking `[1]` scrolls to source card; clicking source card opens in new tab

### Composer
- Multi-line textarea, auto-grow up to 6 lines
- Enter = send, Shift+Enter = newline
- Disabled with stop button while streaming
- Shows daily token-cap warning when approaching limit

### Streaming
- SSE-style chunked response from `/api/ain-ai/chat`
- Frontend uses `fetch` + `response.body.getReader()` (no EventSource — easier with POST + auth cookies + CSRF)
- Three event types streamed: `tool_call`, `delta` (text chunk), `done` (final with citations array)

---

## 10. Design decisions log

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | **Agent (function calling)**, not RAG | User's corpus already keyword-filtered upstream; embeddings overkill for Ship 1; agent unifies chat + discovery |
| Persona | **Pure analyst** (cooler/more analytical) | User pick. Fits monitoring tool, maximizes credibility |
| Tools in Ship 1 | **1 tool** (`fetch_live_news`) | Quality + speed focus; user explicitly excluded corpus access |
| Discovery in Ship 1 | **Yes, included** | User pick. Tab feels finished from day one |
| Model | **GPT-4o-mini** | Cheap, fast, good Arabic; user pick |
| Layout | **Single column, no sessions** | User pick — simplicity over chat-history features |
| Follow-up chips | **None** | User pick — cleaner UX |
| Topics/Watchlists | **Deferred** | Out of Ship 1 scope; will revisit before write-action tools land |
| Corpus access | **Deferred to v2** | User explicitly: "later on updates not now" |
| Embeddings / vectors | **Deferred to v2** | Not needed without corpus access; keep infra simple |

---

## 11. Build order (~2 working days)

| # | Task | Effort |
|---|---|---|
| 1 | `ain_ai.py` — system prompt, tool schema, agent loop, OpenAI function-calling helper | 3h |
| 2 | `ain_ai_cache.py` — discovery cache reader/writer + cluster pipeline | 2h |
| 3 | `app.py` endpoints — chat (SSE), discover, refresh + cost guards | 3h |
| 4 | `AinAI.jsx` — discovery cards + chat UI + streaming + citations | 6h |
| 5 | Sidebar nav entry + App.jsx route registration | 30m |
| 6 | Manual smoke testing + iteration | 3h |

Total: **~17.5 hours** ≈ 2 working days.

---

## 12. Out of Ship 1 (parking lot for v2+)

- Corpus access tools (`search_user_articles`, `get_user_profile`, `get_sentiment_breakdown`, `count_articles_over_time`)
- Write-action tools (`propose_keyword_to_track`, `propose_topic_for_tracking`)
- Embedding-based semantic search (only if corpus tools prove insufficient with SQL/keyword retrieval)
- Topics/Watchlists feature (precursor for "accept-trending → topic" flow)
- Persistent chat sessions + history sidebar
- Suggested follow-up chips
- Voice input
- Web search tool (Tavily/SerpAPI) for non-news context
- PDF report export
- Push notifications / alerts
- Multi-tenant team workspaces
- Personal API tokens
- English UI toggle
- Onboarding wizard tied to discovery

---

## 13. Production readiness checklist (before deploying to Render)

- [ ] Both `OPENAI_API_KEY` and `NEWSDATA_API_KEY` exist in Render env
- [ ] Daily token/call caps enforced server-side
- [ ] Errors surface user-friendly Arabic messages, not stack traces
- [ ] All endpoints behind `@login_required` (admin endpoints behind `@admin_required`)
- [ ] No PII in logs (only user IDs, never emails)
- [ ] Frontend handles 429 (rate-limit) and 503 (LLM down) gracefully
- [ ] Discovery cache file path writable in Render's filesystem (or moved to DB)
- [ ] Manual smoke test on local + staging before push
- [ ] User has approved the build before merging to main

---

## 14. Open / pending items

_(Empty for now. Add here whenever a new question or refinement comes up during the build.)_

---

## 15. Revision history

| Date | Change |
|---|---|
| Ship 1 kickoff | Initial plan locked after 5 design rounds and 4 confirmation questions |
