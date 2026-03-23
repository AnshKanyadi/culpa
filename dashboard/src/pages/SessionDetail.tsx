/**
 * Session detail page — the main event of the Prismo dashboard.
 * Three-panel layout: Timeline | Event Detail | Session Overview
 */

import React, { useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ChevronLeft } from 'lucide-react'
import { useSession } from '../hooks/useSession'
import { useReplay } from '../hooks/useReplay'
import { useFork } from '../hooks/useFork'
import { Timeline } from '../components/Timeline'
import { EventDetail } from '../components/EventDetail'
import { SessionOverview } from '../components/SessionOverview'
import { ReplayControls } from '../components/ReplayControls'
import { ForkModal } from '../components/ForkModal'
import { cn, getSessionId } from '../lib/utils'
import type { AnyEvent, LLMCallEvent, FileChangeEvent } from '../lib/types'

export function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const { data: session, isLoading, error } = useSession(sessionId)
  const [selectedEvent, setSelectedEvent] = useState<AnyEvent | null>(null)
  const [highlightedEventIds, setHighlightedEventIds] = useState<Set<string>>(new Set())

  const events = session?.events || []
  const replay = useReplay(events)
  const fork = useFork(sessionId || '')

  // During replay, auto-select the current event
  const effectiveSelectedEvent = replay.isPlaying || replay.isPaused
    ? replay.currentEvent
    : selectedEvent

  const handleSelectEvent = useCallback((event: AnyEvent) => {
    setSelectedEvent(event)

    // Highlight related events
    const related = new Set<string>()
    if (event.event_type === 'file_change') {
      const fileEvent = event as FileChangeEvent
      if (fileEvent.triggering_llm_call_id) {
        related.add(fileEvent.triggering_llm_call_id)
      }
    } else if (event.event_type === 'llm_call') {
      // Highlight child events
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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-prismo-bg flex items-center justify-center">
        <div className="text-prismo-text-dim">Loading session...</div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-prismo-bg flex flex-col items-center justify-center gap-4">
        <div className="text-prismo-red">Session not found</div>
        <Link to="/" className="text-sm text-prismo-blue hover:underline">
          ← Back to sessions
        </Link>
      </div>
    )
  }

  const sid = getSessionId(session)

  return (
    <div className="h-screen bg-prismo-bg flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex-shrink-0 border-b border-prismo-border bg-prismo-surface">
        <div className="flex items-center gap-4 px-4 py-3">
          <Link
            to="/"
            className="flex items-center gap-1.5 text-xs text-prismo-text-dim hover:text-prismo-text transition-colors"
          >
            <ArrowLeft size={14} />
            Sessions
          </Link>
          <div className="w-px h-4 bg-prismo-border" />
          <div className="flex-1 min-w-0">
            <h1 className="text-sm font-semibold text-prismo-text truncate">{session.name}</h1>
          </div>

          {/* Replay controls in the top bar */}
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

      {/* Three-panel layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT — Timeline */}
        <div className="w-72 flex-shrink-0 border-r border-prismo-border overflow-y-auto bg-prismo-surface">
          <div className="px-3 py-2 border-b border-prismo-border flex items-center justify-between">
            <span className="text-xs text-prismo-text-dim uppercase tracking-wide">
              Timeline
            </span>
            <span className="text-xs text-prismo-text-dim font-mono">
              {events.length} events
            </span>
          </div>
          <Timeline
            events={events}
            selectedEventId={effectiveSelectedEvent?.event_id}
            highlightedEventIds={highlightedEventIds}
            replayIndex={replay.currentIndex}
            onSelectEvent={handleSelectEvent}
            onForkEvent={fork.openFork}
          />
        </div>

        {/* CENTER — Event Detail */}
        <div className="flex-1 overflow-hidden flex flex-col">
          <div className="px-4 py-2 border-b border-prismo-border flex items-center gap-2 flex-shrink-0">
            <span className="text-xs text-prismo-text-dim uppercase tracking-wide">
              Event Detail
            </span>
            {effectiveSelectedEvent && (
              <>
                <span className="text-prismo-border">·</span>
                <span className="text-xs text-prismo-text-dim font-mono capitalize">
                  {effectiveSelectedEvent.event_type.replace('_', ' ')}
                </span>
                <span className="text-prismo-border">·</span>
                <span className="text-xs text-prismo-text-dim font-mono">
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

        {/* RIGHT — Session Overview */}
        <div className="w-64 flex-shrink-0 border-l border-prismo-border overflow-y-auto bg-prismo-surface">
          <div className="px-3 py-2 border-b border-prismo-border">
            <span className="text-xs text-prismo-text-dim uppercase tracking-wide">Overview</span>
          </div>
          <SessionOverview
            session={session}
            onSelectFileEvents={handleSelectFileEvents}
          />
        </div>
      </div>

      {/* Fork Modal */}
      <ForkModal
        event={fork.forkEvent}
        result={fork.forkResult}
        isForking={fork.isForking}
        error={fork.forkError}
        onClose={fork.closeFork}
        onRunFork={fork.runFork}
      />
    </div>
  )
}
