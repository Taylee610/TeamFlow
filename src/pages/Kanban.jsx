import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import {
  DndContext, useDraggable, useDroppable,
  PointerSensor, useSensor, useSensors, DragOverlay, closestCorners,
} from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'

const COLUMNS = [
  { key: 'todo', label: 'To Do' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'done', label: 'Done' },
]

export default function Kanban() {
  const { id } = useParams()
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [activeTask, setActiveTask] = useState(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  function reload() {
    api.get(`/projects/${id}/`).then(({ data }) => setProject(data))
    api.get(`/tasks/?project=${id}&page_size=200`).then(({ data }) => setTasks(data.results ?? data))
  }

  useEffect(reload, [id])

  const people = project ? [project.owner, ...project.members] : []

  function handleDragStart(event) {
    const task = tasks.find((t) => t.id === event.active.id)
    setActiveTask(task || null)
  }

  async function handleDragEnd(event) {
    const { active, over } = event
    setActiveTask(null)
    if (!over) return

    const task = tasks.find((t) => t.id === active.id)
    const newStatus = over.id
    if (!task || task.status === newStatus) return

    const previousTasks = tasks
    setTasks(tasks.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t)))

    try {
      await api.patch(`/tasks/${task.id}/`, { status: newStatus })
    } catch {
      toast.error("Couldn't move that task -- you may not have permission.")
      setTasks(previousTasks)
    }
  }

  if (!project || !tasks) {
    return <div className="p-6 text-sm text-slate-400">Loading board...</div>
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <Link to={`/projects/${id}`} className="text-xs text-brand-600 hover:underline">
            &larr; Back to {project.name}
          </Link>
          <h1 className="text-lg font-semibold text-slate-900 mt-1">{project.name} · Kanban</h1>
        </div>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {COLUMNS.map((col) => (
            <Column
              key={col.key}
              id={col.key}
              label={col.label}
              tasks={tasks.filter((t) => t.status === col.key)}
              currentUserId={user?.id}
              people={people}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTask ? <Card task={activeTask} currentUserId={user?.id} people={people} overlay /> : null}
        </DragOverlay>
      </DndContext>
    </div>
  )
}

function Column({ id, label, tasks, currentUserId, people }) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border flex flex-col min-h-[65vh] transition-colors ${
        isOver ? 'bg-brand-50 border-brand-300' : 'bg-slate-100/60 border-slate-200'
      }`}
    >
      <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-800">{label}</h3>
        <span className="text-xs font-medium text-slate-500 bg-white rounded-full px-2 py-0.5">
          {tasks.length}
        </span>
      </div>
      <div className="flex-1 p-3 space-y-3">
        {tasks.map((task) => (
          <DraggableCard key={task.id} task={task} currentUserId={currentUserId} people={people} />
        ))}
      </div>
    </div>
  )
}

function DraggableCard({ task, currentUserId, people }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: task.id })

  const style = {
    transform: CSS.Translate.toString(transform),
    opacity: isDragging ? 0.4 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <Card task={task} currentUserId={currentUserId} people={people} />
    </div>
  )
}

function Card({ task, currentUserId, people, overlay }) {
  const overdue = task.due_date && new Date(task.due_date) < new Date() && task.status !== 'done'
  const assignee = task.assigned_to ? people.find((p) => p.id === task.assigned_to) : null

  return (
    <div
      className={`bg-white border border-slate-200 rounded-lg p-3 shadow-sm cursor-grab active:cursor-grabbing select-none ${
        overlay ? 'shadow-lg rotate-2' : ''
      }`}
    >
      <p className="text-sm font-medium text-slate-800 leading-snug">{task.title}</p>
      <div className="mt-2 flex items-center justify-between text-xs">
        <span className={overdue ? 'text-red-500 font-medium' : 'text-slate-400'}>
          {task.due_date ? new Date(task.due_date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : 'No due date'}
        </span>
        {assignee && (
          <span
            className="h-5 w-5 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-[10px] font-semibold"
            title={task.assigned_to === currentUserId ? 'You' : (assignee.first_name || assignee.email)}
          >
            {(assignee.first_name || assignee.email || '?').slice(0, 1).toUpperCase()}
          </span>
        )}
      </div>
    </div>
  )
}