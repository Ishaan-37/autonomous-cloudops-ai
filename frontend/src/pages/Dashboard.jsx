import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { getRuns, getMetrics, subscribeToRuns } from '../services/api'
import MetricsCard from '../components/MetricsCard'
import IncidentCard from '../components/IncidentCard'
import WorkflowGraph from '../components/WorkflowGraph'

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    getRuns().then(setRuns)
    getMetrics().then(setMetrics)
    const unsubscribe = subscribeToRuns(setRuns)
    return unsubscribe
  }, [])

  const activeRun = runs[0]

  return (
    <div className="p-8 space-y-8">
      {/* Signature: live pipeline rail for the most recent run */}
      {activeRun && (
        <div className="card p-6 animate-[fadeIn_0.4s_ease-out]">
          <div className="flex items-center justify-between mb-5">
            <div>
              <p className="eyebrow">Live run</p>
              <Link to={`/workflow?run=${activeRun.id}`} className="group flex items-center gap-1.5 w-fit">
                <h2 className="font-display font-semibold text-lg mt-1 group-hover:text-active transition-colors">
                  {activeRun.alarm}
                </h2>
                <ArrowUpRight size={15} className="text-faint group-hover:text-active transition-colors mt-1" />
              </Link>
            </div>
            <span className="font-mono text-xs text-faint">{activeRun.id}</span>
          </div>
          <WorkflowGraph currentStage={activeRun.stage} />
          {activeRun.stage === 'approve' && (
            <div className="mt-5 flex items-center justify-between rounded-lg border border-signal/30 bg-signal-dim px-4 py-3">
              <p className="text-sm text-ink">Waiting on your approval to remediate.</p>
              <div className="flex gap-2">
                <button className="px-3 py-1.5 rounded-md bg-signal text-bg text-sm font-medium hover:opacity-90 transition-opacity">
                  Approve
                </button>
                <button className="px-3 py-1.5 rounded-md border border-border text-sm text-muted hover:text-ink transition-colors">
                  Reject
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* KPI row */}
      {metrics && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          <MetricsCard label="Alarms · 24h" value={metrics.alarmsProcessed24h} />
          <MetricsCard
            label="Remediation rate"
            value={`${Math.round(metrics.remediationSuccessRate * 100)}%`}
            tone="active"
          />
          <MetricsCard label="Avg latency" value={`${(metrics.avgAgentLatencyMs / 1000).toFixed(1)}s`} />
          <MetricsCard label="Monthly spend" value={`$${metrics.monthlySpend.toLocaleString()}`} />
          <MetricsCard
            label="Savings found"
            value={`$${metrics.savingsIdentified.toLocaleString()}`}
            tone="signal"
            hint="via FinOps sweep"
          />
        </div>
      )}

      {/* Recent runs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <p className="eyebrow">Recent runs</p>
          <Link to="/incidents" className="flex items-center gap-1 text-xs text-muted hover:text-active transition-colors">
            View all <ArrowUpRight size={12} />
          </Link>
        </div>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {runs.map((run) => (
            <IncidentCard key={run.id} run={run} />
          ))}
        </div>
      </div>
    </div>
  )
}
