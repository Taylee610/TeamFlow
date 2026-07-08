import { Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import IconRail from './IconRail'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <IconRail
        onCreateClick={() => { /* piece 2+: wire up create-task/project */ }}
        onSearchClick={() => { /* piece 2+: wire up global search */ }}
      />

      <aside className="w-64 shrink-0 bg-white border-r border-slate-200 flex flex-col">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-slate-200">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold">
            T
          </div>
          <span className="font-bold text-lg tracking-tight text-slate-900">TeamFlow</span>
        </div>

        {/* Workspace/project context panel -- filled in during the board-header
            and column pieces (e.g. project switcher, Tasks/Files/Discussions). */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Workspace
          </p>
        </nav>

        <div className="p-3 border-t border-slate-200">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
              {(user?.email || '?').slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate text-slate-900">
                {user?.first_name || user?.email}
              </p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-2 w-full text-left px-3 py-2 rounded-lg text-sm text-slate-500 hover:bg-slate-100"
          >
            Log out
          </button>
        </div>
      </aside>

      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  )
}