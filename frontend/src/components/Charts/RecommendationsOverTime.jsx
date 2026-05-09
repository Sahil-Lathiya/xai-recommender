import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-400 mb-1">{label}</p>
      <p className="text-cyan-400 font-bold">
        {payload[0].value} recommendations
      </p>
    </div>
  )
}

export default function RecommendationsOverTime({ days = [] }) {
  if (!days.length) return null

  const data = days.map((d) => ({
    date: d.date?.slice(5) ?? d.date,
    count: d.recommendations_count,
    confidence: d.avg_confidence,
  }))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#00B4D8" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00B4D8" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#94A3B8', fontSize: 11 }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#94A3B8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="count"
          stroke="#00B4D8"
          strokeWidth={2}
          fill="url(#areaGrad)"
          dot={{ fill: '#00B4D8', r: 3 }}
          activeDot={{ r: 5, fill: '#00B4D8' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
