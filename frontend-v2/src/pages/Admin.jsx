import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Users, Activity, Search, Plus, Trash2, Save, X, Lock, KeyRound,
  ChevronDown, ChevronUp, ChevronRight, ChevronLeft, ChevronsLeft, ChevronsRight,
  RefreshCw, Loader2, ShieldCheck, UserCog, LogIn, LogOut,
  Pencil, FileText, FileSpreadsheet, RotateCcw, Upload, AlertCircle,
} from 'lucide-react'
import { apiFetch } from '../apiClient'

// ============================================================
// Admin Panel
// ------------------------------------------------------------
// Two tabs:
//   1. المستخدمون  — paginated user table + search + management
//   2. سجل النشاط  — human-readable activity log
//
// UI principles for this page:
//   - Use the shared utility classes (.card, .btn, .input, .badge,
//     .btn-ghost, .btn-outline) so we look like the rest of the app.
//   - Compact: a row in the user table is one line, not a card.
//   - All destructive actions ask for confirmation.
//   - No information density loss vs the old panel: every previous
//     control is reachable, just better organized.
// ============================================================

const USERS_PER_PAGE = 20
const LOGS_PER_PAGE = 30
const LOGS_AUTOREFRESH_MS = 30_000

// ── Render an audit-log action as a human-readable Arabic sentence ──
// Returns { verb, target, icon, tone } so the row can be styled
// consistently. The `actor` is rendered separately by the caller so
// we don't repeat the name inside the sentence.
function renderAction(log) {
  const m = log.meta || {}
  const kw = m.text_ar || m.keyword || ''
  const where = (() => {
    switch (m.source_type) {
      case 'dashboard': return 'الخلاصة'
      case 'top_headlines': return 'أبرز العناوين'
      case 'bookmarks': return 'المحفوظات'
      case 'country': return `صفحة ${m.country || 'الدولة'}`
      default: return m.source_type || ''
    }
  })()

  switch (log.action) {
    case 'login':
      return { verb: 'سجّل الدخول', icon: LogIn, tone: 'auth' }
    case 'logout':
      return { verb: 'سجّل الخروج', icon: LogOut, tone: 'auth' }
    case 'signup_requested':
      return { verb: 'طلب إنشاء حساب', icon: UserCog, tone: 'auth' }
    case 'change_password':
      return { verb: 'غيّر كلمة المرور', icon: Lock, tone: 'auth' }
    case 'update_name':
      return {
        verb: 'غيّر الاسم',
        target: m.old && m.new ? `من «${m.old}» إلى «${m.new}»` : '',
        icon: Pencil, tone: 'auth',
      }
    case 'add_keyword':
      return { verb: 'أضاف كلمة مفتاحية', target: kw && `«${kw}»`, icon: Plus, tone: 'keywords' }
    case 'delete_keyword':
      return { verb: 'حذف كلمة مفتاحية', target: kw && `«${kw}»`, icon: Trash2, tone: 'keywords' }
    case 'export_pdf':
      return {
        verb: 'صدّر ملف PDF',
        target: where ? `من ${where}` : '',
        icon: FileText, tone: 'exports',
      }
    case 'export_xlsx':
      return {
        verb: 'صدّر ملف Excel',
        target: where ? `من ${where}` : '',
        icon: FileSpreadsheet, tone: 'exports',
      }
    case 'export_and_reset':
      return {
        verb: 'صدّر بياناته وأعاد تهيئة الحساب',
        target: m.articles_deleted != null ? `(${m.articles_deleted} خبر، ${m.keywords_deleted || 0} كلمة)` : '',
        icon: RotateCcw, tone: 'exports',
      }
    case 'bulk_import_sources': {
      const s = m.summary || {}
      return {
        verb: 'رفع ملف مصادر',
        target: s.added != null ? `(أُضيف ${s.added} مصدر)` : '',
        icon: Upload, tone: 'exports',
      }
    }
    case 'admin_create_user':
      return { verb: 'أنشأ مستخدماً جديداً', target: m.email ? `(${m.email})` : '', icon: Plus, tone: 'admin' }
    case 'admin_update_user': {
      const fields = Object.keys(m || {}).filter(k => k !== 'email')
      let detail = ''
      if (fields.includes('name')) detail = 'الاسم'
      else if (fields.includes('role')) detail = 'الصلاحية'
      else if (fields.includes('is_active')) detail = m.is_active ? 'تفعيل الحساب' : 'تعطيل الحساب'
      else if (fields.length === 0) detail = 'كلمة المرور'
      return { verb: 'حدّث بيانات مستخدم', target: detail, icon: UserCog, tone: 'admin' }
    }
    case 'admin_delete_user':
      return { verb: 'حذف مستخدماً', target: m.email ? `(${m.email})` : '', icon: Trash2, tone: 'admin' }
    default:
      return { verb: log.action, icon: Activity, tone: 'auth' }
  }
}

