import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import DirectSearch from './pages/DirectSearch'
import TopHeadlines from './pages/TopHeadlines'
import Countries from './pages/Countries'
import Keywords from './pages/Keywords'
import Settings from './pages/Settings'
import Login from './pages/Login'
import Admin from './pages/Admin'
import MyFiles from './pages/MyFiles'

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  const pages = {
    dashboard: <Dashboard />,
    directsearch: <DirectSearch />,
    topheadlines: <TopHeadlines />,
    myfiles: <MyFiles />,
    countries: <Countries />,
    keywords: <Keywords />,
    settings: <Settings />,
    admin: <Admin />,
  }

  useEffect(() => {
    const loadCurrentUser = async () => {
      try {
        const res = await fetch('/api/auth/me')
        if (res.ok) {
          const data = await res.json()
          setCurrentUser(data)
        } else {
          setCurrentUser(null)
        }
      } catch (e) {
        setCurrentUser(null)
      } finally {
        setAuthLoading(false)
      }
    }

    loadCurrentUser()
  }, [])

  const handleLogout = async () => {
    try {
      await fetch('/api/auth/logout', { method: 'POST' })
    } catch (e) {}
    setCurrentUser(null)
  }

  if (authLoading) {
    return (
      <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-green-50">
        <div className="text-gray-600 text-sm">جاري التحقق من الجلسة...</div>
      </div>
    )
  }

  if (!currentUser) {
    return <Login onLogin={setCurrentUser} />
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-gradient-to-br from-emerald-50 to-green-50 font-cairo">
      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-lg border border-emerald-200"
      >
        {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      <div className="flex flex-col md:flex-row min-h-screen">
        {/* Sidebar */}
        <Sidebar 
          currentPage={currentPage}
          setCurrentPage={setCurrentPage}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          isAdmin={currentUser?.role === 'ADMIN'}
        />
        
        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="flex justify-between items-center px-4 md:px-8 pt-4">
            <div />
            <div className="flex items-center gap-3">
              <div className="text-xs md:text-sm text-gray-700 bg-white/70 border border-emerald-100 rounded-full px-3 py-1 flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                <span className="text-[10px] md:text-xs text-emerald-700 font-semibold uppercase tracking-wide">
                  {currentUser.role}
                </span>
                <span className="font-semibold">
                  {currentUser.name || currentUser.email}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="text-xs md:text-sm px-3 py-1 rounded-full bg-red-50 text-red-600 border border-red-100 hover:bg-red-100 transition"
              >
                تسجيل الخروج
              </button>
            </div>
          </div>
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="p-4 md:p-8"
          >
            {pages[currentPage]}
          </motion.div>
        </main>
      </div>
    </div>
  )
}
