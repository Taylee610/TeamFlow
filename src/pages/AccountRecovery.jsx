import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import api from '../api/axios'
import { errorText } from './Tools'

export default function AccountRecovery(){
  const location=useLocation(),params=new URLSearchParams(location.search),verify=location.pathname.endsWith('/verify'),token=params.get('token'),uid=params.get('uid')
  const [email,setEmail]=useState(''),[password,setPassword]=useState(''),[message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false)
  async function submit(event){event.preventDefault();setBusy(true);setError('');try{const path=verify?'/auth/email/verify/':token?'/auth/password/confirm/':'/auth/password/reset/';const {data}=await api.post(path,verify?{token}:token?{uid,token,password}:{email});setMessage(data.detail)}catch(e){setError(errorText(e))}finally{setBusy(false)}}
  return <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 dark:bg-slate-950"><form onSubmit={submit} className="w-full max-w-md space-y-5 rounded-2xl border bg-white p-8 dark:bg-slate-900"><h1 className="text-2xl font-semibold">{verify?'Verify email':token?'Choose a new password':'Recover your account'}</h1>{error&&<p role="alert" className="text-sm text-red-600">{error}</p>}{message?<p className="text-sm text-emerald-600">{message}</p>:<>{!verify&&<label className="block text-sm">{token?'New password':'Email address'}<input required type={token?'password':'email'} minLength={token?8:undefined} value={token?password:email} onChange={e=>token?setPassword(e.target.value):setEmail(e.target.value)} className="mt-2 w-full rounded-lg border bg-transparent p-3"/></label>}<button disabled={busy||verify&&!token} className="w-full rounded-lg bg-brand-600 p-3 text-white disabled:opacity-50">{busy?'Please wait…':verify?'Confirm email':token?'Reset password':'Send reset email'}</button></>}<Link to="/login" className="block text-sm text-brand-500">Back to sign in</Link></form></div>
}
