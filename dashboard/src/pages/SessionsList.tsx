import React, { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Brain,
  FileText,
  Terminal,
  AlertTriangle,
  Search,
  RefreshCw,
  Clock,
  Zap,
  Key,
  LogOut,
  User,
  Users,
  CreditCard,
  ChevronDown,
  ArrowUpRight,
} from 'lucide-react'
import { useSessions } from '../hooks/useSession'
import { SkeletonCard } from '../components/Skeleton'
import { Logo } from '../components/Logo'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api/client'
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
        'bg-culpa-surface border border-culpa-border rounded-xl p-4',
        'hover:border-culpa-blue/40 hover:bg-culpa-muted transition-all duration-200',
        'hover:shadow-lg hover:shadow-culpa-blue/5',
      )}>
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-culpa-text group-hover:text-white transition-colors line-clamp-2">
              {session.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn('text-xs font-mono', statusColor)}>
                ● {session.status}
              </span>
              <span className="text-xs text-culpa-text-dim">
                {formatRelativeTime(session.started_at)}
              </span>
              {session.duration_ms !== undefined && (
                <>
                  <span className="text-culpa-border">·</span>
                  <span className="text-xs text-culpa-text-dim flex items-center gap-1">
                    <Clock size={10} />
                    {formatDuration(session.duration_ms)}
                  </span>
                </>
              )}
            </div>
          </div>

          {s?.error_count > 0 && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-culpa-red-dim border border-culpa-red/30">
              <AlertTriangle size={10} className="text-culpa-red" />
              <span className="text-xs text-culpa-red font-mono">{s.error_count}</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-xs text-culpa-text-dim">
            <Brain size={12} className="text-culpa-blue" />
            <span>{s?.total_llm_calls || 0} calls</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-culpa-text-dim">
            <Zap size={12} className="text-culpa-text-dim" />
            <span>{formatTokens(totalTokens)} tokens</span>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-culpa-text-dim">
            <FileText size={12} className="text-culpa-green" />
            <span>{totalFilesChanged} files</span>
          </div>
          {(s?.terminal_commands || 0) > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-culpa-text-dim">
              <Terminal size={12} className="text-culpa-orange" />
              <span>{s.terminal_commands} cmds</span>
            </div>
          )}
        </div>

        {s?.models_used && s.models_used.length > 0 && (
          <div className="mt-2 flex gap-1.5 flex-wrap">
            {s.models_used.map((model) => (
              <span
                key={model}
                className="text-xs font-mono text-culpa-blue/70 bg-culpa-blue-dim px-1.5 py-0.5 rounded"
              >
                {model.split('-').slice(0, 3).join('-')}
              </span>
            ))}
          </div>
        )}

        <div className="mt-2 flex gap-1.5 flex-wrap">
          {Boolean(session.metadata?.demo) && (
            <span className="text-xs text-culpa-purple font-mono bg-culpa-purple-dim px-1.5 py-0.5 rounded">
              demo
            </span>
          )}
          {session.expires_at && (() => {
            const hoursLeft = (new Date(session.expires_at).getTime() - Date.now()) / (1000 * 60 * 60)
            if (hoursLeft < 48 && hoursLeft > 0) {
              return (
                <span className="text-xs text-culpa-orange font-mono bg-culpa-orange-dim px-1.5 py-0.5 rounded">
                  expires in {hoursLeft < 24 ? `${Math.round(hoursLeft)}h` : `${Math.round(hoursLeft / 24)}d`}
                </span>
              )
            }
            return null
          })()}
        </div>
      </div>
    </Link>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <img src="/culpa-logo.svg" alt="Culpa" className="h-16 w-16 mb-6 mx-auto" />
      <h2 className="text-xl font-semibold text-culpa-text mb-2">No sessions yet</h2>
      <p className="text-sm text-culpa-text-dim max-w-md mb-6">
        Install the Culpa SDK and start recording your AI agent sessions to see them here.
      </p>
      <div className="bg-culpa-surface border border-culpa-border rounded-xl p-4 text-left max-w-md w-full">
        <div className="text-xs text-culpa-text-dim mb-2 uppercase tracking-wide">Quick Start</div>
        <pre className="text-xs font-mono text-culpa-blue">
          {`pip install culpa

# Generate demo data
python examples/demo_session.py --upload`}
        </pre>
      </div>
    </div>
  )
}

