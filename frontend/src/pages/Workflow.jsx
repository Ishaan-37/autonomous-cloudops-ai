import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, XCircle, Clock, AlertTriangle, Loader2 } from 'lucide-react'
import { subscribeToRuns } from '../services/api'
import WorkflowGraph from '../components/WorkflowGraph'

const STATUS_ICON = {
  running: <Clock size={14} className="text-signal" />,
  completed: <CheckCircle2 size={14} className="text-active" />,
  failed: <XCircle size={14} className="text-danger" />
}

// GitHub-Actions-style status for an individual timeline step.
// success | warning | error | running
const STEP_ICON = {
  success: <CheckCircle2 size={16} className="text-active shrink-0" />,
  warning: <AlertTriangle size={16} className="text-signal shrink-0" />,
  error: <XCircle size={16} className="text-danger shrink-0" />,
  running: <Loader2 size={16} className="text-active shrink-0 animate-spin" />
}

const STEP_BORDER = {
  success: 'border-l-active/50',
  warning: 'border-l-signal/50',
  error: 'border-l-danger/50',
  running: 'border-l-active/50'
}

function AnimatedDots() {
  const [n, setN] = useState(1)
  useEffect(() => {
    const t = setInterval(() => setN((v) => (v % 3) + 1), 450)
    return () => clearInterval(t)
  }, [])
  return <span className="inline-block w-4 text-active">{'.'.repeat(n)}</span>
}

// Infers a step status from timeline note text so mock data (which has
// no explicit status field) still renders correctly. Real backend data
// should set `status` explicitly once node-level events are wired up.
function inferStatus(event) {
  if (event.status) return event.status
  const note = (event.note || '').toLowerCase()
  if (note.includes('fail') || note.includes('error')) return 'error'
  if (note.includes('slow') || note.includes('waiting') || note.includes('timeout')) return 'warning'
  return 'success'
}

export default function Workflow() {
  const [params] = useSearchParams()
  const runId = params.get('run')
  const [runs, setRuns] = useState([])

  useEffect(() => {
    const unsubscribe = subscribeToRuns(setRuns, 3000)
    return unsubscribe
  }, [])

  const run = runs.find((r) => r.id === runId) || runs[0]

  if (runs.length === 0) {
    return <div className="p-8 text-sm text-muted">Loading…</div>
  }

  if (!run) {
    return (
      <div className="p-8">
        <div className="card p-10 text-center">
          <p className="text-sm text-muted">No run found for that ID.</p>
          <Link to="/incidents" className="text-active text-sm mt-2 inline-block">← Back to incidents</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-6">
      <Link to="/incidents" className="flex items-center gap-1.5 text-sm text-muted hover:text-ink w-fit">
        <ArrowLeft size={14} /> Back to incidents
      </Link>

      {/* Header card */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <p className="font-mono text-xs text-faint">{run.id}</p>
            <h2 className="font-display font-semibold text-xl mt-1">{run.alarm}</h2>
            <div className="flex items-center gap-2 mt-2">
              {STATUS_ICON[run.status]}
              <span className="text-sm text-muted capitalize">{run.status}</span>
              <span className="text-faint">·</span>
              <span className="text-sm text-muted font-mono">{run.instance}</span>
              {run.status === 'running' && (
                <>
                  <span className="text-faint">·</span>
                  <span className="flex items-center gap-1.5 text-xs text-active">
                    <span className="h-1.5 w-1.5 rounded-full bg-active animate-pulse" /> live
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <WorkflowGraph currentStage={run.stage} />

        {run.stage === 'approve' && run.status === 'running' && (
          <div className="mt-6 flex items-center justify-between rounded-lg border border-signal/30 bg-signal-dim px-4 py-3">
            <p className="text-sm text-ink">Waiting on approval to remediate.</p>
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

      <div className="grid md:grid-cols-2 gap-4">
        {/* Root cause + plan */}
        <div className="card p-6 space-y-4">
          <div>
            <p className="eyebrow mb-2">Root cause</p>
            <p className="text-sm text-ink leading-relaxed">{run.rootCause}</p>
          </div>
          {run.plan && (
            <div>
              <p className="eyebrow mb-2">Remediation plan</p>
              <p className="text-sm text-ink leading-relaxed">{run.plan}</p>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="card p-6">
          <p className="eyebrow mb-4">Timeline</p>
          <div className="space-y-2">
            {run.timeline.map((event, i) => {
              const status = inferStatus(event)
              const isLast = i === run.timeline.length - 1
              const isRunning = isLast && run.status === 'running' && status !== 'error'
              const effectiveStatus = isRunning ? 'running' : status

              return (
                <div
                  key={i}
                  className={`flex items-start gap-3 border-l-2 ${STEP_BORDER[effectiveStatus]} pl-3 py-1.5`}
                >
                  {STEP_ICON[effectiveStatus]}
                  <div className="min-w-0">
                    <p className="font-mono text-[10px] uppercase tracking-wide text-muted">{event.stage}</p>
                    <p className="text-sm text-ink mt-0.5">
                      {event.note}
                      {isRunning && <AnimatedDots />}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
