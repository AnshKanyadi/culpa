/**
 * Root App component with router setup.
 */

import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SessionsList } from './pages/SessionsList'
import { SessionDetail } from './pages/SessionDetail'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<SessionsList />} />
          <Route path="/session/:sessionId" element={<SessionDetail />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
