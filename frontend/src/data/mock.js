export const STAGES = ['ingest', 'analyze', 'plan', 'approve', 'remediate', 'report']

const timeline = (stage, opts = {}) => {
  const order = ['ingest', 'analyze', 'plan', 'approve', 'remediate', 'report']
  const idx = order.indexOf(stage)
  const notes = {
    ingest: 'Collected alarm metadata, CloudWatch logs, and instance context.',
    analyze: 'Retrieved relevant AWS docs via RAG. Identified likely root cause.',
    plan: 'Generated remediation plan: restart affected process, scale if recurs.',
    approve: 'Posted to #cloudops-alerts. Waiting on human approval.',
    remediate: 'Approved by on-call. Executing remediation steps.',
    report: 'Remediation verified. Incident report generated and archived.'
  }
  const labels = {
    ingest: 'Incident received',
    analyze: 'Knowledge base search',
    plan: 'AI remediation planning',
    approve: 'Awaiting approval',
    remediate: 'Executing remediation',
    report: 'Report generated'
  }
  return order.slice(0, idx + 1).map((s, i) => ({
    stage: s,
    label: labels[s],
    note: (opts.warnAt === s) ? opts.warnNote : notes[s],
    status: opts.warnAt === s ? 'warning' : (i < idx || opts.failAt !== s) ? 'success' : 'failed'
  }))
}

const reasoning = (overrides = {}) => ({
  rootCause: null,
  confidence: null,
  recommendedAction: null,
  ...overrides
})

export const runs = [
  {
    id: 'run_8f2a1c',
    alarm: 'cloudops-high-cpu-staging',
    severity: 'high',
    status: 'running',
    stage: 'approve',
    startedAt: '2026-07-26T09:12:00Z',
    instance: 'i-0abc1234def56789',
    rootCause: 'Runaway batch job pinning CPU at 94% on worker node.',
    plan: 'Restart batch worker process; cap concurrent jobs to prevent recurrence.',
    timeline: timeline('approve')
  },
  {
    id: 'run_3d9e77',
    alarm: 'cloudops-pod-crashloop',
    severity: 'medium',
    status: 'running',
    stage: 'remediate',
    startedAt: '2026-07-26T08:41:00Z',
    instance: 'pod/ingest-worker-7c9',
    rootCause: 'OOMKilled — memory limit too low for current batch size.',
    plan: 'Increase pod memory limit from 512Mi to 1Gi, redeploy.',
    timeline: timeline('remediate')
  },
  {
    id: 'run_1a44b2',
    alarm: 'cloudops-unattached-ebs',
    severity: 'low',
    status: 'completed',
    stage: 'report',
    startedAt: '2026-07-26T06:00:00Z',
    instance: 'vol-0e5f6a7b8c9d0e1f',
    rootCause: 'Idle volume detected during nightly FinOps sweep.',
    plan: 'Flag volume for deletion after 7-day grace period.',
    timeline: timeline('report')
  },
  {
    id: 'run_9c21ff',
    alarm: 'cloudops-disk-pressure',
    severity: 'medium',
    status: 'completed',
    stage: 'report',
    startedAt: '2026-07-25T22:14:00Z',
    instance: 'i-0f1e2d3c4b5a6978',
    rootCause: 'Log rotation misconfigured, /var filled to 96%.',
    plan: 'Force log rotation, apply corrected logrotate config.',
    timeline: timeline('report')
  },
  {
    id: 'run_2b88ad',
    alarm: 'cloudops-latency-spike-api',
    severity: 'high',
    status: 'failed',
    stage: 'analyze',
    startedAt: '2026-07-25T19:30:00Z',
    instance: 'svc/api-gateway',
    rootCause: 'Downstream Pinecone query timeout — RAG context unavailable.',
    plan: null,
    timeline: [
      { stage: 'ingest', status: 'success', note: 'Collected alarm metadata and CloudWatch context.' },
      { stage: 'analyze', status: 'success', note: 'Searching Pinecone for relevant AWS docs' },
      { stage: 'analyze', status: 'warning', note: 'Pinecone query slow (1.8s), continuing with partial context.' },
      { stage: 'analyze', status: 'error', note: 'Pinecone query failed — no matching documents found.' }
    ]
  }
]

export const metrics = {
  alarmsProcessed24h: 14,
  remediationSuccessRate: 0.91,
  avgAgentLatencyMs: 4200,
  monthlySpend: 3820.55,
  savingsIdentified: 412.10
}

// 7-day trend data for Monitoring page
export const latencyTrend = [
  { day: 'Mon', latencyMs: 3800, alarms: 9 },
  { day: 'Tue', latencyMs: 4100, alarms: 12 },
  { day: 'Wed', latencyMs: 3950, alarms: 8 },
  { day: 'Thu', latencyMs: 5200, alarms: 15 },
  { day: 'Fri', latencyMs: 4600, alarms: 11 },
  { day: 'Sat', latencyMs: 3400, alarms: 5 },
  { day: 'Sun', latencyMs: 4200, alarms: 14 }
]

