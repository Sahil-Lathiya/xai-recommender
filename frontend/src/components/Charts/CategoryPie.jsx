import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#00B4D8', '#38BDF8', '#A78BFA', '#F472B6', '#FB923C']

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-300 font-medium">{payload[0].name}</p>
      <p style={{ color: payload[0].payload.fill }} className="font-bold mt-1">
        {payload[0].value} recommendations
      </p>
    </div>
  )
}

export default function CategoryPie({ data = [] }) {
  if (!data.length) {
    const fallback = [
      { name: 'Electronics', value: 42 },
      { name: 'Books', value: 28 },
      { name: 'Clothing', value: 18 },
      { name: 'Home', value: 12 },
    ]
    data = fallback
  }

  const colored = data.map((d, i) => ({ ...d, fill: COLORS[i % COLORS.length] }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={colored}
          cx="50%"
          cy="45%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {colored.map((entry, i) => (
            <Cell key={i} fill={entry.fill} stroke="transparent" />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
