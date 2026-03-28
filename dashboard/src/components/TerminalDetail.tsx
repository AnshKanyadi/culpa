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
      <div className="flex items-center gap-3">
        <Terminal size={16} className="text-culpa-orange flex-shrink-0" />
        <div className="flex-1 min-w-0">
          {event.working_directory && (
            <div className="text-xs text-culpa-text-dim font-mono mb-0.5">
              {event.working_directory}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {event.duration_ms > 0 && (
            <span className="text-xs text-culpa-text-dim">
              {formatDuration(event.duration_ms)}
            </span>
          )}
          <div className={cn(
            'flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-mono',
            success
              ? 'text-culpa-green bg-culpa-green-dim border-culpa-green/30'
              : 'text-culpa-red bg-culpa-red-dim border-culpa-red/30',
          )}>
            {success ? <CheckCircle size={10} /> : <XCircle size={10} />}
            exit {event.exit_code}
          </div>
        </div>
      </div>

      <div>
        <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">Command</div>
        <div className="rounded-lg border border-culpa-orange/30 bg-culpa-orange-dim p-3">
          <pre className="text-sm font-mono text-culpa-orange whitespace-pre-wrap break-all">
            <span className="text-culpa-text-dim">$</span> {event.command}
          </pre>
        </div>
      </div>

      {event.stdout && (
        <div>
          <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">
            Stdout
          </div>
          <div className="rounded-lg border border-culpa-border bg-[#0d0d0f] p-3 max-h-64 overflow-auto">
            <pre className="text-xs font-mono text-culpa-text whitespace-pre-wrap leading-relaxed">
              {event.stdout}
            </pre>
          </div>
        </div>
      )}

      {event.stderr && (
        <div>
          <div className="text-xs text-culpa-red mb-1.5 uppercase tracking-wide">
            Stderr
          </div>
          <div className="rounded-lg border border-culpa-red/30 bg-culpa-red-dim p-3 max-h-48 overflow-auto">
            <pre className="text-xs font-mono text-culpa-red whitespace-pre-wrap leading-relaxed">
              {event.stderr}
            </pre>
          </div>
        </div>
      )}

      {!event.stdout && !event.stderr && (
        <div className="text-sm text-culpa-text-dim italic">No output</div>
      )}
    </div>
  )
}
