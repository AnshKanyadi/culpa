/**
 * Detail view for file change events.
 * Shows a syntax-highlighted side-by-side diff.
 */

import React, { useState } from 'react'
import { FileText, Plus, Minus } from 'lucide-react'
import { cn } from '../lib/utils'
import type { FileChangeEvent } from '../lib/types'

function parseDiff(diff: string): Array<{ type: 'add' | 'remove' | 'context' | 'header'; content: string }> {
  return diff.split('\n').map((line) => {
    if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) {
      return { type: 'header' as const, content: line }
    }
    if (line.startsWith('+')) {
      return { type: 'add' as const, content: line.slice(1) }
    }
    if (line.startsWith('-')) {
      return { type: 'remove' as const, content: line.slice(1) }
    }
    return { type: 'context' as const, content: line.startsWith(' ') ? line.slice(1) : line }
  })
}

interface DiffViewerProps {
  diff: string
}

function DiffViewer({ diff }: DiffViewerProps) {
  const lines = parseDiff(diff)

  return (
    <div className="rounded-lg border border-prismo-border overflow-hidden font-mono text-xs">
      <div className="overflow-auto max-h-96">
        {lines.map((line, i) => (
          <div
            key={i}
            className={cn(
              'flex items-start px-3 py-0.5 leading-5',
              line.type === 'add' && 'bg-prismo-green-dim text-prismo-green',
              line.type === 'remove' && 'bg-prismo-red-dim text-prismo-red',
              line.type === 'header' && 'bg-prismo-muted text-prismo-text-dim',
              line.type === 'context' && 'text-prismo-text-dim',
            )}
          >
            <span className="w-4 flex-shrink-0 select-none mr-2">
              {line.type === 'add' && <Plus size={10} className="inline" />}
              {line.type === 'remove' && <Minus size={10} className="inline" />}
            </span>
            <pre className="whitespace-pre-wrap break-all flex-1">{line.content || ' '}</pre>
          </div>
        ))}
      </div>
    </div>
  )
}

function ContentView({ content, title }: { content: string; title: string }) {
  return (
    <div className="flex-1 min-w-0">
      <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">{title}</div>
      <div className="rounded-lg border border-prismo-border bg-prismo-surface overflow-auto max-h-80">
        <pre className="p-3 text-xs font-mono text-prismo-text whitespace-pre leading-relaxed">
          {content}
        </pre>
      </div>
    </div>
  )
}

interface FileChangeDetailProps {
  event: FileChangeEvent
}

export function FileChangeDetail({ event }: FileChangeDetailProps) {
  const [view, setView] = useState<'diff' | 'split' | 'before' | 'after'>('diff')

  const operationColor = {
    create: 'text-prismo-green bg-prismo-green-dim border-prismo-green/30',
    modify: 'text-prismo-orange bg-prismo-orange-dim border-prismo-orange/30',
    delete: 'text-prismo-red bg-prismo-red-dim border-prismo-red/30',
  }[event.operation]

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <FileText size={16} className="text-prismo-green flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-mono text-sm text-prismo-text truncate">{event.file_path}</div>
          {event.triggering_llm_call_id && (
            <div className="text-xs text-prismo-text-dim mt-0.5">
              Triggered by LLM call {event.triggering_llm_call_id.slice(-8)}
            </div>
          )}
        </div>
        <span className={cn('px-2 py-0.5 rounded border text-xs font-mono uppercase', operationColor)}>
          {event.operation}
        </span>
      </div>

      {/* View tabs */}
      {event.diff && (
        <div className="flex gap-1 p-1 bg-prismo-surface rounded-lg border border-prismo-border">
          {(['diff', 'split', 'before', 'after'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                'flex-1 py-1 px-2 rounded text-xs font-medium capitalize transition-colors',
                view === v
                  ? 'bg-prismo-muted text-prismo-text'
                  : 'text-prismo-text-dim hover:text-prismo-text',
              )}
            >
              {v}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {view === 'diff' && event.diff && <DiffViewer diff={event.diff} />}

      {view === 'split' && (
        <div className="flex gap-3">
          {event.content_before !== undefined && (
            <ContentView content={event.content_before || '(empty)'} title="Before" />
          )}
          {event.content_after !== undefined && (
            <ContentView content={event.content_after || '(deleted)'} title="After" />
          )}
        </div>
      )}

      {view === 'before' && event.content_before !== undefined && (
        <ContentView content={event.content_before || '(file was created)'} title="Before" />
      )}

      {view === 'after' && event.content_after !== undefined && (
        <ContentView content={event.content_after || '(file was deleted)'} title="After" />
      )}

      {/* Stats */}
      {event.diff && (
        <div className="flex gap-4 text-xs font-mono">
          <span className="text-prismo-green">
            +{(event.diff.match(/^\+[^+]/gm) || []).length} lines
          </span>
          <span className="text-prismo-red">
            -{(event.diff.match(/^-[^-]/gm) || []).length} lines
          </span>
        </div>
      )}
    </div>
  )
}
