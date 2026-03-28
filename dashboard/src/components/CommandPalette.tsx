import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  LayoutDashboard,
  Key,
  CreditCard,
  Clock,
} from 'lucide-react'
import { api } from '../api/client'
import { cn, formatRelativeTime } from '../lib/utils'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

interface CommandItem {
  id: string
  label: string
  description?: string
  icon: React.ReactNode
  action: () => void
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const { data: sessionsData } = useQuery({
    queryKey: ['sessions', { page: 1, page_size: 10 }],
    queryFn: () => api.sessions.list({ page: 1, page_size: 10 }),
    enabled: isOpen,
  })

  const navCommands: CommandItem[] = [
    { id: 'nav-sessions', label: 'Sessions', description: 'Go to sessions list', icon: <LayoutDashboard size={14} />, action: () => { navigate('/'); onClose() } },
    { id: 'nav-keys', label: 'API Keys', description: 'Manage API keys', icon: <Key size={14} />, action: () => { navigate('/settings/keys'); onClose() } },
    { id: 'nav-billing', label: 'Billing', description: 'Plan & subscription', icon: <CreditCard size={14} />, action: () => { navigate('/settings/billing'); onClose() } },
  ]

  const sessionCommands: CommandItem[] = (sessionsData?.sessions || []).map((s) => ({
    id: `session-${s.id}`,
    label: s.name,
    description: formatRelativeTime(s.started_at),
    icon: <Clock size={14} />,
    action: () => { navigate(`/session/${s.id}`); onClose() },
  }))

  const allCommands = [...navCommands, ...sessionCommands]
  const filtered = query
    ? allCommands.filter((c) =>
        c.label.toLowerCase().includes(query.toLowerCase()) ||
        c.description?.toLowerCase().includes(query.toLowerCase())
      )
    : allCommands

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  useEffect(() => {
    setSelectedIndex((i) => Math.min(i, Math.max(0, filtered.length - 1)))
  }, [filtered.length])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((i) => Math.max(i - 1, 0))
        break
      case 'Enter':
        e.preventDefault()
        if (filtered[selectedIndex]) filtered[selectedIndex].action()
        break
      case 'Escape':
        onClose()
        break
    }
  }, [filtered, selectedIndex, onClose])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg bg-culpa-surface border border-culpa-border rounded-2xl shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 border-b border-culpa-border">
          <Search size={16} className="text-culpa-text-dim shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0) }}
            onKeyDown={handleKeyDown}
            placeholder="Search sessions, navigate..."
            className="flex-1 py-3 bg-transparent text-sm text-culpa-text placeholder:text-culpa-text-dim
                       focus:outline-none"
          />
          <kbd className="text-[10px] text-culpa-text-dim bg-culpa-muted border border-culpa-border px-1.5 py-0.5 rounded font-mono">
            esc
          </kbd>
        </div>

        <div className="max-h-72 overflow-y-auto py-2">
          {filtered.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-culpa-text-dim">
              No results
            </div>
          )}
          {filtered.map((cmd, i) => (
            <button
              key={cmd.id}
              onClick={cmd.action}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors',
                i === selectedIndex ? 'bg-culpa-muted' : 'hover:bg-culpa-muted/50',
              )}
            >
              <span className="text-culpa-text-dim shrink-0">{cmd.icon}</span>
              <div className="flex-1 min-w-0">
                <span className="text-sm text-culpa-text truncate block">{cmd.label}</span>
                {cmd.description && (
                  <span className="text-xs text-culpa-text-dim">{cmd.description}</span>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
