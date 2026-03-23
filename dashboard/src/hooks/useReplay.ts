/**
 * Hook for managing replay mode in the session detail view.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import type { AnyEvent } from '../lib/types'

export type ReplayState = 'idle' | 'playing' | 'paused'

export function useReplay(events: AnyEvent[]) {
  const [state, setState] = useState<ReplayState>('idle')
  const [currentIndex, setCurrentIndex] = useState(-1)
  const [speed, setSpeed] = useState(1.0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const indexRef = useRef(currentIndex)

  useEffect(() => {
    indexRef.current = currentIndex
  }, [currentIndex])

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const scheduleNext = useCallback(
    (fromIndex: number) => {
      if (fromIndex >= events.length - 1) {
        setState('idle')
        return
      }

      const current = events[fromIndex]
      const next = events[fromIndex + 1]

      // Calculate delay based on timestamps
      let delay = 500 // default 500ms between events
      if (current && next) {
        const curr = new Date(current.timestamp).getTime()
        const nxt = new Date(next.timestamp).getTime()
        const diff = nxt - curr
        if (diff > 0 && diff < 30000) {
          delay = diff / speed
        } else {
          delay = 300 / speed
        }
      }

      timerRef.current = setTimeout(() => {
        const nextIndex = indexRef.current + 1
        if (nextIndex < events.length) {
          setCurrentIndex(nextIndex)
          scheduleNext(nextIndex)
        } else {
          setState('idle')
        }
      }, delay)
    },
    [events, speed]
  )

  const play = useCallback(() => {
    setState('playing')
    const startFrom = currentIndex < 0 ? 0 : currentIndex
    setCurrentIndex(startFrom)
    scheduleNext(startFrom)
  }, [currentIndex, scheduleNext])

  const pause = useCallback(() => {
    setState('paused')
    clearTimer()
  }, [clearTimer])

  const stop = useCallback(() => {
    setState('idle')
    setCurrentIndex(-1)
    clearTimer()
  }, [clearTimer])

  const seekTo = useCallback(
    (index: number) => {
      clearTimer()
      setCurrentIndex(index)
      if (state === 'playing') {
        scheduleNext(index)
      }
    },
    [clearTimer, state, scheduleNext]
  )

  const resume = useCallback(() => {
    setState('playing')
    scheduleNext(currentIndex)
  }, [currentIndex, scheduleNext])

  // Cleanup on unmount
  useEffect(() => {
    return clearTimer
  }, [clearTimer])

  const progress = events.length > 0 ? ((currentIndex + 1) / events.length) * 100 : 0
  const currentEvent = currentIndex >= 0 ? events[currentIndex] : null
  const isPlaying = state === 'playing'
  const isPaused = state === 'paused'

  return {
    state,
    currentIndex,
    currentEvent,
    progress,
    speed,
    isPlaying,
    isPaused,
    setSpeed,
    play,
    pause,
    stop,
    resume,
    seekTo,
  }
}
