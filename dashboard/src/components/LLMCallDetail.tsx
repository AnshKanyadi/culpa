/**
 * Detail view for LLM call events.
 * Shows the full prompt, response, token usage, and tool calls.
 */

import React, { useState } from 'react'
import { GitFork, ChevronDown, ChevronRight, Clock, Zap } from 'lucide-react'
import { cn, formatDuration } from '../lib/utils'
import type { LLMCallEvent, Message, ToolCallRecord } from '../lib/types'

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'
  const isAssistant = message.role === 'assistant'
  const isToolResult = message.role === 'tool'

  const content = typeof message.content === 'string'
    ? message.content
    : JSON.stringify(message.content, null, 2)

  if (isSystem) {
    return (
      <div className="rounded-lg border border-prismo-border bg-prismo-muted/40 p-3">
        <div className="text-xs text-prismo-text-dim mb-1.5 font-mono uppercase tracking-wide">
          System
        </div>
        <pre className="text-xs text-prismo-text font-mono whitespace-pre-wrap leading-relaxed">
          {content}
        </pre>
      </div>
    )
  }

  return (
    <div className={cn(
      'flex',
      isUser || isToolResult ? 'justify-start' : 'justify-end',
    )}>
      <div className={cn(
        'max-w-[85%] rounded-lg p-3',
        isUser ? 'bg-prismo-muted border border-prismo-border' : '',
        isAssistant ? 'bg-prismo-blue-dim border border-prismo-blue/30' : '',
        isToolResult ? 'bg-prismo-purple-dim border border-prismo-purple/30 w-full max-w-full' : '',
      )}>
        <div className={cn(
          'text-xs mb-1.5 font-mono uppercase tracking-wide',
          isUser ? 'text-prismo-text-dim' : '',
          isAssistant ? 'text-prismo-blue' : '',
          isToolResult ? 'text-prismo-purple' : '',
        )}>
          {message.role}
          {message.tool_call_id && (
            <span className="ml-2 text-prismo-text-dim normal-case">
              #{message.tool_call_id.slice(-6)}
            </span>
          )}
        </div>
        <pre className="text-xs text-prismo-text font-mono whitespace-pre-wrap leading-relaxed break-all">
          {content.length > 2000 ? content.slice(0, 2000) + '\n…[truncated]' : content}
        </pre>
      </div>
    </div>
  )
}

