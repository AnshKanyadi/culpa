/**
 * Replay mode controls — play/pause/speed/progress bar.
 */

import React from 'react'
import { Play, Pause, Square, SkipBack, SkipForward, Zap } from 'lucide-react'
import { cn } from '../lib/utils'
import type { ReplayState } from '../hooks/useReplay'

interface ReplayControlsProps {
  state: ReplayState
  progress: number
  speed: number
  eventCount: number
  currentIndex: number
  onPlay: () => void
  onPause: () => void
  onStop: () => void
  onResume: () => void
  onSpeedChange: (speed: number) => void
  onSeek: (index: number) => void
  className?: string
}

const SPEEDS = [0.5, 1, 2, 5, 10]

export function ReplayControls({
  state,
  progress,
  speed,
  eventCount,
  currentIndex,
  onPlay,
  onPause,
  onStop,
  onResume,
  onSpeedChange,
  onSeek,
  className,
}: ReplayControlsProps) {
  const isIdle = state === 'idle'
  const isPlaying = state === 'playing'
  const isPaused = state === 'paused'

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Progress bar */}
      {!isIdle && (
        <div className="relative">
          <div className="h-1 bg-prismo-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-prismo-blue rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          {/* Clickable progress track */}
          <input
            type="range"
            min={0}
            max={Math.max(0, eventCount - 1)}
            value={Math.max(0, currentIndex)}
            onChange={(e) => onSeek(Number(e.target.value))}
            className="absolute inset-0 w-full opacity-0 cursor-pointer"
          />
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-2">
        {/* Main control */}
        {isIdle && (
          <button
            onClick={onPlay}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-prismo-blue text-white text-xs font-medium
                       hover:bg-prismo-blue/80 transition-colors"
          >
            <Play size={12} fill="currentColor" />
            Replay
          </button>
        )}

        {isPlaying && (
          <button
            onClick={onPause}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-prismo-muted border border-prismo-border text-prismo-text text-xs font-medium
                       hover:bg-prismo-border transition-colors"
          >
            <Pause size={12} />
            Pause
          </button>
        )}

        {isPaused && (
          <button
            onClick={onResume}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                       bg-prismo-blue text-white text-xs font-medium
                       hover:bg-prismo-blue/80 transition-colors"
          >
            <Play size={12} fill="currentColor" />
            Resume
          </button>
        )}

        {/* Skip buttons */}
        {!isIdle && (
          <>
            <button
              onClick={() => onSeek(Math.max(0, currentIndex - 1))}
              className="p-1.5 rounded text-prismo-text-dim hover:text-prismo-text hover:bg-prismo-muted transition-colors"
            >
              <SkipBack size={14} />
            </button>
            <button
              onClick={() => onSeek(Math.min(eventCount - 1, currentIndex + 1))}
              className="p-1.5 rounded text-prismo-text-dim hover:text-prismo-text hover:bg-prismo-muted transition-colors"
            >
              <SkipForward size={14} />
            </button>
            <button
              onClick={onStop}
              className="p-1.5 rounded text-prismo-text-dim hover:text-prismo-red hover:bg-prismo-red-dim transition-colors"
            >
              <Square size={14} />
            </button>
          </>
        )}

        {/* Speed selector */}
        <div className="flex items-center gap-1 ml-auto">
          <Zap size={12} className="text-prismo-text-dim" />
          <div className="flex gap-0.5">
            {SPEEDS.map((s) => (
              <button
                key={s}
                onClick={() => onSpeedChange(s)}
                className={cn(
                  'px-1.5 py-0.5 rounded text-xs font-mono transition-colors',
                  speed === s
                    ? 'bg-prismo-blue text-white'
                    : 'text-prismo-text-dim hover:text-prismo-text hover:bg-prismo-muted',
                )}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* Position indicator */}
        {!isIdle && (
          <span className="text-xs text-prismo-text-dim font-mono ml-2">
            {currentIndex + 1}/{eventCount}
          </span>
        )}
      </div>
    </div>
  )
}
