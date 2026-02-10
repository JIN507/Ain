import { useEffect, useState } from 'react'
import { apiFetch } from '../apiClient'

export default function Admin() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: 'USER', password: '' })
  const [passwordModal, setPasswordModal] = useState({ open: false, userId: null, userName: '', newPassword: '' })

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
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الاسم</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">المستخدم</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الدور</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">الحالة</th>
                <th className="py-2.5 px-3 text-right font-semibold text-slate-500">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid rgba(0,0,0,0.03)' }} className="hover:bg-slate-50/50">
                  <td className="py-2 px-3">
                    <input type="text" defaultValue={u.name || ''}
                      className="w-full bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onBlur={(e) => e.target.value !== (u.name || '') && handleChangeUser(u.id, { name: e.target.value })} />
                  </td>
                  <td className="py-2 px-3">
                    <input type="email" defaultValue={u.email}
                      className="w-full bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onBlur={(e) => e.target.value !== u.email && handleChangeUser(u.id, { email: e.target.value })} />
                  </td>
                  <td className="py-2 px-3">
                    <select defaultValue={u.role}
                      className="bg-transparent border border-transparent hover:border-slate-200 rounded-lg px-2 py-1 text-xs transition"
                      onChange={(e) => handleChangeUser(u.id, { role: e.target.value })}>
                      <option value="USER">مستخدم</option>
                      <option value="ADMIN">مسؤول</option>
                    </select>
                  </td>
                  <td className="py-2 px-3">
                    <button
                      onClick={() => handleChangeUser(u.id, { is_active: !u.is_active })}
                      className="badge cursor-pointer"
                      style={u.is_active
                        ? { background: 'rgba(20,184,166,0.1)', color: '#0f766e' }
                        : { background: 'rgba(0,0,0,0.04)', color: '#94a3b8' }}>
                      {u.is_active ? 'مفعل' : 'معلّق'}
                    </button>
                  </td>
                  <td className="py-2 px-3">
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
