import { Loader2 } from 'lucide-react'

export default function Loader({ text }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Loader2 className="w-8 h-8 text-teal-600 animate-spin mb-3" />
      {text && <p className="text-sm text-slate-500">{text}</p>}
    </div>
  )
}
