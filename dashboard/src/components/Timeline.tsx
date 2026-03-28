import React, { useRef, useEffect } from 'react'
import {
  Brain,
  Wrench,
  FileText,
  Terminal,
  GitFork,
  AlertCircle,
  ChevronRight,
} from 'lucide-react'
import { cn, getEventDescription, eventHadError, formatTimestamp, formatDuration } from '../lib/utils'
import type { AnyEvent, EventType, LLMCallEvent } from '../lib/types'

interface TimelineProps {
  events: AnyEvent[]
  selectedEventId?: string
  highlightedEventIds?: Set<string>
  replayIndex?: number
  onSelectEvent: (event: AnyEvent) => void
  onForkEvent: (event: LLMCallEvent) => void
  className?: string
}

function EventIcon({ type }: { type: EventType }) {
  const props = { size: 14, strokeWidth: 2 }
  switch (type) {
    case 'llm_call': return <Brain {...props} />
    case 'tool_call': return <Wrench {...props} />
    case 'file_change': return <FileText {...props} />
    case 'terminal_cmd': return <Terminal {...props} />
  }
}

function getEventTypeColors(type: EventType, hasError: boolean) {
  if (hasError) return 'bg-culpa-red-dim border-culpa-red text-culpa-red'
  switch (type) {
    case 'llm_call': return 'bg-culpa-blue-dim border-culpa-blue text-culpa-blue'
    case 'tool_call': return 'bg-culpa-purple-dim border-culpa-purple text-culpa-purple'
    case 'file_change': return 'bg-culpa-green-dim border-culpa-green text-culpa-green'
    case 'terminal_cmd': return 'bg-culpa-orange-dim border-culpa-orange text-culpa-orange'
  }
}

interface EventNodeProps {
  event: AnyEvent
  isSelected: boolean
  isHighlighted: boolean
  isReplaying: boolean
  isLast: boolean
  onSelect: () => void
  onFork: () => void
}

function EventNode({
  event,
  isSelected,
  isHighlighted,
  isReplaying,
  isLast,
  onSelect,
  onFork,
}: EventNodeProps) {
  const hasError = eventHadError(event)
  const iconColors = getEventTypeColors(event.event_type, hasError)
  const isLLMCall = event.event_type === 'llm_call'
  const llmEvent = isLLMCall ? (event as LLMCallEvent) : null

  const getDuration = () => {
    if (event.event_type === 'llm_call') return formatDuration((event as LLMCallEvent).latency_ms)
    if (event.event_type === 'tool_call' || event.event_type === 'terminal_cmd') {
      return formatDuration((event as { duration_ms: number }).duration_ms)
    }
    return null
  }

  const duration = getDuration()

  return (
    <div className="relative flex gap-3 group">
      {!isLast && (
        <div className="absolute left-[19px] top-[36px] bottom-0 w-px bg-culpa-border" />
      )}

      <div className="flex-shrink-0 relative z-10">
        <button
          onClick={onSelect}
          className={cn(
            'w-10 h-10 rounded-full border flex items-center justify-center transition-all duration-150',
            iconColors,
            isSelected && 'ring-2 ring-white/20 scale-110',
            isReplaying && 'animate-pulse-slow ring-2 ring-white/30',
            !isSelected && 'hover:scale-105',
          )}
        >
          {hasError ? <AlertCircle size={14} /> : <EventIcon type={event.event_type} />}
        </button>
      </div>

      <div
        className={cn(
          'flex-1 min-w-0 pb-4 cursor-pointer rounded-lg p-2 -m-2 transition-colors duration-100',
          isSelected ? 'bg-culpa-muted' : 'hover:bg-culpa-surface',
          isHighlighted && 'bg-culpa-muted/60',
        )}
        onClick={onSelect}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <p className={cn(
              'text-sm font-medium truncate',
              hasError ? 'text-culpa-red' : 'text-culpa-text',
            )}>
              {getEventDescription(event)}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-culpa-text-dim font-mono">
                {formatTimestamp(event.timestamp)}
              </span>
              {duration && (
                <>
                  <span className="text-culpa-border">·</span>
                  <span className="text-xs text-culpa-text-dim">{duration}</span>
                </>
              )}
              {hasError && (
                <>
                  <span className="text-culpa-border">·</span>
                  <span className="text-xs text-culpa-red">error</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {isLLMCall && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onFork()
                }}
                className={cn(
                  'opacity-0 group-hover:opacity-100 transition-opacity',
                  'p-1 rounded text-culpa-text-dim hover:text-culpa-blue hover:bg-culpa-blue-dim',
                )}
                title="Fork from here"
              >
                <GitFork size={12} />
              </button>
            )}
            {isSelected && (
              <ChevronRight size={14} className="text-culpa-text-dim" />
            )}
          </div>
        </div>

        {isLLMCall && llmEvent && (
          <div className="flex gap-3 mt-1.5">
            <span className="text-xs text-culpa-text-dim">
              ↑{llmEvent.token_usage?.input_tokens?.toLocaleString() || 0}
            </span>
            <span className="text-xs text-culpa-text-dim">
              ↓{llmEvent.token_usage?.output_tokens?.toLocaleString() || 0}
            </span>
          </div>
        )}

        {event.parent_event_id && (
          <div className="mt-1">
            <span className="text-xs text-culpa-text-dim/60 font-mono">
              child of {event.parent_event_id.slice(-8)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export function Timeline({
  events,
  selectedEventId,
  highlightedEventIds,
  replayIndex,
  onSelectEvent,
  onForkEvent,
  className,
}: TimelineProps) {
  const selectedRef = useRef<HTMLDivElement>(null)
  const replayingEventId = replayIndex !== undefined && replayIndex >= 0
    ? events[replayIndex]?.event_id
    : undefined

  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [selectedEventId])

  if (events.length === 0) {
    return (
      <div className={cn('flex items-center justify-center h-64 text-culpa-text-dim', className)}>
        No events recorded
      </div>
    )
  }

  return (
    <div className={cn('px-4 py-4 space-y-0', className)}>
      {events.map((event, i) => (
        <div
          key={event.event_id}
          ref={event.event_id === selectedEventId ? selectedRef : undefined}
        >
          <EventNode
            event={event}
            isSelected={event.event_id === selectedEventId}
            isHighlighted={highlightedEventIds?.has(event.event_id) ?? false}
            isReplaying={event.event_id === replayingEventId}
            isLast={i === events.length - 1}
            onSelect={() => onSelectEvent(event)}
            onFork={() => event.event_type === 'llm_call' && onForkEvent(event as LLMCallEvent)}
          />
        </div>
      ))}
    </div>
  )
}
