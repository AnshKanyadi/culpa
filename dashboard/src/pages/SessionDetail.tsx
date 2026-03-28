import React, { useState, useCallback, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, GitCompare, Brain, Wrench, FileText, Terminal } from 'lucide-react'
import { useSession } from '../hooks/useSession'
import { useReplay } from '../hooks/useReplay'
import { useFork } from '../hooks/useFork'
import { Timeline } from '../components/Timeline'
import { EventDetail } from '../components/EventDetail'
import { SessionOverview } from '../components/SessionOverview'
import { ReplayControls } from '../components/ReplayControls'
import { ForkModal } from '../components/ForkModal'
import { SkeletonTimeline, SkeletonDetail, SkeletonOverview } from '../components/Skeleton'
import { KeyboardShortcutsHelp } from '../components/KeyboardShortcutsHelp'
import { cn, getSessionId } from '../lib/utils'
import type { AnyEvent, EventType, LLMCallEvent, FileChangeEvent } from '../lib/types'

const EVENT_TYPE_STYLES: Record<EventType, { active: string; icon: React.ReactNode }> = {
  llm_call: { active: 'text-culpa-blue bg-culpa-blue-dim', icon: <Brain size={12} /> },
  tool_call: { active: 'text-culpa-purple bg-culpa-purple-dim', icon: <Wrench size={12} /> },
  file_change: { active: 'text-culpa-green bg-culpa-green-dim', icon: <FileText size={12} /> },
  terminal_cmd: { active: 'text-culpa-orange bg-culpa-orange-dim', icon: <Terminal size={12} /> },
}

const EVENT_TYPE_KEYS: EventType[] = ['llm_call', 'tool_call', 'file_change', 'terminal_cmd']

