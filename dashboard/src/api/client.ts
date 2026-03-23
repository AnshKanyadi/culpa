/**
 * API client for communicating with the Prismo backend server.
 */

import type {
  Session,
  SessionListResponse,
  ForkRequest,
  ForkResult,
  AnyEvent,
} from '../lib/types'

const BASE_URL = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Request failed: ${response.status}`)
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  sessions: {
    list: (params?: {
      page?: number
      page_size?: number
      status?: string
      search?: string
    }): Promise<SessionListResponse> => {
      const query = new URLSearchParams()
      if (params?.page) query.set('page', String(params.page))
      if (params?.page_size) query.set('page_size', String(params.page_size))
      if (params?.status) query.set('status', params.status)
      if (params?.search) query.set('search', params.search)
      const qs = query.toString()
      return request(`/sessions${qs ? `?${qs}` : ''}`)
    },

    get: (sessionId: string): Promise<Session> =>
      request(`/sessions/${sessionId}`),

    delete: (sessionId: string): Promise<void> =>
      request(`/sessions/${sessionId}`, { method: 'DELETE' }),

    upload: (session: unknown): Promise<{ session_id: string }> =>
      request('/sessions', {
        method: 'POST',
        body: JSON.stringify(session),
      }),

    stats: (sessionId: string): Promise<{
      session_id: string
      summary: Session['summary']
      duration_ms?: number
      event_count: number
    }> => request(`/sessions/${sessionId}/stats`),

    diff: (sessionId: string): Promise<{
      session_id: string
      files: Record<string, Array<{
        event_id: string
        operation: string
        diff?: string
        timestamp: string
      }>>
    }> => request(`/sessions/${sessionId}/diff`),

    fork: (sessionId: string, body: ForkRequest): Promise<ForkResult> =>
      request(`/sessions/${sessionId}/fork`, {
        method: 'POST',
        body: JSON.stringify(body),
      }),

    forks: (sessionId: string): Promise<{ session_id: string; forks: ForkResult[] }> =>
      request(`/sessions/${sessionId}/forks`),
  },

  events: {
    list: (sessionId: string, eventType?: string): Promise<{
      session_id: string
      events: AnyEvent[]
      count: number
    }> => {
      const qs = eventType ? `?event_type=${eventType}` : ''
      return request(`/sessions/${sessionId}/events${qs}`)
    },

    get: (sessionId: string, eventId: string): Promise<AnyEvent> =>
      request(`/sessions/${sessionId}/events/${eventId}`),

    timeline: (sessionId: string): Promise<{
      session_id: string
      timeline: unknown[]
    }> => request(`/sessions/${sessionId}/timeline`),
  },

  forks: {
    get: (forkId: string): Promise<ForkResult> =>
      request(`/forks/${forkId}`),
  },

  health: (): Promise<{ status: string; version: string }> =>
    request('/health'),
}
