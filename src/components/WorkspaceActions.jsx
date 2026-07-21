import { useEffect, useMemo, useState } from 'react'
import { BookOpen, CheckSquare, FileText, FolderKanban, Landmark, Loader2, Search } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import api from '../api/axios'
import Modal from './Modal'

export default function WorkspaceActions({ mode, onClose }) {
  if (!mode) return null
  return mode === 'search' ? <GlobalSearch onClose={onClose} /> : <QuickCreate onClose={onClose} />
}

function GlobalSearch({ onClose }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    Promise.allSettled([
      api.get('/projects/?page_size=200'), api.get('/tasks/?page_size=200'), api.get('/v1/erp/accounts/'), api.get('/v1/erp/journals/'), api.get('/v1/erp/documents/'),
    ]).then(results => {
      const value = i => results[i].status === 'fulfilled' ? (results[i].value.data.results || results[i].value.data) : []
      setItems([
        ...value(0).map(x => ({ type: 'Project', title: x.name, detail: x.description, to: `/projects/${x.id}`, icon: FolderKanban })),
        ...value(1).map(x => ({ type: 'Task', title: x.title, detail: x.description, to: `/projects/${x.project}`, icon: CheckSquare })),
        ...value(2).map(x => ({ type: 'Account', title: `${x.code} · ${x.name}`, detail: x.account_type, to: '/erp?view=accounts', icon: BookOpen })),
        ...value(3).map(x => ({ type: 'Journal', title: x.reference, detail: x.description, to: '/erp?view=journals', icon: Landmark })),
        ...value(4).map(x => ({ type: x.type, title: x.number, detail: x.party, to: '/erp?view=documents', icon: FileText })),
      ]); setLoading(false)
    })
  }, [])
  const results = useMemo(() => query.trim().length < 2 ? [] : items.filter(x => `${x.type} ${x.title} ${x.detail || ''}`.toLowerCase().includes(query.toLowerCase())).slice(0, 30), [items, query])
  function open(to) { onClose(); navigate(to) }
  return <Modal title="Search Taylee"><label className="relative block"><Search size={18} className="absolute left-3 top-3 text-slate-400" /><input autoFocus value={query} onChange={e => setQuery(e.target.value)} placeholder="Search projects, tasks, accounts, journals…" className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-brand-400 dark:border-slate-700 dark:bg-slate-900" /></label><div className="mt-4 max-h-96 overflow-y-auto">{loading ? <p className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500"><Loader2 size={17} className="animate-spin" />Indexing your workspace…</p> : query.length < 2 ? <p className="py-10 text-center text-sm text-slate-500">Type at least two characters to search.</p> : results.length ? results.map((x, i) => <button key={`${x.type}-${x.title}-${i}`} onClick={() => open(x.to)} className="flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left hover:bg-slate-100 dark:hover:bg-slate-700"><span className="rounded-lg bg-brand-50 p-2 text-brand-600 dark:bg-brand-950"><x.icon size={18} /></span><span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{x.title}</span><span className="block truncate text-xs capitalize text-slate-500">{x.type}{x.detail ? ` · ${x.detail}` : ''}</span></span></button>) : <p className="py-10 text-center text-sm text-slate-500">No results for “{query}”.</p>}</div></Modal>
}

function QuickCreate({ onClose }) {
  const navigate = useNavigate()
  const [kind, setKind] = useState('task')
  const [projects, setProjects] = useState([])
  const [form, setForm] = useState({ title: '', name: '', description: '', project: '', priority: 'medium', due_date: '' })
  const [saving, setSaving] = useState(false)
  useEffect(() => { api.get('/projects/?page_size=200').then(({ data }) => { const rows = data.results || data; setProjects(rows); if (rows[0]) setForm(f => ({ ...f, project: rows[0].id })) }).catch(() => {}) }, [])
  async function submit(e) {
    e.preventDefault(); setSaving(true)
    try {
      if (kind === 'project') {
        const { data } = await api.post('/projects/', { name: form.name, description: form.description }); toast.success('Project created'); onClose(); navigate(`/projects/${data.id}`)
      } else {
        const payload = { project: form.project, title: form.title, description: form.description, priority: form.priority, status: 'todo', assigned_to: null, due_date: form.due_date || null }
        await api.post('/tasks/', payload); toast.success('Task created'); onClose(); navigate(`/projects/${form.project}`)
      }
    } catch (err) { toast.error(err.response?.data?.detail || Object.values(err.response?.data || {})?.[0]?.[0] || `Could not create ${kind}.`) } finally { setSaving(false) }
  }
  return <Modal title="Quick create"><div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1 dark:bg-slate-900">{[['task','Task',CheckSquare],['project','Project',FolderKanban]].map(([key,label,Icon]) => <button key={key} onClick={() => setKind(key)} className={`flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${kind === key ? 'bg-white text-brand-600 shadow-sm dark:bg-slate-700' : 'text-slate-500'}`}><Icon size={17} />{label}</button>)}</div><form onSubmit={submit} className="mt-5 space-y-4">{kind === 'task' ? <><Field label="Task title" value={form.title} onChange={v => setForm(f => ({ ...f, title: v }))} required /><label className="block text-sm"><span className="mb-1.5 block font-medium">Project</span><select value={form.project} onChange={e => setForm(f => ({ ...f, project: e.target.value }))} required className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900">{projects.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><div className="grid grid-cols-2 gap-3"><label className="text-sm"><span className="mb-1.5 block font-medium">Priority</span><select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 dark:border-slate-700 dark:bg-slate-900"><option>low</option><option>medium</option><option>high</option></select></label><Field type="datetime-local" label="Due date" value={form.due_date} onChange={v => setForm(f => ({ ...f, due_date: v }))} /></div></> : <Field label="Project name" value={form.name} onChange={v => setForm(f => ({ ...f, name: v }))} required />}<label className="block text-sm"><span className="mb-1.5 block font-medium">Description</span><textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-brand-400 dark:border-slate-700 dark:bg-slate-900" /></label><button disabled={saving || (kind === 'task' ? !form.title || !form.project : !form.name)} className="flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50">{saving && <Loader2 size={16} className="animate-spin" />}Create {kind}</button></form></Modal>
}
function Field({ label, value, onChange, type = 'text', required }) { return <label className="block text-sm"><span className="mb-1.5 block font-medium">{label}</span><input type={type} required={required} value={value} onChange={e => onChange(e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 outline-none focus:border-brand-400 dark:border-slate-700 dark:bg-slate-900" /></label> }
