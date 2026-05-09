import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  ReferenceLine, ResponsiveContainer, LabelList,
} from 'recharts'

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  const d = payload[0]
  const sign = d.value > 0 ? '+' : ''
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-300 font-medium mb-1">{d.payload.label}</p>
      <p style={{ color: d.payload.fill }} className="font-bold">
        {sign}{d.value.toFixed(0)}% influence
      </p>
      <p className="text-slate-400 mt-0.5">Feature value: {d.payload.rawValue}</p>
    </div>
  )
}

export default function SHAPWaterfall({ contributions = [], limit = 8 }) {
  if (!contributions.length) return null

  const sliced = contributions.slice(0, limit)
  const maxAbs = Math.max(...sliced.map(c => Math.abs(c.shap_value)), 1e-10)

  const data = sliced.map((c) => ({
    label: c.human_label,
    value: parseFloat(((c.shap_value / maxAbs) * 100).toFixed(1)),
    rawValue: typeof c.raw_value === 'number' ? c.raw_value.toFixed(2) : c.raw_value,
    fill: c.direction === 'positive' ? '#00B4D8' : '#EF4444',
  }))

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={data.length * 36 + 52}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 52, left: 4, bottom: 28 }}
        >
          <XAxis
            type="number"
            domain={[-100, 100]}
            tick={{ fill: '#94A3B8', fontSize: 10 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={false}
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}%`}
            ticks={[-100, -50, 0, 50, 100]}
            label={{
              value: '← Negative influence  |  Positive influence →',
              position: 'insideBottom',
              offset: -16,
              style: { fill: '#64748B', fontSize: 10, textAnchor: 'middle' },
            }}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={140}
            tick={{ fill: '#94A3B8', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={0} stroke="#475569" strokeWidth={1} />
          <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={20}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} fillOpacity={0.85} />
            ))}
            <LabelList
              dataKey="value"
              position="right"
              formatter={(v) => `${v > 0 ? '+' : ''}${Math.round(v)}%`}
              style={{ fill: '#94A3B8', fontSize: 9 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex items-center gap-4 justify-center">
        <span className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="w-3 h-3 rounded-sm bg-cyan-400 inline-block" />
          Positive impact
        </span>
        <span className="flex items-center gap-1.5 text-xs text-slate-400">
          <span className="w-3 h-3 rounded-sm bg-red-500 inline-block" />
          Negative impact
        </span>
      </div>
    </div>
  )
}