export const successTrend = [
  { day: 'Mon', success: 0.88 },
  { day: 'Tue', success: 0.92 },
  { day: 'Wed', success: 0.85 },
  { day: 'Thu', success: 0.94 },
  { day: 'Fri', success: 0.90 },
  { day: 'Sat', success: 0.96 },
  { day: 'Sun', success: 0.91 }
]

export const tokenUsage = [
  { day: 'Mon', tokens: 42000 },
  { day: 'Tue', tokens: 58000 },
  { day: 'Wed', tokens: 39000 },
  { day: 'Thu', tokens: 71000 },
  { day: 'Fri', tokens: 63000 },
  { day: 'Sat', tokens: 21000 },
  { day: 'Sun', tokens: 55000 }
]

// Costs page data
export const costTrend = [
  { day: 'Mon', spend: 118 },
  { day: 'Tue', spend: 124 },
  { day: 'Wed', spend: 119 },
  { day: 'Thu', spend: 142 },
  { day: 'Fri', spend: 131 },
  { day: 'Sat', spend: 96 },
  { day: 'Sun', spend: 109 }
]

export const costByService = [
  { service: 'EKS', cost: 1840, color: '#4FD1C5' },
  { service: 'EC2', cost: 980, color: '#FF8A3D' },
  { service: 'S3', cost: 320, color: '#8A96A6' },
  { service: 'CloudWatch', cost: 410, color: '#5B6675' },
  { service: 'Other', cost: 270, color: '#2A3441' }
]

export const savingsOpportunities = [
  { id: 1, resource: 'vol-0e5f6a7b8c9d0e1f', type: 'Unattached EBS volume', monthlySavings: 18.40, status: 'flagged' },
  { id: 2, resource: 'i-0b2c3d4e5f6a7b8c', type: 'Idle EC2 instance (t3.large)', monthlySavings: 84.30, status: 'flagged' },
  { id: 3, resource: 'snap-0a1b2c3d4e5f6789', type: 'Orphaned snapshot', monthlySavings: 6.20, status: 'resolved' },
  { id: 4, resource: 'nat-0f9e8d7c6b5a4321', type: 'Unused NAT gateway', monthlySavings: 32.40, status: 'flagged' },
  { id: 5, resource: 'lb-0123456789abcdef', type: 'Idle load balancer', monthlySavings: 21.90, status: 'flagged' }
]

// Kubernetes page
export const pods = [
  { name: 'cloudops-agent-7c9d8f-x2k4p', namespace: 'cloudops-staging', status: 'Running', restarts: 0, cpu: '120m', memory: '340Mi', age: '2d' },
  { name: 'cloudops-agent-7c9d8f-m8n2q', namespace: 'cloudops-staging', status: 'Running', restarts: 0, cpu: '95m', memory: '310Mi', age: '2d' },
  { name: 'ingest-worker-7c9', namespace: 'cloudops-staging', status: 'CrashLoopBackOff', restarts: 4, cpu: '0m', memory: '0Mi', age: '3h' },
  { name: 'rag-indexer-4f8a1', namespace: 'cloudops-staging', status: 'Running', restarts: 1, cpu: '210m', memory: '512Mi', age: '5d' },
  { name: 'otel-collector-9b3c', namespace: 'observability', status: 'Running', restarts: 0, cpu: '40m', memory: '90Mi', age: '9d' }
]

export const nodes = [
  { name: 'ip-10-0-1-42.ec2.internal', status: 'Ready', cpuUsed: 62, memUsed: 71, pods: 8 },
  { name: 'ip-10-0-2-17.ec2.internal', status: 'Ready', cpuUsed: 38, memUsed: 54, pods: 6 }
]

// Logs page
export const logLines = [
  { ts: '01:28:49.068', level: 'INFO', source: 'api.main', msg: 'CloudOps Agent API starting (env=development)' },
  { ts: '01:28:49.071', level: 'INFO', source: 'api.main', msg: 'CloudOps Agent API ready' },
  { ts: '01:30:12.204', level: 'INFO', source: 'agent.graph', msg: 'Agent run started run_8f2a1c' },
  { ts: '01:30:12.410', level: 'INFO', source: 'ingest_node', msg: 'Collected CloudWatch context for i-0abc1234def56789' },
  { ts: '01:30:14.822', level: 'INFO', source: 'analyze_node', msg: 'RAG retrieval returned 4 relevant docs' },
  { ts: '01:30:15.003', level: 'WARN', source: 'rag.query_engine', msg: 'Pinecone doc query slow (1.8s), continuing' },
  { ts: '01:30:22.117', level: 'ERROR', source: 'openai_service', msg: '429 insufficient_quota — falling back to rule-based analysis' },
  { ts: '01:30:22.340', level: 'INFO', source: 'plan_node', msg: 'Generated remediation plan (fallback mode)' },
  { ts: '01:30:22.501', level: 'INFO', source: 'approval_node', msg: 'Posted approval request to #cloudops-alerts' },
  { ts: '01:30:41.902', level: 'INFO', source: 'agent.graph', msg: 'Agent run complete run_8f2a1c' }
]
