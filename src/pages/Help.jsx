import { useMemo, useState } from 'react'
import { BookOpen, Bot, CircleHelp, ExternalLink, Landmark, Search, ShieldCheck, ShoppingCart } from 'lucide-react'
import { Link } from 'react-router-dom'

const guides = [
  { icon: Landmark, title: 'Post a journal entry', category: 'Accounting', body: 'Create at least two lines, keep total debits equal to credits, select an open period, then post. Posted journals become part of the general ledger.' },
  { icon: ShoppingCart, title: 'Purchase-to-pay workflow', category: 'Procurement', body: 'Approve the purchase order, record the goods receipt, create the supplier bill, record payment, and verify the generated journal in the trial balance.' },
  { icon: ShieldCheck, title: 'Roles and tenant access', category: 'Security', body: 'Roles determine module and value-limit permissions. Every ERP API query is scoped to your active Taylee tenant membership.' },
  { icon: BookOpen, title: 'Read the trial balance', category: 'Reports', body: 'The trial balance summarizes posted debit and credit activity by account. Total debits and credits should always agree.' },
  { icon: Bot, title: 'Use Taylee AI', category: 'AI assistant', body: 'Describe a task or operational goal. Taylee AI proposes a clear description, priority, due date, and actionable subtasks.' },
]

export default function Help() {
  const [query, setQuery] = useState('')
  const results = useMemo(() => guides.filter(x => `${x.title} ${x.category} ${x.body}`.toLowerCase().includes(query.toLowerCase())), [query])
  return <div className="min-h-full bg-slate-50 p-8 dark:bg-slate-950"><div className="mx-auto max-w-5xl"><div className="rounded-3xl bg-gradient-to-br from-brand-700 to-brand-700 px-8 py-10 text-white"><CircleHelp size={30} /><h1 className="mt-4 text-3xl font-semibold">How can we help?</h1><p className="mt-2 text-brand-100">Search Taylee guides or ask the AI assistant.</p><label className="relative mt-6 block max-w-2xl"><Search className="absolute left-4 top-3.5 text-slate-400" size={20} /><input autoFocus value={query} onChange={e => setQuery(e.target.value)} placeholder="Search journals, procurement, reports…" className="w-full rounded-xl bg-white py-3.5 pl-12 pr-4 text-slate-900 outline-none ring-4 ring-white/10" /></label></div>
    <div className="mt-6 grid gap-4 md:grid-cols-2">{results.map(({ icon: Icon, title, category, body }) => <article key={title} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="flex items-center gap-3"><span className="rounded-xl bg-brand-50 p-2.5 text-brand-600 dark:bg-brand-950"><Icon size={20} /></span><div><p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{category}</p><h2 className="font-semibold">{title}</h2></div></div><p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">{body}</p></article>)}</div>
    {!results.length && <div className="mt-6 rounded-2xl border border-dashed border-slate-300 p-12 text-center text-slate-500">No guide matched “{query}”. Try a shorter accounting term.</div>}
    <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-brand-200 bg-brand-50 p-6 dark:border-brand-900 dark:bg-brand-950"><div><h2 className="font-semibold text-brand-900 dark:text-brand-100">Need an answer tailored to your work?</h2><p className="text-sm text-brand-700 dark:text-brand-300">Ask Taylee AI to turn your goal into an actionable plan.</p></div><Link to="/ai" className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white"><Bot size={17} />Open Taylee AI <ExternalLink size={14} /></Link></div>
    </div></div>
}
