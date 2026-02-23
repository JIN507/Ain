import { useEffect, useState } from 'react'
import { ChevronDown, ChevronLeft, Key, FileText } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Admin() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: 'USER', password: '' })
  const [passwordModal, setPasswordModal] = useState({ open: false, userId: null, userName: '', newPassword: '' })
  const [expandedUser, setExpandedUser] = useState(null)
  const [userKeywords, setUserKeywords] = useState({})
  const [loadingKeywords, setLoadingKeywords] = useState(null)

  const loadUsers = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/admin/users')
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل تحميل المستخدمين')
      }
      const data = await res.json()
      setUsers(data)
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const toggleExpand = async (userId) => {
    if (expandedUser === userId) {
      setExpandedUser(null)
      return
    }
    setExpandedUser(userId)
    if (!userKeywords[userId]) {
      setLoadingKeywords(userId)
      try {
        const res = await apiFetch(`/api/admin/users/${userId}/keywords`)
        if (res.ok) {
          const data = await res.json()
          setUserKeywords(prev => ({ ...prev, [userId]: data.keywords }))
        }
      } catch (e) {
        console.error('Failed to load keywords:', e)
      } finally {
        setLoadingKeywords(null)
      }
    }
  }

  const handleChangeUser = async (id, changes) => {
    try {
      const res = await apiFetch(`/api/admin/users/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(changes),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل تحديث المستخدم')
      }
      await loadUsers()
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const handleDeleteUser = async (id) => {
    if (!window.confirm('هل أنت متأكد من حذف هذا المستخدم؟')) return
    try {
      const res = await apiFetch(`/api/admin/users/${id}`, { method: 'DELETE' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل حذف المستخدم')
      }
      await loadUsers()
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const handlePasswordChange = async () => {
    if (!passwordModal.newPassword.trim()) {
      setError('يرجى إدخال كلمة المرور الجديدة')
      return
    }
    try {
      const res = await apiFetch(`/api/admin/users/${passwordModal.userId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: passwordModal.newPassword }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'فشل تغيير كلمة المرور')
      }
      setPasswordModal({ open: false, userId: null, userName: '', newPassword: '' })
      setError('')
      await loadUsers()
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setCreating(true)
    setError('')
    try {
      const res = await apiFetch('/api/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          email: form.email,
          role: form.role,
          password: form.password,
          is_active: true,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || 'فشل إنشاء المستخدم')
      }
      setForm({ name: '', email: '', role: 'USER', password: '' })
      await loadUsers()
    } catch (e) {
      setError(e.message || 'خطأ غير متوقع')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">لوحة الإدارة</h1>
        <p className="text-sm text-slate-500 mt-0.5">إدارة المستخدمين وصلاحيات الوصول</p>
      </div>

      {error && (
        <div className="rounded-xl px-4 py-3 text-sm" style={{ background: 'rgba(225,29,72,0.06)', color: '#e11d48' }}>
          {error}
        </div>
      )}

      {/* Create user */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">إضافة مستخدم جديد</h2>
        <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">الاسم</label>
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">اسم المستخدم</label>
            <input type="text" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input" />
          </div>
          <div>
            <label className="block text-[11px] font-medium text-slate-500 mb-1">الدور</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input">
              <option value="USER">مستخدم</option>
              <option value="ADMIN">مسؤول</option>
            </select>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-end">
            <div className="flex-1">
              <label className="block text-[11px] font-medium text-slate-500 mb-1">كلمة المرور</label>
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="input" placeholder="اتركها فارغة لـ 0000" />
            </div>
            <button type="submit" disabled={creating} className="btn !py-2.5 mt-2 md:mt-0">
              {creating ? 'جاري...' : 'إضافة'}
            </button>
          </div>
        </form>
      </div>

      {/* Users table */}
      <div className="card p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">المستخدمون</h2>
        {loading ? (
          <div className="text-xs text-slate-400 py-4">جاري التحميل...</div>
        ) : users.length === 0 ? (
          <div className="text-xs text-slate-400 py-4">لا يوجد مستخدمون</div>
        ) : (
          <table className="min-w-full text-xs">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500 w-8"></th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الاسم</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">المستخدم</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الدور</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الكلمات</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">المقالات</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الحالة</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <>
                <tr key={u.id} style={{ borderBottom: expandedUser === u.id ? 'none' : '1px solid rgba(0,0,0,0.03)' }}
                    className={`hover:bg-slate-50/50 cursor-pointer ${expandedUser === u.id ? 'bg-slate-50/80' : ''}`}
                    onClick={() => toggleExpand(u.id)}>
                  <td className="py-2 px-2 text-center">
                    {expandedUser === u.id
                      ? <ChevronDown className="w-3.5 h-3.5 text-teal-600 inline" />
                      : <ChevronLeft className="w-3.5 h-3.5 text-slate-400 inline" />
                    }
                  </td>
                  <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                    <input type="text" defaultValue={u.name || ''}
                      className="w-full bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onBlur={(e) => e.target.value !== (u.name || '') && handleChangeUser(u.id, { name: e.target.value })} />
                  </td>
                  <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                    <input type="email" defaultValue={u.email}
                      className="w-full bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onBlur={(e) => e.target.value !== u.email && handleChangeUser(u.id, { email: e.target.value })} />
                  </td>
                  <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                    <select defaultValue={u.role}
                      className="bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onChange={(e) => handleChangeUser(u.id, { role: e.target.value })}>
                      <option value="USER">مستخدم</option>
                      <option value="ADMIN">مسؤول</option>
                    </select>
                  </td>
                  <td className="py-2 px-3">
                    <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: u.keyword_count > 0 ? '#0f766e' : '#94a3b8' }}>
                      <Key className="w-3 h-3" />
                      {u.keyword_count || 0}
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: u.article_count > 0 ? '#2563eb' : '#94a3b8' }}>
                      <FileText className="w-3 h-3" />
                      {u.article_count || 0}
                    </span>
                  </td>
                  <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => handleChangeUser(u.id, { is_active: !u.is_active })}
                      className="badge cursor-pointer"
                      style={u.is_active
                        ? { background: 'rgba(20,184,166,0.1)', color: '#0f766e' }
                        : { background: 'rgba(0,0,0,0.04)', color: '#94a3b8' }}>
                      {u.is_active ? 'مفعل' : 'معلّق'}
                    </button>
                  </td>
                  <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => setPasswordModal({ open: true, userId: u.id, userName: u.name || u.email, newPassword: '' })}
                        className="btn-ghost !px-2 !py-1 !text-[11px]" style={{ color: '#2563eb' }}>
                        كلمة المرور
                      </button>
                      <button onClick={() => handleDeleteUser(u.id)}
                        className="btn-ghost !px-2 !py-1 !text-[11px]" style={{ color: '#94a3b8' }}
                        onMouseEnter={(e) => e.currentTarget.style.color = '#e11d48'}
                        onMouseLeave={(e) => e.currentTarget.style.color = '#94a3b8'}>
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>

                {/* Expanded keywords row */}
                {expandedUser === u.id && (
                  <tr key={`kw-${u.id}`} style={{ borderBottom: '1px solid rgba(0,0,0,0.06)' }}>
                    <td colSpan={8} className="px-4 pb-4 pt-1">
                      <div className="rounded-xl p-4" style={{ background: 'rgba(15,23,42,0.02)', border: '1px solid rgba(0,0,0,0.04)' }}>
                        <div className="flex items-center gap-2 mb-3">
                          <Key className="w-3.5 h-3.5 text-teal-600" />
                          <span className="text-xs font-semibold text-slate-700">كلمات المستخدم: {u.name || u.email}</span>
                        </div>
                        {loadingKeywords === u.id ? (
                          <div className="text-[11px] text-slate-400 py-2">جاري تحميل الكلمات...</div>
                        ) : !userKeywords[u.id] || userKeywords[u.id].length === 0 ? (
                          <div className="text-[11px] text-slate-400 py-2">لا توجد كلمات مفتاحية لهذا المستخدم</div>
                        ) : (
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                            {userKeywords[u.id].map((kw) => (
                              <div key={kw.id} className="flex items-center justify-between rounded-lg px-3 py-2.5"
                                style={{ background: 'rgba(255,255,255,0.8)', border: '1px solid rgba(0,0,0,0.04)' }}>
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className={`inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 ${kw.enabled ? 'bg-teal-500' : 'bg-slate-300'}`} />
                                  <div className="min-w-0">
                                    <div className="text-xs font-semibold text-slate-800 truncate">{kw.text_ar}</div>
                                    {kw.text_en && <div className="text-[10px] text-slate-400 truncate">{kw.text_en}</div>}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0 mr-2">
                                  <span className="badge text-[10px]" style={{
                                    background: kw.has_translations ? 'rgba(20,184,166,0.08)' : 'rgba(239,68,68,0.08)',
                                    color: kw.has_translations ? '#0f766e' : '#dc2626',
                                  }}>
                                    {kw.has_translations ? 'مترجمة' : 'غير مترجمة'}
                                  </span>
                                  <span className="text-[10px] font-medium" style={{ color: kw.article_count > 0 ? '#2563eb' : '#94a3b8' }}>
                                    {kw.article_count} مقال
                                  </span>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Password Change Modal */}
      {passwordModal.open && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-sm mx-4">
            <h3 className="text-sm font-semibold text-slate-900 mb-4">
              تغيير كلمة المرور: {passwordModal.userName}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-medium text-slate-500 mb-1">كلمة المرور الجديدة</label>
                <input type="password" value={passwordModal.newPassword}
                  onChange={(e) => setPasswordModal({ ...passwordModal, newPassword: e.target.value })}
                  className="input" placeholder="أدخل كلمة المرور الجديدة" autoFocus />
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setPasswordModal({ open: false, userId: null, userName: '', newPassword: '' })}
                  className="btn-ghost">إلغاء</button>
                <button onClick={handlePasswordChange} className="btn">حفظ</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
