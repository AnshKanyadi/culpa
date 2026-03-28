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
    <div className="rounded-lg border border-culpa-border overflow-hidden font-mono text-xs">
      <div className="overflow-auto max-h-96">
        {lines.map((line, i) => (
          <div
            key={i}
            className={cn(
              'flex items-start px-3 py-0.5 leading-5',
              line.type === 'add' && 'bg-culpa-green-dim text-culpa-green',
              line.type === 'remove' && 'bg-culpa-red-dim text-culpa-red',
              line.type === 'header' && 'bg-culpa-muted text-culpa-text-dim',
              line.type === 'context' && 'text-culpa-text-dim',
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
      <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">{title}</div>
      <div className="rounded-lg border border-culpa-border bg-culpa-surface overflow-auto max-h-80">
        <pre className="p-3 text-xs font-mono text-culpa-text whitespace-pre leading-relaxed">
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
    create: 'text-culpa-green bg-culpa-green-dim border-culpa-green/30',
    modify: 'text-culpa-orange bg-culpa-orange-dim border-culpa-orange/30',
    delete: 'text-culpa-red bg-culpa-red-dim border-culpa-red/30',
  }[event.operation]

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <FileText size={16} className="text-culpa-green flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="font-mono text-sm text-culpa-text truncate">{event.file_path}</div>
          {event.triggering_llm_call_id && (
            <div className="text-xs text-culpa-text-dim mt-0.5">
              Triggered by LLM call {event.triggering_llm_call_id.slice(-8)}
            </div>
          )}
        </div>
        <span className={cn('px-2 py-0.5 rounded border text-xs font-mono uppercase', operationColor)}>
          {event.operation}
        </span>
      </div>

      {event.diff && (
        <div className="flex gap-1 p-1 bg-culpa-surface rounded-lg border border-culpa-border">
          {(['diff', 'split', 'before', 'after'] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                'flex-1 py-1 px-2 rounded text-xs font-medium capitalize transition-colors',
                view === v
                  ? 'bg-culpa-muted text-culpa-text'
                  : 'text-culpa-text-dim hover:text-culpa-text',
              )}
            >
              {v}
            </button>
          ))}
        </div>
      )}

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

      {event.diff && (
        <div className="flex gap-4 text-xs font-mono">
          <span className="text-culpa-green">
            +{(event.diff.match(/^\+[^+]/gm) || []).length} lines
          </span>
          <span className="text-culpa-red">
            -{(event.diff.match(/^-[^-]/gm) || []).length} lines
          </span>
        </div>
      )}
    </div>
  )
}
