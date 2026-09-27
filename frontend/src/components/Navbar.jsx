import { Bell, Search } from 'lucide-react'

export default function Navbar({ title, subtitle }) {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/80 backdrop-blur px-8 py-5 flex items-center justify-between">
      <div>
        <h1 className="font-display text-xl font-semibold">{title}</h1>
        {subtitle && <p className="text-sm text-muted mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-surface text-muted text-sm w-64">
          <Search size={14} />
          <span className="font-mono text-xs">Search runs, alarms…</span>
        </div>
        <button className="relative h-9 w-9 rounded-lg border border-border bg-surface flex items-center justify-center text-muted hover:text-ink transition-colors">
          <Bell size={16} />
          <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-signal" />
        </button>
        <div className="h-9 w-9 rounded-lg bg-raised border border-border flex items-center justify-center font-mono text-xs text-muted">
          IM
        </div>
      </div>
    </header>
  )
}
