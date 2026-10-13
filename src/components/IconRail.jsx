import { Plus, Search, Sun, Moon } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export default function IconRail({ onCreateClick, onSearchClick }) {
  const { theme, toggleTheme } = useTheme()
  return <div className="w-16 shrink-0 bg-slate-900 flex flex-col items-center py-4">
    <button onClick={onCreateClick} title="Create" aria-label="Create" className="h-10 w-10 rounded-xl bg-brand-600 hover:bg-brand-500 text-white flex items-center justify-center"><Plus size={20} /></button>
    <button onClick={onSearchClick} title="Search" aria-label="Search" className="mt-4 h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center"><Search size={20} /></button>
    <div className="flex-1" />
    <button onClick={toggleTheme} title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'} className="h-10 w-10 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 flex items-center justify-center">{theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}</button>
  </div>
}
