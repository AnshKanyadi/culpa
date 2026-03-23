/**
 * Center panel — routes to the correct detail component based on event type.
 */

import React from 'react'
import type { AnyEvent, LLMCallEvent } from '../lib/types'
import { LLMCallDetail } from './LLMCallDetail'
import { FileChangeDetail } from './FileChangeDetail'
import { TerminalDetail } from './TerminalDetail'
import { Wrench, AlertCircle } from 'lucide-react'
import { cn } from '../lib/utils'

function ToolCallDetailView({ event }: { event: Extract<AnyEvent, { event_type: 'tool_call' }> }) {
  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <Wrench size={16} className="text-prismo-purple" />
        <div className="font-mono text-sm text-prismo-purple">{event.tool_name}</div>
        {event.error && (
          <div className="flex items-center gap-1 text-xs text-prismo-red">
            <AlertCircle size={12} /> Error
          </div>
        )}
      </div>

      <div>
        <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">Input</div>
        <pre className="rounded-lg border border-prismo-border bg-prismo-surface p-3 text-xs font-mono text-prismo-text overflow-auto max-h-48">
          {JSON.stringify(event.input_arguments, null, 2)}
        </pre>
      </div>

      {event.output_result !== undefined && (
        <div>
          <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">Output</div>
          <pre className="rounded-lg border border-prismo-border bg-prismo-surface p-3 text-xs font-mono text-prismo-text overflow-auto max-h-48">
            {typeof event.output_result === 'string'
              ? event.output_result
              : JSON.stringify(event.output_result, null, 2)}
          </pre>
        </div>
      )}

      {event.error && (
        <div className="rounded-lg border border-prismo-red/30 bg-prismo-red-dim p-3">
          <div className="text-xs text-prismo-red font-mono">{event.error}</div>
        </div>
      )}

      {event.duration_ms > 0 && (
        <div className="text-xs text-prismo-text-dim">
          Duration: {event.duration_ms.toFixed(0)}ms
        </div>
      )}
    </div>
  )
}

interface EventDetailProps {
  event: AnyEvent | null
  onFork: (event: LLMCallEvent) => void
  className?: string
}

export function EventDetail({ event, onFork, className }: EventDetailProps) {
  if (!event) {
    return (
      <div className={cn('flex flex-col items-center justify-center h-full text-center p-8', className)}>
        <div className="text-4xl mb-4">🔮</div>
        <h3 className="text-prismo-text font-medium mb-2">Select an event</h3>
        <p className="text-sm text-prismo-text-dim max-w-xs">
          Click any event in the timeline to inspect its details, or press Play to replay the session.
        </p>
      </div>
    )
  }

  return (
    <div className={cn('p-4 overflow-auto', className)}>
      {event.event_type === 'llm_call' && (
        <LLMCallDetail
          event={event as LLMCallEvent}
          onFork={() => onFork(event as LLMCallEvent)}
        />
      )}
      {event.event_type === 'tool_call' && (
        <ToolCallDetailView
          event={event as Extract<AnyEvent, { event_type: 'tool_call' }>}
        />
      )}
      {event.event_type === 'file_change' && (
        <FileChangeDetail
          event={event as Extract<AnyEvent, { event_type: 'file_change' }>}
        />
      )}
      {event.event_type === 'terminal_cmd' && (
        <TerminalDetail
          event={event as Extract<AnyEvent, { event_type: 'terminal_cmd' }>}
        />
      )}
    </div>
  )
}
