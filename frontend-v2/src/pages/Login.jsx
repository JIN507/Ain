import { useState } from 'react'

export default function Login({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' or 'signup'
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
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      })

      const data = await res.json()

      if (!res.ok) {
        setError(data.error || 'فشل تسجيل الدخول')
        return
      }

      if (onLogin) {
        onLogin(data)
      }
    } catch (err) {
      setError('حدث خطأ غير متوقع')
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
      const res = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
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

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-gradient-to-br from-emerald-50 to-green-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-white/90 backdrop-blur shadow-xl rounded-2xl p-8 border border-emerald-100">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-extrabold text-emerald-700 tracking-tight mb-2">
              نظام أخبار عين
            </h1>
            <p className="text-gray-600 text-sm">
              {mode === 'login'
                ? 'تسجيل الدخول باستخدام اسم المستخدم وكلمة المرور'
                : 'إنشاء حساب جديد وطلب الوصول من المسؤول'}
            </p>
          </div>
          <div className="flex mb-6 rounded-xl bg-emerald-50 p-1 text-sm">
            <button
              type="button"
              onClick={() => { setMode('login'); setError(''); setInfo('') }}
              className={`flex-1 py-2 rounded-lg ${mode === 'login' ? 'bg-white text-emerald-700 font-semibold shadow-sm' : 'text-emerald-600'}`}
            >
              تسجيل الدخول
            </button>
            <button
              type="button"
              onClick={() => { setMode('signup'); setError(''); setInfo('') }}
              className={`flex-1 py-2 rounded-lg ${mode === 'signup' ? 'bg-white text-emerald-700 font-semibold shadow-sm' : 'text-emerald-600'}`}
            >
              إنشاء حساب
            </button>
          </div>

          <form onSubmit={mode === 'login' ? handleLogin : handleSignup} className="space-y-5">
            {mode === 'signup' && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-700">
                  الاسم الكامل
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-gray-50"
                  placeholder="الاسم"
                  autoComplete="name"
                />
              </div>
            )}

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                اسم المستخدم
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-gray-50"
                placeholder="اسم المستخدم"
                autoComplete="username"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                كلمة المرور
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 bg-gray-50"
                placeholder="••••"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-3 py-2">
                {error}
              </div>
            )}

            {info && (
              <div className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
                {info}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold py-2.5 transition disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading
                ? (mode === 'login' ? 'جاري تسجيل الدخول...' : 'جاري إنشاء الحساب...')
                : (mode === 'login' ? 'تسجيل الدخول' : 'إنشاء حساب جديد')}
            </button>
          </form>

          <div className="mt-6 text-xs text-center text-gray-400">
            الوصول الكامل يتم بعد موافقة المسؤول
          </div>
        </div>
      </div>
    </div>
  )
}
