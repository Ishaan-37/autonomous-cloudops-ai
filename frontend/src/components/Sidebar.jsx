import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Siren, GitBranch, Activity,
  Boxes, ScrollText, PiggyBank, Settings
} from 'lucide-react'

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/incidents', label: 'Incidents', icon: Siren },
  { to: '/workflow', label: 'Workflow', icon: GitBranch },
  { to: '/monitoring', label: 'Monitoring', icon: Activity },
  { to: '/kubernetes', label: 'Kubernetes', icon: Boxes },
  { to: '/logs', label: 'Logs', icon: ScrollText },
  { to: '/costs', label: 'Costs', icon: PiggyBank },
  { to: '/settings', label: 'Settings', icon: Settings }
]

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 border-r border-border bg-surface/60 backdrop-blur flex flex-col">
      <div className="px-5 py-6">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-md bg-active/20 border border-active/40 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-active animate-pulseRing" />
          </div>
          <span className="font-display font-semibold text-[15px] tracking-tight">CloudOps AI</span>
        </div>
        <p className="eyebrow mt-2">Mission Control</p>
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors
               ${isActive
                 ? 'bg-raised text-ink border border-border'
                 : 'text-muted hover:text-ink hover:bg-raised/60 border border-transparent'}`
            }
          >
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted">
          <div className="h-1.5 w-1.5 rounded-full bg-active" />
          Agent online
        </div>
      </div>
    </aside>
  )
}
