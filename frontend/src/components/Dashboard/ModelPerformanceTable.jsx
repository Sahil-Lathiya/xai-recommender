export default function ModelPerformanceTable({ days = [] }) {
  if (!days.length) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700/50">
            {['Date', 'Recommendations', 'Avg Confidence', 'Avg Response'].map((h) => (
              <th key={h} className="text-left text-slate-400 text-xs font-medium uppercase tracking-wide py-2 pr-4">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {days.map((day, i) => (
            <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
              <td className="py-2.5 pr-4 text-slate-300 font-mono text-xs">{day.date}</td>
              <td className="py-2.5 pr-4 text-cyan-400 font-medium">
                {day.recommendations_count.toLocaleString()}
              </td>
              <td className="py-2.5 pr-4">
                <span className={
                  day.avg_confidence >= 70
                    ? 'text-emerald-400'
                    : day.avg_confidence >= 50
                    ? 'text-amber-400'
                    : 'text-slate-400'
                }>
                  {day.avg_confidence > 0 ? `${day.avg_confidence.toFixed(1)}%` : '—'}
                </span>
              </td>
              <td className="py-2.5 text-slate-400">
                {day.avg_response_time_ms > 0 ? `${day.avg_response_time_ms.toFixed(0)}ms` : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
