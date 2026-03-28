import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useSessions(params?: {
  page?: number
  page_size?: number
  status?: string
  search?: string
  scope?: string
}) {
  return useQuery({
    queryKey: ['sessions', params],
    queryFn: () => api.sessions.list(params),
    refetchInterval: 5000,
  })
}

export function useSession(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.sessions.get(sessionId!),
    enabled: !!sessionId,
  })
}

export function useDeleteSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (sessionId: string) => api.sessions.delete(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })
}

export function useSessionForks(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['forks', sessionId],
    queryFn: () => api.sessions.forks(sessionId!),
    enabled: !!sessionId,
  })
}
