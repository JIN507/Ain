import { useState } from 'react'
import { motion } from 'framer-motion'
import { Eye, CheckCircle, Loader2 } from 'lucide-react'

export default function Register({ onRegister, onSwitchToLogin }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) { setError('يرجى إدخال الاسم'); return }
    if (!email.trim()) { setError('يرجى إدخال اسم المستخدم'); return }
    if (!password) { setError('يرجى إدخال كلمة المرور'); return }
    if (password !== confirmPassword) { setError('كلمة المرور غير متطابقة'); return }
    if (password.length < 4) { setError('كلمة المرور يجب أن تكون 4 أحرف على الأقل'); return }

    setLoading(true)
    try {
      await onRegister(name, email, password)
      setSuccess(true)
    } catch (e) {
      setError(e.message || 'فشل إنشاء الحساب')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full rounded-xl px-4 py-3 text-sm transition-all duration-200 bg-white focus:outline-none focus:ring-0"
  const inputStyle = { border: '1.5px solid rgba(0,0,0,0.08)' }

  if (success) {
    return (
      <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center font-cairo p-4" style={{ background: '#f8fafc' }}>
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="w-full max-w-sm">
          <div className="card p-8 text-center">
            <div className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
              style={{ background: 'rgba(20,184,166,0.1)' }}>
              <CheckCircle className="w-7 h-7 text-teal-600" />
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">تم إنشاء الحساب بنجاح</h2>
            <p className="text-sm text-slate-500 mb-6">حسابك قيد المراجعة. سيتم إعلامك عند التفعيل.</p>
            <button onClick={onSwitchToLogin} className="btn w-full !py-3">العودة لتسجيل الدخول</button>
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center font-cairo p-4" style={{ background: '#f8fafc' }}>
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        className="w-full max-w-sm"
      >
        <div className="card p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
              style={{
                background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
                boxShadow: '0 6px 20px rgba(20,184,166,0.3)',
              }}>
              <Eye className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">عين</h1>
            <p className="text-xs text-slate-400 mt-1 font-medium">إنشاء حساب جديد</p>
          </div>

          {error && (
            <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
              className="text-xs text-rose-600 rounded-xl px-3 py-2.5 mb-4"
              style={{ background: 'rgba(225,29,72,0.06)' }}>
              {error}
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">الاسم</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                className={inputClass} placeholder="الاسم الكامل" style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">اسم المستخدم</label>
              <input type="text" value={email} onChange={(e) => setEmail(e.target.value)}
                className={inputClass} placeholder="اسم المستخدم" style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">كلمة المرور</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className={inputClass} placeholder="أدخل كلمة المرور" style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'} />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">تأكيد كلمة المرور</label>
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                className={inputClass} placeholder="أعد إدخال كلمة المرور" style={inputStyle}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'} />
            </div>
            <button type="submit" disabled={loading} className="btn w-full !py-3 !text-sm !rounded-xl">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'إنشاء حساب'}
            </button>
          </form>

          <div className="mt-5 text-center">
            <p className="text-xs text-slate-400">
              لديك حساب؟{' '}
              <button onClick={onSwitchToLogin} className="font-semibold" style={{ color: '#0f766e' }}>
                تسجيل الدخول
              </button>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
