import { useEffect, useMemo, useRef, useState } from 'react'
import { Hash, Lock, Plus, Send, Paperclip, Users as UsersIcon } from 'lucide-react'
import { toast } from 'react-toastify'
import api from '../api/axios'
import { useAuth } from '../context/AuthContext'
import { getChatSocketUrl } from '../api/ws'
import Modal from '../components/Modal'
import LoadingState from '../components/LoadingState'

export default function Chat() {
  const { user } = useAuth()
  const [conversations, setConversations] = useState(null)
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [typingUsers, setTypingUsers] = useState({}) // { [conversationId]: Set(userId) }
  const [colleagues, setColleagues] = useState([])
  const [showNewModal, setShowNewModal] = useState(null) // 'channel' | 'dm' | null

  const socketRef = useRef(null)
  const typingTimeoutRef = useRef(null)

  function loadConversations() {
    api.get('/chat/conversations/').then(({ data }) => {
      const list = data.results ?? data
      setConversations(list)
      if (!activeId && list.length) setActiveId(list[0].id)
    })
  }

  useEffect(loadConversations, [])

  // Build a de-duped list of everyone you share a project with, for the
  // "new channel" member-picker and "new DM" recipient-picker.
  useEffect(() => {
    api.get('/projects/?page_size=200').then(({ data }) => {
      const projects = data.results ?? data
      const byId = new Map()
      projects.forEach((p) => {
        if (p.owner && p.owner.id !== user?.id) byId.set(p.owner.id, p.owner)
        ;(p.members || []).forEach((m) => {
          if (m.id !== user?.id) byId.set(m.id, m)
        })
      })
      setColleagues([...byId.values()])
    })
  }, [user])

  // Load history + open the socket whenever the active conversation changes.
  useEffect(() => {
    if (!activeId) return

    setMessages([])
    api.get(`/chat/conversations/${activeId}/messages/?page_size=100`).then(({ data }) => {
      setMessages(data.results ?? data)
    })
    api.post(`/chat/conversations/${activeId}/read/`).catch(() => {})

    const socket = new WebSocket(getChatSocketUrl(activeId))
    socketRef.current = socket

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data)
      if (payload.kind === 'message') {
        setMessages((prev) => [...prev, payload.message])
      } else if (payload.kind === 'typing') {
        setTypingUsers((prev) => {
          const current = new Set(prev[activeId])
          if (payload.is_typing) current.add(payload.user_id)
          else current.delete(payload.user_id)
          return { ...prev, [activeId]: current }
        })
      }
    }

    return () => socket.close()
  }, [activeId])

  const activeConversation = useMemo(
    () => conversations?.find((c) => c.id === activeId) || null,
    [conversations, activeId]
  )

  async function sendMessage(body, attachment) {
    if (!body.trim() && !attachment) return
    const formData = attachment ? buildFormData(body, attachment) : null
    try {
      if (formData) {
        await api.post(`/chat/conversations/${activeId}/messages/`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      } else {
        await api.post(`/chat/conversations/${activeId}/messages/`, { body })
      }
      // The socket broadcast (which includes our own send) appends the
      // message to the thread, so we don't need to append it here too.
      loadConversations()
    } catch {
      toast.error("Couldn't send that message.")
    }
  }

  function buildFormData(body, attachment) {
    const fd = new FormData()
    fd.append('body', body)
    fd.append('attachment', attachment)
    return fd
  }

  function notifyTyping(isTyping) {
    if (socketRef.current?.readyState !== WebSocket.OPEN) return
    socketRef.current.send(JSON.stringify({ type: 'typing', is_typing: isTyping }))
  }

  async function createConversation(payload) {
    try {
      const { data } = await api.post('/chat/conversations/', payload)
      setShowNewModal(null)
      loadConversations()
      setActiveId(data.id)
    } catch (err) {
      toast.error(err.response?.data?.name?.[0] || err.response?.data?.member_ids?.[0] || 'Could not start that conversation.')
    }
  }

  if (!conversations) {
    return <LoadingState label="Loading chat..." />
  }

  const channels = conversations.filter((c) => c.type === 'channel')
  const dms = conversations.filter((c) => c.type === 'dm')
  const typingInActive = [...(typingUsers[activeId] || [])].filter((id) => id !== user?.id)

  return (
    <div className="flex h-full">
      {/* Conversation list */}
      <div className="w-72 shrink-0 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col">
        <div className="h-16 flex items-center justify-between px-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Chat</h2>
        </div>

        <div className="flex-1 overflow-y-auto py-3">
          <SectionHeader label="Channels" onAdd={() => setShowNewModal('channel')} />
          {channels.map((c) => (
            <ConversationRow
              key={c.id}
              conversation={c}
              active={c.id === activeId}
              onClick={() => setActiveId(c.id)}
              icon={c.is_private ? <Lock size={14} /> : <Hash size={14} />}
              label={c.name}
            />
          ))}

          <SectionHeader label="Direct messages" onAdd={() => setShowNewModal('dm')} />
          {dms.map((c) => {
            const other = c.participants.find((p) => p.user.id !== user?.id)?.user
            return (
              <ConversationRow
                key={c.id}
                conversation={c}
                active={c.id === activeId}
                onClick={() => setActiveId(c.id)}
                icon={<Avatar name={other?.first_name || other?.email} size={18} />}
                label={other?.first_name || other?.email || 'Unknown'}
              />
            )
          })}
        </div>
      </div>

      {/* Thread */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeConversation ? (
          <>
            <div className="h-16 shrink-0 flex items-center gap-2 px-5 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
              {activeConversation.type === 'channel' ? (
                activeConversation.is_private ? <Lock size={16} className="text-slate-400 dark:text-slate-500" /> : <Hash size={16} className="text-slate-400 dark:text-slate-500" />
              ) : (
                <UsersIcon size={16} className="text-slate-400 dark:text-slate-500" />
              )}
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {activeConversation.type === 'channel'
                  ? activeConversation.name
                  : activeConversation.participants.find((p) => p.user.id !== user?.id)?.user.first_name || 'Direct message'}
              </h3>
              {activeConversation.project_name && (
                <span className="text-xs text-slate-400 dark:text-slate-500">in {activeConversation.project_name}</span>
              )}
            </div>

            <MessageList messages={messages} currentUserId={user?.id} />

            {typingInActive.length > 0 && (
              <p className="px-5 text-xs text-slate-400 dark:text-slate-500 italic">Someone is typing…</p>
            )}

            <Composer onSend={sendMessage} onTyping={notifyTyping} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-slate-400 dark:text-slate-500">
            Pick a channel or DM to start chatting.
          </div>
        )}
      </div>

      {showNewModal === 'channel' && (
        <NewChannelModal onClose={() => setShowNewModal(null)} onCreate={createConversation} />
      )}
      {showNewModal === 'dm' && (
        <NewDmModal colleagues={colleagues} onClose={() => setShowNewModal(null)} onCreate={createConversation} />
      )}
    </div>
  )
}

