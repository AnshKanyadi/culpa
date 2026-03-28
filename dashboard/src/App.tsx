import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { CommandPalette } from './components/CommandPalette'
import { SessionsList } from './pages/SessionsList'
import { SessionDetail } from './pages/SessionDetail'
import { Login } from './pages/Login'
import { Register } from './pages/Register'
import { ApiKeys } from './pages/ApiKeys'
import { Billing } from './pages/Billing'
import { BillingSuccess } from './pages/BillingSuccess'
import { SessionCompare } from './pages/SessionCompare'
import { Landing } from './pages/Landing'
import { Team } from './pages/Team'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-culpa-bg flex items-center justify-center">
        <div className="text-culpa-text-dim text-sm">Loading...</div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  return <div className="page-enter">{children}</div>
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/" replace />
  return <>{children}</>
}

function HomePage() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="min-h-screen bg-culpa-bg flex items-center justify-center">
        <div className="text-culpa-text-dim text-sm">Loading...</div>
      </div>
    )
  }
  if (user) return <div className="page-enter"><SessionsList /></div>
  return <Landing />
}

function AppShell() {
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false)
  const { user } = useAuth()

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (user) setCmdPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [user])

  return (
    <>
      <Routes>
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
        <Route path="/" element={<HomePage />} />
        <Route path="/dashboard" element={<ProtectedRoute><SessionsList /></ProtectedRoute>} />
        <Route path="/session/:sessionId" element={<ProtectedRoute><SessionDetail /></ProtectedRoute>} />
        <Route path="/compare" element={<ProtectedRoute><SessionCompare /></ProtectedRoute>} />
        <Route path="/settings/keys" element={<ProtectedRoute><ApiKeys /></ProtectedRoute>} />
        <Route path="/settings/team" element={<ProtectedRoute><Team /></ProtectedRoute>} />
        <Route path="/settings/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
        <Route path="/settings/billing/success" element={<ProtectedRoute><BillingSuccess /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {user && (
        <CommandPalette
          isOpen={cmdPaletteOpen}
          onClose={() => setCmdPaletteOpen(false)}
        />
      )}
    </>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppShell />
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: '#141415',
                border: '1px solid #1e1e21',
                color: '#e8e8ea',
                fontSize: '13px',
              },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
