import React, { useState, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { ArrowLeft, GitCompare, Brain, Wrench, FileText, Terminal } from 'lucide-react'
import { useSession, useSessions } from '../hooks/useSession'
import { cn, getEventDescription, formatTimestamp, formatDuration, formatTokens, formatCost, getSessionId } from '../lib/utils'
import type { AnyEvent, LLMCallEvent, Session, SessionListItem } from '../lib/types'

function getEventIcon(eventType: string) {
  switch (eventType) {
    case 'llm_call': return Brain
    case 'tool_call': return Wrench
    case 'file_change': return FileText
    case 'terminal_cmd': return Terminal
    default: return FileText
  }
}

function getEventIconColor(eventType: string) {
  switch (eventType) {
    case 'llm_call': return 'text-culpa-blue'
    case 'tool_call': return 'text-culpa-purple'
    case 'file_change': return 'text-culpa-green'
    case 'terminal_cmd': return 'text-culpa-orange'
    default: return 'text-culpa-text-dim'
  }
}

function findDivergenceIndex(eventsA: AnyEvent[], eventsB: AnyEvent[]): number {
  const len = Math.min(eventsA.length, eventsB.length)
  for (let i = 0; i < len; i++) {
    if (eventsA[i].event_type !== eventsB[i].event_type) return i
    if (eventsA[i].event_type === 'llm_call') {
      const a = eventsA[i] as LLMCallEvent
      const b = eventsB[i] as LLMCallEvent
      if (a.response_content !== b.response_content) return i
    }
  }
  return -1
}

function SessionPicker({
  sessions,
  isLoading,
  selectedId,
  onSelect,
}: {
  sessions: SessionListItem[]
  isLoading: boolean
  selectedId: string
  onSelect: (id: string) => void
}) {
  return (
    <select
      value={selectedId}
      onChange={(e) => onSelect(e.target.value)}
      className="bg-culpa-bg border border-culpa-border rounded px-3 py-2 text-sm text-culpa-text w-full max-w-md focus:outline-none focus:border-culpa-blue"
    >
      <option value="">Select a session...</option>
      {isLoading && <option disabled>Loading sessions...</option>}
      {sessions.map((s) => (
        <option key={s.id} value={s.id}>
          {s.name} ({s.status})
        </option>
      ))}
    </select>
  )
}

function SkeletonColumn() {
  return (
    <div className="flex-1 p-4 space-y-3">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-start gap-3 animate-pulse">
          <div className="w-5 h-5 rounded bg-culpa-muted flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 bg-culpa-muted rounded w-3/4" />
            <div className="h-2.5 bg-culpa-muted rounded w-1/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

function SessionColumn({
  session,
  events,
  divergenceIndex,
  label,
}: {
  session: Session
  events: AnyEvent[]
  divergenceIndex: number
  label: string
}) {
  const sid = getSessionId(session)

  return (
    <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
      <div className="px-4 py-3 border-b border-culpa-border bg-culpa-surface flex-shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] uppercase tracking-wider text-culpa-text-dim font-medium">{label}</span>
        </div>
        <Link
          to={`/session/${sid}`}
          className="text-sm font-semibold text-culpa-text hover:text-culpa-blue transition-colors truncate block"
        >
          {session.name}
        </Link>
        <div className="flex items-center gap-3 mt-1.5 text-xs text-culpa-text-dim">
          <span>{events.length} events</span>
          <span>{formatDuration(session.duration_ms)}</span>
          <span>{formatTokens(session.summary.total_input_tokens + session.summary.total_output_tokens)} tokens</span>
          <span>{formatCost(session.summary.estimated_cost_usd)}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {events.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-culpa-text-dim">
            No events in this session
          </div>
        ) : (
          <div className="py-1">
            {events.map((event, idx) => {
              const Icon = getEventIcon(event.event_type)
              const iconColor = getEventIconColor(event.event_type)
              const isDiverged = divergenceIndex >= 0 && idx >= divergenceIndex

              return (
                <div
                  key={event.event_id}
                  className={cn(
                    'flex items-start gap-2.5 px-4 py-2 hover:bg-culpa-muted/30 transition-colors',
                    isDiverged && 'border-l-2 border-culpa-orange'
                  )}
                >
                  <Icon size={14} className={cn('mt-0.5 flex-shrink-0', iconColor)} />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-culpa-text truncate">
                      {getEventDescription(event)}
                    </div>
                    <div className="text-[10px] text-culpa-text-dim font-mono mt-0.5">
                      {formatTimestamp(event.timestamp)}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export function SessionCompare() {
  const [searchParams, setSearchParams] = useSearchParams()
  const idA = searchParams.get('a') || ''
  const idB = searchParams.get('b') || ''

  const { data: sessionA, isLoading: loadingA, error: errorA } = useSession(idA || undefined)
  const { data: sessionB, isLoading: loadingB, error: errorB } = useSession(idB || undefined)
  const { data: sessionList, isLoading: loadingSessions } = useSessions({ page_size: 100 })

  const sessions = sessionList?.sessions || []

  const eventsA = sessionA?.events || []
  const eventsB = sessionB?.events || []

  const divergenceIndex = useMemo(() => {
    if (!sessionA || !sessionB) return -1
    return findDivergenceIndex(eventsA, eventsB)
  }, [sessionA, sessionB, eventsA, eventsB])

  const handleSelectB = (newId: string) => {
    const params = new URLSearchParams(searchParams)
    if (newId) {
      params.set('b', newId)
    } else {
      params.delete('b')
    }
    setSearchParams(params)
  }

  return (
    <div className="h-screen bg-culpa-bg flex flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b border-culpa-border bg-culpa-surface">
        <div className="flex items-center gap-4 px-4 py-3">
          <Link
            to={idA ? `/session/${idA}` : '/'}
            className="flex items-center gap-1.5 text-xs text-culpa-text-dim hover:text-culpa-text transition-colors"
          >
            <ArrowLeft size={14} />
            Back
          </Link>
          <div className="w-px h-4 bg-culpa-border" />
          <div className="flex items-center gap-2">
            <GitCompare size={14} className="text-culpa-text-dim" />
            <h1 className="text-sm font-semibold text-culpa-text">Session Comparison</h1>
          </div>

          {divergenceIndex >= 0 && (
            <>
              <div className="w-px h-4 bg-culpa-border" />
              <span className="text-xs text-culpa-orange">
                Divergence at event #{divergenceIndex + 1}
              </span>
            </>
          )}
          {divergenceIndex === -1 && sessionA && sessionB && (
            <>
              <div className="w-px h-4 bg-culpa-border" />
              <span className="text-xs text-culpa-green">
                No divergence detected
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col border-r border-culpa-border min-w-0">
          {!idA ? (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="text-center space-y-3">
                <p className="text-sm text-culpa-text-dim">No session selected for side A</p>
                <Link to="/" className="text-xs text-culpa-blue hover:underline">
                  Go to sessions list
                </Link>
              </div>
            </div>
          ) : loadingA ? (
            <SkeletonColumn />
          ) : errorA || !sessionA ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-2">
                <p className="text-sm text-culpa-red">Session A not found</p>
                <p className="text-xs text-culpa-text-dim font-mono">{idA}</p>
              </div>
            </div>
          ) : (
            <SessionColumn
              session={sessionA}
              events={eventsA}
              divergenceIndex={divergenceIndex}
              label="Session A"
            />
          )}
        </div>

        <div className="flex-1 flex flex-col min-w-0">
          {!idB ? (
            <div className="flex-1 flex flex-col">
              <div className="px-4 py-3 border-b border-culpa-border bg-culpa-surface flex-shrink-0">
                <span className="text-[10px] uppercase tracking-wider text-culpa-text-dim font-medium">
                  Session B
                </span>
                <p className="text-xs text-culpa-text-dim mt-1 mb-2">
                  Select a session to compare
                </p>
                <SessionPicker
                  sessions={sessions.filter((s) => s.id !== idA)}
                  isLoading={loadingSessions}
                  selectedId=""
                  onSelect={handleSelectB}
                />
              </div>
              <div className="flex-1 flex items-center justify-center">
                <p className="text-sm text-culpa-text-dim">Pick a session above to compare</p>
              </div>
            </div>
          ) : loadingB ? (
            <SkeletonColumn />
          ) : errorB || !sessionB ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center space-y-2">
                <p className="text-sm text-culpa-red">Session B not found</p>
                <p className="text-xs text-culpa-text-dim font-mono">{idB}</p>
                <button
                  onClick={() => handleSelectB('')}
                  className="text-xs text-culpa-blue hover:underline"
                >
                  Pick a different session
                </button>
              </div>
            </div>
          ) : (
            <>
              <SessionColumn
                session={sessionB}
                events={eventsB}
                divergenceIndex={divergenceIndex}
                label="Session B"
              />
              <div className="px-4 py-2 border-t border-culpa-border bg-culpa-surface flex-shrink-0">
                <SessionPicker
                  sessions={sessions.filter((s) => s.id !== idA)}
                  isLoading={loadingSessions}
                  selectedId={idB}
                  onSelect={handleSelectB}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
