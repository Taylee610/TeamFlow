import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ roles }) {
  const { user, isAuthenticated, loading, workspace } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 text-slate-400 dark:text-slate-500 text-sm">
        Loading...
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (!workspace && location.pathname !== '/workspaces') return <Navigate to="/workspaces" replace />

  if (roles && !roles.includes(workspace?.role)) {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}
