import { Lightbulb } from 'lucide-react'

export default function CounterfactualCard({ text }) {
  if (!text) return null
  return (
    <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-amber-400/15 flex items-center justify-center">
          <Lightbulb size={16} className="text-amber-400" />
        </div>
        <div>
          <p className="text-amber-300 text-xs font-semibold uppercase tracking-wide mb-1">
            What would change this?
          </p>
          <p className="text-slate-300 text-sm leading-relaxed">{text}</p>
        </div>
      </div>
    </div>
  )
}
