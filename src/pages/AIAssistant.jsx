import { useEffect, useState } from 'react'
import { Bot, Calendar, CheckCircle2, Loader2, Send, Sparkles, WandSparkles } from 'lucide-react'
import { toast } from 'react-toastify'
import api from '../api/axios'
import { requestTaskAssist } from '../api/ai'

const suggestions = ['Prepare the July month-end close', 'Review overdue customer invoices', 'Plan a warehouse stock count', 'Create a supplier onboarding checklist']

export default function AIAssistant() {
  const [prompt, setPrompt] = useState('')
  const [project, setProject] = useState('')
  const [projects, setProjects] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  useEffect(() => { api.get('/projects/?page_size=100').then(({ data }) => setProjects(data.results || data)).catch(() => {}) }, [])
  async function submit(e) {
    e?.preventDefault()
    if (!prompt.trim()) return
    setLoading(true); setResult(null)
    try { setResult(await requestTaskAssist(prompt, project || undefined)) }
    catch (err) { toast.error(err.response?.data?.detail || 'Taylee AI could not generate a response.') }
    finally { setLoading(false) }
  }
  return <div className="min-h-full bg-slate-50 p-8 dark:bg-slate-950"><div className="mx-auto max-w-5xl"><div className="flex items-center gap-4"><div className="rounded-2xl bg-gradient-to-br from-brand-600 to-brand-600 p-3 text-white shadow-lg shadow-brand-500/20"><Bot size={28} /></div><div><div className="flex items-center gap-2"><h1 className="text-2xl font-semibold">Taylee AI</h1><span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-700 dark:bg-brand-950 dark:text-brand-300">Assistant</span></div><p className="text-sm text-slate-500">Turn operational goals into structured, actionable work.</p></div></div>
    <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_0.8fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="flex items-center gap-2"><WandSparkles size={19} className="text-brand-600" /><h2 className="font-semibold">What would you like to accomplish?</h2></div><form onSubmit={submit}><textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Example: Prepare the July close and make sure all bank transactions are reconciled…" className="mt-4 min-h-40 w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 outline-none focus:border-brand-400 focus:bg-white dark:border-slate-700 dark:bg-slate-800" /><div className="mt-4 flex flex-wrap items-end justify-between gap-3"><label className="text-sm"><span className="mb-1.5 block font-medium">Project context</span><select value={project} onChange={e => setProject(e.target.value)} className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 dark:border-slate-700 dark:bg-slate-800"><option value="">No project</option>{projects.map(x => <option key={x.id} value={x.id}>{x.name}</option>)}</select></label><button disabled={loading || !prompt.trim()} className="flex items-center gap-2 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50">{loading ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}{loading ? 'Thinking…' : 'Generate plan'}</button></div></form><div className="mt-6"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Try an example</p><div className="mt-2 flex flex-wrap gap-2">{suggestions.map(x => <button key={x} onClick={() => setPrompt(x)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-brand-300 hover:text-brand-600 dark:border-slate-700 dark:text-slate-300">{x}</button>)}</div></div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">{result ? <Result result={result} /> : <div className="flex h-full min-h-80 flex-col items-center justify-center text-center"><div className="rounded-2xl bg-brand-50 p-4 text-brand-500 dark:bg-brand-950"><Sparkles size={28} /></div><h3 className="mt-4 font-semibold">Your plan will appear here</h3><p className="mt-2 max-w-xs text-sm leading-6 text-slate-500">Taylee AI will suggest a description, priority, due date, and concrete subtasks.</p></div>}</section>
    </div></div></div>
}
function Result({ result }) { return <div><div className="flex items-center justify-between"><h2 className="font-semibold">Suggested plan</h2><span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${result.priority === 'high' ? 'bg-red-100 text-red-700' : result.priority === 'medium' ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>{result.priority} priority</span></div><p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">{result.description}</p><div className="mt-5 flex items-center gap-2 rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800"><Calendar size={17} className="text-brand-500" />Due date: <strong>{result.due_date || 'Not specified'}</strong></div><h3 className="mt-6 text-sm font-semibold">Recommended subtasks</h3><div className="mt-3 space-y-3">{result.subtasks?.map((x, i) => <div key={i} className="flex gap-3 text-sm"><CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-500" /><span>{x}</span></div>)}</div></div> }
