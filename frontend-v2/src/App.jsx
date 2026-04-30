import { useState, useRef, lazy, Suspense } from 'react'
import { motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import Sidebar from './components/Sidebar'
import Login from './pages/Login'
import Register from './pages/Register'
import { AuthProvider, useAuth } from './context/AuthContext'

// Lazy-loaded pages — each becomes a separate JS chunk
const HomePage = lazy(() => import('./pages/HomePage'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const DirectSearch = lazy(() => import('./pages/DirectSearch'))
const TopHeadlines = lazy(() => import('./pages/TopHeadlines'))
const Countries = lazy(() => import('./pages/Countries'))
const Keywords = lazy(() => import('./pages/Keywords'))
const Settings = lazy(() => import('./pages/Settings'))
const Admin = lazy(() => import('./pages/Admin'))
const MyFiles = lazy(() => import('./pages/MyFiles'))
const Bookmarks = lazy(() => import('./pages/Bookmarks'))
const Profile = lazy(() => import('./pages/Profile'))

const PageLoader = () => (
  <div className="flex items-center justify-center min-h-[40vh]">
    <div className="flex flex-col items-center gap-3">
      <div className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)' }}>
        <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
        </svg>
      </div>
      <span className="text-xs text-slate-400 font-medium">جاري التحميل...</span>
    </div>
  </div>
)

function AppContent() {
  const [currentPage, setCurrentPage] = useState('home')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarHovered, setSidebarHovered] = useState(false)
  const hoverTimeout = useRef(null)
  const [showRegister, setShowRegister] = useState(false)
  const [dashboardKeywordFilter, setDashboardKeywordFilter] = useState('')
  const { currentUser, authLoading, logout, login, register } = useAuth()
  
  // Navigate to dashboard with keyword pre-filtered
  const navigateToKeywordResults = (keyword) => {
    setDashboardKeywordFilter(keyword)
    setCurrentPage('dashboard')
  }

  const pages = {
    home: <HomePage />,
    dashboard: <Dashboard initialKeywordFilter={dashboardKeywordFilter} onFilterApplied={() => setDashboardKeywordFilter('')} />,
    directsearch: <DirectSearch />,
    topheadlines: <TopHeadlines />,
    bookmarks: <Bookmarks />,
    myfiles: <MyFiles />,
    countries: <Countries isAdmin={currentUser?.role === 'ADMIN'} />,
    keywords: <Keywords onKeywordClick={navigateToKeywordResults} />,
    settings: <Settings />,
    admin: <Admin />,
    profile: <Profile onBack={() => setCurrentPage('dashboard')} />,
  }

  if (authLoading) {
    return (
      <div dir="rtl" lang="ar" className="min-h-screen flex items-center justify-center" style={{ background: '#f8fafc' }}>
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #0f766e 0%, #14b8a6 100%)' }}>
            <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
          </div>
          <span className="text-xs text-slate-400 font-medium">جاري التحقق...</span>
        </div>
      </div>
    )
  }

  if (!currentUser) {
    if (showRegister) {
      return (
        <Register
          onRegister={register}
          onSwitchToLogin={() => setShowRegister(false)}
        />
      )
    }
    return (
      <Login
        onLogin={login}
        onSwitchToRegister={() => setShowRegister(true)}
      />
    )
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen font-cairo" style={{ background: '#f8fafc' }}>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2.5 rounded-xl transition-all duration-200"
        style={{
          background: 'rgba(255,255,255,0.9)',
          backdropFilter: 'blur(8px)',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
          border: '1px solid rgba(0,0,0,0.06)',
        }}
      >
        {sidebarOpen ? <X className="w-5 h-5 text-slate-700" /> : <Menu className="w-5 h-5 text-slate-700" />}
      </button>

      <div className="flex flex-col md:flex-row min-h-screen">
        {/* Sidebar — hover overlay on all pages */}
        <div className="hidden md:block w-[60px] flex-shrink-0" />
        <div
          className="hidden md:block fixed top-0 right-0 h-screen z-50"
          style={{ width: sidebarHovered ? '256px' : '60px', transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)' }}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current)
            hoverTimeout.current = setTimeout(() => setSidebarHovered(true), 80)
          }}
          onMouseLeave={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current)
            hoverTimeout.current = null
            setSidebarHovered(false)
          }}
        >
          <Sidebar 
            currentPage={currentPage}
            setCurrentPage={(p) => { setCurrentPage(p); setSidebarHovered(false) }}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            isAdmin={currentUser?.role === 'ADMIN'}
            collapsed={!sidebarHovered}
          />
        </div>
        {/* Mobile sidebar */}
        <div className="md:hidden">
          <Sidebar 
            currentPage={currentPage}
            setCurrentPage={setCurrentPage}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            isAdmin={currentUser?.role === 'ADMIN'}
            collapsed={false}
          />
        </div>
        
        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          {/* Top bar */}
          <div className="sticky top-0 z-30 px-4 md:px-8 py-3 flex justify-between items-center"
            style={{
              background: 'rgba(248,250,252,0.85)',
              backdropFilter: 'blur(10px)',
              borderBottom: '1px solid rgba(0,0,0,0.04)',
            }}>
            <div />
            <div className="flex items-center gap-2.5">
              <button
                onClick={() => setCurrentPage('profile')}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs cursor-pointer transition-all duration-200 hover:shadow-md"
                style={{
                  background: 'rgba(255,255,255,0.8)',
                  border: '1px solid rgba(0,0,0,0.06)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                }}>
                <span className="inline-flex h-1.5 w-1.5 rounded-full bg-teal-500 pulse-glow"></span>
                <span className="text-slate-500 font-medium">
                  {currentUser.email}
                </span>
              </button>
              <button
                onClick={logout}
                className="text-xs px-3 py-1.5 rounded-full font-medium transition-all duration-200"
                style={{
                  color: '#64748b',
                  background: 'rgba(0,0,0,0.03)',
                }}
                onMouseEnter={(e) => { e.target.style.background = 'rgba(239,68,68,0.08)'; e.target.style.color = '#ef4444'; }}
                onMouseLeave={(e) => { e.target.style.background = 'rgba(0,0,0,0.03)'; e.target.style.color = '#64748b'; }}
              >
                تسجيل الخروج
              </button>
            </div>
          </div>

          {/* Page Content */}
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] }}
            className={currentPage === 'home' ? 'p-3 md:p-4' : 'p-4 md:p-6'}
          >
            <Suspense fallback={<PageLoader />}>
              {pages[currentPage]}
            </Suspense>
          </motion.div>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
