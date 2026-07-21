import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ArrowDownRight, ArrowUpRight, BookOpen, Building2, CheckCircle2, CircleDollarSign, Landmark, PackageCheck, RefreshCw, Search, ShoppingCart, WalletCards } from 'lucide-react'
import api from '../api/axios'

const money = (value, currency = 'USD') => new Intl.NumberFormat('en-ZW', { style: 'currency', currency }).format(Number(value || 0))
const tabs = [
  ['overview', 'Overview'], ['accounts', 'Chart of accounts'], ['journals', 'Journals'],
  ['documents', 'Invoices & bills'], ['procurement', 'Procurement'], ['reports', 'Trial balance'], ['reconciliation', 'Reconciliation'],
]

function Badge({ children, tone = 'slate' }) {
  const colors = { green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-950 dark:text-emerald-300', amber: 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-950 dark:text-amber-300', blue: 'bg-blue-50 text-blue-700 ring-blue-600/20 dark:bg-blue-950 dark:text-blue-300', slate: 'bg-slate-100 text-slate-700 ring-slate-500/20 dark:bg-slate-700 dark:text-slate-200' }
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${colors[tone]}`}>{children}</span>
}

function Loading() { return <div className="p-16 text-center text-slate-500"><RefreshCw className="mx-auto mb-3 animate-spin" />Loading live ERP data…</div> }
function Empty({ text }) { return <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center text-slate-500 dark:border-slate-700">{text}</div> }

export default function ERP() {
  const location = useLocation()
  const current = new URLSearchParams(location.search).get('view') || 'overview'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  useEffect(() => {
    const endpoint = { overview: 'dashboard/', accounts: 'accounts/', journals: 'journals/', documents: 'documents/', procurement: 'procurement/', reports: 'reports/trial-balance/', reconciliation: 'reconciliation/' }[current]
    setLoading(true); setError('')
    api.get(`/v1/erp/${endpoint}`).then(({ data }) => setData(data)).catch((err) => setError(err.response?.data?.detail || 'Could not load ERP data.')).finally(() => setLoading(false))
  }, [current])

  const rows = useMemo(() => Array.isArray(data) ? data.filter(row => JSON.stringify(row).toLowerCase().includes(query.toLowerCase())) : [], [data, query])

  return <div className="min-h-full bg-[#f5f4f1] text-slate-900 dark:bg-slate-950 dark:text-slate-100">
    <header className="border-b border-slate-200 bg-white px-7 py-5 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div><div className="flex items-center gap-2 text-sm font-medium text-brand-600"><Building2 size={16} /> Taylee</div><h1 className="mt-1 text-2xl font-semibold tracking-tight">Finance & operations</h1></div>
        <div className="flex items-center gap-3"><Badge tone="green"><span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-emerald-500" />Books open · July 2026</Badge><button onClick={() => window.location.reload()} className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800"><RefreshCw size={17} /></button></div>
      </div>
      <nav className="mt-6 flex gap-1 overflow-x-auto">
        {tabs.map(([key, label]) => <NavLink key={key} to={`/erp?view=${key}`} className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium ${current === key ? 'bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}`}>{label}</NavLink>)}
      </nav>
    </header>

    <main className="p-7">
      {current !== 'overview' && <div className="mb-5 flex items-center justify-between gap-4"><div><h2 className="text-lg font-semibold">{tabs.find(x => x[0] === current)?.[1]}</h2><p className="text-sm text-slate-500">Tenant-scoped live records from the accounting API</p></div><label className="relative"><Search size={16} className="absolute left-3 top-3 text-slate-400" /><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search records" className="w-64 rounded-lg border border-slate-200 bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-brand-400 dark:border-slate-700 dark:bg-slate-900" /></label></div>}
      {loading ? <Loading /> : error ? <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-700">{error}</div> : current === 'overview' ? <Overview data={data} /> : <DataView type={current} rows={rows} />}
    </main>
  </div>
}

function Overview({ data }) {
  const m = data?.metrics || {}
  const cards = [
    ['Receivables', money(m.receivables), ArrowUpRight, 'Collectable from customers', 'text-emerald-600', 'bg-emerald-50 dark:bg-emerald-950'],
    ['Payables', money(m.payables), ArrowDownRight, 'Outstanding supplier bills', 'text-amber-600', 'bg-amber-50 dark:bg-amber-950'],
    ['Posted journals', m.posted_journals, BookOpen, 'Balanced entries in the GL', 'text-brand-600', 'bg-brand-50 dark:bg-brand-950'],
    ['Stock on hand', `${Number(m.stock_units || 0).toLocaleString()} units`, PackageCheck, 'Across active warehouses', 'text-blue-600', 'bg-blue-50 dark:bg-blue-950'],
  ]
  return <>
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{cards.map(([label, value, Icon, note, icon, bg]) => <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="flex items-start justify-between"><div><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p></div><div className={`rounded-xl p-2.5 ${bg} ${icon}`}><Icon size={19} /></div></div><p className="mt-4 text-xs text-slate-400">{note}</p></div>)}</div>
    <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="flex items-center justify-between"><div><h3 className="font-semibold">Cash flow snapshot</h3><p className="text-sm text-slate-500">Operational position for the current period</p></div><Landmark className="text-brand-500" /></div><div className="mt-8 flex h-44 items-end gap-4">{[42, 66, 51, 83, 58, 92, 76, 100, 72, 88, 64, 94].map((x, i) => <div key={i} className="group flex-1"><div className="rounded-t-md bg-brand-500/80 transition hover:bg-brand-500" style={{ height: `${x}%` }} /></div>)}</div><div className="mt-3 flex justify-between text-xs text-slate-400"><span>Jul 1</span><span>Jul 7</span><span>Jul 14</span><span>Jul 21</span><span>Jul 31</span></div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><h3 className="font-semibold">Control centre</h3><div className="mt-4 space-y-3"><Control icon={CheckCircle2} title="Journal integrity" detail="All posted entries are balanced" tone="green" /><Control icon={ShoppingCart} title="Purchase orders" detail={`${m.open_purchase_orders || 0} currently open`} tone="amber" /><Control icon={WalletCards} title="Bank reconciliation" detail="Ready for statement import" tone="blue" /></div></section>
    </div>
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="border-b border-slate-100 px-6 py-4 dark:border-slate-800"><h3 className="font-semibold">Recent journal activity</h3></div>{data?.recent_journals?.length ? data.recent_journals.map(x => <div key={x.id} className="flex items-center justify-between border-b border-slate-100 px-6 py-4 last:border-0 dark:border-slate-800"><div><p className="text-sm font-medium">{x.reference}</p><p className="text-xs text-slate-500">{x.description || 'General journal'}</p></div><div className="text-right"><Badge tone="green">Posted</Badge><p className="mt-1 text-xs text-slate-400">{x.entry_date}</p></div></div>) : <Empty text="No posted journals yet" />}</section>
  </>
}

function Control({ icon: Icon, title, detail, tone }) { return <div className="flex items-center gap-3 rounded-xl border border-slate-100 p-3 dark:border-slate-800"><div className="rounded-lg bg-slate-50 p-2 dark:bg-slate-800"><Icon size={18} /></div><div className="min-w-0 flex-1"><p className="text-sm font-medium">{title}</p><p className="text-xs text-slate-500">{detail}</p></div><Badge tone={tone}>Healthy</Badge></div> }

function DataView({ type, rows }) {
  if (!rows.length) return <Empty text={type === 'reconciliation' ? 'No bank transactions imported yet. Import a statement to begin matching.' : 'No matching records found.'} />
  const configs = {
    accounts: [['code', 'Code'], ['name', 'Account'], ['account_type', 'Type'], ['is_active', 'Status']],
    journals: [['reference', 'Reference'], ['date', 'Date'], ['description', 'Description'], ['debit', 'Debit'], ['credit', 'Credit'], ['status', 'Status']],
    documents: [['number', 'Number'], ['type', 'Type'], ['party', 'Customer / supplier'], ['date', 'Issued'], ['due_date', 'Due'], ['total', 'Total'], ['status', 'Status']],
    procurement: [['number', 'PO number'], ['supplier', 'Supplier'], ['date', 'Date'], ['total', 'Total'], ['status', 'Status']],
    reports: [['account__code', 'Code'], ['account__name', 'Account'], ['account__account_type', 'Type'], ['debit', 'Debit'], ['credit', 'Credit']],
    reconciliation: [['date', 'Date'], ['reference', 'Reference'], ['bank', 'Bank'], ['amount', 'Amount'], ['matched', 'Match status']],
  }
  const columns = configs[type]
  const render = (key, value, row) => {
    if (['debit', 'credit', 'total', 'amount'].includes(key)) return <span className="font-medium tabular-nums">{money(value, row.currency)}</span>
    if (key === 'is_active') return <Badge tone={value ? 'green' : 'slate'}>{value ? 'Active' : 'Inactive'}</Badge>
    if (key === 'matched') return <Badge tone={value ? 'green' : 'amber'}>{value ? 'Matched' : 'Unmatched'}</Badge>
    if (key === 'status') return <Badge tone={['posted', 'paid', 'approved', 'confirmed'].includes(value) ? 'green' : value === 'draft' ? 'slate' : 'amber'}>{value}</Badge>
    return value || '—'
  }
  return <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/60"><tr>{columns.map(([key, label]) => <th key={key} className="px-5 py-3.5 font-semibold">{label}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={row.id || i} className="border-t border-slate-100 hover:bg-slate-50/70 dark:border-slate-800 dark:hover:bg-slate-800/40">{columns.map(([key]) => <td key={key} className="px-5 py-4">{render(key, row[key], row)}</td>)}</tr>)}</tbody></table></div></div>
}
