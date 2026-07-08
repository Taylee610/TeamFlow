import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
} from 'recharts'
import api from '../api/axios'

const STATUS_LABELS = { todo: 'To Do', in_progress: 'In Progress', done: 'Done' }
const STATUS_COLORS = { todo: '#94a3b8', in_progress: '#6366f1', done: '#22c55e' }

function fetchAll(url) {
  // Walks every paginated page and returns the full flattened list.
  return api.get(url).then(({ data }) => data.results ?? data)
}

export default function Dashboard() {
  const [projects, setProjects] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      fetchAll('/projects/?page_size=200'),
      fetchAll('/tasks/?page_size=200'),
    ])
      .then(([projectsData, tasksData]) => {
        setProjects(projectsData)
        setTasks(tasksData)
      })
      .catch(() => setError('Could not load dashboard data.'))
  }, [])

  const stats = useMemo(() => {
    if (!tasks || !projects) return null

    const openTasks = tasks.filter((t) => t.status !== 'done').length
    const completedTasks = tasks.filter((t) => t.status === 'done').length
    const activeProjects = projects.length

    const memberIds = new Set(projects.map((p) => p.owner?.id))
    tasks.forEach((t) => t.assigned_to && memberIds.add(t.assigned_to))
    const teamMembers = memberIds.size

    const statusCounts = ['todo', 'in_progress', 'done'].map((key) => ({
      key,
      name: STATUS_LABELS[key],
      value: tasks.filter((t) => t.status === key).length,
    }))

    const now = new Date()
    const dailyCompleted = []
    for (let i = 6; i >= 0; i--) {
      const day = new Date(now)
      day.setDate(now.getDate() - i)
      const dayStr = day.toISOString().slice(0, 10)
      const count = tasks.filter(
        (t) => t.status === 'done' && t.updated_at?.slice(0, 10) === dayStr
      ).length
      dailyCompleted.push({
        day: day.toLocaleDateString(undefined, { weekday: 'short' }),
        completed: count,
      })
    }

    const overdue = tasks
      .filter((t) => t.due_date && new Date(t.due_date) < now && t.status !== 'done')
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      .slice(0, 5)

    const projectProgress = projects.slice(0, 6).map((p) => {
      const projectTasks = tasks.filter((t) => t.project === p.id)
      const done = projectTasks.filter((t) => t.status === 'done').length
      return { ...p, taskTotal: projectTasks.length, doneCount: done }
    })

    return { openTasks, completedTasks, activeProjects, teamMembers, statusCounts, dailyCompleted, overdue, projectProgress }
  }, [tasks, projects])

  if (error) {
    return <div className="p-6 text-sm text-red-600">{error}</div>
  }

  if (!stats) {
    return <div className="p-6 text-sm text-slate-400">Loading dashboard...</div>
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-lg font-semibold text-slate-900">Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Open Tasks" value={stats.openTasks} sub="Tasks pending" color="brand" />
        <KpiCard label="Completed" value={stats.completedTasks} sub="Tasks done" color="green" />
        <KpiCard label="Active Projects" value={stats.activeProjects} sub="In progress" color="amber" />
        <KpiCard label="Team Members" value={stats.teamMembers} sub="Collaborators" color="purple" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Tasks completed — last 7 days</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={stats.dailyCompleted}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#64748b' }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748b' }} />
              <Tooltip />
              <Line type="monotone" dataKey="completed" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Tasks by status</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={stats.statusCounts}
                dataKey="value"
                nameKey="name"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={2}
              >
                {stats.statusCounts.map((entry) => (
                  <Cell key={entry.key} fill={STATUS_COLORS[entry.key]} />
                ))}
              </Pie>
              <Legend verticalAlign="bottom" height={24} />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Projects */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-900">Your Projects</h3>
            <Link to="/projects" className="text-xs text-brand-600 hover:underline">View all</Link>
          </div>
          {stats.projectProgress.length ? (
            <div className="space-y-4">
              {stats.projectProgress.map((p) => {
                const pct = p.taskTotal ? Math.round((p.doneCount / p.taskTotal) * 100) : 0
                return (
                  <Link key={p.id} to={`/projects/${p.id}`} className="block group">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-800 group-hover:text-brand-600">{p.name}</span>
                      <span className="text-xs text-slate-500">{p.doneCount}/{p.taskTotal} tasks</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div className="h-full bg-brand-500 rounded-full" style={{ width: `${pct}%` }} />
                    </div>
                  </Link>
                )
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              No projects yet. <Link to="/projects" className="text-brand-600 hover:underline">Create one</Link>.
            </p>
          )}
        </div>

        {/* Overdue */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">
            Overdue Tasks
            {stats.overdue.length > 0 && (
              <span className="ml-2 text-xs px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">
                {stats.overdue.length}
              </span>
            )}
          </h3>
          {stats.overdue.length ? (
            <ul className="space-y-3">
              {stats.overdue.map((task) => (
                <li key={task.id}>
                  <p className="text-sm font-medium text-slate-800 truncate">{task.title}</p>
                  <p className="text-xs text-red-500">
                    Due {new Date(task.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">Nothing overdue. Nice work!</p>
          )}
        </div>
      </div>
    </div>
  )
}

function KpiCard({ label, value, sub, color }) {
  const colorMap = {
    brand: 'bg-brand-50 text-brand-600',
    green: 'bg-green-50 text-green-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
  }
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        <span className={`h-8 w-8 rounded-lg flex items-center justify-center ${colorMap[color]}`}>●</span>
      </div>
      <p className="text-3xl font-bold mt-3 text-slate-900">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{sub}</p>
    </div>
  )
}