function SectionHeader({ label, onAdd }) {
  return (
    <div className="flex items-center justify-between px-4 mt-3 mb-1">
      <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">{label}</span>
      <button onClick={onAdd} className="text-slate-400 dark:text-slate-500 hover:text-brand-600 dark:hover:text-brand-400" title={`New ${label.toLowerCase()}`}>
        <Plus size={14} />
      </button>
    </div>
  )
}

function ConversationRow({ conversation, active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-2 px-4 py-2 text-sm transition-colors ${
        active
          ? 'bg-brand-50 dark:bg-brand-950/50 text-brand-700 dark:text-brand-400 font-medium'
          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50'
      }`}
    >
      {icon}
      <span className="truncate flex-1 text-left">{label}</span>
      {conversation.unread_count > 0 && (
        <span className="text-[10px] font-semibold bg-brand-600 text-white rounded-full px-1.5 py-0.5">
          {conversation.unread_count}
        </span>
      )}
    </button>
  )
}

function Avatar({ name, size = 24 }) {
  return (
    <span
      style={{ height: size, width: size, fontSize: size * 0.45 }}
      className="rounded-full bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300 flex items-center justify-center font-semibold shrink-0"
    >
      {(name || '?').slice(0, 1).toUpperCase()}
    </span>
  )
}

function MessageList({ messages, currentUserId }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
      {messages.map((m) => {
        const mine = m.sender?.id === currentUserId
        const senderName = m.sender ? (m.sender.first_name || m.sender.email) : (m.sender_contact?.name || 'Customer')
        return (
          <div key={m.id} className={`flex gap-2 ${mine ? 'flex-row-reverse' : ''}`}>
            <Avatar name={senderName} size={28} />
            <div className={`max-w-md ${mine ? 'items-end' : 'items-start'} flex flex-col`}>
              <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 mb-0.5">
                <span className="font-medium text-slate-600 dark:text-slate-300">{mine ? 'You' : senderName}</span>
                <span>{new Date(m.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</span>
              </div>
              <div
                className={`rounded-2xl px-3.5 py-2 text-sm leading-snug ${
                  mine
                    ? 'bg-brand-600 text-white rounded-tr-sm'
                    : 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-tl-sm'
                }`}
              >
                {m.body}
                {m.attachment && (
                  <a
                    href={m.attachment}
                    target="_blank"
                    rel="noreferrer"
                    className={`mt-1 flex items-center gap-1 text-xs underline ${mine ? 'text-brand-100' : 'text-brand-600 dark:text-brand-400'}`}
                  >
                    <Paperclip size={12} /> Attachment
                  </a>
                )}
              </div>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}

function Composer({ onSend, onTyping }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const fileInputRef = useRef(null)
  const stopTypingTimeout = useRef(null)

  function handleChange(e) {
    setText(e.target.value)
    onTyping(true)
    clearTimeout(stopTypingTimeout.current)
    stopTypingTimeout.current = setTimeout(() => onTyping(false), 1500)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim() && !file) return
    onSend(text, file)
    setText('')
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    onTyping(false)
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-3 flex items-end gap-2">
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="h-9 w-9 shrink-0 rounded-lg text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 dark:hover:text-slate-300 flex items-center justify-center"
        title="Attach a file"
      >
        <Paperclip size={18} />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <div className="flex-1">
        {file && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1">
            <Paperclip size={12} /> {file.name}
            <button type="button" onClick={() => setFile(null)} className="text-red-500 dark:text-red-400 ml-1">
              remove
            </button>
          </p>
        )}
        <textarea
          value={text}
          onChange={handleChange}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          rows={1}
          placeholder="Message… (Enter to send, Shift+Enter for a new line)"
          className="w-full resize-none rounded-lg border border-slate-200 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
        />
      </div>
      <button
        type="submit"
        className="h-9 w-9 shrink-0 rounded-lg bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-center"
        title="Send"
      >
        <Send size={16} />
      </button>
    </form>
  )
}

function NewChannelModal({ onClose, onCreate }) {
  const [name, setName] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)

  return (
    <Modal title="New channel" onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onCreate({ type: 'channel', name, is_private: isPrivate })
        }}
        className="space-y-4"
      >
        <div>
          <label className="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">Channel name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. general"
            className="w-full rounded-lg border border-slate-200 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-brand-400"
            required
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)} />
          Private channel
        </label>
        <button type="submit" className="w-full rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium py-2">
          Create channel
        </button>
      </form>
    </Modal>
  )
}

function NewDmModal({ colleagues, onClose, onCreate }) {
  return (
    <Modal title="New direct message" onClose={onClose}>
      {colleagues.length ? (
        <div className="space-y-1 max-h-72 overflow-y-auto">
          {colleagues.map((person) => (
            <button
              key={person.id}
              onClick={() => onCreate({ type: 'dm', member_ids: [person.id] })}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 text-left"
            >
              <Avatar name={person.first_name || person.email} size={28} />
              <span className="text-sm text-slate-800 dark:text-slate-200">{person.first_name || person.email}</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          You don't share a project with anyone yet -- add teammates to a project first.
        </p>
      )}
    </Modal>
  )
}
