import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'react-toastify'
import api from '../api/axios'
import Modal from '../components/Modal'

export default function Projects() {
  const [projects, setProjects] = useState(null)
  const [taskCounts, setTaskCounts] = useState({})
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState(null)

  function reload() {
    api.get('/projects/?page_size=200').then(({ data }) => setProjects(data.results ?? data))
    api.get('/tasks/?page_size=200').then(({ data }) => {
      const tasks = data.results ?? data
      const counts = {}
      tasks.forEach((t) => {
        counts[t.project] = (counts[t.project] || 0) + 1
      })
      setTaskCounts(counts)
    })
  }

  useEffect(reload, [])

  async function handleDelete(id) {
    if (!confirm('Delete this project and all its tasks?')) return
    try {
      await api.delete(`/projects/${id}/`)
      toast.success('Project deleted.')
      reload()
    } catch {
      toast.error('Could not delete project.')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Projects</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium"
        >
          + New Project
        </button>
      </div>

      {projects === null ? (
        <p className="text-sm text-slate-400">Loading projects...</p>
      ) : projects.length === 0 ? (
        <div className="text-center py-16 bg-white border border-dashed border-slate-300 rounded-xl">
          <p className="text-slate-500 text-sm">No projects yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 text-sm text-brand-600 font-medium hover:underline"
          >
            Create your first project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col hover:border-brand-300 transition-colors"
            >
              <Link
                to={`/projects/${project.id}`}
                className="font-semibold text-slate-900 hover:text-brand-600 truncate"
              >
                {project.name}
              </Link>
              <p className="text-sm text-slate-500 mt-1 flex-1 line-clamp-2">
                {project.description || 'No description yet.'}
              </p>
              <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
                <span>{taskCounts[project.id] || 0} task{taskCounts[project.id] === 1 ? '' : 's'}</span>
                <span>{new Date(project.created_at).toLocaleDateString()}</span>
              </div>
              <div className="mt-4 flex items-center gap-2 pt-4 border-t border-slate-100">
                <Link
                  to={`/projects/${project.id}`}
                  className="flex-1 text-center text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200"
                >
                  Open
                </Link>
                <button
                  onClick={() => setEditing(project)}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(project.id)}
                  className="text-xs font-medium px-3 py-1.5 rounded-lg text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <ProjectFormModal
          onClose={() => setShowCreate(false)}
          onSaved={() => {
            setShowCreate(false)
            reload()
          }}
        />
      )}
      {editing && (
        <ProjectFormModal
          project={editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            reload()
          }}
        />
      )}
    </div>
  )
}

function ProjectFormModal({ project, onClose, onSaved }) {
  const [name, setName] = useState(project?.name || '')
  const [description, setDescription] = useState(project?.description || '')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (project) {
        await api.patch(`/projects/${project.id}/`, { name, description })
        toast.success('Project updated.')
      } else {
        await api.post('/projects/', { name, description })
        toast.success('Project created.')
      }
      onSaved()
    } catch {
      toast.error('Could not save project.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal title={project ? 'Edit Project' : 'New Project'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
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