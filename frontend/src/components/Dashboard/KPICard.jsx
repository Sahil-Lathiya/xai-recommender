import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'

function useCountUp(target, duration = 1200) {
  const [value, setValue] = useState(0)
  const frameRef = useRef(null)

  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = performance.now()
    const animate = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(target * eased)
      if (progress < 1) frameRef.current = requestAnimationFrame(animate)
    }
    frameRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frameRef.current)
  }, [target, duration])

  return value
}

export default function KPICard({ title, value, unit = '', prefix = '', icon: Icon, color = 'cyan', decimals = 0 }) {
  const animated = useCountUp(typeof value === 'number' ? value : 0)

  const colorMap = {
    cyan:   { text: 'text-cyan-400',   bg: 'bg-cyan-400/10',   border: 'border-cyan-400/20' },
    violet: { text: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
    amber:  { text: 'text-amber-400',  bg: 'bg-amber-400/10',  border: 'border-amber-400/20' },
    green:  { text: 'text-emerald-400',bg: 'bg-emerald-400/10',border: 'border-emerald-400/20' },
  }
  const c = colorMap[color] || colorMap.cyan

  const displayValue = decimals > 0
    ? animated.toFixed(decimals)
    : Math.round(animated).toLocaleString()

  return (
    <motion.div
      className="card p-5 flex flex-col gap-3"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <div className="flex items-start justify-between">
        <p className="text-slate-400 text-sm font-medium">{title}</p>
        {Icon && (
          <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center border', c.bg, c.border)}>
            <Icon size={18} className={c.text} />
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-1">
        <span className={clsx('text-3xl font-bold', c.text)}>
          {prefix}{displayValue}
        </span>
        {unit && <span className="text-slate-400 text-sm">{unit}</span>}
      </div>
    </motion.div>
  )
}
