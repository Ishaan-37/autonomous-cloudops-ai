import { useEffect, useState } from 'react'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { getMonitoringData, getMetrics } from '../services/api'
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

export default function Monitoring() {
  const [data, setData] = useState(null)
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    getMonitoringData().then(setData)
    getMetrics().then(setMetrics)
  }, [])

  if (!data || !metrics) return <div className="p-8 text-sm text-muted">Loading…</div>

  return (
    <div className="p-8 space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricsCard label="Alarms · 24h" value={metrics.alarmsProcessed24h} />
        <MetricsCard label="Remediation success" value={`${Math.round(metrics.remediationSuccessRate * 100)}%`} tone="active" />
        <MetricsCard label="Avg agent latency" value={`${(metrics.avgAgentLatencyMs / 1000).toFixed(1)}s`} />
        <MetricsCard label="Failure rate" value={`${Math.round((1 - metrics.remediationSuccessRate) * 100)}%`} tone="danger" />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        {/* Agent latency */}
        <div className="card p-6">
          <p className="eyebrow mb-1">AI agent latency</p>
          <p className="text-xs text-muted mb-4">End-to-end pipeline duration, ms</p>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={data.latencyTrend}>
              <defs>
                <linearGradient id="latencyFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4FD1C5" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#4FD1C5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#2A3441" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={axisStyle} axisLine={{ stroke: '#2A3441' }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={tooltipStyle} />
              <Area type="monotone" dataKey="latencyMs" stroke="#4FD1C5" strokeWidth={2} fill="url(#latencyFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Alerts processed */}
        <div className="card p-6">
          <p className="eyebrow mb-1">Alarms processed</p>
          <p className="text-xs text-muted mb-4">CloudWatch alarms ingested per day</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.latencyTrend}>
              <CartesianGrid stroke="#2A3441" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={axisStyle} axisLine={{ stroke: '#2A3441' }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="alarms" fill="#FF8A3D" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Remediation success rate */}
        <div className="card p-6">
          <p className="eyebrow mb-1">Remediation success rate</p>
          <p className="text-xs text-muted mb-4">Share of runs completed without human override</p>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data.successTrend}>
              <CartesianGrid stroke="#2A3441" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={axisStyle} axisLine={{ stroke: '#2A3441' }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={40} domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v) => `${Math.round(v * 100)}%`} />
              <Line type="monotone" dataKey="success" stroke="#4FD1C5" strokeWidth={2} dot={{ r: 3, fill: '#4FD1C5' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* LLM token usage */}
        <div className="card p-6">
          <p className="eyebrow mb-1">LLM token usage</p>
          <p className="text-xs text-muted mb-4">Tokens consumed per day across all runs</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data.tokenUsage}>
              <CartesianGrid stroke="#2A3441" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="day" tick={axisStyle} axisLine={{ stroke: '#2A3441' }} tickLine={false} />
              <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={50} tickFormatter={(v) => `${v / 1000}k`} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="tokens" fill="#8A96A6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
