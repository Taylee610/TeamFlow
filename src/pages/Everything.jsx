import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'react-toastify'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import LoadingState from '../components/LoadingState'

const STATUS_LABELS = { todo: 'To Do', in_progress: 'In Progress', done: 'Done' }
const STATUS_STYLES = {
  todo: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
  in_progress: 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300',
  done: 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300',
}
const PRIORITY_STYLES = {
  low: 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
  medium: 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300',
  high: 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300',
}

export default function Everything() {
  const { user } = useAuth()
  const [tasks, setTasks] = useState(null)
  const [projects, setProjects] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [projectFilter, setProjectFilter] = useState('all')
  const [mineOnly, setMineOnly] = useState(false)
  const [search, setSearch] = useState('')

  function reload() {
    api.get('/tasks/?page_size=200').then(({ data }) => setTasks(data.results ?? data))
    api.get('/projects/?page_size=200').then(({ data }) => setProjects(data.results ?? data))
  }

  useEffect(reload, [])

  const projectById = useMemo(() => {
    const map = new Map()
    ;(projects || []).forEach((p) => map.set(p.id, p))
    return map
  }, [projects])

  async function handleStatusChange(task, status) {
    try {
      await api.patch(`/tasks/${task.id}/`, { status })
      reload()
    } catch {
      toast.error("Could not update status -- you may not have permission.")
    }
  }

  const filtered = useMemo(() => {
    if (!tasks) return []
    return tasks
      .filter((t) => statusFilter === 'all' || t.status === statusFilter)
      .filter((t) => projectFilter === 'all' || String(t.project) === String(projectFilter))
      .filter((t) => !mineOnly || t.assigned_to === user?.id)
      .filter((t) => !search.trim() || t.title.toLowerCase().includes(search.trim().toLowerCase()))
      .sort((a, b) => {
        if (!a.due_date && !b.due_date) return 0
        if (!a.due_date) return 1
        if (!b.due_date) return -1
        return new Date(a.due_date) - new Date(b.due_date)
      })
  }, [tasks, statusFilter, projectFilter, mineOnly, search, user])

  if (!tasks || !projects) {
    return <LoadingState label="Loading everything..." />
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Everything</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Every task across every project you belong to, in one place.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search tasks..."
          className="rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
        >
          <option value="all">All statuses</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="rounded-lg border border-slate-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
        >
          <option value="all">All projects</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <label className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-300 px-1">
          <input type="checkbox" checked={mineOnly} onChange={(e) => setMineOnly(e.target.checked)} />
          Assigned to me
        </label>
      </div>

      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
        {filtered.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-slate-500 dark:text-slate-400">
            Nothing matches those filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wide border-b border-slate-100 dark:border-slate-700">
                  <th className="px-5 py-3 font-medium">Title</th>
                  <th className="px-5 py-3 font-medium">Project</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Priority</th>
                  <th className="px-5 py-3 font-medium">Due</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                {filtered.map((task) => {
                  const overdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done'
                  const project = projectById.get(task.project)
                  return (
                    <tr key={task.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                      <td className="px-5 py-3">
                        <span className="font-medium text-slate-800 dark:text-slate-200">{task.title}</span>
                        {overdue && (
                          <span className="ml-2 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300">
                            Overdue
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        {project ? (
                          <Link to={`/projects/${project.id}`} className="text-brand-600 dark:text-brand-400 hover:underline">
                            {project.name}
                          </Link>
                        ) : (
                          <span className="text-slate-400 dark:text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(task, e.target.value)}
                          className={`text-xs font-medium px-2 py-1 rounded-full border-0 focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400 ${STATUS_STYLES[task.status]}`}
                        >
                          {Object.entries(STATUS_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium}`}>
                          {task.priority || 'medium'}
                        </span>
                      </td>
                      <td className={`px-5 py-3 ${overdue ? 'text-red-500 dark:text-red-400 font-medium' : 'text-slate-500 dark:text-slate-400'}`}>
                        {task.due_date ? new Date(task.due_date).toLocaleDateString() : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
