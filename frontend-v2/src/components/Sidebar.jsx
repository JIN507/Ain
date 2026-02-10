import { motion } from 'framer-motion'
import { Home, Globe, Key, Newspaper, Search, Activity, Shield, Eye } from 'lucide-react'

export default function Sidebar({ currentPage, setCurrentPage, sidebarOpen, setSidebarOpen, isAdmin }) {
  const navItems = [
    { id: 'dashboard', label: 'النتائج', icon: Home },
    { id: 'directsearch', label: 'إبحث الآن', icon: Search },
    { id: 'topheadlines', label: 'أهم العناوين', icon: Activity },
    { id: 'myfiles', label: 'ملفاتي', icon: Newspaper },
    { id: 'countries', label: 'الدول', icon: Globe },
    { id: 'keywords', label: 'مراقبة الأخبار', icon: Key },
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
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:sticky top-0 right-0 h-screen w-64 z-50
          transition-transform duration-300 ease-out
          ${sidebarOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
        `}
        style={{
          background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
        }}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="px-6 pt-8 pb-6">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
                  boxShadow: '0 4px 14px rgba(20,184,166,0.3)',
                }}>
                <Eye className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">عين</h1>
                <p className="text-[11px] text-teal-400/70 font-medium">نظام رصد الأخبار</p>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="mx-5 h-px bg-white/[0.06]" />

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-0.5">
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
                  className={`sidebar-link w-full text-right relative ${isActive ? 'active' : ''}`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="absolute inset-0 rounded-xl"
                      style={{ background: 'rgba(20,184,166,0.12)' }}
                      transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center gap-3">
                    <Icon className="w-[18px] h-[18px]" />
                    <span>{item.label}</span>
                  </span>
                </button>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="px-5 pb-6">
            <div className="rounded-xl p-3.5" style={{ background: 'rgba(255,255,255,0.04)' }}>
              <p className="text-[11px] text-slate-400 font-medium">قسم الحلول التقنية</p>
              <p className="text-[11px] text-slate-500 mt-1">
                {new Date().toLocaleDateString('ar-SA', { timeZone: 'Asia/Riyadh', year: 'numeric', month: 'long', day: 'numeric' })}
              </p>
              <p className="text-[10px] text-teal-500/60 mt-1 font-semibold">v4.0</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
