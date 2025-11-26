import { Loader2 } from 'lucide-react'

export default function Loader({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Loader2 className="w-12 h-12 text-emerald-600 animate-spin mb-4" />
      {text && <p className="text-gray-600">{text}</p>}
    </div>
  )
}
