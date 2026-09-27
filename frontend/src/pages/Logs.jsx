import { useEffect, useState, useMemo, useRef, useCallback } from 'react'
import { getLogs } from '../services/api'
import { Search, Download } from 'lucide-react'

const LEVEL_STYLE = {
  INFO:    { text: 'text-muted',  bg: 'bg-muted/10' },
  WARN:    { text: 'text-signal', bg: 'bg-signal-dim' },
  ERROR:   { text: 'text-danger', bg: 'bg-danger-dim' },
  SUCCESS: { text: 'text-active', bg: 'bg-active-dim' }
}

const SOURCES = ['all', 'api.main', 'agent.graph', 'ingest_node', 'analyze_node', 'plan_node', 'approval_node', 'remediate_node', 'report_node']

const HIGHLIGHT_WORDS = ['error', 'failed', 'timeout', 'exception', 'refused', 'warning', 'quota', 'pinecone', 'openai']

function highlightMessage(msg) {
  const parts = msg.split(new RegExp(`(${HIGHLIGHT_WORDS.join('|')})`, 'gi'))
  return parts.map((part, i) =>
    HIGHLIGHT_WORDS.includes(part.toLowerCase())
      ? <mark key={i} className="bg-signal/20 text-signal rounded px-0.5">{part}</mark>
      : part
  )
}

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [levelFilter, setLevelFilter] = useState('all')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [query, setQuery] = useState('')
  const [live, setLive] = useState(true)
  const bottomRef = useRef(null)

  const fetchLogs = useCallback(async () => {
    const data = await getLogs()
    setLogs(data)
  }, [])

  useEffect(() => {
    fetchLogs()
    if (!live) return
    const interval = setInterval(fetchLogs, 3000)
    return () => clearInterval(interval)
  }, [live, fetchLogs])

  useEffect(() => {
    if (live) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, live])

  const filtered = useMemo(() => {
    return logs.filter((l) => {
      if (levelFilter !== 'all' && l.level !== levelFilter) return false
      if (sourceFilter !== 'all' && l.source !== sourceFilter) return false
      if (query && !l.msg.toLowerCase().includes(query.toLowerCase()) && !l.source.includes(query)) return false
      return true
    })
  }, [logs, levelFilter, sourceFilter, query])

  function exportLogs() {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cloudops-logs-${new Date().toISOString().slice(0, 19)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="p-8 space-y-4 flex flex-col h-[calc(100vh-80px)]">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-surface flex-1 min-w-[200px] max-w-xs">
          <Search size={14} className="text-faint shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search logs, source, alarm..."
            className="bg-transparent outline-none text-xs font-mono w-full placeholder:text-faint"
          />
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg border border-border bg-surface">
          {['all', 'INFO', 'WARN', 'ERROR'].map((f) => (
            <button
              key={f}
              onClick={() => setLevelFilter(f)}
              className={`px-3 py-1 rounded-md text-xs font-mono uppercase transition-colors
                ${levelFilter === f ? 'bg-raised text-ink' : 'text-muted hover:text-ink'}`}
            >
              {f}
            </button>
          ))}
        </div>

        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border bg-surface text-xs font-mono text-muted focus:text-ink outline-none"
        >
          {SOURCES.map((s) => (
            <option key={s} value={s}>{s === 'all' ? 'All sources' : s}</option>
          ))}
        </select>

        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setLive((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors
              ${live ? 'border-active/40 bg-active-dim text-active' : 'border-border bg-surface text-muted hover:text-ink'}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${live ? 'bg-active animate-pulse' : 'bg-faint'}`} />
            {live ? 'Live' : 'Paused'}
          </button>

          <button
            onClick={exportLogs}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-surface text-xs text-muted hover:text-ink transition-colors"
          >
            <Download size={13} />
            Export
          </button>
        </div>
      </div>

      <p className="text-xs text-faint font-mono">{filtered.length} of {logs.length} entries</p>

      <div className="card flex-1 p-4 font-mono text-xs leading-relaxed overflow-y-auto min-h-0">
        {filtered.length === 0 ? (
          <p className="text-muted">No log entries match these filters.</p>
        ) : (
          filtered.map((line, i) => (
            <div
              key={i}
              className={`flex gap-3 py-1 px-1 -mx-1 rounded hover:bg-raised/40 transition-colors
                ${line.level === 'ERROR' ? 'border-l-2 border-l-danger pl-2' : ''}
                ${line.level === 'WARN'  ? 'border-l-2 border-l-signal pl-2' : ''}`}
            >
              <span className="text-faint shrink-0 w-20">{line.ts}</span>
              <span className={`shrink-0 w-14 font-semibold ${(LEVEL_STYLE[line.level] || LEVEL_STYLE.INFO).text}`}>{line.level}</span>
              <span className="text-active shrink-0 w-32 truncate">{line.source}</span>
              <span className="text-ink flex-1">{highlightMessage(line.msg)}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
