import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, Globe, Clock, MapPin } from 'lucide-react'
import { apiFetch } from '../apiClient'

export default function StatsOverview({ stats, keywordCount = 0 }) {
  const [countdown, setCountdown] = useState('--:--')
  const [nextRunTime, setNextRunTime] = useState(null)
  const [isMonitoringRunning, setIsMonitoringRunning] = useState(false)

  // Fetch scheduler status and calculate countdown (only if keywords exist)
  useEffect(() => {
    // No keywords = no monitoring, stop everything
    if (keywordCount === 0) {
      setIsMonitoringRunning(false)
      setNextRunTime(null)
      setCountdown('متوقف')
      return
    }

    const fetchSchedulerStatus = async () => {
      try {
        const res = await apiFetch('/api/monitor/status')
        const data = await res.json()
        setIsMonitoringRunning(data.running || false)
        
        if (data.next_run) {
          setNextRunTime(new Date(data.next_run))
        } else if (data.running) {
          // If running but no next_run yet, refetch soon
          setTimeout(fetchSchedulerStatus, 3000)
        } else {
          // Not running - clear next run time
          setNextRunTime(null)
        }
      } catch (error) {
        console.error('Error fetching scheduler status:', error)
      }
    }

    fetchSchedulerStatus()
    // Refresh scheduler status every 30 seconds to catch new monitoring starts
    const statusInterval = setInterval(fetchSchedulerStatus, 30000)
    return () => clearInterval(statusInterval)
  }, [keywordCount])

  // Update countdown every second
  useEffect(() => {
    // If monitoring not running, show stopped state
    if (!isMonitoringRunning) {
      setCountdown('متوقف')
      return
    }
    
    if (!nextRunTime) {
      setCountdown('جاري التحميل...')
      return
    }

    const updateCountdown = () => {
      const now = new Date()
      const diff = nextRunTime - now
      
      if (diff <= 0) {
        setCountdown('جاري البحث...')
        return
      }
      
      const minutes = Math.floor(diff / 60000)
      const seconds = Math.floor((diff % 60000) / 1000)
      setCountdown(`${minutes}:${seconds.toString().padStart(2, '0')}`)
    }

    updateCountdown()
    const countdownInterval = setInterval(updateCountdown, 1000)
    return () => clearInterval(countdownInterval)
  }, [nextRunTime, isMonitoringRunning])

  const statCards = [
    {
      label: 'إجمالي المقالات',
      value: stats.total,
      icon: FileText,
      color: '#0f766e',
      bg: 'rgba(15,118,110,0.08)',
    },
    {
      label: 'الدول',
      value: stats.uniqueCountries || stats.countries || 0,
      icon: MapPin,
      color: '#4f46e5',
      bg: 'rgba(79,70,229,0.08)',
    },
    {
      label: 'البحث التالي',
      value: countdown,
      icon: Clock,
      color: '#ea580c',
      bg: 'rgba(234,88,12,0.08)',
      isTimer: true,
    },
    {
      label: 'الدول المراقبة',
      value: stats.countries || 0,
      icon: Globe,
      color: '#0284c7',
      bg: 'rgba(2,132,199,0.08)',
    }
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {statCards.map((stat, idx) => {
        const Icon = stat.icon
        return (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.08, duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
            className="card p-5 group"
          >
            <div className="flex items-start justify-between mb-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110"
                style={{ background: stat.bg }}
              >
                <Icon className="w-5 h-5" style={{ color: stat.color }} />
              </div>
              {stat.isTimer && isMonitoringRunning && (
                <span className="inline-flex h-2 w-2 rounded-full bg-teal-500 pulse-glow mt-1" />
              )}
            </div>
            <div className="text-2xl font-bold text-slate-900 animate-count-up">{stat.value}</div>
            <div className="text-xs text-slate-500 mt-0.5 font-medium">{stat.label}</div>
          </motion.div>
        )
      })}
    </div>
  )
}
