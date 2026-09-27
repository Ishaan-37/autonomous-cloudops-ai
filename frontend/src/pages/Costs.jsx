import { useEffect, useState } from 'react'
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { CheckCircle2, AlertCircle } from 'lucide-react'
import { getCostData, getMetrics } from '../services/api'
import MetricsCard from '../components/MetricsCard'

const tooltipStyle = {
  background: '#1B2330',
  border: '1px solid #2A3441',
  borderRadius: 8,
  fontSize: 12,
  fontFamily: 'JetBrains Mono, monospace',
  color: '#E7ECF2'
}

const axisStyle = { fontSize: 11, fill: '#5B6675', fontFamily: 'JetBrains Mono, monospace' }

export default function Costs() {
  const [data, setData] = useState(null)
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    getCostData().then(setData)
    getMetrics().then(setMetrics)
  }, [])

  if (!data || !metrics) return <div className="p-8 text-sm text-muted">Loading…</div>

  const totalSavings = data.savingsOpportunities
    .filter((s) => s.status === 'flagged')
    .reduce((sum, s) => sum + s.monthlySavings, 0)

  return (
    <div className="p-8 space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <MetricsCard label="Monthly spend" value={`$${metrics.monthlySpend.toLocaleString()}`} />
        <MetricsCard label="Savings identified" value={`$${metrics.savingsIdentified.toLocaleString()}`} tone="signal" hint="via FinOps sweep" />
        <MetricsCard label="Open opportunities" value={`$${totalSavings.toFixed(2)}/mo`} tone="active" hint={`${data.savingsOpportunities.filter(s => s.status === 'flagged').length} flagged resources`} />
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Cost trend */}
        <div className="card p-6 lg:col-span-2">
          <p className="eyebrow mb-1">AWS cost trend</p>
          <p className="text-xs text-muted mb-4">Daily spend, last 7 days</p>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.costTrend}>
              <defs>
                <linearGradient id="costFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FF8A3D" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#FF8A3D" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#2A3441" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={axisStyle} axisLine={{ stroke: '#2A3441' }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={40} tickFormatter={(v) => `$${v}`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => `$${v}`} />
              <Area type="monotone" dataKey="spend" stroke="#FF8A3D" strokeWidth={2} fill="url(#costFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Cost by service */}
        <div className="card p-6">
          <p className="eyebrow mb-1">Spend by service</p>
          <p className="text-xs text-muted mb-4">Monthly breakdown</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={data.costByService}
                dataKey="cost"
                nameKey="service"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={2}
              >
                {data.costByService.map((entry, i) => (
                  <Cell key={i} fill={entry.color} stroke="#131922" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => `$${v}`} />
            </PieChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 mt-2">
            {data.costByService.map((s) => (
              <div key={s.service} className="flex items-center gap-1.5 text-xs">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ background: s.color }} />
                <span className="text-muted truncate">{s.service}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Savings opportunities */}
      <div className="card p-6">
        <p className="eyebrow mb-4">FinOps savings opportunities</p>
        <div className="space-y-2">
          {data.savingsOpportunities.map((s) => (
            <div key={s.id} className="flex items-center justify-between py-2.5 px-3 rounded-lg border border-border/60 hover:border-border transition-colors">
              <div className="flex items-center gap-3 min-w-0">
                {s.status === 'flagged'
                  ? <AlertCircle size={15} className="text-signal shrink-0" />
                  : <CheckCircle2 size={15} className="text-active shrink-0" />}
                <div className="min-w-0">
                  <p className="text-sm text-ink truncate">{s.type}</p>
                  <p className="font-mono text-xs text-faint truncate">{s.resource}</p>
                </div>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <span className="font-mono text-sm text-ink">${s.monthlySavings.toFixed(2)}/mo</span>
                <span className={`text-[10px] font-mono uppercase tracking-wide px-2 py-1 rounded-md border
                  ${s.status === 'flagged' ? 'text-signal border-signal/40 bg-signal-dim' : 'text-active border-active/40 bg-active-dim'}`}>
                  {s.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
