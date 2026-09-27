import { useEffect, useState } from 'react'
import { getKubernetesData } from '../services/api'

const STATUS_STYLE = {
  Running: 'text-active border-active/40 bg-active-dim',
  CrashLoopBackOff: 'text-danger border-danger/40 bg-danger-dim',
  Pending: 'text-signal border-signal/40 bg-signal-dim',
  Ready: 'text-active border-active/40 bg-active-dim'
}

function UsageBar({ pct }) {
  const tone = pct > 80 ? 'bg-danger' : pct > 60 ? 'bg-signal' : 'bg-active'
  return (
    <div className="h-1.5 w-24 rounded-full bg-raised overflow-hidden">
      <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export default function Kubernetes() {
  const [data, setData] = useState(null)

  useEffect(() => { getKubernetesData().then(setData) }, [])

  if (!data) return <div className="p-8 text-sm text-muted">Loading…</div>

  return (
    <div className="p-8 space-y-6">
      {/* Nodes */}
      <div className="card p-6">
        <p className="eyebrow mb-4">Cluster nodes</p>
        <div className="space-y-3">
          {data.nodes.map((n) => (
            <div key={n.name} className="flex items-center justify-between py-2.5 px-3 rounded-lg border border-border/60">
              <div className="flex items-center gap-3 min-w-0">
                <span className="h-2 w-2 rounded-full bg-active shrink-0" />
                <span className="font-mono text-sm text-ink truncate">{n.name}</span>
                <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md border shrink-0 ${STATUS_STYLE[n.status]}`}>
                  {n.status}
                </span>
              </div>
              <div className="flex items-center gap-6 shrink-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-faint font-mono w-8">CPU</span>
                  <UsageBar pct={n.cpuUsed} />
                  <span className="text-xs text-muted font-mono w-9">{n.cpuUsed}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-faint font-mono w-8">MEM</span>
                  <UsageBar pct={n.memUsed} />
                  <span className="text-xs text-muted font-mono w-9">{n.memUsed}%</span>
                </div>
                <span className="text-xs text-muted font-mono">{n.pods} pods</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pods */}
      <div className="card p-6">
        <p className="eyebrow mb-4">Pods · cloudops-staging</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-faint font-mono text-[10px] uppercase tracking-wide border-b border-border">
                <th className="pb-2 font-normal">Name</th>
                <th className="pb-2 font-normal">Namespace</th>
                <th className="pb-2 font-normal">Status</th>
                <th className="pb-2 font-normal">Restarts</th>
                <th className="pb-2 font-normal">CPU</th>
                <th className="pb-2 font-normal">Memory</th>
                <th className="pb-2 font-normal">Age</th>
              </tr>
            </thead>
            <tbody>
              {data.pods.map((p) => (
                <tr key={p.name} className="border-b border-border/40 last:border-0">
                  <td className="py-2.5 font-mono text-xs text-ink">{p.name}</td>
                  <td className="py-2.5 text-xs text-muted">{p.namespace}</td>
                  <td className="py-2.5">
                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-md border ${STATUS_STYLE[p.status] || 'text-muted border-border'}`}>
                      {p.status}
                    </span>
                  </td>
                  <td className="py-2.5 text-xs text-muted">
                    <span className={p.restarts > 0 ? 'text-signal' : ''}>{p.restarts}</span>
                  </td>
                  <td className="py-2.5 text-xs font-mono text-muted">{p.cpu}</td>
                  <td className="py-2.5 text-xs font-mono text-muted">{p.memory}</td>
                  <td className="py-2.5 text-xs text-faint">{p.age}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
