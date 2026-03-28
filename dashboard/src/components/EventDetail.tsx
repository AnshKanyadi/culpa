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
        <Wrench size={16} className="text-culpa-purple" />
        <div className="font-mono text-sm text-culpa-purple">{event.tool_name}</div>
        {event.error && (
          <div className="flex items-center gap-1 text-xs text-culpa-red">
            <AlertCircle size={12} /> Error
          </div>
        )}
      </div>

      <div>
        <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">Input</div>
        <pre className="rounded-lg border border-culpa-border bg-culpa-surface p-3 text-xs font-mono text-culpa-text overflow-auto max-h-48">
          {JSON.stringify(event.input_arguments, null, 2)}
        </pre>
      </div>

      {event.output_result !== undefined && (
        <div>
          <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">Output</div>
          <pre className="rounded-lg border border-culpa-border bg-culpa-surface p-3 text-xs font-mono text-culpa-text overflow-auto max-h-48">
            {typeof event.output_result === 'string'
              ? event.output_result
              : JSON.stringify(event.output_result, null, 2)}
          </pre>
        </div>
      )}

      {event.error && (
        <div className="rounded-lg border border-culpa-red/30 bg-culpa-red-dim p-3">
          <div className="text-xs text-culpa-red font-mono">{event.error}</div>
        </div>
      )}

      {event.duration_ms > 0 && (
        <div className="text-xs text-culpa-text-dim">
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
        <img src="/culpa-logo.svg" alt="Culpa" className="h-12 w-12 mb-4" />
        <h3 className="text-culpa-text font-medium mb-2">Select an event</h3>
        <p className="text-sm text-culpa-text-dim max-w-xs">
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
