import { useState } from 'react'
import { Newspaper, CheckCircle } from 'lucide-react'

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

    if (!name.trim()) {
      setError('يرجى إدخال الاسم')
      return
    }
    if (!email.trim()) {
      setError('يرجى إدخال اسم المستخدم')
      return
    }
    if (!password) {
      setError('يرجى إدخال كلمة المرور')
      return
    }
    if (password !== confirmPassword) {
      setError('كلمة المرور غير متطابقة')
      return
    }
    if (password.length < 4) {
      setError('كلمة المرور يجب أن تكون 4 أحرف على الأقل')
      return
    }

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

  // Show success message after registration
  if (success) {
    return (
      <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-green-50 font-cairo p-4">
        <div className="w-full max-w-md">
          <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-emerald-200 p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-10 h-10 text-emerald-600" />
            </div>
            <h2 className="text-2xl font-bold text-emerald-900 mb-3">تم إنشاء الحساب بنجاح</h2>
            <p className="text-gray-600 mb-6">
              حسابك قيد المراجعة من قبل الإدارة. سيتم إعلامك عند تفعيل حسابك.
            </p>
            <button
              onClick={onSwitchToLogin}
              className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition"
            >
              العودة لتسجيل الدخول
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-green-50 font-cairo p-4">
      <div className="w-full max-w-md">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-emerald-200 p-8">
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg mb-4">
              <Newspaper className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-emerald-900">عين</h1>
            <p className="text-emerald-600 mt-1">إنشاء حساب جديد</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl px-4 py-3 mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">الاسم</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="أدخل اسمك الكامل"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">اسم المستخدم</label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="أدخل اسم المستخدم"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">كلمة المرور</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="أدخل كلمة المرور"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">تأكيد كلمة المرور</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
                placeholder="أعد إدخال كلمة المرور"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition disabled:opacity-60"
            >
              {loading ? 'جاري الإنشاء...' : 'إنشاء حساب'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              لديك حساب بالفعل؟{' '}
              <button
                onClick={onSwitchToLogin}
                className="text-emerald-600 hover:text-emerald-700 font-semibold"
              >
                تسجيل الدخول
              </button>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-gray-500 mt-6">
          طور بواسطة قسم الحلول التقنية - 2025
        </p>
      </div>
    </div>
  )
}
