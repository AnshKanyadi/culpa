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
    credentials: 'include',
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
      scope?: string
    }): Promise<SessionListResponse> => {
      const query = new URLSearchParams()
      if (params?.page) query.set('page', String(params.page))
      if (params?.page_size) query.set('page_size', String(params.page_size))
      if (params?.status) query.set('status', params.status)
      if (params?.search) query.set('search', params.search)
      if (params?.scope) query.set('scope', params.scope)
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

  auth: {
    register: (email: string, password: string, name?: string): Promise<{ user: import('../contexts/AuthContext').User }> =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, name }),
      }),

    login: (email: string, password: string): Promise<{ user: import('../contexts/AuthContext').User }> =>
      request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),

    logout: (): Promise<{ ok: boolean }> =>
      request('/auth/logout', { method: 'POST' }),

    me: (): Promise<{ user: import('../contexts/AuthContext').User }> =>
      request('/auth/me'),

    createKey: (name: string): Promise<{ key: string; record: unknown }> =>
      request('/keys', {
        method: 'POST',
        body: JSON.stringify({ name }),
      }),

    listKeys: (): Promise<{ keys: unknown[] }> =>
      request('/keys'),

    revokeKey: (keyId: string): Promise<void> =>
      request(`/keys/${keyId}`, { method: 'DELETE' }),

    usage: (): Promise<{
      session_count: number
      session_limit: number | null
      retention_days: number
      max_forks_per_session: number | null
      earliest_expiry: string | null
      at_limit: boolean
    }> => request('/usage'),
  },

  billing: {
    status: (): Promise<{
      plan: string
      stripe_customer_id?: string
      has_subscription: boolean
      plan_expires_at?: string
      subscription?: {
        status: string
        current_period_end: number
        cancel_at_period_end: boolean
      } | null
    }> => request('/billing/status'),

    createCheckout: (): Promise<{ checkout_url: string }> =>
      request('/billing/create-checkout', { method: 'POST' }),

    createPortal: (): Promise<{ portal_url: string }> =>
      request('/billing/portal', { method: 'POST' }),
  },

  teams: {
    list: (): Promise<{ teams: unknown[] }> =>
      request('/teams'),

    get: (teamId: string): Promise<{ team: unknown; members: unknown[]; pending_invites: unknown[] }> =>
      request(`/teams/${teamId}`),

    create: (name: string): Promise<{ team: unknown }> =>
      request('/teams', { method: 'POST', body: JSON.stringify({ name }) }),

    invite: (teamId: string, email: string): Promise<{ invite: unknown }> =>
      request(`/teams/${teamId}/invite`, { method: 'POST', body: JSON.stringify({ email }) }),

    join: (teamId: string): Promise<{ joined: boolean }> =>
      request(`/teams/${teamId}/join`, { method: 'POST' }),

    removeMember: (teamId: string, userId: string): Promise<void> =>
      request(`/teams/${teamId}/members/${userId}`, { method: 'DELETE' }),

    setVisibility: (sessionId: string, visibility: 'private' | 'team'): Promise<unknown> =>
      request(`/teams/sessions/${sessionId}/visibility`, {
        method: 'PATCH',
        body: JSON.stringify({ visibility }),
      }),
  },
}
