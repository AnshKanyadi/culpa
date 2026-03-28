import React, { useState } from 'react'
import {
  Brain,
  FileText,
  Terminal,
  AlertTriangle,
  DollarSign,
  ChevronRight,
} from 'lucide-react'
import { cn, formatDuration, formatTokens, formatCost, formatDate, getStatusColor } from '../lib/utils'
import type { Session, AnyEvent, FileChangeEvent } from '../lib/types'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
  subValue?: string
  color?: string
}

function StatCard({ icon, label, value, subValue, color }: StatCardProps) {
  return (
    <div className="bg-culpa-surface border border-culpa-border rounded-lg p-3">
      <div className={cn('flex items-center gap-2 mb-1', color || 'text-culpa-text-dim')}>
        {icon}
        <span className="text-xs uppercase tracking-wide">{label}</span>
      </div>
      <div className="text-lg font-mono font-medium text-culpa-text">{value}</div>
      {subValue && <div className="text-xs text-culpa-text-dim mt-0.5">{subValue}</div>}
    </div>
  )
}

interface FileTreeProps {
  filePaths: string[]
  events: AnyEvent[]
  onSelectFile: (path: string) => void
}

function FileTree({ filePaths, events, onSelectFile }: FileTreeProps) {
  if (filePaths.length === 0) return null

  const fileEventCounts = filePaths.reduce<Record<string, number>>((acc, path) => {
    acc[path] = events.filter(
      (e) => e.event_type === 'file_change' && (e as FileChangeEvent).file_path === path
    ).length
    return acc
  }, {})

  return (
    <div className="space-y-1">
      {filePaths.map((path) => {
        const parts = path.split('/')
        const filename = parts[parts.length - 1]
        const dir = parts.slice(0, -1).join('/')
        const count = fileEventCounts[path] || 0

        return (
          <button
            key={path}
            onClick={() => onSelectFile(path)}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-culpa-muted transition-colors text-left group"
          >
            <FileText size={12} className="text-culpa-green flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-mono text-culpa-text truncate">{filename}</div>
              {dir && (
                <div className="text-xs text-culpa-text-dim truncate">{dir}/</div>
              )}
            </div>
            {count > 0 && (
              <span className="text-xs text-culpa-text-dim bg-culpa-muted px-1.5 py-0.5 rounded font-mono">
                {count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}

interface SessionOverviewProps {
  session: Session
  onSelectFileEvents: (path: string) => void
  className?: string
}

export function SessionOverview({ session, onSelectFileEvents, className }: SessionOverviewProps) {
  const [filesExpanded, setFilesExpanded] = useState(true)
  const s = session.summary
  const statusColor = getStatusColor(session.status)

  const totalTokens = (s.total_input_tokens || 0) + (s.total_output_tokens || 0)
  const totalFilesChanged = (s.files_created || 0) + (s.files_modified || 0) + (s.files_deleted || 0)

  return (
    <div className={cn('p-4 space-y-4 overflow-auto', className)}>
      <div>
        <h2 className="text-sm font-semibold text-culpa-text mb-1 line-clamp-2">
          {session.name}
        </h2>
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-mono', statusColor)}>
            ● {session.status}
          </span>
          {session.started_at && (
            <span className="text-xs text-culpa-text-dim">
              {formatDate(session.started_at)}
            </span>
          )}
        </div>
        {session.duration_ms !== undefined && (
          <div className="text-xs text-culpa-text-dim mt-0.5">
            Duration: {formatDuration(session.duration_ms)}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <StatCard
          icon={<Brain size={12} />}
          label="LLM Calls"
          value={s.total_llm_calls || 0}
          color="text-culpa-blue"
        />
        <StatCard
          icon={<FileText size={12} />}
          label="Tokens"
          value={formatTokens(totalTokens)}
          subValue={`↑${formatTokens(s.total_input_tokens || 0)} ↓${formatTokens(s.total_output_tokens || 0)}`}
          color="text-culpa-text-dim"
        />
        <StatCard
          icon={<DollarSign size={12} />}
          label="Est. Cost"
          value={formatCost(s.estimated_cost_usd || 0)}
          color="text-culpa-text-dim"
        />
        <StatCard
          icon={<AlertTriangle size={12} />}
          label="Errors"
          value={s.error_count || 0}
          color={s.error_count ? 'text-culpa-red' : 'text-culpa-text-dim'}
        />
        <StatCard
          icon={<FileText size={12} />}
          label="Files Changed"
          value={totalFilesChanged}
          subValue={`+${s.files_created || 0} ~${s.files_modified || 0} -${s.files_deleted || 0}`}
          color="text-culpa-green"
        />
        <StatCard
          icon={<Terminal size={12} />}
          label="Commands"
          value={s.terminal_commands || 0}
          color="text-culpa-orange"
        />
      </div>

      {s.models_used && s.models_used.length > 0 && (
        <div>
          <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">Models</div>
          <div className="space-y-1">
            {s.models_used.map((model) => (
              <div key={model} className="text-xs font-mono text-culpa-blue bg-culpa-blue-dim px-2 py-1 rounded">
                {model}
              </div>
            ))}
          </div>
        </div>
      )}

      {s.files_touched && s.files_touched.length > 0 && (
        <div>
          <button
            className="w-full flex items-center justify-between text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide hover:text-culpa-text transition-colors"
            onClick={() => setFilesExpanded(!filesExpanded)}
          >
            <span>Files Touched ({s.files_touched.length})</span>
            <ChevronRight
              size={12}
              className={cn('transition-transform', filesExpanded && 'rotate-90')}
            />
          </button>
          {filesExpanded && (
            <FileTree
              filePaths={s.files_touched}
              events={session.events || []}
              onSelectFile={onSelectFileEvents}
            />
          )}
        </div>
      )}

      {session.metadata && Object.keys(session.metadata).length > 0 && (
        <div>
          <div className="text-xs text-culpa-text-dim mb-1.5 uppercase tracking-wide">Metadata</div>
          <div className="space-y-1">
            {Object.entries(session.metadata).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-culpa-text-dim font-mono">{key}</span>
                <span className="text-culpa-text font-mono truncate ml-2">
                  {String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
