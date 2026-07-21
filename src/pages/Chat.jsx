import { useEffect, useMemo, useRef, useState } from 'react'
import { Hash, Lock, Plus, Send, Paperclip, Users as UsersIcon, Search, MoreVertical, Smile, X, MessageCircle, CheckCheck, Info, Bell, BellOff, Wallpaper, ChevronLeft } from 'lucide-react'
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
  const [search, setSearch] = useState('')
  const [messageSearch, setMessageSearch] = useState('')
  const [showMessageSearch, setShowMessageSearch] = useState(false)
  const [showChatInfo, setShowChatInfo] = useState(false)
  const [showChatMenu, setShowChatMenu] = useState(false)
  const [showWallpaper, setShowWallpaper] = useState(true)
  const [mutedChats, setMutedChats] = useState(() => JSON.parse(localStorage.getItem('taylee_muted_chats') || '[]'))

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

  const matchesSearch = (c) => {
    const other = c.participants.find((p) => p.user.id !== user?.id)?.user
    return `${c.name || ''} ${other?.first_name || ''} ${other?.email || ''} ${c.last_message?.body || ''}`.toLowerCase().includes(search.toLowerCase())
  }
  const channels = conversations.filter((c) => c.type === 'channel' && matchesSearch(c))
  const dms = conversations.filter((c) => c.type === 'dm' && matchesSearch(c))
  const typingInActive = [...(typingUsers[activeId] || [])].filter((id) => id !== user?.id)
  const isMuted = mutedChats.includes(activeId)
  function toggleMute() {
    const next = isMuted ? mutedChats.filter(id => id !== activeId) : [...mutedChats, activeId]
    setMutedChats(next); localStorage.setItem('taylee_muted_chats', JSON.stringify(next))
  }

  return (
    <div className="flex h-full bg-[#efeae2] dark:bg-slate-950">
      {/* Conversation list */}
      <div className="w-80 shrink-0 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 flex flex-col">
        <div className="h-16 flex items-center justify-between px-4 bg-[#f0f2f5] dark:bg-slate-800">
          <div className="flex items-center gap-3"><Avatar name={user?.first_name || user?.email} size={38} /><div><h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Messages</h2><p className="text-[11px] text-emerald-600">● Online</p></div></div>
          <button onClick={() => setShowNewModal('dm')} title="New chat" className="rounded-full p-2 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"><MessageCircle size={20} /></button>
        </div>

        <div className="border-b border-slate-100 p-2.5 dark:border-slate-800"><label className="relative block"><Search size={16} className="absolute left-3 top-2.5 text-slate-400" /><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search or start a new chat" className="w-full rounded-lg bg-[#f0f2f5] py-2 pl-9 pr-8 text-sm outline-none dark:bg-slate-800" />{search && <button onClick={() => setSearch('')} className="absolute right-2 top-2 text-slate-400"><X size={17} /></button>}</label></div>

        <div className="flex-1 overflow-y-auto py-2">
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
            <div className="h-16 shrink-0 flex items-center gap-3 px-5 border-b border-slate-200 dark:border-slate-700 bg-[#f0f2f5] dark:bg-slate-800">
              <Avatar name={activeConversation.type === 'channel' ? activeConversation.name : activeConversation.participants.find((p) => p.user.id !== user?.id)?.user.first_name} size={40} />
              {activeConversation.type === 'channel' ? (
                activeConversation.is_private ? <Lock size={16} className="text-slate-400 dark:text-slate-500" /> : <Hash size={16} className="text-slate-400 dark:text-slate-500" />
              ) : (
                <UsersIcon size={16} className="text-slate-400 dark:text-slate-500" />
              )}
              <div className="min-w-0 flex-1"><h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {activeConversation.type === 'channel'
                  ? activeConversation.name
                  : activeConversation.participants.find((p) => p.user.id !== user?.id)?.user.first_name || 'Direct message'}
              </h3>
              {activeConversation.project_name && (
                <span className="text-xs text-slate-400 dark:text-slate-500">in {activeConversation.project_name}</span>
              )}<p className="text-xs text-slate-500">{typingInActive.length ? 'typing…' : isMuted ? 'notifications muted' : 'online'}</p></div>
              <button onClick={() => { setShowMessageSearch(v => !v); setShowChatMenu(false) }} title="Search messages" className={`rounded-full p-2 hover:bg-slate-200 dark:hover:bg-slate-700 ${showMessageSearch ? 'bg-slate-200 text-emerald-600 dark:bg-slate-700' : 'text-slate-500'}`}><Search size={19} /></button>
              <button onClick={() => { setShowChatInfo(v => !v); setShowChatMenu(false) }} title="Conversation info" className={`rounded-full p-2 hover:bg-slate-200 dark:hover:bg-slate-700 ${showChatInfo ? 'bg-slate-200 text-emerald-600 dark:bg-slate-700' : 'text-slate-500'}`}><Info size={19} /></button>
              <div className="relative"><button onClick={() => setShowChatMenu(v => !v)} title="Chat settings" className={`rounded-full p-2 hover:bg-slate-200 dark:hover:bg-slate-700 ${showChatMenu ? 'bg-slate-200 text-emerald-600 dark:bg-slate-700' : 'text-slate-500'}`}><MoreVertical size={19} /></button>{showChatMenu && <ChatMenu muted={isMuted} wallpaper={showWallpaper} onMute={toggleMute} onWallpaper={() => setShowWallpaper(v => !v)} onInfo={() => { setShowChatInfo(true); setShowChatMenu(false) }} />}</div>
            </div>

            {showMessageSearch && <div className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 dark:border-slate-700 dark:bg-slate-900"><button onClick={() => { setShowMessageSearch(false); setMessageSearch('') }} className="rounded-full p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"><ChevronLeft size={19} /></button><label className="relative flex-1"><Search size={15} className="absolute left-3 top-2.5 text-slate-400" /><input autoFocus value={messageSearch} onChange={e => setMessageSearch(e.target.value)} placeholder="Search in this conversation" className="w-full rounded-lg bg-slate-100 py-2 pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-800" /></label><span className="text-xs text-slate-500">{messageSearch ? messages.filter(m => m.body.toLowerCase().includes(messageSearch.toLowerCase())).length : 0} found</span></div>}

            <MessageList messages={messages} currentUserId={user?.id} search={messageSearch} wallpaper={showWallpaper} />

            {typingInActive.length > 0 && (
              <p className="bg-[#efeae2] px-5 pb-1 text-xs text-emerald-600 dark:bg-slate-950 italic">Someone is typing…</p>
            )}

            <Composer onSend={sendMessage} onTyping={notifyTyping} />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-sm text-slate-400 dark:text-slate-500">
            Pick a channel or DM to start chatting.
          </div>
        )}
      </div>
      {showChatInfo && activeConversation && <ChatInfo conversation={activeConversation} currentUserId={user?.id} muted={isMuted} wallpaper={showWallpaper} onClose={() => setShowChatInfo(false)} onMute={toggleMute} onWallpaper={() => setShowWallpaper(v => !v)} />}

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
  const last = conversation.last_message
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-3 text-sm transition-colors ${
        active
          ? 'bg-[#f0f2f5] dark:bg-slate-800 text-slate-900 dark:text-white'
          : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/70'
      }`}
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-300">{icon}</span>
      <span className="min-w-0 flex-1 border-b border-slate-100 pb-2 text-left dark:border-slate-800"><span className="flex items-center justify-between gap-2"><strong className="truncate font-medium">{label}</strong><time className={`text-[11px] ${conversation.unread_count ? 'text-emerald-600' : 'text-slate-400'}`}>{last?.created_at ? new Date(last.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}</time></span><span className="mt-1 flex items-center justify-between gap-2"><span className="truncate text-xs font-normal text-slate-500">{last?.sender_name ? `${last.sender_name}: ` : ''}{last?.body || 'Start the conversation'}</span>{conversation.unread_count > 0 && <span className="min-w-5 rounded-full bg-emerald-500 px-1.5 py-0.5 text-center text-[10px] font-bold text-white">{conversation.unread_count}</span>}</span></span>
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

function MessageList({ messages, currentUserId, search, wallpaper }) {
  const bottomRef = useRef(null)
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className={`${wallpaper ? 'chat-doodle-bg' : 'bg-[#efeae2] dark:bg-slate-950'} flex-1 overflow-y-auto px-5 py-5 space-y-2`}>
      {!messages.length && <div className="mx-auto mt-20 max-w-sm rounded-xl bg-[#fff8c5] p-4 text-center text-xs leading-5 text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-300">Messages are protected inside your Taylee workspace. Say hello to begin the conversation.</div>}
      {messages.filter(m => !search || m.body.toLowerCase().includes(search.toLowerCase())).map((m) => {
        const mine = m.sender?.id === currentUserId
        const senderName = m.sender ? (m.sender.first_name || m.sender.email) : (m.sender_contact?.name || 'Customer')
        return (
          <div key={m.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
            <div className={`relative max-w-[75%] md:max-w-[65%] ${mine ? 'items-end' : 'items-start'} flex flex-col`}>
              <div
                className={`rounded-lg px-3 py-2 text-sm leading-relaxed shadow-sm ${
                  mine
                    ? 'bg-[#d9fdd3] text-slate-900 rounded-tr-none dark:bg-emerald-900 dark:text-white'
                    : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 rounded-tl-none'
                }`}
              >
                {!mine && <p className="mb-0.5 text-xs font-semibold text-brand-600 dark:text-brand-300">{senderName}</p>}
                <span className={`whitespace-pre-wrap break-words ${search ? 'rounded bg-yellow-200/80 px-0.5 text-slate-900' : ''}`}>{m.body}</span>
                {m.attachment && (
                  <a
                    href={m.attachment}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 flex items-center gap-1 rounded-md bg-black/5 p-2 text-xs text-brand-600 underline dark:bg-white/5 dark:text-brand-300"
                  >
                    <Paperclip size={12} /> Attachment
                  </a>
                )}<span className="ml-3 inline-flex translate-y-1 items-center gap-0.5 text-[10px] text-slate-500">{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}{mine && <CheckCheck size={14} className="text-sky-500" />}</span>
              </div>
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )
}

function ChatMenu({ muted, wallpaper, onMute, onWallpaper, onInfo }) {
  return <div className="absolute right-0 top-11 z-30 w-60 overflow-hidden rounded-xl border border-slate-200 bg-white py-2 text-sm shadow-xl dark:border-slate-700 dark:bg-slate-800">
    <button onClick={onInfo} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-100 dark:hover:bg-slate-700"><Info size={17} />Conversation info</button>
    <button onClick={onMute} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-100 dark:hover:bg-slate-700">{muted ? <Bell size={17} /> : <BellOff size={17} />}{muted ? 'Unmute notifications' : 'Mute notifications'}</button>
    <button onClick={onWallpaper} className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-100 dark:hover:bg-slate-700"><Wallpaper size={17} />{wallpaper ? 'Hide chat wallpaper' : 'Show chat wallpaper'}</button>
  </div>
}

function ChatInfo({ conversation, currentUserId, muted, wallpaper, onClose, onMute, onWallpaper }) {
  const other = conversation.participants.find(p => p.user.id !== currentUserId)?.user
  const title = conversation.type === 'channel' ? conversation.name : (other?.first_name || other?.email || 'Conversation')
  return <aside className="w-80 shrink-0 border-l border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
    <div className="flex h-16 items-center gap-4 bg-[#f0f2f5] px-4 dark:bg-slate-800"><button onClick={onClose} className="rounded-full p-1.5 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"><X size={20} /></button><h2 className="font-medium">Conversation info</h2></div>
    <div className="border-b border-slate-100 p-7 text-center dark:border-slate-800"><Avatar name={title} size={72} /><h3 className="mt-4 text-lg font-semibold">{conversation.type === 'channel' ? `#${title}` : title}</h3><p className="mt-1 text-sm text-slate-500">{conversation.type === 'channel' ? `${conversation.participants.length} participants` : other?.email}</p>{conversation.project_name && <p className="mt-2 text-xs text-brand-600">Project: {conversation.project_name}</p>}</div>
    <div className="border-b border-slate-100 py-2 dark:border-slate-800"><button onClick={onMute} className="flex w-full items-center justify-between px-5 py-3 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"><span className="flex items-center gap-3">{muted ? <BellOff size={18} /> : <Bell size={18} />}Mute notifications</span><span className={`h-5 w-9 rounded-full p-0.5 ${muted ? 'bg-emerald-500' : 'bg-slate-300'}`}><span className={`block h-4 w-4 rounded-full bg-white transition-transform ${muted ? 'translate-x-4' : ''}`} /></span></button><button onClick={onWallpaper} className="flex w-full items-center justify-between px-5 py-3 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"><span className="flex items-center gap-3"><Wallpaper size={18} />Chat wallpaper</span><span className={`h-5 w-9 rounded-full p-0.5 ${wallpaper ? 'bg-emerald-500' : 'bg-slate-300'}`}><span className={`block h-4 w-4 rounded-full bg-white transition-transform ${wallpaper ? 'translate-x-4' : ''}`} /></span></button></div>
    <div className="p-5"><p className="mb-3 text-xs font-semibold uppercase tracking-wide text-emerald-600">Participants</p>{conversation.participants.map(p => <div key={p.id} className="flex items-center gap-3 py-2"><Avatar name={p.user.first_name || p.user.email} size={34} /><div className="min-w-0"><p className="truncate text-sm font-medium">{p.user.id === currentUserId ? 'You' : p.user.first_name || p.user.email}</p><p className="truncate text-xs text-slate-500">{p.user.email}</p></div></div>)}</div>
  </aside>
}

