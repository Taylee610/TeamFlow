import { NavLink } from 'react-router-dom'
import {
  Plus, Search, FolderKanban, Globe2, BarChart3,
  Users, MessageSquare, Settings, HelpCircle,
} from 'lucide-react'

// Icons that go to a real route in the app today.
const primaryItems = [
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/dashboard', label: 'Reports', icon: BarChart3 },
]

// Icons that don't have a page yet — shown so the rail reads complete,
// but they don't navigate anywhere until those features exist.
const stubItems = [
  { label: 'Everything', icon: Globe2 },
  { label: 'People', icon: Users },
]
export default function IconRail({ onCreateClick, onSearchClick }) {
  return (
    <div className="w-16 shrink-0 bg-slate-900 flex flex-col items-center py-4">
      <button
        onClick={onCreateClick}
        title="Create"
        className="h-10 w-10 rounded-xl bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-center transition-colors"
      >
        <Plus size={20} />
      </button>

      <button
        onClick={onSearchClick}
        title="Search"
        className="mt-4 h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center transition-colors"
      >
        <Search size={20} />
      </button>

      <div className="mt-2 flex-1 flex flex-col items-center gap-1 w-full">
        {primaryItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            title={label}
            className={({ isActive }) =>
              `h-10 w-10 rounded-xl flex items-center justify-center transition-colors ${
                isActive
                  ? 'bg-slate-800 text-brand-400'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              }`
            }
          >
            <Icon size={20} />
          </NavLink>
        ))}

        {stubItems.map(({ label, icon: Icon }) => (
          <button
            key={label}
            title={`${label} — coming soon`}
            className="h-10 w-10 rounded-xl text-slate-600 flex items-center justify-center cursor-not-allowed"
          >
            <Icon size={20} />
          </button>
        ))}
      </div>

      <button
        title="Settings — coming soon"
        className="h-10 w-10 rounded-xl text-slate-600 flex items-center justify-center cursor-not-allowed"
      >
        <Settings size={20} />
      </button>
      <button
        title="Help — coming soon"
        className="mt-1 h-10 w-10 rounded-xl text-slate-600 flex items-center justify-center cursor-not-allowed"
      >
        <HelpCircle size={20} />
      </button>
    </div>
  )
}