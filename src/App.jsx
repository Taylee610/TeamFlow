import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Signup from './pages/SignUp'
import Workspaces from './pages/Workspaces'
import Landing from './pages/Landing'
const Dashboard = lazy(() => import('./pages/Dashboard'))
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Kanban from './pages/Kanban'
import Chat from './pages/Chat'
import Everything from './pages/Everything'
import People from './pages/People'
const ERP = lazy(() => import('./pages/ERP'))
import Settings from './pages/Settings'
import Help from './pages/Help'
const AIAssistant = lazy(() => import('./pages/AIAssistant'))
const Tools = lazy(() => import('./pages/Tools'))
const PublicTools = lazy(() => import('./pages/PublicTools'))
const AccountRecovery = lazy(() => import('./pages/AccountRecovery'))
const Billing = lazy(() => import('./pages/Billing'))
const WorkspaceAccess = lazy(() => import('./pages/WorkspaceAccess'))
import ProjectWorkspace from './pages/ProjectWorkspace'
import TaskDetail from './pages/TaskDetail'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastContainer position="top-right" autoClose={3000} />
          <Suspense fallback={<div className="p-10 text-center text-slate-500">Loading…</div>}><Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/workspaces" element={<Workspaces />} />
            <Route path="/p/:id" element={<PublicTools kind="profiles" />} />
            <Route path="/f/:id" element={<PublicTools kind="forms" />} />
            <Route path="/account/reset" element={<AccountRecovery />} />
            <Route path="/account/verify" element={<AccountRecovery />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/projects/:id" element={<ProjectDetail />} />
                <Route path="/projects/:id/kanban" element={<Kanban />} />
                <Route path="/projects/:id/tasks/:taskId" element={<TaskDetail />} />
                <Route path="/projects/:id/:section" element={<ProjectWorkspace />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/everything" element={<Everything />} />
                <Route path="/people" element={<People />} />
                <Route path="/erp" element={<ERP />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/help" element={<Help />} />
                <Route path="/ai" element={<AIAssistant />} />
                <Route path="/tools" element={<Tools />} />
                <Route path="/tools/:tool" element={<Tools />} />
                <Route path="/billing" element={<Billing />} />
                <Route path="/access" element={<WorkspaceAccess />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes></Suspense>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
