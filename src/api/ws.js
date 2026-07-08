// Builds a ws:// (or wss://) URL for the chat socket, using the same
// access token the REST client already attaches as a Bearer header.
// Browsers can't set custom headers on a WebSocket handshake, so the
// token travels as a query param instead -- see chat/middleware.py.
export function getChatSocketUrl(conversationId) {
  const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api'
  const httpBase = apiBase.replace(/\/api\/?$/, '')
  const wsBase = httpBase.replace(/^http/, 'ws')
  const token = localStorage.getItem('access_token') || ''
  return `${wsBase}/ws/chat/conversations/${conversationId}/?token=${encodeURIComponent(token)}`
}