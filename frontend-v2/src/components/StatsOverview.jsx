import { motion } from 'framer-motion'
import { FileText, TrendingUp, AlertCircle, Globe } from 'lucide-react'

export default function StatsOverview({ stats }) {
  const statCards = [
    {
      label: 'إجمالي المقالات',
      value: stats.total,
      icon: FileText,
      gradient: 'from-emerald-500 to-emerald-700'
    },
    {
      label: 'مشاعر إيجابية',
      value: stats.positive,
      icon: TrendingUp,
      gradient: 'from-green-500 to-green-700'
    },
    {
      label: 'مشاعر سلبية',
      value: stats.negative,
      icon: AlertCircle,
      gradient: 'from-red-500 to-pink-600'
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
