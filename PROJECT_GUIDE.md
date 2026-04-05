# عين (Ain) — News Monitor Project Guide

> A full-stack **Arabic-first news monitoring system** that fetches RSS feeds from 200+ sources across 30+ countries, matches articles against user-defined keywords in 32+ languages, translates results to Arabic, and presents them in a modern dashboard.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Backend Deep Dive](#backend-deep-dive)
5. [Frontend Deep Dive](#frontend-deep-dive)
6. [Authentication & Authorization](#authentication--authorization)
7. [Monitoring Pipeline](#monitoring-pipeline)
8. [Global Scheduler](#global-scheduler)
9. [Keyword Expansion & Matching](#keyword-expansion--matching)
10. [API Endpoints Reference](#api-endpoints-reference)
11. [Database Schema](#database-schema)
12. [Configuration](#configuration)
13. [AI Features](#ai-features)
14. [Data Lifecycle](#data-lifecycle)
15. [Deployment](#deployment)
16. [Local Development Setup](#local-development-setup)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React SPA)                      │
│  Vite + Tailwind CSS + Framer Motion + Lucide Icons              │
│  Port: 5173 (dev) │ Served from backend/static (prod)            │
└────────────────────────────┬────────────────────────────────────┘
                             │  REST API (JSON) + Session Cookies
                             │  CSRF via X-CSRFToken header
┌────────────────────────────┴────────────────────────────────────┐
│                        Backend (Flask API)                        │
│  Port: 5555 (dev) │ Gunicorn (prod)                              │
│                                                                   │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐   │
│  │  Auth Layer  │  │  API Routes   │  │  Global Scheduler   │   │
│  │  (bcrypt +   │  │  (app.py      │  │  (background thread │   │
│  │   JWT +      │  │   ~3966 lines)│  │   every 15 min)     │   │
│  │   sessions)  │  │               │  │                     │   │
│  └──────────────┘  └───────────────┘  └─────────────────────┘   │
│                                                                   │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────────┐   │
│  │  RSS Fetch   │  │  Multilingual │  │  Translation        │   │
│  │  (async +    │  │  Matcher      │  │  (Google Translate   │   │
│  │   sync)      │  │  (32+ langs)  │  │   FREE, no API key) │   │
│  └──────────────┘  └───────────────┘  └─────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Database: SQLite (local) │ PostgreSQL (production/Render)│    │
│  │  ORM: SQLAlchemy                                          │    │
│  └──────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
- **Framework:** Flask
- **ORM:** SQLAlchemy
- **Database:** SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`)
- **Auth:** bcrypt (password hashing), PyJWT (tokens), Flask-Login (sessions), Flask-WTF (CSRF)
- **RSS:** feedparser, aiohttp (async fetching), requests (sync fallback)
- **Translation:** deep-translator (Google Translate, free, no API key)
- **Language Detection:** langdetect
- **PDF Generation:** reportlab + arabic-reshaper + python-bidi
- **AI:** OpenAI GPT-4o-mini (optional, for daily briefs and sentiment)
- **External News API:** NewsData.io (optional, requires `NEWSDATA_API_KEY`)

### Frontend
- **Framework:** React 18 (SPA, no router — state-based navigation)
- **Build Tool:** Vite
- **Styling:** Tailwind CSS + custom CSS
- **Animations:** Framer Motion
- **Icons:** Lucide React
- **Exports:** html2pdf.js, jspdf, jspdf-autotable, xlsx

---

## Project Structure

```
ain-news-monitor/
├── backend/
│   ├── app.py                      # Main Flask app (~3966 lines) — ALL API routes
│   ├── models.py                   # SQLAlchemy ORM models + DB setup
│   ├── config.py                   # System configuration constants
│   ├── auth_utils.py               # Password hashing, JWT, CSRF helpers
│   ├── global_scheduler.py         # Singleton scheduler (background thread)
│   ├── job_executor.py             # Per-user background monitoring jobs
│   ├── async_rss_fetcher.py        # High-performance async RSS fetcher (aiohttp)
│   ├── async_monitor_wrapper.py    # Bridges async fetcher with sync Flask routes
│   ├── rss_service.py              # Sync RSS fetching with retries + SSL fixes
│   ├── multilingual_matcher.py     # Keyword matching across 32+ languages
│   ├── keyword_expansion.py        # Translates Arabic keywords to 32+ languages
│   ├── translation_service.py      # Google Translate wrapper (keyword + article)
│   ├── translation_cache.py        # Translation caching layer
│   ├── text_normalization.py       # Unicode/script normalization for matching
│   ├── arabic_utils.py             # Arabic text normalization (alef, taa marbuta, etc.)
│   ├── match_context_extractor.py  # Extracts surrounding text around keyword matches
│   ├── article_balancer.py         # Balances saved articles across keywords/countries
│   ├── feed_health.py              # Tracks RSS feed reliability over time
│   ├── proper_noun_rules.py        # Curated translations for proper nouns
│   ├── pdf_generator.py            # PDF report generation (reportlab, Arabic support)
│   ├── ai_service.py               # OpenAI integration (daily briefs, sentiment)
│   ├── newsdata_client.py          # NewsData.io API client
│   ├── seed_data.py                # Database seeding (countries + RSS sources)
│   ├── utils.py                    # HTML cleaning, date parsing, keyword matching
│   ├── requirements.txt            # Python dependencies (pinned versions)
│   ├── exports/                    # Legacy export file storage (per-user folders)
│   ├── uploads/                    # User uploaded files (per-user folders)
│   ├── fonts/                      # Arabic fonts for PDF generation (auto-downloaded)
│   └── static/                     # Built frontend served in production
│
├── frontend-v2/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx                # React entry point
│       ├── App.jsx                 # Root component (routing, layout, auth gate)
│       ├── apiClient.js            # Centralized fetch wrapper (CSRF, credentials)
│       ├── index.css               # Tailwind + custom styles
│       ├── context/
│       │   └── AuthContext.jsx     # Auth state (login, register, logout, session)
│       ├── components/
│       │   ├── Sidebar.jsx         # Navigation sidebar (RTL Arabic)
│       │   ├── ArticleCard.jsx     # Article display card
│       │   ├── FilterBar.jsx       # Article filter controls
│       │   ├── StatsOverview.jsx   # Dashboard statistics cards
│       │   ├── Loader.jsx          # Loading spinner
│       │   ├── Skeleton.jsx        # Skeleton loading states
│       │   ├── QueryBuilder.jsx    # NewsData.io query builder
│       │   ├── GuidedQueryBuilder.jsx  # Step-by-step query builder
│       │   └── ArabicOperatorHelper.jsx # Arabic operator guide
│       ├── pages/
│       │   ├── Dashboard.jsx       # Main results page (articles, stats, AI brief)
│       │   ├── Keywords.jsx        # Keyword management + monitoring controls
│       │   ├── DirectSearch.jsx    # NewsData.io advanced search
│       │   ├── DirectSearch_v2.jsx # Alternate search UI
│       │   ├── TopHeadlines.jsx    # Browse headlines by country
│       │   ├── Countries.jsx       # Country/source management
│       │   ├── Bookmarks.jsx       # Saved articles (survive monthly reset)
│       │   ├── MyFiles.jsx         # File uploads and export history
│       │   ├── Admin.jsx           # Admin dashboard (users, stats, audit)
│       │   ├── Settings.jsx        # User settings
│       │   ├── Profile.jsx         # User profile management
│       │   ├── Login.jsx           # Login page
│       │   └── Register.jsx        # Registration page (pending admin approval)
│       └── utils/                  # Frontend utility functions
│
├── render.yaml                     # Render.com deployment config
├── .env.example                    # Example environment variables
└── README.md                       # Basic setup instructions
```

---

## Backend Deep Dive

### `app.py` — The Monolith (~3966 lines)

All API routes live in this single file. Key sections:

| Lines (approx) | Section | Description |
|---|---|---|
| 1–134 | **Setup** | Flask app, CORS, Flask-Login, CSRF cookie, DB session management |
| 137–194 | **Helpers** | `admin_required` decorator, `scoped()` query filter, `get_current_user_id()` |
| 196–224 | **Audit Logging** | `log_action()` writes to AuditLog table |
| 227–512 | **Exports** | PDF generation, export CRUD, file download (DB + legacy filesystem) |
| 514–655 | **User Files** | File upload/download/delete with per-user isolation |
| 658–731 | **Search History** | CRUD for search history records |
| 733–984 | **Admin APIs** | User management (list, create, update, delete), admin stats |
| 987–1194 | **Auth Routes** | Signup, login, logout, `/me`, profile update, password change |
| 1196–1347 | **Countries & Sources** | CRUD for RSS source catalog (admin-only writes) |
| 1348–1619 | **Keywords** | CRUD with auto-translation, expansion, keyword sharing between users |
| 1621–1760 | **Monitoring Jobs** | Background job execution and global scheduler controls |
| 1761–1938 | **Manual Monitoring** | On-demand RSS fetch + match + save pipeline |
| 1940–2058 | **Articles** | Paginated article listing with filters |
| 2060–2167 | **Article Metadata** | Country breakdown, stats, health checks |
| 2169–2372 | **Export & Reset** | Atomic export-to-Excel then delete all user data |
| 2374–2503 | **Feed Diagnostics** | Admin feed self-test and diagnosis tools |
| 2505–2894 | **NewsData.io** | Direct search, advanced search, query builder, count, sources |
| 2910–3374 | **Top Headlines** | Per-country RSS headlines (internal + external API) |
| 3377–3512 | **AI Features** | Daily brief (GPT-4o-mini summary), sentiment explanation |
| 3514–3638 | **Bookmarks** | CRUD for bookmarked articles (survive monthly reset) |
| 3640–3712 | **Data Lifecycle** | Monthly auto-cleanup on 1st of each month |
| 3715–3966 | **Auto-Initialize** | DB migration, admin user seeding, country/source seeding, scheduler start |

### `models.py` — Database Models

| Model | Table | Purpose |
|---|---|---|
| `User` | `users` | User accounts (email, password_hash, role: ADMIN/USER, is_active) |
| `Country` | `countries` | Arab countries catalog (name_ar, enabled) |
| `Source` | `sources` | RSS feed sources (url, country, name, fail_count) |
| `Keyword` | `keywords` | User keywords with translations to 7 base languages + JSON expansion to 32+ |
| `Article` | `articles` | Matched articles with original + Arabic text, sentiment, match context |
| `AuditLog` | `audit_log` | Admin action audit trail |
| `ExportRecord` | `exports` | Export history with optional file_data (BLOB for Render compatibility) |
| `UserFile` | `user_files` | User-uploaded files |
| `SearchHistory` | `search_history` | Search query history |
| `MonitorJob` | `monitor_jobs` | Background monitoring job tracking (status, progress) |
| `BookmarkedArticle` | `bookmarked_articles` | Bookmarks that survive monthly data reset |
| `DailyBrief` | `daily_briefs` | Cached AI daily brief per user per day (+ keyword filter) |
| `SystemConfig` | `system_config` | Key-value system configuration |

**Key relationships:**
- All user-owned data has `user_id` foreign key
- Articles have composite unique constraint: `(url, user_id)` — same article can exist for multiple users
- `MonitorJob` with `user_id=0` represents global scheduler system jobs

### Key Backend Services

#### `async_rss_fetcher.py` — AsyncRSSFetcher
- Fetches 200+ RSS feeds **concurrently** using aiohttp
- Connection pooling, adaptive timeouts (5s fast / 15s slow)
- Exponential backoff retry (max 2 retries)
- Duplicate detection via URL hashing
- RAM-optimized: ETag cache disabled (Phase 3)

#### `async_monitor_wrapper.py` — Sync-Async Bridge
- Wraps async RSS fetcher for use in sync Flask routes
- Processes sources in batches (memory-optimized for 512MB RAM limit)
- Handles keyword matching, translation, and match context extraction

#### `rss_service.py` — Sync RSS Fetcher (Fallback)
- requests + feedparser based
- IPv4 preference (fixes Windows DNS issues)
- SSL certificate handling via certifi
- Realistic User-Agent headers to avoid 403s

#### `translation_service.py` — Google Translate Wrapper
- `translate_keyword()`: Arabic → 7 languages (en, fr, tr, ur, zh, ru, es)
- `translate_to_arabic()`: Any language → Arabic (for article translation)
- `detect_language()`: Uses langdetect
- `analyze_sentiment()`: Placeholder (returns neutral)
- **No API key required** — uses free Google Translate via deep-translator

#### `keyword_expansion.py` — Keyword Expansion
- Expands Arabic keywords to **32+ languages** using Google Translate
- Stored in `keywords.translations_json` column (not RAM)
- Supports curated proper noun translations (via `proper_noun_rules.py`)
- TTL: 365 days before re-expansion

#### `pdf_generator.py` — PDF Reports
- Pure Python (reportlab + arabic-reshaper + python-bidi)
- Auto-downloads Arabic fonts (Amiri) from Google Fonts
- Zero system dependencies

#### `ai_service.py` — AI Features
- Uses OpenAI GPT-4o-mini
- `generate_daily_brief()`: Summarizes day's articles into Arabic paragraph
- `explain_sentiment()`: Explains why an article has positive/negative sentiment
- Requires `OPENAI_API_KEY` environment variable

#### `newsdata_client.py` — NewsData.io Client
- Advanced search with query builder (AND/OR/NOT operators)
- Multiple endpoints: latest, crypto, archive, market, sources
- Requires `NEWSDATA_API_KEY` environment variable

---

## Frontend Deep Dive

### Navigation (State-Based, No Router)

The app uses `useState('dashboard')` in `App.jsx` for page switching — no React Router. Pages:

| Page ID | Component | Description |
|---|---|---|
| `dashboard` | `Dashboard.jsx` | Main results view: article cards, stats, filters, AI daily brief |
| `keywords` | `Keywords.jsx` | Add/delete keywords, trigger monitoring, view expansion status |
| `directsearch` | `DirectSearch.jsx` | NewsData.io search with advanced query builder |
| `topheadlines` | `TopHeadlines.jsx` | Browse latest headlines by country (from RSS) |
| `bookmarks` | `Bookmarks.jsx` | Saved articles that persist across monthly resets |
| `myfiles` | `MyFiles.jsx` | File uploads + export download history |
| `countries` | `Countries.jsx` | View/manage countries and RSS sources (admin: add/toggle) |
| `admin` | `Admin.jsx` | User management, system stats, audit logs (ADMIN only) |
| `settings` | `Settings.jsx` | App settings |
| `profile` | `Profile.jsx` | Edit name, change password |

### `apiClient.js` — Centralized API Client

```javascript
// All API calls go through apiFetch()
export function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;          // VITE_API_BASE_URL or '' (relative)
  const csrfToken = getCookie('csrf_token');   // Read CSRF from cookie
  return fetch(url, {
    credentials: 'include',                    // Always send session cookies
    headers: { 'X-CSRFToken': csrfToken, ...options.headers },
    ...options,
  });
}
```

### `AuthContext.jsx` — Auth State Management

- Checks session on mount via `GET /api/auth/me`
- Provides: `currentUser`, `authLoading`, `isAdmin`, `login()`, `register()`, `logout()`, `refreshUser()`
- Login gates: unauthenticated users see `Login.jsx` or `Register.jsx`
- Registration creates inactive accounts (pending admin approval)

### UI Design
- **RTL (Right-to-Left)** Arabic layout throughout
- **Dark sidebar** with teal accent gradient
- **Glassmorphism** top bar with backdrop blur
- **Framer Motion** page transitions
- **Responsive**: mobile hamburger menu + desktop sidebar

---

## Authentication & Authorization

### Flow
1. **Registration**: `POST /api/auth/signup` → creates inactive user (`is_active=false`)
2. **Admin Approval**: Admin activates user via `PATCH /api/admin/users/:id`
3. **Login**: `POST /api/auth/login` → Flask-Login session cookie set
4. **Session Check**: `GET /api/auth/me` → returns user info or 401
5. **CSRF**: Cookie `csrf_token` set on every response; frontend sends as `X-CSRFToken` header

### Security Features
- **bcrypt** password hashing (12 rounds)
- **Password strength validation** (min 8 chars, mixed case, number, special char)
- **CSRF protection** via double-submit cookie pattern
- **Session-based auth** (Flask-Login) with `SameSite=Lax` cookies
- **JWT tokens** available for API auth (not actively used in SPA flow)
- **Rate limiting** on monitoring jobs (10/hour per user)
- **User isolation**: `scoped()` query helper with `force_user_filter=True`
- **Admin-only routes**: `@admin_required` decorator
- **External API auth**: HMAC constant-time key comparison, header-only (no query params)

### Roles
| Role | Capabilities |
|---|---|
| `USER` | Own keywords, articles, exports, bookmarks, files |
| `ADMIN` | All USER capabilities + manage users, sources, countries, global scheduler, feed diagnostics |
| `SYSTEM` | Internal (user_id=0, used by global scheduler for DB locks) |

---

## Monitoring Pipeline

### On-Demand Flow (`POST /api/monitor/run`)

```
1. Get enabled Sources (shared catalog, all countries)
2. Get current user's enabled Keywords
3. Load cached keyword expansions (32+ language translations from DB)
4. run_optimized_monitoring():
   a. Fetch ALL RSS feeds concurrently (50 at a time via aiohttp)
   b. For each article from each feed:
      - Extract title + summary, clean HTML
      - Detect language (langdetect)
      - Match against ALL keyword variants (multilingual_matcher)
      - Extract match context (surrounding text snippet)
   c. Collect all matches with relevance scores
5. save_matched_articles_sync():
   a. Balance articles across keywords/countries (article_balancer)
   b. Translate to Arabic (Google Translate)
   c. Deduplicate by (url, user_id)
   d. Save to articles table
6. Return results with comprehensive stats
```

### Background Job Flow (`POST /api/monitor/job/start`)

Uses `job_executor.py` (JobExecutor singleton):
- Runs in a background thread
- Per-user limits: 1 concurrent job, 10/hour rate limit
- Global concurrency: max 5 simultaneous jobs
- Tracks progress in `monitor_jobs` table
- Supports cancellation via threading events

---

## Global Scheduler

`global_scheduler.py` — Singleton `GlobalMonitoringScheduler`:

- **One scheduler for ALL users** (replaces per-user schedulers)
- Runs as a daemon thread, default interval: **15 minutes**
- On each run:
  1. Acquire DB lock (`MonitorJob` with `user_id=0`)
  2. Fetch ALL enabled RSS feeds once
  3. For each user with enabled keywords: match articles and save results
  4. Release DB lock
- **Self-healing**: auto-restarts after crashes (up to 5 consecutive)
- **Watchdog**: `ensure_running()` called by Dashboard status poll (every 30s)
- **Stale lock cleanup**: force-releases locks older than 5 minutes
- **Trigger**: immediate run when new keyword is added

---

## Keyword Expansion & Matching

### Expansion Flow (When Keyword Added)
```
1. User adds Arabic keyword (e.g., "السعودية")
2. Step 1: Translate to 7 base languages (Google Translate)
   → en, fr, tr, ur, zh, ru, es → stored in Keyword model columns
3. Step 2: Expand to 32+ languages (keyword_expansion.py)
   → en, fr, es, de, ru, zh-cn, ja, hi, id, pt, tr, ar, ko, it, nl, pl, vi, th, uk, ro, el, cs, sv, hu, fi, da, no, sk, bg, hr, ms, fa, ur
   → Stored in keywords.translations_json (database, not RAM)
4. Check for curated proper noun forms (proper_noun_rules.py)
5. Copy articles from other users with same keyword (keyword sharing)
6. Trigger global scheduler immediate run
```

### Matching Logic (multilingual_matcher.py)
- **Latin scripts**: Word-boundary matching (regex `\b`)
- **Arabic/CJK scripts**: Substring matching (no word boundaries)
- **Arabic normalization**: Alef variants → ا, taa marbuta → هاء, remove diacritics
- **Text normalization**: Lowercase, strip HTML, collapse whitespace
- **Relevance scoring**: Title match (weight 0.6) + description match (weight 0.4)

---

## API Endpoints Reference

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/signup` | Public | Register (pending approval) |
| POST | `/api/auth/login` | Public | Login (session cookie) |
| POST | `/api/auth/logout` | User | Logout |
| GET | `/api/auth/me` | User | Get current user |
| PATCH | `/api/auth/profile` | User | Update display name |
| POST | `/api/auth/change-password` | User | Change password |

### Keywords
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/keywords` | User | List user's keywords |
| GET | `/api/keywords/expanded` | User | Keywords with 32+ lang expansions |
| POST | `/api/keywords` | User | Add keyword (auto-translate + expand) |
| DELETE | `/api/keywords/:id` | User | Delete keyword |
| POST | `/api/keywords/:id/toggle` | User | Toggle keyword enabled |

### Monitoring
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/monitor/run` | User | Run monitoring on-demand |
| POST | `/api/monitor/job/start` | User | Start background monitoring job |
| GET | `/api/monitor/job/status` | User | Get active job status |
| GET | `/api/monitor/status` | User | Get scheduler status (+ watchdog) |
| POST | `/api/monitor/start` | Admin | Start global scheduler |
| POST | `/api/monitor/stop` | Admin | Stop global scheduler |

### Articles
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/articles` | User | List articles (paginated, filtered) |
| GET | `/api/articles/stats` | User | Article statistics |
| GET | `/api/articles/countries` | User | Distinct countries in user's articles |
| POST | `/api/articles/clear` | User | Delete all user's articles |
| POST | `/api/articles/export-and-reset` | User | Export to Excel then delete all |

### Bookmarks
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/bookmarks` | User | List bookmarks |
| POST | `/api/bookmarks` | User | Create bookmark |
| DELETE | `/api/bookmarks/:id` | User | Delete bookmark |
| POST | `/api/bookmarks/check` | User | Batch check bookmarked URLs |

### Exports & Files
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/exports` | User | List export history |
| POST | `/api/exports` | User | Create export record (+ optional file) |
| GET | `/api/exports/:id/download` | User | Download exported file |
| DELETE | `/api/exports/:id` | User | Delete export |
| POST | `/api/exports/generate-pdf` | User | Generate PDF from article data |
| GET | `/api/files` | User | List user files |
| POST | `/api/files` | User | Upload file |
| GET | `/api/files/:id` | User | Download file |
| DELETE | `/api/files/:id` | User | Delete file |

### Countries & Sources
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/countries` | User | List all countries |
| POST | `/api/countries/:id/toggle` | Admin | Toggle country enabled |
| GET | `/api/sources` | User | List all RSS sources |
| POST | `/api/sources` | Admin | Add RSS source |
| PUT | `/api/sources/:id` | Admin | Update source |
| DELETE | `/api/sources/:id` | Admin | Delete source |
| POST | `/api/sources/:id/toggle` | Admin | Toggle source enabled |
| GET | `/api/sources/countries` | Public | Countries with source counts |

### Admin
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/admin/users` | Admin | List users (with search) |
| POST | `/api/admin/users` | Admin | Create user |
| PATCH | `/api/admin/users/:id` | Admin | Update user |
| DELETE | `/api/admin/users/:id` | Admin | Delete user (cascade) |
| GET | `/api/admin/users/:id/keywords` | Admin | Get user's keywords |
| GET | `/api/admin/stats` | Admin | System statistics |
| GET | `/api/admin/audit` | Admin | Audit logs |
| GET | `/api/feeds/diagnose` | Admin | Diagnose all feeds |
| GET | `/api/feeds/selftest` | Admin | Quick self-test N feeds |

### NewsData.io (External API)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/direct-search` | User | Simple NewsData.io search |
| GET/POST | `/api/newsdata/search` | User | Advanced search (all endpoints) |
| GET/POST | `/api/newsdata/count` | User | Estimated result count |
| POST | `/api/newsdata/build-query` | User | Preview query string |
| GET | `/api/newsdata/sources` | User | Available NewsData.io sources |

### Headlines
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/headlines/top` | User | Top headlines per country (RSS) |
| POST | `/api/external/headlines` | API Key | External API for headlines |

### AI
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/ai/daily-brief` | User | Generate AI daily brief |
| POST | `/api/ai/explain-sentiment` | User | AI sentiment explanation |

### System
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | Public | Health check |
| GET | `/api/health/translation` | Public | Test Google Translate |
| GET | `/api/system/cleanup-status` | User | Monthly reset countdown |
| GET | `/api/search-history` | User | Search history |
| POST | `/api/search-history` | User | Record search |
| DELETE | `/api/search-history/:id` | User | Delete search entry |

---

## Database Schema

### Key Design Decisions
- **Multi-tenant isolation**: All user data filtered by `user_id`
- **Composite unique**: Articles `(url, user_id)` — same URL can exist per-user
- **File storage**: Exports store `file_data` as BLOB (Render-compatible, no filesystem)
- **DB-backed translations**: `keywords.translations_json` stores 32+ language expansions
- **System user**: `user_id=0` reserved for global scheduler job locks
- **Auto-migration**: `auto_initialize()` handles schema changes on startup

### SQLite vs PostgreSQL
| Feature | SQLite (Local) | PostgreSQL (Production) |
|---|---|---|
| Connection | `sqlite:///ain_news.db` | `DATABASE_URL` env var |
| File storage | BLOB column | BYTEA column |
| Schema migration | PRAGMA-based checks | `ALTER TABLE ... IF NOT EXISTS` |
| Constraint migration | Table rebuild | `ALTER TABLE` in-place |

---

## Configuration

### Environment Variables
| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Prod | Auto-generated | Flask session secret |
| `JWT_SECRET` | Prod | Ephemeral | JWT signing key |
| `DATABASE_URL` | Prod | SQLite file | PostgreSQL connection string |
| `ADMIN_INIT_PASSWORD` | No | Random | Initial admin password |
| `NEWSDATA_API_KEY` | No | — | NewsData.io API key |
| `OPENAI_API_KEY` | No | — | OpenAI API key (AI features) |
| `EXTERNAL_API_KEY` | No | — | External headlines API key |
| `SESSION_COOKIE_SECURE` | Prod | false | HTTPS-only cookies |
| `FLASK_RUN_PORT` | No | 5555 | Backend port |
| `PORT` | Render | 5555 | Render's port variable |
| `TRANSLATE_TARGETS` | No | 33 langs | Comma-separated language codes |
| `PYTHONIOENCODING` | Windows | — | Set to `utf-8` for emoji support |

### `config.py` — System Constants
| Setting | Default | Description |
|---|---|---|
| `MAX_ARTICLES_PER_SAVE` | 200 | Max articles saved per monitoring run |
| `RSS_MAX_CONCURRENT` | 50 | Max concurrent RSS connections |
| `RSS_TIMEOUT_SECONDS` | 10 | Per-feed timeout |
| `RSS_MAX_PER_SOURCE` | 30 | Max articles per feed |
| `MONITORING_INTERVAL_SECONDS` | 900 | Global scheduler interval (15 min) |
| `KEYWORD_MIN_SCORE` | 0.3 | Minimum relevance score for match |
| `FEED_HEALTH_WINDOW` | 100 | Number of fetches to track per feed |

---

## AI Features

### Daily Brief (`/api/ai/daily-brief`)
- Summarizes all of today's articles for the user into a concise Arabic paragraph
- Supports keyword-specific filtering
- Cached per user per day (+ keyword) in `daily_briefs` table
- Force refresh available

### Sentiment Explanation (`/api/ai/explain-sentiment`)
- On-demand explanation of why an article is positive/negative/neutral
- Uses GPT-4o-mini with article title, summary, source, country, keyword context

### Requirements
- `OPENAI_API_KEY` must be set
- Model: `gpt-4o-mini`
- Max tokens: 1024
- Temperature: 0.4

---

## Data Lifecycle

### Monthly Reset (1st of Every Month)
- `check_and_run_cleanup()` runs on server startup
- If today is the 1st: deletes **ALL articles** + old completed/failed monitor jobs
- **Bookmarks survive** the reset (separate table)
- Frontend shows warning banner 3 days before reset
- Users can export before reset via `/api/articles/export-and-reset`

### Export & Reset Flow
1. Generates Excel file in memory (no filesystem)
2. Stores in `exports.file_data` column (BLOB)
3. Atomically deletes user's articles + keywords
4. Returns download URL

---

## Deployment

### Render (Production)
Defined in `render.yaml`:

```yaml
services:
  - type: web
    name: ain-news-monitor
    env: python
    buildCommand: |
      cd frontend-v2 && npm install && npm run build
      cp -r dist/* ../backend/static/
      cd ../backend && pip install -r requirements.txt
    startCommand: cd backend && gunicorn app:app --bind 0.0.0.0:$PORT
    envVars:
      - SECRET_KEY, SESSION_COOKIE_SECURE, NEWSDATA_API_KEY,
        OPENAI_API_KEY, DATABASE_URL (PostgreSQL)
```

### Key Production Behaviors
- Frontend built and copied to `backend/static/`
- Flask serves SPA from `static/index.html` at `/`
- Gunicorn multi-worker: DB locks prevent duplicate scheduler runs
- File exports stored in database (not filesystem — Render ephemeral FS)
- Auto-initialize runs on every Gunicorn worker start

---

## Local Development Setup

### Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt    # May need to skip psycopg2-binary locally
$env:PYTHONIOENCODING = "utf-8"    # Fix Windows emoji/Unicode issues
python app.py                       # Runs on http://localhost:5555
```

### Frontend
```powershell
cd frontend-v2
npm install
npm run dev                         # Runs on http://localhost:5173
```

### Frontend → Backend Proxy
Vite dev server proxies `/api` requests to the backend. Set `VITE_API_BASE_URL` or configure `vite.config.js` proxy.

### Default Admin Account
- Email: `elite@local`
- Password: Set via `ADMIN_INIT_PASSWORD` env var, or auto-generated (printed to console on first run)

### Notes
- **SQLite** is used locally (no PostgreSQL needed)
- **psycopg2-binary** can be skipped locally (only needed for PostgreSQL)
- **aiohttp** may need Visual C++ Build Tools on Windows; install unpinned version for newer Python
- Set `PYTHONIOENCODING=utf-8` on Windows to fix emoji print errors
- Use `powershell -ExecutionPolicy Bypass` if npm scripts are blocked

---

*Last updated: Auto-generated project guide for Ain News Monitor*
