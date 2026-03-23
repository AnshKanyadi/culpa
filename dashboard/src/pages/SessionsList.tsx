/**
 * Sessions list page — the main landing page showing all recorded sessions.
 */

import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Brain,
  FileText,
  Terminal,
  AlertTriangle,
  Search,
  Filter,
  Plus,
  RefreshCw,
  Clock,
  Zap,
} from 'lucide-react'
import { useSessions } from '../hooks/useSession'
import {
  cn,
  formatRelativeTime,
  formatDuration,
  formatTokens,
  getStatusColor,
} from '../lib/utils'
import type { SessionListItem } from '../lib/types'

function SessionCard({ session }: { session: SessionListItem }) {
  const statusColor = getStatusColor(session.status)
  const s = session.summary
  const totalFilesChanged = (s?.files_created || 0) + (s?.files_modified || 0) + (s?.files_deleted || 0)
  const totalTokens = (s?.total_input_tokens || 0) + (s?.total_output_tokens || 0)
  const sessionId = session.id || ''

  return (
    <Link
      to={`/session/${sessionId}`}
      className="block group"
    >
      <div className={cn(
        'bg-prismo-surface border border-prismo-border rounded-xl p-4',
        'hover:border-prismo-blue/40 hover:bg-prismo-muted transition-all duration-200',
        'hover:shadow-lg hover:shadow-prismo-blue/5',
      )}>
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-prismo-text group-hover:text-white transition-colors line-clamp-2">
              {session.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn('text-xs font-mono', statusColor)}>
                ● {session.status}
              </span>
              <span className="text-xs text-prismo-text-dim">
                {formatRelativeTime(session.started_at)}
              </span>
              {session.duration_ms !== undefined && (
                <>
                  <span className="text-prismo-border">·</span>
                  <span className="text-xs text-prismo-text-dim flex items-center gap-1">
                    <Clock size={10} />
                    {formatDuration(session.duration_ms)}
                  </span>
                </>
              )}
            </div>
          </div>

          {s?.error_count > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-prismo-red-dim border border-prismo-red/30">
              <AlertTriangle size={10} className="text-prismo-red" />
              <span className="text-xs text-prismo-red font-mono">{s.error_count}</span>
            </div>
          )}
        </div>

        {/* Stats row */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs text-prismo-text-dim">
            <Brain size={12} className="text-prismo-blue" />
            <span>{s?.total_llm_calls || 0} calls</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-prismo-text-dim">
            <Zap size={12} className="text-prismo-text-dim" />
            <span>{formatTokens(totalTokens)} tokens</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-prismo-text-dim">
            <FileText size={12} className="text-prismo-green" />
            <span>{totalFilesChanged} files</span>
          </div>
          {(s?.terminal_commands || 0) > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-prismo-text-dim">
              <Terminal size={12} className="text-prismo-orange" />
              <span>{s.terminal_commands} cmds</span>
            </div>
          )}
        </div>

        {/* Models */}
        {s?.models_used && s.models_used.length > 0 && (
          <div className="mt-2 flex gap-1.5 flex-wrap">
            {s.models_used.map((model) => (
              <span
                key={model}
                className="text-xs font-mono text-prismo-blue/70 bg-prismo-blue-dim px-1.5 py-0.5 rounded"
              >
                {model.split('-').slice(0, 3).join('-')}
              </span>
            ))}
          </div>
        )}

        {/* Demo badge */}
        {Boolean(session.metadata?.demo) && (
          <div className="mt-2">
            <span className="text-xs text-prismo-purple font-mono bg-prismo-purple-dim px-1.5 py-0.5 rounded">
              demo
            </span>
          </div>
        )}
      </div>
    </Link>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="text-6xl mb-6">🔮</div>
      <h2 className="text-xl font-semibold text-prismo-text mb-2">No sessions yet</h2>
      <p className="text-sm text-prismo-text-dim max-w-md mb-6">
        Install the Prismo SDK and start recording your AI agent sessions to see them here.
      </p>
      <div className="bg-prismo-surface border border-prismo-border rounded-xl p-4 text-left max-w-md w-full">
        <div className="text-xs text-prismo-text-dim mb-2 uppercase tracking-wide">Quick Start</div>
        <pre className="text-xs font-mono text-prismo-blue">
          {`pip install prismo

# Generate demo data
python examples/demo_session.py --upload`}
        </pre>
      </div>
    </div>
  )
}

export function SessionsList() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [page, setPage] = useState(1)

  const { data, isLoading, error, refetch } = useSessions({
    page,
    page_size: 20,
    status,
    search: search || undefined,
  })

  return (
    <div className="min-h-screen bg-prismo-bg">
      {/* Header */}
      <div className="border-b border-prismo-border bg-prismo-surface">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🔮</div>
              <div>
                <h1 className="text-lg font-bold text-prismo-text">Prismo</h1>
                <p className="text-xs text-prismo-text-dim">AI Agent Debugger</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => refetch()}
                className="p-2 rounded-lg text-prismo-text-dim hover:text-prismo-text hover:bg-prismo-muted transition-colors"
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Search and filter bar */}
        <div className="flex items-center gap-3 mb-6">
          <div className="flex-1 relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-prismo-text-dim"
            />
            <input
              type="text"
              placeholder="Search sessions..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="w-full pl-9 pr-4 py-2 bg-prismo-surface border border-prismo-border rounded-lg
                         text-sm text-prismo-text placeholder:text-prismo-text-dim
                         focus:outline-none focus:ring-2 focus:ring-prismo-blue/30 focus:border-prismo-blue/40"
            />
          </div>

          <div className="flex items-center gap-1 p-1 bg-prismo-surface border border-prismo-border rounded-lg">
            {(['all', 'completed', 'failed', 'recording'] as const).map((s) => (
              <button
                key={s}
                onClick={() => {
                  setStatus(s === 'all' ? undefined : s)
                  setPage(1)
                }}
                className={cn(
                  'px-3 py-1 rounded text-xs font-medium capitalize transition-colors',
                  (s === 'all' ? !status : status === s)
                    ? 'bg-prismo-muted text-prismo-text'
                    : 'text-prismo-text-dim hover:text-prismo-text',
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        {isLoading && (
          <div className="flex items-center justify-center py-24">
            <div className="text-prismo-text-dim text-sm">Loading sessions...</div>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <AlertTriangle size={32} className="text-prismo-red mb-4" />
            <div className="text-sm text-prismo-red mb-2">Failed to load sessions</div>
            <div className="text-xs text-prismo-text-dim mb-4">{error.message}</div>
            <div className="text-xs text-prismo-text-dim max-w-md">
              Make sure the Prismo server is running:{' '}
              <code className="font-mono text-prismo-blue">prismo serve</code>
              {' '}or{' '}
              <code className="font-mono text-prismo-blue">cd server && uvicorn main:app</code>
            </div>
          </div>
        )}

        {!isLoading && !error && data?.sessions.length === 0 && <EmptyState />}

        {!isLoading && !error && data && data.sessions.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs text-prismo-text-dim">
                {data.total} session{data.total !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.sessions.map((session) => (
                <SessionCard key={session.id} session={session} />
              ))}
            </div>

            {/* Pagination */}
            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded-lg text-xs text-prismo-text-dim
                             border border-prismo-border hover:bg-prismo-muted transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-xs text-prismo-text-dim">
                  Page {data.page} of {data.total_pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page >= data.total_pages}
                  className="px-3 py-1.5 rounded-lg text-xs text-prismo-text-dim
                             border border-prismo-border hover:bg-prismo-muted transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
