import { useState } from 'react'
import { motion } from 'framer-motion'
import { Eye, Loader2 } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function Login({ onLogin, onSwitchToRegister }) {
  const [mode, setMode] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')

    if (!email || !password) {
      setError('يرجى إدخال البريد الإلكتروني وكلمة المرور')
      return
    }

    setLoading(true)
    try {
      await onLogin(email, password)
    } catch (err) {
      setError(err.message || 'حدث خطأ غير متوقع')
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')

    if (!name || !email || !password) {
      setError('يرجى إدخال الاسم والبريد الإلكتروني وكلمة المرور')
      return
    }

    setLoading(true)
    try {
      const res = await apiFetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.error || 'فشل إنشاء الحساب')
        return
      }
      setInfo('تم إرسال طلب التسجيل، سيتم تفعيل الحساب بعد موافقة المسؤول')
      setPassword('')
    } catch (err) {
      setError('حدث خطأ غير متوقع')
    } finally {
      setLoading(false)
    }
  }

  const inputClass = "w-full rounded-xl px-4 py-3 text-sm transition-all duration-200 bg-white focus:outline-none focus:ring-0"

  return (
    <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center px-4" style={{ background: '#f8fafc' }}>
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
            <p className="text-xs text-slate-400 mt-1 font-medium">
              {mode === 'login' ? 'تسجيل الدخول إلى حسابك' : 'إنشاء حساب جديد'}
            </p>
          </div>

          {/* Mode Toggle */}
          <div className="flex mb-6 rounded-xl p-1 text-xs font-semibold" style={{ background: 'rgba(0,0,0,0.03)' }}>
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); setInfo('') }}
              className={`flex-1 py-2 rounded-lg transition-all duration-200 ${
                mode === 'login'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              تسجيل الدخول
            </button>
            <button
              type="button"
              onClick={() => {
                if (onSwitchToRegister) { onSwitchToRegister() }
                else { setMode('signup'); setError(''); setInfo('') }
              }}
              className={`flex-1 py-2 rounded-lg transition-all duration-200 ${
                mode === 'signup'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              حساب جديد
            </button>
          </div>

          <form onSubmit={mode === 'login' ? handleLogin : handleSignup} className="space-y-4">
            {mode === 'signup' && (
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1.5">الاسم الكامل</label>
                <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                  className={inputClass} placeholder="الاسم" autoComplete="name"
                  style={{ border: '1.5px solid rgba(0,0,0,0.08)' }}
                  onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'}
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">اسم المستخدم</label>
              <input type="text" value={email} onChange={(e) => setEmail(e.target.value)}
                className={inputClass} placeholder="اسم المستخدم" autoComplete="username"
                style={{ border: '1.5px solid rgba(0,0,0,0.08)' }}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-500 mb-1.5">كلمة المرور</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className={inputClass} placeholder="••••••"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                style={{ border: '1.5px solid rgba(0,0,0,0.08)' }}
                onFocus={(e) => e.target.style.borderColor = '#14b8a6'}
                onBlur={(e) => e.target.style.borderColor = 'rgba(0,0,0,0.08)'}
              />
            </div>

            {error && (
              <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                className="text-xs text-rose-600 rounded-xl px-3 py-2.5"
                style={{ background: 'rgba(225,29,72,0.06)' }}>
                {error}
              </motion.div>
            )}

            {info && (
              <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }}
                className="text-xs rounded-xl px-3 py-2.5"
                style={{ background: 'rgba(20,184,166,0.08)', color: '#0f766e' }}>
                {info}
              </motion.div>
            )}

            <button type="submit" disabled={loading} className="btn w-full !py-3 !text-sm !rounded-xl">
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                mode === 'login' ? 'تسجيل الدخول' : 'إنشاء حساب جديد'
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-[11px] text-slate-400">
            الوصول الكامل يتم بعد موافقة المسؤول
          </p>
        </div>
      </motion.div>
    </div>
  )
}
