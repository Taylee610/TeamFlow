import { useEffect } from 'react'
import { X } from 'lucide-react'

export default function Modal({ title, onClose, children }) {
  useEffect(() => {
    const closeOnEscape = (event) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])
  return (
    <div onMouseDown={(event) => event.target === event.currentTarget && onClose()} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 dark:bg-black/60 px-4">
      <div role="dialog" aria-modal="true" className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 dark:hover:bg-slate-700 dark:hover:text-white"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