const TONE_COLOR = {
  auth:     { bg: 'rgba(15,118,110,0.08)',  fg: '#0f766e' },
  keywords: { bg: 'rgba(20,184,166,0.08)',  fg: '#0d9488' },
  exports:  { bg: 'rgba(234,88,12,0.08)',   fg: '#c2410c' },
  admin:    { bg: 'rgba(99,102,241,0.08)',  fg: '#4f46e5' },
}

// ── Friendly relative timestamp ───────────────────────────────────
function relativeTime(iso) {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  const diff = (Date.now() - t) / 1000
  if (diff < 5) return 'الآن'
  if (diff < 60) return `قبل ${Math.floor(diff)} ث`
  if (diff < 3600) return `قبل ${Math.floor(diff / 60)} د`
  if (diff < 86400) return `قبل ${Math.floor(diff / 3600)} س`
  if (diff < 7 * 86400) return `قبل ${Math.floor(diff / 86400)} يوم`
  return new Date(iso).toLocaleDateString('ar-EG', { year: 'numeric', month: 'short', day: 'numeric' })
}

function absoluteTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('ar-EG', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}


// ============================================================
// Main component — tab container
// ============================================================
export default function Admin() {
  const [tab, setTab] = useState('users')

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">لوحة الإدارة</h1>
        <p className="text-sm text-slate-500 mt-0.5">إدارة المستخدمين ومراقبة النشاط</p>
      </div>

      {/* Tab strip — minimal, matches app aesthetic */}
      <div className="flex items-center gap-1 p-1 rounded-xl"
        style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(0,0,0,0.05)', width: 'fit-content' }}>
        <TabButton active={tab === 'users'} onClick={() => setTab('users')} icon={Users}>المستخدمون</TabButton>
        <TabButton active={tab === 'logs'} onClick={() => setTab('logs')} icon={Activity}>سجل النشاط</TabButton>
      </div>

      {tab === 'users' ? <UsersTab /> : <ActivityLogTab />}
    </div>
  )
}

function TabButton({ active, onClick, icon: Icon, children }) {
  return (
    <button
      onClick={onClick}
      className="px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all duration-150"
      style={{
        background: active ? '#ffffff' : 'transparent',
        color: active ? '#0f766e' : '#64748b',
        boxShadow: active ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
      }}>
      <Icon className="w-4 h-4" />
      {children}
    </button>
  )
}


