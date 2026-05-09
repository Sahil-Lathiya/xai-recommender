import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-300 font-medium">{d.payload.description}</p>
      <p className="text-cyan-400 font-bold mt-1">
        Importance: {(d.value * 100).toFixed(1)}%
      </p>
      <p className="text-slate-400">Rank #{d.payload.rank}</p>
    </div>
  )
}

export default function FeatureImportanceChart({ features = [] }) {
  if (!features.length) return null

  const data = [...features]
    .sort((a, b) => b.importance_score - a.importance_score)
    .slice(0, 8)
    .map((f, i) => ({
      label: f.description,
      value: f.importance_score,
      rank: f.rank,
      description: f.description,
      fill: i === 0 ? '#00B4D8' : i === 1 ? '#38BDF8' : '#7DD3FC',
    }))

  return (
    <ResponsiveContainer width="100%" height={data.length * 40 + 20}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 48, left: 4, bottom: 4 }}
      >
        <XAxis
          type="number"
          tick={{ fill: '#94A3B8', fontSize: 10 }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={155}
          tick={{ fill: '#94A3B8', fontSize: 10 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={22}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} fillOpacity={0.9} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