function ToolCallCard({ tc }: { tc: ToolCallRecord }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="rounded-lg border border-prismo-purple/30 bg-prismo-purple-dim">
      <button
        className="w-full flex items-center justify-between p-3 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown size={14} className="text-prismo-purple" />
          ) : (
            <ChevronRight size={14} className="text-prismo-purple" />
          )}
          <span className="text-sm font-mono text-prismo-purple">{tc.tool_name}</span>
          <span className="text-xs text-prismo-text-dim">#{tc.tool_call_id.slice(-6)}</span>
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          <div>
            <div className="text-xs text-prismo-text-dim mb-1">Input</div>
            <pre className="text-xs font-mono text-prismo-text bg-prismo-surface rounded p-2 overflow-auto max-h-32">
              {JSON.stringify(tc.input_arguments, null, 2)}
            </pre>
          </div>
          {tc.output_result !== undefined && (
            <div>
              <div className="text-xs text-prismo-text-dim mb-1">Output</div>
              <pre className="text-xs font-mono text-prismo-text bg-prismo-surface rounded p-2 overflow-auto max-h-32">
                {typeof tc.output_result === 'string'
                  ? tc.output_result
                  : JSON.stringify(tc.output_result, null, 2)}
              </pre>
            </div>
          )}
          {tc.error && (
            <div className="text-xs text-prismo-red font-mono bg-prismo-red-dim rounded p-2">
              Error: {tc.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface LLMCallDetailProps {
  event: LLMCallEvent
  onFork: () => void
}

export function LLMCallDetail({ event, onFork }: LLMCallDetailProps) {
  const [showRaw, setShowRaw] = useState(false)
  const totalTokens = (event.token_usage?.input_tokens || 0) + (event.token_usage?.output_tokens || 0)

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-prismo-surface border border-prismo-border rounded-lg p-3">
          <div className="text-xs text-prismo-text-dim mb-1">Model</div>
          <div className="text-sm font-mono text-prismo-blue truncate" title={event.model}>
            {event.model}
          </div>
        </div>
        <div className="bg-prismo-surface border border-prismo-border rounded-lg p-3">
          <div className="text-xs text-prismo-text-dim mb-1">Tokens</div>
          <div className="text-sm font-mono text-prismo-text">
            <span className="text-prismo-text-dim">↑</span>
            {event.token_usage?.input_tokens?.toLocaleString() || 0}
            {' '}
            <span className="text-prismo-text-dim">↓</span>
            {event.token_usage?.output_tokens?.toLocaleString() || 0}
          </div>
        </div>
        <div className="bg-prismo-surface border border-prismo-border rounded-lg p-3">
          <div className="text-xs text-prismo-text-dim mb-1 flex items-center gap-1">
            <Clock size={10} /> Latency
          </div>
          <div className="text-sm font-mono text-prismo-text">
            {formatDuration(event.latency_ms)}
          </div>
        </div>
      </div>

      {/* Temperature / params */}
      {(event.parameters?.temperature !== undefined || event.parameters?.max_tokens !== undefined) && (
        <div className="flex gap-3 text-xs font-mono text-prismo-text-dim">
          {event.parameters.temperature !== undefined && (
            <span>temp={event.parameters.temperature}</span>
          )}
          {event.parameters.max_tokens !== undefined && (
            <span>max_tokens={event.parameters.max_tokens}</span>
          )}
          {event.stop_reason && (
            <span>stop={event.stop_reason}</span>
          )}
        </div>
      )}

      {/* System prompt */}
      {event.system_prompt && (
        <div className="rounded-lg border border-prismo-border bg-prismo-muted/40 p-3">
          <div className="text-xs text-prismo-text-dim mb-1.5 font-mono uppercase tracking-wide">
            System Prompt
          </div>
          <pre className="text-xs text-prismo-text font-mono whitespace-pre-wrap leading-relaxed max-h-24 overflow-auto">
            {event.system_prompt}
          </pre>
        </div>
      )}

      {/* Messages */}
      <div>
        <div className="text-xs text-prismo-text-dim mb-2 uppercase tracking-wide">
          Conversation ({event.messages?.length || 0} messages)
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
          {event.messages?.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
        </div>
      </div>

      {/* Response */}
      <div>
        <div className="text-xs text-prismo-text-dim mb-2 uppercase tracking-wide">Response</div>
        <div className="rounded-lg border border-prismo-blue/30 bg-prismo-blue-dim p-3">
          <pre className="text-sm text-prismo-text font-mono whitespace-pre-wrap leading-relaxed max-h-48 overflow-auto">
            {event.response_content || '(empty response)'}
          </pre>
        </div>
      </div>

      {/* Tool calls */}
      {event.tool_calls_made && event.tool_calls_made.length > 0 && (
        <div>
          <div className="text-xs text-prismo-text-dim mb-2 uppercase tracking-wide">
            Tool Calls ({event.tool_calls_made.length})
          </div>
          <div className="space-y-2">
            {event.tool_calls_made.map((tc) => (
              <ToolCallCard key={tc.tool_call_id} tc={tc} />
            ))}
          </div>
        </div>
      )}

      {/* Fork button */}
      <button
        onClick={onFork}
        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg
                   border border-prismo-blue/40 bg-prismo-blue-dim text-prismo-blue
                   hover:bg-prismo-blue/20 transition-colors text-sm font-medium"
      >
        <GitFork size={15} />
        Fork from here
      </button>
    </div>
  )
}
