import { useEffect, useMemo, useState } from 'react'
import { getRuns } from '../services/api'
import IncidentCard from '../components/IncidentCard'
import { Search } from 'lucide-react'

const SEVERITIES = ['all', 'high', 'medium', 'low']
const STATUSES = ['all', 'running', 'completed', 'failed']

export default function Incidents() {
  const [runs, setRuns] = useState([])
  const [severity, setSeverity] = useState('all')
  const [status, setStatus] = useState('all')
  const [query, setQuery] = useState('')

  useEffect(() => { getRuns().then(setRuns) }, [])

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      if (severity !== 'all' && r.severity !== severity) return false
      if (status !== 'all' && r.status !== status) return false
      if (query && !r.alarm.toLowerCase().includes(query.toLowerCase()) && !r.id.includes(query)) return false
      return true
    })
  }, [runs, severity, status, query])

  return (
    <div className="p-8 space-y-6">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border bg-surface flex-1 min-w-[200px] max-w-xs">
          <Search size={14} className="text-faint" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search alarm or run id…"
            className="bg-transparent outline-none text-sm font-mono w-full placeholder:text-faint"
          />
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg border border-border bg-surface">
          {SEVERITIES.map((s) => (
            <button
              key={s}
              onClick={() => setSeverity(s)}
              className={`px-3 py-1 rounded-md text-xs font-mono uppercase transition-colors
                ${severity === s ? 'bg-raised text-ink' : 'text-muted hover:text-ink'}`}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg border border-border bg-surface">
          {STATUSES.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={`px-3 py-1 rounded-md text-xs font-mono uppercase transition-colors
                ${status === s ? 'bg-raised text-ink' : 'text-muted hover:text-ink'}`}
            >
              {s}
            </button>
          ))}
        </div>

        <span className="ml-auto text-xs text-faint font-mono">{filtered.length} of {runs.length} runs</span>
      </div>

      {/* Results */}
      {filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <p className="text-sm text-muted">No runs match these filters.</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((run) => (
            <IncidentCard key={run.id} run={run} />
          ))}
        </div>
      )}
    </div>
  )
}
