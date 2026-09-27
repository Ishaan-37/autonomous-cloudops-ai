import { runs, metrics, latencyTrend, successTrend, tokenUsage, costTrend, costByService, savingsOpportunities, pods, nodes, logLines } from '../data/mock'

// ── Backend wiring ──────────────────────────────────────────────
// USE_LIVE_BACKEND = false  → always use mock data (safe for demos
//   without a running backend, or before OpenAI billing is set up)
// USE_LIVE_BACKEND = true   → real endpoints where they exist,
//   automatic fallback to mock data if backend is unreachable
const USE_LIVE_BACKEND = true
const API_BASE = '' // vite.config.js proxies /runs, /health, /trigger, /approve, /reject → :8000

async function safeFetch(path, fallback, options = {}) {
  if (!USE_LIVE_BACKEND) return fallback
  try {
    const res = await fetch(`${API_BASE}${path}`, options)
    if (!res.ok) throw new Error(`${path} returned ${res.status}`)
    return await res.json()
  } catch (err) {
    console.warn(`[api] Live fetch failed for ${path}, using mock data.`, err.message)
    return fallback
  }
}

// Map a backend RUN_REGISTRY entry onto the shape frontend components expect.
// Falls back gracefully when per-node log_step() calls aren't wired yet.
function normalizeRun(r) {
  const hasRealTimeline = Array.isArray(r.timeline) && r.timeline.length > 0
  return {
    id:        r.run_id,
    alarm:     r.alarm_name   || 'unknown-alarm',
    severity:  r.severity     || 'medium',
    status:    r.status       || 'running',
    stage:     r.stage        || 'ingest',
    startedAt: r.started_at   ? new Date(r.started_at * 1000).toISOString() : new Date().toISOString(),
    instance:  r.instance     || '—',
    rootCause: r.root_cause   || (r.error ? `Run failed: ${r.error}` : 'Analysis pending — awaiting AI response.'),
    plan:      r.plan         || null,
    timeline:  hasRealTimeline
      ? r.timeline.map((e) => ({ stage: e.stage, status: e.status, note: e.message, time: e.time }))
      : [{ stage: r.stage || 'ingest', status: 'running', note: 'Live run — per-node timeline populates once agent/run_events.py is wired into node files.' }]
  }
}

// ── Runs — real backend ──────────────────────────────────────────
export const getRuns = async () => {
  const data    = await safeFetch('/runs', { runs })
  const rawRuns = data.runs ?? data
  return Array.isArray(rawRuns) && rawRuns.length && rawRuns[0]?.run_id
    ? rawRuns.map(normalizeRun)
    : rawRuns
}

export const getRun = async (id) => {
  const data = await safeFetch(`/runs/${id}`, runs.find(r => r.id === id))
  return data?.run_id ? normalizeRun(data) : data
}

// ── Approval — real backend ──────────────────────────────────────
// These call the dedicated /approve/{run_id} and /reject/{run_id}
// endpoints added to api/main.py (see updated main.py).
// Falls back to a no-op console log if the backend is unreachable.
export const approveRun = async (runId) => {
  if (!USE_LIVE_BACKEND) {
    console.log('[api] approveRun called (mock mode) for', runId)
    return { status: 'approved', run_id: runId }
  }
  const data = await safeFetch(
    `/approve/${runId}`,
    { status: 'approved', run_id: runId },
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  )
  return data
}

export const rejectRun = async (runId) => {
  if (!USE_LIVE_BACKEND) {
    console.log('[api] rejectRun called (mock mode) for', runId)
    return { status: 'rejected', run_id: runId }
  }
  const data = await safeFetch(
    `/reject/${runId}`,
    { status: 'rejected', run_id: runId },
    { method: 'POST', headers: { 'Content-Type': 'application/json' } }
  )
  return data
}

// ── Live subscription — polls /runs every N ms ───────────────────
export const subscribeToRuns = (callback, intervalMs = 4000) => {
  let cancelled = false
  const tick = async () => {
    const data = await getRuns()
    if (!cancelled) callback(data)
  }
  tick()
  const interval = setInterval(tick, intervalMs)
  return () => { cancelled = true; clearInterval(interval) }
}

// ── All five pages now hit real backend endpoints ────────────────
export const getMetrics = async () => {
  const data = await safeFetch('/metrics', metrics)
  return data
}

export const getMonitoringData = async () => {
  const data = await safeFetch('/monitoring', { latencyTrend, successTrend, tokenUsage })
  return data
}

export const getCostData = async () => {
  const data = await safeFetch('/costs', { costTrend, costByService, savingsOpportunities })
  return data
}

export const getKubernetesData = async () => {
  const data = await safeFetch('/kubernetes', { pods, nodes })
  return data
}

export const getLogs = async () => {
  const data = await safeFetch('/logs', logLines)
  // /logs returns a flat array; mock fallback is also a flat array
  return Array.isArray(data) ? data : logLines
}