// ============================================================
// Users tab
// ============================================================
function UsersTab() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [expanded, setExpanded] = useState(null)            // user id whose keywords are open
  const [keywordsByUser, setKeywordsByUser] = useState({})  // { [user_id]: [...] }
  const [keywordsLoading, setKeywordsLoading] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editDraft, setEditDraft] = useState({})
  const [saving, setSaving] = useState(false)
  const [passwordTarget, setPasswordTarget] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)

  // Debounce the search input so we don't hit the API on every keystroke.
  const [debouncedQ, setDebouncedQ] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => { setPage(1) }, [debouncedQ])

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(page), per_page: String(USERS_PER_PAGE),
      })
      if (debouncedQ) params.set('q', debouncedQ)
      const res = await apiFetch(`/api/admin/users?${params}`)
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
        setTotalPages(data.total_pages || 1)
        setTotal(data.total || 0)
      }
    } catch (e) {
      console.error('Failed to load users:', e)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedQ])

  useEffect(() => { loadUsers() }, [loadUsers])

  const toggleKeywords = async (userId) => {
    if (expanded === userId) { setExpanded(null); return }
    setExpanded(userId)
    if (!keywordsByUser[userId]) {
      setKeywordsLoading(userId)
      try {
        const res = await apiFetch(`/api/admin/users/${userId}/keywords`)
        if (res.ok) {
          const data = await res.json()
          // Backend returns { user_id, user_name, keywords: [...], total }
          // — unwrap the array (tolerate older shape that returned a bare list).
          const list = Array.isArray(data) ? data : (data.keywords || [])
          setKeywordsByUser(prev => ({ ...prev, [userId]: list }))
        }
      } catch (e) {
        console.error('Failed to load keywords:', e)
      } finally {
        setKeywordsLoading(null)
      }
    }
  }

  const startEdit = (u) => {
    setEditingId(u.id)
    setEditDraft({ name: u.name || '', role: u.role, is_active: u.is_active })
  }
  const cancelEdit = () => { setEditingId(null); setEditDraft({}) }

  const saveEdit = async (userId) => {
    setSaving(true)
    try {
      const res = await apiFetch(`/api/admin/users/${userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editDraft),
      })
      if (res.ok) {
        cancelEdit()
        loadUsers()
      } else {
        const err = await res.json().catch(() => ({}))
        alert(err.error || 'فشل الحفظ')
      }
    } finally { setSaving(false) }
  }

  const deleteUser = async (u) => {
    if (!confirm(`هل أنت متأكد من حذف المستخدم ${u.email}؟\nسيتم حذف بياناته بالكامل ولا يمكن التراجع.`)) return
    try {
      const res = await apiFetch(`/api/admin/users/${u.id}`, { method: 'DELETE' })
      if (res.ok) loadUsers()
      else {
        const err = await res.json().catch(() => ({}))
        alert(err.error || 'فشل الحذف')
      }
    } catch (e) { alert('فشل الحذف: ' + e.message) }
  }

  return (
    <div className="space-y-4">
      {/* Toolbar: search + create button */}
      <div className="card p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
          <input
            type="text"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="ابحث بالاسم أو البريد الإلكتروني..."
            className="input"
            style={{ paddingRight: '2.25rem' }}
          />
        </div>
        <div className="text-xs text-slate-400 px-2">
          {total} مستخدم
        </div>
        <button onClick={() => setCreateOpen(true)} className="btn">
          <Plus className="w-4 h-4" />
          إضافة مستخدم
        </button>
      </div>

      {/* Users table */}
      <div className="card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" dir="rtl">
            <thead>
              <tr className="text-[11px] uppercase tracking-wider text-slate-500"
                  style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                <th className="text-right font-semibold px-4 py-3 w-8"></th>
                <th className="text-right font-semibold px-2 py-3">المستخدم</th>
                <th className="text-right font-semibold px-2 py-3 hidden md:table-cell">الصلاحية</th>
                <th className="text-right font-semibold px-2 py-3 hidden md:table-cell">الحالة</th>
                <th className="text-right font-semibold px-2 py-3 hidden lg:table-cell">الكلمات</th>
                <th className="text-right font-semibold px-2 py-3 hidden lg:table-cell">الأخبار</th>
                <th className="text-right font-semibold px-2 py-3 hidden xl:table-cell">تاريخ الإنشاء</th>
                <th className="text-right font-semibold px-4 py-3 w-[180px]">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {loading && users.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-400">
                  <Loader2 className="w-5 h-5 animate-spin inline-block" /> جاري التحميل...
                </td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-12 text-slate-400">لا توجد نتائج</td></tr>
              ) : users.map(u => {
                const isEdit = editingId === u.id
                const isOpen = expanded === u.id
                return (
                  <UserRow
                    key={u.id}
                    user={u}
                    isEdit={isEdit}
                    isOpen={isOpen}
                    editDraft={editDraft}
                    setEditDraft={setEditDraft}
                    saving={saving}
                    onToggleKeywords={() => toggleKeywords(u.id)}
                    onStartEdit={() => startEdit(u)}
                    onCancelEdit={cancelEdit}
                    onSaveEdit={() => saveEdit(u.id)}
                    onDelete={() => deleteUser(u)}
                    onPassword={() => setPasswordTarget(u)}
                    keywords={keywordsByUser[u.id]}
                    keywordsLoading={keywordsLoading === u.id}
                  />
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3"
            style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
            <div className="text-xs text-slate-400">
              صفحة {page} من {totalPages}
            </div>
            <Pager page={page} totalPages={totalPages} onChange={setPage} />
          </div>
        )}
      </div>

      {/* Modals */}
      {passwordTarget && (
        <PasswordModal
          user={passwordTarget}
          onClose={() => setPasswordTarget(null)}
          onSaved={() => { setPasswordTarget(null); loadUsers() }}
        />
      )}
      {createOpen && (
        <CreateUserModal
          onClose={() => setCreateOpen(false)}
          onCreated={() => { setCreateOpen(false); loadUsers() }}
        />
      )}
    </div>
  )
}

// ── A single user row (with inline edit + expandable keywords) ──
function UserRow({
  user: u, isEdit, isOpen, editDraft, setEditDraft, saving,
  onToggleKeywords, onStartEdit, onCancelEdit, onSaveEdit, onDelete, onPassword,
  keywords, keywordsLoading,
}) {
  return (
    <>
      <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
        {/* Expand toggle */}
        <td className="px-4 py-2.5 align-middle">
          <button
            onClick={onToggleKeywords}
            className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-slate-100 transition-colors"
            title="عرض الكلمات">
            {isOpen ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
          </button>
        </td>

        {/* User identity */}
        <td className="px-2 py-2.5 align-middle">
          {isEdit ? (
            <input
              className="input !py-1.5 !text-sm"
              value={editDraft.name || ''}
              onChange={e => setEditDraft(d => ({ ...d, name: e.target.value }))}
              placeholder="الاسم"
            />
          ) : (
            <div>
              <div className="font-semibold text-slate-900 text-sm">{u.name || '—'}</div>
              <div className="text-xs text-slate-400 mt-0.5">{u.email}</div>
            </div>
          )}
        </td>

        {/* Role */}
        <td className="px-2 py-2.5 align-middle hidden md:table-cell">
          {isEdit ? (
            <select className="input !py-1.5 !text-sm"
              value={editDraft.role}
              onChange={e => setEditDraft(d => ({ ...d, role: e.target.value }))}>
              <option value="USER">مستخدم</option>
              <option value="ADMIN">مسؤول</option>
            </select>
          ) : (
            <span className={`badge ${u.role === 'ADMIN' ? 'badge-positive' : 'badge-neutral'}`}>
              {u.role === 'ADMIN' ? <><ShieldCheck className="w-3 h-3" /> مسؤول</> : 'مستخدم'}
            </span>
          )}
        </td>

        {/* Active */}
        <td className="px-2 py-2.5 align-middle hidden md:table-cell">
          {isEdit ? (
            <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer">
              <input type="checkbox"
                checked={!!editDraft.is_active}
                onChange={e => setEditDraft(d => ({ ...d, is_active: e.target.checked }))} />
              نشط
            </label>
          ) : (
            <span className={`badge ${u.is_active ? 'badge-positive' : 'badge-negative'}`}>
              {u.is_active ? 'نشط' : 'معطّل'}
            </span>
          )}
        </td>

        {/* Keyword count */}
        <td className="px-2 py-2.5 align-middle hidden lg:table-cell text-slate-600 font-medium text-sm">
          {u.keyword_count}
        </td>

        {/* Article count */}
        <td className="px-2 py-2.5 align-middle hidden lg:table-cell text-slate-600 font-medium text-sm">
          {u.article_count?.toLocaleString('ar-EG') || 0}
        </td>

        {/* Created at */}
        <td className="px-2 py-2.5 align-middle hidden xl:table-cell text-xs text-slate-400">
          {u.created_at ? new Date(u.created_at).toLocaleDateString('ar-EG') : '—'}
        </td>

        {/* Actions */}
        <td className="px-4 py-2.5 align-middle">
          <div className="flex items-center gap-1">
            {isEdit ? (
              <>
                <IconBtn title="حفظ" onClick={onSaveEdit} disabled={saving} tone="primary">
                  {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                </IconBtn>
                <IconBtn title="إلغاء" onClick={onCancelEdit}>
                  <X className="w-3.5 h-3.5" />
                </IconBtn>
              </>
            ) : (
              <>
                <IconBtn title="تعديل" onClick={onStartEdit}>
                  <Pencil className="w-3.5 h-3.5" />
                </IconBtn>
                <IconBtn title="تغيير كلمة المرور" onClick={onPassword}>
                  <KeyRound className="w-3.5 h-3.5" />
                </IconBtn>
                <IconBtn title="حذف" onClick={onDelete} tone="danger">
                  <Trash2 className="w-3.5 h-3.5" />
                </IconBtn>
              </>
            )}
          </div>
        </td>
      </tr>

      {/* Expanded keywords row */}
      {isOpen && (
        <tr>
          <td colSpan={8} className="px-4 pb-4"
            style={{ background: 'rgba(0,0,0,0.015)' }}>
            <div className="pr-10 pt-3">
              <div className="text-xs font-semibold text-slate-500 mb-2">الكلمات المفتاحية ({keywords?.length ?? 0})</div>
              {keywordsLoading ? (
                <div className="text-xs text-slate-400 flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" /> جاري التحميل...
                </div>
              ) : !keywords?.length ? (
                <div className="text-xs text-slate-400">لا توجد كلمات لهذا المستخدم.</div>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {keywords.map(k => (
                    <span
                      key={k.id}
                      className="px-2.5 py-1 rounded-full text-xs font-medium"
                      style={{
                        background: k.enabled ? 'rgba(15,118,110,0.08)' : 'rgba(0,0,0,0.04)',
                        color: k.enabled ? '#0f766e' : '#94a3b8',
                      }}
                      title={k.enabled ? 'مفعّلة' : 'معطّلة'}>
                      {k.text_ar}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

function IconBtn({ children, tone, ...props }) {
  const base = 'w-7 h-7 rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
  const styles = {
    primary: { background: 'rgba(15,118,110,0.08)', color: '#0f766e' },
    danger:  { background: 'transparent', color: '#94a3b8' },
    default: { background: 'transparent', color: '#64748b' },
  }
  const s = tone === 'primary' ? styles.primary : tone === 'danger' ? styles.danger : styles.default
  return (
    <button {...props} className={base}
      style={{ ...s }}
      onMouseEnter={e => {
        if (tone === 'danger') { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#dc2626' }
        else if (tone !== 'primary') { e.currentTarget.style.background = 'rgba(0,0,0,0.04)' }
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = s.background
        e.currentTarget.style.color = s.color
      }}>
      {children}
    </button>
  )
}

// ── Page navigation buttons used by both tabs ─────────────────────
function Pager({ page, totalPages, onChange }) {
  const go = (p) => onChange(Math.max(1, Math.min(p, totalPages)))
  const btn = (p, label, title) => (
    <button
      key={`${title}-${p}`}
      onClick={() => go(p)}
      disabled={p === page}
      title={title}
      className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      style={{
        background: p === page ? '#0f766e' : 'rgba(0,0,0,0.02)',
        color: p === page ? '#fff' : '#475569',
        border: '1px solid rgba(0,0,0,0.05)',
      }}>
      {label}
    </button>
  )

  // Build page-number window
  const nums = []
  let start = Math.max(1, page - 2)
  let end = Math.min(totalPages, start + 4)
  start = Math.max(1, end - 4)
  for (let i = start; i <= end; i++) nums.push(i)

  return (
    <div className="flex items-center gap-1">
      <button onClick={() => go(1)} disabled={page === 1} title="أول صفحة"
        className="w-8 h-8 rounded-lg flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ background: 'rgba(0,0,0,0.02)', color: '#475569', border: '1px solid rgba(0,0,0,0.05)' }}>
        <ChevronsRight className="w-3.5 h-3.5" />
      </button>
      <button onClick={() => go(page - 1)} disabled={page === 1} title="السابق"
        className="w-8 h-8 rounded-lg flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ background: 'rgba(0,0,0,0.02)', color: '#475569', border: '1px solid rgba(0,0,0,0.05)' }}>
        <ChevronRight className="w-3.5 h-3.5" />
      </button>
      {nums.map(n => (
        <button key={n} onClick={() => go(n)}
          className="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-medium transition-colors"
          style={{
            background: n === page ? '#0f766e' : 'rgba(0,0,0,0.02)',
            color: n === page ? '#fff' : '#475569',
            border: '1px solid rgba(0,0,0,0.05)',
          }}>
          {n}
        </button>
      ))}
      <button onClick={() => go(page + 1)} disabled={page === totalPages} title="التالي"
        className="w-8 h-8 rounded-lg flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ background: 'rgba(0,0,0,0.02)', color: '#475569', border: '1px solid rgba(0,0,0,0.05)' }}>
        <ChevronLeft className="w-3.5 h-3.5" />
      </button>
      <button onClick={() => go(totalPages)} disabled={page === totalPages} title="آخر صفحة"
        className="w-8 h-8 rounded-lg flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ background: 'rgba(0,0,0,0.02)', color: '#475569', border: '1px solid rgba(0,0,0,0.05)' }}>
        <ChevronsLeft className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}


// ============================================================
// Create-user modal
// ============================================================
function CreateUserModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', email: '', role: 'USER', is_active: true, password: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e?.preventDefault()
    setError(null)
    if (!form.name.trim() || !form.email.trim()) {
      setError('الاسم والبريد الإلكتروني مطلوبان')
      return
    }
    setSaving(true)
    try {
      const res = await apiFetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.ok) onCreated()
      else {
        const err = await res.json().catch(() => ({}))
        setError(err.error || 'فشل الإنشاء')
      }
    } finally { setSaving(false) }
  }

  return (
    <Modal onClose={onClose} title="إضافة مستخدم جديد" icon={Plus}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="text-xs font-semibold text-slate-600 mb-1 block">الاسم</label>
          <input className="input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} autoFocus />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 mb-1 block">البريد الإلكتروني</label>
          <input type="email" className="input" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">الصلاحية</label>
            <select className="input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
              <option value="USER">مستخدم</option>
              <option value="ADMIN">مسؤول</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1 block">كلمة المرور</label>
            <input type="text" className="input" placeholder="اتركها فارغة للتوليد التلقائي"
              value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </div>
        </div>
        <label className="inline-flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <input type="checkbox" checked={form.is_active}
            onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))} />
          الحساب نشط
        </label>

        {error && (
          <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
            style={{ background: 'rgba(239,68,68,0.06)', color: '#b91c1c' }}>
            <AlertCircle className="w-3.5 h-3.5" /> {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2">
          <button type="button" className="btn-ghost" onClick={onClose}>إلغاء</button>
          <button type="submit" disabled={saving} className="btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            حفظ
          </button>
        </div>
      </form>
    </Modal>
  )
}


// ============================================================
// Password-change modal (admin sets a new password for a user)
// ============================================================
function PasswordModal({ user, onClose, onSaved }) {
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e?.preventDefault()
    setError(null)
    if (!pw || pw.length < 4) { setError('كلمة المرور قصيرة جداً'); return }
    if (pw !== confirm) { setError('كلمتا المرور غير متطابقتين'); return }
    setSaving(true)
    try {
      const res = await apiFetch(`/api/admin/users/${user.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw }),
      })
      if (res.ok) onSaved()
      else {
        const err = await res.json().catch(() => ({}))
        setError(err.error || 'فشل التغيير')
      }
    } finally { setSaving(false) }
  }

  return (
    <Modal onClose={onClose} title="تغيير كلمة المرور" icon={Lock} subtitle={user.email}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className="text-xs font-semibold text-slate-600 mb-1 block">كلمة المرور الجديدة</label>
          <input type="password" className="input" value={pw} onChange={e => setPw(e.target.value)} autoFocus />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 mb-1 block">تأكيد كلمة المرور</label>
          <input type="password" className="input" value={confirm} onChange={e => setConfirm(e.target.value)} />
        </div>
        {error && (
          <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg"
            style={{ background: 'rgba(239,68,68,0.06)', color: '#b91c1c' }}>
            <AlertCircle className="w-3.5 h-3.5" /> {error}
          </div>
        )}
        <div className="flex items-center justify-end gap-2 pt-2">
          <button type="button" className="btn-ghost" onClick={onClose}>إلغاء</button>
          <button type="submit" disabled={saving} className="btn">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            تغيير
          </button>
        </div>
      </form>
    </Modal>
  )
}


