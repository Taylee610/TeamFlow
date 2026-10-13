import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, ArrowRight, Plus, Users } from 'lucide-react'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'

const inputStyle = 'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-900 dark:text-white'
const buttonStyle = 'rounded-lg bg-brand-600 px-4 py-2 text-white font-medium hover:bg-brand-700 disabled:opacity-50'

export default function Workspaces() {
  const { isAuthenticated, loading, user, workspaces, workspace, workspaceError, refreshWorkspaces, selectWorkspace, logout } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [inviteUrl, setInviteUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [members, setMembers] = useState([])
  const [invitations, setInvitations] = useState([])
  const [token, setToken] = useState(() => new URLSearchParams(window.location.search).get('invite') || sessionStorage.getItem('workspace_invite') || '')

  useEffect(() => {
    if (token) {
      sessionStorage.setItem('workspace_invite', token)
      window.history.replaceState({}, '', '/workspaces')
    }
  }, [token])

  useEffect(() => {
    if (!workspace) return
    api.get('/workspaces/members/').then(({ data }) => setMembers(data)).catch(() => setError('Could not load workspace members.'))
    if (workspace.role === 'admin') api.get('/workspaces/invitations/').then(({ data }) => setInvitations(data)).catch(() => setError('Could not load invitations.'))
  }, [workspace])

  async function perform(action) {
    setBusy(true); setError('')
    try { await action() } catch (err) {
      const data = err.response?.data
      setError(data && typeof data === 'object'
        ? Object.values(data).flat().join(' ')
        : 'The server could not save this change. Please check the backend terminal and retry.')
    } finally { setBusy(false) }
  }

  if (loading) return <div className="p-10 text-center">Loading workspaces…</div>

  return <main className="min-h-screen bg-slate-50 px-5 py-12 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
    <div className="mx-auto max-w-3xl space-y-7">
      <header className="flex items-start justify-between gap-4">
        <div><Building2 className="mb-4 text-brand-600" size={32} /><p className="text-sm font-medium text-brand-600">TeamFlow</p><h1 className="mt-1 text-3xl font-bold">Your team's workspace</h1><p className="mt-2 text-slate-500">Bring your people and projects together.</p></div>
        {isAuthenticated && <button onClick={logout} className="text-sm text-slate-500">Log out</button>}
      </header>
      {!isAuthenticated ? <section className="rounded-2xl border bg-white p-7 dark:border-slate-700 dark:bg-slate-900"><h2 className="text-xl font-semibold">{token ? 'You have a workspace invitation' : 'Get started with your team'}</h2><p className="my-4 text-slate-500">{token ? 'Sign in or create an account with the email address that received the invitation. You can accept it after signing in.' : 'Create an account to set up a workspace or join your team.'}</p><div className="flex gap-4"><Link className={buttonStyle} to="/signup">Create account</Link><Link className="px-4 py-2" to="/login">Sign in</Link></div></section> : <>
        {(error || workspaceError) && <div role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">{error || workspaceError}{workspaceError && <button className="ml-3 underline" onClick={() => refreshWorkspaces()}>Retry</button>}</div>}
        {token && <section className="rounded-2xl border border-brand-200 bg-white p-6 dark:bg-slate-900"><h2 className="font-semibold">Join your team</h2><p className="my-3 text-sm text-slate-500">Accepting as {user.email}. Invitations expire after seven days.</p><button disabled={busy} className={buttonStyle} onClick={() => perform(async () => {
          const { data } = await api.post('/workspaces/invitations/accept/', { token })
          sessionStorage.removeItem('workspace_invite'); setToken('')
          await refreshWorkspaces(data.id); selectWorkspace(data)
        })}>Accept invitation</button><button className="ml-4 text-sm text-slate-500" onClick={() => { sessionStorage.removeItem('workspace_invite'); setToken('') }}>Dismiss</button></section>}
        {workspaces.length > 0 && <section className="space-y-3"><h2 className="font-semibold">Choose a workspace</h2>{workspaces.map(w => <button key={w.id} onClick={() => selectWorkspace(w)} className="flex w-full items-center gap-4 rounded-xl border bg-white p-5 text-left hover:border-brand-500 dark:border-slate-700 dark:bg-slate-900"><Building2 className="text-brand-600" /><span className="flex-1"><span className="block font-semibold">{w.name}</span><span className="text-sm text-slate-500">{w.role === 'admin' ? 'Administrator' : 'Member'}{workspace?.id === w.id ? ' · Current workspace' : ''}</span></span><ArrowRight size={18} /></button>)}</section>}
        <form onSubmit={e => { e.preventDefault(); perform(async () => {
          const { data } = await api.post('/workspaces/', { name })
          await refreshWorkspaces(data.id); selectWorkspace(data)
        }) }} className="space-y-4 rounded-2xl border bg-white p-6 dark:border-slate-700 dark:bg-slate-900"><h2 className="flex items-center gap-2 font-semibold"><Plus size={18} />Create a workspace</h2><label className="block text-sm">Business or team name<input required maxLength={180} value={name} onChange={e => setName(e.target.value)} className={`${inputStyle} mt-2`} placeholder="e.g. Acme Studio" /></label><button disabled={busy || !name.trim()} className={buttonStyle}>Create workspace</button></form>
        {workspace?.role === 'admin' && <form onSubmit={e => { e.preventDefault(); perform(async () => {
          const { data } = await api.post('/workspaces/invitations/', { email })
          setInviteUrl(data.invite_url)
          setInvitations(current => [{ id: data.id, email: data.email, expires_at: data.expires_at }, ...current])
        }) }} className="space-y-4 rounded-2xl border bg-white p-6 dark:border-slate-700 dark:bg-slate-900"><h2 className="flex items-center gap-2 font-semibold"><Users size={18} />Invite to {workspace.name}</h2><p className="text-sm text-slate-500">Create a link for a teammate and share it with them. The link only works with their email address.</p><label className="block text-sm">Teammate email<input type="email" required value={email} onChange={e => { setEmail(e.target.value); setInviteUrl('') }} className={`${inputStyle} mt-2`} /></label><button disabled={busy} className={buttonStyle}>Create invitation link</button>{inviteUrl && <label className="block text-sm">Invitation link — select to copy<input readOnly value={inviteUrl} onFocus={e => e.target.select()} className={`${inputStyle} mt-2`} /></label>}</form>}
        {workspace?.role === 'admin' && invitations.length > 0 && <section className="rounded-2xl border bg-white p-6 dark:border-slate-700 dark:bg-slate-900"><h2 className="font-semibold">Pending invitations</h2><ul className="divide-y dark:divide-slate-700">{invitations.map(invitation => <li key={invitation.id} className="flex items-center justify-between gap-3 py-3 text-sm"><div>{invitation.email}<p className="text-xs text-slate-500">Expires {new Date(invitation.expires_at).toLocaleDateString()}</p></div><button disabled={busy} className="text-red-600" onClick={() => perform(async () => { await api.delete(`/workspaces/invitations/${invitation.id}/`); setInvitations(current => current.filter(i => i.id !== invitation.id)); setInviteUrl('') })}>Revoke</button></li>)}</ul></section>}
        {workspace && <section className="rounded-2xl border bg-white p-6 dark:border-slate-700 dark:bg-slate-900"><h2 className="mb-4 font-semibold">Members of {workspace.name}</h2><ul className="divide-y dark:divide-slate-700">{members.map(m => <li key={m.id} className="flex justify-between gap-3 py-3 text-sm"><span>{m.user.first_name || m.user.email}</span><span className="text-slate-500">{m.role}</span></li>)}</ul><Link to="/projects" className="mt-4 inline-block font-medium text-brand-600">Open projects →</Link></section>}
      </>}
    </div>
  </main>
}
