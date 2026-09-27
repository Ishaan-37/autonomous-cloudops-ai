import { STAGES } from '../data/mock'

const LABELS = {
  ingest: 'Ingest',
  analyze: 'Analyze',
  plan: 'Plan',
  approve: 'Approve',
  remediate: 'Remediate',
  report: 'Report'
}

// Renders the 6-stage LangGraph pipeline as a live rail.
//
// Preferred: pass `stages`, a {stageName: status} dict where status is
// one of completed | running | pending | failed - this is what the
// backend's compute_stages() now returns on /runs and /runs/{id}.
//
// Fallback: pass `currentStage` (a single stage name) for mock data or
// older call sites - status is inferred from index position.
export default function WorkflowGraph({ currentStage, stages, compact = false }) {
  const currentIdx = STAGES.indexOf(currentStage)

  const statusFor = (stage, i) => {
    if (stages) return stages[stage] || 'pending'
    if (i < currentIdx) return 'completed'
    if (i === currentIdx) return stage === 'approve' ? 'running-approve' : 'running'
    return 'pending'
  }

  return (
    <div className={`flex items-center ${compact ? 'gap-1' : 'gap-2'}`}>
      {STAGES.map((stage, i) => {
        const status = statusFor(stage, i)
        const isApprovePulse = status === 'running-approve' || (status === 'running' && stage === 'approve')
        const isActive = status === 'running' || status === 'running-approve'
        const isDone = status === 'completed'
        const isFailed = status === 'failed'

        const dotColor = isFailed
          ? 'bg-danger'
          : isDone
            ? 'bg-active'
            : isApprovePulse
              ? 'bg-signal'
              : isActive
                ? 'bg-active'
                : 'bg-faint/40'

        const labelColor = isFailed
          ? 'text-danger'
          : isActive
            ? (isApprovePulse ? 'text-signal' : 'text-active')
            : isDone
              ? 'text-muted'
              : 'text-faint'

        const lineColor = (isDone || isFailed) ? 'bg-active/50' : 'bg-border'

        return (
          <div key={stage} className="flex items-center flex-1">
            <div className="flex flex-col items-center gap-1.5 min-w-0">
              <div className={`relative h-2.5 w-2.5 rounded-full shrink-0 transition-colors ${dotColor}`}>
                {isActive && (
                  <span
                    className={`absolute inset-0 rounded-full animate-pulseRing
                      ${isApprovePulse ? 'shadow-signalGlow' : ''}`}
                  />
                )}
              </div>
              {!compact && (
                <span className={`font-mono text-[10px] uppercase tracking-wide whitespace-nowrap ${labelColor}`}>
                  {LABELS[stage]}
                </span>
              )}
            </div>
            {i < STAGES.length - 1 && (
              <div className={`h-px flex-1 mx-1 ${lineColor}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
