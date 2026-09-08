import { createContext, useContext, useEffect, useState } from 'react'
import api from '../api/axios'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [workspaces, setWorkspaces] = useState([])
  const [workspace, setWorkspace] = useState(null)
  const [workspaceError, setWorkspaceError] = useState('')

  async function refreshWorkspaces(preferredId) {
    try {
      const { data } = await api.get('/workspaces/')
      const saved = String(preferredId || localStorage.getItem('workspace_id') || '')
      const selected = data.find(w => String(w.id) === saved) || (data.length === 1 ? data[0] : null)
      setWorkspaces(data)
      setWorkspace(selected)
      setWorkspaceError('')
      if (selected) localStorage.setItem('workspace_id', selected.id)
      else localStorage.removeItem('workspace_id')
      return selected
    } catch {
      setWorkspaceError('Could not load your workspaces. Please retry.')
      return null
    }
  }

  function selectWorkspace(selected) {
    localStorage.setItem('workspace_id', selected.id)
    window.location.assign('/dashboard')
  }

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get('/auth/me/')
      .then(async ({ data }) => { setUser(data); await refreshWorkspaces() })
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const { data } = await api.post('/auth/token/', { email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    const { data: me } = await api.get('/auth/me/')
    setUser(me)
    await refreshWorkspaces()
    return me
  }

  async function signup({ email, password, first_name, last_name }) {
    await api.post('/auth/signup/', { email, password, first_name, last_name })
    return login(email, password)
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('workspace_id')
    setUser(null)
    setWorkspace(null)
    setWorkspaces([])
  }

  const isAdmin = workspace?.role === 'admin'
  const isManagerOrAdmin = isAdmin

  const value = { user, loading, login, signup, logout, isAuthenticated: !!user, isAdmin, isManagerOrAdmin,
    workspaces, workspace, workspaceError, refreshWorkspaces, selectWorkspace }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside an AuthProvider')
  return ctx
}
