import { CheckCircle2, XCircle } from 'lucide-react'

const CONNECTIONS = [
  { name: 'OpenAI', key: 'OPENAI_API_KEY', connected: true },
  { name: 'Pinecone', key: 'PINECONE_API_KEY', connected: true },
  { name: 'Slack', key: 'SLACK_BOT_TOKEN', connected: true },
  { name: 'AWS', key: 'AWS credentials', connected: true }
]

export default function Settings() {
  return (
    <div className="p-8 space-y-6 max-w-2xl">
      <div className="card p-6">
        <p className="eyebrow mb-4">Environment</p>
        <div className="flex items-center justify-between py-2">
          <span className="text-sm text-muted">Environment</span>
          <span className="font-mono text-sm text-ink">development</span>
        </div>
        <div className="flex items-center justify-between py-2 border-t border-border/60">
          <span className="text-sm text-muted">Slack channel</span>
          <span className="font-mono text-sm text-ink">#cloudops-alerts</span>
        </div>
        <div className="flex items-center justify-between py-2 border-t border-border/60">
          <span className="text-sm text-muted">EKS namespace</span>
          <span className="font-mono text-sm text-ink">cloudops-staging</span>
        </div>
      </div>

      <div className="card p-6">
        <p className="eyebrow mb-4">Connections</p>
        <div className="space-y-1">
          {CONNECTIONS.map((c) => (
            <div key={c.key} className="flex items-center justify-between py-2.5 border-b border-border/40 last:border-0">
              <div>
                <p className="text-sm text-ink">{c.name}</p>
                <p className="font-mono text-xs text-faint">{c.key}</p>
              </div>
              {c.connected
                ? <span className="flex items-center gap-1.5 text-xs text-active"><CheckCircle2 size={14} /> Connected</span>
                : <span className="flex items-center gap-1.5 text-xs text-danger"><XCircle size={14} /> Missing</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
