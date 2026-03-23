/**
 * Fork modal — lets users inject an alternative LLM response and see what would have happened.
 */

import React, { useState, useEffect } from 'react'
import { X, GitFork, Loader2, AlertCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { cn, getEventDescription } from '../lib/utils'
import type { LLMCallEvent, ForkResult, AnyEvent } from '../lib/types'

function EventTimeline({ events, label, colorClass }: {
  events: AnyEvent[]
  label: string
  colorClass: string
}) {
  if (events.length === 0) {
    return (
      <div className="text-xs text-prismo-text-dim italic">No events</div>
    )
  }

  return (
    <div className="space-y-1.5">
      {events.slice(0, 10).map((event, i) => (
        <div key={event.event_id || i} className={cn('flex items-start gap-2 text-xs', colorClass)}>
          <div className="w-1.5 h-1.5 rounded-full bg-current mt-1 flex-shrink-0" />
          <span className="font-mono text-prismo-text-dim">
            {getEventDescription(event)}
          </span>
        </div>
      ))}
      {events.length > 10 && (
        <div className="text-xs text-prismo-text-dim pl-3.5">
          +{events.length - 10} more events
        </div>
      )}
    </div>
  )
}

function ForkComparisonView({ result }: { result: ForkResult }) {
  const [showDiffs, setShowDiffs] = useState(true)

  return (
    <div className="space-y-4 animate-slide-in">
      {/* Divergence summary */}
      {result.divergence_summary && (
        <div className="rounded-lg border border-prismo-border bg-prismo-muted p-3">
          <pre className="text-xs font-mono text-prismo-text-dim whitespace-pre-wrap">
            {result.divergence_summary}
          </pre>
        </div>
      )}

      {/* Side by side timelines */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-prismo-text-dim mb-2 uppercase tracking-wide">
            Original Path ({result.original_events_after.length} events)
          </div>
          <div className="rounded-lg border border-prismo-border bg-prismo-surface p-3">
            <EventTimeline
              events={result.original_events_after}
              label="Original"
              colorClass="text-prismo-text-dim"
            />
          </div>
        </div>
        <div>
          <div className="text-xs text-prismo-blue mb-2 uppercase tracking-wide">
            Forked Path ({result.forked_events.length} events)
          </div>
          <div className="rounded-lg border border-prismo-blue/30 bg-prismo-blue-dim p-3">
            <EventTimeline
              events={result.forked_events}
              label="Fork"
              colorClass="text-prismo-blue"
            />
          </div>
        </div>
      </div>

      {/* File diffs */}
      {Object.keys(result.file_diffs).length > 0 && (
        <div>
          <button
            className="flex items-center gap-1.5 text-xs text-prismo-text-dim mb-2 uppercase tracking-wide hover:text-prismo-text"
            onClick={() => setShowDiffs(!showDiffs)}
          >
            {showDiffs ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            File Diffs ({Object.keys(result.file_diffs).length} files differ)
          </button>
          {showDiffs && (
            <div className="space-y-3">
              {Object.entries(result.file_diffs).map(([path, diff]) => (
                <div key={path}>
                  <div className="text-xs font-mono text-prismo-text mb-1">{path}</div>
                  <pre className="rounded-lg border border-prismo-border bg-[#0d0d0f] p-2 text-xs font-mono overflow-auto max-h-32 text-prismo-text-dim">
                    {diff.slice(0, 1000)}{diff.length > 1000 ? '\n…' : ''}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface ForkModalProps {
  event: LLMCallEvent | null
  result: ForkResult | null
  isForking: boolean
  error: Error | null
  onClose: () => void
  onRunFork: (newResponse: string) => void
}

export function ForkModal({
  event,
  result,
  isForking,
  error,
  onClose,
  onRunFork,
}: ForkModalProps) {
  const [newResponse, setNewResponse] = useState('')

  useEffect(() => {
    if (event) {
      setNewResponse(event.response_content || '')
    }
  }, [event])

  if (!event) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-3xl max-h-[90vh] mx-4 rounded-xl border border-prismo-border bg-prismo-surface shadow-2xl flex flex-col overflow-hidden animate-slide-in">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-prismo-border flex-shrink-0">
          <div className="flex items-center gap-2">
            <GitFork size={16} className="text-prismo-blue" />
            <h2 className="text-sm font-semibold text-prismo-text">Fork Session</h2>
            <span className="text-xs text-prismo-text-dim font-mono">
              at event {event.event_id.slice(-8)}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded text-prismo-text-dim hover:text-prismo-text hover:bg-prismo-muted transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!result ? (
            <>
              {/* Event context */}
              <div>
                <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">
                  LLM Call — {event.model}
                </div>
                <div className="text-xs text-prismo-text-dim bg-prismo-muted border border-prismo-border rounded-lg p-2 font-mono">
                  Original response ↓
                </div>
              </div>

              {/* Editable response */}
              <div>
                <div className="text-xs text-prismo-blue mb-1.5 uppercase tracking-wide">
                  Alternative Response (edit below)
                </div>
                <textarea
                  value={newResponse}
                  onChange={(e) => setNewResponse(e.target.value)}
                  rows={10}
                  className="w-full rounded-lg border border-prismo-blue/40 bg-prismo-bg
                             text-sm font-mono text-prismo-text p-3 resize-y
                             focus:outline-none focus:ring-2 focus:ring-prismo-blue/30
                             placeholder:text-prismo-text-dim"
                  placeholder="Edit the LLM response to explore an alternative path..."
                />
                <div className="text-xs text-prismo-text-dim mt-1">
                  Modify this response to explore "what if the AI had said something different?"
                </div>
              </div>

              {error && (
                <div className="flex items-center gap-2 rounded-lg border border-prismo-red/30 bg-prismo-red-dim p-3">
                  <AlertCircle size={14} className="text-prismo-red flex-shrink-0" />
                  <div className="text-xs text-prismo-red">{error.message}</div>
                </div>
              )}
            </>
          ) : (
            <ForkComparisonView result={result} />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-prismo-border flex-shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-prismo-text-dim
                       hover:text-prismo-text hover:bg-prismo-muted transition-colors"
          >
            {result ? 'Close' : 'Cancel'}
          </button>

          {!result && (
            <button
              onClick={() => onRunFork(newResponse)}
              disabled={isForking || !newResponse.trim()}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                'bg-prismo-blue text-white hover:bg-prismo-blue/80',
                (isForking || !newResponse.trim()) && 'opacity-50 cursor-not-allowed',
              )}
            >
              {isForking ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Running Fork…
                </>
              ) : (
                <>
                  <GitFork size={14} />
                  Run Fork
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
