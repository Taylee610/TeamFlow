import { useAuth } from '../context/AuthContext'

export default function Dashboard() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
        <div className="flex items-center gap-2 font-bold text-lg text-slate-900">
          <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white">
            T
          </div>
          TeamFlow
        </div>
        <button
          onClick={logout}
          className="text-sm font-medium text-slate-500 hover:text-slate-800"
        >
          Log out
        </button>
      </header>
      <main className="p-6">
        <h1 className="text-xl font-semibold text-slate-900">
          Welcome, {user?.first_name || user?.email}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Login is fully wired up. Projects, tasks, and the real dashboard land in the next piece.
        </p>
      </main>
    </div>
  )
}