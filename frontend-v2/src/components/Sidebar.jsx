import { Home, Globe, Key, Settings, Newspaper, Search, Activity, Shield } from 'lucide-react'

export default function Sidebar({ currentPage, setCurrentPage, sidebarOpen, setSidebarOpen, isAdmin }) {
  const navItems = [
    { id: 'dashboard', label: 'النتائج', icon: Home },
    { id: 'directsearch', label: 'إبحث بكلمة مباشرة', icon: Search },
    { id: 'topheadlines', label: 'أهم العناوين', icon: Activity },
    { id: 'myfiles', label: 'ملفاتي', icon: Newspaper },
    { id: 'countries', label: 'الدول', icon: Globe },
    { id: 'keywords', label: 'الكلمات المفتاحية', icon: Key },
    { id: 'settings', label: 'تشغيل النظام', icon: Settings },
  ]

  const adminItems = isAdmin
    ? [
        { id: 'admin', label: 'لوحة الإدارة', icon: Shield },
      ]
    : []

  return (
    <>
      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:sticky top-0 right-0 h-screen w-72 bg-white/90 backdrop-blur-sm
          border-l border-emerald-200 shadow-xl z-50 transition-transform duration-300
          ${sidebarOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-emerald-200">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg">
                <Newspaper className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-emerald-900">عين</h1>
                <p className="text-sm text-emerald-600">لرؤية شاملة</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {[...navItems, ...adminItems].map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setCurrentPage(item.id)
                    setSidebarOpen(false)
                  }}
                  className={`sidebar-link w-full text-right flex items-center gap-3 ${isActive ? 'active' : ''}`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-semibold">{item.label}</span>
                </button>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-emerald-200">
            <div className="bg-emerald-50 rounded-lg p-3 mb-3">
              <p className="text-xs text-emerald-700 font-semibold">طور بواسطة قسم الحلول التقنية</p>
              <p className="text-sm text-emerald-900">{new Date().toLocaleDateString('ar-SA', { timeZone: 'Asia/Riyadh', year: 'numeric', month: 'long', day: 'numeric' , hour: '2-digit', minute: '2-digit' })}</p>
              <p className="text-sm text-red-900">Version 2.0</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
