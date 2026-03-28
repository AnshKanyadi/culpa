export type EventType = 'llm_call' | 'tool_call' | 'file_change' | 'terminal_cmd'
export type FileOperation = 'create' | 'modify' | 'delete'
export type SessionStatus = 'recording' | 'completed' | 'failed'

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_write_tokens: number
  total_tokens?: number
}

export interface LLMParameters {
  temperature?: number
  top_p?: number
  max_tokens?: number
  stop_sequences?: string[]
  tools?: unknown[]
  extra?: Record<string, unknown>
}

export interface ToolCallRecord {
  tool_call_id: string
  tool_name: string
  input_arguments: Record<string, unknown>
  output_result?: unknown
  error?: string
}

export interface Message {
  role: string
  content: string | unknown[]
  tool_call_id?: string
  name?: string
}

export interface BaseEvent {
  event_id: string
  event_type: EventType
  timestamp: string
  sequence: number
  parent_event_id?: string
  session_id: string
}

export interface LLMCallEvent extends BaseEvent {
  event_type: 'llm_call'
  model: string
  messages: Message[]
  parameters: LLMParameters
  system_prompt?: string
  response_content: string
  token_usage: TokenUsage
  stop_reason?: string
  tool_calls_made: ToolCallRecord[]
  latency_ms: number
  request_start?: string
  first_token_at?: string
  request_end?: string
  raw_response?: Record<string, unknown>
}

export interface ToolCallEvent extends BaseEvent {
  event_type: 'tool_call'
  tool_name: string
  input_arguments: Record<string, unknown>
  output_result?: unknown
  error?: string
  duration_ms: number
  side_effects: string[]
}

export interface FileChangeEvent extends BaseEvent {
  event_type: 'file_change'
  file_path: string
  operation: FileOperation
  content_before?: string
  content_after?: string
  diff?: string
  triggering_llm_call_id?: string
}

export interface TerminalCommandEvent extends BaseEvent {
  event_type: 'terminal_cmd'
  command: string
  working_directory?: string
  stdout: string
  stderr: string
  exit_code: number
  duration_ms: number
}

export type AnyEvent = LLMCallEvent | ToolCallEvent | FileChangeEvent | TerminalCommandEvent

export interface SessionSummary {
  total_llm_calls: number
  total_input_tokens: number
  total_output_tokens: number
  estimated_cost_usd: number
  files_created: number
  files_modified: number
  files_deleted: number
  files_touched: string[]
  tool_calls: number
  terminal_commands: number
  error_count: number
  models_used: string[]
}

export interface Session {
  session_id?: string
  id?: string
  name: string
  status: SessionStatus
  metadata: Record<string, unknown>
  started_at: string
  ended_at?: string
  duration_ms?: number
  events: AnyEvent[]
  summary: SessionSummary
}

export interface ForkRequest {
  fork_point_event_id: string
  injected_response: string
  injected_tool_calls?: ToolCallRecord[]
}

export interface ForkResult {
  fork_id: string
  session_id: string
  fork_point_event_id: string
  original_events_after: AnyEvent[]
  forked_events: AnyEvent[]
  injected_response: string
  created_at: string
  divergence_summary?: string
  file_diffs: Record<string, string>
}

export interface SessionListItem {
  id: string
  name: string
  status: SessionStatus
  metadata: Record<string, unknown>
  started_at: string
  ended_at?: string
  duration_ms?: number
  expires_at?: string
  summary: SessionSummary
}

export interface SessionListResponse {
  sessions: SessionListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}
