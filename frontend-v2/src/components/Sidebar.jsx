import { motion } from 'framer-motion'
import { Home, Globe, Key, Newspaper, Search, Activity, Shield, Eye, Bookmark, Map } from 'lucide-react'

export default function Sidebar({ currentPage, setCurrentPage, sidebarOpen, setSidebarOpen, isAdmin, collapsed = false }) {
  const navItems = [
    { id: 'home', label: 'الرئيسية', icon: Map },
    { id: 'dashboard', label: 'النتائج', icon: Home },
    { id: 'keywords', label: 'الكلمات والمراقبة', icon: Key },
    { id: 'directsearch', label: 'إبحث الآن', icon: Search },
    { id: 'topheadlines', label: 'أهم العناوين', icon: Activity },
    { id: 'bookmarks', label: 'المفضلة', icon: Bookmark },
    { id: 'myfiles', label: 'ملفاتي', icon: Newspaper },
    { id: 'countries', label: 'الدول', icon: Globe },
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
          fixed md:sticky top-0 right-0 h-screen z-50
          ${collapsed ? 'w-[60px]' : 'w-64'}
          ${sidebarOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
        `}
        style={{
          background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
          overflow: 'hidden',
          transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1), transform 0.3s ease-out',
        }}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className={`pt-8 pb-6 flex-shrink-0 ${collapsed ? 'px-2.5' : 'px-6'}`}>
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{
                  background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)',
                  boxShadow: '0 4px 14px rgba(20,184,166,0.3)',
                }}>
                <Eye className="w-5 h-5 text-white" />
              </div>
              <div style={{ opacity: collapsed ? 0 : 1, transform: collapsed ? 'translateX(8px)' : 'translateX(0)', transition: 'opacity 0.2s ease, transform 0.2s ease', pointerEvents: collapsed ? 'none' : 'auto' }}>
                <h1 className="text-xl font-bold text-white tracking-tight whitespace-nowrap">عين</h1>
                <p className="text-[11px] text-teal-400/70 font-medium whitespace-nowrap">نظام رصد الأخبار</p>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className={`h-px bg-white/[0.06] flex-shrink-0 ${collapsed ? 'mx-2' : 'mx-5'}`} />
                
          {/* Navigation */}
          <nav className={`py-4 space-y-0.5 overflow-y-auto flex-shrink ${collapsed ? 'px-1.5' : 'px-3'}`}>
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
                  className={`sidebar-link w-full text-right relative overflow-hidden ${isActive ? 'active' : ''}`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-indicator"
                      className="absolute inset-0 rounded-lg"
                      style={{ background: 'rgba(20,184,166,0.12)' }}
                      transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center py-2 gap-3 px-3">
                    <Icon className="w-[18px] h-[18px] flex-shrink-0" />
                    <span className="whitespace-nowrap" style={{ opacity: collapsed ? 0 : 1, transition: 'opacity 0.2s ease' }}>{item.label}</span>
                  </span>
                </button>
              )
            })}
          </nav>

          <div className="flex-1" />

          {/* Footer */}
          <div className="pb-6 pt-2 flex-shrink-0 px-2" style={{ transition: 'padding 0.25s ease' }}>
            <div className="rounded-xl p-2.5" style={{ background: collapsed ? 'transparent' : 'rgba(255,255,255,0.04)', transition: 'background 0.2s ease' }}>
              <div style={{ opacity: collapsed ? 0 : 1, height: collapsed ? 0 : 'auto', overflow: 'hidden', transition: 'opacity 0.2s ease, height 0.25s ease' }}>
                <p className="text-[14px] text-slate-400 font-medium whitespace-nowrap">قسم الحلول التقنية</p>
                <p className="text-[14px] text-green-500 mt-1 whitespace-nowrap">
                  {new Date().toLocaleDateString('ar-SA', { timeZone: 'Asia/Riyadh', year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
              </div>
              <p className={`text-green-500/90 font-semibold ${collapsed ? 'text-[10px] text-center' : 'text-[12px] mt-2'}`} style={{ opacity: collapsed ? 0 : 1, transition: 'all 0.2s ease' }}>V3.1</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}