function Composer({ onSend, onTyping }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const fileInputRef = useRef(null)
  const stopTypingTimeout = useRef(null)
  const [showEmoji, setShowEmoji] = useState(false)

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
    <form onSubmit={handleSubmit} className="relative border-t border-slate-200 bg-[#f0f2f5] p-3 flex items-end gap-2 dark:border-slate-700 dark:bg-slate-800">
      {showEmoji && <div className="absolute bottom-16 left-3 z-10 grid grid-cols-6 gap-1 rounded-xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-700 dark:bg-slate-800">{['😀','😂','😍','👍','🙏','🎉','✅','👋','💡','📌','🔥','❤️'].map(emoji => <button key={emoji} type="button" onClick={() => { setText(t => t + emoji); setShowEmoji(false) }} className="rounded p-1.5 text-xl hover:bg-slate-100 dark:hover:bg-slate-700">{emoji}</button>)}</div>}
      <button type="button" onClick={() => setShowEmoji(v => !v)} className="h-10 w-10 shrink-0 rounded-full text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700" title="Emoji"><Smile size={22} className="mx-auto" /></button>
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="h-10 w-10 shrink-0 rounded-full text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700 flex items-center justify-center"
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
          <div className="mb-2 flex items-center justify-between rounded-lg bg-white px-3 py-2 text-xs text-slate-600 shadow-sm dark:bg-slate-900 dark:text-slate-300"><span className="flex min-w-0 items-center gap-2"><Paperclip size={14} /><span className="truncate">{file.name}</span></span><button type="button" onClick={() => setFile(null)} className="ml-2 rounded-full p-1 text-red-500 hover:bg-red-50"><X size={14} /></button></div>
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
          placeholder="Type a message"
          className="max-h-32 w-full resize-none rounded-xl border-0 bg-white px-4 py-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 dark:bg-slate-900 dark:text-slate-100"
        />
      </div>
      <button
        type="submit"
        className="h-11 w-11 shrink-0 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white flex items-center justify-center shadow-sm disabled:opacity-50"
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