export function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { data: session, isLoading, error } = useSession(sessionId)
  const [selectedEvent, setSelectedEvent] = useState<AnyEvent | null>(null)
  const [highlightedEventIds, setHighlightedEventIds] = useState<Set<string>>(new Set())
  const [eventTypeFilter, setEventTypeFilter] = useState<EventType | null>(null)
  const [showShortcuts, setShowShortcuts] = useState(false)

  const events = session?.events || []
  const filteredEvents = eventTypeFilter
    ? events.filter((e) => e.event_type === eventTypeFilter)
    : events

  const replay = useReplay(events)
  const fork = useFork(sessionId || '')

  const effectiveSelectedEvent = replay.isPlaying || replay.isPaused
    ? replay.currentEvent
    : selectedEvent

  const handleSelectEvent = useCallback((event: AnyEvent) => {
    setSelectedEvent(event)

    const related = new Set<string>()
    if (event.event_type === 'file_change') {
      const fileEvent = event as FileChangeEvent
      if (fileEvent.triggering_llm_call_id) {
        related.add(fileEvent.triggering_llm_call_id)
      }
    } else if (event.event_type === 'llm_call') {
      events.forEach((e) => {
        if (e.parent_event_id === event.event_id) {
          related.add(e.event_id)
        }
      })
    }
    setHighlightedEventIds(related)
  }, [events])

  const handleSelectFileEvents = useCallback((filePath: string) => {
    const fileEvents = events.filter(
      (e) => e.event_type === 'file_change' && (e as FileChangeEvent).file_path === filePath
    )
    if (fileEvents.length > 0) {
      handleSelectEvent(fileEvents[fileEvents.length - 1])
    }
  }, [events, handleSelectEvent])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return
      }

      if (fork.forkEvent) return

      switch (e.key) {
        case 'j': {
          e.preventDefault()
          const currentIdx = effectiveSelectedEvent
            ? filteredEvents.findIndex((ev) => ev.event_id === effectiveSelectedEvent.event_id)
            : -1
          const nextIdx = Math.min(currentIdx + 1, filteredEvents.length - 1)
          if (filteredEvents[nextIdx]) {
            handleSelectEvent(filteredEvents[nextIdx])
          }
          break
        }
        case 'k': {
          e.preventDefault()
          const currentIdx = effectiveSelectedEvent
            ? filteredEvents.findIndex((ev) => ev.event_id === effectiveSelectedEvent.event_id)
            : filteredEvents.length
          const prevIdx = Math.max(currentIdx - 1, 0)
          if (filteredEvents[prevIdx]) {
            handleSelectEvent(filteredEvents[prevIdx])
          }
          break
        }
        case ' ': {
          e.preventDefault()
          if (replay.isPlaying) {
            replay.pause()
          } else if (replay.isPaused) {
            replay.resume()
          } else {
            replay.play()
          }
          break
        }
        case 'f': {
          e.preventDefault()
          if (effectiveSelectedEvent && effectiveSelectedEvent.event_type === 'llm_call') {
            fork.openFork(effectiveSelectedEvent as LLMCallEvent)
          }
          break
        }
        case '1':
        case '2':
        case '3':
        case '4': {
          e.preventDefault()
          const idx = parseInt(e.key) - 1
          const type = EVENT_TYPE_KEYS[idx]
          setEventTypeFilter((prev) => (prev === type ? null : type))
          break
        }
        case 'Escape': {
          e.preventDefault()
          setSelectedEvent(null)
          setHighlightedEventIds(new Set())
          setEventTypeFilter(null)
          break
        }
        case '?': {
          e.preventDefault()
          setShowShortcuts((prev) => !prev)
          break
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [effectiveSelectedEvent, filteredEvents, handleSelectEvent, replay, fork])

  if (isLoading) {
    return (
      <div className="h-screen bg-culpa-bg flex flex-col overflow-hidden">
        <div className="flex-shrink-0 border-b border-culpa-border bg-culpa-surface">
          <div className="flex items-center gap-4 px-4 py-3">
            <div className="bg-culpa-muted animate-pulse rounded h-4 w-20" />
            <div className="w-px h-4 bg-culpa-border" />
            <div className="bg-culpa-muted animate-pulse rounded h-4 w-48" />
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="w-72 flex-shrink-0 border-r border-culpa-border bg-culpa-surface">
            <div className="px-3 py-2 border-b border-culpa-border flex items-center justify-between">
              <div className="bg-culpa-muted animate-pulse rounded h-3 w-16" />
              <div className="bg-culpa-muted animate-pulse rounded h-3 w-12" />
            </div>
            <SkeletonTimeline />
          </div>

          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="px-4 py-2 border-b border-culpa-border">
              <div className="bg-culpa-muted animate-pulse rounded h-3 w-24" />
            </div>
            <SkeletonDetail />
          </div>

          <div className="w-64 flex-shrink-0 border-l border-culpa-border bg-culpa-surface">
            <div className="px-3 py-2 border-b border-culpa-border">
              <div className="bg-culpa-muted animate-pulse rounded h-3 w-16" />
            </div>
            <SkeletonOverview />
          </div>
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-culpa-bg flex flex-col items-center justify-center gap-4">
        <div className="text-culpa-red text-sm">Session not found or expired</div>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-culpa-blue hover:underline"
        >
          <ArrowLeft size={14} />
          Back to sessions
        </Link>
      </div>
    )
  }

  const sid = getSessionId(session)

  return (
    <div className="h-screen bg-culpa-bg flex flex-col overflow-hidden">
      <div className="flex-shrink-0 border-b border-culpa-border bg-culpa-surface">
        <div className="flex items-center gap-4 px-4 py-3">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs text-culpa-text-dim hover:text-culpa-text transition-colors"
          >
            <ArrowLeft size={14} />
            Sessions
          </Link>
          <div className="w-px h-4 bg-culpa-border" />
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <h1 className="text-sm font-semibold text-culpa-text truncate">{session.name}</h1>
            <button
              onClick={() => navigate(`/compare?a=${sid}`)}
              className="flex items-center gap-1 text-xs text-culpa-text-dim hover:text-culpa-text border border-culpa-border rounded px-2 py-1 transition-colors flex-shrink-0"
            >
              <GitCompare size={12} />
              Compare
            </button>
          </div>

          <ReplayControls
            state={replay.state}
            progress={replay.progress}
            speed={replay.speed}
            eventCount={events.length}
            currentIndex={replay.currentIndex}
            onPlay={replay.play}
            onPause={replay.pause}
            onStop={replay.stop}
            onResume={replay.resume}
            onSpeedChange={replay.setSpeed}
            onSeek={replay.seekTo}
            className="w-80"
          />
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="w-72 flex-shrink-0 border-r border-culpa-border overflow-y-auto bg-culpa-surface">
          <div className="px-3 py-2 border-b border-culpa-border">
            <div className="flex items-center justify-between">
              <span className="text-xs text-culpa-text-dim uppercase tracking-wide">
                Timeline
              </span>
              <span className="text-xs text-culpa-text-dim font-mono">
                {eventTypeFilter
                  ? `${filteredEvents.length}/${events.length} events`
                  : `${events.length} events`}
              </span>
            </div>
            <div className="flex items-center gap-1 mt-2">
              {EVENT_TYPE_KEYS.map((type) => (
                <button
                  key={type}
                  onClick={() => setEventTypeFilter((prev) => (prev === type ? null : type))}
                  className={cn(
                    'p-1 rounded text-xs transition-colors',
                    eventTypeFilter === type
                      ? EVENT_TYPE_STYLES[type].active
                      : 'text-culpa-text-dim hover:text-culpa-text',
                  )}
                  title={type.replace('_', ' ')}
                >
                  {EVENT_TYPE_STYLES[type].icon}
                </button>
              ))}
            </div>
          </div>
          <Timeline
            events={filteredEvents}
            selectedEventId={effectiveSelectedEvent?.event_id}
            highlightedEventIds={highlightedEventIds}
            replayIndex={replay.currentIndex}
            onSelectEvent={handleSelectEvent}
            onForkEvent={fork.openFork}
          />
        </div>

        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="px-4 py-2 border-b border-culpa-border flex items-center gap-2 flex-shrink-0">
            <span className="text-xs text-culpa-text-dim uppercase tracking-wide">
              Event Detail
            </span>
            {effectiveSelectedEvent && (
              <>
                <span className="text-culpa-border">·</span>
                <span className="text-xs text-culpa-text-dim font-mono capitalize">
                  {effectiveSelectedEvent.event_type.replace('_', ' ')}
                </span>
                <span className="text-culpa-border">·</span>
                <span className="text-xs text-culpa-text-dim font-mono">
                  #{effectiveSelectedEvent.sequence}
                </span>
              </>
            )}
          </div>
          <EventDetail
            event={effectiveSelectedEvent}
            onFork={fork.openFork}
            className="flex-1"
          />
        </div>

        <div className="w-64 flex-shrink-0 border-l border-culpa-border overflow-y-auto bg-culpa-surface">
          <div className="px-3 py-2 border-b border-culpa-border">
            <span className="text-xs text-culpa-text-dim uppercase tracking-wide">Overview</span>
          </div>
          <SessionOverview
            session={session}
            onSelectFileEvents={handleSelectFileEvents}
          />
        </div>
      </div>

      <ForkModal
        event={fork.forkEvent}
        result={fork.forkResult}
        isForking={fork.isForking}
        error={fork.forkError}
        onClose={fork.closeFork}
        onRunFork={fork.runFork}
      />

      <KeyboardShortcutsHelp
        isOpen={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
    </div>
  )
}
