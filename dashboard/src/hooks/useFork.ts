/**
 * Hook for managing fork operations.
 */

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { ForkResult, LLMCallEvent } from '../lib/types'

export function useFork(sessionId: string) {
  const [forkEvent, setForkEvent] = useState<LLMCallEvent | null>(null)
  const [forkResult, setForkResult] = useState<ForkResult | null>(null)
  const queryClient = useQueryClient()

  const forkMutation = useMutation({
    mutationFn: ({
      eventId,
      newResponse,
    }: {
      eventId: string
      newResponse: string
    }) =>
      api.sessions.fork(sessionId, {
        fork_point_event_id: eventId,
        injected_response: newResponse,
      }),
    onSuccess: (result) => {
      setForkResult(result)
      queryClient.invalidateQueries({ queryKey: ['forks', sessionId] })
    },
  })

  const openFork = (event: LLMCallEvent) => {
    setForkEvent(event)
    setForkResult(null)
  }

  const closeFork = () => {
    setForkEvent(null)
    setForkResult(null)
  }

  const runFork = (newResponse: string) => {
    if (!forkEvent) return
    forkMutation.mutate({
      eventId: forkEvent.event_id,
      newResponse,
    })
  }

  return {
    forkEvent,
    forkResult,
    isForking: forkMutation.isPending,
    forkError: forkMutation.error,
    openFork,
    closeFork,
    runFork,
  }
}
