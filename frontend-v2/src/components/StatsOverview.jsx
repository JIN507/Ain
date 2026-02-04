import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FileText, Globe, Clock, MapPin } from 'lucide-react'
import { apiFetch } from '../api'

export default function StatsOverview({ stats }) {
  const [countdown, setCountdown] = useState('--:--')
  const [nextRunTime, setNextRunTime] = useState(null)

  // Fetch scheduler status and calculate countdown
  useEffect(() => {
    const fetchSchedulerStatus = async () => {
      try {
        const res = await apiFetch('/api/monitor/status')
        const data = await res.json()
        if (data.next_run) {
          setNextRunTime(new Date(data.next_run))
        }
      } catch (error) {
        console.error('Error fetching scheduler status:', error)
      }
    }

    fetchSchedulerStatus()
    // Refresh scheduler status every 60 seconds
    const statusInterval = setInterval(fetchSchedulerStatus, 60000)
    return () => clearInterval(statusInterval)
  }, [])

  // Update countdown every second
  useEffect(() => {
    if (!nextRunTime) return

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
  }, [nextRunTime])

  const statCards = [
    {
      label: 'إجمالي المقالات',
      value: stats.total,
      icon: FileText,
      gradient: 'from-emerald-500 to-emerald-700'
    },
    {
      label: 'الدول',
      value: stats.uniqueCountries || stats.countries || 0,
      icon: MapPin,
      gradient: 'from-green-500 to-green-700'
    },
    {
      label: 'البحث',
      value: countdown,
      icon: Clock,
      gradient: 'from-orange-500 to-red-500'
    },
    {
      label: 'الدول المراقبة',
      value: stats.countries || 0,
      icon: Globe,
      gradient: 'from-blue-500 to-indigo-600'
    }
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((stat, idx) => {
        const Icon = stat.icon
        return (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="card p-5"
          >
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${stat.gradient} flex items-center justify-center shadow-lg flex-shrink-0`}>
                <Icon className="w-7 h-7 text-white" />
              </div>
              <div>
                <div className="text-3xl font-bold text-gray-900">{stat.value}</div>
                <div className="text-sm text-gray-600">{stat.label}</div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}
