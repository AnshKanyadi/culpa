import React, { useEffect } from 'react'
import { X } from 'lucide-react'

interface KeyboardShortcutsHelpProps {
  isOpen: boolean
  onClose: () => void
}

const SHORTCUTS = [
  { key: 'j', description: 'Next event' },
  { key: 'k', description: 'Previous event' },
  { key: 'Space', description: 'Play / pause replay' },
  { key: 'f', description: 'Fork at selected event' },
  { key: '1', description: 'Filter: LLM calls' },
  { key: '2', description: 'Filter: Tool calls' },
  { key: '3', description: 'Filter: File changes' },
  { key: '4', description: 'Filter: Terminal commands' },
  { key: 'Esc', description: 'Clear selection & filters' },
  { key: '?', description: 'Show this help' },
]

export function KeyboardShortcutsHelp({ isOpen, onClose }: KeyboardShortcutsHelpProps) {
  useEffect(() => {
    if (!isOpen) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        onClose()
      }
    }
    window.addEventListener('keydown', handleKey, true)
    return () => window.removeEventListener('keydown', handleKey, true)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/60" />

      <div
        className="relative bg-culpa-surface border border-culpa-border rounded-xl p-6 w-80 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-culpa-text">Keyboard Shortcuts</h2>
          <button
            onClick={onClose}
            className="p-1 rounded text-culpa-text-dim hover:text-culpa-text hover:bg-culpa-muted transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        <div className="space-y-2.5">
          {SHORTCUTS.map(({ key, description }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-xs text-culpa-text-dim">{description}</span>
              <kbd className="px-2 py-0.5 text-xs font-mono text-culpa-text bg-culpa-muted border border-culpa-border rounded min-w-[28px] text-center">
                {key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
