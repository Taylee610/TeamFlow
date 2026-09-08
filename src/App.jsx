import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Kanban from './pages/Kanban'
import Chat from './pages/Chat'
import Everything from './pages/Everything'
import People from './pages/People'
import ERP from './pages/ERP'
import Settings from './pages/Settings'
import Help from './pages/Help'
import AIAssistant from './pages/AIAssistant'
import ProjectWorkspace from './pages/ProjectWorkspace'
import TaskDetail from './pages/TaskDetail'

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <ToastContainer position="top-right" autoClose={3000} />
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/workspaces" element={<Workspaces />} />

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
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}
