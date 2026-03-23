/**
 * Detail view for terminal command events.
 */

import React from 'react'
import { Terminal, CheckCircle, XCircle } from 'lucide-react'
import { cn, formatDuration } from '../lib/utils'
import type { TerminalCommandEvent } from '../lib/types'

interface TerminalDetailProps {
  event: TerminalCommandEvent
}

export function TerminalDetail({ event }: TerminalDetailProps) {
  const success = event.exit_code === 0

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Terminal size={16} className="text-prismo-orange flex-shrink-0" />
        <div className="flex-1 min-w-0">
          {event.working_directory && (
            <div className="text-xs text-prismo-text-dim font-mono mb-0.5">
              {event.working_directory}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {event.duration_ms > 0 && (
            <span className="text-xs text-prismo-text-dim">
              {formatDuration(event.duration_ms)}
            </span>
          )}
          <div className={cn(
            'flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-mono',
            success
              ? 'text-prismo-green bg-prismo-green-dim border-prismo-green/30'
              : 'text-prismo-red bg-prismo-red-dim border-prismo-red/30',
          )}>
            {success ? <CheckCircle size={10} /> : <XCircle size={10} />}
            exit {event.exit_code}
          </div>
        </div>
      </div>

      {/* Command */}
      <div>
        <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">Command</div>
        <div className="rounded-lg border border-prismo-orange/30 bg-prismo-orange-dim p-3">
          <pre className="text-sm font-mono text-prismo-orange whitespace-pre-wrap break-all">
            <span className="text-prismo-text-dim">$</span> {event.command}
          </pre>
        </div>
      </div>

      {/* Stdout */}
      {event.stdout && (
        <div>
          <div className="text-xs text-prismo-text-dim mb-1.5 uppercase tracking-wide">
            Stdout
          </div>
          <div className="rounded-lg border border-prismo-border bg-[#0d0d0f] p-3 max-h-64 overflow-auto">
            <pre className="text-xs font-mono text-prismo-text whitespace-pre-wrap leading-relaxed">
              {event.stdout}
            </pre>
          </div>
        </div>
      )}

      {/* Stderr */}
      {event.stderr && (
        <div>
          <div className="text-xs text-prismo-red mb-1.5 uppercase tracking-wide">
            Stderr
          </div>
          <div className="rounded-lg border border-prismo-red/30 bg-prismo-red-dim p-3 max-h-48 overflow-auto">
            <pre className="text-xs font-mono text-prismo-red whitespace-pre-wrap leading-relaxed">
              {event.stderr}
            </pre>
          </div>
        </div>
      )}

      {!event.stdout && !event.stderr && (
        <div className="text-sm text-prismo-text-dim italic">No output</div>
      )}
    </div>
  )
}
