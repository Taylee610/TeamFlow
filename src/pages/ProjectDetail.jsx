import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import Modal from '../components/Modal'

const STATUS_LABELS = { todo: 'To Do', in_progress: 'In Progress', done: 'Done' }
const STATUS_STYLES = {
  todo: 'bg-slate-100 text-slate-600',
  in_progress: 'bg-blue-100 text-blue-700',
  done: 'bg-green-100 text-green-700',
}

export default function ProjectDetail() {
  const { id } = useParams()
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [notFound, setNotFound] = useState(false)

  function reload() {
    api.get(`/projects/${id}/`).then(({ data }) => setProject(data)).catch(() => setNotFound(true))
    api.get(`/tasks/?project=${id}&page_size=200`).then(({ data }) => setTasks(data.results ?? data))
  }

  useEffect(reload, [id])

  // Everyone who could plausibly be an assignee: the owner plus members.
  const people = useMemo(() => {
    if (!project) return []
    return [project.owner, ...project.members]
  }, [project])

  function nameFor(userId) {
    if (!userId) return 'Unassigned'
    if (userId === user?.id) return 'You'
    const person = people.find((p) => p.id === userId)
    return person ? (person.first_name || person.email) : `User #${userId}`
  }

  async function handleDeleteTask(taskId) {
    if (!confirm('Delete this task?')) return
    try {
      await api.delete(`/tasks/${taskId}/`)
      toast.success('Task deleted.')
      reload()
    } catch {
      toast.error("Could not delete task -- you may not have permission.")
    }
  }

  async function handleStatusChange(task, status) {
    try {
      await api.patch(`/tasks/${task.id}/`, { status })
      reload()
    } catch {
      toast.error("Could not update status -- you may not have permission.")
    }
  }

  const isOwner = project && user && project.owner?.id === user.id

  if (notFound) {
    return (
      <div className="p-6">
        <p className="text-sm text-slate-500">Project not found, or you don't have access to it.</p>
        <Link to="/projects" className="text-sm text-brand-600 hover:underline">Back to projects</Link>
      </div>
    )
  }

  if (!project || !tasks) {
    return <div className="p-6 text-sm text-slate-400">Loading...</div>
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <Link to="/projects" className="text-xs text-brand-600 hover:underline">&larr; Back to Projects</Link>
        <div className="flex items-start justify-between mt-2">
          <div>
            <h1 className="text-lg font-semibold text-slate-900">{project.name}</h1>
            <p className="text-sm text-slate-500 mt-1 max-w-xl">
              {project.description || 'No description yet.'}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Owned by {project.owner?.first_name || project.owner?.email}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Link
              to={`/projects/${project.id}/kanban`}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium"
            >
              Kanban
            </Link>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium"
            >
              + New Task
            </button>
          </div>
        </div>
      </div>

      <TeamPanel project={project} isOwner={isOwner} onChanged={reload} />

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">Tasks</h3>
        </div>
        {tasks.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-slate-500">
            No tasks yet.{' '}
            <button onClick={() => setShowCreate(true)} className="text-brand-600 hover:underline">
              Create the first one
            </button>.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 uppercase tracking-wide border-b border-slate-100">
                  <th className="px-5 py-3 font-medium">Title</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Due</th>
                  <th className="px-5 py-3 font-medium">Assignee</th>
                  <th className="px-5 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {tasks.map((task) => {
                  const overdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done'
                  return (
                    <tr key={task.id} className="hover:bg-slate-50">
                      <td className="px-5 py-3">
                        <span className="font-medium text-slate-800">{task.title}</span>
                        {overdue && (
                          <span className="ml-2 text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">
                            Overdue
                          </span>
                        )}
                        {task.description && (
                          <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{task.description}</p>
                        )}
                      </td>
                      <td className="px-5 py-3">
                        <select
                          value={task.status}
                          onChange={(e) => handleStatusChange(task, e.target.value)}
                          className={`text-xs font-medium px-2 py-1 rounded-full border-0 focus:ring-2 focus:ring-brand-500 ${STATUS_STYLES[task.status]}`}
                        >
                          {Object.entries(STATUS_LABELS).map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </select>
                      </td>
                      <td className={`px-5 py-3 ${overdue ? 'text-red-500 font-medium' : 'text-slate-500'}`}>
                        {task.due_date ? new Date(task.due_date).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-5 py-3 text-slate-500">{nameFor(task.assigned_to)}</td>
                      <td className="px-5 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => setEditingTask(task)}
                          className="text-xs font-medium text-brand-600 hover:underline"
                        >
                          Edit
                        </button>
                        {isOwner && (
                          <button
                            onClick={() => handleDeleteTask(task.id)}
                            className="ml-3 text-xs font-medium text-red-600 hover:underline"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <TaskFormModal
          projectId={project.id}
          people={people}
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false)
            reload()
          }}
        />
      )}
      {editingTask && (
        <TaskFormModal
          projectId={project.id}
          task={editingTask}
          people={people}
          onClose={() => setEditingTask(null)}
          onSaved={() => {
            setEditingTask(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function TeamPanel({ project, isOwner, onChanged }) {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleAdd(e) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await api.post(`/projects/${project.id}/members/`, { email })
      toast.success(`Added ${email} to the project.`)
      setEmail('')
      onChanged()
    } catch (err) {
      const data = err.response?.data
      toast.error(data?.email?.[0] || data?.detail || 'Could not add that person.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemove(memberId, memberEmail) {
    if (!confirm(`Remove ${memberEmail} from this project?`)) return
    try {
      await api.delete(`/projects/${project.id}/members/${memberId}/`)
      toast.success('Member removed.')
      onChanged()
    } catch {
      toast.error('Could not remove member.')
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">Team</h3>
      <div className="flex flex-wrap gap-2 mb-4">
        <Person person={project.owner} tag="Owner" />
        {project.members.map((m) => (
          <Person key={m.id} person={m} onRemove={isOwner ? () => handleRemove(m.id, m.email) : null} />
        ))}
      </div>

      {isOwner && (
        <form onSubmit={handleAdd} className="flex items-center gap-2 max-w-sm">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="teammate@example.com"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium whitespace-nowrap"
          >
            {submitting ? 'Adding...' : 'Add member'}
          </button>
        </form>
      )}
      {isOwner && (
        <p className="text-xs text-slate-400 mt-2">
          They need an existing TeamFlow account (signed up with that email) to be added.
        </p>
      )}
    </div>
  )
}

function Person({ person, tag, onRemove }) {
  return (
    <div className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-full bg-slate-100 border border-slate-200">
      <div className="h-6 w-6 rounded-full bg-brand-600 text-white flex items-center justify-center text-[10px] font-semibold">
        {(person.first_name || person.email || '?').slice(0, 1).toUpperCase()}
      </div>
      <span className="text-xs font-medium text-slate-700">{person.first_name || person.email}</span>
      {tag && <span className="text-[10px] uppercase font-semibold text-slate-400">{tag}</span>}
      {onRemove && (
        <button onClick={onRemove} className="text-slate-400 hover:text-red-600 text-sm leading-none ml-1">
          &times;
        </button>
      )}
    </div>
  )
}

function TaskFormModal({ projectId, task, people, onClose, onSaved }) {
  const [title, setTitle] = useState(task?.title || '')
  const [description, setDescription] = useState(task?.description || '')
  const [status, setStatus] = useState(task?.status || 'todo')
  const [dueDate, setDueDate] = useState(task?.due_date ? task.due_date.slice(0, 10) : '')
  const [assignedTo, setAssignedTo] = useState(task?.assigned_to ?? '')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    const payload = {
      project: projectId,
      title,
      description,
      status,
      due_date: dueDate ? `${dueDate}T00:00:00Z` : null,
      assigned_to: assignedTo || null,
    }
    try {
      if (task) {
        await api.patch(`/tasks/${task.id}/`, payload)
        toast.success('Task updated.')
      } else {
        await api.post('/tasks/', payload)
        toast.success('Task created.')
      }
      onSaved()
    } catch (err) {
      const data = err.response?.data
      toast.error(data ? Object.values(data).flat().join(' ') : 'Could not save task.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title={task ? 'Edit Task' : 'New Task'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="done">Done</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Due date</label>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Assignee</label>
          <select
            value={assignedTo}
            onChange={(e) => setAssignedTo(e.target.value ? Number(e.target.value) : '')}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">Unassigned</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>{p.first_name || p.email}</option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium"
          >
            {submitting ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </Modal>
  )
}