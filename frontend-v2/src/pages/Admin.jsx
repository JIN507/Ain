import { useEffect, useState } from 'react'
import { apiFetch } from '../apiClient'

export default function Admin() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', role: 'USER', password: '' })

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900">لوحة الإدارة</h1>
          <p className="text-gray-600 mt-1">إدارة المستخدمين وصلاحيات الوصول</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3">
          {error}
        </div>
      )}

      {/* Create user */}
      <div className="card p-4 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">إضافة مستخدم جديد</h2>
        <form onSubmit={handleCreateUser} className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">الاسم</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">اسم المستخدم</label>
            <input
              type="text"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">الدور</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            >
              <option value="USER">مستخدم</option>
              <option value="ADMIN">مسؤول</option>
            </select>
          </div>
          <div className="flex flex-col gap-2 md:flex-row md:items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-700 mb-1">كلمة المرور المبدئية</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="اتركها فارغة لاستخدام 0000"
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="md:w-32 h-10 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold mt-2 md:mt-0 disabled:opacity-60"
            >
              {creating ? 'جاري الإضافة...' : 'إضافة'}
            </button>
          </div>
        </form>
      </div>

      {/* Users table */}
      <div className="card p-4 overflow-x-auto">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">جميع المستخدمين</h2>
        {loading ? (
          <div className="text-sm text-gray-500">جاري التحميل...</div>
        ) : users.length === 0 ? (
          <div className="text-sm text-gray-500">لا يوجد مستخدمون حتى الآن</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="py-2 px-3 text-right font-semibold text-gray-700">الاسم</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">اسم المستخدم</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">الدور</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">الحالة</th>
                <th className="py-2 px-3 text-right font-semibold text-gray-700">إجراءات</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-2 px-3">
                    <input
                      type="text"
                      defaultValue={u.name || ''}
                      className="w-full bg-transparent border border-transparent hover:border-gray-200 rounded px-2 py-1 text-xs"
                      onBlur={(e) =>
                        e.target.value !== (u.name || '') &&
                        handleChangeUser(u.id, { name: e.target.value })
                      }
                    />
                  </td>
                  <td className="py-2 px-3">
                    <input
                      type="email"
                      defaultValue={u.email}
                      className="w-full bg-transparent border border-transparent hover:border-gray-200 rounded px-2 py-1 text-xs"
                      onBlur={(e) =>
                        e.target.value !== u.email &&
                        handleChangeUser(u.id, { email: e.target.value })
                      }
                    />
                  </td>
                  <td className="py-2 px-3">
                    <select
                      defaultValue={u.role}
                      className="bg-white border border-gray-200 rounded px-2 py-1 text-xs"
                      onChange={(e) => handleChangeUser(u.id, { role: e.target.value })}
                    >
                      <option value="USER">مستخدم</option>
                      <option value="ADMIN">مسؤول</option>
                    </select>
                  </td>
                  <td className="py-2 px-3">
                    <button
                      onClick={() => handleChangeUser(u.id, { is_active: !u.is_active })}
                      className={`px-3 py-1 rounded-full text-xs font-semibold border ${
                        u.is_active
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-gray-50 text-gray-500 border-gray-200'
                      }`}
                    >
                      {u.is_active ? 'مفعل' : 'معلّق'}
                    </button>
                  </td>
                  <td className="py-2 px-3 space-x-1 space-x-reverse">
                    <button
                      onClick={() =>
                        handleChangeUser(u.id, { reset_password: true })
                      }
                      className="inline-flex items-center px-2 py-1 rounded-md bg-blue-50 text-blue-700 border border-blue-200 text-xs mr-1"
                    >
                      إعادة تعيين كلمة المرور (0000)
                    </button>
                    <button
                      onClick={() => handleDeleteUser(u.id)}
                      className="inline-flex items-center px-2 py-1 rounded-md bg-red-50 text-red-700 border border-red-200 text-xs"
                    >
                      حذف
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
