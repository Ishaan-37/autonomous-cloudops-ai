export default function MetricsCard({ label, value, hint, tone = 'default' }) {
  const toneClass = {
    default: 'text-ink',
    active: 'text-active',
    signal: 'text-signal',
    danger: 'text-danger'
  }[tone]

  return (
    <div className="card p-5 min-w-0">
      <p className="eyebrow truncate">{label}</p>
      <p className={`font-display text-2xl font-semibold mt-2 truncate ${toneClass}`}>{value}</p>
      {hint && <p className="text-xs text-muted mt-1 truncate">{hint}</p>}
    </div>
  )
}
