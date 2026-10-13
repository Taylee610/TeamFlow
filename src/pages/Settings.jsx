import { useEffect, useState } from 'react'
import { Bell, Check, Moon, Save, ShieldCheck, Sun, User } from 'lucide-react'
import { toast } from 'react-toastify'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export default function Settings() {
  const { user, workspace } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [profile, setProfile] = useState({ first_name: user?.first_name || '', last_name: user?.last_name || '' })
  const [prefs, setPrefs] = useState({email_notifications:true,period_reminders:true,approval_alerts:true})
  const [saving, setSaving] = useState(false)
  useEffect(() => { api.get('/tools/preferences/').then(({data})=>setPrefs(data)).catch(()=>toast.error('Could not load notification preferences')) }, [])
  async function changePreference(key,value) { try { const {data}=await api.patch('/tools/preferences/',{[key]:value});setPrefs(data) } catch { toast.error('Could not save notification preferences') } }
  async function save() {
    setSaving(true)
    try { await api.patch('/auth/me/', profile); toast.success('Settings saved') } catch { toast.error('Could not save profile') } finally { setSaving(false) }
  }
  return <Page title="Settings" subtitle="Manage your Taylee profile, appearance, and notifications.">
    <Card icon={User} title="Profile" note="Shown to teammates and in audit trails."><div className="grid gap-4 sm:grid-cols-2"><Field label="First name" value={profile.first_name} onChange={v => setProfile(p => ({ ...p, first_name: v }))} /><Field label="Last name" value={profile.last_name} onChange={v => setProfile(p => ({ ...p, last_name: v }))} /></div><Field label="Email address" value={user?.email || ''} disabled /><button onClick={save} disabled={saving} className="mt-4 flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500 disabled:opacity-50"><Save size={16} />{saving ? 'Saving…' : 'Save profile'}</button></Card>
    <Card icon={theme === 'dark' ? Moon : Sun} title="Appearance" note="Your choice is saved on this device."><div className="grid grid-cols-2 gap-3"><Choice active={theme === 'light'} icon={Sun} label="Light" onClick={() => theme !== 'light' && toggleTheme()} /><Choice active={theme === 'dark'} icon={Moon} label="Dark" onClick={() => theme !== 'dark' && toggleTheme()} /></div></Card>
    <Card icon={Bell} title="Notifications" note="Email preferences are saved to your account. Approval alerts apply to client reviews; period-close delivery will be available with period administration.">{[['email_notifications','Email notifications'],['approval_alerts','Approval requests']].map(([key,label]) => <label key={key} className="flex items-center justify-between border-b border-slate-100 py-3 last:border-0 dark:border-slate-800"><span className="text-sm">{label}</span><input type="checkbox" checked={!!prefs[key]} onChange={e => changePreference(key,e.target.checked)} className="h-4 w-4 accent-brand-600" /></label>)}</Card>
    {!user?.email_verified&&<Card icon={ShieldCheck} title="Verify your email" note="Verify ownership before accepting workspace invitations in production."><button className="rounded-lg bg-brand-600 px-4 py-2 text-white" onClick={()=>api.post('/auth/email/request/').then(()=>toast.success('Verification email queued')).catch(()=>toast.error('Could not request verification'))}>Send verification email</button></Card>}
    <Card icon={ShieldCheck} title="Security" note="Your workspace administrator manages access."><div className="flex items-center justify-between rounded-xl bg-slate-50 p-4 dark:bg-slate-800"><div><p className="text-sm font-medium">Current access role</p><p className="text-xs text-slate-500">Applies to {workspace?.name}</p></div><span className="rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold capitalize text-brand-700 dark:bg-brand-950 dark:text-brand-300">{workspace?.role}</span></div></Card>
  </Page>
}
function Page({ title, subtitle, children }) { return <div className="min-h-full bg-slate-50 p-8 dark:bg-slate-950"><div className="mx-auto max-w-4xl"><h1 className="text-2xl font-semibold text-slate-900 dark:text-white">{title}</h1><p className="mt-1 text-sm text-slate-500">{subtitle}</p><div className="mt-7 grid gap-5">{children}</div></div></div> }
function Card({ icon: Icon, title, note, children }) { return <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"><div className="mb-5 flex gap-3"><div className="rounded-xl bg-brand-50 p-2.5 text-brand-600 dark:bg-brand-950"><Icon size={20} /></div><div><h2 className="font-semibold">{title}</h2><p className="text-sm text-slate-500">{note}</p></div></div>{children}</section> }
function Field({ label, value, onChange, disabled }) { return <label className="mb-3 block"><span className="mb-1.5 block text-sm font-medium">{label}</span><input value={value} disabled={disabled} onChange={e => onChange?.(e.target.value)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-brand-400 disabled:bg-slate-100 disabled:text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:disabled:bg-slate-950" /></label> }
function Choice({ active, icon: Icon, label, onClick }) { return <button onClick={onClick} className={`flex items-center justify-between rounded-xl border p-4 text-left ${active ? 'border-brand-500 bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300' : 'border-slate-200 dark:border-slate-700'}`}><span className="flex items-center gap-3"><Icon size={19} />{label}</span>{active && <Check size={18} />}</button> }
