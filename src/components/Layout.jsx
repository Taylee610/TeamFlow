import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import IconRail from './IconRail'
import { NavLink } from 'react-router-dom'
import { BarChart3, BookOpen, FileText, Landmark, Package, Scale } from 'lucide-react'
import WorkspaceActions from './WorkspaceActions'

export default function Layout() {
  const { user, logout } = useAuth()
  const [workspaceAction, setWorkspaceAction] = useState(null)

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-900 transition-colors">
      <IconRail
        onCreateClick={() => setWorkspaceAction('create')}
        onSearchClick={() => setWorkspaceAction('search')}
      />

      <aside className="w-64 shrink-0 bg-white dark:bg-slate-800 border-r border-slate-200 dark:border-slate-700 flex flex-col transition-colors">
        <div className="h-16 flex items-center gap-2 px-5 border-b border-slate-200 dark:border-slate-700">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold">
            T
          </div>
          <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-slate-100">Taylee ERP</span>
        </div>

        {/* Workspace/project context panel -- filled in during the board-header
            and column pieces (e.g. project switcher, Tasks/Files/Discussions). */}
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          <p className="px-3 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
            Workspace
          </p>
          {[
            ['/erp', 'Finance overview', Landmark],
            ['/erp?view=accounts', 'Chart of accounts', BookOpen],
            ['/erp?view=journals', 'Journal entries', FileText],
            ['/erp?view=procurement', 'Procurement', Package],
            ['/erp?view=reports', 'Trial balance', BarChart3],
            ['/erp?view=reconciliation', 'Reconciliation', Scale],
          ].map(([to, label, Icon]) => <NavLink key={to} to={to} className="mt-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"><Icon size={17} />{label}</NavLink>)}
        </nav>

        <div className="p-3 border-t border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
              {(user?.email || '?').slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate text-slate-900 dark:text-slate-100">
                {user?.first_name || user?.email}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-2 w-full text-left px-3 py-2 rounded-lg text-sm text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            Log out
          </button>
        </div>
      </aside>

      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
      <WorkspaceActions mode={workspaceAction} onClose={() => setWorkspaceAction(null)} />
    </div>
  )
}