function ProfileDropdown({ user, onLogout }: { user: any; onLogout: () => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const items = [
    { to: '/settings/keys', icon: <Key size={14} />, label: 'API Keys' },
    { to: '/settings/billing', icon: <CreditCard size={14} />, label: 'Billing' },
    { to: '/settings/team', icon: <Users size={14} />, label: 'Team' },
  ]

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-culpa-text-dim
                   hover:text-culpa-text hover:bg-culpa-muted transition-colors"
      >
        <User size={14} />
        <span className="hidden sm:inline text-xs">{user?.email}</span>
        <ChevronDown size={12} className={cn('transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-52 bg-culpa-surface border border-culpa-border rounded-xl
                        shadow-xl shadow-black/30 py-1.5 z-50 animate-fade-in">
          <div className="px-3 py-2 border-b border-culpa-border mb-1">
            <div className="text-xs font-medium text-culpa-text truncate">{user?.name || user?.email}</div>
            {user?.name && <div className="text-[11px] text-culpa-text-dim truncate">{user?.email}</div>}
            <div className="mt-1">
              <span className={cn(
                'text-[10px] font-mono px-1.5 py-0.5 rounded',
                user?.plan === 'pro' ? 'bg-culpa-green/15 text-culpa-green' : 'bg-culpa-muted text-culpa-text-dim',
              )}>
                {user?.plan === 'pro' ? 'Pro' : 'Free'}
              </span>
            </div>
          </div>
          {items.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-3 py-2 text-xs text-culpa-text-dim
                         hover:text-culpa-text hover:bg-culpa-muted transition-colors"
            >
              {item.icon} {item.label}
            </Link>
          ))}
          <div className="border-t border-culpa-border mt-1 pt-1">
            <button
              onClick={() => { setOpen(false); onLogout() }}
              className="flex items-center gap-2.5 px-3 py-2 text-xs text-culpa-text-dim
                         hover:text-culpa-red w-full text-left transition-colors"
            >
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function SessionsList() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const { user, logout } = useAuth()

  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: () => api.auth.usage(),
  })

  const { data, isLoading, error, refetch } = useSessions({
    page,
    page_size: 20,
    status,
    search: search || undefined,
  })

  return (
    <div className="min-h-screen bg-culpa-bg">
      <div className="border-b border-culpa-border bg-culpa-surface">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Logo size="lg" linkTo="/" />

            <div className="flex items-center gap-2">
              <button
                onClick={() => refetch()}
                className="p-2 rounded-lg text-culpa-text-dim hover:text-culpa-text hover:bg-culpa-muted transition-colors"
                title="Refresh"
              >
                <RefreshCw size={16} />
              </button>
              <ProfileDropdown user={user} onLogout={logout} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {usage?.at_limit && user?.plan === 'free' && (
          <div className="mb-6 bg-culpa-orange-dim border border-culpa-orange/30 rounded-xl px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertTriangle size={16} className="text-culpa-orange shrink-0" />
              <div>
                <p className="text-sm font-medium text-culpa-text">
                  You've reached the free tier limit ({usage.session_count}/{usage.session_limit} sessions).
                </p>
                <p className="text-xs text-culpa-text-dim mt-0.5">
                  Upgrade to Pro for unlimited sessions and 90-day retention.
                </p>
              </div>
            </div>
            <Link
              to="/settings/billing"
              className="flex items-center gap-1 px-3 py-1.5 bg-culpa-orange text-black text-xs font-semibold
                         rounded-lg hover:bg-culpa-orange/80 transition-colors whitespace-nowrap shrink-0"
            >
              Upgrade to Pro <ArrowUpRight size={12} />
            </Link>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-6">
          <div className="flex-1 relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-culpa-text-dim"
            />
            <input
              type="text"
              placeholder="Search sessions..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              className="w-full pl-9 pr-16 py-2 bg-culpa-surface border border-culpa-border rounded-lg
                         text-sm text-culpa-text placeholder:text-culpa-text-dim
                         focus:outline-none focus:ring-2 focus:ring-culpa-blue/30 focus:border-culpa-blue/40"
            />
            <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline-flex text-[10px] text-culpa-text-dim
                            bg-culpa-muted border border-culpa-border px-1.5 py-0.5 rounded font-mono">
              Cmd+K
            </kbd>
          </div>

          <div className="flex items-center gap-1 p-1 bg-culpa-surface border border-culpa-border rounded-lg">
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
                    ? 'bg-culpa-muted text-culpa-text'
                    : 'text-culpa-text-dim hover:text-culpa-text',
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <AlertTriangle size={32} className="text-culpa-red mb-4" />
            <div className="text-sm text-culpa-red mb-2">Failed to load sessions</div>
            <div className="text-xs text-culpa-text-dim mb-4">{error.message}</div>
            <div className="text-xs text-culpa-text-dim max-w-md">
              Make sure the Culpa server is running:{' '}
              <code className="font-mono text-culpa-blue">culpa serve</code>
              {' '}or{' '}
              <code className="font-mono text-culpa-blue">cd server && uvicorn main:app</code>
            </div>
          </div>
        )}

        {!isLoading && !error && data?.sessions.length === 0 && <EmptyState />}

        {!isLoading && !error && data && data.sessions.length > 0 && (
          <>
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs text-culpa-text-dim">
                {data.total} session{data.total !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.sessions.map((session) => (
                <SessionCard key={session.id} session={session} />
              ))}
            </div>

            {data.total_pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded-lg text-xs text-culpa-text-dim
                             border border-culpa-border hover:bg-culpa-muted transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-xs text-culpa-text-dim">
                  Page {data.page} of {data.total_pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page >= data.total_pages}
                  className="px-3 py-1.5 rounded-lg text-xs text-culpa-text-dim
                             border border-culpa-border hover:bg-culpa-muted transition-colors
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
