import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
})

// Attach the access token to every request if we have one.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const workspaceId = localStorage.getItem('workspace_id')
  if (workspaceId) config.headers['X-Workspace-ID'] = workspaceId
  return config
})

// If a request comes back 401, try refreshing the access token once and
// replay the original request. If the refresh itself fails, log the user
// out (clear tokens) so the app can redirect to /login.
let isRefreshing = false
let pendingQueue = []

function resolveQueue(error, token = null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  pendingQueue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const status = error.response?.status

    if (status !== 401 || originalRequest._retry || originalRequest.url?.includes('/auth/token/')) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      const { data } = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      })
      localStorage.setItem('access_token', data.access)
      if (data.refresh) localStorage.setItem('refresh_token', data.refresh)
      resolveQueue(null, data.access)
      originalRequest.headers.Authorization = `Bearer ${data.access}`
      return api(originalRequest)
    } catch (refreshError) {
      resolveQueue(refreshError, null)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.dispatchEvent(new Event('auth-expired'))
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default api
