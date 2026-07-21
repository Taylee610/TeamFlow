import { NavLink } from 'react-router-dom'
import {
  Plus, Search, FolderKanban, Globe2, BarChart3,
  Users, MessageSquare, Settings, HelpCircle, Sun, Moon, Landmark, Bot,
} from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

// Icons that go to a real route in the app today.
const primaryItems = [
  { to: '/erp', label: 'ERP Finance', icon: Landmark },
  { to: '/ai', label: 'Taylee AI', icon: Bot },
  { to: '/everything', label: 'Everything', icon: Globe2 },
  { to: '/projects', label: 'Projects', icon: FolderKanban },
  { to: '/people', label: 'People', icon: Users },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/dashboard', label: 'Reports', icon: BarChart3 },
]
export default function IconRail({ onCreateClick, onSearchClick }) {
  const { theme, toggleTheme } = useTheme()

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
      </div>

      <button
        onClick={toggleTheme}
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        className="h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center transition-colors"
      >
        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </button>
      <NavLink to="/settings" title="Settings" className="mt-1 h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center">
        <Settings size={20} />
      </NavLink>
      <NavLink to="/help" title="Help" className="mt-1 h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center">
        <HelpCircle size={20} />
      </NavLink>
    </div>
  )
}
