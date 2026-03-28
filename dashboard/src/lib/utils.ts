import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format, parseISO } from 'date-fns'
import type { AnyEvent, EventType, SessionStatus } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), 'MMM d, yyyy HH:mm')
  } catch {
    return dateStr
  }
}

export function formatRelativeTime(dateStr: string): string {
  try {
    return formatDistanceToNow(parseISO(dateStr), { addSuffix: true })
  } catch {
    return dateStr
  }
}

export function formatDuration(ms: number | undefined): string {
  if (ms === undefined || ms === null) return '—'
  if (ms < 1000) return `${Math.round(ms)}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const mins = Math.floor(ms / 60000)
  const secs = Math.floor((ms % 60000) / 1000)
  return `${mins}m ${secs}s`
}

export function formatTokens(count: number): string {
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`
  return String(count)
}

export function formatCost(usd: number): string {
  if (usd < 0.01) return `<$0.01`
  return `$${usd.toFixed(3)}`
}

export function formatTimestamp(ts: string): string {
  try {
    return format(parseISO(ts), 'HH:mm:ss.SSS')
  } catch {
    return ts
  }
}

export function getEventColor(eventType: EventType): string {
  switch (eventType) {
    case 'llm_call': return 'culpa-blue'
    case 'tool_call': return 'culpa-purple'
    case 'file_change': return 'culpa-green'
    case 'terminal_cmd': return 'culpa-orange'
    default: return 'culpa-text-dim'
  }
}

export function getEventBg(eventType: EventType): string {
  switch (eventType) {
    case 'llm_call': return 'bg-culpa-blue-dim'
    case 'tool_call': return 'bg-culpa-purple-dim'
    case 'file_change': return 'bg-culpa-green-dim'
    case 'terminal_cmd': return 'bg-culpa-orange-dim'
    default: return 'bg-culpa-muted'
  }
}

export function getStatusColor(status: SessionStatus): string {
  switch (status) {
    case 'completed': return 'text-culpa-green'
    case 'failed': return 'text-culpa-red'
    case 'recording': return 'text-culpa-orange'
    default: return 'text-culpa-text-dim'
  }
}

export function getEventDescription(event: AnyEvent): string {
  switch (event.event_type) {
    case 'llm_call': {
      const total = (event.token_usage?.input_tokens || 0) + (event.token_usage?.output_tokens || 0)
      return `Called ${event.model.split('-').slice(0, 3).join('-')} · ${total.toLocaleString()} tokens`
    }
    case 'tool_call':
      return `Tool: ${event.tool_name}`
    case 'file_change':
      return `${event.operation.charAt(0).toUpperCase() + event.operation.slice(1)} ${event.file_path}`
    case 'terminal_cmd': {
      const cmd = event.command.length > 50 ? event.command.slice(0, 50) + '…' : event.command
      return `$ ${cmd}`
    }
    default:
      return 'Unknown event'
  }
}

export function eventHadError(event: AnyEvent): boolean {
  switch (event.event_type) {
    case 'llm_call': return event.stop_reason === 'error'
    case 'tool_call': return !!event.error
    case 'file_change': return false
    case 'terminal_cmd': return event.exit_code !== 0
    default: return false
  }
}

export function getSessionId(session: { session_id?: string; id?: string }): string {
  return session.session_id || session.id || ''
}
