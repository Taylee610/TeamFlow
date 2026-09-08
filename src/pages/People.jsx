import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import LoadingState from '../components/LoadingState'

const ROLE_STYLES = {
  admin: 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300',
  manager: 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300',
  member: 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
}

export default function People() {
  const { user } = useAuth()
  const [projects, setProjects] = useState(null)

  useEffect(() => {
    api.get('/projects/?page_size=200').then(({ data }) => setProjects(data.results ?? data))
  }, [])

  const colleagues = useMemo(() => {
    if (!projects) return []
    const byId = new Map()
    projects.forEach((p) => {
      const members = [p.owner, ...(p.members || [])]
      members.forEach((m) => {
        if (!m || m.id === user?.id) return
        const entry = byId.get(m.id) || { person: m, projects: [] }
        if (!entry.projects.some((proj) => proj.id === p.id)) {
          entry.projects.push({ id: p.id, name: p.name })
        }
        byId.set(m.id, entry)
      })
    })
    return [...byId.values()].sort((a, b) =>
      (a.person.first_name || a.person.email).localeCompare(b.person.first_name || b.person.email)
    )
  }, [projects, user])

  if (!projects) {
    return <LoadingState label="Loading people..." />
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">People</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Everyone you share a project with.
        </p>
      </div>

      {colleagues.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-slate-800 border border-dashed border-slate-300 dark:border-slate-600 rounded-xl">
          <p className="text-slate-500 dark:text-slate-400 text-sm">
            You don't share a project with anyone yet.
          </p>
          <Link to="/projects" className="mt-3 inline-block text-sm text-brand-600 dark:text-brand-400 font-medium hover:underline">
            Add teammates to a project
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {colleagues.map(({ person, projects: sharedProjects }) => (
            <div
              key={person.id}
              className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5"
            >
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-brand-600 text-white flex items-center justify-center text-sm font-semibold shrink-0">
                  {(person.first_name || person.email || '?').slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold text-slate-900 dark:text-slate-100 truncate">
                    {person.first_name ? `${person.first_name} ${person.last_name || ''}`.trim() : person.email}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{person.email}</p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                <p className="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase tracking-wide mb-2">
                  Shared projects
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {sharedProjects.map((p) => (
                    <Link
                      key={p.id}
                      to={`/projects/${p.id}`}
                      className="text-xs px-2 py-1 rounded-full bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-600 dark:text-slate-300 transition-colors"
                    >
                      {p.name}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
