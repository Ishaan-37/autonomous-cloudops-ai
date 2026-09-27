import { Link } from 'react-router-dom'
import WorkflowGraph from './WorkflowGraph'

const SEVERITY = {
  high: 'text-danger border-danger/40 bg-danger-dim',
  medium: 'text-signal border-signal/40 bg-signal-dim',
  low: 'text-active border-active/40 bg-active-dim'
}

const STATUS_DOT = {
  running: 'bg-signal animate-pulse',
  completed: 'bg-active',
  failed: 'bg-danger'
}

export default function IncidentCard({ run }) {
  return (
    <Link to={`/workflow?run=${run.id}`} className="card p-5 flex flex-col gap-4 hover:border-active/40 transition-colors block">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATUS_DOT[run.status] || 'bg-faint'}`} />
            <p className="font-mono text-xs text-faint">{run.id}</p>
          </div>
          <h3 className="font-display font-semibold text-sm mt-1.5 truncate">{run.alarm}</h3>
          <p className="text-xs text-muted mt-1 line-clamp-2">{run.rootCause}</p>
        </div>
        <span className={`shrink-0 text-[10px] font-mono uppercase tracking-wide px-2 py-1 rounded-md border ${SEVERITY[run.severity]}`}>
          {run.severity}
        </span>
      </div>
      <WorkflowGraph currentStage={run.stage} compact />
    </Link>
  )
}