// ── Generic modal shell ───────────────────────────────────────────
function Modal({ onClose, title, subtitle, icon: Icon, children }) {
  // Close on Escape
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(15,23,42,0.45)', backdropFilter: 'blur(4px)' }}>
      <div
        onClick={e => e.stopPropagation()}
        className="card p-5 w-full max-w-md"
        style={{ background: '#ffffff' }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ background: 'rgba(15,118,110,0.08)' }}>
                <Icon className="w-4 h-4" style={{ color: '#0f766e' }} />
              </div>
            )}
            <div>
              <h2 className="font-bold text-slate-900 text-base">{title}</h2>
              {subtitle && <div className="text-xs text-slate-400 mt-0.5">{subtitle}</div>}
            </div>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-100 transition-colors">
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}


// ============================================================
// Activity log tab
// ============================================================
function ActivityLogTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')  // '' | 'auth' | 'keywords' | 'exports' | 'admin'
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  // Debounce search input
  const [debouncedQ, setDebouncedQ] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 250)
    return () => clearTimeout(t)
  }, [q])

  // Reset to page 1 whenever filters change
  useEffect(() => { setPage(1) }, [debouncedQ, category])

  const loadLogs = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(page), per_page: String(LOGS_PER_PAGE),
      })
      if (debouncedQ) params.set('q', debouncedQ)
      if (category) params.set('category', category)
      const res = await apiFetch(`/api/admin/audit?${params}`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs || [])
        setTotalPages(data.total_pages || 1)
        setTotal(data.total || 0)
        setLastRefresh(new Date())
      }
    } catch (e) {
      console.error('Failed to load audit logs:', e)
    } finally {
      if (!silent) setLoading(false)
    }
  }, [page, debouncedQ, category])

  useEffect(() => { loadLogs() }, [loadLogs])

  // Auto-refresh only on page 1 (so we don't fight with the user's
  // navigation through older pages).
  useEffect(() => {
    if (!autoRefresh || page !== 1) return
    const id = setInterval(() => loadLogs(true), LOGS_AUTOREFRESH_MS)
    return () => clearInterval(id)
  }, [autoRefresh, page, loadLogs])

  const categories = [
    { id: '',         label: 'الكل' },
    { id: 'auth',     label: 'تسجيل دخول وحساب' },
    { id: 'keywords', label: 'الكلمات' },
    { id: 'exports',  label: 'التصدير' },
    { id: 'admin',    label: 'إجراءات المسؤول' },
  ]

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="ابحث باسم المستخدم أو البريد..."
              className="input"
              style={{ paddingRight: '2.25rem' }}
            />
          </div>
          <div className="text-xs text-slate-400 px-2">
            {total} حدث
          </div>
          <label className="inline-flex items-center gap-2 text-xs font-medium text-slate-600 cursor-pointer select-none">
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} />
            تحديث تلقائي
          </label>
          <button onClick={() => loadLogs()} className="btn-ghost !px-2.5 !py-1.5" title="تحديث">
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Category filter pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {categories.map(c => (
            <button
              key={c.id || 'all'}
              onClick={() => setCategory(c.id)}
              className="px-3 py-1 rounded-full text-xs font-semibold transition-all"
              style={{
                background: category === c.id ? '#0f766e' : 'rgba(0,0,0,0.04)',
                color: category === c.id ? '#fff' : '#475569',
              }}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {/* Log list */}
      <div className="card p-0 overflow-hidden">
        {loading && logs.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin inline-block" /> جاري التحميل...
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-12 text-slate-400">لا توجد أحداث مطابقة</div>
        ) : (
          <div>
            {logs.map(log => <LogRow key={log.id} log={log} />)}
          </div>
        )}

        {/* Pagination + footer */}
        {(totalPages > 1 || lastRefresh) && (
          <div className="flex items-center justify-between flex-wrap gap-3 px-4 py-3"
            style={{ borderTop: '1px solid rgba(0,0,0,0.04)' }}>
            <div className="text-xs text-slate-400">
              {totalPages > 1 ? <>صفحة {page} من {totalPages}</> : null}
              {lastRefresh && (
                <span className="mx-2 text-slate-300">
                  · آخر تحديث {lastRefresh.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
              )}
            </div>
            {totalPages > 1 && <Pager page={page} totalPages={totalPages} onChange={setPage} />}
          </div>
        )}
      </div>
    </div>
  )
}

function LogRow({ log }) {
  const r = useMemo(() => renderAction(log), [log])
  const tone = TONE_COLOR[r.tone] || TONE_COLOR.auth
  const Icon = r.icon || Activity

  // Prefer the acting user; fall back to admin id (admin actions where
  // user_id == admin_id, or rare cases where user was deleted).
  const actor = log.user || log.admin
  const actorName = actor?.name || actor?.email || 'مستخدم محذوف'
  const actorEmail = actor?.email && actor.email !== actorName ? actor.email : null

  // For admin-on-user actions where admin acted on someone else, show
  // a small "by admin X" suffix to keep accountability clear.
  const isAdminAction = log.admin && log.user && log.admin.id !== log.user.id
  const adminLabel = isAdminAction
    ? `(بواسطة ${log.admin.name || log.admin.email})`
    : null

  return (
    <div className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
      style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
      <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: tone.bg, color: tone.fg }}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-slate-800 leading-relaxed">
          <span className="font-bold">{actorName}</span>
          {actorEmail && <span className="text-xs text-slate-400 mx-1">({actorEmail})</span>}
          <span className="text-slate-600 mx-1">{r.verb}</span>
          {r.target && <span className="text-slate-900 font-medium">{r.target}</span>}
          {adminLabel && <span className="text-xs text-slate-400 mx-1.5">{adminLabel}</span>}
        </div>
        <div className="text-[11px] text-slate-400 mt-0.5" title={absoluteTime(log.created_at)}>
          {relativeTime(log.created_at)}
        </div>
      </div>
    </div>
  )
}
