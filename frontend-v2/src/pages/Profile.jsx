import { useState } from 'react'
import { User, Lock, Loader2, Check, AlertCircle, ArrowRight } from 'lucide-react'
import { apiFetch } from '../apiClient'
import { useAuth } from '../context/AuthContext'

export default function Profile({ onBack }) {
  const { currentUser, refreshUser } = useAuth()

  // Name form
  const [name, setName] = useState(currentUser?.name || '')
  const [nameSaving, setNameSaving] = useState(false)
  const [nameMsg, setNameMsg] = useState(null)

  // Password form
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState(null)

  const handleNameSave = async (e) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) {
      setNameMsg({ type: 'error', text: 'الاسم مطلوب' })
      return
    }
    if (trimmed === currentUser?.name) {
      setNameMsg({ type: 'info', text: 'لم يتغير الاسم' })
      return
    }
    setNameSaving(true)
    setNameMsg(null)
    try {
      const res = await apiFetch('/api/auth/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: trimmed }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'فشل التحديث')
      setNameMsg({ type: 'success', text: 'تم تحديث الاسم بنجاح' })
      await refreshUser()
    } catch (err) {
      setNameMsg({ type: 'error', text: err.message })
    } finally {
      setNameSaving(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (!oldPassword || !newPassword) {
      setPwMsg({ type: 'error', text: 'جميع الحقول مطلوبة' })
      return
    }
    if (newPassword !== confirmPassword) {
      setPwMsg({ type: 'error', text: 'كلمة المرور الجديدة غير متطابقة' })
      return
    }
    const pwErrors = []
    if (newPassword.length < 8) pwErrors.push('8 أحرف على الأقل')
    if (!/[A-Z]/.test(newPassword)) pwErrors.push('حرف كبير واحد على الأقل')
    if (!/[a-z]/.test(newPassword)) pwErrors.push('حرف صغير واحد على الأقل')
    if (!/[!@#$%&*\-]/.test(newPassword)) pwErrors.push('رمز خاص واحد على الأقل (!@#$%&*-)')
    if (pwErrors.length > 0) {
      setPwMsg({ type: 'error', text: 'يجب أن تحتوي كلمة المرور على: ' + pwErrors.join(' و') })
      return
    }
    setPwSaving(true)
    setPwMsg(null)
    try {
      const res = await apiFetch('/api/auth/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'فشل تغيير كلمة المرور')
      setPwMsg({ type: 'success', text: 'تم تغيير كلمة المرور بنجاح' })
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setPwMsg({ type: 'error', text: err.message })
    } finally {
      setPwSaving(false)
    }
  }

  const msgStyle = (type) => {
    if (type === 'success') return { background: 'rgba(20,184,166,0.08)', color: '#0f766e' }
    if (type === 'error') return { background: 'rgba(225,29,72,0.08)', color: '#e11d48' }
    return { background: 'rgba(100,116,139,0.08)', color: '#64748b' }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        {onBack && (
          <button onClick={onBack} className="btn-ghost !p-2">
            <ArrowRight className="w-5 h-5" />
          </button>
        )}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">الملف الشخصي</h1>
          <p className="text-sm text-slate-500 mt-0.5">{currentUser?.email}</p>
        </div>
      </div>

      {/* Name Card */}
      <form onSubmit={handleNameSave} className="card p-6 space-y-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(15,118,110,0.08)' }}>
            <User className="w-4.5 h-4.5" style={{ color: '#0f766e' }} />
          </div>
          <h2 className="text-base font-semibold text-slate-900">الاسم</h2>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1.5">الاسم الحالي</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="أدخل اسمك"
            className="w-full px-4 py-2.5 rounded-xl text-sm border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
            style={{ background: 'rgba(0,0,0,0.02)', borderColor: 'rgba(0,0,0,0.08)' }}
            maxLength={100}
          />
        </div>

        {nameMsg && (
          <div className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-medium" style={msgStyle(nameMsg.type)}>
            {nameMsg.type === 'success' ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {nameMsg.text}
          </div>
        )}

        <button type="submit" disabled={nameSaving} className="btn !text-sm">
          {nameSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          حفظ الاسم
        </button>
      </form>

      {/* Password Card */}
      <form onSubmit={handlePasswordChange} className="card p-6 space-y-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'rgba(139,92,246,0.08)' }}>
            <Lock className="w-4.5 h-4.5" style={{ color: '#7c3aed' }} />
          </div>
          <h2 className="text-base font-semibold text-slate-900">تغيير كلمة المرور</h2>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1.5">كلمة المرور الحالية</label>
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            placeholder="أدخل كلمة المرور الحالية"
            className="w-full px-4 py-2.5 rounded-xl text-sm border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            style={{ background: 'rgba(0,0,0,0.02)', borderColor: 'rgba(0,0,0,0.08)' }}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1.5">كلمة المرور الجديدة</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="8 أحرف على الأقل"
            className="w-full px-4 py-2.5 rounded-xl text-sm border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            style={{ background: 'rgba(0,0,0,0.02)', borderColor: 'rgba(0,0,0,0.08)' }}
            minLength={8}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1.5">تأكيد كلمة المرور الجديدة</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="أعد كتابة كلمة المرور الجديدة"
            className="w-full px-4 py-2.5 rounded-xl text-sm border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-400"
            style={{ background: 'rgba(0,0,0,0.02)', borderColor: 'rgba(0,0,0,0.08)' }}
            minLength={8}
          />
        </div>

        {pwMsg && (
          <div className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-medium" style={msgStyle(pwMsg.type)}>
            {pwMsg.type === 'success' ? <Check className="w-3.5 h-3.5" /> : <AlertCircle className="w-3.5 h-3.5" />}
            {pwMsg.text}
          </div>
        )}

        <button type="submit" disabled={pwSaving} className="btn !text-sm" style={{ background: 'linear-gradient(135deg, #bd4224 0%, #f35208 100%)' }}>
          {pwSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
          تغيير كلمة المرور
        </button>
      </form>
    </div>
  )
}
