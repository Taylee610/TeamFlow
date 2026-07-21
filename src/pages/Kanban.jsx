import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'react-toastify'
import {
  DndContext, useDraggable, useDroppable,
  PointerSensor, useSensor, useSensors, DragOverlay, closestCorners,
} from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { CalendarDays, CheckSquare2, ChevronDown, Clock3, GripVertical, LayoutDashboard, List, MoreHorizontal, Paperclip, Plus, Users } from 'lucide-react'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import LoadingState from '../components/LoadingState'

const COLUMNS = [
  { key: 'todo', label: 'TO DO', tone: 'bg-slate-200 text-slate-700' },
  { key: 'drafting', label: 'DRAFTING', tone: 'bg-sky-100 text-sky-700' },
  { key: 'in_review', label: 'IN REVIEW', tone: 'bg-blue-100 text-blue-700' },
  { key: 'done', label: 'DONE', tone: 'bg-emerald-100 text-emerald-700' },
]
const boardCache = new Map()

export default function Kanban() {
  const { id } = useParams()
  const { user } = useAuth()
  const [project, setProject] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [activeTask, setActiveTask] = useState(null)
  const [quickColumn, setQuickColumn] = useState(null)
  const [quickTitle, setQuickTitle] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  async function reload({ background = false } = {}) {
    if (!background) { setProject(null); setTasks(null) }
    try {
      const { data } = await api.get(`/projects/${id}/board/`)
      boardCache.set(id, data)
      setProject(data.project); setTasks(data.tasks)
    } catch {
      toast.error("Couldn't load this board.")
      setTasks([])
    }
  }

  useEffect(() => {
    const cached = boardCache.get(id)
    if (cached) {
      setProject(cached.project); setTasks(cached.tasks)
      reload({ background: true })
    } else reload()
  }, [id])

  const people = project ? [project.owner, ...project.members] : []
  const tasksFor = (status) => tasks.filter(task => status === 'drafting' ? ['drafting', 'in_progress'].includes(task.status) : task.status === status)

  async function createTask(status) {
    if (!quickTitle.trim()) return
    try {
      const { data } = await api.post('/tasks/', { project: Number(id), title: quickTitle.trim(), description: '', status, priority: 'medium', assigned_to: null, due_date: null })
      const next = [...tasks, data]; setTasks(next); boardCache.set(id, { project, tasks: next })
      setQuickTitle(''); setQuickColumn(null); toast.success('Task created')
    } catch { toast.error("Couldn't create that task.") }
  }

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
    const optimisticTasks = tasks.map((t) => (t.id === task.id ? { ...t, status: newStatus } : t))
    setTasks(optimisticTasks)
    boardCache.set(id, { project, tasks: optimisticTasks })

    try {
      await api.patch(`/tasks/${task.id}/`, { status: newStatus })
    } catch {
      toast.error("Couldn't move that task -- you may not have permission.")
      setTasks(previousTasks)
      boardCache.set(id, { project, tasks: previousTasks })
    }
  }

  if (!project || !tasks) {
    return <LoadingState label="Loading board..." />
  }

  return (
    <div className="min-h-full bg-white dark:bg-slate-950">
      <div className="border-b border-slate-200 px-6 pt-5 dark:border-slate-800">
        <div className="flex items-start justify-between gap-4"><div><p className="text-xs text-slate-500">Projects / {project.name}</p><div className="mt-2 flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-600 text-white"><LayoutDashboard size={19} /></span><h1 className="text-xl font-bold text-slate-800 dark:text-white">{project.name}</h1></div></div><button className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300">Project settings</button></div>
        <nav className="mt-5 flex gap-1 overflow-x-auto text-sm text-slate-600 dark:text-slate-300">{[['Summary',`/projects/${id}/summary`],['Board',`/projects/${id}/kanban`],['List',`/projects/${id}`],['Calendar',`/projects/${id}/calendar`],['Timeline',`/projects/${id}/timeline`],['Approvals',`/projects/${id}/approvals`],['Forms',`/projects/${id}/forms`],['Reports',`/projects/${id}/reports`]].map(([tab,to]) => tab === 'Board' ? <span key={tab} className="border-b-2 border-brand-600 px-3 py-3 font-semibold text-brand-600">{tab}</span> : <Link key={tab} to={to} className="whitespace-nowrap px-3 py-3 hover:bg-slate-50 dark:hover:bg-slate-900">{tab}</Link>)}</nav>
      </div>
      <div className="flex items-center justify-between px-6 py-4"><div className="flex -space-x-2">{people.slice(0, 5).map(person => <span key={person.id} title={person.first_name || person.email} className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-gradient-to-br from-brand-400 to-brand-600 text-xs font-bold text-white dark:border-slate-950">{(person.first_name || person.email || '?')[0].toUpperCase()}</span>)}{people.length > 5 && <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-slate-200 text-xs font-semibold text-slate-600">+{people.length - 5}</span>}</div><div className="flex items-center gap-2"><button className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300"><Users size={16} />Team</button><button className="rounded-lg border border-slate-200 p-2 text-slate-500 dark:border-slate-700"><MoreHorizontal size={18} /></button></div></div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-3 overflow-x-auto bg-slate-50 px-5 pb-8 pt-1 dark:bg-slate-950">
          {COLUMNS.map((col) => (
            <Column
              key={col.key}
              id={col.key}
              label={col.label}
              tasks={tasksFor(col.key)}
              tone={col.tone}
              currentUserId={user?.id}
              people={people}
              creating={quickColumn === col.key}
              quickTitle={quickTitle}
              onQuickTitle={setQuickTitle}
              onStartCreate={() => { setQuickColumn(col.key); setQuickTitle('') }}
              onCancelCreate={() => { setQuickColumn(null); setQuickTitle('') }}
              onCreate={() => createTask(col.key)}
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

function Column({ id, label, tone, tasks, currentUserId, people, creating, quickTitle, onQuickTitle, onStartCreate, onCancelCreate, onCreate }) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <div
      ref={setNodeRef}
      className={`w-[290px] min-w-[290px] rounded-lg flex flex-col min-h-[64vh] transition-colors ${
        isOver
          ? 'bg-brand-50 ring-2 ring-brand-300 dark:bg-brand-950/40'
          : 'bg-[#f1f2f4] dark:bg-slate-900'
      }`}
    >
      <div className="px-3 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2"><GripVertical size={15} className="text-slate-400" /><span className={`rounded px-2 py-1 text-[11px] font-bold tracking-wide ${tone}`}>{label}</span><span className="text-xs text-slate-500">{tasks.length}</span></div><button className="rounded p-1 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800"><MoreHorizontal size={17} /></button>
      </div>
      <div className="flex-1 px-2 pb-2 space-y-2">
        {tasks.map((task) => (
          <DraggableCard key={task.id} task={task} currentUserId={currentUserId} people={people} />
        ))}
      </div>
      {creating ? <div className="m-2 rounded-lg bg-white p-2 shadow-md dark:bg-slate-800"><textarea autoFocus value={quickTitle} onChange={e => onQuickTitle(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onCreate() } if (e.key === 'Escape') onCancelCreate() }} placeholder="What needs to be done?" className="min-h-20 w-full resize-none border-0 p-2 text-sm outline-none dark:bg-slate-800" /><div className="flex gap-2"><button onClick={onCreate} className="rounded bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white">Add</button><button onClick={onCancelCreate} className="rounded px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700">Cancel</button></div></div> : <button onClick={onStartCreate} className="m-2 flex items-center gap-2 rounded-md px-2 py-2 text-sm text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"><Plus size={17} />Create</button>}
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
      className={`group bg-white dark:bg-slate-800 rounded-lg p-3 shadow-sm hover:shadow-md cursor-grab active:cursor-grabbing select-none ${
        overlay ? 'shadow-lg rotate-2' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-2"><Link to={`/projects/${task.project}/tasks/${task.id}`} onPointerDown={e => e.stopPropagation()} className="text-sm font-medium text-slate-800 hover:text-brand-600 dark:text-slate-200 leading-snug">{task.title}</Link><MoreHorizontal size={15} className="shrink-0 text-slate-400 opacity-0 group-hover:opacity-100" /></div>
      {task.description && <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{task.description}</p>}
      {overdue && <span className="mt-2 inline-flex items-center gap-1 rounded bg-red-50 px-1.5 py-1 text-[10px] font-medium text-red-600 dark:bg-red-950"><Clock3 size={11} />{new Date(task.due_date).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })}</span>}
      <div className="mt-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2"><span className={`flex h-4 w-4 items-center justify-center rounded ${task.status === 'done' ? 'bg-emerald-500' : 'bg-sky-500'} text-white`}><CheckSquare2 size={11} /></span><span className="font-medium text-slate-500">TAY-{task.id}</span>{task.attachment && <Paperclip size={12} className="text-slate-400" />}</div>
        {assignee && (
          <span
            className="h-5 w-5 rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 flex items-center justify-center text-[10px] font-semibold"
            title={task.assigned_to === currentUserId ? 'You' : (assignee.first_name || assignee.email)}
          >
            {(assignee.first_name || assignee.email || '?').slice(0, 1).toUpperCase()}
          </span>
        )}
      </div>
    </div>
  )
}
