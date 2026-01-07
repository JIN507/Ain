import { createContext, useContext, useState, useEffect } from 'react'
import { apiFetch } from '../apiClient'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  const loadCurrentUser = async () => {
    try {
      const res = await apiFetch('/api/auth/me')
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

  useEffect(() => {
    loadCurrentUser()
  }, [])

  const login = async (email, password) => {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.error || 'فشل تسجيل الدخول')
    }
    setCurrentUser(data)
    return data
  }

  const register = async (name, email, password) => {
    const res = await apiFetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    const data = await res.json()
    if (!res.ok) {
      throw new Error(data.error || 'فشل إنشاء الحساب')
    }
    // Do NOT auto-login - user must be approved by admin first
    return { ...data, pendingApproval: true }
  }

  const logout = async () => {
    try {
      await apiFetch('/api/auth/logout', { method: 'POST' })
    } catch (e) {
      // Ignore errors
    }
    setCurrentUser(null)
  }

  const value = {
    currentUser,
    authLoading,
    isAuthenticated: !!currentUser,
    isAdmin: currentUser?.role === 'ADMIN',
    login,
    register,
    logout,
    refreshUser: loadCurrentUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
