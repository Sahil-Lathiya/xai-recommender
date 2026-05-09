import { useEffect, useRef } from 'react'

export default function ConfidenceRing({ score = 0, size = 110 }) {
  const circleRef = useRef(null)
  const strokeWidth = 9
  const radius = (size - strokeWidth * 2) / 2
  const circumference = 2 * Math.PI * radius

  const color =
    score >= 80 ? '#00B4D8' : score >= 60 ? '#F59E0B' : '#EF4444'
  const label =
    score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : 'Fair'

  useEffect(() => {
    if (!circleRef.current) return
    const offset = circumference - (score / 100) * circumference
    circleRef.current.style.strokeDashoffset = offset
  }, [score, circumference])

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1E293B"
            strokeWidth={strokeWidth}
          />
          {/* Progress */}
          <circle
            ref={circleRef}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference}
            style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.16,1,0.3,1)' }}
          />
        </svg>
        {/* Centre text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold" style={{ color }}>
            {score}%
          </span>
          <span className="text-slate-500 text-xs">match</span>
        </div>
      </div>
      <span className="text-xs font-medium" style={{ color }}>
        {label} match
      </span>
    </div>
  )
}
