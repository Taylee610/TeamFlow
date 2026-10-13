import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await login(email, password)
      navigate(sessionStorage.getItem('workspace_invite') ? '/workspaces' : '/dashboard')
    } catch (err) {
      toast.error('Invalid email or password.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-900 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="h-12 w-12 mx-auto rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white font-bold text-xl">
            T
          </div>
          <h1 className="mt-4 text-2xl font-bold text-slate-900 dark:text-slate-100">Welcome back</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Log in to your TeamFlow workspace</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium text-sm transition-colors"
          >
            {submitting ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500 dark:text-slate-400 mt-6">
          <Link to="/account/reset" className="block mb-3 text-brand-600 hover:underline">Forgot your password?</Link>
          No account?{' '}
          <Link to="/signup" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
